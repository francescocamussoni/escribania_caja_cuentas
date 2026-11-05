# Tasks: Endose de cheques pendientes

**Branch**: `011-cheque-endose`  
**Input**: `specs/011-cheque-endose/` (plan.md, spec.md, research.md, data-model.md, contracts/openapi-delta.yaml, quickstart.md)  
**Prerequisites**: plan.md, spec.md · depende de la feature 010 (ya implementada)  
**Testing**: **TDD-first** — tests escritos y **fallando** ANTES de cada implementación (spec.md → Testing Strategy)

**Organization**: Tareas agrupadas por user story. Cada story es independientemente verificable; las tareas de test van antes de su implementación y deben fallar y luego pasar.

## Design Reference (UI)

Esta feature **no usa Figma** (no hay URL ni node-id en spec/plan; el desarrollador eligió continuar sin Figma, igual que en la feature 010). Las tareas UI usan el campo `wireframe:` (no `figma:`). El botón **Endose** y la ventana de selección de caja **no figuran** en los `.drawio`: se definen en `spec.md` y su desviación de layout queda registrada en `plan.md` › Complexity Tracking (Principio III). La ventana reutiliza el patrón visual existente `.complementario-dialog*` de `frontend/src/index.css`.

| Pantalla / pieza | Wireframe / fuente |
|---|---|
| Bloque de cheques pendientes (botón **Endose** junto a **Liquidar**) en Registro | `registro_de_caja.drawio` + spec FR-001–FR-004 |
| Ventana de selección de caja (**EndoseDialog**) | Patrón `.complementario-dialog*` de `index.css` + spec FR-005–FR-007 |
| Historial con marcas **Endosado → caja** / **Endose desde caja** | `registro_de_caja.drawio` + spec FR-010, FR-019 |
| Sección **Cheques** (botón **Endose** en ambos listados) | `consulta_de_caja.drawio` (patrón tabla/paginación) + spec FR-001, US2 |
| Colores semánticos | Verde = entrada, rojo = salida (constitución, Principio III) |

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Paralelizable (archivos distintos, sin dependencias de tareas incompletas)
- **[USn]**: User story del `spec.md`
- Tareas UI (archivos `.tsx`/`.css`): llevan `wireframe:` en la línea siguiente (ver Design Reference)

## Path Conventions

- Backend: `backend/src/app/`, tests en `backend/tests/`
- Frontend: `frontend/src/`, tests en `frontend/tests/`
- Migración: `backend/alembic/versions/011_movimiento_endose.py`
- Los tests de cada story van en archivos nuevos cuando es posible (`test_cheque_endose_*`, `test_cheques_endose_*`); los archivos legacy se extienden solo donde se indica (paridad / regresión).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline verde y contrato alineado antes de TDD.

- [x] T001 Verify branch `011-cheque-endose` and record the baseline: `python -m pytest tests/` in `backend/` and `npm run test -- --run` in `frontend/` (note any pre-existing failures)
- [x] T002 [P] Confirm `specs/011-cheque-endose/contracts/openapi-delta.yaml` path `/api/v1/cajas/{caja_id}/movimientos/{movimiento_id}/endosar` matches the prefixes in `backend/src/app/api/router.py` and the existing `liquidar` route in `backend/src/app/api/routes/movimientos.py`

**Checkpoint**: Branch correcto; baseline conocido; contrato no choca con el router.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Migración y modelo con el vínculo cheque ↔ movimiento de endose, y tipos de API del frontend. **Bloquea todas las user stories.**

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests FIRST (must fail)

- [x] T003 [P] Unit tests FIRST: `Movimiento` derived properties (`endosado`, `es_endose_destino`, `bloqueado_por_endose`) and CHECK constraints (`endosado_a_caja_id` on a common movement fails; on a pending cheque fails; on a liquidated cheque passes; `endose_cheque_id` on a cheque fails; on a common movement passes) plus unique partial index (two movements with the same `endose_cheque_id` → integrity error) in `backend/tests/unit/test_movimiento_endose_model.py` (new)

### Implementation

