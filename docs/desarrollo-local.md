# Desarrollo local

Guía para levantar el stack completo en tu máquina con Docker Compose.

## Prerrequisitos

| Herramienta | Versión |
|-------------|---------|
| Docker | 24+ |
| Docker Compose | v2 |
| Make | (opcional, recomendado) |
| Node.js | 20+ (solo si desarrollás frontend fuera de Docker) |
| Python | 3.12+ (solo si desarrollás backend fuera de Docker) |

## Configuración inicial

```bash
cp .env.example .env
```

Variables mínimas (`.env`):

```env
DATABASE_URL=postgresql://escribania:escribania@localhost:5432/escribania_cajas
JWT_SECRET=<openssl rand -hex 32>
JWT_EXPIRE_HOURS=8
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
CORS_ORIGINS=http://localhost:5173
ENVIRONMENT=development
```

## Levantar el stack

```bash
make up        # postgres + backend + frontend
make migrate   # alembic upgrade head
make seed      # 15 cajas iniciales + admin + escribano (solo dev)
```

Equivalente manual:

```bash
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
```

### Servicios

| Servicio | Contenedor | Puerto | URL |
|----------|------------|--------|-----|
| PostgreSQL | `escribania_postgres` | 5432 | `localhost:5432` |
| Backend | `escribania_backend` | 8000 | http://localhost:8000 |
| Frontend | `escribania_frontend` | 5173 | http://localhost:5173 |

Swagger: http://localhost:8000/docs

## Comandos Makefile

| Comando | Acción |
|---------|--------|
| `make up` | Build + levanta los 3 servicios |
| `make down` | Detiene y elimina contenedores |
| `make build` | Rebuild de imágenes |
| `make logs` | `docker compose logs -f` |
| `make ps` | Estado de contenedores |
| `make migrate` | Aplica migraciones Alembic |
| `make db-stamp` | Marca migraciones si las tablas ya existen |
| `make seed` | Carga datos de desarrollo |
| `make test` | pytest + vitest |
| `make test-backend` | Solo pytest |
| `make test-frontend` | Solo vitest |

## Flujo de trabajo habitual

### Cambios en backend

```bash
# El código se monta en la imagen; rebuild si cambian dependencias
docker compose build backend
docker compose up -d backend
make test-backend
```

### Cambios en frontend

Hot-reload automático: `frontend/src` está montado como volumen en Docker.

### Nueva migración

```bash
docker compose exec backend alembic revision -m "descripcion"
# editar alembic/versions/...
make migrate
```

## Credenciales de prueba

Ver [usuarios-y-contraseñas.md](./usuarios-y-contraseñas.md).

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| `admin` | `admin` | Secretaria |
| `escribano` | `escribano` | Escribano |

## Pruebas manuales rápidas

### Login

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | jq
```

### Registrar movimiento

```bash
TOKEN="<access_token>"
curl -s -X POST http://localhost:8000/api/v1/cajas/1/movimientos \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"descripcion":"Pago cliente","monto":"5000.00","tipo":"entrada"}' | jq
```

Más ejemplos en `specs/001-registro-cajas/quickstart.md` (secciones 4–8).

## Desarrollo sin Docker

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
# PostgreSQL corriendo en localhost:5432
export DATABASE_URL=postgresql://escribania:escribania@localhost:5432/escribania_cajas
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --app-dir src
```

### Frontend

```bash
cd frontend
npm ci
export VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

## Troubleshooting

| Problema | Solución |
|----------|----------|
| `DuplicateTable` en migrate | Tablas sin `alembic_version` → `make db-stamp` y luego `make migrate` |
| DB connection refused | `make ps` — esperar healthcheck de postgres |
| 401 en todas las rutas | Token expirado o `JWT_SECRET` distinto al del login |
| Subtotal incorrecto | Revisar tests de integración en `backend/tests/` |
| Backend no refleja cambios | `docker compose build backend && docker compose up -d backend` |
| Puerto 5432 ocupado | Cambiar `POSTGRES_PORT` en `.env` |

## Qué no commitear

- `.env` con secretos reales
- `infra/environments/prod.tfvars`

Validar antes de push: `make check-secrets`
