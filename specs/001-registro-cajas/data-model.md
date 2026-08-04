# Data Model: Registro de Cajas para Escribanía

**Feature**: `001-registro-cajas`  
**Storage**: PostgreSQL 16

## Entity Relationship Overview

```text
┌─────────────┐       ┌─────────────┐       ┌──────────────────┐
│   usuario   │       │    caja     │       │    movimiento    │
├─────────────┤       ├─────────────┤       ├──────────────────┤
│ id (PK)     │       │ id (PK)     │◄──────│ caja_id (FK)     │
│ username    │       │ nombre      │       │ id (PK)          │
│ password_hash│      │ slug        │       │ descripcion      │
│ rol         │       │ created_at  │       │ monto            │
│ created_at  │       └─────────────┘       │ tipo             │
│ updated_at  │              ▲              │ subtotal         │
└─────────────┘              │              │ created_at       │
       │                     │              │ created_by (FK)  │
       └─────────────────────┴──────────────┤ updated_at       │
                                            │ updated_by (FK)  │
                                            └──────────────────┘
```

## Tables

### `caja`

Catálogo fijo de 15 cajas (sembrado por migración).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `SMALLSERIAL` | PK | |
| `nombre` | `VARCHAR(100)` | NOT NULL, UNIQUE | Nombre visible (ej. "Maria Teresa") |
| `slug` | `VARCHAR(100)` | NOT NULL, UNIQUE | Identificador URL-safe |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | |

**Seed data**: 15 filas según catálogo constitucional (Bambina … Fideicomiso).

### `usuario`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `SERIAL` | PK | |
| `username` | `VARCHAR(50)` | NOT NULL, UNIQUE | |
| `password_hash` | `VARCHAR(255)` | NOT NULL | bcrypt |
| `rol` | `VARCHAR(20)` | NOT NULL, CHECK IN ('secretaria','escribano') | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | |

**Seed (dev)**: `admin` / bcrypt(`admin`) / rol `secretaria`.

### `movimiento`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `BIGSERIAL` | PK | |
| `caja_id` | `SMALLINT` | NOT NULL, FK → caja.id | |
| `descripcion` | `VARCHAR(500)` | NOT NULL | Texto libre |
| `monto` | `NUMERIC(15,2)` | NOT NULL, CHECK > 0 | Siempre positivo; signo por `tipo` |
| `tipo` | `VARCHAR(10)` | NOT NULL, CHECK IN ('entrada','salida') | |
| `subtotal` | `NUMERIC(15,2)` | NOT NULL | Acumulado tras este movimiento |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Fecha del movimiento (FR-009) |
| `created_by` | `INTEGER` | NOT NULL, FK → usuario.id | Auditoría (FR-013) |
| `updated_at` | `TIMESTAMPTZ` | NULL | Set on edit |
| `updated_by` | `INTEGER` | NULL, FK → usuario.id | Usuario que editó |

**Business rules**:
- `editable` = `created_at` >= now() - interval '24 hours' (computed, not stored)
- Solo rol `secretaria` puede UPDATE/DELETE

**Indexes**:
- `idx_movimiento_caja_created` ON (`caja_id`, `created_at` DESC, `id` DESC) — paginación
- `idx_movimiento_caja_id` ON (`caja_id`, `id`) — recálculo secuencial

## Validation Rules

| Rule | Source |
|------|--------|
| `monto` > 0 | Edge case spec |
| `descripcion` no vacía (trim) | FR-007 |
| `tipo` ∈ {entrada, salida} | FR-008 |
| Subtotal = subtotal_anterior ± monto | FR-010 |
| Subtotal puede ser negativo | Clarificación spec |
| Primer movimiento: subtotal_anterior = 0 | Edge case spec |
| Solo `secretaria` inserta movimientos | FR-016, FR-021 |
| Solo `secretaria` edita/elimina movimientos < 24h | FR-013a–FR-013e |
| Rechazar edit/delete si `created_at` > 24h ago | FR-013d |

## Subtotal Calculation Algorithm (create)

```text
1. BEGIN TRANSACTION
2. SELECT último movimiento de caja_id ORDER BY created_at DESC, id DESC FOR UPDATE
3. previous = último.subtotal OR 0 si no hay filas
4. IF tipo = 'entrada' THEN subtotal = previous + monto
   ELSE subtotal = previous - monto
5. INSERT movimiento con subtotal calculado
6. COMMIT
```

## Subtotal Recalculation Algorithm (edit / delete)

```text
1. BEGIN TRANSACTION
2. Validate movimiento.created_at >= now() - 24h AND user.rol = secretaria
3. IF DELETE → remove row; ELSE UPDATE fields and set updated_at/updated_by
4. SELECT all movimientos of caja_id ORDER BY created_at ASC, id ASC FOR UPDATE
5. previous = 0
6. FOR EACH movimiento IN order:
     subtotal = previous + monto (entrada) OR previous - monto (salida)
     UPDATE movimiento SET subtotal = computed
     previous = subtotal
7. COMMIT
```

## API Projection (read models)

### `MovimientoResponse`

```json
{
  "id": 42,
  "descripcion": "Pago cliente",
  "monto": "5000.00",
  "tipo": "entrada",
  "subtotal": "12500.00",
  "fecha": "2026-08-03T14:30:00-03:00",
  "editable": true,
  "caja": { "id": 1, "nombre": "Bambina" }
}
```

`editable`: `true` si el movimiento tiene menos de 24 horas y el usuario es secretaria.

### `CajaSaldoResponse`

```json
{
  "caja": { "id": 1, "nombre": "Bambina" },
  "saldo_actual": "12500.00",
  "ultimo_movimiento_at": "2026-08-03T14:30:00-03:00"
}
```

### `PaginatedMovimientos`

```json
{
  "items": [ "...MovimientoResponse..." ],
  "page": 1,
  "page_size": 20,
  "total_items": 87,
  "total_pages": 5
}
```

## State Transitions

| Estado | Condición | Transiciones permitidas (secretaria) |
|--------|-----------|--------------------------------------|
| Editable | `created_at` dentro de 24h | UPDATE, DELETE |
| Inmutable | `created_at` > 24h | ninguna |
| Eliminado | DELETE ejecutado | fila removida; subtotales recalculados |

Escribano: solo lectura en todos los estados.

## Volume Assumptions

- Usuarios concurrentes: ≤ 10
- Movimientos por caja/año: ≤ 5 000
- Total movimientos: < 100 000 en 5 años
