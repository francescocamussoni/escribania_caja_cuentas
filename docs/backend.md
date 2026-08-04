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
│   ├── catalog/cajas.py     # 15 cajas predefinidas
│   ├── core/                # config, security, logging
│   ├── db/                  # session, base
│   ├── models/              # Usuario, Caja, Movimiento
│   ├── schemas/             # Pydantic request/response
│   └── services/            # Lógica de negocio (subtotales, ventana 24h)
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

### Cajas

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/api/v1/cajas` | JWT | Lista las 15 cajas |
| `GET` | `/api/v1/cajas/{id}/saldo` | JWT | Saldo actual y último movimiento |

### Movimientos

| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| `GET` | `/api/v1/cajas/{id}/movimientos?page=N` | Cualquiera autenticado | Historial (20 por página, más recientes primero) |
| `POST` | `/api/v1/cajas/{id}/movimientos` | **secretaria** | Crear entrada/salida |
| `PATCH` | `/api/v1/cajas/{id}/movimientos/{mid}` | **secretaria** | Editar (ventana 24 h) |
| `DELETE` | `/api/v1/cajas/{id}/movimientos/{mid}` | **secretaria** | Eliminar (ventana 24 h) |

### Health

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Liveness (`{"status":"ok"}`) |

En producción, CloudFront expone `/api/health` reescrito a `/health` en el origen EC2.

## Modelo de datos

### `usuario`

- `username` (único), `password_hash`, `rol` (`secretaria` | `escribano`)
- Sin API de administración de usuarios; ver [usuarios-y-contraseñas.md](./usuarios-y-contraseñas.md)

### `caja`

- Catálogo fijo de 15 cajas (`catalog/cajas.py`)
- Creadas por bootstrap/seed de forma idempotente

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
2. `python -m app.bootstrap_production` — 15 cajas + admin si no existen
3. `uvicorn app.main:app` — servidor HTTP

En **desarrollo local**, después del primer arranque conviene `make seed` para cargar
el usuario `escribano` de prueba (`seed.py` rechaza `ENVIRONMENT=production`).

## Seguridad

- Contraseñas con **bcrypt** (`core/security.py`)
- JWT con algoritmo **HS256** explícito; payload: `sub`, `rol`, `exp`
- RBAC en rutas vía `require_role("secretaria")`
- Headers de seguridad (`SecurityHeadersMiddleware`)
- Logs de eventos de auth sin exponer contraseñas

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

Cobertura principal: auth, RBAC, movimientos, bootstrap de producción, ventana 24 h.

## Contrato OpenAPI

Especificación en `specs/001-registro-cajas/contracts/openapi.yaml`.
