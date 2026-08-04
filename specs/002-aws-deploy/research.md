# Research: Despliegue en AWS del Registro de Cajas

**Feature**: `002-aws-deploy`  
**Date**: 2026-08-04

## R1 — Arquitectura AWS objetivo

**Decision**: Frontend estático en **S3 + CloudFront**; API en **EC2 t4g.micro** (Docker) como origen de CloudFront `/api/*`; base de datos en **RDS PostgreSQL 16** (`db.t4g.micro`, Single-AZ); secretos en **SSM Parameter Store** (SecureString); IaC con **Terraform** en `infra/`. **Sin** ALB, ECS Fargate, ECR ni NAT Gateway.

**Rationale**:
- Alineado con principio VI (costo mínimo) y amend FR-015 (~USD 20–32/mes vs ~USD 40–60+).
- CloudFront provee URL HTTPS pública sin dominio propio.
- EC2 t4g.micro + Docker reutiliza imagen existente sin costo de orquestación.
- Terraform satisface FR-007 (despliegue repetible).
- us-east-1 elegido en clarificación (costo/servicios).

**Alternatives considered**:
- **ECS Fargate + ALB** (diseño v1): ~USD 25–35/mes adicionales en ALB+NAT+ECS; rechazado tras amend costo mínimo.
- **App Runner**: más simple pero menos control de red/VPC con RDS privado.
- **Lambda + API Gateway**: cold starts y contenedor monolítico FastAPI menos natural.

## R2 — URL pública y HTTPS sin dominio propio

**Decision**: Una sola URL de usuario vía **CloudFront** que sirve el frontend y enruta `/api/*` al **origen EC2** (puerto 8000, HTTP origin). Certificado **ACM** en CloudFront (región us-east-1 obligatoria para CloudFront).

**Rationale**:
- Cumple FR-001, FR-002 y SC-004 con una URL compartible (`https://d1234abcd.cloudfront.net`).
- Evita CORS complejo: frontend y API comparten origen en producción.
- No requiere compra de dominio ni ALB (~USD 16–22/mes ahorrados).

**Alternatives considered**:
- **ALB como origen intermedio** (diseño v1): costo adicional sin beneficio en carga baja.
- **Dos URLs** (CloudFront + EC2 directo): peor UX y CORS adicional.

## R3 — Base de datos vacía y bootstrap de producción

**Decision**: En producción el entrypoint ejecuta **solo** `alembic upgrade head` + **`bootstrap_production`** (nuevo script): inserta catálogo de 15 cajas si vacío y crea usuario admin desde secretos. **No** ejecuta `seed.py` completo (sin `escribano`/`escribano` ni `admin`/`admin` de dev).

**Rationale**:
- Cumple FR-003, FR-004, FR-005: esquema + cajas maestras sí; sin datos operativos ni usuarios de desarrollo.
- Reutiliza `CAJAS_CATALOG` y lógica idempotente de `seed_cajas` / `seed_admin_user`.
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` inyectados desde SSM Parameter Store (no en imagen).

**Alternatives considered**:
- **Migración con INSERT de cajas**: válido; bootstrap script es más explícito y testeable.
- **Seed completo con flag**: riesgo de ejecutar escribano dev por error.

## R4 — Secretos y configuración

**Decision**: **SSM Parameter Store** (tipo `SecureString`) almacena: `DATABASE_URL` (o componentes), `JWT_SECRET`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`. EC2 instance profile lee params vía IAM; contenedor recibe env en `docker compose`. Variables no sensibles (`CORS_ORIGINS`, `JWT_EXPIRE_HOURS`) en env file.

**Rationale**:
- Cumple FR-008 y SC-006 con menor costo que Secrets Manager (~USD 2–4/mes ahorrados).
- Suficiente para rotación manual documentada en quickstart.

**Alternatives considered**:
- **Secrets Manager** (diseño v1): rotación automática; costo extra no justificado en v1.
- **Env vars en user_data en texto**: rechazado por seguridad.

## R5 — Red y seguridad

**Decision**: VPC con subnets públicas (EC2) y privadas (RDS). **Sin NAT Gateway.** RDS **no** expuesto a internet; solo security group desde EC2. CloudFront termina TLS; EC2 SG permite puerto 8000 solo desde CloudFront managed prefix list.

**Rationale**:
- Principio IV (TLS en CloudFront; datos en reposo en RDS encrypted).
- Elimina NAT Gateway (~USD 32+/mes).
- RDS Single-AZ en subnet privada cumple FR-013.

