# Implementation Plan: Plazos Fijos por Caja

**Branch**: `003-plazos-fijos` | **Date**: 2026-08-06 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/003-plazos-fijos/spec.md`

## Summary

Extensión incremental del sistema de cajas: dos nuevas pantallas (**Plazos Fijos**
gestión secretaria, **Consulta Plazos Fijos** lectura escribano/secretaria) con CRUD
sin ventana 24h, listado paginado (futuros primero por vencimiento, vencidos al
final), panel de dos totales solo para plazos activos, y API REST bajo el mismo
stack FastAPI + PostgreSQL + React. Enfoque **TDD** según spec.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x / React 18 (frontend)  
**Primary Dependencies**: FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 (existentes); React Router, Vite (existentes)  
**Storage**: PostgreSQL 16 — nueva tabla `plazo_fijo`  
**Testing**: pytest + httpx (backend TDD/integration); Vitest + Testing Library (frontend)  
**Target Platform**: Navegador web; API Linux container (igual que 001)  
**Project Type**: Web application (`frontend/` + `backend/`)  
**Performance Goals**: API listado/resumen < 500ms p95; ≤ 10 usuarios concurrentes  
**Constraints**: RBAC server-side; paginación fija 20; ARS 2 decimales; JWT 8h; sin multi-caja por registro  
**Scale/Scope**: 15 cajas; ~500 plazos/caja estimado; 2 pantallas nuevas + navbar

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I — Integridad Financiera | ✅ PASS | Totales y validación montos en backend/SQL; sin subtotales en cascada (dominio distinto a movimientos) |
| II — RBAC | ✅ PASS | POST/PATCH/DELETE `secretaria`; GET ambos roles; 403 escribano en escritura |
| III — Fidelidad al Diseño | ✅ PASS (con nota) | Sin drawio nuevos; paridad layout Registro/Consulta (FR-002); documentado en research R6 |
| IV — Seguridad | ✅ PASS | JWT, validación server-side, logs de escritura, sin PII en errores |
| V — Fullstack Desacoplado | ✅ PASS | OpenAPI en `contracts/`; lógica orden/agregación en backend |
| VI — Costo Mínimo AWS | ✅ PASS | Solo migración + deploy existente; sin nueva infra |

**Post-design re-check (Phase 1)**: ✅ All gates pass. No Complexity Tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/003-plazos-fijos/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── openapi.yaml     # Phase 1 — REST plazos fijos
└── tasks.md             # Phase 2 (/spec-kitti.tasks)
```

### Source Code (cambios esperados)

```text
backend/
├── alembic/versions/
│   └── 003_plazo_fijo.py          # NEW
├── src/app/
│   ├── models/
│   │   └── plazo_fijo.py          # NEW
│   ├── schemas/
│   │   └── plazo_fijo.py          # NEW
│   ├── services/
│   │   └── plazo_fijo_service.py  # NEW — orden, agregación, validación
│   ├── api/routes/
│   │   └── plazos_fijos.py        # NEW
│   └── main.py                    # register router
├── tests/
│   ├── unit/
│   │   └── test_plazo_fijo_order.py    # NEW
│   └── integration/
│       └── test_plazos_fijos_api.py    # NEW

frontend/
├── src/
│   ├── pages/
│   │   ├── PlazosFijosPage.tsx           # NEW — gestión (secretaria)
│   │   └── ConsultaPlazosFijosPage.tsx   # NEW — consulta
│   ├── components/
│   │   ├── PlazoFijoForm.tsx             # NEW
│   │   ├── PlazoFijoTable.tsx            # NEW
│   │   └── PlazosFijosResumenPanel.tsx   # NEW
│   ├── components/layout/Navbar.tsx      # MODIFY — links
│   ├── services/api.ts                   # MODIFY — tipos + fetchers
│   └── App.tsx                           # MODIFY — rutas + guards
└── tests/
    ├── PlazosFijosPage.test.tsx          # NEW
    └── ConsultaPlazosFijosPage.test.tsx  # NEW
```

**Structure Decision**: Extensión del monorepo `frontend/` + `backend/` existente.
Sin nuevos servicios Docker.

## Plan Jerárquico (para Itti-Kit)

### Work Unit 1: Modelo y Servicio Plazo Fijo (backend)

**Propósito**: Persistir `plazo_fijo`, validar montos, ordenar listado y calcular resumen activos.

**Entidades afectadas**:
- `plazo_fijo` (nueva tabla)
- `caja`, `usuario` (FK existentes)

**Archivos a crear/modificar**:
- `backend/alembic/versions/003_plazo_fijo.py`
- `backend/src/app/models/plazo_fijo.py`
- `backend/src/app/models/caja.py` — relationship opcional
- `backend/src/app/schemas/plazo_fijo.py`
- `backend/src/app/services/plazo_fijo_service.py`
- `backend/tests/unit/test_plazo_fijo_order.py`
- `backend/tests/unit/test_plazo_fijo_validation.py`

**Pruebas de Paridad Legacy**:
- `test_plazo_fijo_order.py` — orden futuros/vencidos, desempate created_at
- `test_plazo_fijo_validation.py` — montos, monto_a_vencimiento ≥ ingresado

**Subtareas internas**:
1. [TDD] Tests unitarios orden paginado y validación montos
2. Modelo SQLAlchemy + constraints CHECK
3. Migración Alembic `003_plazo_fijo`
4. Servicio: create, update, delete, list (paginado), get_resumen
5. Helper `hoy_ar` (America/Argentina/Buenos_Aires)

