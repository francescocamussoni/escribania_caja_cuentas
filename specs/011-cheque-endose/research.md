# Research: 011-cheque-endose

**Date**: 2026-11-04  
**Branch**: `011-cheque-endose`  
**Spec**: [spec.md](./spec.md)

El Technical Context no tiene puntos `NEEDS CLARIFICATION` pendientes. Esta investigación documenta las decisiones de diseño, basadas en la lectura del código vigente de la feature 010 (`models/movimiento.py`, `services/movimiento_service.py`, `api/routes/{movimientos,cajas,cheques}.py`, `schemas/movimiento.py`, `ChequesPendientesBlock.tsx`, `ChequesPage.tsx`, `MovimientoTable.tsx`, `RegistroCajaPage.tsx`).

## Hallazgos sobre el código existente

| Hallazgo | Consecuencia para esta feature |
|---|---|
| `MovimientoService.liquidar_cheque` ya rechaza liquidar antes de `fecha_liquidacion` (`ChequeAunNoLiquidableError` → 409) y `ChequesPendientesBlock` / `ChequesPage` ya deshabilitan **Liquidar** hasta esa fecha (`llegoFechaLiquidacion`). | FR-003 **ya está implementado**: solo se agregan tests de regresión. El endose NO reutiliza esa validación (puede ocurrir en cualquier momento). |
| La liquidación toma lock de `caja` → fila del cheque → filas del stream y recalcula el stream (`recalculate_subtotals`). | El endose sigue el mismo orden de locks, extendido a dos cajas (ver §3). |
| `MovimientoResponse.editable` hoy es `true` para toda secretaria (`is_editable`). | Debe pasar a `false` para cheques endosados y movimientos de endose (FR-019). |
| Cajas seleccionables ya disponibles vía `GET /api/v1/cajas/operativas` (solo `estado = 'activa'`). | El frontend reutiliza el endpoint; el servidor igualmente valida destino activo (no se confía en el cliente). |
| Ya existe un patrón de diálogo (`.complementario-dialog*` en `index.css`). | La ventana de endose reutiliza ese patrón visual/estructural, sin dependencias nuevas. |

---

## 1. Modelo: ¿tabla `endose` o columnas en `movimiento`?

### Decision
Extender `movimiento` con **dos columnas nullable**:

| Columna | Tipo | Aplica a | Significado |
|---|---|---|---|
| `endosado_a_caja_id` | `SMALLINT NULL FK caja.id` | el **cheque** | Caja destino del endose. `NOT NULL` ⇒ cheque endosado. |
| `endose_cheque_id` | `BIGINT NULL FK movimiento.id` (UNIQUE parcial) | el **movimiento destino** | Cheque que originó el movimiento. `NOT NULL` ⇒ movimiento de endose. |

Dos `CHECK`s mantienen la coherencia (ver data-model). El estado del cheque sigue siendo `pendiente | liquidado`; "Endosado" es un atributo derivado (`endosado_a_caja_id IS NOT NULL`), no un tercer estado.

### Rationale
- Coherente con la decisión de la feature 010 (extender `movimiento`, no tabla aparte): el cheque endosado y el movimiento destino **son** movimientos del stream (caja, moneda) y deben ordenarse, saldarse y listarse con el código existente.
- El vínculo bidireccional permite mostrar origen/destino en ambas listas sin joins complejos.
- Reutiliza `updated_by/updated_at` (cheque) y `created_by/created_at` (movimiento destino) como auditoría (FR-017).
- Mantener `estado = liquidado` evita tocar `estado_cheque`, `cheque_pendiente_expr`, `impacta_saldo_expr`, saldo, informes y proyección: un endosado ya queda **fuera** de todos los listados/proyecciones de pendientes (FR-014, FR-015) sin cambios.

### Alternatives considered
- **Tabla `endose`** (cheque_id, movimiento_destino_id, caja_origen, caja_destino, usuario, fecha): más limpia para auditoría pero agrega un join en cada listado y una tabla más para lo que son dos referencias. Descartado por costo/beneficio (≤ 10 usuarios).
- **Nuevo estado `endosado` en el cheque**: obligaría a revisar `impacta_saldo_expr`, el `CHECK ck_movimiento_subtotal_estado`, informes y saldos. Descartado.
- **Solo columna en el destino** (derivar el cheque endosado por consulta inversa): ahorra una columna pero obliga a subconsultas en cada fila de listado. Descartado.

---

## 2. Movimiento destino: movimiento común

### Decision
Se crea con `instrumento = 'ninguno'`, misma `moneda` y `monto` que el cheque, `tipo` inverso, `fecha_override = NULL` (fecha efectiva = momento del endose) y descripción generada en el servidor:

`Endose cheque: <descripcion del cheque> (Caja <nombre origen>)`, truncada a 500 caracteres.

### Rationale
- Impacta el subtotal de inmediato por el camino existente (Principio I, FR-009).
- La descripción se genera en el servidor: no hay campo libre del cliente que validar ni sanear (Seguridad por Diseño); el cliente solo envía `caja_destino_id`.

### Alternatives considered
- **Destino como cheque pendiente/liquidado**: contradice FR-008/FR-009 (impacto inmediato) y duplicaría el ciclo de vida. Descartado.
- **Descripción editable en la ventana** (respuesta C de la clarificación 2): descartada por el usuario (eligió A).

---

## 3. Atomicidad, concurrencia y orden de locks

