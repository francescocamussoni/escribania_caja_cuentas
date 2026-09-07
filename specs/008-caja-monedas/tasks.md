# Tasks: Selección de Moneda en Registro de Cajas

**Input**: Design documents from `/specs/008-caja-monedas/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md  
**Testing**: TDD obligatorio (spec.md → Testing Strategy `TDD`)

**Organization**: Tareas agrupadas por user story. Tests escritos **antes** de implementación; deben fallar y luego pasar.

## Design Reference (UI)

Este proyecto **no usa Figma** para esta feature (no hay URL ni node-id en spec/plan). La spec y el plan mandan `willing.drawio` para el formulario de alta; filtros, carteles y valor de caja dual están en `spec.md`. Las tareas UI usan campo `wireframe:` (patrón 001–007), no `figma:`.

| Pantalla / pieza | Wireframe / fuente |
|------------------|-------------------|
| Formulario alta (Descripción, Monto, Moneda, Entrada, Salida) | `willing.drawio` (raíz del repo) |
| Punto de partida formulario | `actual.drawio` |
| Tabla, paginación, valor de caja | `registro_de_caja.drawio` / `consulta_de_caja.drawio` + spec FR-013, FR-016–020 |
| Cartel USD | Textos exactos en spec US2 / FR-006, FR-007 |

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Paralelizable (archivos distintos, sin dependencias incompletas)
- **[USn]**: User story del spec.md

## Path Conventions

- Backend: `backend/src/app/`, tests en `backend/tests/`
- Frontend: `frontend/src/`, tests en `frontend/tests/`
- Migración: `backend/alembic/versions/008_movimiento_moneda.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline verde y contrato alineado antes de TDD.

- [x] T001 Verify branch `008-caja-monedas` and record baseline `make test-backend` / `make test-frontend` (or equivalent pytest + `npm test`)
- [x] T002 [P] Confirm `specs/008-caja-monedas/contracts/openapi.yaml` paths match `backend/src/app/api/router.py` prefix `/api/v1` + `/cajas` (ids `cajaId` vs `{caja_id}`)

**Checkpoint**: Branch correcto; se conoce el baseline de tests; contrato no choca con el router.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Columna `moneda` en `movimiento` (default ARS). **Bloquea todas las user stories.**

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Unit tests FIRST (must fail): `moneda` default ARS, reject values outside ARS/USD, CHECK/constraint in `backend/tests/unit/test_movimiento_moneda.py` (new)
- [x] T004 Add Alembic revision adding `movimiento.moneda VARCHAR(3) NOT NULL DEFAULT 'ARS'` + CHECK `IN ('ARS','USD')` + index `(caja_id, moneda, created_at DESC, id DESC)` in `backend/alembic/versions/008_movimiento_moneda.py`
- [x] T005 Add `moneda` mapped column and table CHECK to `Movimiento` in `backend/src/app/models/movimiento.py`
- [x] T006 [P] Add shared `Moneda` enum/literal (`ARS` \| `USD`) and validators (`extra="forbid"`) on create/update DTOs in `backend/src/app/schemas/movimiento.py` (default create `ARS`; `registrar_complementario` default false — logic later)

**Checkpoint**: `alembic upgrade` deja filas existentes en ARS. T003 verde. Sin cambiar aún cálculo de subtotales ni UI.

---

## Phase 3: User Story 1 — Registrar movimiento indicando moneda (Priority: P1) 🎯 MVP

**Goal**: Cada alta persiste ARS o USD (default ARS); subtotales y valor de caja no mezclan monedas; el formulario muestra el selector según `willing.drawio`.

**Independent Test**: Secretaria elige USD, registra una entrada **sin** par; el listado muestra USD; valor de caja ARS no cambia. Alta ARS sin selector tocado se comporta como hoy. Spec US1. Quickstart §3 pasos 2–3.

### Tests for User Story 1 (TDD — write FIRST)

> Write these tests FIRST, ensure they FAIL before implementation

