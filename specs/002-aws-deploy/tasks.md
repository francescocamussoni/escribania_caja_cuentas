# Tasks: Despliegue en AWS del Registro de Cajas

**Input**: Design documents from `/specs/002-aws-deploy/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/  
**Testing**: Hybrid (spec.md → Testing Strategy) — unit tests en bootstrap y scripts; smoke post-despliegue; sin TDD estricto en IaC Terraform

**Organization**: Tareas agrupadas por user story. Infraestructura compartida en Setup/Foundational.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Paralelizable (archivos distintos, sin dependencias incompletas)
- **[USn]**: User story del spec.md

## Path Conventions

- Infraestructura: `infra/`, módulos en `infra/modules/`
- Scripts operativos: `scripts/`
- Backend (bootstrap): `backend/src/app/`, tests en `backend/tests/`
- Contratos: `specs/002-aws-deploy/contracts/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Estructura base para Terraform, scripts y configuración segura.

- [x] T001 Create `infra/main.tf`, `infra/variables.tf`, and `infra/outputs.tf` with AWS provider pinned to `us-east-1` in `infra/versions.tf`
- [x] T002 [P] Create `infra/environments/prod.tfvars.example` documenting region, instance sizes, and non-secret variables per `research.md`
- [x] T003 [P] Update `.gitignore` to exclude `infra/environments/prod.tfvars`, `*.tfstate`, `*.tfstate.backup`, and `.terraform/`
- [x] T004 [P] Create `infra/README.md` with prerequisites (AWS CLI, Terraform, Docker) and pointer to `specs/002-aws-deploy/quickstart.md`
- [x] T005 [P] Create `scripts/check-secrets.sh` scanning repo for hardcoded secrets patterns (JWT, passwords, DATABASE_URL with credentials)

**Checkpoint**: `infra/` tree exists; `scripts/check-secrets.sh` is executable; secrets patterns documented.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Bootstrap de producción en backend y capa de red/datos/secrets en AWS. **Bloquea todas las user stories.**

- [x] T006 [P] Create unit tests for production bootstrap in `backend/tests/unit/test_bootstrap_production.py` (idempotency, 15 cajas, no `escribano` user, no movimientos)
- [x] T007 Refactor reusable `seed_cajas()` export in `backend/src/app/seed.py` for use by bootstrap
- [x] T008 Implement idempotent `bootstrap_production` in `backend/src/app/bootstrap_production.py` (cajas + admin from settings; excludes `seed_escribano_user`)
- [x] T009 Create production entrypoint `backend/src/app/entrypoint.sh` running `alembic upgrade head`, `python -m app.bootstrap_production`, then `uvicorn`
- [x] T010 Update `backend/Dockerfile` to use `ENTRYPOINT` via `backend/src/app/entrypoint.sh`
- [x] T011 [P] Implement Terraform VPC module in `infra/modules/vpc/` (VPC, public/private subnets, **no NAT**, security groups per `data-model.md`)
- [x] T012 [P] Implement Terraform secrets module in `infra/modules/secrets/` (SSM Parameter Store SecureString for db, jwt, admin per `contracts/infrastructure.md`)
- [x] T013 Implement Terraform RDS module in `infra/modules/rds/` (`postgres` 16, `db.t4g.micro`, `multi_az=false`, `backup_retention_period=7`, `storage_encrypted=true`, `publicly_accessible=false`)
- [x] T014 Wire VPC, SSM secrets, and RDS modules in `infra/main.tf` with required tags (`Project`, `Environment`, `ManagedBy`, `Feature`)
- [x] T015 Run `terraform init` and `terraform validate` in `infra/` against `infra/environments/prod.tfvars.example`

**Checkpoint**: `pytest backend/tests/unit/test_bootstrap_production.py` green; `terraform validate` passes; RDS plan shows Single-AZ and 7-day backups.

---

## Phase 3: User Story 1 — Acceder a la aplicación por URL pública (Priority: P1) 🎯 MVP

**Goal**: Usuarios acceden vía URL HTTPS pública (CloudFront); login y navegación funcionan desde internet.

**Independent Test**: Abrir `terraform output public_url` en navegador externo → pantalla login; `GET /api/health` vía misma URL → 200; HTTP redirige a HTTPS (ST-001, ST-002, ST-003).

### Tests for User Story 1 (Hybrid)

- [x] T016 [P] [US1] Implement smoke cases ST-001, ST-002, ST-003 in `scripts/smoke-aws.sh` per `specs/002-aws-deploy/contracts/smoke-tests.md`

### Implementation for User Story 1