### Decision
`MovimientoService.endosar_cheque` corre íntegro en la transacción del request (como `liquidar_cheque`):

1. Lock de las **dos cajas en orden ascendente de `id`** (`FOR NO KEY UPDATE`) → evita deadlock entre endoses cruzados A→B y B→A.
2. Lock de la fila del cheque (`FOR UPDATE`); `404` si no existe / no es cheque de esa caja; `409` si ya está liquidado o endosado (un solo error de dominio, `ChequeYaLiquidadoError`, cubre ambos: un endosado siempre tiene `fecha_liquidado`).
3. Marca el cheque: `fecha_liquidado = now`, `subtotal` provisional, `endosado_a_caja_id`, `updated_*`.
4. Inserta el movimiento destino con `endose_cheque_id`.
5. Reproduce el stream (caja, moneda) de **origen** y de **destino**.
6. El router hace `commit`; ante cualquier excepción hace `rollback` ⇒ cheque pendiente y ningún movimiento (FR-011).

La doble pulsación o dos pantallas simultáneas: el segundo request encuentra el cheque ya liquidado → `409` sin duplicar (FR-012, SC-005). Un índice único parcial sobre `endose_cheque_id` es la red de seguridad a nivel base de datos.

### Rationale
Misma estrategia ya probada en la feature 010 (lock de caja + fila + stream), ampliada con un orden determinístico para dos cajas.

### Alternatives considered
- **Dos requests (liquidar + crear movimiento) orquestados por el frontend**: no es atómico; viola FR-011. Descartado.
- **Sin lock de caja destino**: dos endoses concurrentes hacia la misma caja podrían interleavear el recálculo del stream. Descartado.

---

## 4. Bloqueo de edición/eliminación (FR-019)

### Decision
- `MovimientoService.update_movimiento` y `delete_movimiento` rechazan con `MovimientoEndosadoError` cuando `endosado_a_caja_id IS NOT NULL` **o** `endose_cheque_id IS NOT NULL` → los routers responden `409` con mensaje genérico ("Un endose no se puede modificar").
- `MovimientoResponse.editable` = `false` en esos casos para que la UI oculte **Editar/Eliminar**. El servidor es la autoridad; la UI es solo reflejo.

### Rationale
Impide que una edición/eliminación en una caja deje desalineada a la otra (neto ≠ 0). Es coherente con "sin deshacer" (Assumptions).

### Alternatives considered
- Cascada de eliminación a ambos registros: descartada por el usuario (respuesta A de la clarificación 3).

---

## 5. Contrato de API

### Decision
Un único endpoint nuevo, aditivo:

`POST /api/v1/cajas/{caja_id}/movimientos/{movimiento_id}/endosar` — rol `secretaria`.  
Request `{ "caja_destino_id": int }` (`extra="forbid"`). Response `200` `EndoseResponse { cheque, movimiento_destino }`.

| Código | Caso |
|---|---|
| 401 / 403 | Sin token / rol Escribano |
| 404 | Caja origen, cheque (otra caja o no cheque) o caja destino inexistentes |
| 409 | Cheque ya liquidado o endosado |
| 422 | Payload inválido, destino == origen o destino archivada |
| 500 | Error genérico (rollback) |

`MovimientoResponse` se amplía (aditivo): `endosable`, `endosado_a` (caja destino, en el cheque) y `endose_origen` (caja y cheque origen, en el movimiento destino).

### Rationale
Sigue el patrón `POST .../liquidar` de 010. Devolver ambos registros evita un segundo round-trip y permite refrescar las dos cajas.

---

## 6. Frontend

### Decision
- Nuevo componente `EndoseDialog` (diálogo modal accesible: `role="dialog"`, `aria-modal`, foco inicial, cierre con Esc / Cancelar) con la **lista de cajas desplegadas** como grupo de opciones (radio), excluyendo la caja origen; botón **Confirmar** deshabilitado sin selección.
- Botón **Endose** (siempre habilitado mientras `endosable`) junto a **Liquidar** en `ChequesPendientesBlock` y `ChequesPage` (ambos listados). Tras éxito se refrescan listados, Valor de caja, historial y Saldo a futuro.
- `MovimientoTable`: marca **Endosado → <caja>** en el cheque liquidado y **Endose desde <caja>** en el movimiento destino; sin botones Editar/Eliminar cuando `editable = false`.
- Cajas de la ventana: `fetchCajas()` (ya existente, apunta a las operativas). Con ≤ 15 cajas + configurables no se requiere búsqueda ni paginación (diferido de la clarificación).

### Rationale
Reutiliza patrones de diálogo y acciones de tabla existentes; sin dependencias nuevas.

### Alternatives considered
- `<select>` desplegable en lugar de lista: el pedido dice "cajas desplegadas donde permite seleccionar una"; una lista de opciones visible cumple ambas lecturas y es más rápida de operar. Se puede ajustar en la verificación con el usuario.

---

## 7. Fuera de alcance / sin cambios

- Informe PDF: el cheque endosado figura como movimiento liquidado (indicación Cheque/Echeque ya existente) y el movimiento destino como movimiento común con su descripción de endose; no se agregan secciones nuevas. Saldo a futuro, `/cheques`, `cheques-pendientes` y `saldo-proyectado` quedan correctos sin cambios porque el endosado ya no es pendiente.
- Sin dependencias nuevas, sin scheduler, sin cambios de infraestructura (Principio VI).