**Alternatives considered**:
- **NAT Gateway + ECS en subnet privada** (diseño v1): costo alto para carga mínima.
- **RDS público**: rechazado por superficie de ataque.

## R6 — Backups y disponibilidad RDS

**Decision**: RDS PostgreSQL 16, `db.t4g.micro`, **Single-AZ**, `backup_retention_period = 7` (default mínimo), `storage_encrypted = true`, `deletion_protection = true` (prod).

**Rationale**:
- Cumple FR-012 y FR-013 según clarificaciones.
- Costo acotado (~USD 15–25/mes región us-east-1, estimación orientativa).

**Alternatives considered**:
- **Multi-AZ**: rechazado en clarificación.
- **Aurora Serverless**: mayor costo base para carga mínima.

## R7 — Migraciones y actualizaciones

**Decision**: Contenedor backend en arranque ejecuta `alembic upgrade head` antes de `uvicorn`. Despliegue: build imagen local → `docker save` + `scp` a EC2 o `docker build` en instancia vía `deploy-aws.sh`. **Sin ECR.**

**Rationale**:
- Cumple FR-009, FR-010: migraciones idempotentes; datos persisten en RDS entre deploys.
- Evita costo y complejidad de ECR para un solo host.

**Alternatives considered**:
- **ECR + pull en EC2**: válido si CI madura; diferido para minimizar costo v1.
- **Blue/green**: fuera de alcance v1.

## R8 — Frontend build de producción

**Decision**: `npm run build` produce assets estáticos; `VITE_API_BASE_URL=""` (same-origin vía CloudFront `/api` proxy). Sync a S3; invalidación CloudFront en deploy.

**Rationale**:
- Build estático de bajo costo; mismo patrón que desarrollo con proxy.
- No se ejecuta Vite dev server en producción.

**Alternatives considered**:
- **Frontend en ECS**: mayor costo sin beneficio para SPA estática.

## R9 — Testing (Hybrid)

**Decision**:
- **Unit**: scripts shell/Python de validación pre-deploy (`check-secrets.sh`, parser de tfvars); tests de `bootstrap_production` idempotencia en pytest.
- **Smoke post-deploy**: script `scripts/smoke-aws.sh` contra URL pública (health, HTTPS redirect, login admin, cajas sin movimientos).

**Rationale**:
- Cumple Testing Strategy Hybrid del spec y FR-011.
- No TDD estricto en HCL Terraform; sí `terraform validate` + `tflint` en CI local opcional.

**Alternatives considered**:
- **Terratest completo**: valioso pero costoso en tiempo; diferido si no hay cuenta CI dedicada.

## R10 — Estimación de costo mensual (orientativa)

| Servicio | Configuración | Costo est. USD/mes |
|----------|---------------|-------------------|
| RDS | db.t4g.micro Single-AZ, 20GB | ~12–18 |
| EC2 | t4g.micro, 1 instancia | ~6–8 |
| EBS | 8GB gp3 | ~0.80 |
| CloudFront + S3 | tráfico bajo | ~1–5 |
| SSM Parameter Store | 4 SecureString params | ~0–1 |
| **Total** | | **~20–32** |

*Estimación para pocos usuarios; us-east-1; sin dominio propio; sin ALB/ECS/NAT.*

### Diseño anterior (v1, superseded)

| Servicio | Costo est. USD/mes |
|----------|-------------------|
| ECS + ALB + NAT + Secrets Manager | +25–40 adicional |
| **Total v1** | **~40–60+** |

## R11 — Amend 2026-08-04: Arquitectura lean por costo mínimo

**Decision**: Adoptar arquitectura **EC2 + CloudFront + RDS + SSM** eliminando ALB, ECS Fargate, ECR y NAT Gateway. Single EC2 aceptado (sin HA de compute).

**Rationale**:
- Cumple FR-015 y SC-007 (≤ USD 35/mes).
- Carga ≤ 10 usuarios concurrentes no justifica orquestación Fargate.
- Constitution VI actualizada: preferir EC2 mínima sobre ECS+ALB+NAT.

**Alternatives considered**:
- **Mantener ECS+ALB**: mayor resiliencia operativa; costo ~2× superior.
- **Lightsail**: más simple pero menos integración Terraform/RDS VPC.
- **Lambda**: refactor significativo del monolito FastAPI.

**Impacto en artefactos**: `plan.md`, `data-model.md`, `contracts/infrastructure.md`, `tasks.md` (pending), `quickstart.md`.
