# Implementation Plan: Configuración y Archivo de Cajas

**Branch**: `006-config-archivo-cajas` | **Date**: 2026-08-14 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/006-config-archivo-cajas/spec.md`

## Summary

Se incorpora una solapa de configuración para que solo `secretaria` pueda crear o archivar cajas, manteniendo persistencia histórica y excluyendo cajas archivadas de todos los controles operativos seleccionables. El diseño se apoya en estado lógico de caja (activa/archivada), filtros de lectura por estado activo y enforcement RBAC server-side, con enfoque TDD definido en la spec.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x + React 18 (frontend)  
**Primary Dependencies**: FastAPI, SQLAlchemy 2, Pydantic 2, Alembic, python-jose/passlib; React Router, Vite, Vitest, Testing Library  
**Storage**: PostgreSQL (tabla `caja` y trazabilidad en backend)  
**Testing**: TDD obligatorio para esta feature; pytest (unit/integration) + Vitest (frontend)  
**Target Platform**: Web app en navegador + API Linux container  
**Project Type**: Web application (`frontend/` + `backend/`)  
**Performance Goals**: Alta/archivo de caja visible en UI operativa en <= 30s; operaciones de configuración p95 <= 500ms para carga normal  
**Constraints**: RBAC estricto (solo secretaria escribe), persistencia histórica intacta, sin borrar datos al archivar, auditoría de eventos de configuración  
**Scale/Scope**: Operación de baja concurrencia (<= 10 usuarios), catálogo de cajas pequeño, 1 nueva solapa + endpoints de configuración

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I — Integridad Financiera | ✅ PASS | Archivo lógico preserva historial; no borra movimientos ni altera subtotales existentes |
| II — RBAC | ✅ PASS | Alta/archivo restringido a `secretaria`; rechazo explícito a otros roles |
| III — Fidelidad al Diseño | ✅ PASS | Se agrega nueva solapa funcional sin romper estructuras existentes de registro/consulta |
| IV — Seguridad por Diseño | ✅ PASS | Validación authz en backend, auditoría de eventos, sin exposición de secretos |
| V — Arquitectura Fullstack Desacoplada | ✅ PASS | Lógica de estado y permisos en backend; frontend consume contratos API |
| VI — Costo Mínimo AWS | ✅ PASS | Cambios sobre stack actual, sin nuevos servicios de infraestructura |

**Post-design re-check (Phase 1)**: ✅ All gates remain pass. No constitution violations introduced.

## Project Structure

### Documentation (this feature)

```text
specs/006-config-archivo-cajas/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── openapi.yaml
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── src/app/
│   ├── api/routes/
│   │   └── cajas.py                    # MODIFY: endpoints configuración + filtros activas
│   ├── services/
│   │   └── caja_service.py             # NEW/MODIFY: reglas de alta/archivo
│   ├── models/
│   │   └── caja.py                     # MODIFY: estado archivado + auditoría
│   ├── schemas/
│   │   └── caja.py                     # MODIFY: DTOs de configuración
│   └── api/deps.py                     # REUSE: guardas de rol
└── tests/
    ├── integration/
    │   └── test_cajas_config_api.py    # NEW: RBAC + archivo + listados
    └── unit/
        └── test_caja_service.py        # NEW: unicidad, idempotencia, transitions

frontend/
├── src/
│   ├── pages/
│   │   └── ConfiguracionCajasPage.tsx  # NEW: solapa de configuración
│   ├── components/
│   │   └── CajaSelector*.tsx           # MODIFY: consumo de cajas activas
│   ├── services/
│   │   └── api.ts                      # MODIFY: endpoints crear/archivar/listar
│   ├── App.tsx                         # MODIFY: nueva ruta protegida por rol
│   └── components/layout/Navbar.tsx    # MODIFY: acceso a solapa según rol
└── tests/
    ├── ConfiguracionCajasPage.test.tsx # NEW
    └── RegistroCajaPage.test.tsx       # MODIFY: cajas archivadas no visibles
