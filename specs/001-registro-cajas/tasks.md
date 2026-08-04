# Tasks: Registro de Cajas para Escribanía

**Input**: Design documents from `/specs/001-registro-cajas/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml  
**Testing**: TDD obligatorio (spec.md → Testing Strategy)

**Organization**: Tareas agrupadas por user story. Tests escritos **antes** de implementación.

## Design Reference (UI)

Este proyecto no usa Figma; la constitución (principio III) define los wireframes
`.drawio` en la raíz del repositorio como fuente de diseño. Las tareas UI usan
campo `wireframe:` en lugar de `figma:`.

| Pantalla | Wireframe |
|----------|-----------|
| Registro de Caja | `registro_de_caja.drawio` |
| Consulta de Caja | `consulta_de_caja.drawio` |
| Login | Sin wireframe — formulario estándar mínimo |

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Paralelizable (archivos distintos, sin dependencias incompletas)
- **[USn]**: User story del spec.md

## Path Conventions

- Backend: `backend/src/app/`, tests en `backend/tests/`
- Frontend: `frontend/src/`, tests en `frontend/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Bootstrap reproducible con Docker, PostgreSQL, FastAPI y React.

- [x] T001 Create root `docker-compose.yml` orchestrating postgres (16), backend (8000), frontend (5173) with healthchecks and volume for PG data
- [x] T060 Create root `Makefile` with targets up, down, build, migrate, seed, test, logs wrapping docker-compose (see quickstart.md)
- [x] T002 [P] Create `backend/pyproject.toml` with FastAPI, SQLAlchemy 2, Alembic, pytest, httpx, python-jose, passlib dependencies
- [x] T003 [P] Create `frontend/package.json` with React 18, TypeScript, Vite, React Router, Vitest, Testing Library
- [x] T004 Create `backend/src/app/main.py` with FastAPI app, CORS, `/health` endpoint
- [x] T005 [P] Create `frontend/src/main.tsx` and `frontend/src/App.tsx` with React Router shell
- [x] T006 Create `.env.example` documenting DATABASE_URL, JWT_SECRET, JWT_EXPIRE_HOURS, ADMIN credentials
- [x] T007 [P] Create `backend/Dockerfile` and `frontend/Dockerfile` for docker-compose
- [x] T008 [P] Create smoke test `backend/tests/test_health.py` (TDD baseline — must pass after T004)

**Checkpoint**: `make up` levanta stack healthy; `pytest backend/tests/test_health.py` green.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestructura DB, sesión y utilidades compartidas. **Bloquea todas las user stories.**

- [x] T009 Create `backend/src/app/core/config.py` loading settings from environment variables
- [x] T010 Create `backend/src/app/db/session.py` and `backend/src/app/db/base.py` for SQLAlchemy engine and Base
- [x] T011 Configure `backend/alembic.ini` and `backend/alembic/env.py` for async/sync migrations with PostgreSQL
- [x] T012 [P] Create `backend/tests/conftest.py` with test DB fixture and httpx AsyncClient
- [x] T013 [P] Create `frontend/src/services/api.ts` base HTTP client with Authorization header support
- [x] T014 Register API routers placeholder in `backend/src/app/main.py` under `/api/v1` prefix

**Checkpoint**: Alembic connects to DB; test client fixture works.

---

## Phase 3: User Story 1 — Iniciar Sesión (Priority: P1) 🎯 MVP

**Goal**: Login usuario/contraseña, JWT 8h, protección de rutas por rol.

**Independent Test**: Login admin/admin accede; credenciales inválidas rechazadas;
visitante sin token redirigido a `/login`; token expirado tras 8h rechazado.

### Tests for User Story 1 (TDD — write FIRST)

- [x] T015 [P] [US1] Integration test login success and invalid credentials in `backend/tests/integration/test_auth.py`
- [x] T016 [P] [US1] Integration test protected route 401 without token in `backend/tests/integration/test_auth.py`
- [x] T017 [P] [US1] Integration test JWT expiration after 8h in `backend/tests/integration/test_auth.py`
- [x] T018 [P] [US1] Component test LoginPage submit flow in `frontend/tests/LoginPage.test.tsx`

