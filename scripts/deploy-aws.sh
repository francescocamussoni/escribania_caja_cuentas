#!/usr/bin/env bash
# Full AWS deploy orchestration (T034): terraform → backend EC2 → frontend S3 → CF → smoke.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="${ROOT}/infra"
FRONTEND_DIR="${ROOT}/frontend"
BACKEND_DIR="${ROOT}/backend"

BACKEND_IMAGE="${BACKEND_IMAGE:-escribania-backend:latest}"
DOCKER_PLATFORM="${DOCKER_PLATFORM:-linux/arm64}"
INSTALL_DIR="/opt/escribania"
DEPLOY_PREFIX="_deploy"
TFVARS_FILE="${TFVARS_FILE:-${INFRA_DIR}/environments/prod.tfvars}"
DEFAULT_SMOKE_CASES="ST-001,ST-002,ST-003,ST-004,ST-005,ST-006,ST-007,ST-008"
BASIC_SMOKE_CASES="ST-001,ST-002,ST-003"

SKIP_TERRAFORM="${SKIP_TERRAFORM:-0}"
SKIP_BACKEND_BUILD="${SKIP_BACKEND_BUILD:-0}"
SKIP_FRONTEND_BUILD="${SKIP_FRONTEND_BUILD:-0}"
SKIP_EC2_DEPLOY="${SKIP_EC2_DEPLOY:-0}"
SKIP_FRONTEND_SYNC="${SKIP_FRONTEND_SYNC:-0}"
SKIP_CF_INVALIDATION="${SKIP_CF_INVALIDATION:-0}"
SKIP_SMOKE="${SKIP_SMOKE:-0}"
SKIP_BOOTSTRAP_VERIFY="${SKIP_BOOTSTRAP_VERIFY:-0}"
TERRAFORM_PLAN_ONLY="${TERRAFORM_PLAN_ONLY:-0}"

usage() {
  cat <<'EOF'
Usage: ./scripts/deploy-aws.sh [options]

Orchestrate production deploy: terraform init/plan/apply, backend image to EC2,
frontend build + S3 sync, CloudFront invalidation, and smoke tests.

Options:
  --skip-terraform        Skip terraform init/plan/apply (app-only redeploy)
  --terraform-plan-only   Run terraform plan but do not apply
  --skip-backend-build    Skip docker build
  --skip-frontend-build   Skip npm run build
  --skip-ec2-deploy       Skip image transfer and API restart on EC2
  --skip-frontend-sync    Skip aws s3 sync to frontend bucket
  --skip-cf-invalidation  Skip CloudFront cache invalidation
  --skip-smoke            Skip all post-deploy smoke tests
  --skip-bootstrap-verify Skip auth/bootstrap smoke cases (ST-004–ST-008)
  -h, --help              Show this help

Environment:
  TFVARS_FILE            Terraform var file (default: infra/environments/prod.tfvars)
  SKIP_TERRAFORM         Set to 1 to skip terraform (same as --skip-terraform)
  TERRAFORM_PLAN_ONLY    Set to 1 to plan without apply
  BACKEND_IMAGE          Docker tag (default: escribania-backend:latest)
  DOCKER_PLATFORM        Build platform (default: linux/arm64 for t4g.micro)
  FRONTEND_BUCKET        Override S3 bucket for frontend + deploy staging
  FRONTEND_BUCKET_SUFFIX Override bucket suffix when not using account ID
  AWS_REGION             AWS region (default: from terraform output or us-east-1)
  ADMIN_USER             Production admin username (smoke ST-005+)
  ADMIN_PASS             Production admin password (smoke ST-005+)
  SMOKE_CASES            Override smoke cases (default: ST-001–ST-008 if creds set)
  SKIP_SMOKE             Set to 1 to skip smoke tests
  SKIP_BOOTSTRAP_VERIFY  Set to 1 to run only ST-001–ST-003

Prerequisites:
  - prod.tfvars configured (gitignored) for first deploy
  - docker, npm, aws CLI, terraform, jq, gzip, curl
EOF
}

