# Implementation Plan: Registro de Cajas para Escribanía

**Branch**: `001-registro-cajas` | **Date**: 2026-08-03 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/001-registro-cajas/spec.md`

## Summary

Plataforma web fullstack para que la **secretaria** registre ingresos/egresos en 15
cajas con subtotales acumulados, y los **escribanos** consulten saldo e historial
en solo lectura. Stack: **React + TypeScript** (frontend), **FastAPI + PostgreSQL**
(backend), autenticación JWT 8h, TDD obligatorio, despliegue local con Docker
Compose extrapolable a **AWS RDS + S3/CloudFront + ECS**.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x / React 18 (frontend)  
**Primary Dependencies**: FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, python-jose, passlib[bcrypt]; Vite, React Router, fetch/axios  
**Storage**: PostgreSQL 16 (local Docker; producción AWS RDS `db.t4g.micro`)  
**Testing**: pytest + httpx (backend TDD/integration); Vitest + React Testing Library (frontend)  
**Target Platform**: Navegador web moderno; API Linux container  
**Project Type**: Web application (`frontend/` + `backend/`)  
**Performance Goals**: Respuesta API < 500ms p95 para consultas paginadas; ≤ 10 usuarios concurrentes  
**Constraints**: TLS en producción; sin secretos en código; paginación fija 20; sesión 8h; ARS 2 decimales  
**Scale/Scope**: 15 cajas, 2 roles, 3 pantallas principales + login

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I — Integridad Financiera | ✅ PASS | Subtotal calculado en backend en transacción DB; algoritmo en `data-model.md` |
| II — RBAC | ✅ PASS | JWT + middleware rol; POST movimientos solo `secretaria`; 403 para escribano |
| III — Wireframes | ✅ PASS | Rutas `/registro` y `/consulta` mapean drawios; colores verde/rojo en UI |
| IV — Seguridad | ✅ PASS | bcrypt, JWT 8h, validación server-side, logs sin PII, `.env` gitignored |
| V — Fullstack Desacoplado | ✅ PASS | REST OpenAPI en `contracts/`; lógica solo en backend |
| VI — Costo Mínimo AWS | ✅ PASS | RDS micro, S3+CloudFront, ECS Fargate mínimo documentado en `quickstart.md` |

**Post-design re-check (Phase 1)**: ✅ All gates pass. No Complexity Tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/001-registro-cajas/
├── plan.md              # This file
├── research.md          # Phase 0 — technology decisions
├── data-model.md        # Phase 1 — PostgreSQL schema
├── quickstart.md        # Phase 1 — local dev & AWS reference
├── contracts/
│   └── openapi.yaml     # Phase 1 — REST API contract
└── tasks.md             # Phase 2 (/spec-kitti.tasks)
```

### Source Code (repository root)

```text
backend/
├── alembic/
│   └── versions/
├── src/app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── cajas.py
│   │   │   └── movimientos.py
│   │   └── deps.py          # JWT + RBAC dependencies
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── models/
│   │   ├── caja.py
│   │   ├── movimiento.py
│   │   └── usuario.py
│   ├── schemas/               # Pydantic DTOs
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── movimiento_service.py   # subtotal logic
│   │   └── caja_service.py
│   ├── db/
│   │   ├── session.py
│   │   └── base.py
│   ├── seed.py
│   └── main.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── alembic.ini
├── pyproject.toml
└── Dockerfile

frontend/
├── src/
│   ├── components/
│   │   ├── CajaSelector.tsx
│   │   ├── MovimientoTable.tsx
│   │   ├── MovimientoForm.tsx
│   │   └── Pagination.tsx
│   ├── pages/
│   │   ├── LoginPage.tsx
│   │   ├── RegistroCajaPage.tsx
│   │   └── ConsultaCajaPage.tsx
│   ├── services/
│   │   └── api.ts
│   ├── hooks/
│   │   └── useAuth.ts
│   ├── App.tsx
│   └── main.tsx
├── tests/
├── package.json
├── vite.config.ts
└── Dockerfile

docker-compose.yml
.env.example
Makefile
```

**Structure Decision**: Opción web (`frontend/` + `backend/`) según constitución V.
PostgreSQL como servicio en `docker-compose.yml`. **`Makefile`** en raíz como interfaz
única para levantar el fullstack local (`make up`).

## Plan Jerárquico (para Itti-Kit)

### Work Unit 1: Infraestructura y Proyecto Base

**Propósito**: Bootstrap reproducible del monorepo con Docker, PostgreSQL y esqueleto
FastAPI + React.

**Entidades afectadas**: N/A (infraestructura)

**Archivos a crear/modificar**:
- `docker-compose.yml` — postgres, backend, frontend
- `backend/pyproject.toml`, `backend/src/app/main.py` — app FastAPI mínima
- `frontend/package.json`, `frontend/src/main.tsx` — app React mínima
- `.env.example` — variables documentadas
- `backend/tests/conftest.py` — fixtures pytest

