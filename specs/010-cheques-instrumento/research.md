# Research: 010-cheques-instrumento

**Date**: 2026-10-21  
**Branch**: `010-cheques-instrumento`  
**Spec**: [spec.md](./spec.md)

El Technical Context no tiene puntos pendientes de clarificación. Esta investigación documenta las decisiones de diseño, basadas en la lectura del código actual (`models/movimiento.py`, `services/movimiento_service.py`, `api/routes/{movimientos,cajas,informes}.py`, `services/{caja,informe}_service.py`, `services/pdf_informe_renderer.py` y el frontend de Registro/Consulta).

---

## 1. Modelo: ¿tabla nueva `cheque` o extender `movimiento`?

### Decision
Extender la tabla `movimiento` con tres columnas nuevas y hacer `subtotal` nullable:

| Columna | Tipo | Significado |
|---|---|---|
| `instrumento` | `VARCHAR(10) NOT NULL` (`ninguno` \| `cheque` \| `echeque`) | Instrumento. Los movimientos existentes quedan en `ninguno`. |
| `fecha_liquidacion` | `DATE NULL` | Fecha estimada de cobro/pago (calendario Argentina). Obligatoria si `instrumento <> 'ninguno'`. |
| `fecha_liquidado` | `TIMESTAMPTZ NULL` | Momento en que se pulsó **Liquidar**. `NULL` = pendiente. |

Estados derivados (no persistidos): `ninguno` → sin estado; `cheque/echeque` con `fecha_liquidado IS NULL` → **Pendiente**; con `fecha_liquidado` → **Liquidado**.

La **fecha de carga** NO necesita columna nueva: es `COALESCE(fecha_override, created_at)`, la misma regla que ya usa la feature 009 para la "Fecha (opcional)" (FR-008 de la spec).

### Rationale
- Un cheque ES un movimiento de caja que cambia de estado: al liquidarse debe formar parte del mismo stream (caja, moneda) y de la misma lista cronológica. Una tabla aparte obligaría a duplicar descripción/monto/tipo/moneda/auditoría y a migrar filas al liquidar.
- Reutiliza `created_by`, `updated_by`, `updated_at` para auditoría (FR-028): al liquidar se completan `updated_by` y `updated_at`.
- `descripcion`, `monto`, `tipo`, `moneda`, edición, eliminación y cajas adicionales funcionan sin duplicar código.

### Alternatives considered
- **Tabla `cheque` separada** (como `plazo_fijo`): más aislamiento, pero duplica el CRUD y obliga a insertar un `movimiento` al liquidar con riesgo de inconsistencia entre ambas tablas. Descartado.
- **Dos fechas de carga (`fecha_carga` explícita)**: redundante con `COALESCE(fecha_override, created_at)`. Descartado.
- **Subtotal = 0 como placeholder para pendientes**: oculta el estado y expone un valor falso en todas las consultas que lean `subtotal`. Descartado en favor de `NULL` + constraint.

---

## 2. Subtotal de cheques pendientes: `NULL` protegido por constraint

### Decision
`movimiento.subtotal` pasa a ser `NUMERIC(15,2) NULL`. Tres `CHECK` mantienen la integridad en la base de datos:

1. `ck_movimiento_instrumento`: `instrumento IN ('ninguno','cheque','echeque')`.
2. `ck_movimiento_cheque_fechas`: `(instrumento = 'ninguno' AND fecha_liquidacion IS NULL AND fecha_liquidado IS NULL) OR (instrumento <> 'ninguno' AND fecha_liquidacion IS NOT NULL)`.
3. `ck_movimiento_subtotal_estado`: `(subtotal IS NOT NULL) = (instrumento = 'ninguno' OR fecha_liquidado IS NOT NULL)` — solo los movimientos que impactan el saldo tienen subtotal.

El predicado "impacta en el saldo" es exactamente `subtotal IS NOT NULL` (en SQL) / `Movimiento.impacta_saldo` (propiedad Python).

### Rationale
- Hace imposible, a nivel de datos, que un cheque pendiente contamine un stream (Principio I).
- Toda consulta de stream debe filtrar `subtotal IS NOT NULL`; se centraliza en un único helper (ver §4) y se cubre con tests de paridad.

### Alternatives considered
- **Columna `estado` explícita**: redundante con `fecha_liquidado` y permite estados incoherentes. Descartado.

