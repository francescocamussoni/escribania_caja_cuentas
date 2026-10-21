# Implementation Plan: Instrumento Cheque/Echeque, Sección Cheques y Saldo a Futuro

**Branch**: `010-cheques-instrumento` | **Date**: 2026-10-21 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/010-cheques-instrumento/spec.md`

---

## Summary

Agregar el concepto de **cheque / echeque** a los movimientos de caja:

1. **Registro**: desplegable **Instrumento** (`-`, Cheque, Echeque) entre *Fecha (opcional)* y *Entrada*. Con Cheque/Echeque aparece **Fecha de liquidación** (estrictamente futura) y el registro queda **pendiente**: aparece en la caja pero **no impacta** el saldo hasta que la secretaria pulsa **Liquidar** (que guarda la *fecha liquidado* y recién ahí suma/resta).
2. **Sección Cheques** (entre *Consulta plazos fijos* e *Impresión*): pendientes de todas las cajas, en **Aptos para liquidar** y **Próximos a liquidar este mes**, con **Liquidar** para la secretaria.
3. **Saldo a futuro**: desplegable en *Valor de caja* (Registro y Consulta) con el saldo de hoy y el saldo proyectado acumulado por cada fecha de liquidación de cheques pendientes, por moneda.
4. **Impresión (informe de Caja)**: sección *Cheques pendientes* y *Saldo a futuro*; el resto del informe y los saldos solo consideran movimientos que impactan el saldo.

**Enfoque técnico** (detalle en [research.md](./research.md)):

- Extender `movimiento` (no tabla nueva): `instrumento`, `fecha_liquidacion`, `fecha_liquidado` + `subtotal` nullable protegido por `CHECK`s. Un cheque pendiente tiene `subtotal = NULL`; "impacta el saldo" ≙ `subtotal IS NOT NULL`.
- **Fecha efectiva** única `COALESCE(fecha_liquidado, fecha_override, created_at)` para orden, filtros y saldos (hoy los saldos/informes ordenan por `created_at` y no respetan `fecha_override`).
- **Saldo actual por suma** (`saldo_service`) en lugar de "subtotal de la última fila": independiente del orden, robusto ante subtotales desactualizados.
- **Liquidación atómica** con lock de caja + fila, `409` si ya liquidado, y recálculo del stream.
- **Saldo a futuro** como función pura (`saldo_futuro.py`) reutilizada por la API y el PDF → valores idénticos (SC-009).
- API aditiva; sin dependencias nuevas; sin scheduler (la llegada de la fecha **no** liquida sola).

---

## Technical Context

**Language/Version**: Python 3.12 (backend) · TypeScript 5.6 / React 18.3 (frontend)  
**Primary Dependencies**: FastAPI 0.115, SQLAlchemy 2.0, Alembic 1.14, Pydantic 2.10, fpdf2 2.8 (informes), React Router 6, Vite 5 — **sin dependencias nuevas**  
**Storage**: PostgreSQL 16 (local + AWS RDS) — columnas nuevas en `movimiento` + migración Alembic `010`  
**Testing**: pytest (unit + integración sobre Postgres) · Vitest 2 + Testing Library 16 · **TDD-first** (decisión de la spec)  
**Target Platform**: Linux server (backend) · Navegador web (frontend)  
**Project Type**: Web application (`backend/` + `frontend/`)  
**Performance Goals**: Saldo a futuro < 2 s con hasta 100 cheques pendientes (SC-008); alta de cheque ≤ operación simple  
**Constraints**: Cheques pendientes jamás alteran subtotal/saldo (SC-002); liquidación atómica e idempotente (409); cálculos de saldo/proyección solo en servidor (Principio V); zona horaria Argentina (UTC-3) para "hoy" y "este mes"; PDF con fuente core latin-1  
**Scale/Scope**: ≤ 10 usuarios concurrentes · 15 cajas (+ cajas configurables) · 2 monedas (ARS/USD) · cientos de cheques

---

## Constitution Check

*GATE: evaluado antes de Phase 0. Re-evaluado post-diseño (abajo).*

| Principio | Estado | Evidencia |
|---|---|---|
| **I. Integridad Financiera de Caja** | ✅ PASS | Los cheques pendientes quedan fuera del stream por diseño de datos (`subtotal NULL` + `ck_movimiento_subtotal_estado`). Subtotales siguen siendo acumulados cronológicos **por (caja, moneda)**; la liquidación recalcula el stream en orden de fecha efectiva. ARS/USD nunca se mezclan (proyección por moneda). Edición/eliminación de movimientos que impactan saldo mantiene el recálculo en cascada. |
| **II. RBAC** | ✅ PASS | Crear/editar/eliminar/liquidar → `require_role("secretaria")` (403 al Escribano). Lecturas (`saldo-futuro`, `cheques-pendientes`, `/cheques`) → ambos roles. Auditoría: `created_by` / `updated_by` + eventos `cheque_liquidated`, `movimiento_*`. |
| **III. Fidelidad al Diseño (Wireframes)** | ⚠️ PASS CON DESVIACIÓN DOCUMENTADA | Se extiende (sin romper) el layout de `registro_de_caja.drawio` / `consulta_de_caja.drawio`: nuevo campo **Instrumento** (+ **Fecha de liquidación** condicional) en el formulario, bloque **cheques pendientes** sobre el historial, desplegable **Saldo a futuro** dentro de *Valor de caja* y enlace **Cheques** en la barra. Ninguno figura en los wireframes; todos fueron pedidos explícitamente por el usuario (ver Complexity Tracking). Colores semánticos se respetan (verde = entrada, rojo = salida). |
| **IV. Seguridad por Diseño** | ✅ PASS | Validación server-side por esquema (Pydantic, `extra="forbid"`, fecha futura, combinaciones instrumento/fecha); autorización en cada endpoint; consultas parametrizadas (SQLAlchemy); listados paginados con tamaño máximo; DTOs explícitos; errores genéricos; logs sin montos ni PII; sin secretos. Deadlocks evitados con orden de locks definido; `409` en doble liquidación. |
| **V. Arquitectura Fullstack Desacoplada** | ✅ PASS | Proyección y saldos calculados en backend; el frontend solo presenta. Contratos explícitos en `contracts/openapi-delta.yaml`. |
| **VI. Costo Mínimo en AWS** | ✅ PASS | Sin servicios, endpoints de infraestructura, scheduler ni dependencias nuevas; solo columnas e índices parciales en la tabla existente. |

**Constraints técnicas**: PostgreSQL ✔ · monedas ARS/USD independientes ✔ · paginación obligatoria en listados ✔ · catálogo de cajas sin cambios ✔.  
**Tests obligatorios** (subtotales y RBAC, Reglas de Implementación) ✔ planificados en WU-2, WU-4 y WU-5.

### Re-check post-diseño (Phase 1)

**PASS.** Las decisiones de Phase 1 no introducen violaciones:
- `subtotal` nullable es la única relajación de integridad; queda compensada por 3 `CHECK`s y por el helper único de "impacta saldo".
- El cambio de "último subtotal" a "suma" en el saldo es **equivalente** en streams consistentes y estrictamente más robusto (se prueba con tests de paridad).
- La desviación de wireframes (Principio III) se documenta en **Complexity Tracking** y se valida con los usuarios en la verificación manual.

---

## Project Structure

### Documentation (this feature)

```text
specs/010-cheques-instrumento/
├── plan.md                    ← este archivo
├── research.md                ← Phase 0 ✅
├── data-model.md              ← Phase 1 ✅
├── quickstart.md              ← Phase 1 ✅
├── contracts/
│   └── openapi-delta.yaml     ← Phase 1 ✅
├── checklists/
│   └── requirements.md
└── tasks.md                   ← generado por /spec-kitti.tasks
```

### Source Code — archivos afectados

```text
backend/
├── alembic/versions/
│   └── 010_movimiento_cheque.py                  [CREAR]
├── src/app/
│   ├── core/
│   │   └── dates.py                              [MODIFICAR] +end_of_month
│   ├── models/
│   │   └── movimiento.py                         [MODIFICAR] +instrumento/fecha_liquidacion/fecha_liquidado, subtotal nullable, CHECKs, propiedades, helpers fecha efectiva
│   ├── schemas/
│   │   └── movimiento.py                         [MODIFICAR] +instrumento/fecha_liquidacion (create/update/response), DTOs saldo futuro
│   ├── services/
│   │   ├── saldo_service.py                      [CREAR]     saldo actual por suma (caja/moneda)
│   │   ├── saldo_futuro.py                       [CREAR]     proyección pura
│   │   ├── movimiento_service.py                 [MODIFICAR] cheques: create/update/delete/liquidar; stream solo impacta_saldo; fecha efectiva
│   │   ├── caja_service.py                       [MODIFICAR] saldos activos vía saldo_service
│   │   ├── informe_service.py                    [MODIFICAR] impacta_saldo, fecha efectiva, cheques pendientes, saldo futuro
│   │   └── pdf_informe_renderer.py               [MODIFICAR] marca cheque, secciones Cheques pendientes y Saldo a futuro
│   └── api/
│       ├── router.py                             [MODIFICAR] registrar router de cheques
│       └── routes/
│           ├── movimientos.py                    [MODIFICAR] list (impacta saldo + fecha efectiva), create/update (cheque), +liquidar, +cheques-pendientes
│           ├── cajas.py                          [MODIFICAR] /saldo vía saldo_service, +GET saldo-futuro
│           ├── cheques.py                        [CREAR]     GET /cheques (aptos/próximos)
│           └── informes.py                       [MODIFICAR] pasar cheques pendientes y saldo futuro al renderer
└── tests/
    ├── unit/
    │   ├── test_movimiento_cheque_model.py       [CREAR]
    │   ├── test_movimiento_cheque_schema.py      [CREAR]
    │   ├── test_saldo_futuro.py                  [CREAR]
    │   ├── test_dates.py                         [MODIFICAR] end_of_month
    │   ├── test_movimiento_service.py            [MODIFICAR] cheques
    │   ├── test_informe_service.py               [MODIFICAR]
    │   └── test_pdf_informe_renderer.py          [MODIFICAR]
    └── integration/
        ├── test_saldo_service.py                 [CREAR]
        ├── test_cheques_api.py                   [CREAR]
        ├── test_cheques_seccion_api.py           [CREAR]
        ├── test_saldo_futuro_api.py              [CREAR]
        ├── test_cajas_saldo_moneda.py            [MODIFICAR] paridad
        ├── test_movimientos_api.py               [MODIFICAR] paridad + cheques
        ├── test_movimiento_edit_delete.py        [MODIFICAR] cheques
        ├── test_movimiento_service.py            [MODIFICAR]
        ├── test_consulta_rbac.py                 [MODIFICAR] RBAC cheques
        └── test_informes_api.py                  [MODIFICAR]