log() {
  echo "==> $*"
}

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --skip-terraform) SKIP_TERRAFORM=1 ;;
      --terraform-plan-only) TERRAFORM_PLAN_ONLY=1 ;;
      --skip-backend-build) SKIP_BACKEND_BUILD=1 ;;
      --skip-frontend-build) SKIP_FRONTEND_BUILD=1 ;;
      --skip-ec2-deploy) SKIP_EC2_DEPLOY=1 ;;
      --skip-frontend-sync) SKIP_FRONTEND_SYNC=1 ;;
      --skip-cf-invalidation) SKIP_CF_INVALIDATION=1 ;;
      --skip-smoke) SKIP_SMOKE=1 ;;
      --skip-bootstrap-verify) SKIP_BOOTSTRAP_VERIFY=1 ;;
      -h | --help)
        usage
        exit 0
        ;;
      *)
        fail "Unknown option: $1"
        ;;
    esac
    shift
  done
}

terraform_output() {
  local name="$1"
  (cd "$INFRA_DIR" && terraform output -raw "$name" 2>/dev/null) || return 1
}

resolve_aws_region() {
  if [[ -n "${AWS_REGION:-}" ]]; then
    echo "${AWS_REGION}"
    return
  fi
  terraform_output aws_region || echo "us-east-1"
}

resolve_frontend_bucket() {
  if [[ -n "${FRONTEND_BUCKET:-}" ]]; then
    echo "${FRONTEND_BUCKET}"
    return
  fi
  if bucket="$(terraform_output frontend_bucket_name 2>/dev/null)"; then
    echo "${bucket}"
    return
  fi
  local prefix account suffix
  prefix="$(terraform_output name_prefix || echo "escribania-prod")"
  account="$(aws sts get-caller-identity --query Account --output text)"
  suffix="${FRONTEND_BUCKET_SUFFIX:-${account}}"
  echo "${prefix}-frontend-${suffix}"
}

resolve_tfvars_file() {
  if [[ ! -f "${TFVARS_FILE}" ]]; then
    fail "Terraform var file not found: ${TFVARS_FILE} (copy from prod.tfvars.example)"
  fi
  echo "${TFVARS_FILE}"
}

run_terraform() {
  local tfvars

  if [[ "${SKIP_TERRAFORM}" == "1" ]]; then
    log "Skipping terraform (--skip-terraform / SKIP_TERRAFORM=1)"
    return
  fi

  tfvars="$(resolve_tfvars_file)"
  export AWS_REGION="$(resolve_aws_region)"

  log "Terraform init (${INFRA_DIR})"
  (cd "${INFRA_DIR}" && terraform init -input=false)

  log "Terraform validate"
  (cd "${INFRA_DIR}" && terraform validate)

  log "Terraform plan -var-file=${tfvars}"
  (cd "${INFRA_DIR}" && terraform plan -input=false -var-file="${tfvars}")

  if [[ "${TERRAFORM_PLAN_ONLY}" == "1" ]]; then
    log "Terraform plan-only mode — skipping apply"
    return
  fi

  log "Terraform apply -var-file=${tfvars} (-auto-approve)"
  (cd "${INFRA_DIR}" && terraform apply -input=false -var-file="${tfvars}" -auto-approve)

  log "Terraform apply complete"
}

build_backend() {
  if [[ "$SKIP_BACKEND_BUILD" == "1" ]]; then
    log "Skipping backend Docker build"
    docker image inspect "${BACKEND_IMAGE}" >/dev/null 2>&1 \
      || fail "Image ${BACKEND_IMAGE} not found (run without --skip-backend-build)"
    return
  fi

  log "Building backend image (${DOCKER_PLATFORM}): ${BACKEND_IMAGE}"
  docker build --platform "${DOCKER_PLATFORM}" -t "${BACKEND_IMAGE}" "${BACKEND_DIR}"
}

build_frontend() {
  if [[ "$SKIP_FRONTEND_BUILD" == "1" ]]; then
    log "Skipping frontend build"
    return
  fi

  log "Building frontend (VITE_API_BASE_URL=\"\" for same-origin /api)"
  (
    cd "${FRONTEND_DIR}"
    npm ci
    VITE_API_BASE_URL="" npm run build
  )
  log "Frontend artifacts: ${FRONTEND_DIR}/dist/"
}

