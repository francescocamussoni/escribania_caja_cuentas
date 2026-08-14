# Tasks: Cambio de Contraseña y Consulta Conjunta de Cajas

**Input**: Design documents from `/specs/005-cambio-clave-consulta-conjunto/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml  
**Testing**: TDD obligatorio (spec.md → Testing Strategy)

**Organization**: Tareas agrupadas por user story. Tests escritos **antes** de implementación.

## Design Reference (UI)

Este proyecto no usa Figma para esta feature. La constitución (principio III) define
`consulta_de_caja.drawio` como referencia de Consulta. Login y Navbar no tienen frame
nuevo: se extienden las pantallas existentes. Las tareas UI usan campo `wireframe:`
(patrón features 001, 003 y 004).

| Pantalla | Wireframe / referencia |
|----------|------------------------|
| Login (cambio de clave) | `frontend/src/pages/LoginPage.tsx` (misma tarjeta; enlace reemplaza el form) |
| Sección de usuario | `frontend/src/components/layout/Navbar.tsx` |
| Consulta una caja / conjunto | `consulta_de_caja.drawio` · `frontend/src/pages/ConsultaCajaPage.tsx` |
| Casillas adicionales | `frontend/src/components/CajasAdicionalesSelector.tsx` (título distinto; Registro no cambia) |

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Paralelizable (archivos distintos, sin dependencias incompletas)
- **[USn]**: User story del spec.md

## Path Conventions

- Backend: `backend/src/app/`, tests en `backend/tests/`
- Frontend: `frontend/src/`, tests en `frontend/tests/`
- Migración: `backend/alembic/versions/005_usuario_password_changed_at.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline verde y contrato alineado antes de TDD.

- [x] T001 Verify branch `005-cambio-clave-consulta-conjunto` and baseline `make test-backend` / `make test-frontend` pass
- [x] T002 [P] Cross-check `POST /api/v1/auth/change-password` and `POST /api/v1/auth/me/password` in `specs/005-cambio-clave-consulta-conjunto/contracts/openapi.yaml` against mount pattern in `backend/src/app/api/router.py` and `backend/src/app/api/routes/auth.py`
- [x] T003 [P] Add Alembic revision `password_changed_at` TIMESTAMPTZ NULL in `backend/alembic/versions/005_usuario_password_changed_at.py` per `data-model.md`

**Checkpoint**: Branch correcta. Frontend 17/17 verde. Backend 102 passed / 1 failed preexistente (`test_post_rejects_monto_a_vencimiento_less_than_ingresado` espera 400 y recibe 422 — fuera de alcance 005). Contrato alineado en `contracts/mount-alignment.md`. Migración Alembic 005 agregada (modelo ORM en T005).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Columna, claim JWT `iat` y corte de sesión. **Bloquea user stories de contraseña.**

**⚠️ CRITICAL**: US1 y US2 no pueden implementarse hasta completar esta fase. US3/US4 no dependen del JWT cutover pero el flujo del comando exige foundation antes de stories.

- [x] T004 [P] Unit tests: token con `iat` anterior a `password_changed_at` se rechaza; `iat` posterior se acepta; usuario con `password_changed_at` null acepta token in `backend/tests/unit/test_auth_token_cutover.py`
- [x] T005 Add `password_changed_at: Mapped[datetime | None]` in `backend/src/app/models/usuario.py`
- [x] T006 Add `iat` (UTC) to payload in `create_access_token` in `backend/src/app/core/security.py`; expose `iat` from `decode_access_token`
- [x] T007 Reject tokens when `password_changed_at` is set and `iat` is missing or earlier in `get_current_user` in `backend/src/app/api/deps.py` (401 `UNAUTHORIZED_MESSAGE`)
- [x] T008 [P] Add `ChangePasswordPublicRequest` and `ChangePasswordAuthenticatedRequest` with `extra="forbid"`, min 8, confirm match in `backend/src/app/schemas/auth.py`

