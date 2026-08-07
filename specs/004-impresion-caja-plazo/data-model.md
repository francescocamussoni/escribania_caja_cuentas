# Data Model: Impresión de Caja y Plazos Fijos

**Feature**: `004-impresion-caja-plazo`  
**Storage**: PostgreSQL 16 (sin cambios de schema — reutiliza tablas existentes)

## Entity Relationship Overview

```text
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   usuario   │       │    caja     │       │  movimiento │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │◄──────│ caja_id     │
│ rol         │       │ nombre      │       │ created_at  │◄── filtro informe CAJA
└─────────────┘       │ slug        │       │ subtotal    │◄── saldo cierre / actual
                      └──────┬──────┘       └─────────────┘
                             │
                      ┌──────▼──────┐
                      │ plazo_fijo  │
                      ├─────────────┤
                      │ caja_id     │
                      │ created_at  │◄── filtro informe PLAZO_FIJO
                      │ fecha_vencimiento │◄── activo vs vencido (resumen)
                      └─────────────┘

┌──────────────────────┐
│ Solicitud de informe │  (DTO efímero — no persistido)
├──────────────────────┤
│ tipo                 │
│ caja_id              │
│ modo_temporal        │
│ hasta_hoy (bool)     │
│ mes, anio | fechas   │
└──────────────────────┘
```

## Tablas reutilizadas (sin migración)

### `movimiento`

| Uso en informe CAJA | Campo |
|---------------------|-------|
| Filtro temporal | `created_at` → fecha calendario AR |
| Columnas PDF | `descripcion`, `monto`, `tipo`, `subtotal`, `created_at` |
| Saldo cierre período | `subtotal` del registro con max `created_at` en filtro |
| Saldo actual | `subtotal` del registro con max `created_at` de la caja (sin filtro) |
| Orden filas | `created_at DESC`, `id DESC` |

### `plazo_fijo`

| Uso en informe PLAZO_FIJO | Campo |
|---------------------------|-------|
| Filtro temporal | `created_at` → fecha calendario AR |
| Columnas PDF | `monto_ingresado`, `fecha_vencimiento`, `monto_a_vencimiento` |
| Resumen activos filtrados | `SUM` donde `fecha_vencimiento >= hoy_AR` y `created_at` en rango |
| Orden filas | Misma regla que `PlazoFijoService._list_order_clauses` |

### `caja`

| Uso | Campo |
|-----|-------|
| Selector / encabezado | `id`, `nombre`, `slug` |
| Filename | `nombre` normalizado (espacios → `-`) |

## DTOs de aplicación (nuevos — no tablas)

### `InformePdfRequest`

| Campo | Tipo | Validación |
|-------|------|------------|
| `tipo` | enum `CAJA` \| `PLAZO_FIJO` | Obligatorio |
| `caja_id` | int | FK válida, 1–15 |
| `modo` | enum `MES_ANIO` \| `PERIODO` | Obligatorio |
| `hasta_hoy` | bool | Default `false`; si `true`, `date_to = today_ar()` |
| `mes` | int 1–12 | Requerido si `modo=MES_ANIO` |
| `anio` | int | Requerido si `modo=MES_ANIO` |
| `fecha_inicio` | date | Requerido si `modo=PERIODO` |
| `fecha_fin` | date | Requerido si `modo=PERIODO` y `hasta_hoy=false`; ≥ `fecha_inicio` |

**Resolución de rango** (`resolve_date_range`):

| modo | hasta_hoy | date_from | date_to |
|------|-----------|-----------|---------|
| MES_ANIO | false | 1er día mes/anio | último día mes/anio |
| MES_ANIO | true | 1er día mes/anio | `today_ar()` |
| PERIODO | false | `fecha_inicio` | `fecha_fin` |
| PERIODO | true | `fecha_inicio` | `today_ar()` |

Validación: `date_from` ≤ `date_to`; si `hasta_hoy` y mes/fecha inicio > hoy → 400.

`extra="forbid"` en Pydantic.

### `InformePdfMetadata` (interno, respuesta headers)

| Campo | Ejemplo |
|-------|---------|
| `filename` | `CAJA-Ebel-2026-03.pdf` |
| `content_type` | `application/pdf` |
| `generated_at` | ISO8601 AR |

## Reglas de negocio — informes

| Regla | Fuente |
|-------|--------|
| Solo lectura; sin INSERT/UPDATE/DELETE | FR-024 |
| Roles `secretaria` y `escribano` | FR-001, FR-026 |
| Movimiento: etiqueta Entrada/Salida o +/− en PDF | FR-014a |
| Caja: dos saldos (cierre período + actual) | FR-016, clarificación Q1 |
| Plazos: resumen solo activos del período filtrado | FR-019, clarificación Q2 |
| Período vacío → PDF con mensaje, sin tabla vacía | Edge cases |
| Filename `<TIPO>-<NOMBRE>-<PERIODO>.pdf` | FR-021a |
| `hasta_hoy` en mes y período | FR-005a, amend 2026-08-06 |

## Funciones de dominio (nuevos servicios)

### `InformeService`

- `resolve_date_range(request) -> (date_from, date_to)` — mes/año, período, **hasta_hoy**
- `fetch_movimientos_informe(caja_id, date_from, date_to) -> list[Movimiento]`
- `compute_saldo_cierre(movimientos_filtrados) -> Decimal | None`
- `fetch_plazos_informe(caja_id, date_from, date_to) -> list[PlazoFijo]`
- `compute_resumen_plazos_filtrado(plazos_filtrados) -> PlazosFijosResumen`

### `PdfInformeRenderer`

- `render_caja_pdf(metadata, movimientos, saldo_cierre, saldo_actual) -> bytes`
- `render_plazo_fijo_pdf(metadata, plazos, resumen) -> bytes`
- Tipografía formal A4; encabezado operativo (FR-022)

## Índices existentes (suficientes v1)

- `movimiento`: índice por `caja_id` + orden por `created_at` (existente en uso de listado)
- `plazo_fijo`: `idx_plazo_fijo_caja_vencimiento` (feature 003)

No se requieren migraciones Alembic para esta feature.

## Seguridad

- JWT obligatorio en `POST /informes/pdf`
- Validar `caja_id` existe antes de consultar
- No incluir PII de usuario en PDF ni logs del contenido del informe
- Registrar evento `informe_generated` con `tipo`, `caja_id`, `modo` (sin montos)