**Pruebas de Paridad Legacy**: N/A (greenfield)

**Subtareas internas**:
1. Crear `docker-compose.yml` con PostgreSQL 16 y healthcheck
2. Scaffold FastAPI con `/health` y CORS para frontend
3. Scaffold React + Vite + TypeScript con router básico
4. Configurar pytest y Vitest con un test smoke cada uno (TDD baseline)
5. Documentar en `.env.example`

**Criterio de éxito**: `docker compose up` levanta 3 servicios; `/health` retorna 200;
`npm test` y `pytest` pasan smoke tests.

**Estimación**: 4 horas

---

### Work Unit 2: Autenticación y Usuarios (US1 — P1)

**Propósito**: Login usuario/contraseña, JWT 8h, seed admin/admin, protección de rutas.

**Entidades afectadas**: `usuario`

**Archivos a crear/modificar**:
- `backend/src/app/models/usuario.py`
- `backend/src/app/core/security.py` — bcrypt + JWT
- `backend/src/app/api/routes/auth.py`
- `backend/src/app/api/deps.py` — `get_current_user`, `require_role`
- `backend/alembic/versions/001_usuario.py`
- `backend/src/app/seed.py`
- `backend/tests/integration/test_auth.py`
- `frontend/src/pages/LoginPage.tsx`
- `frontend/src/hooks/useAuth.ts`
- `frontend/src/services/api.ts`

**Pruebas de Paridad Legacy**:
- `backend/tests/integration/test_auth.py` — login OK/KO, token expirado, rutas protegidas

**Subtareas internas**:
1. [TDD] Tests: login válido, credenciales inválidas (mensaje genérico), 401 sin token
2. Modelo `usuario` + migración Alembic
3. Endpoint `POST /api/v1/auth/login`
4. Seed `admin`/`admin` rol secretaria
5. Middleware JWT 8h en deps
6. LoginPage + guard de rutas en frontend

**Criterio de éxito**: Login con admin/admin redirige a app; visitante sin token va a
/login; token > 8h rechazado.

**Dependencias**: WU-001

**Estimación**: 6 horas

---

### Work Unit 3: Catálogo de Cajas y Modelo de Movimientos (US2 base)

**Propósito**: Persistir 15 cajas, modelo movimiento, servicio de subtotales.

**Entidades afectadas**: `caja`, `movimiento`

**Archivos a crear/modificar**:
- `backend/src/app/models/caja.py`, `movimiento.py`
- `backend/alembic/versions/002_caja_movimiento.py`
- `backend/src/app/seed.py` — 15 cajas
- `backend/src/app/services/movimiento_service.py`
- `backend/tests/unit/test_subtotal_calculation.py`
- `backend/tests/integration/test_movimiento_service.py`

**Pruebas de Paridad Legacy**:
- `test_subtotal_calculation.py` — entrada, salida, negativo, primer movimiento
- `test_movimiento_service.py` — transacción concurrente básica

**Subtareas internas**:
1. [TDD] Tests unitarios algoritmo subtotal (incl. saldo negativo)
2. Migraciones caja + movimiento con índices
3. Seed 15 cajas
4. `MovimientoService.create()` con `SELECT FOR UPDATE`
5. Tests integración con PostgreSQL de test

**Criterio de éxito**: 100% tests subtotal pasan; 15 cajas en DB tras seed.

**Dependencias**: WU-002

**Estimación**: 8 horas

---

### Work Unit 4: API Registro de Caja (US2 — P2)

**Propósito**: Endpoints crear/listar movimientos paginados; solo secretaria escribe.

**Entidades afectadas**: `movimiento`, `caja`

**Archivos a crear/modificar**:
- `backend/src/app/api/routes/cajas.py`
- `backend/src/app/api/routes/movimientos.py`
- `backend/src/app/schemas/` — DTOs alineados a OpenAPI
- `backend/tests/integration/test_movimientos_api.py`
- `specs/001-registro-cajas/contracts/openapi.yaml` — validar paridad

**Pruebas de Paridad Legacy**:
- `test_movimientos_api.py` — POST secretaria OK, POST escribano 403, paginación 20

**Subtareas internas**:
1. [TDD] Contract tests según `openapi.yaml`
2. `GET /cajas`, `GET /cajas/{id}/movimientos`, `POST /cajas/{id}/movimientos`
3. Validación descripción/monto/tipo
4. Paginación offset page=1 más recientes primero
5. `GET /cajas/{id}/saldo`

**Criterio de éxito**: API cumple contrato OpenAPI; RBAC 403 verificado; SC-002 y SC-005.

**Dependencias**: WU-003

**Estimación**: 8 horas

---

### Work Unit 5: UI Registro de Caja (US2 — P2 frontend)

