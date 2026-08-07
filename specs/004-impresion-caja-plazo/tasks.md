# Tasks: Impresión de Caja y Plazos Fijos

**Input**: Design documents from `/specs/004-impresion-caja-plazo/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml  
**Testing**: TDD obligatorio (spec.md → Testing Strategy)

**Organization**: Tareas agrupadas por user story. Tests escritos **antes** de implementación.

## Design Reference (UI)

Este proyecto no usa Figma para esta feature; el spec (FR-007) exige paridad visual con
Consulta de Caja y Consulta Plazos Fijos. La constitución (principio III) define
`consulta_de_caja.drawio` como referencia. Las tareas UI usan campo `wireframe:` (patrón
features 001 y 003).

| Pantalla | Wireframe / referencia código |
|----------|-------------------------------|
| Impresión | `consulta_de_caja.drawio` · paridad `frontend/src/pages/ConsultaCajaPage.tsx` |

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Paralelizable (archivos distintos, sin dependencias incompletas)
- **[USn]**: User story del spec.md

## Path Conventions

- Backend: `backend/src/app/`, tests en `backend/tests/`
- Frontend: `frontend/src/`, tests en `frontend/tests/`
- Sin migraciones Alembic (solo lectura de tablas existentes)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencia PDF y alineación de contrato antes de implementar.

- [x] T001 Verify branch `004-impresion-caja-plazo` and baseline `make test` passes (features 001 + 003 operativas)
- [x] T002 [P] Add `fpdf2` dependency in `backend/pyproject.toml` per research.md R3
- [x] T003 [P] Cross-check `POST /api/v1/informes/pdf` in `specs/004-impresion-caja-plazo/contracts/openapi.yaml` against mount pattern in `backend/src/app/api/router.py`

**Checkpoint**: Stack local healthy; contrato revisado; fpdf2 declarado.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: DTO, resolución de rangos temporales (incl. **hasta hoy**) y filename. **Bloquea user stories.**

- [x] T004 [P] Unit tests `resolve_date_range` (mes único, mes+hasta hoy abr→17/jul, período, período+hasta hoy, inicio > hoy → error) in `backend/tests/unit/test_informe_date_range.py`
- [x] T005 [P] Unit tests `build_informe_filename` (YYYY-MM, YYYY-MM-01_YYYY-MM-DD, YYYY-MM-DD_YYYY-MM-DD) in `backend/tests/unit/test_informe_filename.py`
- [x] T006 [P] Create `InformePdfRequest` with `hasta_hoy`, validators and `extra="forbid"` in `backend/src/app/schemas/informe.py` per `data-model.md`
- [x] T007 Implement `build_informe_filename()` in `backend/src/app/core/filenames.py` per FR-021a
- [x] T008 Implement `resolve_date_range()` and shared helpers in `backend/src/app/services/informe_service.py` using `today_ar()` from `backend/src/app/core/dates.py`

**Checkpoint**: Rango temporal y filename testeados sin depender de PDF.

---

## Phase 3: User Story 1 — Imprimir Informe de Caja (Priority: P1) 🎯 MVP

**Goal**: Generar PDF de movimientos de caja filtrados por mes/año, período o **hasta hoy**;
columnas consulta + signos Entrada/Salida + saldo cierre y saldo actual.

**Independent Test**: Login secretaria/escribano → `/impresion` → tipo Caja → Ebel → abril 2026
+hasta hoy → PDF con movimientos 1/abr–hoy, filename `CAJA-Ebel-2026-04-01_YYYY-MM-DD.pdf`.
API: `quickstart.md` §2 curl CAJA.

### Tests for User Story 1 (TDD — write FIRST)

- [x] T009 [P] [US1] Unit tests `fetch_movimientos_informe`, `compute_saldo_cierre`, saldo actual in `backend/tests/unit/test_informe_service.py`
- [x] T010 [P] [US1] Unit tests `render_caja_pdf` (encabezado, +/−, dos saldos, período vacío) in `backend/tests/unit/test_pdf_informe_renderer.py`
- [x] T011 [P] [US1] Integration tests POST informes tipo CAJA (200 PDF bytes, 400 fechas, 401, 404, escribano OK) in `backend/tests/integration/test_informes_api.py`

### Implementation for User Story 1 — Backend

- [x] T012 [US1] Implement `fetch_movimientos_informe` and saldo helpers in `backend/src/app/services/informe_service.py`
- [x] T013 [US1] Implement `render_caja_pdf` in `backend/src/app/services/pdf_informe_renderer.py` (A4, encabezado operativo, tabla, FR-014a)
- [x] T014 [US1] Implement `POST /informes/pdf` for `tipo=CAJA` in `backend/src/app/api/routes/informes.py` with `StreamingResponse` and `Content-Disposition`
- [x] T015 [US1] Register informes router in `backend/src/app/api/router.py`; log `informe_generated` (sin montos)

### Tests for User Story 1 — Frontend (TDD — write FIRST)

- [x] T016 [P] [US1] Component tests formulario caja (mes/año, período, hasta hoy, validación, submit blob) in `frontend/tests/ImpresionPage.test.tsx`

### Implementation for User Story 1 — Frontend

- [x] T017 [P] [US1] Add `postInformePdf()` blob helper and types in `frontend/src/services/api.ts`
- [x] T018 [US1] Implement `frontend/src/pages/ImpresionPage.tsx` (tipo Caja, `CajaSelector`, temporalidad, checkbox Hasta hoy, generar informe)
  - wireframe: consulta_de_caja.drawio
- [x] T019 [US1] Add route `/impresion` (secretaria + escribano) in `frontend/src/App.tsx` and Navbar link "Impresión" in `frontend/src/components/layout/Navbar.tsx`

**Checkpoint**: US1 tests green; PDF caja end-to-end; SC-001, SC-002, SC-005 (caja), SC-006, SC-007, SC-009.

---

## Phase 4: User Story 2 — Imprimir Informe de Plazos Fijos (Priority: P2)

**Goal**: Mismo flujo Impresión con tipo Plazo fijo; PDF con resumen dual (solo activos del
período filtrado) y tabla orden consulta.

**Independent Test**: Tipo Plazo fijo → Gabriel → período con plazos → PDF con resumen y
columnas Monto ingresado / Fecha vencimiento / Monto a vencimiento. `quickstart.md` §2 PLAZO_FIJO.

### Tests for User Story 2 (TDD — write FIRST)

- [x] T020 [P] [US2] Unit tests `fetch_plazos_informe` and `compute_resumen_plazos_filtrado` in `backend/tests/unit/test_informe_service.py`
- [x] T021 [P] [US2] Unit tests `render_plazo_fijo_pdf` (resumen dual, orden vencimiento) in `backend/tests/unit/test_pdf_informe_renderer.py`
- [x] T022 [P] [US2] Integration tests POST informes tipo PLAZO_FIJO in `backend/tests/integration/test_informes_api.py`

### Implementation for User Story 2

- [x] T023 [US2] Extend `informe_service.py` with plazos fijos queries and filtered resumen
- [x] T024 [US2] Implement `render_plazo_fijo_pdf` in `backend/src/app/services/pdf_informe_renderer.py`
- [x] T025 [US2] Extend `informes.py` route to handle `tipo=PLAZO_FIJO`
- [x] T026 [P] [US2] Component tests tipo Plazo fijo and resumen expectations in `frontend/tests/ImpresionPage.test.tsx`
- [x] T027 [US2] Extend `ImpresionPage.tsx` for tipo Plazo fijo (misma temporalidad / hasta hoy)
  - wireframe: consulta_de_caja.drawio

**Checkpoint**: US2 tests green; SC-003, SC-004; plazos filtrados con hasta hoy.

---

## Phase 5: User Story 3 — Documento PDF Formal y Descargable (Priority: P3)

**Goal**: PDF legible A4, tipografía formal, multipágina sin límite 20 filas, mensaje explícito
si período vacío.

**Independent Test**: Informe con muchos registros → varias páginas legibles; período sin datos →
PDF válido con mensaje (no tabla vacía). SC-008 checklist manual.

### Tests for User Story 3 (TDD — write FIRST)

- [x] T028 [P] [US3] Unit tests multipágina, tipografía mínima legible, mensaje período vacío in `backend/tests/unit/test_pdf_informe_renderer.py`

### Implementation for User Story 3

- [x] T029 [US3] Polish `pdf_informe_renderer.py`: tipografía formal, márgenes A4, repetición encabezado tabla en páginas siguientes (FR-022, FR-023)
- [x] T030 [US3] Ensure encabezado operativo muestra rango resuelto legible (ej. `01/04/2026 – 17/07/2026`) en `pdf_informe_renderer.py`

**Checkpoint**: US3 tests green; SC-008 verificable en revisión manual.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentación y validación E2E.

- [x] T031 [P] Update `docs/frontend.md` with route `/impresion`, roles y flujo hasta hoy
- [x] T032 Run backend + frontend test suites per `quickstart.md` §4
- [x] T033 Manual validation checklist `quickstart.md` §5 (filename, hasta hoy, saldos dual, B/N signos)

**Checkpoint**: Quickstart completo; listo para deploy.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias
- **Foundational (Phase 2)**: Depende de Phase 1 — **bloquea** todas las user stories
- **US1 (Phase 3)**: Depende de Phase 2 — **MVP**
- **US2 (Phase 4)**: Depende de US1 backend renderer/route (extensión, no reescritura)
- **US3 (Phase 5)**: Depende de US1 renderer base; puede solaparse con US2
- **Polish (Phase 6)**: Depende de US1–US3 deseados

### User Story Dependencies

| Story | Depende de | Independiente en |
|-------|------------|------------------|
| US1 P1 | Phase 2 | PDF caja + pantalla Impresión (tipo Caja) |
| US2 P2 | US1 informes route/renderer | PDF plazo fijo en misma pantalla |
| US3 P3 | US1 renderer | Calidad formal multipágina |

### Parallel Opportunities

- Phase 1: T002 ∥ T003
- Phase 2: T004 ∥ T005 ∥ T006
- US1 tests: T009 ∥ T010 ∥ T011; T016 ∥ backend impl tras tests red
- US2 tests: T020 ∥ T021 ∥ T022
- Polish: T031 ∥ T032 tras implementación

### Parallel Example: User Story 1

```bash
# Tests en rojo (paralelo):
pytest backend/tests/unit/test_informe_service.py -k caja
pytest backend/tests/unit/test_pdf_informe_renderer.py -k caja
pytest backend/tests/integration/test_informes_api.py -k caja

