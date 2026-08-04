locals {
  base_path = trimsuffix(var.parameter_path_prefix, "/")
}

resource "aws_ssm_parameter" "jwt_secret" {
  name        = "${local.base_path}/jwt"
  description = "JWT signing secret (${var.name_prefix})"
  type        = "SecureString"
  value       = var.jwt_secret
  key_id      = "alias/aws/ssm"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-jwt-secret"
  })
}

resource "aws_ssm_parameter" "db_password" {
  name        = "${local.base_path}/db"
  description = "RDS master password (${var.name_prefix})"
  type        = "SecureString"
  value       = var.db_password
  key_id      = "alias/aws/ssm"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-db-password"
  })
}

resource "aws_ssm_parameter" "admin_username" {
  name        = "${local.base_path}/admin_username"
  description = "Bootstrap admin username (${var.name_prefix})"
  type        = "SecureString"
  value       = var.admin_username
  key_id      = "alias/aws/ssm"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-admin-username"
  })
}

resource "aws_ssm_parameter" "admin_password" {
  name        = "${local.base_path}/admin_password"
  description = "Bootstrap admin password (${var.name_prefix})"
  type        = "SecureString"
  value       = var.admin_password
  key_id      = "alias/aws/ssm"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-admin-password"
  })
}
