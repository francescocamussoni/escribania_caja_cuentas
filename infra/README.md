# Infraestructura AWS — Registro de Cajas

Terraform para arquitectura lean (EC2 + CloudFront + RDS + SSM).

**Documentación:** [docs/desarrollo-aws.md](../docs/desarrollo-aws.md)

Terraform root module para desplegar la aplicación en **AWS us-east-1** con
arquitectura lean: **EC2** (API Docker) + **CloudFront/S3** (frontend) + **RDS**
(PostgreSQL) + **SSM Parameter Store** (secretos).

## Prerrequisitos

| Herramienta | Versión mínima |
|-------------|----------------|
| [Terraform](https://www.terraform.io/downloads) | ≥ 1.5 |
| [AWS CLI](https://aws.amazon.com/cli/) | 2.x |
| [Docker](https://docs.docker.com/get-docker/) | 24+ (build imagen backend) |

Credenciales AWS con permisos para EC2, RDS, S3, CloudFront, SSM, IAM y VPC.

```bash
aws configure
aws sts get-caller-identity
```

## Estructura

```text
infra/
├── main.tf              # Provider y tags
├── variables.tf         # Variables del root module
├── outputs.tf           # Outputs (public_url, etc. — ver tareas T014+)
├── versions.tf          # Provider AWS ~> 5.0, región us-east-1
├── environments/
│   ├── prod.tfvars.example
│   └── prod.tfvars      # gitignored — copiar desde el ejemplo
└── modules/             # vpc, rds, compute, frontend, secrets (T011+)
```

## Inicio rápido

Guía completa de despliegue: **[specs/002-aws-deploy/quickstart.md](../specs/002-aws-deploy/quickstart.md)**

```bash
# 1. Variables de entorno (sin secretos)
cp environments/prod.tfvars.example environments/prod.tfvars

# 2. Validar configuración (Phase 2 checkpoint — T015)
terraform init
terraform validate
terraform fmt -check -recursive

# Plan con prod.tfvars.example requiere secretos (usar prod.tfvars real o -var):
terraform plan -var-file=environments/prod.tfvars.example \
  -var="jwt_secret=..." -var="db_password=..." \
  -var="admin_username=..." -var="admin_password=..."

# Verificar en el plan: multi_az=false, backup_retention_period=7, sin aws_nat_gateway

# 3. Antes de apply: cargar secretos en SSM (ver quickstart §3)
# terraform apply -var-file=environments/prod.tfvars
```

## Secretos

No incluir `JWT_SECRET`, contraseñas de BD ni credenciales de admin en
`prod.tfvars`. Usar SSM Parameter Store (SecureString). Verificar el repo con:

```bash
./scripts/check-secrets.sh
./scripts/validate-infra-contract.sh
./scripts/validate-outputs-security.sh
make validate-infra
make preprod-checklist
```

Validación de contrato INF-001–INF-010:
`specs/002-aws-deploy/contracts/infrastructure.md`

## Costo estimado

~USD 20–32/mes para carga baja (`specs/002-aws-deploy/research.md` R10).

## Referencias

- Spec: `specs/002-aws-deploy/spec.md`
- Plan: `specs/002-aws-deploy/plan.md`
- Contrato infra: `specs/002-aws-deploy/contracts/infrastructure.md`