**Propósito**: Pantalla registro según `registro_de_caja.drawio`.

**Entidades afectadas**: N/A (UI)

**Archivos a crear/modificar**:
- `frontend/src/pages/RegistroCajaPage.tsx`
- `frontend/src/components/CajaSelector.tsx`
- `frontend/src/components/MovimientoForm.tsx`
- `frontend/src/components/MovimientoTable.tsx`
- `frontend/src/components/Pagination.tsx`
- `frontend/tests/RegistroCajaPage.test.tsx`

**Pruebas de Paridad Legacy**:
- Tests componente: selector caja, botones Entrada/Salida, colores verde/rojo

**Subtareas internas**:
1. [TDD] Tests UI registro con mocks API
2. Layout según wireframe (selector arriba, tabla, paginador abajo)
3. Integración API crear + listar movimientos
4. Ocultar formulario para rol escribano
5. Formato ARS y fechas locale AR

**Criterio de éxito**: Secretaria registra movimiento y ve tabla actualizada; layout
alineado a drawio; SC-001.

**Dependencias**: WU-004

**Estimación**: 8 horas

---

### Work Unit 6: UI y API Consulta de Caja (US3 — P3)

**Propósito**: Pantalla consulta solo lectura según `consulta_de_caja.drawio`.

**Entidades afectadas**: N/A (reutiliza endpoints GET)

**Archivos a crear/modificar**:
- `frontend/src/pages/ConsultaCajaPage.tsx`
- `frontend/tests/ConsultaCajaPage.test.tsx`
- `backend/tests/integration/test_consulta_rbac.py`

**Pruebas de Paridad Legacy**:
- Escribano consulta cualquier caja; no ve controles de escritura

**Subtareas internas**:
1. [TDD] Tests RBAC consulta (escribano + secretaria)
2. Pantalla Consulta: selector + botón Consulta + banner VALOR DE CAJA
3. Tabla historial idéntica a registro (sin formulario)
4. Navegación por rol post-login

**Criterio de éxito**: Escribano consulta 15 cajas; SC-003, SC-004, SC-006.

**Dependencias**: WU-004

**Estimación**: 6 horas

---

### Work Unit 7: Polish, Seguridad y Quickstart

**Propósito**: Hardening, logging estructurado, validación quickstart end-to-end.

**Entidades afectadas**: N/A

**Archivos a crear/modificar**:
- `backend/src/app/core/logging.py`
- `quickstart.md` — validar comandos
- Headers seguridad en FastAPI
- README raíz (opcional, si no existe)

**Subtareas internas**:
1. Logging auth failures y operaciones escritura (sin PII)
2. Security headers (CORS allowlist, nosniff)
3. Ejecutar walkthrough completo `quickstart.md`
4. Revisión Constitution Check final

**Criterio de éxito**: Quickstart reproducible de punta a punta; sin secretos en repo.

**Dependencias**: WU-005, WU-006

**Estimación**: 4 horas

---

### Work Unit 8: Edición / Eliminación 24h (Amend — US2 extensión)

**Propósito**: Secretaria edita o elimina movimientos < 24h con recálculo de subtotales.

**Entidades afectadas**: `movimiento` (`updated_at`, `updated_by`)

**Archivos a crear/modificar**:
- `backend/src/app/services/movimiento_service.py` — `update()`, `delete()`, `recalculate_subtotals()`
- `backend/src/app/api/routes/movimientos.py` — PATCH, DELETE
- `backend/tests/integration/test_movimiento_edit_delete.py`
- `frontend/src/components/MovimientoTable.tsx` — acciones editar/eliminar si `editable`
- `specs/001-registro-cajas/contracts/openapi.yaml` — v1.1 endpoints

**Subtareas internas**:
1. [TDD] Tests ventana 24h, recálculo cascada, 403 escribano
2. PATCH y DELETE endpoints
3. UI editar/eliminar en tabla de registro

**Criterio de éxito**: SC-007, SC-008; movimientos > 24h inmutables.

**Dependencias**: WU-004

**Estimación**: 6 horas

---

### Notas para Itti-Kit

**Total estimado de Work Units**: 8  
**Tiempo total estimado**: 50 horas  
**Work Units paralelizables**: WU-005 y WU-006 (tras WU-004, si hay 2 devs)

## Complexity Tracking

> No violations — table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Open Items (post-plan)

- Ninguno bloqueante. Amend 2026-08-03 integrado (edición/eliminación 24h, PostgreSQL, Makefile/docker-compose).

## Artifacts Generated (Phase 0 + Phase 1)

| Artifact | Path |
|----------|------|
| Research | `specs/001-registro-cajas/research.md` |
| Data model | `specs/001-registro-cajas/data-model.md` |
| API contract | `specs/001-registro-cajas/contracts/openapi.yaml` |
| Quickstart | `specs/001-registro-cajas/quickstart.md` |
