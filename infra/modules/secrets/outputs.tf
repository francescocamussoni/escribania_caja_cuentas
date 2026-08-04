output "jwt_secret_parameter_name" {
  description = "SSM parameter name for JWT secret."
  value       = aws_ssm_parameter.jwt_secret.name
}

output "db_password_parameter_name" {
  description = "SSM parameter name for RDS master password."
  value       = aws_ssm_parameter.db_password.name
}

output "admin_username_parameter_name" {
  description = "SSM parameter name for bootstrap admin username."
  value       = aws_ssm_parameter.admin_username.name
}

output "admin_password_parameter_name" {
  description = "SSM parameter name for bootstrap admin password."
  value       = aws_ssm_parameter.admin_password.name
}

output "parameter_arns" {
  description = "ARNs of SSM parameters (no secret values)."
  value = {
    jwt            = aws_ssm_parameter.jwt_secret.arn
    db_password    = aws_ssm_parameter.db_password.arn
    admin_username = aws_ssm_parameter.admin_username.arn
    admin_password = aws_ssm_parameter.admin_password.arn
  }
}
