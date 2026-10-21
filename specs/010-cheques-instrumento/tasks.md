# Tasks: Instrumento Cheque/Echeque, Sección Cheques y Saldo a Futuro

**Branch**: `010-cheques-instrumento`  
**Input**: `specs/010-cheques-instrumento/` (plan.md, spec.md, research.md, data-model.md, contracts/openapi-delta.yaml, quickstart.md)  
**Prerequisites**: plan.md, spec.md  
**Testing**: **TDD-first** — tests escritos y **fallando** ANTES de cada implementación (spec.md → Testing Strategy)

**Organization**: Tareas agrupadas por user story. Cada story es independientemente verificable; las tareas de test van antes de su implementación y deben fallar y luego pasar.

## Design Reference (UI)

Este proyecto **no usa Figma** para esta feature (no hay URL ni node-id en spec/plan; el desarrollador delegó el criterio y se mantiene el patrón de las features 004, 005 y 008). Las tareas UI usan el campo `wireframe:` (no `figma:`). Los elementos nuevos (Instrumento, Fecha de liquidación, bloque de cheques pendientes, Saldo a futuro, sección Cheques) **no figuran** en los `.drawio`: se definen en `spec.md` y su desviación de layout queda registrada en `plan.md` › Complexity Tracking (Principio III).

| Pantalla / pieza | Wireframe / fuente |
|---|---|
| Formulario de Registro (Descripción, Monto, Moneda, Fecha, **Instrumento**, **Fecha de liquidación**, Entrada/Salida) | `actual.drawio` (raíz) + spec FR-001–FR-007 |
| Valor de caja + **Saldo a futuro** (Registro) | `actual.drawio` + `registro_de_caja.drawio` + spec FR-022–FR-025 |
| Valor de caja + **Saldo a futuro** (Consulta) | `consulta_de_caja.drawio` + spec FR-022–FR-025 |
| Historial de Registro + **bloque de cheques pendientes** arriba | `registro_de_caja.drawio` + spec FR-015 |
| Historial de Consulta + bloque de cheques pendientes (solo lectura) | `consulta_de_caja.drawio` + spec FR-015 |
| **Sección Cheques** (dos listados) | `consulta_de_caja.drawio` (patrón selector/tabla/paginación) + spec FR-017–FR-021 |
| Barra de navegación (enlace **Cheques**) | `Navbar` actual (`frontend/src/components/layout/Navbar.tsx`) + spec FR-017 |
| Colores semánticos | Verde = entrada, rojo = salida (constitución, Principio III) |

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Paralelizable (archivos distintos, sin dependencias de tareas incompletas)
- **[USn]**: User story del `spec.md`
- Tareas UI (archivos `.tsx`/`.css` de componentes y páginas): llevan `wireframe:` en la línea siguiente (ver Design Reference)

## Path Conventions

- Backend: `backend/src/app/`, tests en `backend/tests/`
- Frontend: `frontend/src/`, tests en `frontend/tests/`
- Migración: `backend/alembic/versions/010_movimiento_cheque.py`
- Los tests de cada story van en archivos nuevos (`test_cheque_*.py`, `test_cheques_*_api.py`) para permitir trabajo en paralelo; los archivos de test legacy solo se extienden en la fase Foundational (paridad).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline verde y contrato alineado antes de TDD.

- [ ] T001 Verify branch `010-cheques-instrumento` and record the baseline: `python -m pytest tests/` in `backend/` and `npm run test -- --run` in `frontend/` (note any pre-existing failures)
- [ ] T002 [P] Confirm `specs/010-cheques-instrumento/contracts/openapi-delta.yaml` paths match `backend/src/app/api/router.py` prefixes (`/api/v1` + `/cajas`; new `/cheques`)

**Checkpoint**: Branch correcto; baseline conocido; contrato no choca con el router.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Migración y modelo de cheque, `fecha efectiva`, saldo por suma y refactor de paridad de las consultas existentes (stream, listado, saldos). **Bloquea todas las user stories.**

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests FIRST (must fail)

