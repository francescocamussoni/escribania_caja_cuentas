# Data Model: 011-cheque-endose

**Date**: 2026-11-04  
**Branch**: `011-cheque-endose`  
**Migración**: `backend/alembic/versions/011_movimiento_endose.py` (down_revision `010_movimiento_cheque`)

---

## 1. Entidad modificada: `Movimiento` (tabla `movimiento`)

### 1.1 Columnas nuevas

| Columna | Tipo SQL | Null | Default | Descripción |
|---|---|---|---|---|
| `endosado_a_caja_id` | `SMALLINT` FK → `caja.id` | SÍ | `NULL` | Solo en el **cheque**: caja destino del endose. `NOT NULL` ⇒ cheque endosado. |
| `endose_cheque_id` | `BIGINT` FK → `movimiento.id` | SÍ | `NULL` | Solo en el **movimiento destino**: cheque que lo originó. `NOT NULL` ⇒ movimiento de endose. |

Las filas existentes quedan con ambas columnas en `NULL` (sin backfill).

### 1.2 Constraints (en migración **y** en el modelo, para que `create_all` de los tests los aplique)

| Nombre | Expresión |
|---|---|
| `ck_movimiento_endose_cheque` | `endosado_a_caja_id IS NULL OR (instrumento <> 'ninguno' AND fecha_liquidado IS NOT NULL)` |
| `ck_movimiento_endose_destino` | `endose_cheque_id IS NULL OR (instrumento = 'ninguno' AND endosado_a_caja_id IS NULL)` |

Los constraints de la feature 010 (`ck_movimiento_cheque_fechas`, `ck_movimiento_subtotal_estado`, …) no cambian: un cheque endosado cumple "liquidado ⇒ con subtotal".

No se expresa en `CHECK` que destino ≠ origen (requiere comparar con otra fila): lo valida el servicio.

### 1.3 Índices

| Índice | Definición | Propósito |
|---|---|---|
| `uq_movimiento_endose_cheque` | `UNIQUE (endose_cheque_id) WHERE endose_cheque_id IS NOT NULL` | Un cheque no puede originar más de un movimiento de endose (SC-005). Red de seguridad ante concurrencia. |

Índice parcial creado con `op.execute` (como en 009/010).

### 1.4 Propiedades derivadas (Python, no persistidas)

| Propiedad | Definición |
|---|---|
| `endosado` | `endosado_a_caja_id is not None` |
| `es_endose_destino` | `endose_cheque_id is not None` |
| `bloqueado_por_endose` | `endosado or es_endose_destino` (no editable ni eliminable) |
| `endosable` | `estado_cheque == 'pendiente'` (el rol se aplica al serializar) |

### 1.5 Relaciones ORM (solo lectura para respuestas)

| Relación | Destino | Carga |
|---|---|---|
| `endosado_a_caja` | `Caja` | `selectin` |
| `endose_cheque` | `Movimiento` (cheque origen, con su `caja`) | `selectin` |

### 1.6 Reglas de negocio

| # | Regla | Origen |
|---|---|---|
| E1 | Solo un cheque **pendiente** puede endosarse, en cualquier fecha (no depende de `fecha_liquidacion`). | FR-001, FR-002 |
| E2 | Destino: caja existente, `estado = 'activa'`, distinta de la caja del cheque. | FR-006, FR-017 |
| E3 | Efecto atómico: cheque → `fecha_liquidado = now`, impacto en su caja (entrada suma / salida resta); destino → movimiento común con `tipo` inverso, misma `moneda` y `monto`. Neto entre ambas cajas = 0. | FR-008, FR-009 |
| E4 | Descripción del destino: `Endose cheque: <descripcion> (Caja <origen>)` truncada a 500; la fija el servidor. | FR-010 |
| E5 | Un cheque endosado y su movimiento destino no se editan ni eliminan (409). | FR-019 |
| E6 | Un cheque no puede endosarse dos veces ni liquidarse tras endosarse (409). | FR-012 |
| E7 | Liquidar (botón) no cambia: no crea movimientos en otras cajas; sigue exigiendo fecha de liquidación llegada. | FR-003, FR-013 |
| E8 | Solo rol Secretaria; se audita en `updated_by` (cheque) y `created_by` (destino) + evento `cheque_endorsed`. | FR-016, FR-017 |

