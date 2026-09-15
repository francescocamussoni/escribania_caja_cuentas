# Implementation Plan: Botón Entrada+Salida Simultáneo y Selector de Fecha

**Branch**: `009-entrada-salida-fecha` | **Date**: 2026-09-14 | **Spec**: [spec.md](./spec.md)

---

## Summary

Expandir el formulario de registro de movimientos para soportar:
1. Un botón **"Entrada y Salida"** que registra un par atómico (entrada + salida) en la misma caja y moneda, tanto para ARS como para USD, reemplazando el diálogo modal de confirmación complementario.
2. Un **selector de fecha opcional** que permite registrar movimientos en una fecha pasada o futura; el backend aplica hora `09:00 AM (UTC-3)` al valor recibido.

Enfoque técnico: extender el campo `registrar_complementario` para ARS (eliminar validación USD-only), añadir columna `fecha_override TIMESTAMPTZ` al modelo, y actualizar el componente `MovimientoForm` eliminando el estado `pendingTipo`.

---

## Technical Context

**Language/Version**: Python 3.12 (backend) · TypeScript 5.6 / React 18.3 (frontend)  
**Primary Dependencies**: FastAPI 0.115, SQLAlchemy 2.0, Alembic 1.14, Pydantic 2.10, Vitest 2.1, Testing Library 16  
**Storage**: PostgreSQL (local + AWS RDS)  
**Testing**: pytest (backend) · Vitest + @testing-library/react (frontend) · **TDD-first**  
**Target Platform**: Linux server (backend) · Navegador web (frontend)  
**Project Type**: Web application (backend/ + frontend/)  
**Performance Goals**: Operación par Entrada+Salida ≤ 2× latencia de operación simple  
**Constraints**: Atomicidad en base de datos (una transacción para el par); subtotales correctos tras inserción en fecha pasada  
**Scale/Scope**: ≤10 usuarios concurrentes; ~15 cajas activas

---

## Constitution Check

*GATE: evaluado antes de Phase 0. Re-evaluado post-diseño.*

| Principio | Estado | Evidencia |
|---|---|---|
| **I. Integridad Financiera** | ✅ PASS | Par Entrada+Salida atómico (FR-002, FR-005). `fecha_override` ordena correctamente el stream; subtotales recalculados. |
| **II. Control de Acceso RBAC** | ✅ PASS | El endpoint existente ya requiere rol `secretaria`. Ningún endpoint nuevo que requiera nueva validación de auth. |
| **III. Fidelidad al Diseño (Wireframes)** | ✅ PASS | Botón "Entrada y Salida" añadido al formulario. Diálogo modal eliminado. El selector de fecha es un campo adicional no contemplado en wireframes pero acordado con el usuario. |
| **IV. Seguridad por Diseño** | ✅ PASS | `fecha_manual` validada con regex en Pydantic. `registrar_complementario` sigue siendo server-side. No se exponen datos internos nuevos. |
| **V. Arquitectura Fullstack Desacoplada** | ✅ PASS | Lógica de conversión fecha→datetime en backend. Frontend solo envía `YYYY-MM-DD`. |
| **VI. Costo Mínimo AWS** | ✅ PASS | Un campo nullable en tabla existente + índice. Sin nuevos servicios ni endpoints. |

**Re-check post-diseño**: PASS — la columna `fecha_override` es additive (nullable); la eliminación de la restricción USD-only en `registrar_complementario` es backward-compatible en la API (clients que enviaban `true` solo para USD siguen funcionando).

---

## Project Structure

### Documentation (this feature)

```text
specs/009-entrada-salida-fecha/
├── plan.md              ← este archivo
├── research.md          ← Phase 0 ✅
├── data-model.md        ← Phase 1 ✅
├── quickstart.md        ← Phase 1 ✅
├── contracts/
│   └── openapi-delta.yaml  ← Phase 1 ✅
├── checklists/
│   └── requirements.md
└── tasks.md             ← generado por /spec-kitti.tasks
```

### Source Code — archivos afectados

```text
backend/
├── alembic/versions/
│   └── 009_movimiento_fecha_override.py     [CREAR]
├── src/app/
│   ├── models/
│   │   └── movimiento.py                    [MODIFICAR] +fecha_override
│   ├── schemas/
│   │   └── movimiento.py                    [MODIFICAR] +fecha_manual, -validate_complementario_only_for_usd
│   ├── services/
│   │   └── movimiento_service.py            [MODIFICAR] create_movimiento_pair(moneda), ordenamiento COALESCE
│   └── api/routes/
│       └── movimientos.py                   [MODIFICAR] pasar moneda a create_movimiento_pair, fecha_override
└── tests/
    ├── unit/
    │   ├── test_movimiento_service.py        [MODIFICAR] casos par ARS, fecha_override
    │   └── test_movimiento_moneda.py         [MODIFICAR] casos par ARS
    └── integration/
        └── test_movimientos_api.py           [MODIFICAR] casos fecha_manual, par ARS

frontend/
└── src/
    ├── services/
    │   └── api.ts                           [MODIFICAR] +fecha_manual en CreateMovimientoPayload
    └── components/
        ├── MovimientoForm.tsx               [MODIFICAR] +botón Entrada y Salida, +selector fecha, -dialog
        └── MovimientoForm.test.tsx          [CREAR] Vitest + Testing Library
```