---

## 3. Fecha efectiva y orden del stream

### Decision
Definir la **fecha efectiva** de un movimiento que impacta el saldo:

```
fecha_efectiva = COALESCE(fecha_liquidado, fecha_override, created_at)
```

- Movimientos comunes: igual que hoy (`fecha_override` o `created_at`).
- Cheques liquidados: su `fecha_liquidado` (cumple la clarificación "se ubica al final del historial, según la fecha liquidado").
- Se implementa una sola vez en `app/models/movimiento.py` (`effective_date_expr()` para SQL, `effective_date(m)` para Python) y se usa en todos los `ORDER BY`, filtros de fecha y cálculos de saldo.
- El índice actual `idx_movimiento_caja_moneda_fecha` (feature 009) se reemplaza por un índice parcial `WHERE subtotal IS NOT NULL` sobre `(caja_id, moneda, COALESCE(fecha_liquidado, fecha_override, created_at) DESC, id DESC)`.
- Se agrega un índice parcial para pendientes: `(fecha_liquidacion, id) WHERE instrumento <> 'ninguno' AND fecha_liquidado IS NULL`.

### Rationale
- Hoy `GET /cajas/{id}/saldo`, `list_saldos_cajas_activas`, `InformeService.fetch_saldo_*`, `compute_saldo_cierre*`, `fetch_movimientos_informe` y `list_movimientos` ordenan por `created_at`, mientras que `MovimientoService` ya ordena por `COALESCE(fecha_override, created_at)` (feature 009). Para un cheque liquidado con `created_at` antiguo, ordenar por `created_at` lo dejaría en el medio del historial y rompería el saldo y el orden. Hay que unificar el criterio.
- Los movimientos sin `fecha_override` y sin instrumento ordenan idéntico a hoy: **paridad garantizada** (tests de paridad en WU-2).

### Alternatives considered
- **Pisar `fecha_override = now` al liquidar**: perdería la fecha de carga manual del cheque. Descartado.
- **Mantener `created_at` y mover el cheque al insertarlo**: no hay inserción al liquidar (el registro ya existe). Descartado.

---

## 4. Cálculo del saldo actual: suma en lugar de "último subtotal"

### Decision
El saldo actual de (caja, moneda) pasa a calcularse como:

```
saldo = SUM(CASE tipo WHEN 'entrada' THEN monto ELSE -monto END)
        WHERE caja_id = :c AND moneda = :m AND subtotal IS NOT NULL
```

Se centraliza en un nuevo `app/services/saldo_service.py` (`get_saldo_actual`, `get_saldos_caja`, `get_saldos_cajas_activas`) y lo consumen `cajas.py` (`/saldo`), `caja_service.list_saldos_cajas_activas` (`/saldo-general`), `informe_service` (saldo actual) y el cálculo de saldo a futuro.

### Rationale
- La suma es independiente del orden y de subtotales almacenados potencialmente desactualizados. Esto evita un riesgo ya presente: `create_movimiento` con `fecha_override` en el pasado calcula `subtotal = último + monto` y no recalcula los posteriores; si el saldo se leyera como "subtotal de la última fila por fecha efectiva", ese caso devolvería un saldo incorrecto.
- Es equivalente al "último subtotal" cuando el stream es consistente (test de paridad).
- Rendimiento: ≤ cientos/miles de filas por stream, con el índice de stream; muy por debajo de SC-008 (< 2 s).

### Alternatives considered
- **Último subtotal por fecha efectiva**: depende de que los subtotales almacenados estén siempre recalculados. Descartado por el riesgo anterior.
- **Tabla/columna de saldo materializado**: complejidad innecesaria para ≤ 10 usuarios (Principio VI). Descartado.

### Hardening incluido (brecha preexistente de la feature 009)
`MovimientoService.create_movimiento` con `fecha_override` informado ejecuta `recalculate_subtotals(caja_id, moneda)` al final, de modo que la columna **Subtotal** del historial quede consistente con el orden cronológico. Sin `fecha_override` el comportamiento es idéntico al actual. La liquidación de un cheque también recalcula el stream completo (ver §5).

---

## 5. Liquidación: atomicidad, idempotencia y concurrencia