wait_for_ssm_command() {
  local command_id="$1"
  local instance_id="$2"
  local status=""
  local attempt

  for attempt in $(seq 1 60); do
    status="$(aws ssm list-command-invocations \
      --command-id "${command_id}" \
      --details \
      --query "CommandInvocations[?InstanceId=='${instance_id}'].Status | [0]" \
      --output text 2>/dev/null || echo "Pending")"

    case "${status}" in
      Success)
        return 0
        ;;
      Failed | Cancelled | TimedOut | DeliveryTimedOut | ExecutionTimedOut)
        log "SSM command failed (status=${status})"
        aws ssm get-command-invocation \
          --command-id "${command_id}" \
          --instance-id "${instance_id}" \
          --query '{Status:Status,Stdout:StandardOutputContent,Stderr:StandardErrorContent}' \
          --output text || true
        return 1
        ;;
      Pending | InProgress | Delayed)
        sleep 5
        ;;
      *)
        sleep 5
        ;;
    esac
  done

  fail "Timed out waiting for SSM command ${command_id}"
}

deploy_backend_to_ec2() {
  local instance_id bucket region tar_path staging_key s3_uri command_id
  local remote_script

  instance_id="$(terraform_output ec2_instance_id)" \
    || fail "ec2_instance_id not found — run terraform apply first"
  bucket="$(resolve_frontend_bucket)"
  region="$(resolve_aws_region)"
  export AWS_REGION="${region}"

  tar_path="$(mktemp /tmp/escribania-backend.XXXXXX.tar.gz)"
  staging_key="${DEPLOY_PREFIX}/escribania-backend-$(date +%Y%m%d%H%M%S).tar.gz"
  s3_uri="s3://${bucket}/${staging_key}"

  log "Saving Docker image to ${tar_path}"
  docker save "${BACKEND_IMAGE}" | gzip > "${tar_path}"

  log "Uploading image to ${s3_uri}"
  aws s3 cp "${tar_path}" "${s3_uri}"
  rm -f "${tar_path}"

  remote_script="$(cat <<EOF
set -euo pipefail
export AWS_DEFAULT_REGION=${region}
aws s3 cp '${s3_uri}' /tmp/escribania-backend.tar.gz
gunzip -c /tmp/escribania-backend.tar.gz | docker load
rm -f /tmp/escribania-backend.tar.gz
docker tag ${BACKEND_IMAGE} escribania-backend:latest 2>/dev/null || true
${INSTALL_DIR}/load-env-from-ssm.sh
cd ${INSTALL_DIR}
docker compose down 2>/dev/null || true
systemctl restart escribania-api.service
sleep 5
docker ps --filter name=escribania-api
curl -sf http://127.0.0.1:8000/health || echo "WARN: local health check failed (container may still be starting)"
EOF
)"

  log "Loading image on EC2 (${instance_id}) via SSM"
  command_id="$(aws ssm send-command \
    --instance-ids "${instance_id}" \
    --document-name "AWS-RunShellScript" \
    --comment "deploy-aws.sh backend image load" \
    --parameters "$(jq -n --arg script "${remote_script}" '{commands: [$script]}')" \
    --query "Command.CommandId" \
    --output text)"

  if ! wait_for_ssm_command "${command_id}" "${instance_id}"; then
    aws s3 rm "${s3_uri}" 2>/dev/null || true
    fail "EC2 deploy failed — see SSM output above"
  fi

  log "Removing staging object ${s3_uri}"
  aws s3 rm "${s3_uri}" || true
  log "Backend deployed on EC2"
}

sync_frontend_to_s3() {
  local bucket region

  if [[ "$SKIP_FRONTEND_SYNC" == "1" ]]; then
    log "Skipping frontend S3 sync"
    return
  fi

  [[ -d "${FRONTEND_DIR}/dist" ]] \
    || fail "frontend/dist not found — run without --skip-frontend-build first"

  bucket="$(resolve_frontend_bucket)"
  region="$(resolve_aws_region)"
  export AWS_REGION="${region}"

  log "Syncing ${FRONTEND_DIR}/dist/ to s3://${bucket}/"
  aws s3 sync "${FRONTEND_DIR}/dist/" "s3://${bucket}/" --delete
  log "Frontend synced to S3"
}

