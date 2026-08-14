# Research: Cambio de Contraseña y Consulta Conjunta de Cajas

**Feature**: `005-cambio-clave-consulta-conjunto`  
**Date**: 2026-08-14

## R1 — Extensión del stack existente

**Decision**: Reutilizar monorepo `frontend/` + `backend/` (Python 3.12 + FastAPI + SQLAlchemy 2; React 18 + TypeScript + Vite; PostgreSQL 16). Sin nuevos servicios Docker ni librerías de terceros.

**Rationale**:
- Cambio de contraseña y consulta conjunta son incrementos sobre auth y consulta de 001.
- Mismos patrones JWT HS256, bcrypt, RBAC y `extra="forbid"` en Pydantic.

**Alternatives considered**:
- Panel de administración de usuarios: fuera de alcance (spec Out of Scope).
- Recuperación por email: fuera de alcance.

## R2 — Endpoints de cambio de contraseña

**Decision**: Dos operaciones POST, ambas `204` sin cuerpo ni token:

| Ruta | Auth | Body |
|------|------|------|
| `POST /api/v1/auth/change-password` | Pública | `username`, `current_password`, `new_password`, `new_password_confirm` |
| `POST /api/v1/auth/me/password` | Bearer JWT | `current_password`, `new_password`, `new_password_confirm` |

**Rationale**:
- El flujo de login no tiene sesión (FR-002/FR-009); el autenticado no debe reenviar username (FR-005, anti-IDOR).
- Confirmación en servidor evita clientes que omitan el chequeo (FR-006).
- `204` no inicia sesión automáticamente.

**Alternatives considered**:
- Un solo endpoint con username opcional: más fácil equivocar el sujeto del cambio.
- `PATCH /users/me`: no hay API de usuarios; auth es el bounded context correcto.

## R3 — Invalidación de sesión (JWT sin denylist)

**Decision**:
- Incluir claim **`iat`** (UTC) en tokens nuevos.
- Columna **`usuario.password_changed_at`** (timestamptz, nullable).
- Tras un cambio exitoso, setear `password_changed_at = now()`.
- `get_current_user` rechaza con 401 si `password_changed_at` no es null y `iat` del token es **estrictamente anterior**.
- El frontend, en el flujo autenticado, hace `logout()` local (limpia sessionStorage) y redirige a `/login`.

**Rationale**:
- JWT actual es stateless (`sub`, `rol`, `exp`); no hay denylist. Comparar `iat` vs marca de cambio cumple FR-008 sin Redis.
- Tokens emitidos **después** del cambio (nuevo login) siguen válidos.
- `password_changed_at` null = usuarios que nunca cambiaron clave; tokens viejos (sin `iat`) se tratan como inválidos **solo si** ya hubo un cambio (decode: falta `iat` → 401 cuando `password_changed_at` está set).

**Alternatives considered**:
- Denylist de `jti` en memoria/Redis: infra extra, viola costo mínimo (principio VI).
- Solo logout en el cliente: no invalida otra pestaña u otro navegador (incumple FR-008).

## R4 — Errores y enumeración de usuarios

**Decision**:
- Login público y `change-password` público: mismo mensaje genérico existente (`Credenciales inválidas`) y HTTP **401** si usuario no existe o contraseña actual no coincide.
- Política de clave (largo menor a 8, confirmación distinta, nueva igual a la actual): HTTP **422** con detalle de validación. El schema Pydantic valida formato de la nueva clave **antes** de tocar la base; eso no revela si el usuario existe. Luego se verifica usuario + clave actual (401 genérico).
- Endpoint autenticado: contraseña actual incorrecta → **401** genérico; la sesión actual permanece hasta que el cliente reciba 401 de *token* (aquí el token sigue válido porque el hash no cambió).
- Logs: `password_change_success` / `password_change_failed` sin secretos ni PII extra.

**Rationale**: Alineado a FR-010 y al login actual.

**Alternatives considered**:
- 404 si el usuario no existe: enumeración de cuentas.

## R5 — Consulta conjunta sin API batch

**Decision**: **No** hay endpoint nuevo de consulta. El frontend:

1. Conserva desplegable + **Consulta**.
2. Sección **Ver en conjunto con otras cajas** reutiliza el patrón de `CajasAdicionalesSelector` con título distinto (prop `summary`), **sin** cambiar Registro.
3. Sin adicionales: mismas llamadas que hoy (`GET saldo` + `GET movimientos?page=`).
4. Con adicionales: `Promise.all` de **`GET /api/v1/cajas/{id}/saldo`** para principal + marcadas. Si **cualquiera** rechaza, se descarta el intento (FR-021a).
5. **Valor en conjunto**: suma en el cliente de los `saldo_actual` de ese intento; se muestra **arriba** de las solapas (FR-018a). Sin endpoint de total.
6. Historial: se pide al **expandir** cada solapa (todas inician cerradas) vía `GET .../movimientos?page=1`, paginación independiente.

Orden UI: principal primero; resto `cajas` ya ordenadas por `id` (catálogo).

**Rationale**:
- Subtotales por caja siguen siendo autoritativos en backend (constitución I y V).
- El total conjunto no introduce una cifra nueva en servidor: es la suma de las mismas respuestas.
- Tabs cerradas evitan 15× historiales en el primer click.
- Fail-all es trivial con `Promise.all`.

**Alternatives considered**:
- `GET /cajas/consulta-conjunto?ids=`: menos round-trips, más superficie API para un catálogo de 15. Rechazado en v1.
- Cargar historiales de todas las cajas en Consulta: innecesario con solapas cerradas.

## R6 — Fortaleza de contraseña

**Decision**: Mínimo **8 caracteres**; distinta de la actual; confirmación igual. Hash **bcrypt** existente (`hash_password`). Sin reglas extra de alfabeto (spec Assumptions).

**Alternatives considered**:
- Complejidad tipo NIST con clases de caracteres: no pedido; se puede enmendar después.

## R7 — TDD

**Decision**: Tests **antes** de implementación (spec Testing Strategy).

Cobertura mínima:

- Unit: validadores de schema; comparación `iat` vs `password_changed_at`.
- Integration: ambos POST; 401 genérico; 422; login viejo falla; JWT anterior 401 tras cambio autenticado; escribano puede cambiar clave; consulta existente no regresa.
- Frontend: LoginPage toggle enlace; Navbar menú usuario; ConsultaCajaPage una caja vs conjunto, fail-all, orden, solapas cerradas, Valor en conjunto.