**Checkpoint**: 15 tests de foundation + login existentes verdes. JWT incluye `iat`; corte por `password_changed_at` en `get_current_user`. DTOs listos. Migración 005 aplicada en el Postgres de compose.

---

## Phase 3: User Story 1 — Cambiar contraseña desde el login (Priority: P1) 🎯 MVP

**Goal**: Enlace **Cambiar contraseña** reemplaza el formulario de ingreso; POST público 204; no emite token; login solo con la nueva clave.

**Independent Test**: Quickstart §2 curl público + login con nueva clave; UI `http://localhost:5173/login` enlace → form cambio → éxito vuelve a ingresar. Spec US1.

### Tests for User Story 1 (TDD — write FIRST)

> Write these tests FIRST, ensure they FAIL before implementation

- [x] T009 [P] [US1] Unit tests `change_password_public` (éxito hash, rechazo igual a actual, 401 genérico si user/clave mal) in `backend/tests/unit/test_auth_password.py`
- [x] T010 [P] [US1] Integration tests `POST /api/v1/auth/change-password` (204, 401 genérico igual que login, 422 confirm/min length, login viejo falla) in `backend/tests/integration/test_auth_change_password.py`
- [x] T011 [P] [US1] Component tests: enlace reemplaza form, cancelar vuelve a ingresar, éxito muestra mensaje y form login in `frontend/tests/LoginPage.test.tsx`

### Implementation for User Story 1 — Backend

- [x] T012 [US1] Implement `change_password` (verify current, hash new, set `password_changed_at`) in `backend/src/app/services/auth_service.py`
- [x] T013 [US1] Implement `POST /change-password` in `backend/src/app/api/routes/auth.py` returning 204; log `password_change_success` / `password_change_failed` without secrets via `backend/src/app/core/logging.py`

### Implementation for User Story 1 — Frontend

- [x] T014 [P] [US1] Add `postChangePasswordPublic()` in `frontend/src/services/api.ts`
- [x] T015 [US1] Implement login toggle: enlace **Cambiar contraseña**, form (usuario, actual, nueva, confirmación), cancelar, éxito 204 in `frontend/src/pages/LoginPage.tsx`
  - wireframe: frontend/src/pages/LoginPage.tsx

**Checkpoint**: US1 tests green (backend 12 + frontend LoginPage 4). SC-001/SC-003 verificables. MVP de clave.

---

## Phase 4: User Story 2 — Cambiar contraseña desde la sección de usuario (Priority: P2)

**Goal**: Click en el nombre arriba a la derecha abre menú con cambio de clave; POST autenticado; token previo 401; cliente hace logout y redirige a `/login`.

**Independent Test**: Login → click username → cambiar clave → redirige a login; `GET /cajas` con token viejo → 401. Spec US2. Quickstart §2 autenticado.

### Tests for User Story 2 (TDD — write FIRST)

- [x] T016 [P] [US2] Integration tests `POST /api/v1/auth/me/password` (204, 401 current wrong, 401 unauthenticated, old JWT 401 on `GET /cajas`, escribano OK) in `backend/tests/integration/test_auth_change_password.py`
- [x] T017 [P] [US2] Component tests: click username abre sección, submit llama API, logout on 204 in `frontend/tests/Navbar.test.tsx`

### Implementation for User Story 2

- [x] T018 [US2] Implement `POST /me/password` using JWT subject only (no username in body) in `backend/src/app/api/routes/auth.py` via `auth_service.py`
- [x] T019 [P] [US2] Add `postChangePasswordMe()` in `frontend/src/services/api.ts` and `changePassword` + `logout` after 204 in `frontend/src/hooks/useAuth.tsx`
- [x] T020 [US2] Implement user section on username click (cambiar contraseña + salir) in `frontend/src/components/layout/Navbar.tsx`
  - wireframe: frontend/src/components/layout/Navbar.tsx