### Implementation for User Story 1

- [x] T019 [P] [US1] Create `Usuario` model in `backend/src/app/models/usuario.py` per data-model.md
- [x] T020 [US1] Create Alembic migration `backend/alembic/versions/001_create_usuario.py`
- [x] T021 [P] [US1] Implement bcrypt + JWT helpers in `backend/src/app/core/security.py` (8h expiry)
- [x] T022 [US1] Implement `POST /api/v1/auth/login` in `backend/src/app/api/routes/auth.py` per contracts/openapi.yaml
- [x] T023 [US1] Implement `get_current_user` and `require_role` in `backend/src/app/api/deps.py`
- [x] T024 [US1] Create seed script `backend/src/app/seed.py` for admin/admin (rol secretaria)
- [x] T025 [US1] Implement `frontend/src/hooks/useAuth.ts` for token storage and role state
- [x] T026 [US1] Implement `frontend/src/pages/LoginPage.tsx` with username/password form
- [x] T027 [US1] Add route guards in `frontend/src/App.tsx` redirecting unauthenticated users to `/login`

**Checkpoint**: All US1 tests pass; manual login flow works.

---

## Phase 4: User Story 2 — Registrar Movimientos de Caja (Priority: P2)

**Goal**: Secretaria registra entradas/salidas; subtotales acumulados; historial paginado (20, más recientes primero).

**Independent Test**: Secretaria registra entrada y salida; subtotal correcto (incl.
negativo); página 1 muestra 20 más recientes; escribano no puede POST.

### Tests for User Story 2 (TDD — write FIRST)

- [x] T028 [P] [US2] Unit tests subtotal algorithm (entrada, salida, negativo, primer movimiento) in `backend/tests/unit/test_subtotal_calculation.py`
- [x] T029 [P] [US2] Integration tests MovimientoService transaction in `backend/tests/integration/test_movimiento_service.py`
- [x] T030 [P] [US2] Contract tests POST/GET movimientos per `specs/001-registro-cajas/contracts/openapi.yaml` in `backend/tests/integration/test_movimientos_api.py`
- [x] T031 [P] [US2] Integration test escribano POST movimientos returns 403 in `backend/tests/integration/test_movimientos_api.py`
- [x] T032 [P] [US2] Component tests RegistroCajaPage in `frontend/tests/RegistroCajaPage.test.tsx`

### Implementation for User Story 2 — Backend

- [x] T033 [P] [US2] Create `Caja` model in `backend/src/app/models/caja.py`
- [x] T034 [P] [US2] Create `Movimiento` model in `backend/src/app/models/movimiento.py`
- [x] T035 [US2] Create Alembic migration `backend/alembic/versions/002_create_caja_movimiento.py` with indexes
- [x] T036 [US2] Extend `backend/src/app/seed.py` to seed 15 cajas del catálogo
- [x] T037 [US2] Implement create/update/delete and `recalculate_subtotals()` in `backend/src/app/services/movimiento_service.py` with `SELECT FOR UPDATE`
- [x] T038 [P] [US2] Create Pydantic schemas in `backend/src/app/schemas/movimiento.py` and `backend/src/app/schemas/caja.py`
- [x] T039 [US2] Implement `GET /api/v1/cajas` in `backend/src/app/api/routes/cajas.py`
- [x] T040 [US2] Implement `GET /api/v1/cajas/{id}/saldo` in `backend/src/app/api/routes/cajas.py`
- [x] T041 [US2] Implement `GET /api/v1/cajas/{id}/movimientos` with page_size=20, newest first in `backend/src/app/api/routes/movimientos.py`
- [x] T042 [US2] Implement `POST /api/v1/cajas/{id}/movimientos` (secretaria only) in `backend/src/app/api/routes/movimientos.py`