- [x] T007 [P] [US1] Unit tests: create ARS vs USD uses previous subtotal of **that** currency only; first USD starts at 0 in `backend/tests/unit/test_movimiento_service.py`
- [x] T008 [P] [US1] Integration tests: `POST /api/v1/cajas/{id}/movimientos` with `moneda` omitted → ARS; `moneda: USD`; invalid moneda 400; escribano 403 in `backend/tests/integration/test_movimientos_api.py`
- [x] T009 [P] [US1] Integration tests: `GET /api/v1/cajas/{id}/saldo` returns `saldo_ars` and `saldo_usd` (not mixed `saldo_actual`) in `backend/tests/integration/test_movimientos_api.py` or `backend/tests/integration/test_cajas_saldo_moneda.py` (new)
- [x] T010 [P] [US1] Component tests: moneda default ARS, only ARS/USD, reset to ARS when caja changes, submit includes `moneda` in `frontend/tests/RegistroCajaPage.test.tsx` (and/or `frontend/tests/MovimientoForm.test.tsx` new)

### Implementation for User Story 1 — Backend

- [x] T011 [US1] Scope `create_movimiento` / last-row lock / `recalculate_subtotals` to `(caja_id, moneda)` in `backend/src/app/services/movimiento_service.py` (T007 green)
- [x] T012 [US1] Accept `moneda` on create; return `MovimientoCreateResponse` `{ movimiento, complementario: null }` and include `moneda` on `MovimientoResponse` in `backend/src/app/schemas/movimiento.py` and `backend/src/app/api/routes/movimientos.py` (T008 green)
- [x] T013 [US1] Compute dual saldos in `backend/src/app/services/caja_service.py` and `backend/src/app/api/routes/cajas.py`; update `CajaSaldoResponse` in `backend/src/app/schemas/caja.py` (T009 green; stop returning mixed `saldo_actual`)
- [x] T014 [US1] Recalculate only the affected currency stream on PATCH/DELETE in `backend/src/app/services/movimiento_service.py`; allow optional `moneda` on `UpdateMovimientoRequest` and recalc **both** streams if moneda changes; extend `backend/tests/integration/test_movimiento_edit_delete.py`

### Implementation for User Story 1 — Frontend

- [x] T015 [US1] Update `CajaSaldo`, `Movimiento`, `CreateMovimientoPayload`, `createMovimiento` return type in `frontend/src/services/api.ts` per OpenAPI
- [x] T016 [US1] Add moneda selector (default ARS, reset on caja change) in `frontend/src/components/MovimientoForm.tsx`
  - wireframe: willing.drawio
- [x] T017 [US1] Show `saldo_ars` and `saldo_usd` (filters later must not change this) and POST `moneda` in `frontend/src/pages/RegistroCajaPage.tsx`
  - wireframe: willing.drawio
- [x] T018 [P] [US1] Display both saldos on consulta header (replace `saldo_actual`) in `frontend/src/pages/ConsultaCajaPage.tsx`
  - wireframe: consulta_de_caja.drawio
- [x] T019 [US1] Adjust CSS so Moneda sits between Monto and Entrada/Salida without breaking mobile stack in `frontend/src/index.css` and `frontend/src/components/MovimientoForm.tsx`
  - wireframe: willing.drawio

**Checkpoint**: US1 — alta ARS/USD, subtotales por stream, valor de caja dual, selector default ARS. Sin cartel de par todavía.

---

## Phase 4: User Story 2 — Movimiento complementario solo en USD (Priority: P1)

**Goal**: En USD, Entrada/Salida preguntan el par; confirmar persiste dos movimientos atómicos; rechazar uno solo; ARS sin cartel.

**Independent Test**: USD + Entrada + confirmar → dos renglones mismo monto tipos opuestos; cancelar → uno; fallo simulado → cero. ARS sin diálogo. Spec US2. Quickstart §3 paso 4.

### Tests for User Story 2 (TDD — write FIRST)