frontend/
├── src/
│   ├── services/
│   │   └── api.ts                                [MODIFICAR] tipos y funciones de cheques / saldo futuro
│   ├── components/
│   │   ├── MovimientoForm.tsx                    [MODIFICAR] Instrumento + Fecha de liquidación; oculta "Entrada y Salida"
│   │   ├── MovimientoTable.tsx                   [MODIFICAR] subtotal null-safe; marca Cheque/Echeque
│   │   ├── ChequesPendientesBlock.tsx            [CREAR]     bloque sobre el historial (Registro editable / Consulta solo lectura)
│   │   ├── SaldoFuturoDesplegable.tsx            [CREAR]     <details> con carga diferida
│   │   └── layout/Navbar.tsx                     [MODIFICAR] +enlace "Cheques"
│   ├── pages/
│   │   ├── RegistroCajaPage.tsx                  [MODIFICAR] bloque pendientes, saldo a futuro, edición de cheque, liquidar
│   │   ├── ConsultaCajaPage.tsx                  [MODIFICAR] bloque pendientes (solo lectura), saldo a futuro
│   │   └── ChequesPage.tsx                       [CREAR]     sección Cheques
│   ├── App.tsx                                   [MODIFICAR] ruta /cheques
│   └── index.css                                 [MODIFICAR] estilos nuevos
└── tests/
    ├── MovimientoForm.test.tsx                   [MODIFICAR]
    ├── ChequesPendientesBlock.test.tsx           [CREAR]
    ├── SaldoFuturoDesplegable.test.tsx           [CREAR]
    ├── ChequesPage.test.tsx                      [CREAR]
    ├── Navbar.test.tsx                           [MODIFICAR]
    ├── AppRoutes.test.tsx                        [MODIFICAR]
    ├── RegistroCajaPage.test.tsx                 [MODIFICAR]
    └── ConsultaCajaPage.test.tsx                 [MODIFICAR]
