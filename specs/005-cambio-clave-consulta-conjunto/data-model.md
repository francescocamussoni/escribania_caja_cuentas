# Data Model: Cambio de Contraseña y Consulta Conjunta de Cajas

**Feature**: `005-cambio-clave-consulta-conjunto`  
**Storage**: PostgreSQL 16 — una columna nueva en `usuario`; consulta reutiliza `caja` y `movimiento`.

## Entity Relationship Overview

```text
┌──────────────────────────┐
│         usuario          │
├──────────────────────────┤
│ id (PK)                  │
│ username UNIQUE          │
│ password_hash            │
│ rol                      │
│ password_changed_at      │  ← NUEVO (nullable timestamptz)
│ created_at / updated_at  │
└──────────────────────────┘

┌─────────────┐       ┌─────────────┐
│    caja     │◄──────│  movimiento │
├─────────────┤       ├─────────────┤
│ id, nombre  │       │ caja_id     │
│ slug        │       │ subtotal    │  ← valor actual = último subtotal
└─────────────┘       │ created_at  │
                      └─────────────┘

JWT (no persistido): sub, rol, exp, iat
```

## Migración

**Alembic** `005_usuario_password_changed_at.py`:

```text
ALTER TABLE usuario
  ADD COLUMN password_changed_at TIMESTAMPTZ NULL;
```

- Default `NULL`: usuarios existentes (incluido bootstrap) no invalidan tokens hasta el primer cambio de clave.
- No backfill.

## `usuario` (campos relevantes)

| Campo | Tipo | Reglas |
|-------|------|--------|
| `username` | varchar(50) unique | Sujeto del JWT `sub`; requerido en cambio público |
| `password_hash` | varchar(255) | bcrypt; se reemplaza en cambio exitoso |
| `rol` | secretaria \| escribano | Ambos roles pueden cambiar su clave |
| `password_changed_at` | timestamptz null | Set a `now()` UTC en cada cambio exitoso |
| `updated_at` | timestamptz | `onupdate` existente |

### Transición de clave

1. Validar body (largo ≥ 8, confirmación igual).
2. Verificar `current_password` contra `password_hash`.
3. Rechazar si `new_password == current_password`.
4. `password_hash = hash_password(new_password)`.
5. `password_changed_at = now(UTC)`.
6. Commit. Tokens con `iat` anterior a `password_changed_at` → 401.

## JWT

| Claim | Uso |
|-------|-----|
| `sub` | username |
| `rol` | secretaria \| escribano |
| `exp` | 8 h (existente) |
| `iat` | **nuevo** — instante de emisión UTC |

`get_current_user`: si `user.password_changed_at` está definido y (`iat` ausente o `iat < password_changed_at`) → 401 `No autenticado o token expirado`.

## DTOs (no tablas)

### `ChangePasswordPublicRequest`

| Campo | Validación |
|-------|------------|
| `username` | 1–50, extra forbid |
| `current_password` | min 1 |
| `new_password` | min 8 |
| `new_password_confirm` | igual a `new_password` |

### `ChangePasswordAuthenticatedRequest`

Igual sin `username`. El sujeto es `current_user` (nunca un id en el body).

### Consulta conjunta (estado de UI, no persistido)

| Campo | Significado |
|-------|-------------|
| `principalCajaId` | Desplegable |
| `adicionalesIds` | Subconjunto del catálogo excepto principal |
| `consultaIds` | `[principal] + adicionales` ordenados: principal, luego catálogo (`caja.id`) |
| `saldosPorCaja` | Resultado de N `GET saldo` (todo o nada) |
| `valorEnConjunto` | Suma de `saldosPorCaja[].saldo_actual` (UI; no persistido) |
| `historialPorCaja` | Lazy al expandir; página independiente |

## Validation summary

| Regla | Dónde |
|-------|--------|
| extra fields forbidden | Pydantic `extra="forbid"` |
| Nueva ≠ actual | Servicio, tras verificar actual |
| Confirmación | Schema |
| Solo propia clave | Público: username + actual; autenticado: JWT subject |
| Subtotales por caja | Backend existente; UI no recalcula movimientos |
| Valor en conjunto | UI: suma de `saldo_actual` del intento (FR-018a) |
| Fail-all conjunto | Cliente: cualquier fallo de saldo aborta el intento |

## Indexes

Ningún índice nuevo: lookup por `username` (unique) y `id` de caja ya cubiertos.
