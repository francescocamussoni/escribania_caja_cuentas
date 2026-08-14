# Quickstart: Despliegue AWS — Registro de Cajas

**Feature**: `002-aws-deploy`  
**Region**: `us-east-1`  
**Prerrequisito**: Feature `001-registro-cajas` implementada y validada en local.

> Documentación operativa consolidada: [docs/desarrollo-aws.md](../../docs/desarrollo-aws.md)  
> Usuarios en producción: [docs/usuarios-y-contraseñas.md](../../docs/usuarios-y-contraseñas.md)

## 1. Prerrequisitos locales

| Herramienta | Versión mínima | Uso |
|-------------|----------------|-----|
| AWS CLI | 2.x | Autenticación y operaciones |
| Terraform | ≥ 1.5 | Provisionar infraestructura |
| Docker | 24+ | Build imagen backend |
| Node.js | 20+ | Build frontend estático |
| jq, curl | — | Smoke tests |

```bash
aws configure   # credenciales con permisos EC2, RDS, S3, CloudFront, SSM, IAM
aws sts get-caller-identity
```

## 2. Estructura prevista (post-implementación)

```text
infra/
├── main.tf
├── variables.tf
├── outputs.tf
├── modules/
│   ├── vpc/
│   ├── rds/
│   ├── compute/       # EC2 t4g.micro + Docker
│   ├── frontend/
│   └── secrets/       # SSM Parameter Store
└── environments/
    └── prod.tfvars.example

scripts/
├── deploy-aws.sh          # orquestación build + push + apply + smoke
├── smoke-aws.sh           # contrato smoke-tests.md
└── check-secrets.sh       # valida que no hay secretos en repo

backend/src/app/
└── bootstrap_production.py  # cajas + admin; NO seed de desarrollo
```

## 3. Configurar secretos (antes del primer deploy)

**No commitear valores reales.** Copiar ejemplo:

```bash
cp infra/environments/prod.tfvars.example infra/environments/prod.tfvars
```

Generar secretos:

```bash
export JWT_SECRET=$(openssl rand -hex 32)
export DB_PASSWORD=$(openssl rand -base64 24)
export ADMIN_USERNAME="prod-admin"
export ADMIN_PASSWORD=$(openssl rand -base64 16)
```

Tras `terraform apply`, cargar en **SSM Parameter Store** (SecureString) vía
Terraform o AWS CLI. Documentar nombres de parámetros en output.

## 4. Build imagen backend (sin ECR)

```bash
# Desde raíz del repo
docker build -t escribania-backend:latest ./backend
```

La imagen se transfiere a EC2 durante `deploy-aws.sh` (`docker save` + `scp` o
`docker build` remoto). No se usa ECR en arquitectura lean.

## 5. Build frontend de producción

```bash
cd frontend
npm ci
VITE_API_BASE_URL="" npm run build
# Artefactos en frontend/dist/ → sync a S3 (terraform o aws s3 sync)
```

## 6. Provisionar infraestructura

```bash
cd infra
terraform init
terraform plan -var-file=environments/prod.tfvars
terraform apply -var-file=environments/prod.tfvars
```

Obtener URL pública:

```bash
terraform output -raw public_url
# Ejemplo: https://d111111abcdef8.cloudfront.net
```

## 7. Verificar despliegue (smoke tests)

```bash
export BASE_URL=$(cd infra && terraform output -raw public_url)
export ADMIN_USER="prod-admin"
export ADMIN_PASS="<desde-ssm-parameter-store>"

./scripts/smoke-aws.sh
```

Casos verificados: ver [contracts/smoke-tests.md](./contracts/smoke-tests.md).

## 8. Primer acceso de usuario

1. Abrir `public_url` en el navegador.
2. Iniciar sesión con `ADMIN_USER` / `ADMIN_PASS` (rol secretaria).
3. Verificar: 15 cajas disponibles, sin movimientos históricos.
4. Crear usuarios adicionales (escribanos) según [docs/usuarios-y-contraseñas.md](../../docs/usuarios-y-contraseñas.md)
   (`./scripts/aws-create-user.sh --username … --rol escribano`).

## 9. Actualizar aplicación (sin perder datos)

Actualizaciones de **código** (backend/frontend) no deben recrear RDS ni borrar
movimientos existentes (FR-009). Usar deploy de aplicación sin `terraform apply`
salvo que cambien recursos de infraestructura.

### Procedimiento recomendado (app-only)

```bash
# Desde la raíz del repo — omite terraform, solo rebuild + EC2 + S3 + smoke
SKIP_TERRAFORM=1 \
ADMIN_USER="prod-admin" \
ADMIN_PASS="<desde-prod.tfvars-o-ssm>" \
make deploy-aws

# Equivalente directo:
SKIP_TERRAFORM=1 ADMIN_USER="prod-admin" ADMIN_PASS="..." ./scripts/deploy-aws.sh
```

Qué hace el script en modo app-only:

1. Build imagen Docker backend (`linux/arm64`) y transferencia a EC2 vía S3 + SSM
2. Reinicio del contenedor (`load-env-from-ssm.sh` + `docker compose up`)
3. Build frontend con `VITE_API_BASE_URL=""` y `aws s3 sync` al bucket
4. Invalidación CloudFront `/*`
5. Smoke tests (ST-001–ST-008 si hay credenciales admin)

### Verificar persistencia de datos

Tras el deploy, los movimientos y saldos en RDS **deben conservarse**:

