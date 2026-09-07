# Research: Selección de Moneda en Registro de Cajas

**Feature**: `008-caja-monedas`  
**Date**: 2026-09-07

## R1 — Persistencia de moneda

**Decision:** Columna `movimiento.moneda` `CHAR(3)` / `VARCHAR(3)` NOT NULL, CHECK `IN ('ARS','USD')`, DEFAULT `'ARS'`. Migración Alembic `008_movimiento_moneda.py`. Filas existentes quedan ARS sin recálculo (el stream histórico ya era implícitamente ARS).

**Rationale:** Un campo en la misma tabla mantiene paginación, edición 24h y auditoría. El DEFAULT cubre FR-015.

**Alternatives considered:**
- Tabla `movimiento_usd` separada — duplica servicios, paginación y RBAC.
- Moneda a nivel caja — contradice “elegir moneda por movimiento”.

## R2 — Subtotales por (caja, moneda)

**Decision:** `compute_subtotal` y `recalculate_subtotals` filtran por `caja_id` **y** `moneda`. Lock `FOR UPDATE` sobre esa partición. Índice `(caja_id, moneda, created_at DESC, id DESC)`.

**Rationale:** FR-012 / SC-006: no mezclar ARS y USD. El algoritmo 001 se reutiliza por stream.

**Alternatives considered:**
- Un solo acumulado con conversión — fuera de spec (sin tipo de cambio).
- Recalcular toda la caja ignorando moneda — viola integridad.

## R3 — Alta del par USD (todo o nada)

**Decision:** Un solo `POST /api/v1/cajas/{id}/movimientos` con `moneda` y `registrar_complementario` (boolean, default `false`). Si `true`, el servicio inserta tipo accionado y tipo opuesto en la **misma transacción**; rollback si cualquiera falla. Respuesta 201: `{ movimiento, complementario }` (`complementario` null si no hubo par). `registrar_complementario: true` con `moneda: ARS` → 400.

**Rationale:** FR-008a exige atomicidad; dos POST del cliente no pueden garantizarla. El cartel es solo UI; el servidor es la fuente de verdad.

**Alternatives considered:**
- Endpoint `/movimientos/par` — más superficie, mismo efecto.
- Dos INSERT desde el frontend — no cumple todo-o-nada.

## R4 — Filtros de listado (fecha y moneda)

**Decision:** Query params en GET listado: `moneda` (`ARS`|`USD`, omitido = todas), `fecha_desde`, `fecha_hasta` (`YYYY-MM-DD`). Fechas interpretadas en `America/Argentina/Buenos_Aires` (reutilizar `app.core.dates` / el mismo `timezone` que informes). Rango inclusive; un extremo omitido = abierto. Paginación 20 sobre el conjunto **filtrado**.

**Rationale:** Alineado a clarificación de rango y a informes existentes. Evita ambigüedad UTC vs hora Argentina.

**Alternatives considered:**
- Filtro solo en frontend — incorrecto con paginación server-side.
- `timestamptz` crudo en query — peor UX y errores de zona.

## R5 — Valor de caja y saldo-general

**Decision:** `CajaSaldoResponse` expone `saldo_ars` y `saldo_usd` (último subtotal de cada stream, o `0.00`). No se envía un `saldo_actual` mezclado. `GET /cajas/saldo-general` deja de sumar un único `subtotal_general`; pasa a `subtotal_general_ars` y `subtotal_general_usd`, y cada ítem de caja con ambos saldos.

**Rationale:** Clarificación: el encabezado no sigue al filtro. Consulta conjunto (005/006) hoy suma el último subtotal de la caja; con USD eso mezclaría monedas (Principio I).

**Alternatives considered:**
- Mantener `saldo_actual` como “último movimiento de cualquier moneda” — incorrecto.
- Deprecar conjunto en esta feature — dejaría un bug financiero a la vista.

## R6 — Cajas adicionales y edición

**Decision:** Cajas adicionales siguen siendo N POSTs independientes (comportamiento actual). Cada POST aplica moneda/par atómico **por caja**. Editar/borrar un renglón del par no toca al otro; recálculo solo del stream `(caja, moneda)` afectado. Si el PATCH cambia `moneda`, recálculo de **ambos** streams de esa caja.

**Rationale:** Spec: el par son dos registros independientes tras un alta atómica. No hay transacción multi-caja hoy.

**Alternatives considered:**
- Borrar el par en cascada — no pedido.
- Transacción multi-caja para adicionales — cambio de alcance de otra feature.

## R7 — Informes / impresión

**Decision:** Alcance mínimo de integridad (no rediseño): montos de movimientos en PDF muestran código de moneda; `saldo_cierre` no usa el último movimiento de cualquier moneda. Informes emiten cierre ARS y USD por separado (o filtran por moneda si el informe es de un stream). Plazos fijos no cambian (siguen ARS).

**Rationale:** Spec deja el rediseño de impresión fuera, pero asume que un comprobante no oculte la moneda. Un saldo de cierre mezclado rompería Principio I.

**Alternatives considered:**
- No tocar informes — riesgo de PDF con totales mezclados.

## R8 — Testing

**Decision:** TDD (clarificación). pytest unit+integration en backend **antes** de cambiar `MovimientoService`; Vitest/RTL en formulario (selector, cartel USD, ARS sin cartel) y tabla/filtros.

**Rationale:** Spec Testing Strategy + constitución (subtotales y RBAC).

**Alternatives considered:** Hybrid / sin tests — rechazado por el usuario (opción A).

## R9 — Constitución “moneda única ARS”

**Decision:** Esta feature **enmienda de facto** el constraint constitucional de moneda única **solo para movimientos de caja**. El plan registra la violación justificada. Tras implementar, conviene `/spec-kitti.amend` o bump de constitución (MINOR: multi-moneda ARS/USD en caja).

**Rationale:** El spec es explícito; no se puede implementar USD sin esa excepción.

**Alternatives considered:** Rechazar USD — contradice la spec.
