#!/usr/bin/env bash
# T043: Verify infra/outputs.tf does not expose secret values (constitution IV).
# Exit 0 if compliant; exit 1 if prohibited outputs or value leaks found.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUTS="${ROOT}/infra/outputs.tf"

FOUND=0

fail() {
  echo "FAIL: $1" >&2
  FOUND=1
}

pass() {
  echo "OK: $1"
}

echo "Auditing ${OUTPUTS#${ROOT}/} for secret exposure..."

# Prohibited output names that must never carry secret values
PROHIBITED_NAMES=(
  jwt_secret
  admin_password
  database_url
  db_password
)

for name in "${PROHIBITED_NAMES[@]}"; do
  if grep -qE "output \"${name}\"" "${OUTPUTS}"; then
    fail "Prohibited output \"${name}\" defined — use *_parameter_name only"
  else
    pass "No output \"${name}\""
  fi
done

# ssm_parameter_names must reference names only, not values
if grep -qE 'output "ssm_parameter_names"' "${OUTPUTS}"; then
  if grep -A20 'output "ssm_parameter_names"' "${OUTPUTS}" | grep -qE 'value\s*=\s*module\.secrets\.(jwt_secret|db_password|admin_password)\s*$'; then
    fail "ssm_parameter_names may expose raw secret module outputs"
  else
    pass "ssm_parameter_names uses parameter_name references"
  fi
fi

# Sensitive RDS endpoint marked sensitive
if grep -A5 'output "rds_endpoint"' "${OUTPUTS}" | grep -q 'sensitive   = true'; then
  pass "rds_endpoint marked sensitive"
else
  fail "rds_endpoint must be marked sensitive = true"
fi

# No literal secret patterns in output value blocks
if grep -E 'value\s*=' "${OUTPUTS}" | grep -qiE '(JWT_SECRET|ADMIN_PASSWORD|postgresql://)'; then
  fail "outputs.tf value assignment may contain secret literals"
else
  pass "No secret literals in output value assignments"
fi

# public_url must be HTTPS CloudFront URL from module, not raw credentials
if grep -A3 'output "public_url"' "${OUTPUTS}" | grep -q 'module.frontend.public_url'; then
  pass "public_url sourced from frontend module"
else
  fail "public_url must reference module.frontend.public_url"
fi

echo
if [[ "${FOUND}" -eq 0 ]]; then
  echo "Outputs security audit passed (no JWT_SECRET, ADMIN_PASSWORD, or DATABASE_URL values)."
  exit 0
fi

echo "Outputs security audit failed."
exit 1