### Decision
Nuevo endpoint `POST /api/v1/cajas/{caja_id}/movimientos/{movimiento_id}/liquidar` (rol `secretaria`). Algoritmo en `MovimientoService.liquidar_cheque`:

1. Tomar un lock de fila sobre la **caja** (`SELECT ... FROM caja WHERE id = :id FOR UPDATE`) como mutex del stream de esa caja.
2. Leer el cheque con `FOR UPDATE`; validar que pertenece a la caja, que `instrumento <> 'ninguno'` (si no: 404) y que `fecha_liquidado IS NULL` (si no: **409 Conflict**).
3. `fecha_liquidado = now(UTC)`, `updated_at = now`, `updated_by = user.id`.
4. `recalculate_subtotals(caja_id, moneda)`: reproduce el stream en orden de fecha efectiva y completa el `subtotal` del cheque.
5. Commit en el router; ante excepción, `rollback` (el cheque permanece pendiente — FR-014).

### Rationale
- Bloquear primero la caja y luego las filas evita *deadlocks* entre dos liquidaciones simultáneas sobre el mismo stream (cada una tomaría su fila de cheque y luego esperaría la del otro en `recalculate_subtotals`). El costo (serializar por caja) es irrelevante con ≤ 10 usuarios.
- La segunda llamada concurrente espera el lock, ve `fecha_liquidado` ya seteado y responde 409 sin duplicar el impacto (FR-013).
- Recalcular todo el stream (en vez de `último + monto`) mantiene la consistencia aun si existen movimientos con fecha futura manual posteriores al "ahora" (la feature 009 permite fechas futuras).

### Alternatives considered
- **Idempotencia silenciosa (200 sin efecto)**: oculta errores de uso; la spec pide rechazar. Descartado, se elige 409.
- **Advisory locks de Postgres**: funciona pero agrega un mecanismo nuevo; el lock de fila de `caja` es suficiente y portable con los tests actuales. Descartado.

---

## 6. Validación de Fecha de liquidación

### Decision
- Esquema Pydantic (`CreateMovimientoRequest` / `UpdateMovimientoRequest`): `fecha_liquidacion` string `YYYY-MM-DD` (misma regex y validación calendario que `fecha_manual`) y **estrictamente mayor** que `today_ar()`; error 422 con mensaje en español.
- Reglas cruzadas (`model_validator`): `instrumento != 'ninguno'` ⇒ `fecha_liquidacion` obligatoria; `instrumento == 'ninguno'` ⇒ `fecha_liquidacion` debe ser `None`; `instrumento != 'ninguno'` + `registrar_complementario=true` ⇒ 422 (FR-005, backend como autoridad).
- Frontend: atributo `min` = mañana (UX), pero la autoridad es el servidor (security-main §2).
- `today_ar()` ya existe en `app/core/dates.py`; los tests lo parchean en `app.schemas.movimiento` para evitar dependencias del reloj.

### Alternatives considered
- **Validar solo en el servicio con `ValueError → 400`**: el repo usa 422 para esquemas y 400 para reglas de servicio. Como es validación de entrada, se prefiere 422.

---

## 7. Edición y eliminación de cheques

### Decision
- `UpdateMovimientoRequest` agrega `instrumento: Literal["cheque","echeque"] | None` y `fecha_liquidacion`. El literal **no incluye** `"ninguno"`, por lo que pasar a "-" da 422 (clarificación: solo Cheque ↔ Echeque).
- Reglas en `update_movimiento`:
  - Registro con `instrumento = 'ninguno'` + payload con `instrumento` o `fecha_liquidacion` → 400 (no se convierte un movimiento común en cheque).
  - `fecha_liquidacion` solo editable en pendientes (400 si ya está liquidado); debe ser > hoy.
  - Pendiente: no se llama a `recalculate_subtotals` (no impacta saldo); aplica tanto a cambios de monto, tipo o moneda.
  - Liquidado: se aplican las reglas actuales (recálculo en cascada de (caja, moneda), y de la moneda anterior si cambia).
- `delete_movimiento`: si el registro era pendiente no se recalcula; si impactaba el saldo, se mantiene el recálculo actual.

### Rationale
Cumple FR-016 y las clarificaciones sin tocar subtotales por accidente (Principio I).

---

## 8. Saldo a futuro (proyección)