- [x] T004 Add Alembic revision `011_movimiento_endose` (down_revision `010_movimiento_cheque`): add `endosado_a_caja_id SMALLINT NULL` FK `caja.id` and `endose_cheque_id BIGINT NULL` FK `movimiento.id`; create `ck_movimiento_endose_cheque` and `ck_movimiento_endose_destino`; create partial unique index `uq_movimiento_endose_cheque` via `op.execute`; `downgrade` aborts with a clear error if any endose exists in `backend/alembic/versions/011_movimiento_endose.py`
- [x] T005 Extend `Movimiento` with the two columns, the 2 `CheckConstraint`s (so `create_all` in tests applies them), `selectin` relationships `endosado_a_caja` / `endose_cheque`, and the derived properties in `backend/src/app/models/movimiento.py` (T003 green)
- [x] T006 Verify `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` on a database with 010 data, and that downgrade aborts when an endose exists, using `backend/alembic/versions/011_movimiento_endose.py`
- [x] T007 [P] Extend `frontend/src/services/api.ts`: `Movimiento` with `endosable`, `endosado_a`, `endose_origen`; types `EndoseOrigen`, `EndoseResponse`; function `endosarCheque(cajaId, movimientoId, cajaDestinoId)` posting only `{ caja_destino_id }` to `/api/v1/cajas/{cajaId}/movimientos/{movimientoId}/endosar`, per `contracts/openapi-delta.yaml`

**Checkpoint**: Migración aplicada y reversible; constraints activos; tipos de API listos; suite de 010 verde.

---

## Phase 3: User Story 1 — Endosar un cheque pendiente a otra caja en cualquier momento (Priority: P1) 🎯 MVP

**Goal**: Cada cheque pendiente muestra **Endose** (siempre habilitado, solo Secretaria) junto a **Liquidar** (habilitado desde la fecha de liquidación). Al pulsar **Endose** se abre una ventana con las cajas; al confirmar, el cheque queda liquidado en su caja y la caja destino recibe el movimiento inverso, todo de forma atómica. Cheque endosado y movimiento destino no se editan ni eliminan.

**Independent Test**: Cheque pendiente de entrada ARS 500 en caja A (liquidación futura) → **Liquidar** deshabilitado, **Endose** habilitado → Endose → elegir caja B → confirmar → A +500 (cheque Liquidado · Endosado → B), B −500 (salida "Endose cheque: … (Caja A)"); sin Editar/Eliminar en ambos. Repetir con cheque de salida (A −M, B +M). Spec US1. Quickstart pasos 1–3, 5–8.

### Tests for User Story 1 (TDD — write FIRST)

> Write these tests FIRST, ensure they FAIL before implementation

- [x] T008 [P] [US1] Unit tests: `endosar_cheque` — entrada: origen +M and destino salida M; salida: origen −M and destino entrada M (neto 0); ARS and USD independent; works with `fecha_liquidacion` in the future; cheque gets `fecha_liquidado`, `endosado_a_caja_id`, `updated_by`; destino is `instrumento='ninguno'` with `endose_cheque_id`, same `moneda`/`monto`, generated description `Endose cheque: <desc> (Caja <origen>)` truncated to 500; errors: cheque missing / common movement / other caja → not found; already liquidated or endorsed → `ChequeYaLiquidadoError`; destino missing, archived or equal to origen → validation error; failure after marking the cheque leaves it pending and creates no movement (rollback); `update_movimiento`/`delete_movimiento` on an endorsed cheque and on an endose movement → `MovimientoEndosadoError`, unchanged for the rest in `backend/tests/unit/test_cheque_endose_service.py` (new)
- [x] T009 [P] Integration tests (Postgres): concurrent double endose of the same cheque → exactly one succeeds and the other conflicts (balances not duplicated); crossed endorsements A→B and B→A run without deadlock; subtotals of both streams match chronological replay after endose (including a later-dated manual movement) in `backend/tests/integration/test_cheques_endose_service.py` (new)
- [x] T010 [P] Unit tests: `EndosarChequeRequest` — `caja_destino_id` required, integer ≥ 1, `extra="forbid"`; `MovimientoResponse`: `endosable` true only for pending cheque + secretaria, `endosado_a` on the cheque, `endose_origen` on the destino, `editable=false` for both in `backend/tests/unit/test_movimiento_endose_schema.py` (new)
- [x] T011 [P] Integration tests: `POST /api/v1/cajas/{id}/movimientos/{mid}/endosar` → 200 with `cheque` (Liquidado, `endosado_a`) and `movimiento_destino` (`endose_origen`, inverse tipo); `/saldo` of both cajas updated for entrada and salida, ARS and USD; 401 no token; 403 Escribano; 404 unknown origin caja / cheque of another caja / common movement / unknown destino; 409 already liquidated, already endorsed, second call; 422 destino == origen, destino archived, extra fields, `caja_destino_id` ≤ 0; `PATCH`/`DELETE` on the endorsed cheque and on the destino movement → 409 in `backend/tests/integration/test_cheques_endose_api.py` (new)
- [x] T012 [P] [US1] Regression tests: `POST .../liquidar` before `fecha_liquidacion` → 409 and cheque stays pending; on/after the date → 200; liquidating never creates a movement in another caja in `backend/tests/integration/test_cheques_liquidar_api.py` (extend legacy file)
- [x] T013 [P] [US1] Component tests: `EndoseDialog` lists the cajas expanded (radio group) excluding the origin caja; **Confirmar** disabled until one is selected; confirm calls `onConfirm(cajaId)`; **Cancelar** and Esc close without calling; while submitting blocks a second confirm; on error shows a generic message and keeps the dialog usable in `frontend/tests/EndoseDialog.test.tsx` (new)
- [x] T014 [P] [US1] Component tests: `ChequesPendientesBlock` shows **Endose** next to **Liquidar** only when `endosable`; with a future `fecha_liquidacion` Liquidar is disabled and Endose enabled; with a reached date both enabled; opening Endose shows the dialog; confirm calls `endosarCheque` and reloads the block; server error keeps the cheque and shows a message; read-only mode / Escribano shows neither button in `frontend/tests/ChequesPendientesBlock.test.tsx`
- [x] T015 [P] [US1] Component tests: `MovimientoTable` shows **Endosado → <caja>** on the liquidated cheque and **Endose desde <caja>** on the destino movement and hides Editar/Eliminar when `editable=false`; Registro refreshes Valor de caja, historial, pending block and Saldo a futuro after an endose in `frontend/tests/MovimientoTable.test.tsx` and `frontend/tests/RegistroCajaPage.test.tsx`

