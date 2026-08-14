# Tasks: Configuración y Archivo de Cajas

**Input**: Design documents from `/specs/006-config-archivo-cajas/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml  
**Testing**: TDD obligatorio (spec.md → Testing Strategy)

**Organization**: Tareas agrupadas por user story. Tests escritos **antes** de implementación.

## Design Reference (UI)

Este proyecto no usa Figma para esta feature. La constitución (principio III) define
`registro_de_caja.drawio` y `consulta_de_caja.drawio` como referencia de Registro y Consulta.
La solapa de configuración es pantalla nueva: layout alineado a Navbar + páginas existentes
(paridad visual, sin frame Figma). Las tareas UI usan campo `wireframe:` (patrón 001–005).

| Pantalla | Wireframe / referencia |
|----------|------------------------|
| Solapa Configuración | `frontend/src/pages/ConfiguracionCajasPage.tsx` (nueva; paridad `RegistroCajaPage.tsx`) |
| Navbar (enlace Configuración) | `frontend/src/components/layout/Navbar.tsx` |
| Selectores / boxes de cajas | `frontend/src/components/CajaSelector.tsx`, `CajasAdicionalesSelector.tsx` |

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Paralelizable (archivos distintos, sin dependencias incompletas)
- **[USn]**: User story del spec.md

## Path Conventions

- Backend: `backend/src/app/`, tests en `backend/tests/`
- Frontend: `frontend/src/`, tests en `frontend/tests/`
- Migración: `backend/alembic/versions/006_caja_estado_archivo.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline verde y contrato alineado antes de TDD.

- [x] T001 Verify branch `006-config-archivo-cajas` and baseline `make test-backend` / `make test-frontend` pass
- [x] T002 [P] Extend `specs/006-config-archivo-cajas/contracts/openapi.yaml` with `GET /cajas/config` (lista activas+archivadas para la solapa) and align prefixes with `backend/src/app/api/router.py` (`/api/v1` + `/cajas`)
- [x] T003 [P] Add Alembic revision `caja.estado`, `archived_at`, `archived_by_user_id` and table `evento_configuracion_caja` in `backend/alembic/versions/006_caja_estado_archivo.py` per `data-model.md` (cajas existentes default `activa`)

**Checkpoint**: Branch `006-config-archivo-cajas`. Frontend 27/27 verde. Backend 111 passed / 1 failed / 25 errors preexistentes: login `admin`/`admin` → 401 porque tests de cambio de clave mutaron el hash en el Postgres compartido (fuera de alcance 006; fixtures no recrean usuario existente). Contrato OpenAPI alineado (`/api/v1` + `/cajas`, `GET /cajas/config`, ids integer). Migración Alembic 006 agregada (ORM en T005/T006).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modelo de estado de caja, auditoría y DTOs. **Bloquea todas las user stories.**

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 [P] Unit tests FIRST (must fail): transición `activa→archivada`, unicidad de `nombre` (activo o archivado), archivo idempotente in `backend/tests/unit/test_caja_service.py`
- [x] T005 Add `estado`, `archived_at`, `archived_by_user_id`, `updated_at` to `Caja` in `backend/src/app/models/caja.py`
- [x] T006 [P] Create `EventoConfiguracionCaja` model in `backend/src/app/models/evento_configuracion_caja.py` (`accion`, `resultado`, `actor_user_id`, `caja_id`, `detalle`)
- [x] T007 Add `CajaCreateRequest` (`extra="forbid"`, `nombre` 1–120) and extend `CajaResponse` with `estado` in `backend/src/app/schemas/caja.py`
- [x] T008 Implement `create_caja`, `archive_caja`, `list_cajas_activas`, `list_cajas_config` in `backend/src/app/services/caja_service.py` (TDD until T004 green)

**Checkpoint**: 8 tests de ciclo de vida verdes (`test_caja_service.py`). Modelos + DTOs listos. Migración 006 aplicada en el Postgres de compose. Sin endpoints públicos todavía.

---

## Phase 3: User Story 1 — Gestión de cajas por secretaria (Priority: P1) 🎯 MVP

**Goal**: Secretaria crea cajas nuevas (activas) y archiva cajas existentes desde una solapa de configuración, sin perder historial.

**Independent Test**: Login secretaria → `/configuracion` → crear caja → aparece en operación; archivar otra → queda en config como archivada y el historial de movimientos sigue accesible por id. Spec US1. Quickstart §3.

### Tests for User Story 1 (TDD — write FIRST)

> Write these tests FIRST, ensure they FAIL before implementation