---

## Plan Jerárquico

### Work Unit 1: Backend — Migración y modelo `fecha_override`

**Propósito**: Añadir la columna `fecha_override` al modelo y la base de datos, con el índice compuesto actualizado.

**Entidades afectadas**:
- `Movimiento` (tabla `movimiento`)
- Índice `idx_movimiento_caja_moneda_created` (reemplazado)

**Archivos a crear/modificar**:
- `backend/alembic/versions/009_movimiento_fecha_override.py` — migración Alembic
- `backend/src/app/models/movimiento.py` — columna `fecha_override: Mapped[datetime | None]`

**Pruebas de Paridad Legacy**:
- `backend/tests/unit/test_movimiento_moneda.py` — todos los tests existentes deben seguir pasando tras la migración

**Subtareas internas**:
1. Escribir test de migración (aplica / revierte sin errores)
2. Crear `009_movimiento_fecha_override.py` con `ADD COLUMN` y reemplazo de índice
3. Añadir `fecha_override` a `Movimiento` ORM (`Mapped[datetime | None]`, nullable)
4. Ejecutar y verificar migración en local

**Criterio de éxito**: `alembic upgrade head` y `alembic downgrade -1` ejecutan sin errores. El modelo refleja la nueva columna.

**Estimación**: 1h

---

### Work Unit 2: Backend — Schema y validación `fecha_manual`

**Propósito**: Extender `CreateMovimientoRequest` con `fecha_manual` opcional y eliminar la restricción `registrar_complementario` USD-only.

**Entidades afectadas**:
- `CreateMovimientoRequest` (Pydantic schema)

**Archivos a crear/modificar**:
- `backend/src/app/schemas/movimiento.py` — +`fecha_manual`, -`validate_complementario_only_for_usd`
- `backend/tests/unit/test_movimiento_moneda.py` — tests TDD para nuevas validaciones

**Pruebas de Paridad Legacy**:
- Todos los tests existentes de `CreateMovimientoRequest` deben seguir pasando

**Subtareas internas**:
1. [TDD] Escribir tests: `fecha_manual` válida, inválida, ausente; `registrar_complementario=true` con ARS
2. Añadir campo `fecha_manual: date | None` con validador de formato
3. Eliminar `validate_complementario_only_for_usd`
4. Correr tests — todos deben pasar

**Criterio de éxito**: Suite de tests del schema pasa al 100%. `registrar_complementario=true` con `moneda="ARS"` es aceptado sin error 422.

**Estimación**: 1.5h

---

### Work Unit 3: Backend — Servicio `create_movimiento_pair` + ordenamiento COALESCE

**Propósito**: Extender `create_movimiento_pair` para soportar cualquier moneda, y actualizar el ordenamiento en `create_movimiento` y `recalculate_subtotals` para usar `COALESCE(fecha_override, created_at)`.

**Entidades afectadas**:
- `MovimientoService`

**Archivos a crear/modificar**:
- `backend/src/app/services/movimiento_service.py`
- `backend/tests/unit/test_movimiento_service.py`
- `backend/tests/unit/test_movimiento_moneda.py`

**Pruebas de Paridad Legacy**:
- `backend/tests/unit/test_movimiento_service.py` — tests existentes de `create_movimiento_pair` (USD) deben seguir pasando
- `backend/tests/unit/test_movimiento_moneda.py` — tests existentes de streams de moneda

**Subtareas internas**:
1. [TDD] Escribir tests: par ARS atómico; subtotales correctos con `fecha_override` en pasado; `recalculate_subtotals` con `fecha_override`
2. Añadir parámetro `moneda` a `create_movimiento_pair` (ya no hardcodea `"USD"`)
3. Actualizar `create_movimiento`: ORDER BY `COALESCE(fecha_override, created_at) DESC, id DESC`
4. Actualizar `create_movimiento`: persistir `fecha_override` desde parámetro `fecha_override: datetime | None`
5. Actualizar `recalculate_subtotals`: ORDER BY `COALESCE(fecha_override, created_at) ASC, id ASC`
6. Correr tests

**Criterio de éxito**: Par ARS crea dos movimientos atómicos con subtotales correctos. Insertar un movimiento con fecha pasada ordena el historial correctamente y recalcula subtotales.

**Estimación**: 2h

---

### Work Unit 4: Backend — Endpoint y response `fecha_override`

**Propósito**: Actualizar el router para pasar `moneda` a `create_movimiento_pair`, calcular `fecha_override` desde `fecha_manual`, y actualizar `movimiento_to_response` para devolver `fecha_override ?? created_at`.

