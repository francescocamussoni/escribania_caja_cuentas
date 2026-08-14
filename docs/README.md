# Registro de Cajas — Escribanía

Documentación del proyecto. La aplicación permite registrar y consultar movimientos de
dinero en cajas/cuentas de una escribanía (seed inicial de 15; altas y archivo por
secretaria), con control de acceso por rol.

## Índice

| Documento | Contenido |
|-----------|-----------|
| [Backend](./backend.md) | API FastAPI, modelos, autenticación, migraciones |
| [Frontend](./frontend.md) | React, rutas, componentes, build |
| [Desarrollo local](./desarrollo-local.md) | Docker Compose, Makefile, tests |
| [Desarrollo AWS](./desarrollo-aws.md) | Terraform, deploy, smoke tests, actualizaciones |
| [Usuarios y contraseñas](./usuarios-y-contraseñas.md) | Roles, bootstrap, alta de usuarios (`aws-create-user.sh`) |

## Quickstart (5 minutos)

```bash
git clone <repo>
cd escribania_caja_cuentas
cp .env.example .env
make up
make migrate
make seed
```

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |

**Credenciales de desarrollo** (solo local, ver [usuarios](./usuarios-y-contraseñas.md)):

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| `admin` | `admin` | Secretaria |
| `escribano` | `escribano` | Escribano |

## Pantallas

| Ruta | Rol | Función |
|------|-----|---------|
| `/login` | Todos | Inicio de sesión |
| `/registro` | Secretaria | Alta, edición y baja de movimientos |
| `/consulta` | Secretaria, Escribano | Saldo e historial (solo lectura para escribano) |
| `/configuracion` | Secretaria | Alta y archivo de cajas |

## Producción (AWS)

URL pública vía CloudFront. Guía completa: [desarrollo-aws.md](./desarrollo-aws.md).

```bash
make validate-infra
make check-secrets
make deploy-aws          # primer deploy o infra + app
SKIP_TERRAFORM=1 make deploy-aws   # solo actualizar código
```

## Specs y contratos

Documentación de diseño en `specs/`:

- `specs/001-registro-cajas/` — funcionalidad de negocio
- `specs/002-aws-deploy/` — infraestructura y despliegue
- `specs/006-config-archivo-cajas/` — alta y archivo de cajas

## Estructura del repositorio

```text
backend/          API FastAPI + Alembic
frontend/         SPA React (Vite)
infra/            Terraform (VPC, EC2, RDS, S3, CloudFront, SSM)
scripts/          deploy-aws.sh, smoke-aws.sh, validaciones
docs/             Esta documentación
specs/            Especificaciones Spec-Kitti
```