- [x] T020 [P] [US2] Unit tests: `registrar_complementario` inserts two rows same caja/descripcion/monto/USD opposite tipos; rollback leaves zero rows; ARS+complementario rejected in `backend/tests/unit/test_movimiento_service.py`
- [x] T021 [P] [US2] Integration tests: POST USD `registrar_complementario: true` 201 with both bodies; `false`/omit one row; ARS+true 400; 403 escribano in `backend/tests/integration/test_movimientos_api.py`
- [x] T022 [P] [US2] Component tests: USD Entrada shows exact **¿Registrar también como salida?**; USD Salida **¿Registrar también como entrada?**; ARS never; validate empty monto before dialog in `frontend/tests/MovimientoForm.test.tsx`

### Implementation for User Story 2

- [x] T023 [US2] Implement atomic pair insert (actioned tipo first, then opposite) in one DB transaction in `backend/src/app/services/movimiento_service.py` (T020 green)
- [x] T024 [US2] Wire `registrar_complementario` on POST; fill `complementario` in 201; generic error if commit fails (no partial persist) in `backend/src/app/api/routes/movimientos.py` (T021 green)
- [x] T025 [US2] After valid descripcion/monto, confirm dialogs then POST flag; additional cajas reuse same payload per caja in `frontend/src/components/MovimientoForm.tsx` and `frontend/src/pages/RegistroCajaPage.tsx`
  - wireframe: willing.drawio
- [x] T026 [P] [US2] Log `movimiento_created` (and complementario id if any) without secrets in `backend/src/app/api/routes/movimientos.py`

**Checkpoint**: US1+US2 — par USD atómico y cartel solo USD.

---

## Phase 5: User Story 3 — Ver moneda en el listado y filtrar (Priority: P2)

**Goal**: Cada monto muestra ARS/USD; filtros rango de fechas (TZ Argentina) y moneda; paginación sobre el filtrado; consulta igual para escribano.

**Independent Test**: Historial mixto; filtrar USD y un rango; página 1 = 20 más recientes del **filtro**; valor de caja sigue mostrando ambos saldos. Spec US3. Quickstart §3 paso 5–6.

### Tests for User Story 3 (TDD — write FIRST)

- [x] T027 [P] [US3] Integration tests: GET list `moneda`, `fecha_desde`, `fecha_hasta` (inclusive, America/Argentina/Buenos_Aires), AND combo, empty page, page_size 20 in `backend/tests/integration/test_movimientos_api.py`
- [x] T028 [P] [US3] Component tests: monto shows moneda; filter controls; clearing filters reloads full list; escribano has filters not Entrada/Salida in `frontend/tests/listadoStackedFields.test.tsx` and `frontend/tests/ConsultaCajaPage.test.tsx`

### Implementation for User Story 3 — Backend

- [x] T029 [US3] Apply list filters (reuse TZ pattern from `backend/src/app/services/informe_service.py` / `app.core.dates`) in `backend/src/app/api/routes/movimientos.py`; count/offset on filtered set (T027 green)
- [x] T030 [P] [US3] Document/query-validate `fecha_desde` > `fecha_hasta` → 400 in `backend/src/app/api/routes/movimientos.py`

### Implementation for User Story 3 — Frontend

- [x] T031 [US3] Show moneda next to monto (keep entrada/salida colors) in `frontend/src/components/MovimientoTable.tsx`
  - wireframe: registro_de_caja.drawio
- [x] T032 [US3] Add moneda filter (todas/ARS/USD) and date from/to; pass query params; pagination uses filtered totals in `frontend/src/pages/RegistroCajaPage.tsx` and `frontend/src/services/api.ts`
  - wireframe: registro_de_caja.drawio
- [x] T033 [US3] Same filters + moneda on amounts for escribano/secretaria consulta in `frontend/src/pages/ConsultaCajaPage.tsx`
  - wireframe: consulta_de_caja.drawio
- [x] T034 [P] [US3] Stack filter row on mobile without hiding pager in `frontend/src/index.css`
  - wireframe: registro_de_caja.drawio

**Checkpoint**: US3 — listado y consulta filtrables; SC-005/SC-007.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Conjunto, informes y paridad; no mezclar monedas en ningún total.

