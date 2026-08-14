# Implementation Plan: Cambio de Contraseña y Consulta Conjunta de Cajas

**Branch**: `005-cambio-clave-consulta-conjunto` | **Date**: 2026-08-14 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/005-cambio-clave-consulta-conjunto/spec.md`

## Summary

Autoservicio de **cambio de contraseña** (enlace en login que sustituye el formulario;
menú al tocar el nombre arriba a la derecha) y **consulta conjunta de cajas** (desplegable
igual que hoy + sección «Ver en conjunto con otras cajas»). Backend: dos POST de auth,
hash bcrypt, claim JWT `iat` + `usuario.password_changed_at` para invalidar sesiones.
Consulta conjunta **reutiliza** saldo/movimientos existentes; el cliente hace fail-all
en saldos y carga historial al expandir solapas (todas cerradas; principal primero,
adicionales en orden de catálogo). En conjunto se muestra **Valor en conjunto** =
suma de los `saldo_actual` ya obtenidos (sin endpoint nuevo). Enfoque **TDD**.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x / React 18 (frontend)  
**Primary Dependencies**: FastAPI, SQLAlchemy 2, Pydantic v2, python-jose, bcrypt (existentes); React Router, Vite (existentes). Sin dependencias nuevas.  
**Storage**: PostgreSQL 16 — columna `usuario.password_changed_at` (Alembic 005)  
**Testing**: pytest + httpx (backend TDD/integration); Vitest + Testing Library (frontend)  
**Target Platform**: Navegador web; API Linux container (igual que 001–004)  
**Project Type**: Web application (`frontend/` + `backend/`)  
**Performance Goals**: Cambio de clave en menos de 2 min (SC-001/002); consulta 1 caja en menos de 10 s (SC-005); conjunto hasta 15 saldos en paralelo  
**Constraints**: RBAC server-side; mensaje 401 genérico en flujo público; JWT HS256 con `iat`; no recuperación de clave; no batch API de consulta  
**Scale/Scope**: ≤ 10 usuarios concurrentes; 15 cajas; 2 pantallas tocadas (login, consulta) + Navbar

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I — Integridad Financiera | ✅ PASS | Consulta conjunta no recalcula subtotales de movimientos; lee saldo/movimientos del backend. El Valor en conjunto es suma de esos `saldo_actual` (presentación) |
| II — RBAC | ✅ PASS | Escribano y secretaria cambian solo su clave; consulta conjunta solo lectura; escritura de movimientos no se abre |
| III — Fidelidad al Diseño | ✅ PASS (con nota) | Consulta conserva desplegable (`consulta_de_caja.drawio`); sección conjunta es adición de spec sin drawio nuevo |
| IV — Seguridad | ✅ PASS | bcrypt; `extra="forbid"`; 401 genérico; logs sin secretos; invalidación por `iat` vs `password_changed_at`; anti-IDOR (me/password) |
| V — Fullstack Desacoplado | ✅ PASS | OpenAPI en `contracts/`; lógica de hash y corte de sesión en backend |
| VI — Costo Mínimo AWS | ✅ PASS | Sin Redis/denylist; una columna; mismos EC2/RDS |

**Post-design re-check (Phase 1)**: ✅ All gates pass. No Complexity Tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/005-cambio-clave-consulta-conjunto/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── openapi.yaml
└── tasks.md             # Phase 2 (/spec-kitti.tasks)
```

### Source Code (cambios esperados)

```text
backend/
├── alembic/versions/
│   └── 005_usuario_password_changed_at.py   # NEW
├── src/app/
│   ├── models/usuario.py                    # MODIFY — password_changed_at
│   ├── schemas/auth.py                      # MODIFY — change-password DTOs
│   ├── services/auth_service.py             # NEW — change password + cutover
│   ├── core/security.py                     # MODIFY — iat en JWT
│   ├── api/deps.py                          # MODIFY — rechazar iat viejo
│   ├── api/routes/auth.py                   # MODIFY — dos POST
│   └── core/logging.py                      # VERIFY — denylist de campos secretos
└── tests/
    ├── unit/test_auth_password.py           # NEW
    └── integration/test_auth_change_password.py  # NEW

frontend/
├── src/
│   ├── pages/LoginPage.tsx                  # MODIFY — enlace + formulario cambio
│   ├── pages/ConsultaCajaPage.tsx           # MODIFY — conjunto + solapas
│   ├── components/CajasAdicionalesSelector.tsx  # MODIFY — prop summary (registro intacto)
│   ├── components/layout/Navbar.tsx         # MODIFY — menú usuario
│   ├── components/CajaConsultaSolapa.tsx    # NEW — solapa cerrada + historial lazy
│   ├── hooks/useAuth.tsx                    # MODIFY — changePassword helpers + logout
│   └── services/api.ts                      # MODIFY — POST change-password
└── tests/
    ├── LoginPage.test.tsx                   # MODIFY/NEW
    ├── Navbar.test.tsx                      # NEW o MODIFY
    └── ConsultaCajaPage.test.tsx            # MODIFY
```

**Structure Decision**: Extensión del monorepo existente. Una migración Alembic. Sin paquetes nuevos.

## Plan Jerárquico (para Itti-Kit)

### Work Unit 1: Cambio de contraseña (backend)

**Propósito**: Persistir nueva clave, cortar JWT previos y exponer los dos POST de auth.

**Entidades afectadas**:
- `usuario` (password_hash, password_changed_at)