- [ ] T003 [P] Unit tests FIRST: `Movimiento` derived properties (`es_cheque`, `estado_cheque`, `impacta_saldo`, `fecha_carga`, `fecha_efectiva`) and CHECK constraints (invalid `instrumento`; cheque without `fecha_liquidacion`; `ninguno` with `fecha_liquidacion`/`fecha_liquidado`; `subtotal` NULL with `ninguno`; `subtotal` NOT NULL on a pending cheque) in `backend/tests/unit/test_movimiento_cheque_model.py` (new)
- [ ] T004 [P] Unit tests FIRST: `end_of_month` (28/29 Feb, 30/31-day months, December) in `backend/tests/unit/test_dates.py`
- [ ] T005 [P] Integration tests FIRST: `saldo_service` — saldo = SUM(entrada − salida) over rows with `subtotal IS NOT NULL`; equals last subtotal on a consistent stream; ignores pending cheques; counts liquidated cheques; `0.00` for empty caja; ARS/USD independent; correct with past `fecha_override` in `backend/tests/integration/test_saldo_service.py` (new)
- [ ] T006 [P] Integration parity tests FIRST: `GET /api/v1/cajas/{id}/saldo` and `/saldo-general` return the same values as before for common movements (with and without `fecha_override`); `ultimo_movimiento_at` uses effective date in `backend/tests/integration/test_cajas_saldo_moneda.py`
- [ ] T007 [P] Unit tests FIRST: stream queries (`create_movimiento` last-row lookup, `recalculate_subtotals`) ignore rows with `subtotal IS NULL` and order by effective date `COALESCE(fecha_liquidado, fecha_override, created_at)`; `create_movimiento` with `fecha_override` recalculates the stream (hardening); parity for movements without `fecha_override` in `backend/tests/unit/test_movimiento_service.py`
- [ ] T008 [P] Integration parity tests FIRST: `GET /api/v1/cajas/{id}/movimientos` excludes pending cheques (inserted directly in DB), orders and filters `fecha_desde`/`fecha_hasta` by effective date (Argentina TZ), unchanged for common movements in `backend/tests/integration/test_movimientos_api.py`

### Implementation

- [ ] T009 Add Alembic revision `010_movimiento_cheque` (down_revision `009_movimiento_fecha_override`): add `instrumento` (backfill `'ninguno'`, then NOT NULL), `fecha_liquidacion DATE NULL`, `fecha_liquidado TIMESTAMPTZ NULL`; make `subtotal` nullable; create `ck_movimiento_instrumento`, `ck_movimiento_cheque_fechas`, `ck_movimiento_subtotal_estado`; replace `idx_movimiento_caja_moneda_fecha` with partial `idx_movimiento_stream_efectiva`; add `idx_movimiento_cheque_pendiente` and `idx_movimiento_cheque_caja_pendiente`; `downgrade` aborts with a clear error if pending cheques exist in `backend/alembic/versions/010_movimiento_cheque.py`
- [ ] T010 Extend `Movimiento` with the new columns, nullable `subtotal`, the 3 CHECKs, derived properties and `effective_date_expr()` helper in `backend/src/app/models/movimiento.py` (T003 green)
- [ ] T011 [P] Add `end_of_month(d: date) -> date` in `backend/src/app/core/dates.py` (T004 green)
- [ ] T012 Verify `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` on a database with 009 data, and that downgrade aborts when a pending cheque exists, using `backend/alembic/versions/010_movimiento_cheque.py`
- [ ] T013 [P] Create `saldo_service` (`get_saldo_actual`, `get_saldos_caja`, `get_saldos_cajas_activas`) with aggregate query filtered by `subtotal IS NOT NULL` in `backend/src/app/services/saldo_service.py` (T005 green)
- [ ] T014 Use `saldo_service` in `GET /{caja_id}/saldo` (and `ultimo_movimiento_at` by effective date) in `backend/src/app/api/routes/cajas.py`, and in `list_saldos_cajas_activas` in `backend/src/app/services/caja_service.py` (T006 green)
- [ ] T015 Update `create_movimiento` / `recalculate_subtotals` to filter `impacta_saldo`, order by effective date, and recalculate after create when `fecha_override` is given in `backend/src/app/services/movimiento_service.py` (T007 green)
- [ ] T016 Update `list_movimientos` to return only rows that impact the balance and to order/filter by effective date (Argentina TZ) in `backend/src/app/api/routes/movimientos.py` (T008 green)
- [ ] T017 [P] Extend `frontend/src/services/api.ts` with `Instrumento`, `EstadoCheque`, widened `Movimiento` (`instrumento`, `estado`, nullable `subtotal`, `fecha_carga`, `fecha_liquidacion`, `fecha_liquidado`, `liquidable`), `CreateMovimientoPayload`/`UpdateMovimientoPayload` fields, `SaldoFuturo*` types, and `fetchChequesPendientes`, `fetchCheques`, `liquidarCheque`, `fetchSaldoFuturo` per `contracts/openapi-delta.yaml`

**Checkpoint**: Migración aplicada y reversible; saldos y listados con paridad legacy (suite completa verde); pendientes ya no pueden alterar un stream; tipos de API listos para el frontend.

---

## Phase 3: User Story 1 — Registrar un cheque/echeque sin afectar el subtotal (Priority: P1) 🎯 MVP

**Goal**: El formulario de Registro ofrece **Instrumento** (`-`, Cheque, Echeque); con Cheque/Echeque pide **Fecha de liquidación** (> hoy) y crea un cheque **pendiente** que aparece en el bloque de pendientes y **no** modifica subtotal ni Valor de caja. Con `-` todo funciona como hoy.

**Independent Test**: Caja con saldo conocido → Instrumento = Cheque, fecha de liquidación futura, **Entrada** → el cheque aparece en el bloque de pendientes (con ambas fechas y sin subtotal) y el Valor de caja no cambia; fecha vacía/hoy/pasada se rechaza; con `-` el comportamiento es idéntico al anterior. Spec US1. Quickstart pasos 1–7 de Secretaria.