- [x] T009 [P] [US1] Integration tests `POST /api/v1/cajas/config` (201 activa, 400 duplicado, 401) in `backend/tests/integration/test_cajas_config_api.py`
- [x] T010 [P] [US1] Integration tests `POST /api/v1/cajas/{id}/archive` (200 archivada, idempotente, 404, historial `GET /movimientos` intacto) in `backend/tests/integration/test_cajas_config_api.py`
- [x] T011 [P] [US1] Integration tests `GET /api/v1/cajas/config` incluye activas y archivadas in `backend/tests/integration/test_cajas_config_api.py`
- [x] T012 [P] [US1] Component tests: alta, archivo, mensajes de éxito/error, listado mixto in `frontend/tests/ConfiguracionCajasPage.test.tsx`

### Implementation for User Story 1 — Backend

- [x] T013 [US1] Implement `POST /config`, `POST /{caja_id}/archive`, `GET /config` with `require_role("secretaria")` in `backend/src/app/api/routes/cajas.py` (declare `/config` before `/{caja_id}` to avoid path clash)
- [x] T014 [US1] Persist `EventoConfiguracionCaja` and log `caja_created` / `caja_archived` without PII extra in `backend/src/app/services/caja_service.py` via `backend/src/app/core/logging.py`

### Implementation for User Story 1 — Frontend

- [x] T015 [P] [US1] Add `listCajasConfig()`, `createCaja()`, `archiveCaja()` in `frontend/src/services/api.ts`
- [x] T016 [US1] Implement configuración (alta + archivo + listado con estado) in `frontend/src/pages/ConfiguracionCajasPage.tsx`
  - wireframe: frontend/src/pages/ConfiguracionCajasPage.tsx
- [x] T017 [US1] Add `/configuracion` behind `SecretariaOnlyRoute` in `frontend/src/App.tsx` and **Configuración** link (`roles: ["secretaria"]`) in `frontend/src/components/layout/Navbar.tsx`
  - wireframe: frontend/src/components/layout/Navbar.tsx

**Checkpoint**: US1 tests verdes. Secretaria puede crear y archivar. MVP. Ruta `/configuracion` y enlace Navbar listos.

---

## Phase 4: User Story 2 — Exclusión de cajas archivadas en operación (Priority: P2)

**Goal**: Desplegables y boxes operativos (Registro, Consulta, Plazos, Impresión) muestran solo cajas activas.

**Independent Test**: Archivar una caja → recargar Registro/Consulta/Plazos/Impresión → no aparece en selectores ni casillas adicionales; `GET /api/v1/cajas` no la incluye. Spec US2. Quickstart §3 pasos 5–6.

### Tests for User Story 2 (TDD — write FIRST)

- [x] T018 [P] [US2] Integration tests `GET /api/v1/cajas` and `GET /api/v1/cajas/operativas` return only `estado=activa` in `backend/tests/integration/test_cajas_config_api.py`
- [x] T019 [P] [US2] Extend `frontend/tests/RegistroCajaPage.test.tsx` so archived cajas are absent from the selector
- [x] T020 [P] [US2] Extend `frontend/tests/ConsultaCajaPage.test.tsx` so archived cajas are absent from dropdowns and additional boxes
- [x] T021 [P] [US2] Extend `frontend/tests/PlazosFijosPage.test.tsx`, `ConsultaPlazosFijosPage.test.tsx`, `ImpresionPage.test.tsx` so selectors only list activas

### Implementation for User Story 2

- [x] T022 [US2] Filter `list_cajas` (`GET ""`) to activas and add `GET /operativas` delegating to `list_cajas_activas` in `backend/src/app/api/routes/cajas.py` (keep `GET /{id}/saldo` and movimientos working for archived ids — FR-006)
- [x] T023 [US2] Keep `getCajas()` on `/api/v1/cajas` in `frontend/src/services/api.ts` so `CajaSelector` / `CajasAdicionalesSelector` and pages consume only activas without per-page filter hacks

**Checkpoint**: US1+US2. Frontend 36/36. Integración cajas config 9/9. SC-001 verificable. Historial de archivadas sigue por id.

---

## Phase 5: User Story 3 — Protección por rol en configuración (Priority: P3)

**Goal**: Escribano (y cualquier rol no secretaria) no puede crear ni archivar; la solapa no es operable para ellos.

**Independent Test**: JWT escribano → POST create/archive → 403; UI no muestra enlace Configuración. Spec US3. Quickstart §4.

### Tests for User Story 3 (TDD — write FIRST)

- [x] T024 [P] [US3] Integration tests: escribano `POST /cajas/config` and `POST /cajas/{id}/archive` → 403; `GET /cajas` allowed in `backend/tests/integration/test_cajas_config_api.py`
- [x] T025 [P] [US3] Navbar tests: secretaria ve Configuración; escribano no in `frontend/tests/Navbar.test.tsx`
- [x] T026 [P] [US3] Route tests: escribano hitting `/configuracion` redirects away in `frontend/tests/ConfiguracionCajasPage.test.tsx` or App-level test colocated with Navbar

### Implementation for User Story 3

