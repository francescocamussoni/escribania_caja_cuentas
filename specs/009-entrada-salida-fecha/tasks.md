# Tasks: Botón Entrada+Salida Simultáneo y Selector de Fecha

**Branch**: `009-entrada-salida-fecha`  
**Input**: `specs/009-entrada-salida-fecha/` (plan.md, spec.md, data-model.md, contracts/, research.md, quickstart.md)  
**Testing**: TDD-first — tests escritos y fallando ANTES de cada implementación (spec § Testing Strategy)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias incompletas)
- **[Story]**: User Story a la que pertenece (US1/US2/US3)
- TDD: ⚠️ indica que el test debe escribirse PRIMERO y FALLAR antes de implementar

---

## Phase 1: Fundational — Migración y Modelo (bloqueante)

**Purpose**: La columna `fecha_override` y el índice COALESCE son prerequisito de todo el backend. Sin esta migración no pueden arrancarse WU-2, WU-3 ni WU-4.

**⚠️ CRÍTICO**: Ninguna tarea de backend puede comenzar hasta que esta fase esté completa.

- [x] T001 Crear migración Alembic `009_movimiento_fecha_override` en `backend/alembic/versions/009_movimiento_fecha_override.py` — ADD COLUMN `fecha_override TIMESTAMPTZ NULL`, reemplazar índice `idx_movimiento_caja_moneda_created` por expresión COALESCE
- [x] T002 Añadir campo `fecha_override: Mapped[datetime | None]` (nullable, `DateTime(timezone=True)`) al ORM en `backend/src/app/models/movimiento.py`
- [x] T003 Ejecutar `alembic upgrade head` y verificar que `alembic downgrade -1` + `alembic upgrade head` completa sin errores (verificación local)

**Checkpoint**: Migración aplicada. `Movimiento` ORM tiene `fecha_override`. Suite existente sigue en verde.

---

## Phase 2: US1 + US2 — Par Entrada+Salida y Eliminación del Diálogo (P1)

**Goal**: Registrar un par entrada+salida atómico para cualquier moneda (ARS y USD) desde el botón "Entrada y Salida". Eliminar el diálogo modal de confirmación complementario.

**Independent Test**: POST `/{caja_id}/movimientos` con `registrar_complementario: true` y `moneda: "ARS"` crea dos movimientos. Botón "Entrada" con moneda USD en el formulario registra directamente sin diálogo.

### Tests — US1/US2 Backend (TDD: escribir primero, deben FALLAR)

- [x] T004 [P] [US1] Escribir test unitario: `create_movimiento_pair` con `moneda="ARS"` crea par atómico con subtotales correctos en `backend/tests/unit/test_movimiento_service.py`
- [x] T005 [P] [US1] Escribir test unitario: `create_movimiento_pair` con `moneda="ARS"` hardcode eliminado — acepta parámetro moneda en `backend/tests/unit/test_movimiento_moneda.py`
- [x] T006 [P] [US2] Escribir test unitario: `CreateMovimientoRequest` con `registrar_complementario=True` y `moneda="ARS"` es válido (sin error 422) en `backend/tests/unit/test_movimiento_moneda.py`
- [x] T007 [P] [US1] Escribir test de integración: POST con `registrar_complementario: true, moneda: "ARS"` retorna 201 con `movimiento` y `complementario` no nulo en `backend/tests/integration/test_movimientos_api.py`
- [x] T008 [P] [US2] Escribir test de integración: POST con `registrar_complementario: false, moneda: "USD"` retorna 201 con `complementario: null` (sin diálogo en backend) en `backend/tests/integration/test_movimientos_api.py`

### Implementación — US1/US2 Backend