### Tests for User Story 1 (TDD — write FIRST)

> Write these tests FIRST, ensure they FAIL before implementation

- [ ] T018 [P] [US1] Unit tests: `CreateMovimientoRequest` — cheque without `fecha_liquidacion` fails; `ninguno` with `fecha_liquidacion` fails; date today/past/invalid format/non-calendar fails; tomorrow passes; cheque + `registrar_complementario=true` fails; `extra="forbid"`; response DTO (`estado`, null `subtotal`, `fecha` = fecha de carga, `liquidable` by role) in `backend/tests/unit/test_movimiento_cheque_schema.py` (new; patch `today_ar` in `app.schemas.movimiento`)
- [ ] T019 [P] [US1] Unit tests: `create_movimiento` for a cheque stores `subtotal=None`, does not lock/touch the stream, leaves existing subtotals unchanged, honors `fecha_override` as fecha de carga in `backend/tests/unit/test_cheque_creacion_service.py` (new)
- [ ] T020 [P] [US1] Integration tests: `POST /api/v1/cajas/{id}/movimientos` with cheque/echeque → 201, `subtotal=null`, `/saldo` unchanged; entrada and salida; ARS and USD; invalid date/missing date/complementario → 422; Escribano 403; no token 401; the movement does not appear in `GET .../movimientos` in `backend/tests/integration/test_cheques_api.py` (new)
- [ ] T021 [P] [US1] Integration tests: `GET /api/v1/cajas/{id}/cheques-pendientes` — lists only pending ordered by `fecha_liquidacion ASC, id ASC`; filters `moneda` and `fecha_desde`/`fecha_hasta` by fecha de carga; page size 20 and pagination; excludes liquidated; 404 unknown caja; both roles OK; 401 in `backend/tests/integration/test_cheques_pendientes_api.py` (new)
- [ ] T022 [P] [US1] Component tests: **Instrumento** sits between *Fecha (opcional)* and *Entrada*, default `-`, options `-`/Cheque/Echeque; **Fecha de liquidación** appears only with Cheque/Echeque (`min` = tomorrow) and is discarded on return to `-`; **Entrada y Salida** unavailable with an instrument; payload carries `instrumento`/`fecha_liquidacion` only when applicable (identical payload with `-`); form resets after success; server error message in `frontend/tests/MovimientoForm.test.tsx`
- [ ] T023 [P] [US1] Component tests: `ChequesPendientesBlock` lists pending cheques with fecha de carga and fecha de liquidación, no subtotal, instrument badge, read-only mode (no actions), empty and error states, own pagination in `frontend/tests/ChequesPendientesBlock.test.tsx` (new)
- [ ] T024 [P] [US1] Component tests: Registro and Consulta pages render the pending block above the historial; Consulta has no action buttons for either role; `MovimientoTable` tolerates `subtotal: null` in `frontend/tests/RegistroCajaPage.test.tsx` and `frontend/tests/ConsultaCajaPage.test.tsx`

### Implementation for User Story 1 — Backend

- [ ] T025 [US1] Add `instrumento` and `fecha_liquidacion` to `CreateMovimientoRequest` (validators, cross-field rules, date > `today_ar()`), widen `MovimientoResponse` and `movimiento_to_response` (`instrumento`, `estado`, nullable `subtotal`, `fecha`, `fecha_carga`, `fecha_liquidacion`, `fecha_liquidado`, `liquidable`) in `backend/src/app/schemas/movimiento.py` (T018 green)
- [ ] T026 [US1] Support cheque creation (`subtotal=None`, no stream lookup/lock, `fecha_liquidacion` persisted) in `create_movimiento` in `backend/src/app/services/movimiento_service.py` (T019 green)
- [ ] T027 [US1] Wire cheque creation in `POST /{caja_id}/movimientos` (parse `fecha_liquidacion`, reject complementario for cheques, include `instrumento` in the `movimiento_created` security log, no amounts in logs) in `backend/src/app/api/routes/movimientos.py` (T020 green)
- [ ] T028 [US1] Add `GET /{caja_id}/cheques-pendientes` (any authenticated user, paginated 20, filters by fecha de carga in Argentina TZ, 404 on missing caja) in `backend/src/app/api/routes/movimientos.py` (T021 green)

### Implementation for User Story 1 — Frontend

- [ ] T029 [US1] Add **Instrumento** select and conditional **Fecha de liquidación** (required, `min` tomorrow), hide **Entrada y Salida** when an instrument is selected, send fields only when applicable, reset after success in `frontend/src/components/MovimientoForm.tsx` (T022 green)
  - wireframe: actual.drawio
- [ ] T030 [US1] Create `ChequesPendientesBlock` (paginated table: descripción, monto + moneda badge, instrumento, fecha de carga, fecha de liquidación; `readOnly` prop; empty/loading/error states; stacked `data-label` cells for mobile) in `frontend/src/components/ChequesPendientesBlock.tsx` (T023 green)
  - wireframe: registro_de_caja.drawio