- [x] T017 [P] [US1] Implement EC2 compute module in `infra/modules/compute/` (t4g.micro, IAM instance profile for SSM, SG for CloudFront → :8000)
- [x] T018 [US1] Add EC2 user_data and `infra/docker-compose.prod.yml` for backend container with env from SSM in `infra/modules/compute/`
- [x] T020 [US1] Wire compute module in `infra/main.tf` with health check path `/health` and RDS/SSM dependencies
- [x] T021 [P] [US1] Implement frontend module in `infra/modules/frontend/` (private S3 bucket, CloudFront OAC, default root `index.html`)
- [x] T022 [US1] Add CloudFront behavior `/api/*` forwarding to EC2 origin in `infra/modules/frontend/main.tf`
- [x] T023 [US1] Add CloudFront custom error responses (403/404 → `/index.html`) for SPA routing in `infra/modules/frontend/main.tf`
- [x] T024 [US1] Export `public_url` output in `infra/outputs.tf` (CloudFront HTTPS domain)
- [x] T025 [US1] Inject `CORS_ORIGINS` from CloudFront domain into EC2 container env in `infra/modules/compute/variables.tf`
- [x] T026 [US1] Create `scripts/deploy-aws.sh` with backend Docker build, image transfer to EC2 (`docker save`/`scp` or remote build), and `VITE_API_BASE_URL="" npm run build` for `frontend/dist/`
- [x] T027 [US1] Add S3 sync and CloudFront invalidation steps to `scripts/deploy-aws.sh` after Terraform apply

**Checkpoint**: `public_url` serves login page; `/api/health` returns 200 over HTTPS; smoke ST-001–ST-003 pass.

---

## Phase 4: User Story 2 — Arrancar con base de datos vacía (Priority: P2)

**Goal**: Primer despliegue sin movimientos ni usuarios de desarrollo; catálogo de 15 cajas y admin bootstrap desde secretos.

**Independent Test**: Tras deploy inicial, `admin`/`admin` → 401; login con admin prod → 200; 15 cajas; 0 movimientos; saldo 0 (ST-004–ST-008).

### Tests for User Story 2 (Hybrid)

- [x] T028 [P] [US2] Extend `backend/tests/unit/test_bootstrap_production.py` asserting `ENVIRONMENT=production` path never calls `seed_escribano_user`
- [x] T029 [P] [US2] Implement smoke cases ST-004, ST-005, ST-006, ST-007, ST-008 in `scripts/smoke-aws.sh`

### Implementation for User Story 2

- [x] T030 [US2] Ensure EC2 container sets `ENVIRONMENT=production` and admin credentials from SSM Parameter Store in `infra/modules/compute/main.tf`
- [x] T031 [US2] Verify entrypoint does not invoke `backend/src/app/seed.py` `run_seed()` in production path in `backend/src/app/entrypoint.sh`
- [x] T032 [US2] Document production bootstrap variables (`ADMIN_USERNAME`, `ADMIN_PASSWORD`, `JWT_SECRET`, `DATABASE_URL`) in `.env.example` with note "production uses SSM Parameter Store"
- [x] T033 [US2] Add bootstrap verification step to `scripts/deploy-aws.sh` (log grep or smoke ST-004/ST-006/ST-007 after first deploy)

**Checkpoint**: Dev credentials rejected; prod admin login works; 15 cajas, 0 movimientos, saldo cero; bootstrap unit tests pass.

---

## Phase 5: User Story 3 — Desplegar y mantener de forma repetible (Priority: P3)

**Goal**: Operador puede desplegar y actualizar siguiendo documentación; sin secretos en repo; datos persisten entre updates.

**Independent Test**: Seguir `quickstart.md` desde cero → URL funcional < 60 min; segundo deploy sin recrear RDS → movimientos previos consultables; `check-secrets.sh` clean.

### Implementation for User Story 3

- [x] T034 [US3] Complete orchestration in `scripts/deploy-aws.sh` (terraform init/plan/apply, EC2 image deploy, frontend sync, invalidation, smoke invocation)
- [x] T035 [US3] Finalize `scripts/smoke-aws.sh` with exit codes and `BASE_URL`/`ADMIN_USER`/`ADMIN_PASS` env vars per `contracts/smoke-tests.md`
- [x] T036 [P] [US3] Harden `scripts/check-secrets.sh` to fail CI if `prod.tfvars` or literal secrets committed
- [x] T037 [US3] Add `deploy-aws` and `smoke-aws` targets to root `Makefile` wrapping `scripts/deploy-aws.sh` and `scripts/smoke-aws.sh`
- [x] T038 [US3] Validate Terraform resources match `specs/002-aws-deploy/contracts/infrastructure.md` checklist (INF-001–INF-010; no ALB/ECS/ECR/NAT)
- [x] T039 [US3] Document update-in-place procedure (no RDS recreation) in `specs/002-aws-deploy/quickstart.md` section 9 per FR-009
- [x] T040 [US3] Document destructive operations (terraform destroy, RDS recreate) in `specs/002-aws-deploy/quickstart.md` section 10

**Checkpoint**: Full deploy + smoke green; update redeploy preserves data; no secrets in git.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validación final, seguridad y documentación.