- [x] T009 [US2] Eliminar `model_validator` `validate_complementario_only_for_usd` de `CreateMovimientoRequest` en `backend/src/app/schemas/movimiento.py`
- [x] T010 [US1] Añadir parámetro `moneda: str` a `create_movimiento_pair` y eliminar hardcode `moneda="USD"` interno en `backend/src/app/services/movimiento_service.py`
- [x] T011 [US1] Actualizar llamada a `service.create_movimiento_pair(...)` en el router para pasar `moneda=payload.moneda` en `backend/src/app/api/routes/movimientos.py`
- [x] T012 [US1] Correr suite backend: `python -m pytest backend/tests/ -v` — todos los tests T004–T008 deben pasar

### Tests — US1/US2 Frontend (TDD: escribir primero, deben FALLAR)

- [x] T013 [US1] Crear `frontend/src/components/MovimientoForm.test.tsx` con test: renderiza botón "Entrada y Salida" en el DOM
- [x] T014 [P] [US1] Añadir test en `MovimientoForm.test.tsx`: al pulsar "Entrada y Salida", `onSubmit` se llama con `registrar_complementario: true` y `tipo: "entrada"`
- [x] T015 [P] [US2] Añadir test en `MovimientoForm.test.tsx`: al pulsar "Entrada" con moneda USD, `onSubmit` se llama directamente (sin render del diálogo modal)
- [x] T016 [P] [US2] Añadir test en `MovimientoForm.test.tsx`: el elemento `complementario-dialog-backdrop` NO está presente en el DOM para ninguna moneda

### Implementación — US1/US2 Frontend

- [x] T017 [US2] Eliminar estado `pendingTipo`, handlers `handleDialogConfirm` / `handleDialogCancel`, y todo el bloque JSX `complementario-dialog-backdrop` de `frontend/src/components/MovimientoForm.tsx`
- [x] T018 [US2] Actualizar `handleButtonClick` en `MovimientoForm.tsx` para llamar `doSubmit` directamente (sin bifurcación por moneda USD) en `frontend/src/components/MovimientoForm.tsx`
- [x] T019 [US1] Añadir botón "Entrada y Salida" (tipo `button`, clase `button btn-entrada-salida movimiento-form__action`) que llama `doSubmit("entrada", true)` en `frontend/src/components/MovimientoForm.tsx`
- [x] T020 [US1] Correr suite frontend: `npm run test -- --run` (desde `frontend/`) — tests T013–T016 deben pasar

**Checkpoint US1+US2**: Par ARS atómico funciona. Botones simples registran sin diálogo. Suite completa en verde.

---

## Phase 3: US3 — Selector de Fecha Manual (P2)

**Goal**: Selector de fecha opcional en el formulario. Movimientos con fecha manual se guardan a las 09:00 AM (UTC-3). Sin fecha seleccionada, comportamiento actual preservado.

**Independent Test**: POST con `fecha_manual: "2026-09-01"` retorna movimiento con `fecha = "2026-09-01T09:00:00-03:00"`. POST sin `fecha_manual` retorna `fecha` = timestamp del servidor.

### Tests — US3 Backend (TDD: escribir primero, deben FALLAR)

- [x] T021 [P] [US3] Escribir test unitario: `CreateMovimientoRequest` con `fecha_manual="2026-09-01"` es válido; con `fecha_manual="no-es-fecha"` lanza `ValidationError` en `backend/tests/unit/test_movimiento_moneda.py`
- [x] T022 [P] [US3] Escribir test unitario: `create_movimiento` con `fecha_override=datetime(2026,9,1,9,0,0,tzinfo=AR_TZ)` persiste ese valor en la columna en `backend/tests/unit/test_movimiento_service.py`
- [x] T023 [P] [US3] Escribir test unitario: ordenamiento COALESCE — movimiento con `fecha_override` en pasado queda antes de movimiento con `created_at` reciente en subtotales en `backend/tests/unit/test_movimiento_service.py`
- [x] T024 [P] [US3] Escribir test de integración: POST con `fecha_manual: "2026-09-01"` → response `fecha = "2026-09-01T09:00:00-03:00"` en `backend/tests/integration/test_movimientos_api.py`
- [x] T025 [P] [US3] Escribir test de integración: POST sin `fecha_manual` → response `fecha` igual a `created_at` del movimiento (sin regresión) en `backend/tests/integration/test_movimientos_api.py`
- [x] T026 [P] [US3] Escribir test de integración: POST con `registrar_complementario: true` y `fecha_manual: "2026-09-01"` → ambos movimientos del par tienen `fecha = "2026-09-01T09:00:00-03:00"` en `backend/tests/integration/test_movimientos_api.py`