### Decision
- Función **pura** `proyectar_saldo_futuro(saldo_actual, cheques, hoy)` en `app/services/saldo_futuro.py` (sin acceso a DB; trivialmente testeable con TDD):
  - Agrupa los cheques **pendientes** por `fecha_liquidacion`, ordena ascendente.
  - Efecto neto del grupo: Σ entradas − Σ salidas.
  - `saldo_proyectado` = saldo anterior de la proyección + efecto neto (acumulado; la primera fila parte de `saldo_actual`).
  - `vencido = fecha_liquidacion <= hoy` (consistente con "aptos para liquidar" de la sección Cheques).
  - Se calcula por moneda de forma independiente (ARS y USD).
- Endpoint `GET /api/v1/cajas/{caja_id}/saldo-futuro` (cualquier usuario autenticado; lectura). Devuelve por moneda: `saldo_actual` y `filas[]`.
- El **servidor** calcula (Principio V). El informe PDF reutiliza la misma función (FR-032) y garantiza valores idénticos a pantalla (SC-009).
- Frontend: el desplegable (`<details>`) carga el dato al expandirse y lo refresca cuando cambian los cheques (alta, edición, eliminación, liquidación).

### Alternatives considered
- **Incluir la proyección en `GET /saldo`**: cada refresco del Valor de caja pagaría la consulta aunque el desplegable esté cerrado. Descartado; se prefiere endpoint separado y carga diferida.
- **Calcular en el frontend**: viola el Principio V (el frontend no calcula saldos de forma autoritativa). Descartado.

---

## 9. Sección Cheques (todas las cajas)

### Decision
- `GET /api/v1/cheques?categoria=aptos|proximos&page=N` (roles `secretaria` y `escribano`), **paginado** (tamaño fijo 20, como el resto del repo) y ordenado por `fecha_liquidacion ASC, id ASC`.
  - `aptos`: pendientes con `fecha_liquidacion <= hoy_ar`.
  - `proximos`: pendientes con `hoy_ar < fecha_liquidacion <= último día del mes calendario actual` (helper `end_of_month` en `core/dates.py`).
  - Incluye cajas archivadas (supuesto de la spec).
- El frontend hace una llamada por categoría, cada una con su propia paginación, y muestra **Liquidar** solo a la secretaria, que invoca el endpoint de §5 (con `caja.id` del ítem).
- Ruta frontend `/cheques` (accesible a ambos roles) y enlace entre "Consulta plazos fijos" e "Impresión".

### Alternatives considered
- **Un solo listado con filtro**: la spec pide dos listados diferenciados. Descartado.
- **Endpoint por caja**: la sección es transversal a todas las cajas. Descartado.

---

## 10. Bloque de cheques pendientes por caja (Registro y Consulta)

### Decision
- `GET /api/v1/cajas/{caja_id}/cheques-pendientes?page&moneda&fecha_desde&fecha_hasta` (cualquier usuario autenticado), paginado (20), orden `fecha_liquidacion ASC, id ASC`. Los filtros `moneda`/`fecha_*` aplican sobre la **fecha de carga** (`COALESCE(fecha_override, created_at)` en AR).
- `GET /cajas/{caja_id}/movimientos` pasa a devolver **solo movimientos que impactan el saldo** (comunes y cheques liquidados) y filtra por fecha efectiva.
- El bloque aparece **arriba** del historial en Registro (con **Liquidar / Editar / Eliminar**, solo secretaria) y en Consulta (solo lectura, sin acciones), según la clarificación.

### Rationale
Separa las dos poblaciones (pendientes sin subtotal / movimientos con subtotal) tanto en datos como en UI, sin mezclar filas sin subtotal en una tabla cronológica.

---

## 11. Informe de Impresión (tipo Caja)

### Decision
- `InformeService.fetch_movimientos_informe`: solo movimientos que impactan el saldo (`subtotal IS NOT NULL`), filtro de rango por fecha efectiva AR, orden por fecha efectiva desc. `compute_saldo_cierre*` pasa a usar la fecha efectiva.
- `fetch_saldo_actual/ars/usd` delegan en `saldo_service` (suma).
- Nuevo `fetch_cheques_pendientes(caja_id)` (todos los pendientes de la caja, no filtrados por período; tope defensivo de 1000 filas con leyenda) y `fetch_saldo_futuro(caja_id)` usando la función pura de §8.
- `render_caja_pdf` agrega: (a) prefijo `[Cheque]`/`[Echeque]` en la descripción de cheques liquidados y la fecha mostrada = fecha efectiva; (b) sección **Cheques pendientes** (tabla); (c) sección **Saldo a futuro** por moneda. El informe de Plazos Fijos no cambia.
- Se mantiene fuente core `Times` (solo latin-1) → etiquetas del informe sin caracteres fuera de latin-1 (consistente con el renderer actual).

