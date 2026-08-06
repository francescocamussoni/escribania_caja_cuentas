# Tasks: Plazos Fijos por Caja

**Input**: Design documents from `/specs/003-plazos-fijos/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml  
**Testing**: TDD obligatorio (spec.md → Testing Strategy)

**Organization**: Tareas agrupadas por user story. Tests escritos **antes** de implementación.

## Design Reference (UI)

Este proyecto no usa Figma para esta feature; el spec (FR-002) exige paridad visual con
Registro y Consulta de Caja. La constitución (principio III) define wireframes `.drawio`
como referencia. Las tareas UI usan campo `wireframe:` (patrón feature 001).

| Pantalla | Wireframe / referencia código |
|----------|-------------------------------|
| Plazos Fijos (gestión) | `registro_de_caja.drawio` · paridad `frontend/src/pages/RegistroCajaPage.tsx` |
| Consulta Plazos Fijos | `consulta_de_caja.drawio` · paridad `frontend/src/pages/ConsultaCajaPage.tsx` |

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Paralelizable (archivos distintos, sin dependencias incompletas)
- **[USn]**: User story del spec.md

## Path Conventions

- Backend: `backend/src/app/`, tests en `backend/tests/`
- Frontend: `frontend/src/`, tests en `frontend/tests/`
- Migración siguiente disponible: `004_plazo_fijo.py` (003 ya usado por movimiento_updated_by)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verificar stack existente (001) y alinear contrato antes de implementar.

- [x] T001 Verify branch `003-plazos-fijos` and baseline `make test` passes on current stack (001-registro-cajas operativo)
- [x] T002 [P] Cross-check endpoint paths in `specs/003-plazos-fijos/contracts/openapi.yaml` against mount pattern in `backend/src/app/api/router.py`

**Checkpoint**: Stack local healthy; contrato revisado.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Utilidad compartida para límite activo/vencido (calendario Argentina). **Bloquea user stories.**

- [x] T003 [P] Create `backend/src/app/core/dates.py` with `today_ar()` returning date in `America/Argentina/Buenos_Aires` per research.md R3

**Checkpoint**: Helper de fecha listo para servicio y agregaciones.

---

## Phase 3: User Story 1 — Gestionar Plazos Fijos (Priority: P1) 🎯 MVP

**Goal**: Secretaria registra, edita y elimina plazos fijos por caja (sin ventana 24h); listado
paginado (futuros primero, vencidos al final); panel de dos totales solo plazos activos.

**Independent Test**: Login secretaria → `/plazos-fijos` → crear plazo con tres campos → ver
tabla y resumen → editar/eliminar plazo antiguo → paginación correcta. API: CRUD + resumen
vía `quickstart.md` §2.

### Tests for User Story 1 (TDD — write FIRST)

- [x] T004 [P] [US1] Unit tests list order (futuros asc, vencidos desc, desempate created_at) in `backend/tests/unit/test_plazo_fijo_order.py`
- [x] T005 [P] [US1] Unit tests validation (montos > 0, monto_a_vencimiento ≥ ingresado) in `backend/tests/unit/test_plazo_fijo_validation.py`
- [x] T006 [P] [US1] Integration tests POST/PATCH/DELETE/list/resumen secretaria in `backend/tests/integration/test_plazos_fijos_api.py` per `contracts/openapi.yaml`

### Implementation for User Story 1 — Backend

- [x] T007 [P] [US1] Create `PlazoFijo` model in `backend/src/app/models/plazo_fijo.py` per `data-model.md`
- [x] T008 [US1] Create Alembic migration `backend/alembic/versions/004_plazo_fijo.py` with CHECK constraints and index `idx_plazo_fijo_caja_vencimiento`
- [x] T009 [US1] Register `PlazoFijo` in `backend/src/app/models/__init__.py` and optional relationship on `backend/src/app/models/caja.py`
- [x] T010 [P] [US1] Create Pydantic schemas in `backend/src/app/schemas/plazo_fijo.py` (create/update/response/resumen/paginated)
- [x] T011 [US1] Implement `PlazoFijoService` (create, update, delete, list paginated, get_resumen) in `backend/src/app/services/plazo_fijo_service.py` using `today_ar()` and order SQL from data-model.md
- [x] T012 [US1] Implement routes in `backend/src/app/api/routes/plazos_fijos.py` — `GET/POST /cajas/{id}/plazos-fijos`, `GET /cajas/{id}/plazos-fijos/resumen`, `PATCH/DELETE /cajas/{id}/plazos-fijos/{id}` with `require_role("secretaria")` on writes
- [x] T013 [US1] Register plazos fijos router in `backend/src/app/api/router.py` under `/cajas` prefix; add security logging on writes

### Tests for User Story 1 — Frontend (TDD — write FIRST)

- [x] T014 [P] [US1] Component tests create/edit/delete/pagination/resumen in `frontend/tests/PlazosFijosPage.test.tsx`

### Implementation for User Story 1 — Frontend

- [x] T015 [P] [US1] Create `frontend/src/components/PlazosFijosResumenPanel.tsx` (dos totales activos)
  - wireframe: registro_de_caja.drawio
- [x] T016 [P] [US1] Create `frontend/src/components/PlazoFijoForm.tsx` (monto ingresado, fecha vencimiento, monto a vencimiento)
  - wireframe: registro_de_caja.drawio
- [x] T017 [P] [US1] Create `frontend/src/components/PlazoFijoTable.tsx` with edit/delete actions and `window.confirm` on delete
  - wireframe: registro_de_caja.drawio
- [x] T018 [US1] Implement `frontend/src/pages/PlazosFijosPage.tsx` (auto-load on caja change, reuse `CajaSelector`, `Pagination`)
  - wireframe: registro_de_caja.drawio
- [x] T019 [US1] Add API types and fetchers in `frontend/src/services/api.ts` for plazos fijos CRUD, list, resumen
- [x] T020 [US1] Add route `/plazos-fijos` with `SecretariaOnlyRoute` in `frontend/src/App.tsx` and Navbar link (solo secretaria) in `frontend/src/components/layout/Navbar.tsx`

**Checkpoint**: US1 tests green; secretaria gestiona plazos end-to-end; SC-001, SC-002, SC-005, SC-006a.

---

## Phase 4: User Story 2 — Consultar Plazos Fijos (Priority: P2)

**Goal**: Escribano y secretaria consultan plazos fijos por caja (botón Consulta); sin
escritura; mismos datos y resumen que gestión.

**Independent Test**: Login escribano → `/consulta-plazos-fijos` → seleccionar caja → Consulta
→ ver resumen dual + tabla sin editar/eliminar. POST como escribano → 403.

### Tests for User Story 2 (TDD — write FIRST)

- [x] T021 [P] [US2] Integration tests escribano GET list/resumen OK and POST/PATCH/DELETE 403 in `backend/tests/integration/test_plazos_fijos_api.py`
- [x] T022 [P] [US2] Component test read-only consulta flow in `frontend/tests/ConsultaPlazosFijosPage.test.tsx`

### Implementation for User Story 2

- [x] T023 [US2] Implement `frontend/src/pages/ConsultaPlazosFijosPage.tsx` (selector + Consulta button + resumen + read-only table)
  - wireframe: consulta_de_caja.drawio
- [x] T024 [US2] Reuse `CajaSelector`, `PlazosFijosResumenPanel`, `PlazoFijoTable` (read-only), `Pagination` in `frontend/src/pages/ConsultaPlazosFijosPage.tsx`
  - wireframe: consulta_de_caja.drawio
- [x] T025 [US2] Add route `/consulta-plazos-fijos` (secretaria + escribano) in `frontend/src/App.tsx`
- [x] T026 [US2] Add Navbar link "Consulta plazos fijos" for secretaria and escribano in `frontend/src/components/layout/Navbar.tsx`

**Checkpoint**: US2 tests green; escribano consulta 15 cajas; SC-003, SC-004, SC-006.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentación, validación E2E y regresiones.

- [x] T027 [P] Update `docs/frontend.md` with routes `/plazos-fijos` and `/consulta-plazos-fijos` and permisos
- [x] T028 Validate walkthrough in `specs/003-plazos-fijos/quickstart.md` (curl + UI manual)
- [x] T029 [P] Run full suite `make test` and fix regressions

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias
- **Foundational (Phase 2)**: Depende de Phase 1 — **bloquea user stories**
- **US1 (Phase 3)**: Depende de Phase 2
- **US2 (Phase 4)**: Depende de US1 backend (GET endpoints) + US1 frontend components reutilizables
- **Polish (Phase 5)**: Depende de US1 + US2

### User Story Dependencies

- **US1 (P1)**: Tras Phase 2 — sin dependencia de US2; **MVP**
- **US2 (P2)**: Tras US1 backend (T013); frontend consulta puede empezar tras T015–T017 (componentes)

### Within Each User Story

- Tests MUST fail before implementation (TDD)
- Model → migration → schemas → service → routes → frontend API → UI
- US1 completo antes de cerrar MVP

### Parallel Opportunities

- T004, T005, T006 en paralelo (tests backend US1)
- T007, T010 en paralelo (model + schemas)
- T015, T016, T017 en paralelo (componentes frontend US1)
- T021, T022 en paralelo (tests US2)
- Tras US1 backend: US2 frontend (T023–T026) paralelo a polish prep si otro dev

---

## Parallel Example: User Story 1

```bash
# Tests backend US1 en paralelo:
Task T004: backend/tests/unit/test_plazo_fijo_order.py
Task T005: backend/tests/unit/test_plazo_fijo_validation.py
Task T006: backend/tests/integration/test_plazos_fijos_api.py

