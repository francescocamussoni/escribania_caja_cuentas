# Data Model: 010-cheques-instrumento

**Date**: 2026-10-21  
**Branch**: `010-cheques-instrumento`  
**Migración**: `backend/alembic/versions/010_movimiento_cheque.py` (down_revision `009_movimiento_fecha_override`)

---

## 1. Entidad modificada: `Movimiento` (tabla `movimiento`)

### 1.1 Columnas nuevas

| Columna | Tipo SQL | Null | Default | Descripción |
|---|---|---|---|---|
| `instrumento` | `VARCHAR(10)` | NO | `'ninguno'` (backfill; default a nivel ORM) | `ninguno` \| `cheque` \| `echeque` |
| `fecha_liquidacion` | `DATE` | SÍ | `NULL` | Fecha **estimada** de cobro/pago (calendario AR). Obligatoria y futura al crear un cheque. |
| `fecha_liquidado` | `TIMESTAMPTZ` | SÍ | `NULL` | Momento en que se liquidó. `NULL` ⇒ pendiente. |

### 1.2 Columna modificada

| Columna | Antes | Después | Motivo |
|---|---|---|---|
| `subtotal` | `NUMERIC(15,2) NOT NULL` | `NUMERIC(15,2) NULL` | Los cheques pendientes no tienen subtotal (no impactan el saldo). |

### 1.3 Columnas existentes relevantes (sin cambio)

| Columna | Rol en la feature |
|---|---|
| `created_at` | Auditoría del INSERT. **Fecha de carga** si no hay `fecha_override`. |
| `fecha_override` | **Fecha (opcional)** del formulario (09:00 AR). Si existe, es la **fecha de carga** del cheque. |
| `created_by` | Usuario que cargó el cheque. |
| `updated_at`, `updated_by` | Al liquidar/editar se completan (auditoría de liquidación). |
| `tipo` | `entrada` = cheque recibido (suma al liquidar) · `salida` = cheque emitido (resta). |
| `moneda`, `caja_id`, `monto`, `descripcion` | Sin cambios. |

### 1.4 Constraints (en migración **y** en el modelo, para que `create_all` de los tests los aplique)

| Nombre | Expresión |
|---|---|
| `ck_movimiento_instrumento` | `instrumento IN ('ninguno','cheque','echeque')` |
| `ck_movimiento_cheque_fechas` | `(instrumento = 'ninguno' AND fecha_liquidacion IS NULL AND fecha_liquidado IS NULL) OR (instrumento <> 'ninguno' AND fecha_liquidacion IS NOT NULL)` |
| `ck_movimiento_subtotal_estado` | `(subtotal IS NOT NULL) = (instrumento = 'ninguno' OR fecha_liquidado IS NOT NULL)` |

Constraints existentes (`ck_movimiento_monto_positive`, `ck_movimiento_tipo`, `ck_movimiento_moneda`) no cambian.

### 1.5 Índices

| Índice | Acción | Definición |
|---|---|---|
| `idx_movimiento_caja_moneda_fecha` (feature 009) | **REEMPLAZAR** por `idx_movimiento_stream_efectiva` | `(caja_id, moneda, COALESCE(fecha_liquidado, fecha_override, created_at) DESC, id DESC) WHERE subtotal IS NOT NULL` |
| `idx_movimiento_cheque_pendiente` | **NUEVO** | `(fecha_liquidacion, id) WHERE instrumento <> 'ninguno' AND fecha_liquidado IS NULL` |
| `idx_movimiento_cheque_caja_pendiente` | **NUEVO** | `(caja_id, moneda, fecha_liquidacion, id) WHERE instrumento <> 'ninguno' AND fecha_liquidado IS NULL` |

> Los índices con expresión/parciales se crean con `op.execute` (igual que en la migración 009).

### 1.6 Propiedades derivadas (Python, no persistidas)

| Propiedad | Definición |
|---|---|
| `es_cheque` | `instrumento != 'ninguno'` |
| `estado_cheque` | `None` si `ninguno`; `'pendiente'` si `fecha_liquidado is None`; si no `'liquidado'` |
| `impacta_saldo` | `subtotal is not None` (equivale a `instrumento == 'ninguno' or fecha_liquidado is not None`) |
| `fecha_carga` | `fecha_override or created_at` |
| `fecha_efectiva` | `fecha_liquidado or fecha_override or created_at` |

