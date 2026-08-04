# Desarrollo AWS (producción)

Despliegue en AWS con arquitectura **lean**: EC2 + CloudFront + S3 + RDS + SSM.
Sin ALB, ECS, ECR ni NAT Gateway (~USD 20–32/mes).

Guía detallada original: `specs/002-aws-deploy/quickstart.md`.

## Arquitectura

```text
Usuario (HTTPS)
    │
    ▼
CloudFront ──► S3 (SPA estática: /, /login, /registro, /consulta)
    │
    └── /api/* ──► EC2 t4g.micro (Docker: FastAPI :8000)
                        │
                        ▼
                   RDS PostgreSQL (privado, Single-AZ)
```

| Componente | Servicio AWS |
|------------|--------------|
| Frontend | S3 + CloudFront |
| API | EC2 `t4g.micro` (ARM) + Docker |
| Base de datos | RDS `db.t4g.micro` PostgreSQL 16 |
| Secretos | SSM Parameter Store (`SecureString`) |
| TLS | Certificado default de CloudFront |

## Prerrequisitos

| Herramienta | Uso |
|-------------|-----|
| AWS CLI 2.x | Credenciales y operaciones |
| Terraform ≥ 1.5 | Infraestructura |
| Docker 24+ | Build imagen backend (`linux/arm64`) |
| Node.js 20+ | Build frontend |
| jq, curl | Smoke tests |

```bash
aws configure
aws sts get-caller-identity
```

## Configuración de secretos

```bash
cp infra/environments/prod.tfvars.example infra/environments/prod.tfvars
```

`prod.tfvars` está en `.gitignore`. Incluir (entre otros):

```hcl
jwt_secret     = "<openssl rand -hex 32>"
db_password    = "<openssl rand -base64 24>"
admin_username = "prod-admin"
admin_password = "<contraseña-segura>"
```

Terraform crea parámetros SSM bajo `/escribania/prod/`:

| Parámetro SSM | Variable en contenedor |
|---------------|------------------------|
| `jwt` | `JWT_SECRET` |
| `db` | `DATABASE_URL` |
| `admin_username` | `ADMIN_USERNAME` |
| `admin_password` | `ADMIN_PASSWORD` |
| `cors_origins` | `CORS_ORIGINS` (URL CloudFront) |

## Primer deploy

```bash
# Validar antes de aplicar
make validate-infra
make check-secrets

# Deploy completo (terraform + app + smoke)
ADMIN_USER="prod-admin" ADMIN_PASS="..." make deploy-aws
```

O por pasos:

```bash
cd infra
terraform init
terraform plan -var-file=environments/prod.tfvars
terraform apply -var-file=environments/prod.tfvars

cd ..
./scripts/deploy-aws.sh
```

URL pública:

```bash
cd infra && terraform output -raw public_url
# https://dxxxx.cloudfront.net
```

## Actualizar solo la aplicación (sin tocar RDS)

Para cambios de código sin modificar infraestructura:

```bash
SKIP_TERRAFORM=1 \
ADMIN_USER="prod-admin" \
ADMIN_PASS="..." \
make deploy-aws
```

El script:

1. Build imagen Docker `linux/arm64` y la sube a EC2 (S3 + SSM)
2. Reinicia contenedor (`load-env-from-ssm.sh` + docker compose)
3. Build frontend → `aws s3 sync` al bucket
4. Invalida caché CloudFront `/*`
5. Ejecuta smoke tests si hay credenciales admin

Los movimientos en RDS **se conservan** (no recrea la base).

## Smoke tests

```bash
export BASE_URL=$(cd infra && terraform output -raw public_url)
export ADMIN_USER="prod-admin"
export ADMIN_PASS="..."
export SMOKE_CASES="ST-001,ST-002,ST-003,ST-004,ST-005,ST-006,ST-007,ST-008"

make smoke-aws
# o checklist completo:
ADMIN_USER="..." ADMIN_PASS="..." make preprod-checklist
```

Contrato: `specs/002-aws-deploy/contracts/smoke-tests.md`.

## Comandos útiles

| Comando | Descripción |
|---------|-------------|
| `make validate-infra` | `terraform fmt/validate` + contrato INF-001–010 |
| `make check-secrets` | Escaneo de secretos en el repo |
| `make deploy-aws` | Orquestación completa |
| `make smoke-aws` | Tests post-deploy |
| `make preprod-checklist` | Checklist §13 del quickstart |

Flags de `deploy-aws.sh`:

- `SKIP_TERRAFORM=1` — solo app
- `--terraform-plan-only` — plan sin apply
- `--skip-smoke` — sin smoke al final

## Bootstrap en producción

Al arrancar el contenedor (`entrypoint.sh`):

1. `alembic upgrade head`
2. `bootstrap_production` — 15 cajas + usuario admin desde SSM
3. **No** crea `escribano` ni movimientos de prueba

Ver [usuarios-y-contraseñas.md](./usuarios-y-contraseñas.md) para altas adicionales.

## Operaciones destructivas

| Acción | Efecto |
|--------|--------|
| `terraform destroy` | Elimina toda la infra; **pérdida de datos** en RDS |
| Recrear `aws_db_instance` | BD vacía; nuevo bootstrap |

Antes de destroy: snapshot manual de RDS. Detalle en `specs/002-aws-deploy/quickstart.md` §9–10.

## Troubleshooting en producción

| Síntoma | Acción |
|---------|--------|
| 502/504 en `/api/*` | Contenedor caído en EC2 → SSM Session Manager, `docker logs` |
| Login 401 con credenciales correctas | Verificar bootstrap; revisar `ADMIN_*` en SSM vs tabla `usuario` |
| Login 401 con `admin`/`admin` | Esperado: credenciales dev no existen en prod |
| CORS error | Actualizar `cors_origins` en SSM con URL exacta de CloudFront |
| SPA 404 al refrescar | CloudFront debe servir `index.html` en 403/404 |

## Infraestructura (Terraform)

Módulos en `infra/modules/`: `vpc`, `rds`, `compute`, `frontend`, `secrets`.

Documentación operativa: `infra/README.md`  
Contrato de recursos: `specs/002-aws-deploy/contracts/infrastructure.md`

## Outputs relevantes

```bash
cd infra
terraform output public_url
terraform output ec2_instance_id
terraform output frontend_bucket_name
terraform output cloudfront_distribution_id
terraform output -json ssm_parameter_names
```

Los outputs **no** exponen valores de secretos (solo nombres de parámetros SSM).