### Implementación — US3 Backend

- [x] T027 [US3] Añadir campo `fecha_manual: date | None = None` con validador de formato `^\d{4}-\d{2}-\d{2}$` a `CreateMovimientoRequest` en `backend/src/app/schemas/movimiento.py`
- [x] T028 [US3] Añadir parámetro `fecha_override: datetime | None = None` a `create_movimiento` en `backend/src/app/services/movimiento_service.py` y persistirlo en el ORM
- [x] T029 [US3] Actualizar ORDER BY de `create_movimiento` (búsqueda del último del stream) a `COALESCE(fecha_override, created_at) DESC, id DESC` en `backend/src/app/services/movimiento_service.py`
- [x] T030 [US3] Actualizar ORDER BY de `recalculate_subtotals` a `COALESCE(fecha_override, created_at) ASC, id ASC` en `backend/src/app/services/movimiento_service.py`
- [x] T031 [US3] Añadir parámetro `fecha_override: datetime | None = None` a `create_movimiento_pair` y propagarlo a ambas llamadas internas en `backend/src/app/services/movimiento_service.py`
- [x] T032 [US3] En el router `create_movimiento`: calcular `fecha_override = datetime(año, mes, día, 9, 0, 0, tzinfo=_ARGENTINA_TZ)` cuando `payload.fecha_manual` presente; pasar a `service.create_movimiento` y `service.create_movimiento_pair` en `backend/src/app/api/routes/movimientos.py`
- [x] T033 [US3] Actualizar `movimiento_to_response` para retornar `fecha = movimiento.fecha_override or movimiento.created_at` en `backend/src/app/schemas/movimiento.py`
- [x] T034 [US3] Correr suite backend completa: `python -m pytest backend/tests/ -v` — tests T021–T026 deben pasar

### Tests — US3 Frontend (TDD: escribir primero, deben FALLAR)

- [x] T035 [P] [US3] Añadir test en `MovimientoForm.test.tsx`: renderiza campo `<input type="date">` con label "Fecha (opcional)"
- [x] T036 [P] [US3] Añadir test en `MovimientoForm.test.tsx`: al seleccionar una fecha y pulsar "Entrada", `onSubmit` recibe payload con `fecha_manual: "YYYY-MM-DD"`
- [x] T037 [P] [US3] Añadir test en `MovimientoForm.test.tsx`: sin fecha seleccionada, `onSubmit` recibe payload sin campo `fecha_manual` (o `undefined`)
- [x] T038 [P] [US3] Añadir test en `MovimientoForm.test.tsx`: cambiar `activeCajaId` NO resetea el valor del selector de fecha

### Implementación — US3 Frontend

- [x] T039 [US3] Añadir `fecha_manual?: string` a `CreateMovimientoPayload` en `frontend/src/services/api.ts`
- [x] T040 [US3] Añadir estado `fechaManual: string` (default `""`) en `MovimientoForm.tsx` en `frontend/src/components/MovimientoForm.tsx`
- [x] T041 [US3] Añadir campo `<input type="date">` con label "Fecha (opcional)" al formulario; sin reset en `useEffect` de `activeCajaId` en `frontend/src/components/MovimientoForm.tsx`
- [x] T042 [US3] Actualizar `doSubmit` para incluir `fecha_manual: fechaManual || undefined` en el payload enviado a `onSubmit` en `frontend/src/components/MovimientoForm.tsx`
- [x] T043 [US3] Correr suite frontend completa: `npm run test -- --run` (desde `frontend/`) — tests T035–T038 deben pasar

**Checkpoint US3**: Movimientos con fecha manual se persisten a 09:00 AM. Sin fecha, comportamiento sin regresión. Suite completa en verde.