```bash
export BASE_URL=$(cd infra && terraform output -raw public_url)
export ADMIN_USER="prod-admin"
export ADMIN_PASS="..."
export SMOKE_CASES="ST-005,ST-006,ST-007,ST-008"

./scripts/smoke-aws.sh
```

Si ya existían movimientos antes del update, ST-007/ST-008 pueden fallar (esperado:
esos casos validan BD vacía en primer deploy). En updates, verificar manualmente en
la UI que los movimientos previos siguen visibles.

### Cuándo SÍ correr `terraform apply`

Solo cuando cambian módulos Terraform (VPC, SG, CloudFront, variables de
instancia, etc.). Para cambios de código de aplicación, **no** es necesario.

```bash
# Infra + app (primer deploy o cambio de infra)
ADMIN_USER="prod-admin" ADMIN_PASS="..." make deploy-aws
```

### Qué evitar en updates rutinarios

| Acción | Riesgo |
|--------|--------|
| `terraform destroy` | Pérdida total de datos |
| `terraform apply` que fuerza recreación de `aws_db_instance` | BD vacía tras bootstrap |
| Cambiar `identifier` de RDS en Terraform | Nueva instancia vacía |
| `user_data_replace_on_change` en EC2 sin imagen desplegada | API caída hasta `deploy-aws.sh` |

Las migraciones Alembic corren en cada arranque del contenedor (`entrypoint.sh`);
solo aplican cambios de esquema, no borran datos operativos.

## 10. Operaciones destructivas

### `terraform destroy`

Elimina **toda** la infraestructura del stack: VPC, EC2, RDS, S3, CloudFront, SSM
parameters gestionados por Terraform.

**Antes de ejecutar:**

1. Exportar o anotar snapshot ID de RDS en consola AWS (RDS → Snapshots)
2. Confirmar que no hay datos de producción que deban conservarse
3. Ejecutar desde `infra/`:

```bash
cd infra
terraform destroy -var-file=environments/prod.tfvars
```

Efecto: **pérdida irreversible** de movimientos, usuarios y configuración en RDS
(salvo restauración desde snapshot manual).

### Recrear instancia RDS

Ocurre si Terraform detecta que `aws_db_instance` debe reemplazarse (`forces
replacement`), por ejemplo al cambiar `identifier`, subnet group incompatible, o
ciertos atributos inmutables.

Efecto post-recreación:

1. Nueva BD vacía
2. Próximo arranque del contenedor: `alembic upgrade head` + `bootstrap_production`
3. 15 cajas + admin bootstrap; **0 movimientos** (como primer deploy)

**Mitigación:** revisar siempre `terraform plan` antes de `apply`. Si aparece
`aws_db_instance.this must be replaced`, detener y evaluar snapshot/restore.

### Recrear EC2

Menos crítico para datos (están en RDS). Si EC2 se reemplaza:

1. Ejecutar `./scripts/deploy-aws.sh` (o `SKIP_TERRAFORM=1 make deploy-aws`) para
   subir imagen Docker y levantar contenedor
2. Secretos siguen en SSM; bootstrap es idempotente (no duplica admin/cajas)

### Checklist antes de operaciones destructivas

- [ ] Snapshot manual de RDS creado (consola o `aws rds create-db-snapshot`)
- [ ] `terraform plan` revisado — sin `destroy` inesperado en RDS
- [ ] Ventana de mantenimiento acordada (downtime en URL pública)
- [ ] Credenciales admin y `prod.tfvars` respaldados fuera del repo

## 11. Troubleshooting

| Síntoma | Causa probable | Acción |
|---------|----------------|--------|
| 502 en `/api/*` | Contenedor no healthy en EC2 | SSH a instancia; `docker logs`; verificar `DATABASE_URL` en SSM |
| Login 401 con admin prod | Bootstrap no ejecutado | Logs contenedor: buscar `bootstrap_production` |
| Login 401 con admin/admin | Esperado | Credenciales dev no existen en prod |
| CORS error | `CORS_ORIGINS` sin dominio CloudFront | Actualizar env contenedor con URL exacta |
| SPA 404 en refresh | CloudFront sin error page → index.html | Configurar custom error response 403/404 → `/index.html` |

## 12. Costo estimado

Ver `research.md` R10 — ~USD 20–32/mes para carga baja en us-east-1 (arquitectura lean).

## 13. Checklist pre-producción

### Verificación automática (local + conectividad)

```bash
make validate-infra
make check-secrets
make preprod-checklist
```

Valida: `.gitignore`, escaneo de secretos, RDS en módulo/tfvars.example, outputs
sin valores sensibles, y smoke ST-001–ST-003 contra `terraform output public_url`.

### Verificación completa (deploy activo)

Con credenciales admin de producción (desde SSM o `prod.tfvars` local, nunca en git):

```bash
ADMIN_USER="prod-admin" ADMIN_PASS="..." make preprod-checklist
```

Checklist:

- [x] `prod.tfvars` en `.gitignore`
- [x] Secretos en SSM Parameter Store, no en repo (`check-secrets.sh`)
- [x] RDS: Single-AZ, backups 7 días, encryption at rest (módulo + tfvars.example)
- [x] HTTPS en CloudFront (output `public_url`)
- [ ] Smoke tests ST-001 a ST-008 pasan *(requiere comando anterior con credenciales)*
- [ ] `admin`/`admin` rechazado (ST-004)
- [ ] 15 cajas, 0 movimientos en primer deploy (ST-006, ST-007)
