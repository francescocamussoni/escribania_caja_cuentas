# Implementation Plan: Despliegue en AWS del Registro de Cajas

**Branch**: `002-aws-deploy` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/002-aws-deploy/spec.md`

## Summary

Desplegar la aplicación **Registro de Cajas** (FastAPI + React + PostgreSQL) en
**AWS us-east-1** con URL pública HTTPS (CloudFront), base de datos **vacía de
datos operativos** al primer arranque, bootstrap seguro del admin vía secretos, y
despliegue repetible con **Terraform**. Arquitectura **lean (costo mínimo)**:
S3+CloudFront (SPA + `/api/*`) → **EC2 t4g.micro** (Docker, API) → RDS PostgreSQL
Single-AZ (`db.t4g.micro`, backups 7 días). Sin ALB, ECS Fargate, ECR ni NAT Gateway.

## Technical Context

**Language/Version**: HCL (Terraform ≥ 1.5), Bash; Python 3.12 (bootstrap backend); TypeScript (frontend build)  
**Primary Dependencies**: AWS provider ~5.x; Docker en EC2; Alembic (migraciones en arranque contenedor)  
**Storage**: RDS PostgreSQL 16 Single-AZ; S3 (frontend estático); SSM Parameter Store (SecureString)  
**Testing**: Hybrid — `terraform validate`, pytest para `bootstrap_production`, `scripts/smoke-aws.sh` post-deploy (contrato `contracts/smoke-tests.md`)  
**Target Platform**: AWS `us-east-1` — producción internet-facing  
**Project Type**: Infraestructura + cambios mínimos en backend (`bootstrap_production`, entrypoint)  
**Performance Goals**: Misma SLA que local (< 500ms p95 API); ≤ 10 usuarios concurrentes  
**Constraints**: HTTPS obligatorio vía CloudFront; secretos en SSM Parameter Store; sin seed dev en prod; costo ~USD 20–32/mes  
**Scale/Scope**: 1 entorno prod, 1 URL pública, sin dominio propio, sin Multi-AZ, single EC2

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I — Integridad Financiera | ✅ PASS | Sin cambio de lógica de negocio; RDS ACID; migraciones antes de servir tráfico |
| II — RBAC | ✅ PASS | Misma API desplegada; auth JWT sin cambios funcionales |
| III — Wireframes | ✅ PASS | Mismo frontend estático; sin cambios de layout |
| IV — Seguridad | ✅ PASS | TLS CloudFront; RDS privado; SSM SecureString; logs CloudWatch; encryption at rest RDS; SG restringe API a CloudFront |
| V — Fullstack Desacoplado | ✅ PASS | Frontend S3/CloudFront; API en EC2; contratos smoke e infra separados |
| VI — Costo Mínimo AWS | ✅ PASS | db.t4g.micro, EC2 t4g.micro, S3+CloudFront; sin ALB/ECS/NAT; SSM en lugar de Secrets Manager; Single-AZ; us-east-1 |

**Post-design re-check (Phase 1)**: ✅ All gates pass. No Complexity Tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/002-aws-deploy/
├── plan.md              # This file
├── research.md          # Phase 0 — AWS architecture decisions
├── data-model.md        # Phase 1 — infra configuration model
├── quickstart.md        # Phase 1 — deploy runbook
├── contracts/
│   ├── smoke-tests.md   # Post-deploy verification contract
│   └── infrastructure.md # Expected AWS resources
└── tasks.md             # Phase 2 (/spec-kitti.tasks)
```

### Source Code (repository root — cambios previstos)

```text
infra/                          # NEW — Terraform modules
├── main.tf
├── variables.tf
├── outputs.tf
├── modules/
│   ├── vpc/
│   ├── rds/
│   ├── compute/          # EC2 t4g.micro + Docker host
│   ├── frontend/
│   └── secrets/          # SSM Parameter Store
└── environments/
    ├── prod.tfvars.example
    └── prod.tfvars            # gitignored

scripts/                        # NEW
├── deploy-aws.sh
├── smoke-aws.sh
└── check-secrets.sh

backend/src/app/
├── bootstrap_production.py     # NEW — cajas + admin idempotente
├── entrypoint.sh                 # NEW — alembic + bootstrap + uvicorn
└── seed.py                       # sin cambios; NO usado en prod

backend/tests/unit/
└── test_bootstrap_production.py  # NEW — Hybrid unit tests

frontend/                         # build prod sin cambios de código
└── dist/                         # artefacto → S3

docker-compose.yml                # sin cambios (solo local)
```

**Structure Decision**: Se añade capa `infra/` (Terraform) y `scripts/` de
operaciones; cambios mínimos en `backend/` para bootstrap de producción. El
frontend solo requiere build con `VITE_API_BASE_URL=""`.

## Plan Jerárquico (para Itti-Kit)

### Work Unit 1: Bootstrap de producción (backend)

**Propósito**: Separar el arranque de producción del seed de desarrollo; garantizar BD vacía de datos operativos con catálogo de cajas y admin desde secretos.

**Entidades afectadas**:
- `Usuario` (solo admin bootstrap)
- `Caja` (catálogo maestro 15)
- `BootstrapState` (lógico)

**Archivos a crear/modificar**:
- `backend/src/app/bootstrap_production.py` — idempotente: `seed_cajas` + `seed_admin_user` desde settings
- `backend/src/app/entrypoint.sh` — `alembic upgrade head` → bootstrap → uvicorn
- `backend/Dockerfile` — ENTRYPOINT al script
- `backend/tests/unit/test_bootstrap_production.py` — idempotencia, sin escribano dev

**Pruebas**:
- `pytest backend/tests/unit/test_bootstrap_production.py`

**Subtareas internas**:
1. Extraer `seed_cajas` reutilizable desde `seed.py`
2. Implementar `bootstrap_production` sin `seed_escribano_user`
3. Guard: variable `ENVIRONMENT=production` deshabilita `run_seed()` en otros paths
4. Entrypoint shell con fail-fast
5. Unit tests Hybrid (idempotencia, 15 cajas, 1 usuario, 0 movimientos)

**Criterio de éxito**: `pytest` pasa; contenedor local con `ENVIRONMENT=production` no crea usuario `escribano`.

**Estimación**: 4 h

---

### Work Unit 2: Módulos Terraform base (VPC + RDS + SSM)

**Propósito**: Red mínima (sin NAT), base de datos PostgreSQL Single-AZ con backups, y secretos en SSM Parameter Store.

**Entidades afectadas**:
- `VpcNetwork`, `DatabaseInstance`, `SecretBundle`

**Archivos a crear/modificar**:
- `infra/modules/vpc/*`
- `infra/modules/rds/*`
- `infra/modules/secrets/*` (SSM SecureString)
- `infra/environments/prod.tfvars.example`

**Pruebas**:
- `terraform validate`
- `scripts/check-secrets.sh` (sin secretos en tfvars commiteados)

**Subtareas internas**:
1. VPC, subnets públicas (EC2) y privadas (RDS), **sin NAT Gateway**
2. RDS postgres 16, db.t4g.micro, Single-AZ, backup 7d, encrypted
3. SSM Parameter Store: db, jwt, admin (SecureString)
4. Outputs: rds_endpoint (sensitive)
5. Tags constitutionales

**Criterio de éxito**: `terraform plan` muestra RDS con `multi_az=false`, `backup_retention_period=7`, `publicly_accessible=false`; sin recursos `aws_nat_gateway`.

**Estimación**: 6 h

---

### Work Unit 3: EC2 compute + Docker backend

**Propósito**: Ejecutar API FastAPI en contenedor Docker sobre una instancia EC2 t4g.micro; health check en `/health`.

**Entidades afectadas**:
- `ComputeInstance`

**Archivos a crear/modificar**:
- `infra/modules/compute/*` — EC2, IAM instance profile, SG (puerto 8000 solo desde CloudFront prefix list)
- `infra/docker-compose.prod.yml` — servicio backend con env desde SSM (vía user_data o script)
- `backend/Dockerfile` — sin cambios funcionales (ya con entrypoint)

**Pruebas**:
- `terraform validate`
- Health check post-apply: `GET /health` vía CloudFront `/api/health`

**Subtareas internas**:
1. EC2 t4g.micro en subnet pública con Elastic IP opcional (o DNS público de instancia como origin)
2. user_data: instalar Docker, pull/build imagen, `docker compose up`
3. IAM role: lectura SSM params, CloudWatch logs
4. Security group: inbound 8000 restringido a CloudFront managed prefix list
5. CloudWatch log group (agente o docker logs)

**Criterio de éxito**: Contenedor healthy; `curl https://<cloudfront>/api/health` → 200.

**Dependencias**: WU-2

**Estimación**: 6 h

---

### Work Unit 4: Frontend estático (S3 + CloudFront)

**Propósito**: Publicar SPA con URL HTTPS única; proxy `/api/*` al origen EC2.

**Entidades afectadas**:
- `StaticSite`, `PublicEndpoint`

**Archivos a crear/modificar**:
- `infra/modules/frontend/*` — S3, OAC, CloudFront, behaviors
- Script sync en `scripts/deploy-aws.sh` (parcial)

**Pruebas**:
- Smoke ST-002, ST-003 (post-deploy)

**Subtareas internas**:
1. S3 bucket privado + policy CloudFront OAC
2. CloudFront distribution con default root `index.html`
3. Behavior `/api/*` → EC2 origin (HTTP:8000, HTTPS viewer)
4. Custom error responses SPA (403/404 → index.html)
5. Output `public_url`

**Criterio de éxito**: `terraform output public_url` abre login en navegador; `/api/health` responde vía misma URL.

**Dependencias**: WU-3

**Estimación**: 6 h

---

### Work Unit 5: Scripts de despliegue y smoke tests

**Propósito**: Orquestación repetible y verificación automatizada post-deploy (FR-007, FR-011).

**Entidades afectadas**:
- Contratos `smoke-tests.md`, `infrastructure.md`

**Archivos a crear/modificar**:
- `scripts/deploy-aws.sh`
- `scripts/smoke-aws.sh`
- `scripts/check-secrets.sh`

**Pruebas**:
- Ejecutar smoke contra entorno de prueba (manual o CI)

**Subtareas internas**:
1. `deploy-aws.sh`: build backend image → transfer/build on EC2 → build frontend → terraform apply → invalidación CF
2. `smoke-aws.sh`: implementar ST-001 a ST-008
3. `check-secrets.sh`: grep patterns en repo
4. Documentar en quickstart.md (ya generado; validar tras implementación)

**Criterio de éxito**: Operador sigue quickstart y smoke pasa en < 60 min (SC-003).

**Dependencias**: WU-1, WU-4

**Estimación**: 4 h

---

### Work Unit 6: Integración CORS y configuración producción

**Propósito**: Alinear backend con URL CloudFront; asegurar que EC2 recibe `CORS_ORIGINS` correcto desde SSM/env.

**Entidades afectadas**:
- `PublicEndpoint`, configuración EC2/Docker

**Archivos a crear/modificar**:
- `infra/modules/compute/variables.tf` — `cors_origins` desde output CloudFront
- `backend/src/app/core/config.py` — validar lectura en prod (si necesario)

**Pruebas**:
- Smoke login desde browser vía CloudFront URL

**Subtareas internas**:
1. Pasar dominio CloudFront a `CORS_ORIGINS` en env del contenedor
2. Verificar JWT y DATABASE_URL desde SSM Parameter Store
3. Prueba end-to-end login + listar cajas

**Criterio de éxito**: Login y API funcionan desde URL pública sin errores CORS.

**Dependencias**: WU-4, WU-5

**Estimación**: 2 h

---

### Notas para Itti-Kit

**Total estimado de Work Units**: 6  
**Tiempo total estimado**: ~28 h  
**Work Units en paralelo tras WU-2**: WU-1 puede iniciar en paralelo con WU-2; WU-4 tras WU-3

## Complexity Tracking

> Sin violaciones de constitución que requieran justificación.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Phase 0 & Phase 1 Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Research | [research.md](./research.md) | ✅ Complete |
| Data model | [data-model.md](./data-model.md) | ✅ Complete |
| Smoke contract | [contracts/smoke-tests.md](./contracts/smoke-tests.md) | ✅ Complete |
| Infra contract | [contracts/infrastructure.md](./contracts/infrastructure.md) | ✅ Complete |
| Quickstart | [quickstart.md](./quickstart.md) | ✅ Complete |

## Next Steps

1. `/spec-kitti.tasks` — generar tareas atómicas desde Work Units
2. `/spec-kitti.tasks.shape` — Work Units para implementación
3. `/spec-kitti.implement [WU-ID]` — comenzar por WU-1 (bootstrap) en paralelo con WU-2 (Terraform base)
