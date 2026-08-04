#!/bin/bash
# Fetch production secrets from SSM and write /opt/escribania/.env
set -euo pipefail

INSTALL_DIR="/opt/escribania"
CONFIG_FILE="${INSTALL_DIR}/config.env"
ENV_FILE="${INSTALL_DIR}/.env"

if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "Missing ${CONFIG_FILE}" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "${CONFIG_FILE}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command not found: $1" >&2
    exit 1
  }
}

require_cmd aws

ssm_get() {
  local name="$1"
  aws ssm get-parameter \
    --region "${AWS_REGION}" \
    --name "${name}" \
    --with-decryption \
    --query "Parameter.Value" \
    --output text
}

ssm_get_with_retry() {
  local name="$1"
  local max_attempts="${2:-30}"
  local sleep_seconds="${3:-10}"
  local attempt=1
  local value=""

  while [[ "${attempt}" -le "${max_attempts}" ]]; do
    if value="$(ssm_get "${name}" 2>/dev/null)"; then
      echo "${value}"
      return 0
    fi
    echo "Waiting for SSM parameter ${name} (attempt ${attempt}/${max_attempts})..." >&2
    sleep "${sleep_seconds}"
    attempt=$((attempt + 1))
  done

  echo "Failed to read SSM parameter ${name} after ${max_attempts} attempts" >&2
  return 1
}

urlencode() {
  python3 -c 'import urllib.parse, sys; print(urllib.parse.quote_plus(sys.argv[1]))' "$1"
}

JWT_SECRET="$(ssm_get "${SSM_JWT_PARAM}")"
DB_PASSWORD="$(ssm_get "${SSM_DB_PASSWORD_PARAM}")"
ADMIN_USERNAME="$(ssm_get "${SSM_ADMIN_USERNAME_PARAM}")"
ADMIN_PASSWORD="$(ssm_get "${SSM_ADMIN_PASSWORD_PARAM}")"

if [[ -n "${SSM_CORS_PARAM:-}" ]]; then
  CORS_ORIGINS="$(ssm_get_with_retry "${SSM_CORS_PARAM}" 30 10)"
elif [[ -z "${CORS_ORIGINS:-}" ]]; then
  echo "WARN: CORS_ORIGINS not set (no SSM param and no static config)" >&2
  CORS_ORIGINS=""
fi

DB_PASSWORD_ENCODED="$(urlencode "${DB_PASSWORD}")"
DATABASE_URL="postgresql://${RDS_USER}:${DB_PASSWORD_ENCODED}@${RDS_HOST}:${RDS_PORT}/${RDS_DB}"

APP_ENV="${APP_ENVIRONMENT:-production}"

umask 077
cat > "${ENV_FILE}" <<EOF
ENVIRONMENT=${APP_ENV}
DATABASE_URL=${DATABASE_URL}
JWT_SECRET=${JWT_SECRET}
JWT_EXPIRE_HOURS=8
ADMIN_USERNAME=${ADMIN_USERNAME}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
CORS_ORIGINS=${CORS_ORIGINS}
EOF

chmod 600 "${ENV_FILE}"