### Implementation for User Story 2 — Frontend

- [x] T043 [P] [US2] Create `frontend/src/components/CajaSelector.tsx` loading cajas from API
  - wireframe: registro_de_caja.drawio
- [x] T044 [P] [US2] Create `frontend/src/components/MovimientoForm.tsx` with descripción, monto, Entrada/Salida buttons
  - wireframe: registro_de_caja.drawio
- [x] T045 [P] [US2] Create `frontend/src/components/MovimientoTable.tsx` with Descripción/Monto/Subtotal/Fecha, green/red styling, edit/delete actions when `editable`
  - wireframe: registro_de_caja.drawio
- [x] T046 [P] [US2] Create `frontend/src/components/Pagination.tsx` for 20-record pages
  - wireframe: registro_de_caja.drawio
- [x] T047 [US2] Implement `frontend/src/pages/RegistroCajaPage.tsx` assembling layout per wireframe
  - wireframe: registro_de_caja.drawio
- [x] T048 [US2] Wire API calls in `frontend/src/services/api.ts` for list/create movimientos and saldo

**Checkpoint**: US2 backend + frontend tests pass; secretaria registra y ve historial paginado.

---

## Phase 4b: Amend — Edición / Eliminación 24h (US2 extensión)

**Goal**: Secretaria edita o elimina movimientos < 24h; recálculo de subtotales; rechazo fuera de ventana.

**Independent Test**: PATCH movimiento < 24h OK y recalcula; DELETE < 24h OK; operación > 24h → 422; escribano → 403.

### Tests (TDD — write FIRST)

- [x] T061 [P] [US2] Integration tests PATCH/DELETE within 24h and recalc cascade in `backend/tests/integration/test_movimiento_edit_delete.py`
- [x] T062 [P] [US2] Integration test reject edit/delete after 24h (422) in `backend/tests/integration/test_movimiento_edit_delete.py`
- [x] T063 [P] [US2] Integration test escribano PATCH/DELETE returns 403 in `backend/tests/integration/test_movimiento_edit_delete.py`

### Implementation

- [x] T064 [US2] Add Alembic migration `backend/alembic/versions/003_movimiento_updated_by.py` for `updated_by` column
- [x] T065 [US2] Implement `PATCH /api/v1/cajas/{id}/movimientos/{movimientoId}` in `backend/src/app/api/routes/movimientos.py` per openapi v1.1
- [x] T066 [US2] Implement `DELETE /api/v1/cajas/{id}/movimientos/{movimientoId}` in `backend/src/app/api/routes/movimientos.py`
- [x] T067 [US2] Add `editable` flag to movimiento API responses in `backend/src/app/schemas/movimiento.py`
- [x] T068 [US2] Wire edit/delete UI and API calls in `frontend/src/components/MovimientoTable.tsx` and `frontend/src/services/api.ts`
  - wireframe: registro_de_caja.drawio

**Checkpoint**: SC-007, SC-008 pass; amend RFC integrado.

---

## Phase 5: User Story 3 — Consultar Estado de Caja (Priority: P3)

**Goal**: Escribano y secretaria consultan saldo e historial de cualquier caja; sin controles de escritura.

**Independent Test**: Escribano consulta las 15 cajas; no ve formulario de registro;
secretaria también puede consultar; mismos datos que registro.

### Tests for User Story 3 (TDD — write FIRST)

- [x] T049 [P] [US3] Integration test escribano can GET saldo and movimientos for all cajas in `backend/tests/integration/test_consulta_rbac.py`
- [x] T050 [P] [US3] Component test ConsultaCajaPage read-only (no Entrada/Salida) in `frontend/tests/ConsultaCajaPage.test.tsx`

### Implementation for User Story 3

- [x] T051 [US3] Implement `frontend/src/pages/ConsultaCajaPage.tsx` with selector, Consulta button, VALOR DE CAJA banner, read-only table
  - wireframe: consulta_de_caja.drawio