---

## 12. Autorización, auditoría y logging

### Decision
- Crear/editar/eliminar/liquidar: `require_role("secretaria")` (403 para Escribano — FR-027, Principio II).
- Lecturas (`saldo-futuro`, `cheques-pendientes`, `/cheques`): `get_current_user` (ambos roles). Todas validan existencia de la caja (404).
- Eventos de seguridad (`log_security_event`): `movimiento_created` (se agrega `instrumento`), `cheque_liquidated`, `movimiento_updated`/`movimiento_deleted` (sin PII ni montos en logs, consistente con el resto).
- Los DTO nunca exponen entidades ORM completas (security-main §1.4); `subtotal` es `null` solo para pendientes.

---

## 13. Dependencias y compatibilidad

### Decision
- **Sin dependencias nuevas** (backend ni frontend). Se verificó en `pyproject.toml` y `package.json`.
- **Migración Alembic `010_movimiento_cheque`** (down_revision `009_movimiento_fecha_override`):
  - `upgrade`: agrega columnas (`instrumento` con backfill `'ninguno'`), hace `subtotal` nullable, crea los tres `CHECK`, reemplaza el índice de stream por el parcial, crea el índice de pendientes.
  - `downgrade`: **aborta con error explícito si existen cheques pendientes** (para no perder datos); si no hay, restaura índice, `subtotal NOT NULL`, elimina constraints y columnas (los cheques liquidados quedan como movimientos comunes con su subtotal).
- La API es **aditiva**: nuevos campos opcionales en request y nuevos campos en response. Único cambio de tipo: `subtotal` puede ser `null`, solo en cheques pendientes (que no aparecen en `/movimientos`).
- Los tests de backend crean el esquema con `Base.metadata.create_all`; los `CHECK` se declaran también en el modelo para que los tests los ejerciten.

---

## 14. Estrategia de testing (TDD-first, según la spec)

| Nivel | Qué cubre |
|---|---|
| Unit (pytest) | `proyectar_saldo_futuro`; `end_of_month`; validadores de schema (fecha > hoy, combinaciones instrumento/fecha, cheque + complementario); `impacta_saldo`/estado derivado; `compute_subtotal`/recálculo con cheques; renderer PDF. |
| Integración (pytest + DB) | Crear cheque sin impacto; liquidar (entrada/salida, doble liquidación 409, concurrencia lógica); RBAC (Escribano 403 en create/update/delete/liquidar, 200 en lecturas); `/cheques` (aptos/próximos, paginación, exclusión de liquidados y meses posteriores); `saldo-futuro` (acumulado, agrupación por fecha, vencidos, ARS/USD); paridad de `/saldo`, `/saldo-general` e informes; informe con cheques pendientes. |
| Frontend (Vitest + Testing Library) | `MovimientoForm` (instrumento, fecha de liquidación, oculta "Entrada y Salida", reset); `ChequesPendientesBlock`; `SaldoFuturoDesplegable`; `ChequesPage`; `Navbar` (orden del enlace y roles); rutas. |

Los tests de integración de subtotales y RBAC son obligatorios por constitución.

---

## 15. Observaciones sobre el repositorio

- `.cursor/rules/specify-rules.mdc` (ignorado por git) contiene entradas de una feature `010-caja-liquidacion-futura` con **APScheduler** que no corresponden a esta rama/plan. Esta feature **no** incorpora ningún scheduler (la llegada de la fecha de liquidación no liquida automáticamente — spec FR-010).
- No existe `.spec-kitti/discovery/`; la estructura se tomó del código y de planes anteriores (001–009).
- No hay referencia de Figma para esta feature: `/spec-kitti.tasks` deberá solicitarla (regla `spec-kitti-figma.mdc`); la disposición actual del repo se basa en los `.drawio` y en CSS propio.