invalidate_cloudfront() {
  local distribution_id region invalidation_id

  if [[ "$SKIP_CF_INVALIDATION" == "1" ]]; then
    log "Skipping CloudFront invalidation"
    return
  fi

  distribution_id="$(terraform_output cloudfront_distribution_id)" \
    || fail "cloudfront_distribution_id not found — run terraform apply first"
  region="$(resolve_aws_region)"
  export AWS_REGION="${region}"

  log "Invalidating CloudFront cache (distribution ${distribution_id}, paths /*)"
  invalidation_id="$(aws cloudfront create-invalidation \
    --distribution-id "${distribution_id}" \
    --paths "/*" \
    --query "Invalidation.Id" \
    --output text)"

  log "CloudFront invalidation created: ${invalidation_id} (may take 1–3 minutes)"
}

wait_for_public_health() {
  local base_url attempt status
  base_url="${1%/}"

  for attempt in $(seq 1 24); do
    status="$(curl -sS -o /dev/null -w "%{http_code}" "${base_url}/api/health" 2>/dev/null || echo "000")"
    if [[ "${status}" == "200" ]]; then
      log "Public API health check OK (${base_url}/api/health)"
      return 0
    fi
    log "Waiting for public API health (attempt ${attempt}/24, status=${status})..."
    sleep 10
  done

  fail "Public API health check did not return 200"
}

resolve_smoke_cases() {
  if [[ -n "${SMOKE_CASES:-}" ]]; then
    echo "${SMOKE_CASES}"
    return
  fi
  if [[ "${SKIP_BOOTSTRAP_VERIFY}" == "1" ]]; then
    echo "${BASIC_SMOKE_CASES}"
    return
  fi
  if [[ -n "${ADMIN_USER:-}" && -n "${ADMIN_PASS:-}" ]]; then
    echo "${DEFAULT_SMOKE_CASES}"
    return
  fi
  log "WARN: ADMIN_USER/ADMIN_PASS not set — smoke limited to ${BASIC_SMOKE_CASES}"
  echo "${BASIC_SMOKE_CASES}"
}

run_smoke_tests() {
  local public_url smoke_script cases

  if [[ "${SKIP_SMOKE}" == "1" ]]; then
    log "Skipping smoke tests (--skip-smoke / SKIP_SMOKE=1)"
    return
  fi

  if [[ "${TERRAFORM_PLAN_ONLY}" == "1" ]]; then
    log "Skipping smoke tests (terraform plan-only)"
    return
  fi

  public_url="$(terraform_output public_url 2>/dev/null || true)"
  if [[ -z "${public_url}" ]]; then
    log "WARN: public_url not found — skipping smoke tests"
    return
  fi

  cases="$(resolve_smoke_cases)"
  if [[ "${cases}" == *"ST-005"* || "${cases}" == *"ST-006"* || "${cases}" == *"ST-007"* || "${cases}" == *"ST-008"* ]]; then
    if [[ -z "${ADMIN_USER:-}" || -z "${ADMIN_PASS:-}" ]]; then
      fail "ADMIN_USER and ADMIN_PASS required for smoke cases: ${cases}"
    fi
  fi

  smoke_script="${ROOT}/scripts/smoke-aws.sh"
  [[ -f "${smoke_script}" ]] || fail "Smoke script not found: ${smoke_script}"

  wait_for_public_health "${public_url}"

  log "Running smoke tests (${cases})"
  BASE_URL="${public_url}" \
    ADMIN_USER="${ADMIN_USER:-}" \
    ADMIN_PASS="${ADMIN_PASS:-}" \
    SMOKE_CASES="${cases}" \
    bash "${smoke_script}"

  log "Smoke tests passed"
}

main() {
  parse_args "$@"

  require_cmd docker
  require_cmd aws
  require_cmd jq
  require_cmd gzip
  require_cmd curl

  if [[ "${SKIP_TERRAFORM}" != "1" ]]; then
    require_cmd terraform
  fi

  if [[ "$SKIP_FRONTEND_BUILD" != "1" ]]; then
    require_cmd npm
  fi

  run_terraform

  if [[ "${TERRAFORM_PLAN_ONLY}" == "1" ]]; then
    log "Plan-only run complete (no app deploy or smoke)"
    exit 0
  fi

  build_backend
  build_frontend

  if [[ "$SKIP_EC2_DEPLOY" != "1" ]]; then
    deploy_backend_to_ec2
  else
    log "Skipping EC2 deploy (--skip-ec2-deploy)"
  fi

  sync_frontend_to_s3
  invalidate_cloudfront
  run_smoke_tests

  if public_url="$(terraform_output public_url 2>/dev/null)"; then
    log "Public URL: ${public_url}"
  fi

  log "deploy-aws.sh complete"
}

main "$@"