### 1.7 Estados del cheque (actualizado)

```
                 crear
                   │
                   ▼
            ┌─────────────┐
            │  PENDIENTE  │
            └──┬───────┬──┘
   Liquidar    │       │  Endose (cualquier fecha)
 (fecha llegó) │       │  + movimiento inverso en caja destino
               ▼       ▼
        ┌──────────┐ ┌───────────────────────┐
        │LIQUIDADO │ │ LIQUIDADO + ENDOSADO  │  ← final: sin editar/eliminar
        └──────────┘ └───────────────────────┘
```

---

## 2. Vistas calculadas

No hay vistas nuevas. Efecto en las existentes:

| Vista | Efecto del endose |
|---|---|
| Saldo actual por (caja, moneda) | Origen: ± monto del cheque (ya liquidado). Destino: ∓ monto. Suma de ambos = 0. |
| Cheques pendientes / sección Cheques / Saldo a futuro / saldo proyectado | El cheque deja de ser pendiente ⇒ desaparece (sin cambios de código). |
| Informe de Caja | Ambos registros aparecen como movimientos que impactan el saldo; el cheque no figura en "Cheques pendientes". |

---

## 3. Schemas de API (resumen; contrato en `contracts/openapi-delta.yaml`)

### `EndosarChequeRequest`
| Campo | Tipo | Regla |
|---|---|---|
| `caja_destino_id` | `int` (≥ 1) | Obligatorio; `extra="forbid"`. |

### `MovimientoResponse` (+, aditivo)
| Campo | Tipo | Notas |
|---|---|---|
| `endosable` | `bool` | `true` si el cheque está pendiente **y** el usuario es secretaria. |
| `endosado_a` | `CajaResponse \| null` | Caja destino (solo en el cheque endosado). |
| `endose_origen` | `EndoseOrigen \| null` | `{ caja: CajaResponse, cheque_id: int }` (solo en el movimiento destino). |
| `editable` | `bool` | **Cambia**: `false` si `bloqueado_por_endose`. |

### `EndoseResponse`
- `cheque: MovimientoResponse` — liquidado, con `endosado_a`.
- `movimiento_destino: MovimientoResponse` — con `endose_origen`.

---

## 4. Impacto en código existente

| Módulo | Cambio |
|---|---|
| `models/movimiento.py` | +2 columnas, +2 `CheckConstraint`, +relaciones, +propiedades. |
| `services/movimiento_service.py` | +`endosar_cheque`, +`MovimientoEndosadoError`, `create_movimiento(..., endose_cheque_id=None)` interno, bloqueo en `update_movimiento`/`delete_movimiento`. |
| `schemas/movimiento.py` | `EndosarChequeRequest`, `EndoseResponse`, `EndoseOrigen`, campos nuevos en `MovimientoResponse`, `is_editable`. |
| `api/routes/movimientos.py` | `POST .../endosar`; manejo de `MovimientoEndosadoError` (409) en PATCH/DELETE. |
| Listados (`movimientos`, `cheques_service`, `cheques`) | Sin cambio de lógica; cargan relaciones nuevas (`selectin`). |

---

## 5. Datos existentes y migración

| Aspecto | Tratamiento |
|---|---|
| Filas existentes | Columnas nuevas `NULL`; sin cambios de comportamiento (FR-018). |
| Orden de aplicación | (1) agregar columnas + FKs, (2) `CHECK`s, (3) índice único parcial. |
| `downgrade` | Aborta con mensaje claro si existen endoses (`endosado_a_caja_id` o `endose_cheque_id` no nulos); si no, elimina índice, `CHECK`s y columnas. |
| Verificación | `alembic upgrade head` → `downgrade -1` → `upgrade head` sin errores sobre una base con datos de 010. |
