# Implementation Plan: Selección de Moneda en Registro de Cajas

**Branch**: `008-caja-monedas` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/008-caja-monedas/spec.md`

## Summary

Agregar **ARS/USD** a movimientos de caja (default ARS), subtotales y saldos **por moneda**, cartel USD de movimiento complementario persistido **en una transacción**, y filtros de listado por **rango de fechas** y moneda. Stack existente: React + TypeScript / FastAPI + PostgreSQL. Enfoque **TDD**. Sin tipo de cambio. Breaking change en DTOs de saldo y en la respuesta de alta.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x / React 18 (frontend)  
**Primary Dependencies**: FastAPI, SQLAlchemy 2, Alembic, Pydantic v2; Vite, React Router, Vitest (sin paquetes nuevos)  
**Storage**: PostgreSQL 16 — columna `movimiento.moneda` (Alembic 008)  
**Testing**: TDD — pytest (unit/integration) + Vitest + React Testing Library  
**Target Platform**: Navegador web; API Linux container  
**Project Type**: Web application (`frontend/` + `backend/`)  
**Performance Goals**: Listado filtrado p95 alineado al sistema actual (< 500ms carga normal); ≤ 10 usuarios concurrentes  
**Constraints**: RBAC server-side; paginación 20; montos 2 decimales; fechas de filtro en America/Argentina/Buenos_Aires; par USD atómico; no mezclar monedas en saldos; sin FX  
**Scale/Scope**: Registro + consulta de caja, saldo-general, ajuste mínimo de informes; plazos fijos sin cambio de moneda

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I — Integridad Financiera | ✅ PASS* | Subtotal y recálculo por `(caja, moneda)` en transacción; par USD atómico; saldo-general sin suma cruzada. *Extiende “un stream por caja” a “un stream por caja y moneda” (Complexity Tracking). |
| II — RBAC | ✅ PASS | Alta/par/edición solo `secretaria`; escribano lectura + filtros; 403 escritura |
| III — Wireframes | ✅ PASS | Formulario según `willing.drawio` (Descripción, Monto, Moneda, Entrada, Salida). `registro_de_caja.drawio` constitucional no tiene Moneda; la spec manda `willing.drawio`. |
| IV — Seguridad | ✅ PASS | `moneda` y `registrar_complementario` validados en Pydantic/servidor; `extra=forbid`; logs sin montos innecesarios más allá de auditoría existente |
| V — Fullstack Desacoplado | ✅ PASS | OpenAPI en `contracts/`; subtotales solo en backend |
| VI — Costo Mínimo AWS | ✅ PASS | Sin servicios nuevos; una columna e índices |

**Constraint constitucional “moneda única ARS”**: no PASS literal — ver Complexity Tracking. No bloquea la feature: el spec 008 es la excepción explícita para movimientos de caja.

**Post-design re-check (Phase 1)**: Gates I–VI PASS con la excepción documentada de moneda única. Contratos y data-model no introducen FX ni lógica de subtotal en el cliente.

## Project Structure

### Documentation (this feature)

```text
specs/008-caja-monedas/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── openapi.yaml
└── tasks.md              # /spec-kitti.tasks (no esta fase)
```

### Source Code (repository root)

```text
backend/
├── alembic/versions/
│   └── 008_movimiento_moneda.py          # NEW
├── src/app/
│   ├── models/movimiento.py              # MODIFY: moneda
│   ├── schemas/movimiento.py             # MODIFY: moneda, par, filtros
│   ├── schemas/caja.py                   # MODIFY: saldos duales
│   ├── services/movimiento_service.py    # MODIFY: stream + par atómico
│   ├── services/caja_service.py          # MODIFY: list_saldos dual
│   ├── services/informe_service.py       # MODIFY: no mezclar cierre
│   ├── api/routes/movimientos.py         # MODIFY: query + create response
│   └── api/routes/cajas.py               # MODIFY: saldo DTO
└── tests/
    ├── unit/                             # TDD subtotales por moneda / par
    └── integration/                      # API filtros, atomicidad, RBAC