**Entidades afectadas**:
- Router `movimientos.py`
- `movimiento_to_response` en `schemas/movimiento.py`

**Archivos a crear/modificar**:
- `backend/src/app/api/routes/movimientos.py`
- `backend/src/app/schemas/movimiento.py` — `movimiento_to_response`
- `backend/tests/integration/test_movimientos_api.py`

**Pruebas de Paridad Legacy**:
- `backend/tests/integration/test_movimientos_api.py` — todos los tests de integración existentes

**Subtareas internas**:
1. [TDD] Escribir tests de integración: POST con `fecha_manual` → response `fecha` = fecha elegida a 09:00 AM; POST par ARS → response con `complementario` no nulo; POST sin `fecha_manual` → `fecha` = `created_at` (sin regresión)
2. Actualizar `create_movimiento` en router: calcular `fecha_override = datetime(año, mes, día, 9, 0, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))` si `payload.fecha_manual` presente
3. Pasar `fecha_override` a `service.create_movimiento(...)` y `service.create_movimiento_pair(...)`
4. Actualizar `movimiento_to_response`: `fecha = movimiento.fecha_override or movimiento.created_at`
5. Correr tests de integración

**Criterio de éxito**: Los tests de integración pasan. `fecha` en la respuesta refleja `fecha_override` cuando se proveyó `fecha_manual`.

**Estimación**: 2h

---

### Work Unit 5: Frontend — `api.ts` y `MovimientoForm`

**Propósito**: Actualizar el tipo `CreateMovimientoPayload`, eliminar el diálogo de complementario, añadir el botón "Entrada y Salida" y el selector de fecha.

**Entidades afectadas**:
- `MovimientoForm` (componente React)
- `api.ts` (tipo `CreateMovimientoPayload`)

**Archivos a crear/modificar**:
- `frontend/src/services/api.ts` — +`fecha_manual?: string`
- `frontend/src/components/MovimientoForm.tsx` — refactor completo
- `frontend/src/components/MovimientoForm.test.tsx` — **CREAR** (Vitest + Testing Library)

**Pruebas de Paridad Legacy**:
- Ningún test de frontend existente para `MovimientoForm` (archivo nuevo)

**Subtareas internas**:
1. [TDD] Escribir `MovimientoForm.test.tsx`: renderiza botones "Entrada", "Salida", "Entrada y Salida"; al pulsar "Entrada y Salida" llama a `onSubmit` con `registrar_complementario: true`; al seleccionar fecha, la envía en el payload; sin fecha seleccionada, `fecha_manual` ausente en payload; diálogo modal NO renderizado para moneda USD
2. Añadir `fecha_manual?: string` a `CreateMovimientoPayload` en `api.ts`
3. Eliminar estado `pendingTipo`, todo el JSX del diálogo `complementario-dialog-backdrop`
4. Añadir estado `fechaManual: string` (default `""`)
5. Añadir `<input type="date">` con label "Fecha (opcional)"
6. Añadir botón "Entrada y Salida" → `doSubmit("entrada", true)` (el backend crea el par)
7. Actualizar `doSubmit` para incluir `fecha_manual` en el payload cuando `fechaManual !== ""`
8. Ajustar `useEffect` de `activeCajaId`: mantener `setAdditionalCajaIds([])` y `setMoneda("ARS")` pero **no** resetear `fechaManual`
9. Correr tests Vitest

**Criterio de éxito**: Tests Vitest pasan. El formulario renderiza los 3 botones. Para moneda USD, pulsar "Entrada" registra directamente sin diálogo. El payload incluye `fecha_manual` solo cuando hay fecha seleccionada.

**Estimación**: 3h

---

### Notas para Itti-Kit

**Total Work Units**: 5  
**Tiempo total estimado**: 9.5h  
**Work Units que pueden ejecutarse en paralelo**: WU-2 y WU-3 son parcialmente paralelas (WU-3 depende del modelo de WU-1; WU-2 es independiente del modelo)

**Secuencia recomendada**:
```
WU-1 (migración) → WU-3 (servicio) → WU-4 (endpoint)
                ↗
WU-2 (schema)  
                ↘
                 WU-5 (frontend) — puede ejecutarse en paralelo con WU-3/4
```

---

## Complexity Tracking

> No hay violaciones a la constitución que requieran justificación.

| Item | Notas |
|---|---|
| Columna `fecha_override` nullable | Additive change — no rompe streams existentes. Movimientos sin fecha manual tienen `fecha_override = NULL` y siguen usando `created_at`. |
| Índice COALESCE | PostgreSQL soporta expresiones en índices. El índice con `COALESCE` es un índice de expresión estándar. |
| Eliminación de `validate_complementario_only_for_usd` | Backward-compatible — clientes existentes que enviaban `registrar_complementario: false` (o no lo enviaban) no se ven afectados. |