---

## Phase 4: Polish & Validación Final

**Purpose**: Verificación cruzada, limpieza y validación del quickstart.

- [x] T044 [P] Correr suite backend completa final: `python -m pytest backend/tests/ -v` — 0 failures en `backend/`
- [x] T045 [P] Correr suite frontend completa final: `npm run test -- --run` (desde `frontend/`) — 0 failures en `frontend/`
- [x] T046 Verificar flujo manual del quickstart.md — 4 escenarios: (1) Entrada USD sin diálogo, (2) par ARS con "Entrada y Salida", (3) fecha manual en historial, (4) sin fecha = hora actual
- [x] T047 [P] Revisar logs de seguridad: verificar que `log_security_event` en `movimientos.py` incluye `complementario_id` para par ARS (igual que USD) en `backend/src/app/api/routes/movimientos.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Foundational)**: Sin dependencias — puede iniciar inmediatamente
- **Phase 2 (US1+US2)**: Depende de Phase 1 completa (necesita modelo ORM con `fecha_override`)
- **Phase 3 (US3)**: Depende de Phase 1 completa; puede ejecutarse en paralelo con Phase 2
- **Phase 4 (Polish)**: Depende de Phase 2 y Phase 3 completas

### User Story Dependencies

- **US1 (P1) + US2 (P1)**: Agrupadas por acoplamiento — US2 (eliminar diálogo) es parte del mismo cambio que US1 (botón). Se implementan juntas en Phase 2.
- **US3 (P2)**: Independiente de US1/US2 a nivel de schema y servicio. Comparte el modelo de Phase 1.

### Dentro de cada fase (TDD-first)

1. Tests TDD → deben escribirse y **fallar** antes de implementar
2. Modelo/Schema → antes de Servicio
3. Servicio → antes de Endpoint/Router
4. Endpoint → antes de Frontend
5. Frontend → último en cada fase

### Parallel Opportunities

- T004, T005, T006, T007, T008 pueden escribirse en paralelo (archivos distintos o secciones distintas)
- T013, T014, T015, T016 pueden escribirse en paralelo (mismo archivo, secciones independientes)
- T021–T026 pueden escribirse en paralelo
- T035–T038 pueden escribirse en paralelo
- T044, T045, T047 pueden ejecutarse en paralelo

---

## Parallel Example: Phase 2 (US1+US2)

```bash
# Lanzar escritura de tests en paralelo:
Task: "T004 — test unitario create_movimiento_pair con ARS"
Task: "T005 — test unitario moneda ARS en schema"
Task: "T006 — test unitario registrar_complementario ARS válido"
Task: "T007 — test integración par ARS respuesta 201"
Task: "T008 — test integración Entrada USD sin complementario"

# Luego implementar en orden:
T009 (schema) → T010 (servicio) → T011 (router) → T012 (verify backend)
T013–T016 (tests frontend) → T017→T018→T019 (frontend impl) → T020 (verify frontend)
```

---

## Implementation Strategy

### MVP (US1 + US2 — Phase 2 únicamente)

1. Completar Phase 1 (migración)
2. Completar Phase 2 (par ARS + eliminar diálogo)
3. **VALIDAR**: Suite completa en verde, flujo manual verificado
4. Deploy/demo si está listo

### Entrega incremental

1. Phase 1 → base de datos lista
2. Phase 2 → par ARS funciona, diálogo eliminado (MVP deployable)
3. Phase 3 → selector de fecha funciona
4. Phase 4 → polish y validación final

---

## Notes

- `[P]` = archivos distintos, sin dependencias incompletas entre sí
- `[US1]`, `[US2]`, `[US3]` mapean a User Stories del `spec.md`
- TDD: cada bloque de tests DEBE escribirse y **fallar** antes de la implementación correspondiente
- El campo `fecha_override` en base de datos es `NULL` para todos los movimientos existentes — no hay breaking change
- `_ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")` ya existe en `movimientos.py` — reutilizar
- Commit recomendado tras cada Checkpoint de fase
