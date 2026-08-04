# Quickstart: Registro de Cajas para Escribanía

**Feature**: `001-registro-cajas`  
**Branch**: `001-registro-cajas`

## Prerequisites

- Docker & Docker Compose
- Node.js 20+ (desarrollo frontend sin Docker)
- Python 3.12+ (desarrollo backend sin Docker)

## 1. Clonar y configurar entorno

```bash
git checkout 001-registro-cajas
cp .env.example .env
```

Variables mínimas en `.env`:

```env
DATABASE_URL=postgresql://escribania:escribania@localhost:5432/escribania_cajas
JWT_SECRET=<generar-secreto-aleatorio>
JWT_EXPIRE_HOURS=8
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
```

## 2. Levantar stack local

**Opción recomendada (Makefile):**

```bash
make up           # levanta postgres + backend + frontend
make migrate      # aplicar migraciones Alembic
make seed         # cargar 15 cajas + usuarios dev
make logs         # seguir logs de todos los servicios
make down         # detener y limpiar
```

**Equivalente directo:**

```bash
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
```

Targets disponibles en `Makefile`:

| Target | Acción |
|--------|--------|
| `make up` | Levanta postgres + backend + frontend |
| `make down` | `docker compose down` |
| `make build` | Rebuild imágenes |
| `make migrate` | `alembic upgrade head` |
| `make db-stamp` | Marca migraciones como aplicadas si las tablas ya existen |
| `make seed` | Carga 15 cajas + usuarios `admin` y `escribano` |
| `make test` | pytest backend + npm test frontend |
| `make logs` | `docker compose logs -f` |

Servicios esperados:

| Servicio | URL |
|----------|-----|
| API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Frontend | http://localhost:5173 |
| PostgreSQL | localhost:5432 |

## 3. Migraciones y seed

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
```

Seed crea:
- 15 cajas del catálogo
- Usuario `admin` / `admin` (rol `secretaria`, solo dev)
- Usuario `escribano` / `escribano` (rol `escribano`, solo dev)

## 4. Flujo manual — Login

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | jq
```

Guardar `access_token` para siguientes requests.

## 5. Flujo manual — Registrar entrada (Secretaria)

```bash
TOKEN="<access_token>"

curl -s -X POST http://localhost:8000/api/v1/cajas/1/movimientos \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"descripcion":"Pago cliente","monto":"5000.00","tipo":"entrada"}' | jq
```

## 6. Flujo manual — Consultar saldo e historial

```bash
# Saldo actual
curl -s http://localhost:8000/api/v1/cajas/1/saldo \
  -H "Authorization: Bearer $TOKEN" | jq

# Historial página 1 (20 más recientes)
curl -s "http://localhost:8000/api/v1/cajas/1/movimientos?page=1" \
  -H "Authorization: Bearer $TOKEN" | jq
```

## 7. Flujo manual — Escribano (solo lectura)

Tras `make seed`, usar el usuario de desarrollo:

```bash
# Login como escribano
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"escribano","password":"escribano"}' | jq

# Consulta OK
curl -s http://localhost:8000/api/v1/cajas/1/saldo \
  -H "Authorization: Bearer $ESC_TOKEN" | jq

# Escritura debe fallar 403
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/api/v1/cajas/1/movimientos \
  -H "Authorization: Bearer $ESC_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"descripcion":"test","monto":"100.00","tipo":"entrada"}'
# Esperado: 403
```

## 8. Flujo manual — Editar / eliminar movimiento (Secretaria, ventana 24h)

```bash
# Editar movimiento id=5
curl -s -X PATCH http://localhost:8000/api/v1/cajas/1/movimientos/5 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"descripcion":"Pago corregido","monto":"5500.00"}' | jq

# Eliminar movimiento id=5
curl -s -o /dev/null -w "%{http_code}" \
  -X DELETE http://localhost:8000/api/v1/cajas/1/movimientos/5 \
  -H "Authorization: Bearer $TOKEN"
# Esperado: 204

# Movimiento > 24h debe fallar 422
```

## 9. Ejecutar tests (TDD)

```bash
make test

# O por separado:
docker compose exec backend pytest -v
cd frontend && npm test
```

## 10. Pantallas UI

| Pantalla | Ruta | Rol |
|----------|------|-----|
| Login | `/login` | Todos |
| Registro de Caja | `/registro` | Secretaria |
| Consulta de Caja | `/consulta` | Secretaria, Escribano |

Wireframes de referencia: `registro_de_caja.drawio`, `consulta_de_caja.drawio`.

## 11. Despliegue AWS (producción)

El despliegue en AWS está documentado en la feature **002-aws-deploy** (arquitectura
lean: EC2 + CloudFront + S3 + RDS + SSM Parameter Store).

**Guía completa:** [specs/002-aws-deploy/quickstart.md](../002-aws-deploy/quickstart.md)

| Componente | Servicio AWS |
|------------|--------------|
| Frontend estático | S3 + CloudFront (HTTPS) |
| API | Docker en EC2 `t4g.micro` (origen CloudFront `/api/*`) |
| Base de datos | RDS PostgreSQL `db.t4g.micro` (Single-AZ, backups 7 días) |
| Secretos | SSM Parameter Store (`SecureString`) |

Comandos habituales desde la raíz del repo:

```bash
make validate-infra      # terraform fmt/validate + contrato INF
make check-secrets       # escaneo pre-merge
make deploy-aws          # terraform + build + smoke
make smoke-aws           # post-deploy (BASE_URL + credenciales admin)
make preprod-checklist   # checklist §13 de 002-aws-deploy
```

Variables de entorno en producción se cargan desde SSM en el contenedor (`load-env-from-ssm.sh`);
localmente usar `.env.example` como referencia.

## Troubleshooting

| Problema | Solución |
|----------|----------|
| `DuplicateTable` en `make migrate` | Las tablas existen sin `alembic_version`. Ejecutar `make db-stamp` y luego `make migrate` |
| 401 en todas las rutas | Token expirado (8h) o JWT_SECRET distinto |
| Subtotal incorrecto | Verificar orden `created_at` + `id`; revisar tests integración |
| DB connection refused | `docker compose ps` — esperar healthcheck de postgres |
| Cambios backend no visibles en tests Docker | `docker compose build backend && docker compose up -d backend` |