```

**Structure Decision**: Se mantiene el monorepo frontend/backend existente. La feature introduce cambios verticales (modelo, servicio, API, UI y tests) sin alterar arquitectura base.

## Plan Jerárquico (para Itti-Kit)

### Work Unit 1: Modelo y reglas de ciclo de vida de caja (backend)

**Propósito**: Definir y validar el estado operable de cajas (activa/archivada) con reglas de negocio y auditoría.

**Entidades afectadas**:
- `Caja`
- `EventoConfiguracionCaja`

**Archivos a crear/modificar**:
- `backend/src/app/models/caja.py` - estado y metadatos de archivo
- `backend/src/app/services/caja_service.py` - alta, archivo, unicidad, idempotencia
- `backend/tests/unit/test_caja_service.py` - TDD de reglas core

**Pruebas de Paridad Legacy**:
- `backend/tests/integration/test_movimientos_api.py` - preserva operación existente
- `backend/tests/integration/test_consulta_rbac.py` - preserva límites de rol existentes

**Subtareas internas**:
1. [TDD] Escribir tests unitarios para transición `activa -> archivada`.
2. [TDD] Escribir tests de unicidad en alta de caja.
3. Implementar reglas de servicio para alta y archivo idempotente.
4. Persistir metadatos de auditoría de operación.

**Criterio de éxito**: Todos los casos de transición, unicidad e idempotencia pasan en unit tests.

**Estimación**: 4h

---

### Work Unit 2: Contratos API y enforcement RBAC

**Propósito**: Exponer operaciones de configuración y asegurar restricciones de acceso por rol.

**Entidades afectadas**:
- `Caja`
- `EventoConfiguracionCaja`

**Archivos a crear/modificar**:
- `backend/src/app/api/routes/cajas.py` - endpoints crear/archivar/listar
- `backend/src/app/schemas/caja.py` - request/response de configuración
- `backend/tests/integration/test_cajas_config_api.py` - RBAC + comportamiento funcional

**Pruebas de Paridad Legacy**:
- `backend/tests/integration/test_auth.py`
- `backend/tests/integration/test_consulta_rbac.py`

**Subtareas internas**:
1. [TDD] Escribir pruebas integración de permisos (`secretaria` OK, otros 403).
2. Implementar endpoint de alta de caja.
3. Implementar endpoint de archivo lógico.
4. Implementar endpoint/listado operativo solo con cajas activas.
5. Registrar evento de auditoría por acción.

**Criterio de éxito**: Contratos cumplen FR-001..FR-010 y tests de integración quedan verdes.

**Dependencias**: [WU-1]

**Estimación**: 4h

---

### Work Unit 3: Solapa de configuración y consumo operativo de cajas activas (frontend)

**Propósito**: Incorporar UI de configuración para secretaria y reflejar exclusión de cajas archivadas en todos los selectores/boxes.

**Entidades afectadas**:
- `Caja` (vista operativa)

**Archivos a crear/modificar**:
- `frontend/src/pages/ConfiguracionCajasPage.tsx` - alta/archivo desde UI
- `frontend/src/services/api.ts` - cliente de contratos de configuración
- `frontend/src/App.tsx` - ruta protegida por rol
- `frontend/src/components/layout/Navbar.tsx` - acceso condicional a solapa
- `frontend/tests/ConfiguracionCajasPage.test.tsx` - casos de interacción y permisos visuales
- `frontend/tests/RegistroCajaPage.test.tsx` - exclusión de archivadas

**Pruebas de Paridad Legacy**:
- `frontend/tests/RegistroCajaPage.test.tsx`
- `frontend/tests/ConsultaCajaPage.test.tsx`

**Subtareas internas**:
1. [TDD] Crear tests de render condicional por rol.
2. [TDD] Crear tests de alta y archivo con feedback de éxito/error.
3. Implementar solapa de configuración.
4. Ajustar componentes operativos para cargar solo cajas activas.
5. Validar no regresión en pantallas de registro/consulta.

**Criterio de éxito**: UI permite gestión solo a secretaria y cajas archivadas no aparecen en operación.

**Dependencias**: [WU-2]

**Estimación**: 5h

---

### Work Unit 4: Verificación integral y documentación operativa

**Propósito**: Consolidar validación E2E funcional y dejar guía de uso para operación.

**Archivos a crear/modificar**:
- `specs/006-config-archivo-cajas/quickstart.md` - flujo de validación manual
- `docs/backend.md` y/o `docs/frontend.md` - reflejo de nuevos endpoints/rutas (si aplica en implementación)

**Subtareas internas**:
1. Ejecutar suites backend y frontend vinculadas a la feature.
2. Ejecutar escenario manual: alta, archivo, no selección de archivadas.
3. Verificar intentos no autorizados.
4. Actualizar documentación operativa.

**Criterio de éxito**: Criterios SC-001..SC-004 validados y flujo reproducible documentado.

**Dependencias**: [WU-3]

**Estimación**: 2h

---

### Notas para Itti-Kit

**Total estimado de Work Units**: 4  
**Tiempo total estimado**: 15h  
**Work Units que pueden ejecutarse en paralelo**: WU-1 y preparación de mocks frontend; WU-2/WU-3 secuenciales por contrato

---

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Phase Artifacts Generated

| Artifact | Path | Status |
|----------|------|--------|
| Research | [research.md](./research.md) | ✅ Complete |
| Data Model | [data-model.md](./data-model.md) | ✅ Complete |
| OpenAPI | [contracts/openapi.yaml](./contracts/openapi.yaml) | ✅ Complete |
| Quickstart | [quickstart.md](./quickstart.md) | ✅ Complete |

## Testing Strategy (plan reference)

- **Enfoque**: `TDD` — per `spec.md` section `Testing Strategy`
- **Rationale**: Cambia permisos y selección operativa de cajas; se prioriza prevenir regresiones con tests primero.
- **Scope note**: `/spec-kitti.tasks` MUST emit test tasks before implementation tasks.

## Suggested Next Command

`/spec-kitti.tasks` → `/spec-kitti.tasks.shape` → `/spec-kitti.implement`