**Archivos a crear/modificar**:
- `backend/alembic/versions/005_usuario_password_changed_at.py`
- `backend/src/app/models/usuario.py`
- `backend/src/app/schemas/auth.py`
- `backend/src/app/services/auth_service.py`
- `backend/src/app/core/security.py`
- `backend/src/app/api/deps.py`
- `backend/src/app/api/routes/auth.py`
- `backend/tests/unit/test_auth_password.py`
- `backend/tests/integration/test_auth_change_password.py`

**Pruebas de Paridad Legacy**:
- `tests/integration/test_auth.py` — login existente sigue 200/401; tokens nuevos incluyen `iat` y siguen autorizando

**Subtareas internas**:
1. [TDD] Tests schema: confirm mismatch, min 8, extra forbid
2. [TDD] Tests servicio: hash nuevo, `password_changed_at`, rechazo igual a actual
3. [TDD] Integration público 204 / 401 genérico / login viejo falla
4. [TDD] Integration autenticado 204 + GET cajas con token viejo → 401
5. Migración Alembic + modelo
6. `create_access_token` agrega `iat`; `get_current_user` compara con `password_changed_at`
7. Rutas POST y logs de seguridad

**Criterio de éxito**: Quickstart §2; SC-003/SC-004 a nivel API.

**Estimación**: 4h

---

### Work Unit 2: Cambio de contraseña (frontend)

**Propósito**: Enlace en login y menú al tocar el nombre; logout local tras cambio autenticado.

**Entidades afectadas**: N/A (sesión en sessionStorage)

**Archivos a crear/modificar**:
- `frontend/src/pages/LoginPage.tsx`
- `frontend/src/components/layout/Navbar.tsx`
- `frontend/src/hooks/useAuth.tsx`
- `frontend/src/services/api.ts`
- `frontend/tests/LoginPage.test.tsx`
- `frontend/tests/Navbar.test.tsx` (si no existe, crear)

**Pruebas de Paridad Legacy**:
- Login exitoso existente no se rompe (tests actuales de LoginPage)

**Subtareas internas**:
1. [TDD] LoginPage: enlace reemplaza formulario; cancelar vuelve a ingresar
2. [TDD] Éxito 204 muestra mensaje y formulario de login
3. [TDD] Navbar: click en username abre sección con cambiar contraseña
4. Cliente API dos POST; 401/422 mensajes
5. Tras `me/password` 204: `logout()` + navigate `/login`

**Criterio de éxito**: Flujos US1 y US2 del spec en UI; SC-001/SC-002.

**Dependencias**: [WU-1]

**Estimación**: 3h

---

### Work Unit 3: Consulta conjunta (frontend)

**Propósito**: Sección «Ver en conjunto con otras cajas», fail-all de saldos, solapas cerradas con historial lazy, **Valor en conjunto** (suma de saldos).

**Entidades afectadas**:
- `caja`, `movimiento` (solo lectura vía API existente)

**Archivos a crear/modificar**:
- `frontend/src/pages/ConsultaCajaPage.tsx`
- `frontend/src/components/CajasAdicionalesSelector.tsx` — prop `summary`
- `frontend/src/components/CajaConsultaSolapa.tsx`
- `frontend/tests/ConsultaCajaPage.test.tsx`

**Pruebas de Paridad Legacy**:
- Consulta de **una** caja (sin marcas) idéntica a tests actuales (valor + tabla + paginación)

**Subtareas internas**:
1. [TDD] Sin adicionales: misma UI/llamadas que hoy
2. [TDD] Con adicionales: N saldos; si un fetch falla, ningún resultado
3. [TDD] Orden: principal, luego catálogo; todas las solapas `closed`
4. [TDD] Expandir carga movimientos de esa caja; paginar independiente
5. Al cambiar desplegable, quitar esa caja de adicionales (FR-022)
6. Prop `summary` default «Registrar también en otras cajas» para no romper Registro
7. [Amend] Panel **Valor en conjunto** = suma de `saldo_actual` encima de las solapas (FR-018a)

**Criterio de éxito**: US3/US4; SC-005/SC-006/SC-007 (escribano solo lectura ya cubierto por API).

**Dependencias**: ninguna respecto a WU-1 (API de cajas existente)

**Estimación**: 4h

---

### Work Unit 4: Documentación y verificación

**Propósito**: Docs de usuarios/auth/frontend y checklist quickstart.

**Archivos a crear/modificar**:
- `docs/usuarios-y-contraseñas.md` — autoservicio además del script EC2
- `docs/backend.md` — endpoints y `iat` / `password_changed_at`
- `docs/frontend.md` — login enlace, Navbar, consulta conjunta

**Subtareas internas**:
1. Actualizar docs (sin secretos)
2. `make test-backend` y `make test-frontend`
3. Recorrido manual quickstart §3

**Criterio de éxito**: Docs alineados; suites verdes.

**Dependencias**: [WU-2], [WU-3]

**Estimación**: 1.5h

---

### Notas para Itti-Kit

**Total estimado de Work Units**: 4  
**Tiempo total estimado**: 12.5h  
**Work Units que pueden ejecutarse en paralelo**: WU-1 y WU-3; WU-2 tras WU-1; WU-4 al final

---

## Complexity Tracking

> No violations requiring justification.

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

- **Enfoque**: `TDD` — per `spec.md` § Testing Strategy
- **Rationale**: Superficie de seguridad (clave) e integridad de consulta por caja
- **Scope note**: `/spec-kitti.tasks` MUST emit test tasks before implementation tasks

## Suggested Next Command

`/spec-kitti.implement T031` (tests FR-018a) → T032 (UI) → T033 (docs)
