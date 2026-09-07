# Data Model: Selección de Moneda en Registro de Cajas

**Feature**: `008-caja-monedas`  
**Storage**: PostgreSQL 16 (extiende `movimiento` de 001)

## Entity Relationship Overview

```text
┌─────────────┐       ┌─────────────┐       ┌──────────────────┐
│   usuario   │       │    caja     │       │    movimiento    │
├─────────────┤       ├─────────────┤       ├──────────────────┤
│ id (PK)     │       │ id (PK)     │◄──────│ caja_id (FK)     │
│ ...         │       │ ...         │       │ id (PK)          │
└─────────────┘       └─────────────┘       │ descripcion      │
                                            │ monto            │
                                            │ tipo             │
                                            │ moneda           │  ← NEW
                                            │ subtotal         │  (por caja+moneda)
                                            │ created_at       │
                                            │ created_by       │
                                            │ updated_at/by    │
                                            └──────────────────┘
```

No hay entidad “par”: el complementario USD es un segundo `movimiento` independiente.

## Tables

### `movimiento` (delta)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `moneda` | `VARCHAR(3)` | NOT NULL, DEFAULT `'ARS'`, CHECK IN (`'ARS'`,`USD`) | FR-002, FR-004, FR-015 |

Resto de columnas: sin cambio respecto a 001/003.

**Indexes:**
- Reemplazar o complementar `idx_movimiento_caja_created` con  
  `idx_movimiento_caja_moneda_created` ON (`caja_id`, `moneda`, `created_at` DESC, `id` DESC)
- Índice de recálculo: (`caja_id`, `moneda`, `created_at` ASC, `id` ASC) o el mismo índice en orden inverso según planner

**Migration:** Alembic `008_movimiento_moneda.py`: ADD COLUMN + CHECK + backfill DEFAULT (filas existentes = ARS). No recalcular subtotales históricos.

## Validation Rules

| Rule | Source |
|------|--------|
| `moneda` ∈ {ARS, USD} | FR-002, FR-023 |
| Default de alta ARS si el cliente omite el campo | FR-003 |
| `registrar_complementario` solo si `moneda = USD` | FR-010, FR-008 |
| Par USD: mismo `caja_id`, `descripcion`, `monto`, `moneda`; `tipo` opuesto | FR-008 |
| Persistencia del par en una transacción | FR-008a |
| `monto` > 0, descripción no vacía, **antes** del par | FR-011 |
| Subtotal stream = anterior ± monto **de esa moneda** | FR-012 |
| Primer movimiento de un stream: previous = 0 | Edge case |
| Recálculo edit/delete: solo `(caja_id, moneda)` | FR-014 |
| Cambio de moneda en PATCH: recálculo de stream origen y destino | FR-014 |
| Filtro fecha: fecha de `created_at` en America/Argentina/Buenos_Aires | Clarificación |
| List filters AND | FR-019 |

## Subtotal Calculation Algorithm (create)

```text
1. BEGIN TRANSACTION
2. Validate descripcion, monto, tipo, moneda
3. IF registrar_complementario AND moneda != USD → 400
4. previous = último movimiento de (caja_id, moneda) ORDER BY created_at DESC, id DESC FOR UPDATE
   OR 0
5. INSERT movimiento accionado (subtotal = previous ± monto)
6. IF registrar_complementario:
     previous2 = subtotal del insertado
     INSERT complementario tipo opuesto, mismos campos, subtotal = previous2 ∓ monto
7. COMMIT  — si 5 o 6 fallan, ROLLBACK (nada persistido)
```

Orden del par: primero el tipo del botón, después el opuesto.

## Subtotal Recalculation Algorithm (edit / delete)

```text
1. BEGIN TRANSACTION
2. Validate 24h + rol secretaria
3. currencies_to_recalc = {moneda_actual}
4. IF PATCH cambia moneda → currencies_to_recalc += {moneda_nueva}
5. APPLY update or delete
6. FOR EACH moneda IN currencies_to_recalc:
     previous = 0
     FOR EACH movimiento OF (caja_id, moneda) ORDER BY created_at ASC, id ASC FOR UPDATE:
       subtotal = previous ± monto
       UPDATE subtotal
       previous = subtotal
7. COMMIT
```

Borrar uno del par **no** borra el otro.

## Saldos

```text
saldo_ars = último subtotal WHERE caja_id AND moneda='ARS' OR 0.00
saldo_usd = último subtotal WHERE caja_id AND moneda='USD' OR 0.00
```

Independientes del filtro de listado.

`saldo-general`: suma de `saldo_ars` de cajas activas y suma de `saldo_usd` por separado. **Nunca** `saldo_ars + saldo_usd`.

## API Projection (read models)

### `MovimientoResponse`

```json
{
  "id": 42,
  "descripcion": "Pago cliente",
  "monto": "5000.00",
  "moneda": "USD",
  "tipo": "entrada",
  "subtotal": "5000.00",
  "fecha": "2026-09-07T14:30:00-03:00",
  "editable": true,
  "caja": { "id": 1, "nombre": "Bambina", "slug": "bambina", "estado": "activa" }
}
```

`subtotal` es el acumulado **de esa moneda** en esa caja.

### `MovimientoCreateResponse`

```json
{
  "movimiento": { "...MovimientoResponse..." },
  "complementario": { "...MovimientoResponse..." }
}
```

`complementario` es `null` cuando `registrar_complementario` es false.

### `CajaSaldoResponse`

```json
{
  "caja": { "id": 1, "nombre": "Bambina", "slug": "bambina", "estado": "activa" },
  "saldo_ars": "12500.00",
  "saldo_usd": "100.00",
  "ultimo_movimiento_at": "2026-09-07T14:30:00-03:00"
}
```

`ultimo_movimiento_at`: `created_at` del movimiento más reciente de la caja (cualquier moneda), solo informativo.

### `CajaSaldoGeneralResponse`

```json
{
  "subtotal_general_ars": "50000.00",
  "subtotal_general_usd": "200.00",
  "cajas_incluidas": 15,
  "cajas": [
    {
      "caja": { "id": 1, "nombre": "Bambina", "slug": "bambina", "estado": "activa" },
      "saldo_ars": "12500.00",
      "saldo_usd": "0.00"
    }
  ]
}
```

**Breaking change:** desaparecen `saldo_actual` y `subtotal_general` mezclados.

## Concurrency

- Alta/edición: `FOR UPDATE` en el stream `(caja_id, moneda)`.
- Par USD: un solo commit.
- Cajas adicionales: una transacción por caja (igual que hoy).
