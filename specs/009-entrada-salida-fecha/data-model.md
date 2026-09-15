# Data Model: 009-entrada-salida-fecha

**Date**: 2026-09-14  
**Branch**: `009-entrada-salida-fecha`

---

## Entidades modificadas

### `Movimiento` (tabla `movimiento`)

#### Campo nuevo: `fecha_override`

| Atributo | Valor |
|---|---|
| Columna | `fecha_override` |
| Tipo SQL | `TIMESTAMPTZ` |
| Nullable | `YES` |
| Default | `NULL` |
| Propósito | Fecha explícita del movimiento cuando la secretaria elige una fecha distinta a la actual. Si `NULL`, la fecha de visualización y ordenamiento es `created_at`. |

**Regla de negocio**: `fecha_display = COALESCE(fecha_override, created_at)`

#### Impacto en columnas existentes

| Columna | Estado | Notas |
|---|---|---|
| `created_at` | Sin cambio | Sigue siendo la marca de auditoría del INSERT (inmutable) |
| `fecha_override` | **NUEVA** | Fecha de negocio cuando difiere de `created_at` |

#### Impacto en índices existentes

| Índice | Acción | Nuevo valor |
|---|---|---|
| `idx_movimiento_caja_moneda_created` | **REEMPLAZAR** | `(caja_id, moneda, COALESCE(fecha_override, created_at) DESC, id DESC)` |

---

## Schema de API — cambios

### `CreateMovimientoRequest` (backend)

| Campo | Tipo | Requerido | Cambio |
|---|---|---|---|
| `descripcion` | `str` | Sí | Sin cambio |
| `monto` | `str` | Sí | Sin cambio |
| `tipo` | `"entrada" \| "salida"` | Sí | Sin cambio |
| `moneda` | `"ARS" \| "USD"` | No (default `"ARS"`) | Sin cambio |
| `registrar_complementario` | `bool` | No (default `false`) | **Validación modificada**: se elimina restricción USD-only |
| `fecha_manual` | `str` (formato `YYYY-MM-DD`) | **No (nuevo, opcional)** | Nuevo campo |

**Validación `fecha_manual`**:
- Formato: `YYYY-MM-DD` (regex `^\d{4}-\d{2}-\d{2}$`)
- Rango: sin restricción de fechas mínimas/máximas
- Transformación en backend: `datetime(año, mes, día, 9, 0, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))`

**Validación eliminada**:
```
# ELIMINAR este model_validator:
validate_complementario_only_for_usd
```

### `MovimientoResponse` (backend)

| Campo | Tipo | Cambio |
|---|---|---|
| `fecha` | `datetime` | **Lógica modificada**: `fecha_override ?? created_at` |
| Resto | — | Sin cambio |

---

## `MovimientoService` — cambios de lógica

### `create_movimiento` — ordenamiento actualizado

```
# ANTES:
ORDER BY Movimiento.created_at.desc(), Movimiento.id.desc()

# DESPUÉS (pseudocódigo):
ORDER BY COALESCE(fecha_override, created_at) DESC, id DESC
```

### `create_movimiento_pair` — extensión a ARS

```
# ANTES: hardcodeaba moneda="USD"
# DESPUÉS: acepta parámetro moneda (ARS o USD)
```

### `recalculate_subtotals` — ordenamiento actualizado

```
# ANTES:
ORDER BY Movimiento.created_at.asc(), Movimiento.id.asc()

# DESPUÉS:
ORDER BY COALESCE(fecha_override, created_at) ASC, id ASC
```

---

## Frontend — tipos TypeScript (api.ts)

### `CreateMovimientoPayload` — campo nuevo

```typescript
export type CreateMovimientoPayload = {
  descripcion: string;
  monto: string;
  tipo: "entrada" | "salida";
  moneda?: "ARS" | "USD";
  registrar_complementario?: boolean;
  fecha_manual?: string;   // nuevo: "YYYY-MM-DD" | undefined
};
```

---

## Migration

**Número**: `009`  
**Archivo**: `backend/alembic/versions/009_movimiento_fecha_override.py`  
**Descripción**: Add `fecha_override` column and update composite index

```sql
-- upgrade
ALTER TABLE movimiento ADD COLUMN fecha_override TIMESTAMPTZ NULL;

DROP INDEX IF EXISTS idx_movimiento_caja_moneda_created;
CREATE INDEX idx_movimiento_caja_moneda_fecha 
  ON movimiento (caja_id, moneda, COALESCE(fecha_override, created_at) DESC, id DESC);

-- downgrade
DROP INDEX IF EXISTS idx_movimiento_caja_moneda_fecha;
CREATE INDEX idx_movimiento_caja_moneda_created
  ON movimiento (caja_id, moneda, created_at DESC, id DESC);
ALTER TABLE movimiento DROP COLUMN fecha_override;
```

---

## Estado del modelo después de esta feature

```
movimiento
├── id                 BIGINT PK
├── caja_id            SMALLINT FK→caja
├── descripcion        VARCHAR(500)
├── monto              NUMERIC(15,2)
├── tipo               VARCHAR(10)  CHECK IN ('entrada','salida')
├── moneda             VARCHAR(3)   CHECK IN ('ARS','USD')
├── subtotal           NUMERIC(15,2)
├── fecha_override     TIMESTAMPTZ  NULL  ← NUEVO
├── created_at         TIMESTAMPTZ  server_default=now()
├── created_by         INT FK→usuario
├── updated_at         TIMESTAMPTZ  NULL
└── updated_by         INT FK→usuario  NULL
```