- [x] T027 [US3] Confirm write endpoints use `Depends(require_role("secretaria"))` in `backend/src/app/api/routes/cajas.py`; list/saldo remain any authenticated user
- [x] T028 [US3] Confirm `SecretariaOnlyRoute` + Navbar role filter hide configuración from escribano in `frontend/src/App.tsx` and `frontend/src/components/layout/Navbar.tsx`
  - wireframe: frontend/src/components/layout/Navbar.tsx

**Checkpoint**: SC-003. Integración config 10/10. Frontend 39/39. US1–US3 independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Docs, seed/catalog, y verificación quickstart.

- [x] T029 [P] Update Cajas endpoints table in `docs/backend.md` (config, archive, listado operativo vs config)
- [x] T030 [P] Update routes/permisos in `docs/frontend.md` (`/configuracion`, secretaria)
- [x] T031 Stop treating `CAJAS_CATALOG` in `backend/src/app/catalog/cajas.py` as the only closed list: seed keeps 15 activas; altas posteriores no requieren editar el catálogo estático (`backend/src/app/seed.py`)
- [x] T032 Run `specs/006-config-archivo-cajas/quickstart.md` (TDD suites + flujos §3 y §4) and confirm SC-001–SC-004

**Checkpoint**: Docs alineados. Quickstart reproducible.

T032 (2026-08-14): unit `test_caja_service` 8/8; integración `test_cajas_config_api` 10/10; bootstrap 7/7; frontend 39/39.

- SC-001: `GET /cajas` y `/operativas` excluyen archivadas; selectores frontend (registro, consulta, plazos, impresión) no listan archivadas.
- SC-002: alta `POST /cajas/config` → 201 activa; listados operativos leen de DB (sin recatalog estático).
- SC-003: escribano 403 en create/archive; UI redirige `/configuracion`; AppRoutes RBAC.
- SC-004: `ConfiguracionCajasPage` alta + archivo en un formulario (sin pasos extra).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias
- **Foundational (Phase 2)**: Depende de Setup — BLOQUEA user stories
- **User Story 1 (P1)**: Depende de Phase 2 — MVP
- **User Story 2 (P2)**: Depende de Phase 2; se integra con US1 (necesita cajas archivadas para probar exclusión)
- **User Story 3 (P3)**: Depende de Phase 2; cubre RBAC de los mismos endpoints de US1
- **Polish**: Depende de US1–US3

### User Story Dependencies

- **US1 (P1)**: Independiente tras foundation
- **US2 (P2)**: Independiente a nivel de filtro `GET /cajas`; validación E2E más clara tras archivar en US1
- **US3 (P3)**: Independiente a nivel de 403; UI de ocultar solapa puede ir en paralelo a US1 Navbar

### Within Each User Story

- Tests MUST fail before implementation
- Models/service (Phase 2) before endpoints
- Endpoints before frontend clients
- Story complete before next priority when sequential

### Parallel Opportunities

- T002 ∥ T003
- T004 ∥ T006
- T009 ∥ T010 ∥ T011 ∥ T012
- T015 ∥ T013 (después de T012/T009 rojos)
- T018 ∥ T019 ∥ T020 ∥ T021
- T024 ∥ T025 ∥ T026
- T029 ∥ T030

---

## Parallel Example: User Story 1

```bash
# Tests primero (en paralelo):
Task: "Integration POST /cajas/config in backend/tests/integration/test_cajas_config_api.py"
Task: "Integration POST /cajas/{id}/archive in backend/tests/integration/test_cajas_config_api.py"
Task: "Component tests in frontend/tests/ConfiguracionCajasPage.test.tsx"

# Luego implementación:
Task: "Routes in backend/src/app/api/routes/cajas.py"
Task: "API client in frontend/src/services/api.ts"
Task: "Page + Navbar/App"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup
2. Phase 2 Foundational (CRITICAL)
3. Phase 3 US1
4. **STOP and VALIDATE** quickstart §3 (crear/archivar como secretaria)

### Incremental Delivery

1. Setup + Foundational
2. US1 → demo solapa secretaria
3. US2 → selectores solo activas
4. US3 → 403 + UI escribano
5. Polish + quickstart completo

### Parallel Team Strategy

1. Foundation juntos
2. Dev A: US1 backend; Dev B: US1 frontend tests/page
3. US2 filtros API + tests de páginas existentes
4. US3 RBAC fino + Navbar

---

## Notes

- TDD: cada bloque de tests debe fallar antes del código de producción
- `GET /api/v1/cajas` deja de devolver archivadas (rompe el supuesto de “15 fijas” de docs actuales — actualizar en T029/T031)
- No borrar filas ni movimientos al archivar
- Desarchivar restaura `activa` y vuelve a listados operativos (idempotente)
- Commit por tarea o grupo lógico
- `/spec-kitti.tasks.shape` genera Work Units a partir de este archivo y `plan.md`