**Checkpoint**: US1+US2 green; SC-002/SC-004; anti-IDOR (no se cambia clave ajena).

---

## Phase 5: User Story 3 — Consultar una sola caja (Priority: P3)

**Goal**: Consulta individual intacta. Debajo del desplegable existe **Ver en conjunto con otras cajas**; sin marcas, el resultado es el de hoy.

**Independent Test**: Consulta Ebel sin casillas → valor + historial 20/página como tests actuales. Spec US3.

### Tests for User Story 3 (TDD — write FIRST)

- [x] T021 [P] [US3] Extend tests: section title visible; zero adicionales → same `saldo` + `movimientos` calls and layout in `frontend/tests/ConsultaCajaPage.test.tsx`

### Implementation for User Story 3

- [x] T022 [P] [US3] Add optional `summary` prop defaulting to «Registrar también en otras cajas» in `frontend/src/components/CajasAdicionalesSelector.tsx` (Registro unchanged)
  - wireframe: frontend/src/components/CajasAdicionalesSelector.tsx
- [x] T023 [US3] Render «Ver en conjunto con otras cajas» under `CajaSelector` in `frontend/src/pages/ConsultaCajaPage.tsx`; Consulta with empty selection keeps current single-caja fetch/UI
  - wireframe: consulta_de_caja.drawio

**Checkpoint**: Tests de consulta individual siguen verdes; Registro no cambia de copy.

---

## Phase 6: User Story 4 — Consultar varias cajas en conjunto (Priority: P4)

**Goal**: Con casillas marcadas: N saldos (fail-all), N solapas **cerradas**, primera = desplegable, resto orden catálogo; historial lazy al expandir; paginación independiente; FR-022 sin duplicar principal.

**Independent Test**: Ebel + Martin + Gabriel → tres solapas cerradas, Ebel primero, Martin antes que Gabriel; un saldo 404 aborta todo. Spec US4.

### Tests for User Story 4 (TDD — write FIRST)

- [x] T024 [P] [US4] Tests: Promise.all saldos fail-all; orden principal+catálogo; `details` closed; expand fetches movimientos of that caja only; page change isolated; dropdown move removes from adicionales in `frontend/tests/ConsultaCajaPage.test.tsx`

### Implementation for User Story 4

- [x] T025 [P] [US4] Implement collapsible per-caja panel (nombre, subtotal, historial lazy + Pagination) in `frontend/src/components/CajaConsultaSolapa.tsx`
  - wireframe: consulta_de_caja.drawio
- [x] T026 [US4] Implement joint consulta in `frontend/src/pages/ConsultaCajaPage.tsx`: parallel `GET .../saldo`, discard on any failure, solapas via `CajaConsultaSolapa`, lazy `GET .../movimientos`
  - wireframe: consulta_de_caja.drawio

**Checkpoint**: US3+US4 green; SC-005/SC-006/SC-007.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Docs operativos y validación E2E.

- [x] T027 [P] Update auth endpoints, JWT `iat`, and `password_changed_at` in `docs/backend.md`
- [x] T028 [P] Update login enlace, Navbar user section, and consulta conjunta in `docs/frontend.md`
- [x] T029 [P] Document self-service password change (keep EC2 script as fallback) in `docs/usuarios-y-contraseñas.md`
- [x] T030 Run `make test-backend` and `make test-frontend`; walk `specs/005-cambio-clave-consulta-conjunto/quickstart.md` §2–§3

**Checkpoint**: Quickstart completo; listo para `/spec-kitti.tasks.shape` o implementación.

---

## Phase 8: Amend — Valor en conjunto (FR-018a)

**Purpose**: Mostrar arriba de las solapas la suma de los `saldo_actual` del intento conjunto. T024/T026/T028 permanecen `done`.