- [ ] T031 [P] [US1] Make `MovimientoTable` null-safe for `subtotal` and mark liquidated cheques (Cheque/Echeque badge, estado Liquidado) in `frontend/src/components/MovimientoTable.tsx`
  - wireframe: registro_de_caja.drawio
- [ ] T032 [US1] Render the pending block above the historial and refresh it after creating a cheque (including additional cajas: one POST per caja with the same payload) in `frontend/src/pages/RegistroCajaPage.tsx` (T024 green)
  - wireframe: registro_de_caja.drawio
- [ ] T033 [P] [US1] Render the pending block in read-only mode above the historial in `frontend/src/pages/ConsultaCajaPage.tsx` (T024 green)
  - wireframe: consulta_de_caja.drawio
- [ ] T034 [US1] Add styles for the Instrumento/Fecha de liquidación fields, pending block, badges and mobile stacking without breaking the existing form grid in `frontend/src/index.css`
  - wireframe: actual.drawio

**Checkpoint**: US1 — se carga un cheque pendiente sin alterar saldos; con `-` el flujo es idéntico. Suite completa verde.

---

## Phase 4: User Story 2 — Liquidar un cheque y registrar la fecha de liquidado (Priority: P1)

**Goal**: **Liquidar** guarda la *fecha liquidado*, pasa el cheque a Liquidado e incorpora su monto al saldo (entrada suma, salida resta), ubicándolo al final del historial; no se puede liquidar dos veces; el Escribano no puede.

**Independent Test**: Cheque pendiente de entrada 500 en caja con saldo 1000 → **Liquidar** → Valor de caja 1500, el cheque aparece en el historial con su subtotal y fecha liquidado, desaparece de pendientes; segunda liquidación → 409 sin duplicar. Spec US2. Quickstart paso 9.

### Tests for User Story 2 (TDD — write FIRST)

- [ ] T035 [P] [US2] Unit tests: `liquidar_cheque` — entrada adds / salida subtracts; `fecha_liquidado` = now; `updated_by`/`updated_at` set; cheque placed at the end by effective date; stream recalculated (also with a future-dated manual movement); already liquidated → domain error (409); common movement or other caja → not found; failure leaves cheque pending in `backend/tests/unit/test_cheque_liquidacion.py` (new)
- [ ] T036 [P] [US2] Integration tests: `POST /api/v1/cajas/{id}/movimientos/{mid}/liquidar` → 200 and `/saldo` updated for entrada and salida, ARS and USD; cheque now appears in `GET .../movimientos` with subtotal; second call 409 and balance not duplicated; common movement → 404; wrong caja → 404; Escribano 403; no token 401; pending date reached does not auto-liquidate in `backend/tests/integration/test_cheques_liquidar_api.py` (new)
- [ ] T037 [P] [US2] Component tests: **Liquidar** button only when `liquidable`; confirmation; calls `liquidarCheque`; on success the block reloads; on error the cheque stays and a message is shown in `frontend/tests/ChequesPendientesBlock.test.tsx`
- [ ] T038 [P] [US2] Component tests: liquidating from Registro refreshes Valor de caja, historial and pending block; Escribano sees no Liquidar in `frontend/tests/RegistroCajaPage.test.tsx`

### Implementation for User Story 2

- [ ] T039 [US2] Implement `liquidar_cheque` (lock order caja → cheque row → stream; 409/not-found domain errors; set `fecha_liquidado`/`updated_*`; `recalculate_subtotals`) in `backend/src/app/services/movimiento_service.py` (T035 green)
- [ ] T040 [US2] Add `POST /{caja_id}/movimientos/{movimiento_id}/liquidar` (`require_role("secretaria")`, commit/rollback, 404/409 mapping, `cheque_liquidated` security log without amounts) in `backend/src/app/api/routes/movimientos.py` (T036 green)
- [ ] T041 [US2] Add **Liquidar** action (visible only when `liquidable`, confirmation, `onLiquidar` callback) to `frontend/src/components/ChequesPendientesBlock.tsx` (T037 green)
  - wireframe: registro_de_caja.drawio
- [ ] T042 [US2] Handle liquidation in Registro (call `liquidarCheque`, refresh saldo + historial + pending block, show generic error on failure) in `frontend/src/pages/RegistroCajaPage.tsx` (T038 green)
  - wireframe: registro_de_caja.drawio

**Checkpoint**: US1+US2 — ciclo completo pendiente → liquidado con atomicidad e idempotencia.

---

## Phase 5: User Story 3 — Sección Cheques: próximos a liquidar y aptos para liquidar (Priority: P2)

**Goal**: Nueva sección **Cheques** (entre *Consulta plazos fijos* e *Impresión*) con los cheques pendientes de **todas las cajas** en **Aptos para liquidar** y **Próximos a liquidar este mes**, con **Liquidar** para la secretaria; solo lectura para el Escribano.