### Implementation for User Story 1 — Backend

- [x] T016 [US1] Implement in `backend/src/app/services/movimiento_service.py`: `endosar_cheque` (lock both cajas in ascending `id` → cheque row → insert destino → replay origin and destino streams; no `fecha_liquidacion` gate; destino validations; generated description), `MovimientoEndosadoError`, optional `endose_cheque_id` parameter in `create_movimiento`, and guards in `update_movimiento` / `delete_movimiento` (T008, T009 green)
- [x] T017 [US1] Add `EndosarChequeRequest` (`extra="forbid"`, `caja_destino_id ≥ 1`), `EndoseOrigen`, `EndoseResponse`; widen `MovimientoResponse` with `endosable`, `endosado_a`, `endose_origen`; make `is_editable` false when `bloqueado_por_endose` in `backend/src/app/schemas/movimiento.py` (T010 green)
- [x] T018 [US1] Add `POST /{caja_id}/movimientos/{movimiento_id}/endosar` (`require_role("secretaria")`, commit/rollback, 404/409/422 mapping with generic messages, `cheque_endorsed` security log with ids only — no amounts or descriptions) and map `MovimientoEndosadoError` to 409 in `PATCH`/`DELETE` in `backend/src/app/api/routes/movimientos.py` (T011, T012 green)

### Implementation for User Story 1 — Frontend

- [x] T019 [US1] Create `EndoseDialog` (`role="dialog"`, `aria-modal`, initial focus, Esc/Cancelar close, expanded radio list of cajas from `fetchCajas()` excluding the origin caja, **Confirmar** disabled without selection, submitting and error states) in `frontend/src/components/EndoseDialog.tsx` (T013 green)
  - wireframe: .complementario-dialog pattern in frontend/src/index.css (no .drawio)
- [x] T020 [US1] Add styles for the dialog and the cajas list reusing the `.complementario-dialog*` look, mobile-friendly, in `frontend/src/index.css`
  - wireframe: .complementario-dialog pattern in frontend/src/index.css (no .drawio)
- [x] T021 [US1] Add the **Endose** button (visible when `endosable`, always enabled while idle) next to **Liquidar**, open `EndoseDialog`, call `onEndosar(cheque, cajaDestinoId)`, reload the block after success and show a generic error on failure in `frontend/src/components/ChequesPendientesBlock.tsx` (T014 green)
  - wireframe: registro_de_caja.drawio