# Componentes frontend US1 en paralelo (tras tests escritos):
Task T015: frontend/src/components/PlazosFijosResumenPanel.tsx
Task T016: frontend/src/components/PlazoFijoForm.tsx
Task T017: frontend/src/components/PlazoFijoTable.tsx
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 + Phase 2
2. Complete Phase 3 (US1) — tests primero, luego backend, luego frontend
3. **STOP and VALIDATE**: `quickstart.md` §2 + UI `/plazos-fijos`
4. Demo gestión secretaria

### Incremental Delivery

1. Foundation → US1 (MVP gestión secretaria)
2. US2 (consulta escribano/secretaria)
3. Polish (docs + E2E)

### Parallel Team Strategy

- Dev A: US1 backend (T004–T013)
- Dev B: Tras T010, US1 frontend tests + components (T014–T020)
- Tras US1: Dev B US2 consulta UI (T023–T026)

---

## Notes

- Sin `CajasAdicionalesSelector` — un plazo = una caja (clarificación spec)
- Editar/eliminar sin límite 24h (no usar `ensure_within_edit_window` de movimientos)
- Resumen: solo plazos con `fecha_vencimiento >= today_ar()`
- Paginación fija 20; orden según FR-010 / data-model.md

---

## Task Summary

| Métrica | Valor |
|---------|-------|
| **Total tasks** | 29 |
| **US1 (P1)** | 17 (T004–T020) |
| **US2 (P2)** | 6 (T021–T026) |
| **Setup + Foundational** | 3 (T001–T003) |
| **Polish** | 3 (T027–T029) |
| **Parallel-marked [P]** | 14 |
| **MVP scope** | Phase 1–3 (US1) |
