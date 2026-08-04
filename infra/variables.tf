variable "aws_region" {
  description = "AWS region for all resources (FR-014)."
  type        = string
  default     = "us-east-1"

  validation {
    condition     = var.aws_region == "us-east-1"
    error_message = "Production must deploy to us-east-1 per spec FR-014."
  }
}

variable "project_name" {
  description = "Project identifier used in resource names and tags."
  type        = string
  default     = "escribania-cajas"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "production"
}

variable "feature" {
  description = "Spec-Kitti feature id for tagging."
  type        = string
  default     = "002-aws-deploy"
}

variable "name_prefix" {
  description = "Prefix for AWS resource names (e.g. escribania-prod)."
  type        = string
  default     = "escribania-prod"
}

# --- Network (wired in T011) ---

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

# --- Compute (wired in T017) ---

variable "ec2_instance_type" {
  description = "EC2 instance type for the API Docker host."
  type        = string
  default     = "t4g.micro"
}

variable "ec2_root_volume_gb" {
  description = "Root EBS volume size in GB for the API instance."
  type        = number
  default     = 8
}

# --- RDS (wired in T013) ---

variable "rds_instance_class" {
  description = "RDS instance class (FR-013: cost-minimum micro)."
  type        = string
  default     = "db.t4g.micro"
}

variable "rds_engine_version" {
  description = "PostgreSQL major version."
  type        = string
  default     = "16"
}

variable "rds_allocated_storage_gb" {
  description = "RDS allocated storage in GB."
  type        = number
  default     = 20
}

variable "rds_backup_retention_days" {
  description = "RDS automated backup retention (FR-012: 7 days)."
  type        = number
  default     = 7

  validation {
    condition     = var.rds_backup_retention_days >= 7
    error_message = "Backup retention must be at least 7 days per FR-012."
  }
}

variable "rds_database_name" {
  description = "Logical database name on RDS."
  type        = string
  default     = "escribania_cajas"
}

variable "rds_multi_az" {
  description = "Enable Multi-AZ for RDS (must be false per FR-013)."
  type        = bool
  default     = false

  validation {
    condition     = var.rds_multi_az == false
    error_message = "Multi-AZ is disabled per spec FR-013."
  }
}

variable "rds_master_username" {
  description = "RDS master username."
  type        = string
  default     = "escribania_admin"
}

# --- Secrets (wired in T014; set only in gitignored prod.tfvars) ---

variable "ssm_parameter_path_prefix" {
  description = "SSM Parameter Store path prefix for production secrets."
  type        = string
  default     = "/escribania/prod"
}

variable "jwt_secret" {
  description = "JWT signing secret — stored in SSM; never commit."
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "RDS master password — stored in SSM and used by RDS; never commit."
  type        = string
  sensitive   = true
}

variable "admin_username" {
  description = "Bootstrap admin username — stored in SSM; never commit."
  type        = string
  sensitive   = true
}

variable "admin_password" {
  description = "Bootstrap admin password — stored in SSM; never commit."
  type        = string
  sensitive   = true
}

# --- Compute / CORS (wired in T020/T025) ---

variable "cors_origins" {
  description = "Optional static CORS override for compute (non-prod). Production reads CloudFront URL from SSM."
  type        = string
  default     = ""
}

# --- Frontend (wired in T021) ---

variable "frontend_bucket_name_suffix" {
  description = "Optional suffix for globally unique S3 bucket name; auto-generated if empty."
  type        = string
  default     = ""
}