- [x] T022 [P] [US1] Show **Endosado → <caja>** / **Endose desde <caja>** marks and hide Editar/Eliminar when `editable=false` in `frontend/src/components/MovimientoTable.tsx` (T015 green)
  - wireframe: registro_de_caja.drawio
- [x] T023 [US1] Handle the endose in Registro (call `endosarCheque`, refresh saldo + historial + pending block + Saldo a futuro, generic error on failure) and pass `onEndosar` to the pending block in `frontend/src/pages/RegistroCajaPage.tsx` (T015 green)
  - wireframe: registro_de_caja.drawio

**Checkpoint**: US1 — endose atómico desde Registro con saldos correctos en ambas cajas; Liquidar sin regresiones. Suite completa verde.

---

## Phase 4: User Story 2 — Endosar desde la sección Cheques (Priority: P2)

**Goal**: La sección **Cheques** muestra **Endose** (siempre habilitado) y **Liquidar** (según fecha) en ambos listados, solo para la Secretaria; tras endosar el cheque desaparece de la sección.

**Independent Test**: En **Próximos a liquidar este mes** pulsar **Endose** sobre un cheque, elegir caja, confirmar → desaparece de la sección y los saldos cambian como en US1; Escribano no ve botones. Spec US2. Quickstart paso 5.

### Tests for User Story 2 (TDD — write FIRST)

- [x] T024 [P] [US2] Component tests: `ChequesPage` shows **Endose** in **Aptos para liquidar** and **Próximos a liquidar este mes** (Liquidar disabled before its date, Endose enabled); confirm calls `endosarCheque(cheque.caja.id, cheque.id, cajaDestinoId)` and both lists reload; error keeps the cheque; Escribano sees no Endose/Liquidar in `frontend/tests/ChequesPage.test.tsx`

### Implementation for User Story 2

- [x] T025 [US2] Add **Endose** button + `EndoseDialog` flow to both listings (origin caja taken from `cheque.caja`), reload both lists after success, generic error on failure in `frontend/src/pages/ChequesPage.tsx` (T024 green)
  - wireframe: consulta_de_caja.drawio

**Checkpoint**: US1+US2 — endose operable desde Registro y desde la sección Cheques.

---

## Phase 5: User Story 3 — Endose y vistas derivadas consistentes (Priority: P3)

**Goal**: Tras un endose el cheque deja de ser pendiente en todas las vistas y los saldos/informes reflejan ambos movimientos.

**Independent Test**: Endosar un cheque y verificar: ya no figura en `/cheques`, `cheques-pendientes`, `saldo-futuro` ni `saldo-proyectado`; ambos movimientos aparecen en `/movimientos` de su caja, en `saldo-general` y en el informe de Caja. Spec US3. Quickstart paso 4.

### Tests for User Story 3 (TDD — write FIRST)

- [x] T026 [P] [US3] Integration tests: after an endose the cheque is absent from `GET /api/v1/cheques` (aptos and proximos), `GET .../cheques-pendientes`, `GET .../saldo-futuro` and `GET .../saldo-proyectado` of the origin caja; both movements appear in `GET .../movimientos` of their caja with subtotal; `GET /api/v1/cajas/saldo-general` and per-caja `/saldo` reflect both (net 0 across the two cajas); the Caja PDF report of both cajas lists both movements and the endorsed cheque is not in "Cheques pendientes"; Plazos Fijos report unchanged in `backend/tests/integration/test_cheques_endose_vistas.py` (new)

### Implementation for User Story 3

- [x] T027 [US3] Make T026 pass: per the design no code change is expected (an endorsed cheque is already liquidated); if a view still lists it as pending or omits a movement, fix only the offending query in `backend/src/app/services/cheque_service.py`, `backend/src/app/services/informe_service.py` or `backend/src/app/api/routes/cajas.py` and note the cause in the commit message

**Checkpoint**: US1–US3 — vistas derivadas coherentes tras el endose.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T028 Run the full suites: `python -m pytest tests/` in `backend/` and `npm run test -- --run` + `npm run build` in `frontend/`; compare with the T001 baseline (no new failures)
- [x] T029 Execute `specs/011-cheque-endose/quickstart.md` manual verification with both roles (Secretaria and Escribano), including cancel/network error and Liquidar regression
- [x] T030 [P] Security pass on the new endpoint per `.cursor/rules/security-main.mdc`: strict schema, server-side destination validation, RBAC 403, generic errors, no amounts/descriptions in logs, lock ordering documented in `backend/src/app/services/movimiento_service.py`
- [x] T031 [P] Run `/spec-kitti.swagger` (or update `swagger/openapi.yaml` if present) so the OpenAPI contract includes `endosar` and the new `MovimientoResponse` fields

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 → Phase 2 ──► US1 ──► US2
                       └────► US3
                              └──► Phase 6 (Polish)
