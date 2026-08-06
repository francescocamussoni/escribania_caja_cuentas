# Data Model: Plazos Fijos por Caja

**Feature**: `003-plazos-fijos`  
**Storage**: PostgreSQL 16 (extensión de schema `001-registro-cajas`)

## Entity Relationship Overview

```text
┌─────────────┐       ┌─────────────┐       ┌──────────────────┐
│   usuario   │       │    caja     │       │    plazo_fijo    │
├─────────────┤       ├─────────────┤       ├──────────────────┤
│ id (PK)     │       │ id (PK)     │◄──────│ caja_id (FK)     │
│ username    │       │ nombre      │       │ id (PK)          │
│ ...         │       │ slug        │       │ monto_ingresado  │
└─────────────┘       └─────────────┘       │ monto_a_vencimiento│
       │                     ▲              │ fecha_vencimiento  │
       └─────────────────────┴──────────────│ created_at       │
                                            │ created_by (FK)  │
                                            └──────────────────┘
```

Relación: una `caja` tiene muchos `plazo_fijo`; cada `plazo_fijo` pertenece a una sola `caja`.

## Tables

### `plazo_fijo` (nueva)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `BIGSERIAL` | PK | |
| `caja_id` | `SMALLINT` | NOT NULL, FK → caja.id | Una caja por registro |
| `monto_ingresado` | `NUMERIC(15,2)` | NOT NULL, CHECK > 0 | ARS |
| `monto_a_vencimiento` | `NUMERIC(15,2)` | NOT NULL, CHECK > 0 | ARS |
| `fecha_vencimiento` | `DATE` | NOT NULL | Comparación “activo” vs calendario AR |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Auditoría |
| `created_by` | `INTEGER` | NOT NULL, FK → usuario.id | Usuario que registró |

**Table constraints**:

```sql
CHECK (monto_ingresado > 0)
CHECK (monto_a_vencimiento > 0)
CHECK (monto_a_vencimiento >= monto_ingresado)
```

**Indexes**:

- `idx_plazo_fijo_caja_vencimiento` ON (`caja_id`, `fecha_vencimiento`, `created_at` DESC, `id` DESC) — listado paginado
- `idx_plazo_fijo_caja_activos` ON (`caja_id`, `fecha_vencimiento`) WHERE `fecha_vencimiento >= CURRENT_DATE` — opcional para resumen (evaluar en implementación)

### Tablas reutilizadas (sin cambio de schema)

- `caja` — catálogo 15 cajas
- `usuario` — roles `secretaria` | `escribano`

## Validation Rules

| Rule | Source |
|------|--------|
| `monto_ingresado` > 0 | FR-017 |
| `monto_a_vencimiento` > 0 | FR-017 |
| `monto_a_vencimiento` ≥ `monto_ingresado` | FR-017, clarificación |
| `fecha_vencimiento` obligatoria | FR-018 |
| Fechas pasadas permitidas al crear/editar | Edge cases spec |
| Solo `secretaria` INSERT/UPDATE/DELETE | FR-003, FR-014 |
| Sin ventana 24h en edit/delete | FR-007, FR-008 |
| Escribano solo GET | FR-014, FR-015 |

## Activo vs vencido

**Definición**: Plazo **activo** (no vencido) si `fecha_vencimiento >= hoy` en zona `America/Argentina/Buenos_Aires`.

- Totales del panel de resumen (FR-009a): solo plazos activos.
- Listado: activos primero (orden vencimiento ascendente), vencidos al final (vencimiento descendente).

## Listado — orden (paginación)

```text
ORDER BY
  (fecha_vencimiento < hoy_AR) ASC,
  CASE WHEN fecha_vencimiento >= hoy_AR THEN fecha_vencimiento END ASC NULLS LAST,
  CASE WHEN fecha_vencimiento < hoy_AR THEN fecha_vencimiento END DESC NULLS LAST,
  created_at DESC,
  id DESC
LIMIT 20 OFFSET (page-1)*20
```

## Agregación — resumen activos

```sql
SELECT
  COALESCE(SUM(monto_ingresado), 0) AS total_monto_ingresado_activos,
  COALESCE(SUM(monto_a_vencimiento), 0) AS total_monto_a_vencimiento_activos
FROM plazo_fijo
WHERE caja_id = :caja_id
  AND fecha_vencimiento >= :hoy_ar
```

## API Projection (read models)

### `PlazoFijoResponse`

```json
{
  "id": 7,
  "monto_ingresado": "100000.00",
  "monto_a_vencimiento": "105000.00",
  "fecha_vencimiento": "2026-12-31",
  "vencido": false,
  "created_at": "2026-08-06T12:00:00-03:00",
  "caja": { "id": 1, "nombre": "Bambina", "slug": "bambina" }
}
```

`vencido`: calculado (`fecha_vencimiento < hoy_AR`) para posible estilo UI; no persistido.

### `PlazosFijosResumenResponse`

```json
{
  "caja": { "id": 1, "nombre": "Bambina", "slug": "bambina" },
  "total_monto_ingresado_activos": "250000.00",
  "total_monto_a_vencimiento_activos": "262500.00"
}
```

### `PaginatedPlazosFijos`

```json
{
  "items": [ "...PlazoFijoResponse..." ],
  "page": 1,
  "page_size": 20,
  "total_items": 45,
  "total_pages": 3
}
```

## State Transitions

| Estado | Condición | Transiciones (secretaria) |
|--------|-----------|---------------------------|
| Activo | `fecha_vencimiento >= hoy_AR` | UPDATE, DELETE; cuenta en resumen |
| Vencido | `fecha_vencimiento < hoy_AR` | UPDATE, DELETE; no cuenta en resumen |

Escribano: solo lectura en todos los estados.

No hay estado “inmutable por antigüedad” (contraste con movimientos 24h).

## Volume Assumptions

- Plazos fijos por caja: ≤ 500 en operación normal
- Usuarios concurrentes: ≤ 10 (igual que feature 001)
- Sin integración externa ni jobs de vencimiento automático

## Alembic

Nueva revisión esperada: `003_plazo_fijo.py` (nombre exacto en implementación).