**Independent Test**: Cheques pendientes en distintas cajas (fechas ≤ hoy, dentro del mes, mes siguiente) y uno liquidado → la sección muestra solo los de las dos categorías correctas, ordenados, paginados; secretaria puede liquidar desde allí; escribano no. Spec US3. Quickstart paso 10.

### Tests for User Story 3 (TDD — write FIRST)

- [ ] T043 [P] [US3] Integration tests: `GET /api/v1/cheques?categoria=aptos|proximos` — boundaries (today and past → aptos; tomorrow..end of month → proximos; next month excluded); excludes liquidated; several cajas including archived; order by `fecha_liquidacion ASC, id ASC`; page size 20; invalid `categoria`/`page` → 422; `liquidable` by role; 401 (patch `today_ar` in `app.api.routes.cheques`) in `backend/tests/integration/test_cheques_seccion_api.py` (new)
- [ ] T044 [P] [US3] Component tests: `ChequesPage` shows two listings with the required columns (caja, instrumento, descripción, tipo, moneda, monto, fecha de carga, fecha de liquidación), empty states, independent pagination, Liquidar only for Secretaria and reload after success in `frontend/tests/ChequesPage.test.tsx` (new)
- [ ] T045 [P] [US3] Component tests: Navbar link order `… Consulta plazos fijos, Cheques, Impresión`, visible for both roles in `frontend/tests/Navbar.test.tsx`
- [ ] T046 [P] [US3] Component tests: route `/cheques` redirects to login without session and is reachable by both roles in `frontend/tests/AppRoutes.test.tsx`

### Implementation for User Story 3

- [ ] T047 [US3] Create `GET /cheques` (any authenticated user; `categoria` Literal; fixed page size 20; pending only; `hoy_ar` and `end_of_month`; includes caja data) in `backend/src/app/api/routes/cheques.py` (T043 green)
- [ ] T048 [US3] Register the `cheques` router with prefix `/cheques` in `backend/src/app/api/router.py`
- [ ] T049 [US3] Create `ChequesPage` (two listings with their own `Pagination`, `Liquidar` for Secretaria via `liquidarCheque`, empty/loading/error states, stacked cells on mobile) in `frontend/src/pages/ChequesPage.tsx` (T044 green)
  - wireframe: consulta_de_caja.drawio
- [ ] T050 [P] [US3] Add the **Cheques** link between *Consulta plazos fijos* and *Impresión* for roles `secretaria` and `escribano` in `frontend/src/components/layout/Navbar.tsx` (T045 green)
  - wireframe: frontend/src/components/layout/Navbar.tsx (barra actual; spec FR-017)
- [ ] T051 [P] [US3] Add protected route `/cheques` (both roles) in `frontend/src/App.tsx` (T046 green)
  - wireframe: frontend/src/components/layout/Navbar.tsx (barra actual; spec FR-017)
- [ ] T052 [US3] Add styles for the Cheques page and its listings in `frontend/src/index.css`
  - wireframe: consulta_de_caja.drawio

**Checkpoint**: US3 — sección Cheques operativa para ambos roles.

---

## Phase 6: User Story 4 — Saldo a futuro en Valor de caja (Priority: P2)

**Goal**: Desplegable **Saldo a futuro** en *Valor de caja* (Registro y Consulta): saldo de hoy y saldo proyectado acumulado por cada fecha de liquidación de cheques pendientes, por moneda, con vencidos marcados.

**Independent Test**: Saldo ARS 1000, cheque entrada 500 (D1) y salida 200 (D2 > D1) → expandir: Hoy 1000; D1 1500; D2 1300. Misma fecha → una fila; vencidos marcados; ARS/USD separados; sin cheques → solo saldo de hoy. Spec US4. Quickstart paso 7.

### Tests for User Story 4 (TDD — write FIRST)

- [ ] T053 [P] [US4] Unit tests: `proyectar_saldo_futuro` — cumulative example (1000 → 1500 → 1300), grouping by date, ascending order, `vencido` (`<= hoy`), entrada adds / salida subtracts, negative balance, empty list, ARS and USD independent in `backend/tests/unit/test_saldo_futuro.py` (new)
- [ ] T054 [P] [US4] Integration tests: `GET /api/v1/cajas/{id}/saldo-futuro` — spec example, grouping, vencidos included, liquidated excluded and absorbed into `saldo_actual`, ARS/USD, no pending → only today's balance, both roles 200, 404, 401 in `backend/tests/integration/test_saldo_futuro_api.py` (new)
- [ ] T055 [P] [US4] Component tests: `SaldoFuturoDesplegable` collapsed by default; loads on expand; "Hoy" row per moneda; rows with accumulated projection and **Vencido** mark; ARS/USD separated; empty message; loading/error; reloads when `refreshKey` or `cajaId` changes in `frontend/tests/SaldoFuturoDesplegable.test.tsx` (new)
- [ ] T056 [P] [US4] Component tests: the desplegable is inside *Valor de caja* in Registro and in Consulta (single caja mode, not in the joint view) and the ARS/USD banner is unchanged in `frontend/tests/ConsultaCajaPage.test.tsx` and `frontend/tests/RegistroCajaPage.test.tsx`

