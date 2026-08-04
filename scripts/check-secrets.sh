#!/usr/bin/env bash
# Scan repository for hardcoded secrets and committed prod secrets files.
# Exit 0 if clean; exit 1 if potential secrets found.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FOUND=0

SKIP_DIRS=(
  .git
  .terraform
  .cursor
  node_modules
  .venv
  venv
  dist
  htmlcov
  .pytest_cache
  .mypy_cache
  .ruff_cache
)

SAFE_PATH_PATTERNS=(
  'prod\.tfvars\.example'
  'check-secrets\.sh'
  '\.env\.example'
  'load-env-from-ssm\.sh'
  'specs/.*/contracts/'
  'specs/.*/quickstart\.md'
  'specs/.*/research\.md'
)

SAFE_LINE_PATTERNS=(
  'ssm_get'
  'os\.environ'
  'getenv'
  'changeme'
  'your-'
  'example'
  '<openssl'
  'prod-admin'
  '\$\{'
  'quote_plus'
  'SecureString'
  'parameter_path'
)

build_prune_args() {
  local args=()
  for d in "${SKIP_DIRS[@]}"; do
    args+=(--exclude-dir="$d")
  done
  printf '%s\n' "${args[@]}"
}

PRUNE_ARGS=($(build_prune_args))

is_safe_path() {
  local path="$1"
  local pattern
  for pattern in "${SAFE_PATH_PATTERNS[@]}"; do
    if [[ "${path}" =~ ${pattern} ]]; then
      return 0
    fi
  done
  return 1
}

is_safe_line() {
  local line="$1"
  local pattern
  for pattern in "${SAFE_LINE_PATTERNS[@]}"; do
    if [[ "${line}" =~ ${pattern} ]]; then
      return 0
    fi
  done
  return 1
}

filter_matches() {
  local matches="$1"
  local line path
  local filtered=""

  while IFS= read -r line; do
    [[ -z "${line}" ]] && continue
    path="${line%%:*}"
    if is_safe_path "${path}"; then
      continue
    fi
    if is_safe_line "${line}"; then
      continue
    fi
    filtered+="${line}"$'\n'
  done <<< "${matches}"

  printf '%s' "${filtered}"
}

report_match() {
  local label="$1"
  local pattern="$2"
  local matches filtered count

  matches=$(grep -RIn "${PRUNE_ARGS[@]}" -E "$pattern" \
    --include='*.py' --include='*.ts' --include='*.tsx' --include='*.js' \
    --include='*.json' --include='*.yaml' --include='*.yml' --include='*.tf' \
    --include='*.tfvars' --include='*.sh' --include='*.env' --include='*.md' \
    . 2>/dev/null || true)

  filtered="$(filter_matches "${matches}")"
  if [[ -z "${filtered}" ]]; then
    return
  fi

  count=$(printf '%s' "${filtered}" | grep -c '^' || true)
  echo "FAIL: $label"
  printf '%s' "${filtered}" | head -20
  if [[ "${count}" -gt 20 ]]; then
    echo "... (truncated)"
  fi
  echo
  FOUND=1
}

check_committed_secret_files() {
  local tracked_tfvars file

  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if git ls-files --error-unmatch infra/environments/prod.tfvars >/dev/null 2>&1; then
      echo "FAIL: infra/environments/prod.tfvars is tracked by git (must stay gitignored)"
      FOUND=1
    fi

    tracked_tfvars=$(git ls-files 'infra/environments/*.tfvars' 2>/dev/null | grep -v '\.example$' || true)
    if [[ -n "${tracked_tfvars}" ]]; then
      echo "FAIL: committed tfvars with secrets (only *.tfvars.example allowed):"
      echo "${tracked_tfvars}"
      FOUND=1
    fi
  fi

  if [[ -f infra/environments/prod.tfvars ]]; then
    if git check-ignore -q infra/environments/prod.tfvars 2>/dev/null; then
      : # gitignored — ok for local operator use
    else
      echo "FAIL: infra/environments/prod.tfvars exists and is NOT gitignored"
      FOUND=1
    fi
  fi

  for file in .env infra/environments/prod.tfvars; do
    if [[ -f "${file}" ]] && git ls-files --error-unmatch "${file}" >/dev/null 2>&1; then
      echo "FAIL: ${file} is tracked by git"
      FOUND=1
    fi
  done
}

echo "Scanning $ROOT for hardcoded secrets..."

report_match "Hardcoded JWT or API key assignment" \
  '(JWT_SECRET|API_KEY|SECRET_KEY)\s*=\s*["'"'"'][^"'"'"']{8,}["'"'"']'

report_match "DATABASE_URL with embedded credentials" \
  'postgresql(\+[^:]+)?://[^@\s$]+:[^@\s$]+@'

report_match "Hardcoded password assignment" \
  '(password|passwd|ADMIN_PASSWORD|DB_PASSWORD)\s*=\s*["'"'"'](?!changeme|your-|example|xxx|<)[^"'"'"']{6,}["'"'"']'

report_match "AWS access key pattern" \
  '(AKIA[0-9A-Z]{16}|aws_secret_access_key\s*=\s*["'"'"'][^"'"'"']+["'"'"'])'

report_match "PEM private key block" \
  'BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY'

check_committed_secret_files

if [[ "$FOUND" -eq 0 ]]; then
  echo "OK: No hardcoded secrets detected."
  exit 0
fi

echo "Review findings above. Do not commit real secrets."
exit 1
