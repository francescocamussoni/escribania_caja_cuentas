#!/usr/bin/env bash
# Automated items from specs/002-aws-deploy/quickstart.md §13 (T042).
# Runs local/static checks and optional live smoke tests when BASE_URL is set.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="${ROOT}/infra"
GITIGNORE="${ROOT}/.gitignore"

FOUND=0
RAN_SMOKE=0

fail() {
  echo "FAIL: $1" >&2
  FOUND=1
}

pass() {
  echo "OK: $1"
}

echo "=== Pre-production checklist (quickstart §13) ==="
echo

# 1. prod.tfvars in .gitignore
if grep -q 'infra/environments/prod.tfvars' "${GITIGNORE}"; then
  pass "prod.tfvars listed in .gitignore"
else
  fail "prod.tfvars not in .gitignore"
fi

# 2. Secrets in SSM, not repo
"${ROOT}/scripts/check-secrets.sh" || FOUND=1

# 3. RDS: Single-AZ, backups >= 7 days, encryption
if grep -q 'rds_multi_az              = false' "${INFRA_DIR}/environments/prod.tfvars.example"; then
  pass "prod.tfvars.example: rds_multi_az = false"
else
  fail "prod.tfvars.example missing rds_multi_az = false"
fi

if grep -q 'rds_backup_retention_days = 7' "${INFRA_DIR}/environments/prod.tfvars.example"; then
  pass "prod.tfvars.example: backup retention 7 days"
else
  fail "prod.tfvars.example missing rds_backup_retention_days = 7"
fi

if grep -q 'storage_encrypted = true' "${INFRA_DIR}/modules/rds/main.tf"; then
  pass "RDS module: storage_encrypted = true"
else
  fail "RDS module missing storage_encrypted"
fi

# 4. HTTPS on CloudFront
if grep -q 'https://' "${INFRA_DIR}/modules/frontend/outputs.tf" 2>/dev/null \
  || grep -q 'https://\${' "${INFRA_DIR}/modules/frontend/main.tf"; then
  pass "Frontend module exposes HTTPS public URL"
else
  fail "CloudFront HTTPS URL not configured in frontend module"
fi

# Outputs security (T043)
"${ROOT}/scripts/validate-outputs-security.sh" || FOUND=1

# 5–8. Smoke tests (live deploy required)
BASE_URL="${BASE_URL:-}"
if [[ -z "${BASE_URL}" ]] && [[ -d "${INFRA_DIR}/.terraform" || -f "${INFRA_DIR}/terraform.tfstate" ]]; then
  if command -v terraform >/dev/null 2>&1; then
    BASE_URL="$(cd "${INFRA_DIR}" && terraform output -raw public_url 2>/dev/null || true)"
  fi
fi

if [[ -n "${BASE_URL}" ]]; then
  if [[ "${BASE_URL}" != https://* ]]; then
    fail "BASE_URL must use HTTPS: ${BASE_URL}"
  else
    pass "Public URL uses HTTPS: ${BASE_URL}"
  fi

  export BASE_URL
  export SMOKE_CASES="${SMOKE_CASES:-ST-001,ST-002,ST-003,ST-004,ST-005,ST-006,ST-007,ST-008}"

  if [[ -n "${ADMIN_USER:-}" && -n "${ADMIN_PASS:-}" ]]; then
    echo
    echo "Running smoke tests ${SMOKE_CASES} against ${BASE_URL}..."
    if "${ROOT}/scripts/smoke-aws.sh"; then
      pass "Smoke tests ST-001–ST-008 passed"
      RAN_SMOKE=1
    else
      fail "Smoke tests failed (see output above)"
    fi
  else
    echo
    echo "SKIP: Full smoke (ST-004–ST-008) — set ADMIN_USER and ADMIN_PASS to run against live deploy"
    export SMOKE_CASES="ST-001,ST-002,ST-003"
    echo "Running connectivity smoke ${SMOKE_CASES}..."
    if "${ROOT}/scripts/smoke-aws.sh"; then
      pass "Connectivity smoke ST-001–ST-003 passed"
      RAN_SMOKE=1
    else
      fail "Connectivity smoke failed"
    fi
  fi
else
  echo "SKIP: Live smoke tests — no BASE_URL and no terraform output (deploy not detected)"
fi

echo
if [[ "${FOUND}" -eq 0 ]]; then
  echo "Pre-production checklist passed."
  [[ "${RAN_SMOKE}" -eq 1 ]] && echo "Live smoke tests executed against deployed environment."
  exit 0
fi

echo "Pre-production checklist failed — review items above."
exit 1