### Implementation for User Story 4

- [ ] T057 [P] [US4] Implement pure `proyectar_saldo_futuro(saldo_actual, cheques, hoy)` (Decimal, grouped by `fecha_liquidacion`, cumulative, `vencido`) in `backend/src/app/services/saldo_futuro.py` (T053 green)
- [ ] T058 [US4] Add `SaldoFuturoFila`, `SaldoFuturoMoneda`, `SaldoFuturoResponse` DTOs in `backend/src/app/schemas/movimiento.py`
- [ ] T059 [US4] Add `GET /{caja_id}/saldo-futuro` (any authenticated user; uses `saldo_service` + pending cheques per moneda + `proyectar_saldo_futuro`; 404 on missing caja) in `backend/src/app/api/routes/cajas.py` (T054 green)
- [ ] T060 [US4] Create `SaldoFuturoDesplegable` (`<details>`, lazy load on expand, `refreshKey`, per-moneda tables, Vencido mark, empty/loading/error) in `frontend/src/components/SaldoFuturoDesplegable.tsx` (T055 green)
  - wireframe: actual.drawio
- [ ] T061 [US4] Embed the desplegable in the *Valor de caja* section of Registro and bump `refreshKey` after create/edit/delete/liquidate in `frontend/src/pages/RegistroCajaPage.tsx` (T056 green)
  - wireframe: registro_de_caja.drawio
- [ ] T062 [P] [US4] Embed the desplegable in the *Valor de caja* section of Consulta (single caja mode) in `frontend/src/pages/ConsultaCajaPage.tsx` (T056 green)
  - wireframe: consulta_de_caja.drawio
- [ ] T063 [US4] Add styles for the desplegable and its projection tables (mobile stacking) in `frontend/src/index.css`
  - wireframe: actual.drawio

**Checkpoint**: US4 — proyección de saldo visible en Registro y Consulta.

---

## Phase 7: User Story 5 — Editar y eliminar cheques pendientes (Priority: P3)

**Goal**: La secretaria corrige o elimina cheques pendientes sin tocar subtotales; el instrumento solo cambia entre Cheque y Echeque; `fecha_liquidacion` solo editable en pendientes y > hoy; liquidados siguen las reglas actuales.

**Independent Test**: Editar monto y fecha de liquidación de un pendiente → Valor de caja intacto; cambiar Cheque↔Echeque OK; intentar `-` → rechazado; eliminar → desaparece de pendientes, de Cheques y de Saldo a futuro. Spec US5. Quickstart paso 8.

### Tests for User Story 5 (TDD — write FIRST)