```

**Structure Decision**: aplicación web existente (`backend/` + `frontend/`); se extienden `models`, `schemas`, `services`, `api/routes` y componentes/páginas actuales, y se agregan solo módulos nuevos de dominio (`saldo_service`, `saldo_futuro`), un router (`cheques`) y tres componentes/páginas de UI. No hay discovery (`.spec-kitti/discovery/` inexistente); la estructura se toma del código y de los planes 001–009.

---

## Plan Jerárquico (para Itti-Kit)

> Todas las WU siguen **TDD-first**: primero los tests (que fallan), luego la implementación. Cada WU termina con la **suite completa verde** (paridad con comportamiento legacy).

### Work Unit 1: Backend — Migración 010 y modelo `Movimiento`

**Propósito**: Persistir instrumento, fecha de liquidación estimada y fecha liquidado; permitir `subtotal` nulo con integridad garantizada.

**Entidades afectadas**:
- `Movimiento` (tabla `movimiento`)
- Índice `idx_movimiento_caja_moneda_fecha` (reemplazado) + 2 índices parciales nuevos

**Archivos a crear/modificar**:
- `backend/alembic/versions/010_movimiento_cheque.py` — migración (upgrade/downgrade con guarda de pendientes)
- `backend/src/app/models/movimiento.py` — columnas, `subtotal` nullable, 3 `CHECK`s, propiedades (`es_cheque`, `estado_cheque`, `impacta_saldo`, `fecha_carga`, `fecha_efectiva`), `effective_date_expr()`
- `backend/src/app/core/dates.py` — `end_of_month(d)`
- `backend/tests/unit/test_movimiento_cheque_model.py` — propiedades derivadas y constraints
- `backend/tests/unit/test_dates.py` — `end_of_month`

**Pruebas de Paridad Legacy**:
- `backend/tests/unit/test_movimiento_moneda.py`, `test_subtotal_calculation.py`, `tests/integration/test_movimiento_service.py` — siguen pasando tras la migración (filas existentes = `ninguno`).

**Subtareas internas**:
1. [TDD] Tests de propiedades derivadas y de cada `CHECK` (inserciones inválidas rechazadas)
2. [TDD] Test de `end_of_month` (28/29/30/31 días, diciembre)
3. Crear migración: columnas + backfill `'ninguno'` + `instrumento NOT NULL` + `subtotal` nullable
4. Crear los 3 `CHECK`s e índices (parcial de stream y de pendientes) con `op.execute`
5. `downgrade`: abortar con error claro si hay pendientes; si no, revertir
6. Actualizar el modelo ORM y los helpers de fecha efectiva
7. Verificar `upgrade` → `downgrade -1` → `upgrade` sobre base con datos

**Criterio de éxito**: migración reversible; modelo refleja las columnas; constraints impiden estados incoherentes; suite legacy verde.

**Estimación**: 3 h

---

### Work Unit 2: Backend — Núcleo de saldo y proyección de saldo a futuro

**Propósito**: Calcular saldo actual por suma (solo movimientos que impactan el saldo) y la proyección de saldo a futuro con lógica pura reutilizable.

**Entidades afectadas**:
- Saldo por (caja, moneda) · `SaldoFuturo` (vista calculada)

**Archivos a crear/modificar**:
- `backend/src/app/services/saldo_futuro.py` — `proyectar_saldo_futuro(saldo_actual, cheques, hoy)` (pura)
- `backend/src/app/services/saldo_service.py` — `get_saldo_actual`, `get_saldos_caja`, `get_saldos_cajas_activas`
- `backend/src/app/api/routes/cajas.py` — `/saldo` vía `saldo_service`
- `backend/src/app/services/caja_service.py` — `list_saldos_cajas_activas` vía `saldo_service`
- `backend/tests/unit/test_saldo_futuro.py`
- `backend/tests/integration/test_saldo_service.py`
- `backend/tests/integration/test_cajas_saldo_moneda.py` — paridad

**Pruebas de Paridad Legacy**:
- `backend/tests/integration/test_cajas_saldo_moneda.py` — `/saldo` y `/saldo-general` devuelven los mismos valores que antes para movimientos comunes (con y sin `fecha_override`).
- `backend/tests/unit/test_caja_service.py`.

**Subtareas internas**:
1. [TDD] Proyección: acumulado correcto (ejemplo spec: 1000 → 1500 → 1300), agrupación por fecha, orden ascendente, `vencido`, entrada suma / salida resta, saldo negativo, lista vacía, ARS y USD independientes
2. [TDD] `saldo_service`: suma = último subtotal en stream consistente; ignora pendientes; cheque liquidado cuenta; caja sin movimientos = `0.00`
3. Implementar `saldo_futuro.py` (Decimal, sin acceso a DB)
4. Implementar `saldo_service.py` (consulta agregada con filtro `subtotal IS NOT NULL`)
5. Reemplazar cálculos en `/saldo` y `list_saldos_cajas_activas`; `ultimo_movimiento_at` por fecha efectiva
6. Correr tests de paridad

**Criterio de éxito**: proyección y saldo pasan al 100%; `/saldo` y `/saldo-general` sin regresión; cheques pendientes no alteran ningún saldo.

**Dependencias**: WU-1

**Estimación**: 4 h

---

### Work Unit 3: Backend — Schemas de API (request/response/DTOs)

**Propósito**: Validar en servidor `instrumento` y `fecha_liquidacion` y exponer el estado del cheque en las respuestas.

**Entidades afectadas**:
- `CreateMovimientoRequest`, `UpdateMovimientoRequest`, `MovimientoResponse`, `SaldoFuturoResponse` (+ `SaldoFuturoMoneda`, `SaldoFuturoFila`)

**Archivos a crear/modificar**:
- `backend/src/app/schemas/movimiento.py`
- `backend/tests/unit/test_movimiento_cheque_schema.py`

**Pruebas de Paridad Legacy**:
- `backend/tests/unit/test_movimiento_moneda.py` — validaciones existentes de `CreateMovimientoRequest`.
- `backend/tests/unit/test_auth_*` no se ven afectados.

**Subtareas internas**:
1. [TDD] Create: cheque sin `fecha_liquidacion` → error; con `ninguno` y fecha → error; fecha hoy/pasada/formato inválido/no calendario → error; fecha mañana → OK; cheque + `registrar_complementario` → error; `extra=forbid`
2. [TDD] Update: `instrumento="ninguno"` → error; `cheque`/`echeque` válidos; `fecha_liquidacion` con las mismas reglas; al menos un campo
3. [TDD] Response: `estado`, `subtotal` nulo en pendientes, `fecha` efectiva, `fecha_carga`, `liquidable` según rol
4. Implementar campos y validadores (`today_ar()` importable para parchear en tests)
5. `movimiento_to_response` con campos nuevos; DTOs de saldo futuro

**Criterio de éxito**: validaciones y serialización pasan; combinaciones inválidas devuelven 422; sin regresión en requests existentes.

**Dependencias**: WU-1

**Estimación**: 3 h

---

### Work Unit 4: Backend — Servicio de movimientos (cheques y liquidación)

**Propósito**: Implementar el ciclo de vida del cheque garantizando que el stream solo contenga movimientos que impactan el saldo.

**Entidades afectadas**:
- `MovimientoService`

**Archivos a crear/modificar**:
- `backend/src/app/services/movimiento_service.py`
- `backend/tests/unit/test_movimiento_service.py`
- `backend/tests/integration/test_movimiento_service.py`

**Pruebas de Paridad Legacy**:
- `backend/tests/unit/test_movimiento_service.py` (pares ARS/USD, `fecha_override`), `test_movimiento_moneda.py`, `test_subtotal_calculation.py`, `tests/integration/test_movimiento_edit_delete.py`.

**Subtareas internas**:
1. [TDD] `create_movimiento` cheque: `subtotal=None`, no toma lock del stream, no altera subtotales existentes
2. [TDD] `liquidar_cheque`: entrada suma / salida resta; fecha liquidado = ahora; cheque al final; `409` (excepción de dominio) si ya liquidado; `NotFound` si no es cheque o no pertenece a la caja; auditoría (`updated_by/at`); rollback conserva pendiente
3. [TDD] `update_movimiento`: pendiente sin recálculo (monto/tipo/moneda/instrumento↔/fecha_liquidacion); `ninguno` + `instrumento|fecha_liquidacion` → `ValueError`; `fecha_liquidacion` en liquidado → `ValueError`; liquidado con recálculo en cascada
4. [TDD] `delete_movimiento` pendiente sin recálculo; liquidado con recálculo
5. [TDD] Stream y `recalculate_subtotals` solo sobre `impacta_saldo`, orden por fecha efectiva; `create_movimiento` con `fecha_override` ⇒ recálculo (hardening)
6. Implementar `liquidar_cheque` con orden de locks **caja → fila de cheque → stream**
7. Implementar el resto y ejecutar tests

**Criterio de éxito**: ciclo pendiente → liquidado correcto; pendientes nunca alteran subtotales; legacy verde.

**Dependencias**: WU-1, WU-3

**Estimación**: 5 h

---

### Work Unit 5: Backend — Endpoints (movimientos, cheques, saldo futuro)

**Propósito**: Exponer la funcionalidad con autorización por rol, paginación y logging.

**Entidades afectadas**:
- Routers `movimientos`, `cajas`, `cheques` (nuevo), `router.py`

**Archivos a crear/modificar**:
- `backend/src/app/api/routes/movimientos.py` — `list_movimientos` (solo impacta saldo + fecha efectiva), `create`/`update` con cheque, `POST .../liquidar`, `GET .../cheques-pendientes`
- `backend/src/app/api/routes/cajas.py` — `GET /{caja_id}/saldo-futuro`
- `backend/src/app/api/routes/cheques.py` — `GET /cheques?categoria=aptos|proximos&page=`
- `backend/src/app/api/router.py`
- `backend/tests/integration/test_cheques_api.py`, `test_cheques_seccion_api.py`, `test_saldo_futuro_api.py`
- `backend/tests/integration/test_movimientos_api.py`, `test_movimiento_edit_delete.py`, `test_consulta_rbac.py`

**Pruebas de Paridad Legacy**:
- `backend/tests/integration/test_movimientos_api.py` (listado, paginación, filtros, fecha manual), `test_consulta_rbac.py`, `test_movimiento_edit_delete.py`.

**Subtareas internas**:
1. [TDD] POST cheque → 201, `subtotal=null`, saldo sin cambios; fecha ≤ hoy → 422; cheque + complementario → 422; Escribano → 403
2. [TDD] `liquidar`: 200 + saldo actualizado + movimiento aparece en `/movimientos`; segunda llamada 409 sin duplicar; no cheque / otra caja → 404; Escribano → 403; sin token → 401
3. [TDD] `/cheques`: `aptos` (≤ hoy) y `proximos` (hoy < f ≤ fin de mes); excluye liquidados y meses posteriores; incluye varias cajas; paginación 20; orden; `categoria` inválida → 422; `liquidable` por rol
4. [TDD] `cheques-pendientes` por caja: filtros por moneda/fecha de carga, paginación, 404
5. [TDD] `saldo-futuro`: ejemplo de la spec, agrupación por fecha, vencidos, ARS/USD, sin cheques → solo saldo de hoy, ambos roles, 404
6. [TDD] `PATCH`/`DELETE` de cheques (reglas de WU-4 vía API: 400/422/204)
7. Implementar endpoints, logging (`cheque_liquidated`, `instrumento` en `movimiento_created`) y registrar el router
8. Correr toda la suite de integración

**Criterio de éxito**: endpoints cumplen contrato `openapi-delta.yaml`; RBAC verificado; sin regresión de listado/saldo.

**Dependencias**: WU-2, WU-3, WU-4

**Estimación**: 6 h

---

### Work Unit 6: Backend — Informe PDF de Caja

**Propósito**: Incluir cheques pendientes y saldo a futuro en el informe sin alterar saldos.

**Entidades afectadas**:
- `InformeService`, `render_caja_pdf`, router `informes`

**Archivos a crear/modificar**:
- `backend/src/app/services/informe_service.py`
- `backend/src/app/services/pdf_informe_renderer.py`
- `backend/src/app/api/routes/informes.py`
- `backend/tests/unit/test_informe_service.py`, `test_pdf_informe_renderer.py`, `tests/integration/test_informes_api.py`

**Pruebas de Paridad Legacy**:
- `backend/tests/unit/test_informe_service.py`, `test_informe_date_range.py`, `test_informe_filename.py`, `test_pdf_informe_renderer.py`, `tests/integration/test_informes_api.py` (informe de Plazos Fijos y de Caja sin cheques idénticos).

**Subtareas internas**:
1. [TDD] `fetch_movimientos_informe` excluye pendientes y filtra por fecha efectiva; `compute_saldo_cierre*` por fecha efectiva; saldos actuales por `saldo_service`
2. [TDD] `fetch_cheques_pendientes` (todos de la caja; tope 1000) y `fetch_saldo_futuro` (misma función pura)
3. [TDD] PDF: marca `[Cheque]/[Echeque]`; sección "Cheques pendientes" (con y sin filas); sección "Saldo a futuro" por moneda; texto extraíble; plazos fijos sin cambios
4. Implementar servicio, renderer y router
5. Verificar que un informe de un período pasado muestra pendientes/proyección **actuales** y la fecha/hora de generación

**Criterio de éxito**: informe incluye ambas secciones con valores idénticos a la API (SC-009); saldos al cierre/actual sin cambios por pendientes; legacy verde.

**Dependencias**: WU-2, WU-5

**Estimación**: 4 h

---

### Work Unit 7: Frontend — API client y formulario de Registro (Instrumento)

**Propósito**: Permitir cargar cheques/echeques desde el formulario de Registro.

**Entidades afectadas**:
- `MovimientoForm`, `api.ts`

**Archivos a crear/modificar**:
- `frontend/src/services/api.ts` — tipos `Instrumento`, `EstadoCheque`, `SaldoFuturo*`, `Movimiento` ampliado, payloads; `fetchSaldoFuturo`, `fetchChequesPendientes`, `fetchCheques`, `liquidarCheque`
- `frontend/src/components/MovimientoForm.tsx`
- `frontend/tests/MovimientoForm.test.tsx`
- `frontend/src/index.css` — estilos del campo

**Pruebas de Paridad Legacy**:
- `frontend/tests/MovimientoForm.test.tsx` (casos existentes: botones, fecha manual, complementario, cajas adicionales), `RegistroCajaPage.test.tsx`.

**Subtareas internas**:
1. [TDD] Orden de campos: **Instrumento** entre *Fecha (opcional)* y *Entrada*; valor por defecto `-`; opciones `-`, Cheque, Echeque
2. [TDD] Con Cheque/Echeque aparece **Fecha de liquidación** obligatoria (`min` = mañana); al volver a `-` desaparece y se descarta
3. [TDD] Con instrumento ≠ `-` el botón **Entrada y Salida** no está disponible
4. [TDD] El payload incluye `instrumento` y `fecha_liquidacion` solo cuando corresponde; con `-` el payload es idéntico al actual
5. [TDD] Tras éxito: instrumento vuelve a `-` y se limpia Fecha de liquidación; ante error del servidor se muestra mensaje claro
6. Implementar tipos/funciones de `api.ts` y los cambios del formulario
7. Correr Vitest y `npm run build`

**Criterio de éxito**: tests del formulario en verde; sin regresión con instrumento `-`.

**Dependencias**: contrato `openapi-delta.yaml` (puede avanzar en paralelo a WU-4/5)

**Estimación**: 3 h

---

### Work Unit 8: Frontend — Bloque de cheques pendientes, edición y Liquidar (Registro y Consulta)

**Propósito**: Mostrar los cheques pendientes sobre el historial y permitir liquidar, editar y eliminar (secretaria); solo lectura en Consulta.

**Entidades afectadas**:
- `ChequesPendientesBlock` (nuevo), `MovimientoTable`, `RegistroCajaPage`, `ConsultaCajaPage`

**Archivos a crear/modificar**:
- `frontend/src/components/ChequesPendientesBlock.tsx` — tabla paginada (fecha de carga, fecha de liquidación, instrumento, monto, moneda) + acciones
- `frontend/src/components/MovimientoTable.tsx` — `subtotal` null-safe; marca Cheque/Echeque + estado Liquidado
- `frontend/src/pages/RegistroCajaPage.tsx` — bloque arriba del historial, panel de edición con Instrumento (Cheque↔Echeque) y Fecha de liquidación, `Liquidar` con confirmación, refresco de saldo/historial/saldo a futuro
- `frontend/src/pages/ConsultaCajaPage.tsx` — bloque en modo solo lectura
- `frontend/tests/ChequesPendientesBlock.test.tsx`, `RegistroCajaPage.test.tsx`, `ConsultaCajaPage.test.tsx`
- `frontend/src/index.css`

**Pruebas de Paridad Legacy**:
- `frontend/tests/RegistroCajaPage.test.tsx`, `ConsultaCajaPage.test.tsx`, `listadoStackedFields.test.tsx` (responsive de tablas).

**Subtareas internas**:
1. [TDD] El bloque lista pendientes con ambas fechas, sin subtotal, y botón **Liquidar** solo si `liquidable`
2. [TDD] Estado vacío y error; paginación propia; filtros moneda/fecha de carga reutilizados
3. [TDD] Liquidar: confirmación, llamada al endpoint, refresco de Valor de caja + historial + bloque; error deja el cheque pendiente
4. [TDD] Edición de cheque pendiente (Cheque↔Echeque, fecha de liquidación > hoy, monto, descripción, tipo); no ofrece `-`
5. [TDD] Consulta (Escribano y Secretaria): bloque visible **sin** acciones
6. [TDD] `MovimientoTable`: subtotal `null` no rompe; cheque liquidado muestra marca y fecha liquidado
7. Implementar componentes y páginas
8. Verificar diseño responsive (tablas apiladas en móvil como el resto)

**Criterio de éxito**: flujo cargar → ver pendiente → liquidar → ver en historial funciona; Escribano sin acciones de escritura.

**Dependencias**: WU-7

**Estimación**: 6 h

---

### Work Unit 9: Frontend — Desplegable Saldo a futuro (Registro y Consulta)

**Propósito**: Mostrar la proyección del saldo dentro de *Valor de caja*.

**Entidades afectadas**:
- `SaldoFuturoDesplegable` (nuevo), `RegistroCajaPage`, `ConsultaCajaPage`

**Archivos a crear/modificar**:
- `frontend/src/components/SaldoFuturoDesplegable.tsx` — `<details>` colapsado; carga al expandir; refresco por `refreshKey`
- `frontend/src/pages/RegistroCajaPage.tsx`, `frontend/src/pages/ConsultaCajaPage.tsx` — dentro de la sección *Valor de caja*
- `frontend/tests/SaldoFuturoDesplegable.test.tsx`
- `frontend/src/index.css`

**Pruebas de Paridad Legacy**:
- `frontend/tests/RegistroCajaPage.test.tsx`, `ConsultaCajaPage.test.tsx` — banner *Valor de caja* ARS/USD intacto.

**Subtareas internas**:
1. [TDD] Colapsado por defecto; al expandir llama a `fetchSaldoFuturo(cajaId)`; muestra fila "Hoy" por moneda
2. [TDD] Filas por fecha con saldo proyectado acumulado y marca **Vencido**; ARS y USD separados
3. [TDD] Sin cheques pendientes → solo saldo de hoy + mensaje; estados cargando/error
4. [TDD] Se refresca tras alta/edición/eliminación/liquidación de cheques (cambio de `refreshKey`) y al cambiar de caja
5. [TDD] Presente en Registro y en Consulta (modo caja individual); no en vista en conjunto
6. Implementar el componente e integrarlo

**Criterio de éxito**: ejemplo de la spec (Hoy 1000 · D1 1500 · D2 1300) se renderiza correctamente; sin regresión en *Valor de caja*.

**Dependencias**: WU-7

**Estimación**: 3 h

---

### Work Unit 10: Frontend — Sección Cheques, navegación y rutas

**Propósito**: Nueva sección con cheques aptos para liquidar y próximos a liquidar del mes, de todas las cajas.

**Entidades afectadas**:
- `ChequesPage` (nueva), `Navbar`, `App`

**Archivos a crear/modificar**:
- `frontend/src/pages/ChequesPage.tsx` — dos listados con paginación independiente; **Liquidar** para secretaria
- `frontend/src/components/layout/Navbar.tsx` — enlace **Cheques** entre *Consulta plazos fijos* e *Impresión* (roles `secretaria` y `escribano`)
- `frontend/src/App.tsx` — ruta `/cheques` (protegida, ambos roles)
- `frontend/tests/ChequesPage.test.tsx`, `Navbar.test.tsx`, `AppRoutes.test.tsx`
- `frontend/src/index.css`

**Pruebas de Paridad Legacy**:
- `frontend/tests/Navbar.test.tsx`, `AppRoutes.test.tsx`, `ConsultaPlazosFijosPage.test.tsx`, `ImpresionPage.test.tsx`.

**Subtareas internas**:
1. [TDD] Navbar: orden exacto `… Consulta plazos fijos, Cheques, Impresión`; visible para ambos roles
2. [TDD] Ruta `/cheques`: redirige a login sin sesión; accesible a Escribano y Secretaria
3. [TDD] Página: "Aptos para liquidar" y "Próximos a liquidar este mes" (caja, instrumento, descripción, tipo, moneda, monto, fecha de carga, fecha de liquidación), estados vacíos, paginación independiente
4. [TDD] **Liquidar** visible solo para secretaria; tras éxito el cheque sale del listado y ambos se recargan
5. Implementar página, enlace y ruta
6. Correr Vitest y `npm run build`

**Criterio de éxito**: sección operativa para ambos roles; Escribano en modo solo lectura.

**Dependencias**: WU-7

**Estimación**: 4 h

---

### Notas para Itti-Kit

**Total Work Units**: 10  
**Tiempo total estimado**: 41 h  
**Work Units que pueden ejecutarse en paralelo**: tras WU-1, `WU-2` y `WU-3` (independientes entre sí); el frontend `WU-7 → WU-8/9/10` puede avanzar en paralelo al backend usando el contrato `openapi-delta.yaml`.

**Secuencia recomendada**:
```
WU-1 (migración + modelo)
   ├─► WU-2 (saldo + proyección) ──┐
   └─► WU-3 (schemas) ─► WU-4 (servicio cheques) ─► WU-5 (endpoints) ─► WU-6 (informe PDF)
                                      ▲