```

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup; **bloquea** todas las stories.
- **US1 (P1)**: depende de Phase 2. Es el MVP.
- **US2 (P2)**: depende de US1 (`EndoseDialog`, `endosarCheque`, backend).
- **US3 (P3)**: depende del backend de US1 (T016–T018); independiente de US2.
- **Polish**: depende de las stories deseadas.

### Within Each User Story

- Tests (TDD) deben escribirse y **fallar** antes de implementar.
- Modelo/schemas → servicio → endpoint → frontend.
- Archivos compartidos (`movimiento_service.py`, `schemas/movimiento.py`, `routes/movimientos.py`, `ChequesPendientesBlock.tsx`, `RegistroCajaPage.tsx`, `index.css`) se editan en secuencia (las tareas respetan ese orden por ID).

### Parallel Opportunities

- Phase 2: T003 (test) en paralelo con T007 (`api.ts`); T004 → T005 secuenciales.
- US1: T008–T015 (tests) todos en paralelo; T022 en paralelo con T021 tras T019; el frontend T019–T020 puede avanzar en paralelo al backend T016–T018 usando el contrato.
- US2: T024 en paralelo con el cierre de US1 frontend (tras T019).
- US3: T026 en paralelo con US2 (tras T018).
- Polish: T030 y T031 en paralelo.
- **Equipos**: tras Phase 2, Dev A (backend US1: T008–T012 → T016–T018), Dev B (frontend US1: T013–T015 → T019–T023, luego US2), Dev C (US3 tras T018).

---

## Parallel Example: User Story 1

```bash
# Tests FIRST (all fail):
Task: "Service tests in backend/tests/unit/test_cheque_endose_service.py"                # T008
Task: "Concurrency tests in backend/tests/integration/test_cheques_endose_service.py"    # T009
Task: "Schema tests in backend/tests/unit/test_movimiento_endose_schema.py"              # T010
Task: "API tests in backend/tests/integration/test_cheques_endose_api.py"                # T011
Task: "Liquidar regression in backend/tests/integration/test_cheques_liquidar_api.py"    # T012
Task: "Dialog tests in frontend/tests/EndoseDialog.test.tsx"                             # T013
Task: "Block tests in frontend/tests/ChequesPendientesBlock.test.tsx"                    # T014
Task: "Table/page tests in frontend/tests/MovimientoTable.test.tsx + RegistroCajaPage"   # T015

# Then implementation in order:
# T016 → T017 → T018            (backend)
# T019 → T020 → T021 → T023     (frontend), T022 en paralelo con T021
```

---

## Implementation Strategy

### MVP First (US1)

1. Phase 1–2 (migración, modelo, tipos de API).
2. Phase 3 US1 (servicio atómico, endpoint, ventana, botón en Registro).
3. **STOP y validar**: cargar cheque → Endose → saldos de ambas cajas → registros finales, con ambos roles.

### Incremental Delivery

1. Foundational → 2. US1 (MVP) → 3. US2 (sección Cheques) y US3 (vistas derivadas) en paralelo → 4. Polish.

---

## Notes

- [P] = archivos distintos, sin depender de tareas incompletas del mismo archivo.
- TDD: rojo → implementar → verde. Las tareas de test llevan "FIRST/must fail"; la de implementación indica qué test deja en verde.
- UI: `wireframe:` (no Figma). Esta feature documenta en **Design Reference** que no usa Figma; `/spec-kitti.implement` no debe exigir `figma:`.
- Los tests de integración de subtotales y RBAC son **obligatorios** (constitución): T009, T011, T026.
- **FR-003 ya está implementado** en la feature 010 (backend 409 + botón deshabilitado): solo se agregan tests de regresión (T012, T014).
- La API es aditiva; único cambio de semántica: `editable=false` para cheques endosados y movimientos de endose.
- Sin dependencias nuevas; sin scheduler; sin cambios de infraestructura.
