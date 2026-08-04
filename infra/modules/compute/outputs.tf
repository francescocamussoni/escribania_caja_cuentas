output "instance_id" {
  description = "EC2 instance ID."
  value       = aws_instance.api.id
}

output "public_ip" {
  description = "Public IPv4 address of the API instance."
  value       = aws_instance.api.public_ip
}

output "public_dns" {
  description = "Public DNS name of the API instance (CloudFront origin in T022)."
  value       = aws_instance.api.public_dns
}

output "iam_role_name" {
  description = "IAM role name attached to the API instance."
  value       = aws_iam_role.api.name
}

output "iam_instance_profile_name" {
  description = "IAM instance profile name."
  value       = aws_iam_instance_profile.api.name
}

output "health_check_path" {
  description = "Configured API health check path."
  value       = var.health_check_path
}

output "health_check_url" {
  description = "Direct EC2 health URL for diagnostics (production traffic via CloudFront)."
  value       = "http://${aws_instance.api.public_dns}:8000${var.health_check_path}"
}

output "container_environment" {
  description = "ENVIRONMENT value written to the API container .env (bootstrap_production gate)."
  value       = local.app_environment
}

output "bootstrap_ssm_parameter_names" {
  description = "SSM Parameter Store names for admin bootstrap credentials (values not exposed)."
  value = {
    admin_username = var.ssm_admin_username_parameter_name
    admin_password = var.ssm_admin_password_parameter_name
  }
}