### 1.7 Reglas de negocio

| # | Regla | Origen |
|---|---|---|
| R1 | Solo los registros con `impacta_saldo` participan en el stream (caja, moneda): subtotal, saldo, informes, saldo general. | FR-010, FR-029 |
| R2 | `fecha_liquidacion` > `today_ar()` al crear; igual al editar un pendiente. | FR-004, FR-016 |
| R3 | Liquidar: `fecha_liquidado = now`, se completa el `subtotal` por recálculo del stream en orden de `fecha_efectiva`; el cheque queda al final del historial (salvo movimientos con fecha futura manual). | FR-012 |
| R4 | Un cheque liquidado no puede volver a liquidarse (409). No existe "deshacer". | FR-013, supuestos |
| R5 | `instrumento` solo puede cambiar entre `cheque` ↔ `echeque`; nunca desde/hacia `ninguno`. | Clarificación sesión 2 |
| R6 | Un cheque no admite `registrar_complementario = true` (sin "Entrada y Salida"). | FR-005 |
| R7 | Editar/eliminar un **pendiente** no recalcula ningún stream. Editar/eliminar un **liquidado** sí (cascada, como hoy). | FR-016 |
| R8 | `fecha_liquidacion` solo es editable mientras el cheque está pendiente. | FR-016 |
| R9 | Los movimientos existentes quedan `instrumento = 'ninguno'` sin otros cambios. | FR-030 |

### 1.8 Estados del cheque

```
        crear (Entrada/Salida + instrumento)
                    │
                    ▼
             ┌─────────────┐   editar (monto/desc/tipo/moneda/instrumento↔/fecha_liquidacion)
             │  PENDIENTE  │◄──┐
             │ subtotal=∅  │───┘
             └──────┬──────┘
                    │ Liquidar (secretaria) — atómico, 409 si ya liquidado
                    ▼
             ┌─────────────┐   editar/eliminar: reglas de movimiento + recálculo en cascada
             │  LIQUIDADO  │◄──┐
             │ subtotal=n  │───┘
             └─────────────┘
   eliminar (desde PENDIENTE): desaparece sin recalcular
```

---

## 2. Vistas calculadas (no persistidas)

### 2.1 `SaldoActual(caja, moneda)`

```
SUM(CASE tipo WHEN 'entrada' THEN monto ELSE -monto END)
WHERE caja_id = :c AND moneda = :m AND subtotal IS NOT NULL      (0.00 si no hay filas)
```

### 2.2 `SaldoFuturo(caja)` — por moneda

| Campo | Tipo | Descripción |
|---|---|---|
| `moneda` | `ARS` \| `USD` | Stream |
| `saldo_actual` | decimal | Ver 2.1 |
| `filas[]` | lista ordenada por `fecha_liquidacion ASC` | Una fila por fecha distinta de cheques pendientes |
| `filas[].fecha_liquidacion` | date | Fecha estimada (agrupa cheques con la misma fecha) |
| `filas[].vencido` | bool | `fecha_liquidacion <= hoy_ar` |
| `filas[].cheques` | int | Cantidad de cheques en la fecha |
| `filas[].efecto_neto` | decimal | Σ entradas − Σ salidas de la fecha |
| `filas[].saldo_proyectado` | decimal | `saldo_actual` + Σ `efecto_neto` de todas las filas hasta esta (acumulado) |

Ejemplo (spec US4): saldo ARS 1000, cheque entrada 500 en D1, salida 200 en D2 (D2 > D1):

| | fecha | efecto_neto | saldo_proyectado |
|---|---|---|---|
| Hoy | — | — | 1000.00 |
| Fila 1 | D1 | +500.00 | 1500.00 |
| Fila 2 | D2 | −200.00 | 1300.00 |

### 2.3 Categorías de la sección Cheques (solo pendientes, todas las cajas)

| Categoría | Condición |
|---|---|
| `aptos` | `fecha_liquidacion <= hoy_ar` |
| `proximos` | `hoy_ar < fecha_liquidacion <= último_día_del_mes(hoy_ar)` |

