variable "name_prefix" {
  description = "Prefix for RDS resource names."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for the RDS subnet group."
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_ids) >= 2
    error_message = "RDS subnet group requires at least two private subnets."
  }
}

variable "security_group_ids" {
  description = "Security groups attached to the RDS instance."
  type        = list(string)
}

variable "database_name" {
  description = "Logical database name."
  type        = string
}

variable "engine_version" {
  description = "PostgreSQL major version."
  type        = string
  default     = "16"
}

variable "instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "allocated_storage_gb" {
  description = "Allocated storage in GB."
  type        = number
  default     = 20
}

variable "backup_retention_days" {
  description = "Automated backup retention in days (FR-012: minimum 7)."
  type        = number
  default     = 7

  validation {
    condition     = var.backup_retention_days >= 7
    error_message = "backup_retention_days must be at least 7."
  }
}

variable "multi_az" {
  description = "Enable Multi-AZ (must be false per FR-013)."
  type        = bool
  default     = false

  validation {
    condition     = var.multi_az == false
    error_message = "multi_az must be false per FR-013."
  }
}

variable "master_username" {
  description = "RDS master username."
  type        = string
  default     = "escribania_admin"
}

variable "master_password" {
  description = "RDS master password (from SSM / prod.tfvars; never commit)."
  type        = string
  sensitive   = true
}

variable "deletion_protection" {
  description = "Prevent accidental RDS deletion in production."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags applied to RDS resources."
  type        = map(string)
  default     = {}
}
