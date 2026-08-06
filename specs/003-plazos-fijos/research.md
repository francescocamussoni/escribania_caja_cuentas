# Research: Plazos Fijos por Caja

**Feature**: `003-plazos-fijos`  
**Date**: 2026-08-06

## R1 — Extensión del stack existente

**Decision**: Reutilizar stack de `001-registro-cajas` sin cambios (Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic; React 18 + TypeScript + Vite; PostgreSQL 16).

**Rationale**:
- Feature incremental sobre codebase desplegado; minimiza riesgo y costo.
- Mismos patrones de RBAC, paginación y DTOs Pydantic.
- TDD con pytest + Vitest ya configurado.

**Alternatives considered**:
- **Nuevo microservicio**: rechazado — sobrecarga operativa para dominio acoplado a `caja`.
- **Tabla en SQLite separada**: rechazado — viola FR-020 (misma PostgreSQL).

## R2 — Modelo de datos `plazo_fijo`

**Decision**: Nueva tabla `plazo_fijo` con FK a `caja` y `usuario`; sin tabla de historial ni soft-delete.

**Rationale**:
- CRUD simple sin recálculo en cascada (contraste con movimientos).
- Edición/eliminación sin ventana temporal simplifica el servicio.
- `NUMERIC(15,2)` + `CHECK` en DB para montos y `monto_a_vencimiento >= monto_ingresado`.

**Alternatives considered**:
- **Reutilizar `movimiento` con tipo especial**: mezcla dominios distintos y complica subtotales.
- **Soft-delete**: no requerido en spec; delete físico con log de seguridad.

## R3 — Orden y paginación del listado

**Decision**: Orden compuesto en SQL sobre `fecha_vencimiento` (DATE) con referencia **fecha calendario Argentina** (`America/Argentina/Buenos_Aires`):

1. Grupo futuro (`fecha_vencimiento >= hoy_AR`) primero, ascendente por vencimiento.
2. Grupo vencido al final, descendente por vencimiento.
3. Desempate: `created_at DESC`, `id DESC`.

Paginación offset `page` + `page_size=20` igual que movimientos.

**Rationale**:
- Cumple FR-010 y clarificaciones (futuros primero, vencidos al final).
- Una sola query paginada evita lógica frágil en Python.
- Índice compuesto en `(caja_id, fecha_vencimiento, created_at)` para listados.

**SQL de referencia**:

```sql
ORDER BY
  (fecha_vencimiento < :hoy_ar) ASC,
  CASE WHEN fecha_vencimiento >= :hoy_ar THEN fecha_vencimiento END ASC NULLS LAST,
  CASE WHEN fecha_vencimiento < :hoy_ar THEN fecha_vencimiento END DESC NULLS LAST,
  created_at DESC,
  id DESC
```

**Alternatives considered**:
- **Orden solo en aplicación**: rompe paginación correcta entre páginas.
- **Dos endpoints (activos / vencidos)**: más llamadas UI; no alineado a spec de tabla única.

## R4 — Panel de resumen (totales activos)

**Decision**: Endpoint dedicado `GET /cajas/{id}/plazos-fijos/resumen` con agregación SQL `SUM` filtrada `fecha_vencimiento >= hoy_AR`.

**Rationale**:
- Paridad con `GET /cajas/{id}/saldo` en consulta de caja.
- Totales calculados en backend (principio V — frontend no autoritativo).
- Respuesta incluye `total_monto_ingresado_activos` y `total_monto_a_vencimiento_activos`.

**Alternatives considered**:
- **Incluir totales en cada página del listado**: redundante y puede desincronizar al paginar.
- **Calcular en frontend**: rechazado por constitución V.

## R5 — Autorización y edición sin ventana 24h

**Decision**: POST/PATCH/DELETE con `require_role("secretaria")`; sin `ensure_within_edit_window`; escribano recibe 403 en escritura.

**Rationale**:
- FR-007/FR-008 explícitos: sin restricción temporal.
- Contraste intencional con movimientos — no reutilizar guard de 24h.

**Alternatives considered**:
- **Misma ventana 24h que movimientos**: contradice spec y clarificaciones.

## R6 — UX frontend (paridad visual)

**Decision**:
- **Plazos Fijos** (gestión): patrón `RegistroCajaPage` — auto-carga al cambiar caja, formulario + tabla + paginación, confirmación antes de eliminar (`window.confirm` como movimientos).
- **Consulta Plazos Fijos**: patrón `ConsultaCajaPage` — selector + botón **Consulta**, panel de dos totales + tabla.
- Rutas: `/plazos-fijos`, `/consulta-plazos-fijos`.
- Navbar: enlaces visibles según rol (gestión solo secretaria).

**Rationale**:
- FR-002 y FR-011; estética existente en `index.css` sin nuevo framework.
- Sin `CajasAdicionalesSelector` (clarificación: una caja por plazo).

**Alternatives considered**:
- **Wireframes nuevos**: no requeridos; replicar layout consulta/registro.

## R7 — Testing (TDD)

**Decision**: TDD estricto según `spec.md` § Testing Strategy.

**Rationale**:
- Dominio financiero + RBAC; tests de orden/paginación y agregaciones son obligatorios.

**Scope note**: Esta decisión DEBE honrarse en `/spec-kitti.tasks` (tests antes de implementación).

**Alternatives considered**: Ninguna — spec ya fijó TDD.

## R8 — Contrato API

**Decision**: Extender OpenAPI en `specs/003-plazos-fijos/contracts/openapi.yaml` (v1.0.0 feature); implementación en `backend` alineará rutas bajo `/api/v1/cajas/{cajaId}/plazos-fijos`.

**Rationale**:
- Contrato aislado por feature; merge opcional a swagger global en `/spec-kitti.swagger`.

**Alternatives considered**:
- **Solo documentación Markdown**: menos validable en contract tests.