- [ ] T064 [P] [US5] Unit tests: `update_movimiento` on a pending cheque does not recalculate any stream (monto/tipo/moneda/instrumento↔/fecha_liquidacion); common movement + `instrumento`/`fecha_liquidacion` → `ValueError`; `fecha_liquidacion` on a liquidated cheque → `ValueError`; liquidated cheque edit recalculates cascade (and the old moneda stream); `delete_movimiento` of pending without recalculation, of liquidated with recalculation in `backend/tests/unit/test_cheque_edicion.py` (new)
- [ ] T065 [P] [US5] Unit tests: `UpdateMovimientoRequest` — `instrumento="ninguno"` fails; `cheque`/`echeque` valid; `fecha_liquidacion` same rules as create; at least one field; `extra="forbid"` in `backend/tests/unit/test_movimiento_cheque_update_schema.py` (new)
- [ ] T066 [P] [US5] Integration tests: `PATCH`/`DELETE` of cheques via API — 200/204 on pending without balance change; 400 on common movement with instrument fields and on `fecha_liquidacion` of a liquidated cheque; 422 for `ninguno` and for date <= today; liquidated cheque edit recalculates; Escribano 403; 404 in `backend/tests/integration/test_cheques_edicion_api.py` (new)
- [ ] T067 [P] [US5] Component tests: block **Editar**/**Eliminar** (Registro only); edit panel offers Cheque/Echeque (never `-`), fecha de liquidación `min` tomorrow, monto/descripción/tipo; delete confirmation; balance unchanged after edit in `frontend/tests/ChequesPendientesBlock.test.tsx` and `frontend/tests/RegistroCajaPage.test.tsx`

### Implementation for User Story 5

- [ ] T068 [US5] Add `instrumento` (`cheque`|`echeque` only) and `fecha_liquidacion` to `UpdateMovimientoRequest` with validators and at-least-one-field rule in `backend/src/app/schemas/movimiento.py` (T065 green)
- [ ] T069 [US5] Apply cheque rules in `update_movimiento` and `delete_movimiento` (no recalculation for pending; cascade for liquidated; `ValueError` cases) in `backend/src/app/services/movimiento_service.py` (T064 green)
- [ ] T070 [US5] Map new service errors to 400/404 and extend update/delete logs (no amounts) in `PATCH`/`DELETE` of `backend/src/app/api/routes/movimientos.py` (T066 green)
- [ ] T071 [US5] Add **Editar** / **Eliminar** actions (hidden in read-only mode) to `frontend/src/components/ChequesPendientesBlock.tsx` (T067 green)
  - wireframe: registro_de_caja.drawio
- [ ] T072 [US5] Extend the edit panel for cheques (Cheque↔Echeque select without `-`, fecha de liquidación for pendings, hide for liquidated), delete flow and refresh of saldo/block/desplegable in `frontend/src/pages/RegistroCajaPage.tsx` (T067 green)
  - wireframe: registro_de_caja.drawio

**Checkpoint**: US5 — corrección de cheques sin riesgo para subtotales.

---

## Phase 8: User Story 6 — Informe impreso de caja con cheques pendientes y saldo a futuro (Priority: P3)

**Goal**: El PDF de tipo **Caja** lista solo movimientos que impactan el saldo (cheques liquidados marcados), agrega la sección **Cheques pendientes** y el **Saldo a futuro** (estado actual, no filtrado por período); Plazos Fijos no cambia.

**Independent Test**: Caja con saldo ARS 1000, cheque pendiente de entrada 500 (D1) y movimientos en el período → PDF sin el pendiente en el listado, saldos al cierre/actual sin cambios, sección Cheques pendientes con el cheque y Saldo a futuro Hoy 1000 / D1 1500. Spec US6.

### Tests for User Story 6 (TDD — write FIRST)

- [ ] T073 [P] [US6] Unit tests: `fetch_movimientos_informe` excludes pending and filters/orders by effective date; `compute_saldo_cierre*` by effective date; saldos actuales via `saldo_service`; `fetch_cheques_pendientes` (all pending of the caja, cap 1000) and `fetch_saldo_futuro` equal the API projection in `backend/tests/unit/test_informe_service.py`
- [ ] T074 [P] [US6] Unit tests: `render_caja_pdf` — `[Cheque]`/`[Echeque]` mark on liquidated cheques; **Cheques pendientes** section with and without rows; **Saldo a futuro** section per moneda; extractable text; `render_plazo_fijo_pdf` unchanged in `backend/tests/unit/test_pdf_informe_renderer.py`
- [ ] T075 [P] [US6] Integration tests: `POST /api/v1/informes/pdf` tipo CAJA includes both new sections for both roles; past period still shows current pendings/projection and generation timestamp; saldos unaffected by pendings; tipo PLAZO_FIJO identical in `backend/tests/integration/test_informes_api.py`

### Implementation for User Story 6

- [ ] T076 [US6] Update `InformeService` (`impacta_saldo` + effective date in movements and closing balances, `saldo_service` for current balances, new `fetch_cheques_pendientes` and `fetch_saldo_futuro`) in `backend/src/app/services/informe_service.py` (T073 green)
- [ ] T077 [US6] Update `render_caja_pdf` (latin-1 safe labels: `[Cheque]`/`[Echeque]` prefix, section "Cheques pendientes", section "Saldo a futuro", cap note) in `backend/src/app/services/pdf_informe_renderer.py` (T074 green)
- [ ] T078 [US6] Pass pending cheques and saldo a futuro to the renderer for tipo CAJA in `backend/src/app/api/routes/informes.py` (T075 green)

**Checkpoint**: US6 — informe de Caja completo y consistente con pantalla.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Seguridad, RBAC, responsive y verificación final.

- [ ] T079 [P] Integration RBAC matrix for every new/changed endpoint (create/update/delete/liquidar → Escribano 403, no token 401; saldo-futuro, cheques-pendientes, `/cheques`, informe → both roles 200) in `backend/tests/integration/test_consulta_rbac.py`
- [ ] T080 [P] Responsive tests: new tables (pending block, Cheques page, saldo a futuro) expose `data-label` stacked cells like the existing listings in `frontend/tests/listadoStackedFields.test.tsx`
- [ ] T081 [P] Unit tests for logging hygiene: `movimiento_created`, `cheque_liquidated`, `movimiento_updated/deleted` log `username`/`rol`/ids only (no amounts or descriptions) in `backend/tests/unit/test_logging.py`
- [ ] T082 Run the full suites and build: `python -m pytest tests/` in `backend/`; `npm run test -- --run` and `npm run build` in `frontend/` (all green, no regression vs. T001 baseline)
- [ ] T083 Execute the manual verification in `specs/010-cheques-instrumento/quickstart.md` with **both roles** (Secretaria and Escribano) and the edge cases (double liquidation, cajas adicionales, historical movements, Subtotal general / Valor en conjunto)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup — **bloquea** todas las user stories.
- **US1 (Phase 3)** → depende de Foundational. Es el MVP técnico.
- **US2 (Phase 4)** → depende de US1 (necesita cheques pendientes y el bloque).
- **US3 (Phase 5)** → depende de Foundational y de US1 (datos); el botón Liquidar requiere US2 (T040/`liquidarCheque`).
- **US4 (Phase 6)** → depende de Foundational (saldo, modelo); para probar con datos reales usa US1, pero la lógica pura (T053/T057) es independiente.
- **US5 (Phase 7)** → depende de US1 (cheques existentes) y usa el bloque (T030/T041).
- **US6 (Phase 8)** → depende de US4 (T057 `saldo_futuro`) y de Foundational.
- **Polish (Phase 9)** → depende de las stories deseadas.

### User Story Dependencies

```
Phase 1 → Phase 2 ──► US1 ──► US2 ──► US3 (Liquidar en la sección)
                  │      └──► US5
                  └──► US4 ──► US6
```

### Within Each User Story

- Tests (TDD) deben escribirse y **fallar** antes de implementar.
- Modelo/schemas → servicios → endpoints → frontend.
- Los archivos compartidos (`movimientos.py`, `movimiento_service.py`, `schemas/movimiento.py`, `RegistroCajaPage.tsx`, `ChequesPendientesBlock.tsx`, `index.css`) se editan en secuencia, no en paralelo (las tareas respetan ese orden por ID).

### Parallel Opportunities

- Phase 2: T003–T008 (tests) en paralelo; T011, T013 y T017 en paralelo con la migración tras T010.
- US1: T018–T024 en paralelo; T031 y T033 en paralelo con el resto del frontend.
- US2: T035–T038 en paralelo.
- US3: T043–T046 en paralelo; T050 y T051 en paralelo.
- US4: T053–T056 en paralelo; T057 en paralelo con DTOs/endpoint de tests; T062 en paralelo con T061.
- US5: T064–T067 en paralelo.
- US6: T073–T075 en paralelo.
- **Equipos**: tras Phase 2, Dev A (backend US1→US2→US5), Dev B (frontend US1 desde T029/T030 usando `api.ts` T017), Dev C (US4 puro: T053/T057 + endpoint) y luego US3/US6.

---

## Parallel Example: User Story 1

```bash
# Tests FIRST (all fail):
Task: "Schema tests in backend/tests/unit/test_movimiento_cheque_schema.py"            # T018
Task: "Service tests in backend/tests/unit/test_cheque_creacion_service.py"            # T019
Task: "API tests in backend/tests/integration/test_cheques_api.py"                      # T020
Task: "Pending list API tests in backend/tests/integration/test_cheques_pendientes_api.py"  # T021
Task: "Form tests in frontend/tests/MovimientoForm.test.tsx"                            # T022
Task: "Block tests in frontend/tests/ChequesPendientesBlock.test.tsx"                   # T023
Task: "Page tests in frontend/tests/RegistroCajaPage.test.tsx / ConsultaCajaPage.test.tsx"  # T024

# Then implementation in order:
# T025 → T026 → T027 → T028   (backend)
# T029, T030, T031 → T032, T033 → T034   (frontend)
```

---

## Implementation Strategy

### MVP First (US1 + US2 — ambas P1)

1. Phase 1–2 (migración, modelo, saldo por suma, paridad).
2. Phase 3 US1 (cargar cheque pendiente sin impacto).
3. Phase 4 US2 (liquidar). Un cheque que no se puede liquidar deja el flujo incompleto, por eso US1 y US2 se entregan juntas.
4. **STOP y validar**: carga → pendiente → liquidar → saldo, con ambos roles.

### Incremental Delivery

1. Foundational → 2. US1+US2 (MVP) → 3. US3 (sección Cheques) y US4 (saldo a futuro) en paralelo → 4. US5 (edición) → 5. US6 (informe) → 6. Polish.

### Parallel Team Strategy

1. Juntos: Phase 1–2.
2. Dev A: backend US1 → US2 → US5. Dev B: frontend US1 → US2 → US3 → US5. Dev C: US4 → US6.

---

## Notes

- [P] = archivos distintos, sin depender de tareas incompletas del mismo archivo.
- TDD: rojo → implementar → verde. Las tareas de test llevan "FIRST/must fail"; la tarea de implementación indica qué test deja en verde.
- UI: `wireframe:` (no Figma). Esta feature documenta en **Design Reference** que no usa Figma; `/spec-kitti.implement` no debe exigir `figma:`.
- Los tests de integración de subtotales y RBAC son **obligatorios** (constitución): T005–T008, T020, T036, T043, T054, T066, T079.
- Tests de cada story en archivos nuevos (`test_cheque_*`, `test_cheques_*_api`); se apartan levemente del plan (que listaba extender `test_movimiento_service.py`, `test_movimientos_api.py`, etc.) para permitir paralelismo; los legacy se extienden solo en Foundational y Polish.
- La API es aditiva; único cambio de tipo: `subtotal` puede ser `null` en cheques pendientes (no aparecen en `GET .../movimientos`).
- La llegada de la fecha de liquidación **no** liquida automáticamente: no hay scheduler en esta feature.
- Cajas adicionales: N POST con el mismo payload (un cheque pendiente independiente por caja).
