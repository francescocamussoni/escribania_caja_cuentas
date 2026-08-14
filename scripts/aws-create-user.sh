#!/usr/bin/env bash
# Create or reset a production user on EC2 via SSM (no password in argv / send-command).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="${ROOT}/infra"
CONTAINER_NAME="${CONTAINER_NAME:-escribania-api}"
SSM_PREFIX="${SSM_PREFIX:-/escribania/prod}"
RESET=0
USERNAME=""
ROL=""

usage() {
  cat <<'EOF'
Usage: ./scripts/aws-create-user.sh --username NAME --rol escribano|secretaria
       ./scripts/aws-create-user.sh --username NAME --reset

Creates a user (or resets their password) in the production RDS via the API
container on EC2. Prompts for the password locally (hidden). The secret is
stored briefly as an SSM SecureString and deleted afterwards — it is not
passed as --password or left in SSM command history.

Options:
  --username NAME   Login name (1–50 characters)
  --rol ROLE        secretaria or escribano (required unless --reset)
  --reset           Update password of an existing user (invalidates JWTs)
  -h, --help        Show this help

Environment:
  AWS_REGION        Override region (default: terraform output or us-east-1)
  SSM_PREFIX        Parameter prefix (default: /escribania/prod)
  CONTAINER_NAME    Docker name on EC2 (default: escribania-api)

Prerequisites:
  - AWS CLI + credentials that can PutParameter/DeleteParameter and SSM Run Command
  - terraform state with ec2_instance_id
  - API container running on EC2 (uses modules already in the image; no extra deploy)
EOF
}

log() {
  echo "==> $*"
}

fail() {
  echo "ERROR: $*" >&2
  exit 1
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

prompt_password() {
  local first second
  read -r -s -p "Contraseña: " first
  echo >&2
  read -r -s -p "Confirmar contraseña: " second
  echo >&2
  [[ -n "${first}" ]] || fail "La contraseña no puede estar vacía"
  [[ "${first}" == "${second}" ]] || fail "Las contraseñas no coinciden"
  printf '%s' "${first}"
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
        aws ssm get-command-invocation \
          --command-id "${command_id}" \
          --instance-id "${instance_id}" \
          --query 'StandardOutputContent' \
          --output text
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

while [[ $# -gt 0 ]]; do
  case "$1" in
    --username)
      USERNAME="${2:-}"
      shift 2
      ;;
    --rol)
      ROL="${2:-}"
      shift 2
      ;;
    --reset)
      RESET=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown option: $1"
      ;;
  esac
done

[[ -n "${USERNAME}" ]] || fail "--username is required"
if [[ "${RESET}" -eq 0 ]]; then
  [[ -n "${ROL}" ]] || fail "--rol is required when creating a user"
  [[ "${ROL}" == "escribano" || "${ROL}" == "secretaria" ]] \
    || fail "--rol must be escribano or secretaria"
fi

command -v aws >/dev/null 2>&1 || fail "aws CLI is required"
command -v jq >/dev/null 2>&1 || fail "jq is required"

region="$(resolve_aws_region)"
export AWS_REGION="${region}"
export AWS_DEFAULT_REGION="${region}"

instance_id="$(terraform_output ec2_instance_id)" \
  || fail "ec2_instance_id not found — run terraform apply first"

password="$(prompt_password)"
param_name="${SSM_PREFIX}/ops/create-user-$(date +%s)-${RANDOM}"

cleanup_param() {
  aws ssm delete-parameter --name "${param_name}" >/dev/null 2>&1 || true
}
trap cleanup_param EXIT

log "Storing password temporarily in SSM (${param_name})"
aws ssm put-parameter \
  --name "${param_name}" \
  --type SecureString \
  --value "${password}" \
  --overwrite >/dev/null
password=""

user_q="$(printf '%q' "${USERNAME}")"
if [[ "${RESET}" -eq 1 ]]; then
  mode="reset"
  rol_q="''"
  log "Resetting password for ${USERNAME} on ${instance_id}"
else
  mode="create"
  rol_q="$(printf '%q' "${ROL}")"
  log "Creating user ${USERNAME} (${ROL}) on ${instance_id}"
fi

remote_py="${ROOT}/scripts/aws_create_user_remote.py"
[[ -f "${remote_py}" ]] || fail "Missing ${remote_py}"
remote_b64="$(base64 < "${remote_py}" | tr -d '\n')"

# Inline payload uses modules already in the running image (no app.create_user required).
# Password stays in SSM SecureString; send-command only carries the parameter name.
remote_script="$(cat <<EOF
set -euo pipefail
echo '${remote_b64}' | base64 -d > /tmp/ops_create_user.py
PASSWORD=\$(aws ssm get-parameter --name '${param_name}' --with-decryption --query Parameter.Value --output text --region '${region}')
docker exec \\
  -e CREATE_USER_PASSWORD="\$PASSWORD" \\
  -e CREATE_USER_USERNAME=${user_q} \\
  -e CREATE_USER_MODE=${mode} \\
  -e CREATE_USER_ROL=${rol_q} \\
  -i ${CONTAINER_NAME} python - < /tmp/ops_create_user.py
rm -f /tmp/ops_create_user.py
unset PASSWORD
EOF
)"

command_id="$(aws ssm send-command \
  --instance-ids "${instance_id}" \
  --document-name "AWS-RunShellScript" \
  --comment "aws-create-user.sh" \
  --parameters "$(jq -n --arg script "${remote_script}" '{commands: [$script]}')" \
  --query "Command.CommandId" \
  --output text)"

if ! wait_for_ssm_command "${command_id}" "${instance_id}"; then
  fail "User operation failed — see SSM output above"
fi

log "Done. Give the password to the user out of band; they can change it from the login screen."