**Criterio de éxito**: Migración aplicable; tests unitarios verdes; orden y SUM coinciden con spec.

**Estimación**: 6 horas

---

### Work Unit 2: API REST Plazos Fijos

**Propósito**: Exponer endpoints alineados a OpenAPI con RBAC.

**Entidades afectadas**: `plazo_fijo`

**Archivos a crear/modificar**:
- `backend/src/app/api/routes/plazos_fijos.py`
- `backend/src/app/main.py`
- `backend/tests/integration/test_plazos_fijos_api.py`
- `specs/003-plazos-fijos/contracts/openapi.yaml` — validar paridad

**Pruebas de Paridad Legacy**:
- `test_plazos_fijos_api.py` — CRUD secretaria, 403 escribano, paginación 20, resumen

**Subtareas internas**:
1. [TDD] Contract/integration tests según openapi.yaml
2. `GET/POST /cajas/{id}/plazos-fijos`
3. `GET /cajas/{id}/plazos-fijos/resumen`
4. `PATCH/DELETE /cajas/{id}/plazos-fijos/{id}`
5. Logging seguridad en escritura

**Criterio de éxito**: quickstart §2 curl exitoso; SC-004, SC-005, SC-006a vía tests.

**Dependencias**: WU-001

**Estimación**: 6 horas

---

### Work Unit 3: UI Gestión Plazos Fijos (secretaria)

**Propósito**: Pantalla `/plazos-fijos` con formulario, tabla, resumen y CRUD.

**Entidades afectadas**: N/A (UI)

**Archivos a crear/modificar**:
- `frontend/src/pages/PlazosFijosPage.tsx`
- `frontend/src/components/PlazoFijoForm.tsx`
- `frontend/src/components/PlazoFijoTable.tsx`
- `frontend/src/components/PlazosFijosResumenPanel.tsx`
- `frontend/src/services/api.ts`
- `frontend/tests/PlazosFijosPage.test.tsx`

**Pruebas de Paridad Legacy**:
- Tests UI: crear, editar, eliminar (confirm), cambio caja, paginación

**Subtareas internas**:
1. [TDD] Tests página con mocks API
2. Layout paridad RegistroCajaPage (selector, form, resumen, tabla, paginación)
3. Integración API create/update/delete/list/resumen
4. `SecretariaOnlyRoute` en App.tsx
5. Formato ARS y fechas

**Criterio de éxito**: SC-001, SC-002; secretaria completa flujo sin errores.

**Dependencias**: WU-002

**Estimación**: 8 horas

---

### Work Unit 4: UI Consulta Plazos Fijos

**Propósito**: Pantalla `/consulta-plazos-fijos` solo lectura con botón Consulta.

**Entidades afectadas**: N/A (UI)

**Archivos a crear/modificar**:
- `frontend/src/pages/ConsultaPlazosFijosPage.tsx`
- `frontend/src/components/layout/Navbar.tsx`
- `frontend/src/App.tsx`
- `frontend/tests/ConsultaPlazosFijosPage.test.tsx`

**Pruebas de Paridad Legacy**:
- Escribano: consulta OK, sin botones editar/eliminar
- Secretaria: misma vista consulta

**Subtareas internas**:
1. [TDD] Tests consulta escribano/secretaria
2. Patrón ConsultaCajaPage (selector + Consulta + resumen dual + tabla)
3. Navbar links según rol
4. Redirección escribano si intenta `/plazos-fijos`

**Criterio de éxito**: SC-003, SC-006; escribano consulta 15 cajas.

**Dependencias**: WU-002

**Estimación**: 6 horas

---

### Work Unit 5: Documentación y validación E2E

**Propósito**: Actualizar docs operativas y ejecutar quickstart walkthrough.

**Entidades afectadas**: N/A

**Archivos a crear/modificar**:
- `docs/frontend.md` — rutas y pantallas nuevas
- `specs/003-plazos-fijos/quickstart.md` — ajustes si necesario
- `README.md` — mención feature (opcional)

**Subtareas internas**:
1. Ejecutar quickstart completo
2. `make test` verde
3. Revisión Constitution Check final

**Criterio de éxito**: Quickstart reproducible; todos los tests pasan.

**Dependencias**: WU-003, WU-004

**Estimación**: 2 horas

---

### Notas para Itti-Kit

**Total estimado de Work Units**: 5  
**Tiempo total estimado**: 28 horas  
**Work Units paralelizables**: WU-003 y WU-004 (tras WU-002, si 2 devs)

## Complexity Tracking

> No violations — table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Open Items (post-plan)

- Constitution § Funcionalidades no lista Plazos Fijos aún — amend constitución opcional en implementación o `/spec-kitti.amend`.
- Re-ejecutar `setup-plan.sh` sobrescribe `plan.md` con plantilla; restaurar desde git o este archivo.

## Artifacts Generated (Phase 0 + Phase 1)

| Artifact | Path |
|----------|------|
| Research | `specs/003-plazos-fijos/research.md` |
| Data model | `specs/003-plazos-fijos/data-model.md` |
| API contract | `specs/003-plazos-fijos/contracts/openapi.yaml` |
| Quickstart | `specs/003-plazos-fijos/quickstart.md` |

## Testing Strategy (plan alignment)

- **Enfoque**: `TDD` — tests antes de implementación (spec § Testing Strategy).
- **Rationale**: RBAC + orden paginado + agregaciones financieras.
- **Scope note**: `/spec-kitti.tasks` DEBE generar tareas de test previas a código en cada WU.