# Frontend en rojo:
npm test -- ImpresionPage
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 → Phase 2 → Phase 3
2. **STOP**: PDF caja + `/impresion` operativo
3. Demo con informe mensual y con **hasta hoy**

### Incremental Delivery

1. US1 → PDF caja (MVP)
2. US2 → PDF plazos fijos
3. US3 → pulido formal multipágina
4. Phase 6 → docs y quickstart

### Suggested MVP Scope

**User Story 1** (T001–T019): informe de caja con filtros temporales y hasta hoy.

---

## Notes

- Sin Figma: usar `wireframe:` en tareas UI (ver Design Reference arriba)
- `hasta_hoy` default `false`; fecha fin oculta en UI cuando activo (FR-005a)
- Filename siempre generado en servidor (`Content-Disposition`)
- Verificar tests en **rojo** antes de cada bloque de implementación (TDD)

---

## Task Summary

| Phase | Tasks | Story |
|-------|-------|-------|
| 1 Setup | T001–T003 | — |
| 2 Foundational | T004–T008 | — |
| 3 US1 Caja | T009–T019 | P1 MVP |
| 4 US2 Plazos | T020–T027 | P2 |
| 5 US3 PDF formal | T028–T030 | P3 |
| 6 Polish | T031–T033 | — |
| **Total** | **33** | |
