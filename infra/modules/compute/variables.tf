variable "name_prefix" {
  description = "Prefix for EC2 and IAM resource names."
  type        = string
}

variable "subnet_id" {
  description = "Public subnet ID for the API instance."
  type        = string
}

variable "security_group_ids" {
  description = "Security groups for the API instance (CloudFront → :8000)."
  type        = list(string)
}

variable "instance_type" {
  description = "EC2 instance type."
  type        = string
  default     = "t4g.micro"
}

variable "root_volume_gb" {
  description = "Root EBS volume size in GB."
  type        = number
  default     = 8
}

variable "ssm_parameter_path_prefix" {
  description = "SSM path prefix for IAM policy scoping."
  type        = string
  default     = "/escribania/prod"
}

variable "rds_address" {
  description = "RDS hostname for DATABASE_URL assembly."
  type        = string
  sensitive   = true
}

variable "rds_port" {
  description = "RDS port."
  type        = number
  default     = 5432
}

variable "rds_database_name" {
  description = "RDS database name."
  type        = string
}

variable "rds_master_username" {
  description = "RDS master username."
  type        = string
}

variable "ssm_jwt_parameter_name" {
  description = "SSM parameter name for JWT secret."
  type        = string
}

variable "ssm_db_password_parameter_name" {
  description = "SSM parameter name for RDS master password."
  type        = string
}

variable "ssm_admin_username_parameter_name" {
  description = "SSM parameter name for bootstrap admin username."
  type        = string
}

variable "ssm_admin_password_parameter_name" {
  description = "SSM parameter name for bootstrap admin password."
  type        = string
}

variable "cors_origins" {
  description = "Optional static CORS origins (comma-separated). Production uses ssm_cors_origins_parameter_name (CloudFront URL from SSM)."
  type        = string
  default     = ""
}

variable "ssm_cors_origins_parameter_name" {
  description = "SSM Parameter Store name for CORS_ORIGINS (CloudFront HTTPS URL). Wired from frontend in T025."
  type        = string
  default     = ""
}

variable "health_check_path" {
  description = "API health check path exposed on port 8000."
  type        = string
  default     = "/health"
}

variable "deploy_artifact_prefix" {
  description = "S3 key prefix for deploy artifacts (deploy-aws.sh staging)."
  type        = string
  default     = "_deploy"
}

variable "user_data" {
  description = "Optional override for EC2 user_data (defaults to bootstrap template)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "tags" {
  description = "Tags applied to EC2 and IAM resources."
  type        = map(string)
  default     = {}
}