- [x] T035 [P] Tests FIRST then replace `subtotal_general` / item `saldo_actual` with `subtotal_general_ars`/`usd` and per-caja dual saldos in `backend/src/app/services/caja_service.py`, `backend/src/app/schemas/caja.py`, `backend/src/app/api/routes/cajas.py`, `backend/tests/integration/test_cajas_config_api.py`
- [x] T036 Update conjunto UI (general + por caja + suma de adicionales) to dual saldos — never ARS+USD — in `frontend/src/pages/ConsultaCajaPage.tsx` and `frontend/src/services/api.ts`
  - wireframe: consulta_de_caja.drawio
- [x] T037 [P] Split informe `saldo_cierre` / printed amounts by moneda (plazos fijos remain ARS) in `backend/src/app/services/informe_service.py` and related tests; show currency on PDF movement lines
- [x] T038 [P] Fix remaining frontend/backend references to `saldo_actual` (search `frontend/` and `backend/`)
- [x] T039 Run quickstart.md verification (migrate, TDD suites, manual US1–US3) and fix regressions in `backend/tests/integration/test_movimiento_edit_delete.py`, `frontend/tests/RegistroCajaPage.test.tsx`
- [x] T040 [P] Note constitution follow-up: replace “moneda única ARS” for caja movements in `.spec-kitti/memory/constitution.md` (amend after merge — do not silently skip if this task is in-scope for docs only)

**Checkpoint**: Ningún total mezclado; quickstart cubierto; tests de paridad ARS verdes.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Inmediato
- **Foundational (Phase 2)**: Tras Setup — BLOQUEA user stories
- **US1 (Phase 3)**: Tras Phase 2 — MVP
- **US2 (Phase 4)**: Tras US1 backend create DTO (T012); UI cartel tras T016
- **US3 (Phase 5)**: Puede solaparse con US2 en backend de listado tras T011; UI tabla tras T015 tipos
- **Polish (Phase 6)**: Tras US1 saldos (T013); conjunto/informes no bloquean MVP de registro

### User Story Dependencies

- **US1 (P1)**: Independiente tras foundation
- **US2 (P1)**: Extiende POST de US1 (`registrar_complementario`)
- **US3 (P2)**: Lectura; requiere `moneda` persistida (US1)

### Within Each User Story

- Tests FIRST (fail) → modelo/servicio → endpoint → UI
- No mezclar implementación antes de rojo en TDD

### Parallel Opportunities

- T002 ∥ T001
- T007, T008, T009, T010 en paralelo (archivos de test distintos / secciones)
- T020, T021, T022 en paralelo
- T027 ∥ T028
- T035 ∥ T037 ∥ T040
- Tras T011: T029 (list filters) puede avanzar en paralelo a T023 (par)

---

## Parallel Example: User Story 1

```bash
# Tests FIRST (fail):
Task: "Unit tests subtotal per currency in backend/tests/unit/test_movimiento_service.py"
Task: "Integration POST moneda in backend/tests/integration/test_movimientos_api.py"
Task: "Integration GET saldo dual"
Task: "Component MovimientoForm default ARS"

# Then implementation in order: T011 → T012 → T013 → frontend T015–T019
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1–2  
2. Phase 3 US1  
3. **STOP**: demo selector + USD simple + valor de caja dual  
4. Luego US2 (cartel/par) y US3 (filtros)

### Incremental Delivery

1. Foundation `moneda`  
2. US1 alta + saldos  
3. US2 par atómico  
4. US3 filtros  
5. Polish conjunto + informes  

### Parallel Team Strategy

1. Juntos: Phase 1–2  
2. Dev A: US1 backend → US2 backend  
3. Dev B: US1 frontend (tras T012/T013/T015)  
4. Dev C: US3 list API + T029 en paralelo cuando exista `moneda`

---

## Notes

- [P] = archivos distintos, sin depender de tareas incompletas del mismo archivo
- TDD: rojo → implementar → verde
- UI: `wireframe:` (no Figma); implement no debe exigir `figma:` si la Design Reference de esta feature lo documenta
- Breaking API: `MovimientoCreateResponse`, `saldo_ars`/`saldo_usd`, `subtotal_general_ars`/`usd`
- Cajas adicionales: N POST con el mismo payload (par atómico **por caja**)
- Delete/edit de un renglón del par no cascada al otro