WU-2 ────────────────────────────────┘ (WU-5 y WU-6 requieren WU-2)

WU-7 (api.ts + formulario) ─┬─► WU-8 (bloque pendientes / liquidar)
                            ├─► WU-9 (saldo a futuro)
                            └─► WU-10 (sección Cheques + navbar)
```

**Gate de UI (regla `spec-kitti-figma.mdc`)**: las WU 7–10 son tareas de UI; `/spec-kitti.tasks` deberá obtener la referencia Figma (o `node-id`) del desarrollador antes de generarlas.

---

## Complexity Tracking

> Sin violaciones a la constitución. Se documentan las desviaciones/riesgos aceptados.

| Item | Por qué es necesario | Alternativa más simple descartada porque… |
|---|---|---|
| **Desviación de wireframes (Principio III)**: campo Instrumento + Fecha de liquidación, bloque *cheques pendientes*, desplegable *Saldo a futuro*, enlace *Cheques* | Funcionalidad pedida explícitamente por el usuario; no existe en los `.drawio` vigentes | No hay forma de ofrecerla sin ampliar el layout. Se valida con los usuarios en la verificación manual (quickstart). |
| `subtotal` **nullable** + 3 `CHECK`s | Un cheque pendiente no tiene subtotal; el `NULL` expresa "no impacta" y los `CHECK` impiden estados incoherentes | Placeholder `0` o columna `estado` redundante permiten inconsistencias y ocultan el estado en toda consulta. |
| Saldo actual **por suma** (no "último subtotal") | Independiente del orden y de subtotales desactualizados; necesario al introducir fecha efectiva con cheques liquidados | Mantener "último por `created_at`" colocaría cheques liquidados en posición incorrecta y daría saldos erróneos. |
| Cambio de criterio de orden/filtros a **fecha efectiva** en `/movimientos`, saldos e informes | Cheques liquidados deben ubicarse por `fecha_liquidado`; además corrige que hoy los listados/saldos ignoran `fecha_override` (feature 009) | Dejar `created_at` rompe el orden del historial con cheques liquidados. Los movimientos sin `fecha_override` ni instrumento ordenan idéntico a hoy (tests de paridad). |
| Hardening: `create_movimiento` con `fecha_override` recalcula subtotales | La columna Subtotal debe quedar consistente con el orden cronológico (brecha preexistente de 009 que la liquidación expondría) | Omitirlo dejaría subtotales almacenados inconsistentes tras insertar en fechas pasadas; el saldo por suma no se vería afectado, pero sí la columna visible. |
| Índices **parciales** vía `op.execute` | Acelerar stream y pendientes sin penalizar el resto | Índices completos indexarían filas sin utilidad (cheques pendientes en el stream o movimientos en la consulta de pendientes). |
| Lock de **caja** antes del lock de filas al liquidar | Evita deadlocks y garantiza idempotencia (409) bajo concurrencia | Solo `FOR UPDATE` sobre la fila del cheque puede interbloquear con `recalculate_subtotals` entre dos liquidaciones del mismo stream. |