- [x] T052 [US3] Reuse `CajaSelector`, `MovimientoTable`, `Pagination` in consulta mode in `frontend/src/pages/ConsultaCajaPage.tsx`
  - wireframe: consulta_de_caja.drawio
- [x] T053 [US3] Add role-based navigation in `frontend/src/App.tsx` (secretaria → registro+consulta; escribano → consulta only)
- [x] T054 [US3] Hide Registro route and MovimientoForm for escribano role in `frontend/src/App.tsx`

**Checkpoint**: US3 tests pass; escribano solo consulta; SC-003, SC-004, SC-006 satisfied.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Seguridad, logging, validación quickstart end-to-end.

- [x] T055 [P] Implement structured logging in `backend/src/app/core/logging.py` (auth failures, writes; no PII)
- [x] T056 Add security headers and CORS allowlist in `backend/src/app/main.py`
- [x] T057 [P] Add `.gitignore` entries for `.env`, `__pycache__`, `node_modules`, `.venv`
- [x] T058 Validate full walkthrough in `specs/001-registro-cajas/quickstart.md` and fix doc gaps if any
- [x] T059 [P] Run full test suite: `pytest` backend + `npm test` frontend; fix regressions

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias
- **Foundational (Phase 2)**: Depende de Phase 1 — **bloquea todas las user stories**
- **US1 (Phase 3)**: Depende de Phase 2
- **US2 (Phase 4)**: Depende de US1 (auth requerida para API)
- **US3 (Phase 5)**: Depende de US2 backend API (GET endpoints); frontend puede paralelizarse tras T041
- **Polish (Phase 6)**: Depende de US1 + US2 + US3

### User Story Dependencies

- **US1 (P1)**: Tras Foundational — sin dependencia de otras stories
- **US2 (P2)**: Tras US1 — necesita auth para endpoints protegidos
- **US3 (P3)**: Tras US2 backend (datos + GET); UI independiente de US2 frontend

### Within Each User Story (TDD)

1. Tests MUST fail before implementation
2. Models → services → routes → frontend components → pages
3. Checkpoint al completar cada fase

### Parallel Opportunities

- Phase 1: T002, T003, T005, T007, T008 en paralelo tras T001; T060 tras T001
- Phase 2: T012, T013 en paralelo
- US1 tests: T015–T018 en paralelo
- US2 models: T033, T034 en paralelo; componentes T043–T046 en paralelo
- US3 tests: T049, T050 en paralelo
- Polish: T055, T057, T059 en paralelo

---

## Parallel Example: User Story 2 Backend

```bash
# Tests primero (deben fallar):
pytest backend/tests/unit/test_subtotal_calculation.py
pytest backend/tests/integration/test_movimiento_service.py
pytest backend/tests/integration/test_movimientos_api.py

# Modelos en paralelo:
# T033 backend/src/app/models/caja.py
# T034 backend/src/app/models/movimiento.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 + Phase 2
2. Complete Phase 3 (US1)
3. **STOP and VALIDATE**: Login flow end-to-end
4. Demo MVP autenticado

### Incremental Delivery

1. Setup + Foundational → base lista
2. US1 → login seguro (MVP)
3. US2 → registro de caja operativo
4. US3 → consulta para escribanos
5. Polish → producción-ready local

### Suggested MVP Scope

**User Story 1 (P1)** — autenticación JWT + protección de rutas.

---

## Task Summary

| Phase | Tasks | Story |
|-------|-------|-------|
| Setup | T001–T008, T060 | — |
| Foundational | T009–T014 | — |
| US1 Login | T015–T027 | P1 |
| US2 Registro | T028–T048 | P2 |
| US2 Amend 24h | T061–T068 | P2 |
| US3 Consulta | T049–T054 | P3 |
| Polish | T055–T059 | — |
| **Total** | **68** | |

**Parallel opportunities**: 22 tasks marked [P]  
**Independent test criteria**: Documented per user story phase header
