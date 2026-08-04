#!/usr/bin/env bash
# Validate Terraform layout against specs/002-aws-deploy/contracts/infrastructure.md
# (INF-001–INF-010, excluded resources, required outputs). Exit 0 if compliant.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="${ROOT}/infra"
CONTRACT="${ROOT}/specs/002-aws-deploy/contracts/infrastructure.md"

FOUND=0

fail() {
  echo "FAIL: $1" >&2
  FOUND=1
}

pass() {
  echo "OK: $1"
}

require_in_file() {
  local file="$1"
  local pattern="$2"
  local label="$3"
  if ! grep -qE "${pattern}" "${file}"; then
    fail "${label} — pattern not found in ${file#${ROOT}/}"
    return 1
  fi
  pass "${label}"
}

echo "Validating infra against ${CONTRACT#${ROOT}/}"
echo

# --- Excluded resources (amend: lean architecture) ---
FORBIDDEN=(
  'resource "aws_lb"'
  'resource "aws_nat_gateway"'
  'resource "aws_ecs_cluster"'
  'resource "aws_ecs_service"'
  'resource "aws_ecr_repository"'
  'resource "aws_secretsmanager_secret"'
)

while IFS= read -r -d '' file; do
  for pattern in "${FORBIDDEN[@]}"; do
    if grep -qF "${pattern}" "${file}"; then
      fail "Excluded resource ${pattern} found in ${file#${ROOT}/}"
    fi
  done
done < <(find "${INFRA_DIR}" -name '*.tf' -not -path '*/.terraform/*' -print0)

if [[ "${FOUND}" -eq 0 ]]; then
  pass "No excluded resources (ALB, NAT, ECS, ECR, Secrets Manager)"
fi

# --- Required modules (INF-001–INF-010) ---
require_in_file "${INFRA_DIR}/main.tf" 'module "vpc"' 'INF-001 module vpc'
require_in_file "${INFRA_DIR}/modules/vpc/main.tf" 'resource "aws_vpc"' 'INF-001 aws_vpc'
require_in_file "${INFRA_DIR}/modules/vpc/main.tf" 'resource "aws_subnet" "public"' 'INF-002 public subnets'
require_in_file "${INFRA_DIR}/modules/vpc/main.tf" 'resource "aws_subnet" "private"' 'INF-002 private subnets'
require_in_file "${INFRA_DIR}/modules/rds/main.tf" 'resource "aws_db_instance"' 'INF-003 aws_db_instance'
require_in_file "${INFRA_DIR}/modules/rds/main.tf" 'storage_encrypted = true' 'INF-003 RDS encryption at rest'
require_in_file "${INFRA_DIR}/modules/rds/main.tf" 'publicly_accessible    = false' 'INF-003 RDS not public'
require_in_file "${INFRA_DIR}/modules/compute/main.tf" 'resource "aws_instance"' 'INF-004 EC2 API host'
require_in_file "${INFRA_DIR}/modules/vpc/main.tf" 'resource "aws_security_group" "api"' 'INF-005 API security group'
require_in_file "${INFRA_DIR}/modules/vpc/main.tf" 'prefix_list_ids' 'INF-005 CloudFront prefix list on API SG'
require_in_file "${INFRA_DIR}/modules/compute/main.tf" 'resource "aws_iam_instance_profile"' 'INF-006 IAM instance profile'
require_in_file "${INFRA_DIR}/modules/compute/main.tf" 'ssm:GetParameter' 'INF-006 SSM read on instance role'
require_in_file "${INFRA_DIR}/modules/frontend/main.tf" 'resource "aws_s3_bucket"' 'INF-007 frontend S3 bucket'
require_in_file "${INFRA_DIR}/modules/frontend/main.tf" 'block_public_acls' 'INF-007 S3 block public access'
require_in_file "${INFRA_DIR}/modules/frontend/main.tf" 'resource "aws_cloudfront_distribution"' 'INF-008 CloudFront distribution'
require_in_file "${INFRA_DIR}/modules/frontend/main.tf" 'path_pattern' 'INF-008 API path_pattern cache behavior'
require_in_file "${INFRA_DIR}/modules/frontend/variables.tf" 'default     = "/api/\*"' 'INF-008 default /api/* path pattern'
require_in_file "${INFRA_DIR}/modules/secrets/main.tf" 'resource "aws_ssm_parameter" "jwt_secret"' 'INF-009 SSM jwt'
require_in_file "${INFRA_DIR}/modules/secrets/main.tf" 'resource "aws_ssm_parameter" "db_password"' 'INF-009 SSM db password'
require_in_file "${INFRA_DIR}/modules/secrets/main.tf" 'resource "aws_ssm_parameter" "admin_username"' 'INF-009 SSM admin username'
require_in_file "${INFRA_DIR}/modules/secrets/main.tf" 'resource "aws_ssm_parameter" "admin_password"' 'INF-009 SSM admin password'
require_in_file "${INFRA_DIR}/modules/secrets/main.tf" 'type        = "SecureString"' 'INF-009 SecureString parameters'
require_in_file "${INFRA_DIR}/modules/vpc/main.tf" 'resource "aws_security_group" "rds"' 'INF-010 RDS security group'

# --- Required outputs ---
require_in_file "${INFRA_DIR}/outputs.tf" 'output "public_url"' 'Output public_url'
require_in_file "${INFRA_DIR}/outputs.tf" 'output "ec2_public_dns"' 'Output ec2_public_dns'
require_in_file "${INFRA_DIR}/outputs.tf" 'output "rds_endpoint"' 'Output rds_endpoint'

# --- Prohibited outputs (no secret values) ---
if grep -E 'output "(jwt_secret|admin_password|database_url)"' "${INFRA_DIR}/outputs.tf" \
  | grep -qv 'ssm_parameter_names\|parameter_name'; then
  fail "Prohibited secret outputs in outputs.tf"
else
  pass "No prohibited secret value outputs"
fi

if grep -q 'JWT_SECRET\|ADMIN_PASSWORD' "${INFRA_DIR}/outputs.tf" 2>/dev/null; then
  if ! grep 'JWT_SECRET\|ADMIN_PASSWORD' "${INFRA_DIR}/outputs.tf" | grep -q 'parameter_name\|ssm_parameter'; then
    fail "outputs.tf may expose JWT_SECRET or ADMIN_PASSWORD values"
  fi
fi

# --- Common tags ---
require_in_file "${INFRA_DIR}/main.tf" 'ManagedBy' 'Required tags in provider default_tags'

echo
if [[ "${FOUND}" -eq 0 ]]; then
  echo "Infrastructure contract validation passed (INF-001–INF-010)."
  exit 0
fi

echo "Infrastructure contract validation failed."
exit 1
