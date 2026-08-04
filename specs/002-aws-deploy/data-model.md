# Data Model: Despliegue en AWS

**Feature**: `002-aws-deploy`  
**Date**: 2026-08-04 | **Amended**: 2026-08-04 (arquitectura lean)

Este documento describe el **modelo de configuración e infraestructura** del entorno
de producción. No redefine el modelo de datos de negocio (ver
`specs/001-registro-cajas/data-model.md`).

## Entidades de infraestructura

### DeploymentStack

Representa el conjunto de recursos AWS provisionados para un entorno de producción.

| Atributo | Tipo | Reglas |
|----------|------|--------|
| `name` | string | Identificador único, p. ej. `escribania-prod` |
| `region` | string | Fijo: `us-east-1` (FR-014) |
| `environment` | enum | `production` en v1 |
| `terraform_state_key` | string | Clave en backend S3 remoto (opcional v1: local state) |

**Relaciones**: contiene 1 `VpcNetwork`, 1 `DatabaseInstance`, 1 `ComputeInstance`,
1 `StaticSite`, 1 `SecretBundle`, 1 `PublicEndpoint`.

---

### VpcNetwork

Red aislada para componentes compute y datos.

| Atributo | Tipo | Reglas |
|----------|------|--------|
| `cidr` | CIDR | p. ej. `10.0.0.0/16` |
| `public_subnet_ids` | list | Para EC2 (API) |
| `private_subnet_ids` | list | Para RDS (mín. 2 AZ para RDS subnet group, instancia Single-AZ) |

**Reglas**:
- RDS en subnets privadas sin ruta a internet.
- EC2 en subnet pública con SG restrictivo (solo CloudFront → :8000).
- **Sin NAT Gateway** (amend costo mínimo).

---

### DatabaseInstance (RDS)

| Atributo | Tipo | Reglas |
|----------|------|--------|
| `engine` | string | `postgres` |
| `engine_version` | string | `16` |
| `instance_class` | string | `db.t4g.micro` |
| `multi_az` | boolean | `false` (FR-013) |
| `backup_retention_days` | integer | `7` (FR-012) |
| `storage_encrypted` | boolean | `true` |
| `database_name` | string | `escribania_cajas` |
| `master_username` | string | No hardcodeado; generado o en secret |
| `master_password` | secret ref | SSM Parameter Store (SecureString) |

**Estado inicial de datos de negocio** (tras bootstrap):
- Tablas creadas por Alembic.
- 15 filas en `caja` (catálogo maestro).
- 0 filas en `movimiento`.
- 1 fila en `usuario` (admin bootstrap).
- 0 usuarios de desarrollo (`admin`/`admin` local, `escribano`/`escribano`).

---

### ComputeInstance (EC2)

| Atributo | Tipo | Reglas |
|----------|------|--------|
| `instance_type` | string | `t4g.micro` |
| `ami` | string | Amazon Linux 2023 ARM64 o Ubuntu 22.04 ARM |
| `subnet_id` | ref | Subnet pública |
| `security_group_id` | ref | Inbound 8000 desde CloudFront prefix list |
| `iam_instance_profile` | ref | Lectura SSM + CloudWatch logs |
| `container_image` | string | Imagen Docker local (build on host o `docker load`) |
| `health_check_path` | string | `/health` |

**Comportamiento de arranque** (contenedor):
1. `alembic upgrade head`
2. `python -m app.bootstrap_production` (idempotente)
3. `uvicorn app.main:app --host 0.0.0.0 --port 8000`

---

### StaticSite (S3 + CloudFront)

| Atributo | Tipo | Reglas |
|----------|------|--------|
| `bucket_name` | string | Globalmente único |
| `cloudfront_distribution_id` | string | Asignado por AWS |
| `default_root_object` | string | `index.html` |
| `api_origin_path` | string | `/api/*` → EC2 origin :8000 |

**Build input**: artefactos de `frontend/dist/` con `VITE_API_BASE_URL=""`.

---

### SecretBundle

Conjunto de secretos de producción (FR-008).

| Secreto | Contenido | Consumidor |
|---------|-----------|------------|
| `/escribania/prod/db` | `DATABASE_URL` o host/user/pass/db | EC2 / contenedor |
| `/escribania/prod/jwt` | `JWT_SECRET` | EC2 / contenedor |
| `/escribania/prod/admin` | `ADMIN_USERNAME`, `ADMIN_PASSWORD` | bootstrap_production |

**Reglas**:
- Tipo SSM: `SecureString`.
- Nunca en repositorio Git ni en variables de build de imagen Docker.
- Rotación manual documentada en quickstart.

---

### PublicEndpoint

URL de acceso para usuarios finales.

| Atributo | Tipo | Reglas |
|----------|------|--------|
| `url` | URL | `https://<cloudfront-domain>` |
| `tls_version` | string | TLS 1.2+ |
| `http_redirect` | boolean | `true` — HTTP → HTTPS |

**Reglas**:
- `CORS_ORIGINS` en backend debe incluir el dominio CloudFront exacto.
- Documentar en output Terraform cómo obtener la URL tras `terraform apply`.

---

### BootstrapState

Estado lógico tras el primer arranque exitoso en producción.

| Campo | Valor esperado (primer deploy) |
|-------|-------------------------------|
| `schema_version` | head de Alembic |
| `cajas_count` | 15 |
| `movimientos_count` | 0 |
| `usuarios_count` | 1 (admin) |
| `dev_seed_executed` | `false` |

**Transiciones**:
- `pending` → `bootstrapped`: tras primer `bootstrap_production` exitoso.
- `bootstrapped` → `bootstrapped`: arranques posteriores idempotentes (no duplica usuarios/cajas).
- `destroyed` → `pending`: solo si se recrea RDS (operación destructiva documentada).

---

## Diagrama de relaciones

```text
Internet
   │
   ▼
CloudFront (HTTPS URL pública)
   ├── /*  → S3 (SPA estática)
   └── /api/* → EC2 t4g.micro :8000 (Docker / FastAPI)
                    │
                    ▼ (privado, SG)
               RDS PostgreSQL (Single-AZ, backups 7d)
                    ▲
               SSM Parameter Store (SecureString)
```

## Validaciones

| Regla | Verificación |
|-------|--------------|
| BD sin movimientos iniciales | Smoke: `GET /api/v1/cajas/1/movimientos` → `total_items: 0` |
| Sin credenciales dev | Smoke: login `admin`/`admin` → 401 |
| Catálogo completo | Smoke: `GET /api/v1/cajas` → length 15 |
| HTTPS obligatorio | Smoke: `curl -I http://URL` → 301/302 a https |
| Secretos fuera del repo | `gitleaks` / revisión manual de `infra/` y user_data |
| Sin NAT/ALB/ECS | `terraform plan` sin `aws_nat_gateway`, `aws_lb`, `aws_ecs_service` |