- [x] T041 [P] Add `terraform fmt -check` and `terraform validate` to `Makefile` target `validate-infra`
- [x] T042 Run end-to-end `specs/002-aws-deploy/quickstart.md` checklist (section 13) against deployed environment
- [x] T043 [P] Verify Terraform outputs do not expose `JWT_SECRET`, `ADMIN_PASSWORD`, or full `DATABASE_URL` in `infra/outputs.tf`
- [x] T044 Run `./scripts/check-secrets.sh` and confirm clean result before merge
- [x] T045 [P] Update `specs/001-registro-cajas/quickstart.md` section 11 with link to `specs/002-aws-deploy/quickstart.md` for AWS deploy

**Checkpoint**: All smoke tests pass; quickstart checklist complete; constitution principle IV (no secrets exposed) verified.

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) — BLOCKS all user stories
    ↓
Phase 3 (US1 — URL pública) — MVP
    ↓
Phase 4 (US2 — BD vacía) — depends on US1 infra + bootstrap running
    ↓
Phase 5 (US3 — deploy repetible) — depends on US1 + US2
    ↓
Phase 6 (Polish)
```

### User Story Dependencies

| Story | Depends on | Independent test |
|-------|------------|------------------|
| **US1 (P1)** | Foundational (Phase 2) | Smoke ST-001–ST-003; browser login page |
| **US2 (P2)** | US1 (EC2 live with bootstrap) | Smoke ST-004–ST-008; unit tests bootstrap |
| **US3 (P3)** | US1 + US2 | Full quickstart run; update without data loss |

### Parallel Opportunities

**Phase 1** (after T001):
- T002, T003, T004, T005 in parallel

**Phase 2** (after T007–T010 started):
- T011, T012 in parallel
- T006 can start before T008 (tests first for bootstrap only)

**Phase 3 US1**:
- T016, T017, T021 in parallel
- T018 → T020 → T022 → T023 → T024 → T025 → T026 → T027 sequential

**Phase 4 US2**:
- T028, T029 in parallel

**Phase 5 US3**:
- T036 parallel with T034–T035

---

## Parallel Example: User Story 1

```bash
# After Phase 2 complete, launch in parallel:
Task T016: "Implement smoke ST-001–ST-003 in scripts/smoke-aws.sh"
Task T017: "EC2 compute module in infra/modules/compute/"
Task T021: "Frontend module in infra/modules/frontend/"

# Then sequential:
Task T018 → T020 → T022 → T023 → T024 → T025 → T026 → T027
```

---

## Parallel Example: Foundational

```bash
# Backend track (can start immediately after T001):
T006 → T007 → T008 → T009 → T010

# Infra track (parallel):
T011 + T012 → T013 → T014 → T015
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Smoke ST-001–ST-003; open `public_url` in browser
5. Demo URL pública con login page accesible

### Incremental Delivery

1. Setup + Foundational → red + datos listos
2. US1 → URL HTTPS pública funcional (MVP)
3. US2 → BD vacía verificada + admin bootstrap
4. US3 → deploy script + smoke completo + docs
5. Polish → checklist quickstart + security audit

### Suggested implement order via `/spec-kitti.implement`

| Work Unit (plan.md) | Tasks |
|---------------------|-------|
| WU-1 Bootstrap | T006–T010, T028, T030–T032 |
| WU-2 Terraform base | T011–T015 |
| WU-3 EC2 compute | T017–T020, T018 (`docker-compose.prod.yml`) |
| WU-4 CloudFront | T021–T025, T027 |
| WU-5 Scripts + smoke | T005, T016, T026, T029, T034–T037 |
| WU-6 CORS + polish | T025, T041–T045 |

---

## Task Summary

| Phase | Tasks | Story |
|-------|-------|-------|
| Phase 1 Setup | T001–T005 (5) | — |
| Phase 2 Foundational | T006–T015 (10) | — |
| Phase 3 US1 | T016–T027 (11) | US1 |
| Phase 4 US2 | T028–T033 (6) | US2 |
| Phase 5 US3 | T034–T040 (7) | US3 |
| Phase 6 Polish | T041–T045 (5) | — |
| **Total** | **44** | |

**MVP scope**: Phases 1–3 (26 tasks) → URL pública HTTPS con health check y login page.

**Parallel tasks**: 18 marked `[P]`

**Format validation**: ✅ All 44 tasks use `- [ ]` / `- [x]` with `[Tnnn]` IDs and file paths

---

## Notes

- No UI tasks in this feature — no `figma:` fields required
- Hybrid testing: write `test_bootstrap_production.py` before or alongside T008 (not strict TDD for Terraform)
- Do not commit `infra/environments/prod.tfvars` with real secrets
- `terraform apply` incurs AWS costs (~USD 20–32/mes per `research.md` R10, arquitectura lean)
- US2 smoke tests require first deploy with production admin credentials in SSM Parameter Store
- Amend 2026-08-04: T019 (ALB module) eliminada; arquitectura EC2+CloudFront reemplaza ECS+ALB
