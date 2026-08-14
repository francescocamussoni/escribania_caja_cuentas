# Backend

API REST en **FastAPI** + **SQLAlchemy 2** + **PostgreSQL**. Código en `backend/src/app/`.

## Stack

| Componente | Tecnología |
|------------|------------|
| Runtime | Python 3.12 |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.x |
| Migraciones | Alembic |
| Auth | JWT (HS256) + bcrypt |
| Config | pydantic-settings (variables de entorno) |

## Estructura de carpetas

```text
backend/
├── alembic/                 # Migraciones de esquema
├── src/app/
│   ├── main.py              # App FastAPI, CORS, routers
│   ├── entrypoint.sh        # migrate + bootstrap al arrancar contenedor
│   ├── bootstrap_production.py
│   ├── seed.py              # Solo desarrollo (bloqueado en production)
│   ├── api/
│   │   ├── router.py
│   │   ├── deps.py          # JWT, require_role()
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── cajas.py
│   │       └── movimientos.py
│   ├── catalog/cajas.py     # Seed inicial de 15 cajas (no es lista cerrada)
│   ├── core/                # config, security, logging
│   ├── db/                  # session, base
│   ├── models/              # Usuario, Caja, Movimiento, EventoConfiguracionCaja
│   ├── schemas/             # Pydantic request/response
│   └── services/            # Lógica de negocio (subtotales, auth)
└── tests/
    ├── unit/
    └── integration/
```

## Endpoints

Prefijo base: `/api/v1`. Documentación interactiva: `/docs` (Swagger).

### Autenticación

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/login` | No | Devuelve JWT + rol |
| `POST` | `/api/v1/auth/change-password` | No | Cambiar clave con usuario + contraseña actual. **204** sin cuerpo |
| `POST` | `/api/v1/auth/me/password` | JWT | Cambiar la propia clave (sin `username` en el body). **204** |

Cuerpos: `current_password`, `new_password`, `new_password_confirm` (mínimo 8; confirmación igual; extra fields → **422**). En el flujo público también `username`. En `/me/password` un `username` extra es **422** (anti-IDOR).

Respuestas de error:

| Código | Cuándo |
|--------|--------|
| **401** | Credenciales actuales inválidas o token ausente/inválido. En el POST público el `detail` es el mismo mensaje genérico que un login fallido |
| **422** | Validación (largo, confirmación, misma clave que la actual, campos extra) |

Tras un cambio exitoso se actualiza `usuario.password_changed_at` (UTC). Los JWT emitidos **antes** de ese instante dejan de autorizar (`get_current_user` → 401).

Contrato: `specs/005-cambio-clave-consulta-conjunto/contracts/openapi.yaml`.

### Cajas

Listado **operativo** (`GET /cajas`, `GET /cajas/operativas`): solo cajas `activa`.
Listado de **configuración** (`GET /cajas/config`): activas y archivadas (secretaria).

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/api/v1/cajas` | JWT | Cajas **activas** (selectores de registro, consulta, plazos, impresión) |
| `GET` | `/api/v1/cajas/operativas` | JWT | Igual que `GET /cajas` (alias explícito) |
| `GET` | `/api/v1/cajas/config` | JWT **secretaria** | Activas + archivadas para la solapa Configuración |
| `POST` | `/api/v1/cajas/config` | JWT **secretaria** | Alta de caja (`nombre` 1–120). **201**. Duplicado (case/espacios) → **400** |
| `POST` | `/api/v1/cajas/{id}/archive` | JWT **secretaria** | Archiva (idempotente). **200**. Desconocida → **404** |
| `POST` | `/api/v1/cajas/{id}/unarchive` | JWT **secretaria** | Desarchiva (vuelve `activa`, idempotente). **200**. Desconocida → **404** |
| `GET` | `/api/v1/cajas/saldo-general` | JWT **secretaria** | Suma + detalle de saldos de **todas las cajas activas** |
| `GET` | `/api/v1/cajas/{id}/saldo` | JWT | Saldo e historial de una caja (activa o archivada) |

Cuerpo de alta: `{ "nombre": "..." }` (`extra` fields → **422**). Respuesta de caja incluye `estado` (`activa` \| `archivada`). Archivar y desarchivar son operaciones de secretaria.

Escribano en `POST /cajas/config`, `POST .../archive`, `POST .../unarchive` o `GET /cajas/saldo-general` → **403**. Sin JWT → **401**.

Contrato: `specs/006-config-archivo-cajas/contracts/openapi.yaml`.

### Movimientos

| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| `GET` | `/api/v1/cajas/{id}/movimientos?page=N` | Cualquiera autenticado | Historial (20 por página, más recientes primero) |
| `POST` | `/api/v1/cajas/{id}/movimientos` | **secretaria** | Crear entrada/salida |
| `PATCH` | `/api/v1/cajas/{id}/movimientos/{mid}` | **secretaria** | Editar |
| `DELETE` | `/api/v1/cajas/{id}/movimientos/{mid}` | **secretaria** | Eliminar |

### Health

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Liveness (`{"status":"ok"}`) |

En producción, CloudFront expone `/api/health` reescrito a `/health` en el origen EC2.

## Modelo de datos

### `usuario`

- `username` (único), `password_hash`, `rol` (`secretaria` | `escribano`)
- `password_changed_at` (timestamptz, nullable): instante del último cambio de clave; `null` si nunca se cambió. Alembic `005_usuario_password_changed_at`
- Sin API de administración de usuarios; alta/reset operativo: `python -m app.create_user` (ver [usuarios-y-contraseñas.md](./usuarios-y-contraseñas.md))

### `caja`

- Seed inicial de 15 cajas (`catalog/cajas.py`); altas posteriores vía API, sin editar el catálogo
- `estado` (`activa` \| `archivada`), `archived_at`, `archived_by_user_id`, `updated_at`
- Bootstrap/seed inserta las 15 iniciales de forma idempotente si faltan por slug
- Archivo es baja lógica: historial y saldo siguen consultables por `id`

### `evento_configuracion_caja`

- Auditoría de alta/archivo/desarchivo (`caja_created`, `caja_archived`, `caja_unarchived`) con `actor_user_id`

### `movimiento`

- `descripcion`, `monto`, `tipo` (`entrada` | `salida`), `subtotal` calculado
- `created_by` / `updated_by` → auditoría
- Subtotales recalculados al editar o eliminar movimientos recientes

## Variables de entorno

| Variable | Descripción | Default local |
|----------|-------------|---------------|
| `DATABASE_URL` | Conexión PostgreSQL | `postgresql://escribania:...` |
| `JWT_SECRET` | Firma de tokens | *(cambiar en prod)* |
| `JWT_EXPIRE_HOURS` | Duración del token | `8` |
| `ADMIN_USERNAME` | Usuario admin bootstrap | `admin` |
| `ADMIN_PASSWORD` | Contraseña admin bootstrap | `admin` |
| `CORS_ORIGINS` | Orígenes permitidos (coma) | `http://localhost:5173` |
| `ENVIRONMENT` | `development` \| `production` | `development` |

Referencia completa: `.env.example`.

## Arranque del contenedor

`entrypoint.sh` ejecuta en cada inicio:

1. `alembic upgrade head` — aplica migraciones pendientes
2. `python -m app.bootstrap_production` — 15 cajas iniciales + admin si no existen
3. `uvicorn app.main:app` — servidor HTTP

En **desarrollo local**, después del primer arranque conviene `make seed` para cargar
el usuario `escribano` de prueba (`seed.py` rechaza `ENVIRONMENT=production`).

## Seguridad

- Contraseñas con **bcrypt** (`core/security.py`)
- JWT con algoritmo **HS256** explícito; payload: `sub`, `rol`, `exp`, **`iat`** (NumericDate con fracción de segundo)
- Si `password_changed_at` está definido y el token no tiene `iat` o `iat` es anterior al cambio → 401 (`UNAUTHORIZED_MESSAGE`)
- Lógica de cambio de clave en `services/auth_service.py` (flush; commit en la ruta)
- RBAC en rutas vía `require_role("secretaria")`
- Headers de seguridad (`SecurityHeadersMiddleware`)
- Logs de eventos de auth y cambio de clave **sin** contraseñas ni tokens (`current_password` / `new_password` en denylist)

## Desarrollo sin Docker

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export DATABASE_URL=postgresql://escribania:escribania@localhost:5432/escribania_cajas
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --app-dir src
```

## Tests

```bash
make test-backend
# o
docker compose exec backend pytest -v
```

Cobertura principal: auth (login, cambio de clave, corte de JWT), RBAC, movimientos, configuración de cajas (alta/archivo), bootstrap de producción.

## Contrato OpenAPI

Especificación histórica: `specs/001-registro-cajas/contracts/openapi.yaml`.  
Cambio de contraseña: `specs/005-cambio-clave-consulta-conjunto/contracts/openapi.yaml`.  
Configuración de cajas: `specs/006-config-archivo-cajas/contracts/openapi.yaml`.
