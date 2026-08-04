# Escribanía — Registro de Cajas

Control de ingresos y egresos de cajas y cuentas bancarias para una escribanía.

## Documentación

Toda la documentación operativa está en **[docs/](./docs/README.md)**:

| Guía | Descripción |
|------|-------------|
| [Quickstart](./docs/README.md) | Inicio en 5 minutos |
| [Backend](./docs/backend.md) | API FastAPI, endpoints, modelo de datos |
| [Frontend](./docs/frontend.md) | React, rutas, componentes |
| [Desarrollo local](./docs/desarrollo-local.md) | Docker Compose, Makefile, tests |
| [Desarrollo AWS](./docs/desarrollo-aws.md) | Deploy, smoke tests, actualizaciones |
| [Usuarios y contraseñas](./docs/usuarios-y-contraseñas.md) | Roles secretaria/escribano, bootstrap |

## Inicio rápido

```bash
cp .env.example .env
make up && make migrate && make seed
```

- Frontend: http://localhost:5173  
- API: http://localhost:8000/docs  
- Login dev: `admin` / `admin` (secretaria) o `escribano` / `escribano`

## Specs

- `specs/001-registro-cajas/` — requisitos funcionales
- `specs/002-aws-deploy/` — infraestructura AWS
