# Research: 009-entrada-salida-fecha

**Date**: 2026-09-14  
**Branch**: `009-entrada-salida-fecha`

---

## 1. Mecanismo `registrar_complementario` — Estado actual

### Decision
Reutilizar el campo `registrar_complementario: true` en `POST /{caja_id}/movimientos`, eliminando la restricción `validate_complementario_only_for_usd` del schema `CreateMovimientoRequest` y extendiendo `create_movimiento_pair` para aceptar cualquier moneda.

### Rationale
- El backend ya tiene `create_movimiento_pair` en `MovimientoService` que opera dentro de la misma sesión SQLAlchemy y delega el commit al router → atomicidad ya garantizada por `db.rollback()` en el bloque `except`.
- El router ya tiene el bloque try/except con `db.rollback()` para el path `registrar_complementario=True`.
- El único cambio necesario es: (a) quitar el `model_validator` que rechaza ARS y (b) pasar `moneda=payload.moneda` a `create_movimiento_pair` en lugar de hardcodear `"USD"`.

### Alternatives considered
- **Nuevo endpoint** `POST /{caja_id}/movimientos/par`: requeriría nuevo schema, nuevo handler y duplicar lógica de caja/auth. Descartado — mayor surface con igual resultado.
- **Dos requests desde el frontend**: no atómico por definición. Descartado por FR-002.

---

## 2. Campo `fecha_manual` — Diseño del campo en el modelo

### Decision
Agregar columna `fecha_manual` (`DATE`, nullable) al modelo `Movimiento` y tabla `movimiento`. El backend construye `fecha_manual + 09:00:00 America/Argentina/Buenos_Aires` y lo almacena en una nueva columna `fecha_registro` (`TIMESTAMPTZ`, nullable). Cuando `fecha_manual` es `null`, se usa `created_at` como fecha de visualización.

**Alternativa más simple adoptada**: en lugar de una columna separada, añadir solo `fecha_override` (`TIMESTAMPTZ`, nullable). Si está presente, es la fecha del movimiento para visualización y ordenamiento; si es `null`, se usa `created_at`. Esto simplifica el schema evitando dos columnas redundantes.

### Rationale
- `created_at` tiene `server_default=func.now()` — no se debe modificar (es auditoría de cuándo se hizo el INSERT).
- Una columna `fecha_override TIMESTAMPTZ nullable` es suficiente: `fecha_display = fecha_override ?? created_at`.
- El frontend envía `fecha_manual: "YYYY-MM-DD"` (string ISO date). El backend calcula `datetime(año, mes, día, 9, 0, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))` y lo almacena en `fecha_override`.
- El ordenamiento de movimientos (`ORDER BY created_at DESC`) deberá actualizarse para usar `COALESCE(fecha_override, created_at) DESC`.

### Alternatives considered
- **Modificar `created_at`**: viola el principio de auditoría, y tiene `server_default` inmutable. Descartado.
- **Dos columnas `fecha_manual DATE` + `fecha_registro TIMESTAMPTZ`**: más verboso sin ventaja funcional. Descartado.

---

## 3. Impacto en ordenamiento y subtotales

### Decision
El cálculo de subtotales en `create_movimiento` usa `ORDER BY created_at DESC` para encontrar el último movimiento del stream. Con `fecha_override`, se deberá ordenar por `COALESCE(fecha_override, created_at) DESC, id DESC`.

### Rationale
- Insertar un movimiento con fecha pasada debe ubicarse correctamente en el historial cronológico.
- `recalculate_subtotals` ya reordena por `created_at ASC` — deberá actualizarse a `COALESCE(fecha_override, created_at) ASC, id ASC`.
- El índice compuesto `idx_movimiento_caja_moneda_created` también deberá incluir `fecha_override` o reemplazarse.

### Migration note
Nueva migración `009_movimiento_fecha_override.py`:
- `ADD COLUMN fecha_override TIMESTAMPTZ NULL`
- Actualizar índice compuesto para incluir expresión `COALESCE(fecha_override, created_at)`

---

## 4. Exposición de `fecha_override` en la API response

### Decision
`MovimientoResponse.fecha` actualmente mapea desde `movimiento.created_at`. Se actualizará para devolver `fecha_override` si está presente, o `created_at` en caso contrario. No se agrega un campo nuevo al response — el campo `fecha` ya existe y el frontend ya lo consume.

### Rationale
- El frontend (tabla de historial, columna Fecha) ya renderiza `movimiento.fecha`.
- Cambiar la lógica de `movimiento_to_response` para usar `fecha_override ?? created_at` es no-breaking para el cliente.

---

## 5. Frontend — `MovimientoForm` cambios

### Decision
- Eliminar estado `pendingTipo` y todo el JSX del diálogo modal (`complementario-dialog-backdrop`).
- Agregar estado `fechaManual: string` (formato `"YYYY-MM-DD"`, vacío por defecto).
- Agregar `<input type="date">` opcional, sin reset al cambiar caja.
- El botón "Entrada y Salida" llama a `doSubmit` directamente con `registrar_complementario: true` y el tipo que corresponda (siempre se envía `tipo: "entrada"` — el par se genera en backend).
- `CreateMovimientoPayload` en `api.ts` se extiende con `fecha_manual?: string`.

### Rationale
- Eliminar `pendingTipo` simplifica drásticamente el componente (de 3 caminos a 2).
- El selector de fecha no se resetea con `activeCajaId` en el `useEffect` — se elimina `setMoneda("ARS")` del efecto y se mantiene solo `setAdditionalCajaIds([])`.

---

## 6. Testing — TDD-first scope

### Decision
Orden de implementación por Work Unit:
1. Tests unitarios del servicio → implementación del servicio
2. Tests de integración del endpoint → implementación del endpoint/schema
3. Tests unitarios de componentes React (Vitest) → implementación del componente

### Test files afectados
- `backend/tests/unit/test_movimiento_service.py` — extender con casos `fecha_override` y `create_movimiento_pair` con ARS
- `backend/tests/unit/test_movimiento_moneda.py` — agregar casos de par ARS
- `backend/tests/integration/test_movimientos_api.py` — agregar casos de `fecha_manual` y par ARS
- `frontend/src/components/MovimientoForm.test.tsx` — nuevo (Vitest + Testing Library)

---

## 7. Conclusión — Sin bloqueos

Todos los NEEDS CLARIFICATION del spec están resueltos. No hay dependencias externas nuevas. El stack existente (FastAPI + SQLAlchemy + Alembic + React + Vitest) cubre todos los cambios requeridos.