Fuera de ambas: pendientes con fecha en meses posteriores y todos los liquidados.

---

## 3. Schemas de API (resumen; contrato completo en `contracts/openapi-delta.yaml`)

### `CreateMovimientoRequest` (+)
| Campo | Tipo | Regla |
|---|---|---|
| `instrumento` | `"ninguno" \| "cheque" \| "echeque"` (default `"ninguno"`) | |
| `fecha_liquidacion` | `str \| None` (`YYYY-MM-DD`) | Obligatoria si `instrumento != ninguno`; prohibida si `ninguno`; > hoy AR. |
| (cruce) `registrar_complementario` | `bool` | Debe ser `false` si `instrumento != ninguno`. |

### `UpdateMovimientoRequest` (+)
| Campo | Tipo | Regla |
|---|---|---|
| `instrumento` | `"cheque" \| "echeque" \| None` | No admite `"ninguno"` (422). Solo sobre registros que ya son cheque (400 si no). |
| `fecha_liquidacion` | `str \| None` | Solo pendientes; > hoy AR. |

### `MovimientoResponse` (+)
| Campo | Tipo | Notas |
|---|---|---|
| `instrumento` | `"ninguno" \| "cheque" \| "echeque"` | |
| `estado` | `"pendiente" \| "liquidado" \| null` | `null` si `ninguno`. |
| `subtotal` | `string \| null` | `null` solo en pendientes. |
| `fecha` | datetime | Fecha efectiva (pendientes: fecha de carga). |
| `fecha_carga` | datetime | `COALESCE(fecha_override, created_at)` |
| `fecha_liquidacion` | date \| null | |
| `fecha_liquidado` | datetime \| null | |
| `liquidable` | bool | `true` si pendiente **y** el usuario es secretaria. |

### Nuevos DTOs
- `ChequeItemResponse` (listado transversal: `MovimientoResponse` + caja ya incluida) y `PaginatedChequesResponse`.
- `SaldoFuturoResponse { caja, fecha_calculo, monedas: [SaldoFuturoMoneda] }`, `SaldoFuturoMoneda`, `SaldoFuturoFila`.

---

## 4. Impacto en consultas existentes

| Consulta / módulo | Cambio |
|---|---|
| `MovimientoService.create_movimiento` | Cheque: sin stream, `subtotal = NULL`. Común: filtro `subtotal IS NOT NULL`, orden por fecha efectiva; con `fecha_override` ⇒ `recalculate_subtotals` al final (hardening). |
| `MovimientoService.recalculate_subtotals` | Solo filas con `impacta_saldo`; orden por fecha efectiva. |
| `MovimientoService.update_movimiento` / `delete_movimiento` | Ver R5–R8; sin recálculo para pendientes. |
| `routes/movimientos.py::list_movimientos` | Solo `impacta_saldo`; filtro de fecha y orden por fecha efectiva (AR). |
| `routes/cajas.py::get_caja_saldo` | `saldo_service` (suma). |
| `caja_service.list_saldos_cajas_activas` | `saldo_service` (suma por caja y moneda). |
| `informe_service` | Movimientos del informe solo `impacta_saldo`; fecha efectiva; saldos con `saldo_service`; nuevos `fetch_cheques_pendientes` y `fetch_saldo_futuro`. |
| `pdf_informe_renderer.render_caja_pdf` | Marca `[Cheque]/[Echeque]`; secciones **Cheques pendientes** y **Saldo a futuro**. |

---

## 5. Datos existentes y migración

| Aspecto | Tratamiento |
|---|---|
| Filas existentes | `instrumento = 'ninguno'`, `fecha_liquidacion = NULL`, `fecha_liquidado = NULL`; `subtotal` sin cambio (todas impactan saldo). |
| Orden de aplicación | (1) agregar columnas nullable y backfill, (2) `instrumento NOT NULL`, (3) `subtotal` nullable, (4) crear `CHECK`s, (5) reemplazar índice de stream, (6) crear índices de pendientes. |
| `downgrade` | Aborta con error claro si hay cheques pendientes; si no, revierte (cheques liquidados se conservan como movimientos comunes). |
| Verificación | `alembic upgrade head` → `downgrade -1` → `upgrade head` sin errores sobre una base con datos de 009. |
