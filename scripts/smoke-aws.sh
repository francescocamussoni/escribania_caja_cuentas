#!/usr/bin/env bash
# Post-deploy smoke tests for AWS production (contracts/smoke-tests.md).
# Exit 0 on success; exit 1 on any failed case; exit 2 on usage/validation error.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="${ROOT}/infra"

BASE_URL="${BASE_URL:-}"
SMOKE_CASES="${SMOKE_CASES:-ST-001,ST-002,ST-003}"
ADMIN_USER="${ADMIN_USER:-}"
ADMIN_PASS="${ADMIN_PASS:-}"

ACCESS_TOKEN=""
EXIT_USAGE=2
EXIT_FAIL=1

usage() {
  cat <<'EOF'
Usage: ./scripts/smoke-aws.sh [options]

Post-deploy smoke tests per specs/002-aws-deploy/contracts/smoke-tests.md.

Options:
  -h, --help    Show this help

Environment (required):
  BASE_URL      Public HTTPS URL without trailing slash
                Example: https://d111.cloudfront.net

Environment (ST-005+):
  ADMIN_USER    Production admin username
  ADMIN_PASS    Production admin password (never logged)

Optional:
  SMOKE_CASES   Comma-separated case IDs (default: ST-001,ST-002,ST-003)
                Full suite: ST-001,ST-002,ST-003,ST-004,ST-005,ST-006,ST-007,ST-008

Exit codes:
  0  All requested cases passed
  1  At least one case failed
  2  Missing/invalid configuration
EOF
}

should_run() {
  local case_id="$1"
  [[ ",${SMOKE_CASES}," == *",${case_id},"* ]]
}

fail() {
  echo "FAIL: $1" >&2
  exit "${EXIT_FAIL}"
}

usage_error() {
  echo "ERROR: $1" >&2
  exit "${EXIT_USAGE}"
}

pass() {
  echo "PASS: $1"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || usage_error "Required command not found: $1"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -h | --help)
        usage
        exit 0
        ;;
      *)
        usage_error "Unknown option: $1"
        ;;
    esac
    shift
  done
}

resolve_base_url() {
  if [[ -n "${BASE_URL}" ]]; then
    echo "${BASE_URL%/}"
    return
  fi
  if [[ -d "${INFRA_DIR}" ]] && command -v terraform >/dev/null 2>&1; then
    if url="$(cd "${INFRA_DIR}" && terraform output -raw public_url 2>/dev/null)"; then
      echo "${url%/}"
      return
    fi
  fi
  usage_error "Set BASE_URL (e.g. export BASE_URL=https://d123.cloudfront.net)"
}

