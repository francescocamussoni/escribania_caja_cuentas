output "aws_region" {
  description = "AWS region where resources are deployed."
  value       = var.aws_region
}

output "name_prefix" {
  description = "Resource name prefix for this stack."
  value       = var.name_prefix
}

output "vpc_id" {
  description = "VPC identifier."
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs for EC2."
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "Private subnet IDs for RDS."
  value       = module.vpc.private_subnet_ids
}

output "api_security_group_id" {
  description = "Security group ID for API EC2."
  value       = module.vpc.api_security_group_id
}

output "rds_security_group_id" {
  description = "Security group ID for RDS."
  value       = module.vpc.rds_security_group_id
}

output "rds_endpoint" {
  description = "RDS hostname (operators only; use SSM for credentials)."
  value       = module.rds.address
  sensitive   = true
}

output "rds_port" {
  description = "RDS port."
  value       = module.rds.port
}

output "rds_database_name" {
  description = "RDS logical database name."
  value       = module.rds.database_name
}

output "ssm_parameter_names" {
  description = "SSM Parameter Store names for production secrets (no values)."
  value = {
    jwt            = module.secrets.jwt_secret_parameter_name
    db_password    = module.secrets.db_password_parameter_name
    admin_username = module.secrets.admin_username_parameter_name
    admin_password = module.secrets.admin_password_parameter_name
    cors_origins   = module.frontend.cors_origins_parameter_name
  }
}

output "ec2_instance_id" {
  description = "EC2 instance ID for the API host."
  value       = module.compute.instance_id
}

output "ec2_public_dns" {
  description = "EC2 public DNS (diagnostics; API via CloudFront in production)."
  value       = module.compute.public_dns
}

output "api_health_check_path" {
  description = "API health check path on the backend container."
  value       = module.compute.health_check_path
}

output "api_health_check_url" {
  description = "Direct EC2 health check URL (operators only)."
  value       = module.compute.health_check_url
}

output "frontend_bucket_name" {
  description = "S3 bucket for frontend static assets (deploy sync)."
  value       = module.frontend.bucket_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (cache invalidation on deploy)."
  value       = module.frontend.cloudfront_distribution_id
}

output "container_environment" {
  description = "ENVIRONMENT value for the API container (production bootstrap gate)."
  value       = module.compute.container_environment
}

output "bootstrap_ssm_parameter_names" {
  description = "SSM parameter names for admin bootstrap (no secret values)."
  value       = module.compute.bootstrap_ssm_parameter_names
}

output "public_url" {
  description = "Public HTTPS URL for users (CloudFront distribution)."
  value       = module.frontend.public_url
}