frontend/
├── src/
│   ├── components/MovimientoForm.tsx     # MODIFY: moneda + cartel
│   ├── components/MovimientoTable.tsx    # MODIFY: etiqueta moneda
│   ├── pages/RegistroCajaPage.tsx        # MODIFY: filtros, valor caja dual, POST
│   ├── pages/ConsultaCajaPage.tsx        # MODIFY: filtros + moneda
│   ├── services/api.ts                   # MODIFY: tipos breaking
│   └── ... consulta conjunto / informes UI si consumen saldo_actual
└── tests/
```

**Structure Decision**: Extender el fullstack existente; no hay módulos nuevos de top-level.

## Plan Jerárquico (para Itti-Kit)

### Work Unit 1: Persistencia y modelo de moneda

**Propósito**: Cada movimiento tiene `moneda` ARS|USD; históricos quedan ARS.

**Entidades afectadas**:
- Movimiento (columna `moneda`)

**Archivos a crear/modificar**:
- `backend/alembic/versions/008_movimiento_moneda.py` — migración
- `backend/src/app/models/movimiento.py` — campo + CHECK
- `backend/tests/unit/` — constraints / default

**Pruebas de Paridad Legacy**:
- Tests de create ARS sin enviar moneda deben seguir equivalentes al alta actual

**Subtareas internas**:
1. Test: INSERT sin moneda usa ARS
2. Test: USD y valor inválido rechazados a nivel modelo/schema
3. Migración DEFAULT ARS + CHECK
4. Índice `(caja_id, moneda, created_at, id)`

**Criterio de éxito**: `alembic upgrade` en DB con datos 001; todas las filas `moneda=ARS`.

**Estimación**: 3 horas

---

### Work Unit 2: Subtotales por moneda y par USD atómico (TDD)

**Propósito**: Alta/edición/borrado calculan streams independientes; el par USD es todo-o-nada.

**Entidades afectadas**:
- MovimientoService

**Archivos a crear/modificar**:
- `backend/src/app/services/movimiento_service.py`
- `backend/tests/unit/test_movimiento_service.py`
- `backend/tests/integration/test_movimiento_service.py`

**Pruebas de Paridad Legacy**:
- Entrada/salida ARS y recálculo 24h actuales deben pasar igual (un solo stream ARS)

**Subtareas internas**:
1. Tests rojo: subtotal USD no altera ARS
2. Tests rojo: `registrar_complementario` inserta dos filas o cero
3. Implementar create con moneda + lock por stream
4. Recálculo por moneda; PATCH que cambia moneda recálcula ambos streams
5. Delete de un renglón del par no borra el otro

**Criterio de éxito**: 100% de tests de paridad ARS + nuevos de USD/par en verde.

**Estimación**: 6 horas

---

### Work Unit 3: Contrato HTTP de movimientos y filtros

**Propósito**: API de listado/alta/edición según OpenAPI; filtros server-side.

**Entidades afectadas**:
- MovimientoResponse, CreateMovimientoRequest, rutas

**Archivos a crear/modificar**:
- `backend/src/app/schemas/movimiento.py`
- `backend/src/app/api/routes/movimientos.py`
- `backend/tests/integration/test_movimientos_api.py`
- `backend/tests/integration/test_consulta_rbac.py`

**Pruebas de Paridad Legacy**:
- RBAC escribano 403 en POST
- Paginación 20

**Subtareas internas**:
1. DTO create `{ movimiento, complementario }`
2. Query `moneda`, `fecha_desde`, `fecha_hasta` (TZ AR)
3. 400 si complementario en ARS
4. Logs de seguridad incluyen moneda, no secretos

**Criterio de éxito**: Contrato `contracts/openapi.yaml` cumplido por tests de integración.

**Dependencias**: WU-001, WU-002

**Estimación**: 5 horas

---

### Work Unit 4: Saldos duales (caja y conjunto)

**Propósito**: Valor de caja y saldo-general nunca mezclan ARS y USD.

**Entidades afectadas**:
- CajaSaldoResponse, CajaSaldoGeneralResponse, CajaService

**Archivos a crear/modificar**:
- `backend/src/app/schemas/caja.py`
- `backend/src/app/api/routes/cajas.py`
- `backend/src/app/services/caja_service.py`
- `backend/tests/integration/test_cajas_config_api.py` (saldo-general)
- Frontend de consulta conjunto que lea `subtotal_general`

**Pruebas de Paridad Legacy**:
- Conjunto sigue restringido a secretaria; cajas archivadas excluidas

**Subtareas internas**:
1. Tests: saldos independientes del filtro de listado
2. Reemplazar `saldo_actual` / `subtotal_general`
3. Actualizar UI conjunto

**Criterio de éxito**: SC-006 en API y pantalla conjunto.

**Dependencias**: WU-001, WU-002

**Estimación**: 4 horas

---

### Work Unit 5: UI registro — moneda y cartel USD

**Propósito**: Secretaria elige moneda; USD pide confirmación de par; ARS sin cartel.

**Entidades afectadas**:
- MovimientoForm, RegistroCajaPage

**Archivos a crear/modificar**:
- `frontend/src/components/MovimientoForm.tsx`
- `frontend/src/pages/RegistroCajaPage.tsx`
- `frontend/src/services/api.ts`
- `frontend/tests/RegistroCajaPage.test.tsx`

**Pruebas de Paridad Legacy**:
- Alta ARS Entrada/Salida sin diálogo

**Subtareas internas**:
1. Tests: default ARS; reset al cambiar caja
2. Layout willing.drawio
3. `window.confirm` o diálogo accesible con textos exactos de spec
4. Validar monto/descripcion antes del cartel
5. POST `registrar_complementario`; cajas adicionales reutilizan el mismo payload por caja
6. Valor de caja muestra ARS y USD

**Criterio de éxito**: US1 y US2 verificables en tests + flujo manual quickstart.

**Dependencias**: WU-003, WU-004

**Estimación**: 5 horas

---

### Work Unit 6: UI listado, filtros y consulta

**Propósito**: Monto con moneda; filtros fecha+moneda en registro y consulta; escribano solo lectura.

**Entidades afectadas**:
- MovimientoTable, RegistroCajaPage, ConsultaCajaPage

**Archivos a crear/modificar**:
- `frontend/src/components/MovimientoTable.tsx`
- `frontend/src/pages/RegistroCajaPage.tsx`
- `frontend/src/pages/ConsultaCajaPage.tsx`
- `frontend/tests/ConsultaCajaPage.test.tsx`
- `frontend/tests/listadoStackedFields.test.tsx`

**Pruebas de Paridad Legacy**:
- Paginación y stacked mobile (007) conservan campos, ahora con moneda

**Subtareas internas**:
1. Mostrar moneda junto al monto (verde/rojo intactos)
2. Controles desde/hasta + moneda (todas/ARS/USD)
3. Query params al GET; paginación sobre filtrado
4. Filtros no cambian valor de caja
5. Escribano: mismos filtros, sin form de alta

**Criterio de éxito**: US3 y SC-005/SC-007.

**Dependencias**: WU-003, WU-004

**Estimación**: 5 horas

---

### Work Unit 7: Informes — no mezclar moneda

**Propósito**: PDF/cierre no usa un único subtotal cruzado; montos muestran moneda.

**Entidades afectadas**:
- InformeService / plantilla PDF

**Archivos a crear/modificar**:
- `backend/src/app/services/informe_service.py`
- tests de informe existentes
- frontend de impresión si muestra saldo único

**Pruebas de Paridad Legacy**:
- Plazos fijos del informe siguen ARS

**Subtareas internas**:
1. Tests: cierre ARS vs USD
2. Etiqueta de moneda en líneas de movimiento
3. Sin rediseño de layout más allá de lo necesario

**Criterio de éxito**: Un informe con ambas monedas no suma USD+ARS.

**Dependencias**: WU-001, WU-002

**Estimación**: 3 horas

---

### Notas para Itti-Kit

**Total estimado de Work Units**: 7  
**Tiempo total estimado**: 31 horas  
**Work Units que pueden ejecutarse en paralelo**: WU-004 y WU-003 tras WU-002; WU-005 y WU-006 tras WU-003; WU-007 paralelo a UI tras WU-002

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Constraint constitucional “moneda única (ARS)” | Spec 008 exige ARS y USD en movimientos de caja | Seguir solo ARS anula la feature |
| Principio I original “subtotal por caja” (un stream) | Dos streams por caja (ARS y USD) | Un único acumulado mezclaría monedas (SC-006) |
| Breaking DTOs de saldo y POST create | Evitar `saldo_actual` ambiguo y dos POST no atómicos | Compatibilidad hacia atrás dejaría totales incorrectos o pares a medias |

## Phase 0 / Phase 1 outputs

- [research.md](./research.md) — decisiones R1–R9  
- [data-model.md](./data-model.md) — columna, algoritmos, proyecciones  
- [contracts/openapi.yaml](./contracts/openapi.yaml) — REST delta  
- [quickstart.md](./quickstart.md) — migrate, TDD, verificación manual  