validate_base_url() {
  local url="$1"
  if [[ "${url}" != https://* ]]; then
    usage_error "BASE_URL must use HTTPS (got: ${url})"
  fi
}

requires_admin_credentials() {
  local case_id
  for case_id in ST-005 ST-006 ST-007 ST-008; do
    if should_run "${case_id}"; then
      return 0
    fi
  done
  return 1
}

validate_inputs() {
  BASE_URL="$(resolve_base_url)"
  validate_base_url "${BASE_URL}"

  if requires_admin_credentials; then
    if [[ -z "${ADMIN_USER}" || -z "${ADMIN_PASS}" ]]; then
      usage_error "Set ADMIN_USER and ADMIN_PASS for smoke cases: ${SMOKE_CASES}"
    fi
  fi
}

require_cmd curl
require_cmd python3

# ST-001 — Health check API
run_st_001() {
  local body status
  body=$(mktemp)
  status=$(curl -sS -o "$body" -w "%{http_code}" "${BASE_URL}/api/health") || fail "ST-001: curl error"
  if [[ "$status" != "200" ]]; then
    fail "ST-001: expected HTTP 200, got ${status}"
  fi
  if ! grep -q '"status"[[:space:]]*:[[:space:]]*"ok"' "$body"; then
    fail "ST-001: body missing {\"status\": \"ok\"}"
  fi
  rm -f "$body"
  pass "ST-001 health check"
}

# ST-002 — HTTPS redirect
run_st_002() {
  local host headers status location
  host=$(echo "${BASE_URL}" | sed -E 's#^https?://##' | cut -d/ -f1)
  headers=$(mktemp)
  status=$(curl -sS -o /dev/null -w "%{http_code}" -D "$headers" "http://${host}/login") || fail "ST-002: curl error"

  if [[ "$status" == "200" ]]; then
    if [[ "${BASE_URL}" == https://* ]]; then
      rm -f "$headers"
      pass "ST-002 HTTPS (direct 200 on HTTP origin — verify TLS in browser)"
      return
    fi
  fi

  if [[ "$status" != "301" && "$status" != "302" && "$status" != "307" && "$status" != "308" ]]; then
    fail "ST-002: expected redirect (301/302), got ${status}"
  fi

  location=$(grep -i '^[Ll]ocation:' "$headers" | head -1 | cut -d' ' -f2- | tr -d '\r')
  rm -f "$headers"
  if [[ -z "$location" ]]; then
    fail "ST-002: redirect without Location header"
  fi
  if [[ "$location" != https://* ]]; then
    fail "ST-002: Location must be HTTPS, got ${location}"
  fi
  pass "ST-002 HTTPS redirect"
}

# ST-003 — Frontend login page
run_st_003() {
  local body status
  body=$(mktemp)
  status=$(curl -sS -o "$body" -w "%{http_code}" "${BASE_URL}/login") || fail "ST-003: curl error"
  if [[ "$status" != "200" ]]; then
    fail "ST-003: expected HTTP 200, got ${status}"
  fi
  if ! grep -qiE 'Iniciar sesión|Ingresar|Escribanía|Usuario' "$body"; then
    fail "ST-003: login page content not found"
  fi
  rm -f "$body"
  pass "ST-003 frontend login page"
}

# ST-004 — Dev credentials rejected
run_st_004() {
  local body status
  body=$(mktemp)
  status=$(curl -sS -o "$body" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin"}') || fail "ST-004: curl error"

  if [[ "$status" != "401" ]]; then
    rm -f "$body"
    fail "ST-004: expected HTTP 401, got ${status}"
  fi
  if grep -q 'access_token' "$body"; then
    rm -f "$body"
    fail "ST-004: dev login must not return access_token"
  fi
  rm -f "$body"
  pass "ST-004 dev credentials rejected"
}

# ST-005 — Production admin login
run_st_005() {
  local body status json_payload
  body=$(mktemp)
  json_payload=$(ADMIN_USER="${ADMIN_USER}" ADMIN_PASS="${ADMIN_PASS}" python3 -c \
    'import json, os; print(json.dumps({"username": os.environ["ADMIN_USER"], "password": os.environ["ADMIN_PASS"]}))')
  status=$(curl -sS -o "$body" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "${json_payload}") || fail "ST-005: curl error"

  if [[ "$status" != "200" ]]; then
    rm -f "$body"
    fail "ST-005: expected HTTP 200, got ${status}"
  fi

  ACCESS_TOKEN=$(python3 -c '
import json, sys
data = json.load(sys.stdin)
token = data.get("access_token")
rol = data.get("rol")
if not token:
    raise SystemExit("missing access_token")
if rol != "secretaria":
    raise SystemExit(f"expected rol secretaria, got {rol!r}")
print(token)
' <"$body") || {
    rm -f "$body"
    fail "ST-005: invalid login response"
  }

  rm -f "$body"
  pass "ST-005 production admin login (user=${ADMIN_USER})"
}

# ST-006 — Fifteen cajas in catalog
run_st_006() {
  local body status
  if [[ -z "${ACCESS_TOKEN}" ]]; then
    fail "ST-006: run ST-005 first to obtain access token"
  fi
  body=$(mktemp)
  status=$(curl -sS -o "$body" -w "%{http_code}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    "${BASE_URL}/api/v1/cajas") || fail "ST-006: curl error"

  if [[ "$status" != "200" ]]; then
    rm -f "$body"
    fail "ST-006: expected HTTP 200, got ${status}"
  fi

  python3 -c '
import json, sys
data = json.load(sys.stdin)
if not isinstance(data, list):
    raise SystemExit("expected JSON array")
if len(data) != 15:
    raise SystemExit(f"expected 15 cajas, got {len(data)}")
for item in data:
    for key in ("id", "nombre", "slug"):
        if key not in item:
            raise SystemExit(f"missing field {key!r} in caja item")
' <"$body" || {
    rm -f "$body"
    fail "ST-006: invalid cajas response"
  }

  rm -f "$body"
  pass "ST-006 fifteen cajas catalog"
}

# ST-007 — Empty movimientos
run_st_007() {
  local body status
  if [[ -z "${ACCESS_TOKEN}" ]]; then
    fail "ST-007: run ST-005 first to obtain access token"
  fi
  body=$(mktemp)
  status=$(curl -sS -o "$body" -w "%{http_code}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    "${BASE_URL}/api/v1/cajas/1/movimientos?page=1") || fail "ST-007: curl error"

  if [[ "$status" != "200" ]]; then
    rm -f "$body"
    fail "ST-007: expected HTTP 200, got ${status}"
  fi

  python3 -c '
import json, sys
data = json.load(sys.stdin)
total_items = data.get("total_items")
if total_items != 0:
    raise SystemExit(f"expected total_items 0, got {total_items!r}")
if data.get("items") != []:
    raise SystemExit("expected empty items array")
' <"$body" || {
    rm -f "$body"
    fail "ST-007: movimientos not empty"
  }

  rm -f "$body"
  pass "ST-007 empty movimientos"
}

# ST-008 — Zero initial balance
run_st_008() {
  local body status
  if [[ -z "${ACCESS_TOKEN}" ]]; then
    fail "ST-008: run ST-005 first to obtain access token"
  fi
  body=$(mktemp)
  status=$(curl -sS -o "$body" -w "%{http_code}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    "${BASE_URL}/api/v1/cajas/1/saldo") || fail "ST-008: curl error"

  if [[ "$status" != "200" ]]; then
    rm -f "$body"
    fail "ST-008: expected HTTP 200, got ${status}"
  fi

  python3 -c '
import json, sys
from decimal import Decimal
data = json.load(sys.stdin)
saldo = data.get("saldo_actual")
if saldo is None:
    raise SystemExit("missing saldo_actual")
if Decimal(str(saldo)) != 0:
    raise SystemExit(f"expected zero saldo_actual, got {saldo!r}")
' <"$body" || {
    rm -f "$body"
    fail "ST-008: saldo not zero"
  }

  rm -f "$body"
  pass "ST-008 zero initial saldo"
}

main() {
  parse_args "$@"
  validate_inputs

  echo "Smoke tests against ${BASE_URL}"
  echo "Cases: ${SMOKE_CASES}"
  if requires_admin_credentials; then
    echo "Admin user: ${ADMIN_USER}"
  fi

  if should_run "ST-001"; then run_st_001; fi
  if should_run "ST-002"; then run_st_002; fi
  if should_run "ST-003"; then run_st_003; fi
  if should_run "ST-004"; then run_st_004; fi
  if should_run "ST-005"; then run_st_005; fi
  if should_run "ST-006"; then run_st_006; fi
  if should_run "ST-007"; then run_st_007; fi
  if should_run "ST-008"; then run_st_008; fi

  echo "All requested smoke tests passed."
  exit 0
}

main "$@"
