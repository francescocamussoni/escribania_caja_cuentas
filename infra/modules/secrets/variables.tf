variable "name_prefix" {
  description = "Prefix for SSM parameter path segments."
  type        = string
}

variable "parameter_path_prefix" {
  description = "SSM path prefix for secrets (e.g. /escribania/prod)."
  type        = string
  default     = "/escribania/prod"
}

variable "jwt_secret" {
  description = "JWT signing secret for production API."
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "RDS master password (also used to build DATABASE_URL on compute)."
  type        = string
  sensitive   = true
}

variable "admin_username" {
  description = "Bootstrap admin username for production."
  type        = string
  sensitive   = true
}

variable "admin_password" {
  description = "Bootstrap admin password for production."
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Tags applied to SSM parameters."
  type        = map(string)
  default     = {}
}