- [x] T031 [P] [US4] [Refactor] Tests: joint consulta shows **Valor en conjunto** equal to the sum of included `saldo_actual`; fail-all hides the total (modifies T024) in `frontend/tests/ConsultaCajaPage.test.tsx`
- [x] T032 [US4] [Refactor] Render **Valor en conjunto** above solapas from summed `saldo_actual` (no new API) in `frontend/src/pages/ConsultaCajaPage.tsx` (modifies T026)
  - wireframe: consulta_de_caja.drawio
- [x] T033 [P] Document **Valor en conjunto** in `docs/frontend.md` (modifies T028)

**Checkpoint**: SC-006 con total conjunto; consulta individual sin cambio.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias
- **Foundational (Phase 2)**: Depende de Phase 1 — **bloquea** US1/US2
- **US1 (Phase 3)**: Depende de Phase 2 — **MVP clave**
- **US2 (Phase 4)**: Depende de `auth_service` de US1
- **US3 (Phase 5)**: Independiente de US1/US2 (API cajas existente); puede empezar tras Phase 1
- **US4 (Phase 6)**: Depende de US3 (sección conjunta vacía)
- **Polish (Phase 7)**: Depende de las stories entregadas
- **Amend total conjunto (Phase 8)**: Depende de US4 (T026 done)

### User Story Dependencies

| Story | Depende de | Independiente en |
|-------|------------|------------------|
| US1 P1 | Phase 2 | Cambio de clave en login |
| US2 P2 | US1 servicio/rutas auth | Menú usuario + invalidación JWT |
| US3 P3 | Phase 1 (API cajas) | Consulta una caja + sección vacía |
| US4 P4 | US3 | Consulta conjunta |

### Parallel Opportunities

- Phase 1: T002 ∥ T003
- Phase 2: T004 ∥ T008
- US1 tests: T009 ∥ T010 ∥ T011
- US2 tests: T016 ∥ T017
- US3 puede paralelizarse con US1 si hay dos personas
- Polish: T027 ∥ T028 ∥ T029

### Parallel Example: User Story 1

```bash
# Tests en rojo (paralelo):
pytest backend/tests/unit/test_auth_password.py
pytest backend/tests/integration/test_auth_change_password.py -k public
cd frontend && npm test -- LoginPage
```

### Parallel Example: User Story 4

```bash
cd frontend && npm test -- ConsultaCajaPage
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 → Phase 2 → Phase 3
2. **STOP**: cambio de clave desde login operativo
3. Demo: enlace, 204, login con clave nueva

### Incremental Delivery

1. US1 → login change password (MVP)
2. US2 → menú usuario + corte de sesión
3. US3 → consulta individual sin regresión + sección
4. US4 → conjunto
5. Phase 7 → docs y quickstart
6. Phase 8 → Valor en conjunto (amend)

### Suggested MVP Scope

**User Story 1** (T001–T015): cambio de contraseña en la pantalla de login.

---

## Notes

- Sin Figma: usar `wireframe:` en tareas UI (ver Design Reference)
- TDD: tests en **rojo** antes de cada bloque de implementación
- Confirmación de clave se valida en Pydantic y en UI
- Consulta conjunta **no** añade endpoints; fail-all en el cliente; Valor en conjunto = suma de `saldo_actual`
- Registro de caja no debe cambiar el texto del selector adicional (prop `summary`)

---

## Task Summary

| Phase | Tasks | Story |
|-------|-------|-------|
| 1 Setup | T001–T003 | — |
| 2 Foundational | T004–T008 | — |
| 3 US1 Login password | T009–T015 | P1 MVP |
| 4 US2 Navbar password | T016–T020 | P2 |
| 5 US3 Consulta una caja | T021–T023 | P3 |
| 6 US4 Consulta conjunto | T024–T026 | P4 |
| 7 Polish | T027–T030 | — |
| 8 Amend Valor en conjunto | T031–T033 | P4 |
| **Total** | **33** | |
