# Infrastructure Contract — Recursos AWS esperados

**Feature**: `002-aws-deploy`  
**Version**: 2.0.0 (amend: arquitectura lean EC2)  
**Region**: `us-east-1`

Contrato declarativo de recursos que `terraform apply` debe crear o referenciar.
Usado para validación post-provision (`terraform plan` sin drift inesperado).

## Recursos obligatorios

| ID | Tipo AWS | Nombre lógico | Propiedades críticas |
|----|----------|---------------|----------------------|
| INF-001 | `aws_vpc` | `escribania-vpc` | CIDR documentado en tfvars |
| INF-002 | `aws_subnet` (×≥3) | public + private | Al menos 2 AZ para RDS subnet group; **sin NAT** |
| INF-003 | `aws_db_instance` | `escribania-db` | `engine=postgres`, `engine_version=16`, `instance_class=db.t4g.micro`, `multi_az=false`, `backup_retention_period=7`, `storage_encrypted=true`, `publicly_accessible=false` |
| INF-004 | `aws_instance` | `escribania-api` | `instance_type=t4g.micro`, Docker host, puerto 8000 |
| INF-005 | `aws_security_group` | `escribania-api-sg` | Inbound 8000 solo desde CloudFront managed prefix list |
| INF-006 | `aws_iam_instance_profile` | `escribania-api-profile` | `ssm:GetParameter`, CloudWatch logs |
| INF-007 | `aws_s3_bucket` | `escribania-frontend-*` | Block public access; OAC para CloudFront |
| INF-008 | `aws_cloudfront_distribution` | — | Default root `index.html`; behavior `/api/*` → EC2 origin |
| INF-009 | `aws_ssm_parameter` (×4) | db, jwt, admin user, admin pass | Tipo `SecureString`; sin valores en outputs |
| INF-010 | `aws_security_group` | `escribania-rds-sg` | RDS solo desde SG de EC2 |

## Recursos explícitamente excluidos (amend costo mínimo)

- `aws_lb` / ALB
- `aws_ecs_cluster` / `aws_ecs_service` / Fargate
- `aws_ecr_repository`
- `aws_nat_gateway`
- `aws_secretsmanager_secret` (reemplazado por SSM)

## Outputs obligatorios (Terraform)

| Output | Descripción |
|--------|-------------|
| `public_url` | URL HTTPS de CloudFront para usuarios |
| `ec2_public_dns` | DNS público EC2 (diagnóstico; API vía CloudFront) |
| `rds_endpoint` | Host RDS (solo operadores, sensible) |

## Outputs prohibidos

- `JWT_SECRET` en texto plano
- `ADMIN_PASSWORD` en texto plano
- `DATABASE_URL` completo con password en outputs públicos

## Tags requeridos en todos los recursos

```hcl
Project     = "escribania-cajas"
Environment = "production"
ManagedBy   = "terraform"
Feature     = "002-aws-deploy"
```

## Validación

```bash
cd infra/
terraform init
terraform validate
terraform plan -var-file=environments/prod.tfvars
```

Post-apply: ejecutar contrato `smoke-tests.md` contra `public_url`.
