variable "name_prefix" {
  description = "Prefix for S3 and CloudFront resource names."
  type        = string
}

variable "bucket_name_suffix" {
  description = "Optional suffix for globally unique bucket name; defaults to account ID."
  type        = string
  default     = ""
}

variable "default_root_object" {
  description = "CloudFront default root object."
  type        = string
  default     = "index.html"
}

variable "spa_error_caching_min_ttl" {
  description = "Minimum TTL (seconds) for SPA custom error responses (403/404 → index.html)."
  type        = number
  default     = 10
}

variable "api_origin_domain_name" {
  description = "EC2 public DNS hostname for the API origin (CloudFront custom origin)."
  type        = string
}

variable "api_origin_port" {
  description = "HTTP port on the API EC2 instance."
  type        = number
  default     = 8000
}

variable "api_path_pattern" {
  description = "CloudFront path pattern for API traffic."
  type        = string
  default     = "/api/*"
}

variable "ssm_parameter_path_prefix" {
  description = "SSM path prefix for CORS_ORIGINS parameter (e.g. /escribania/prod)."
  type        = string
}

variable "tags" {
  description = "Tags applied to frontend resources."
  type        = map(string)
  default     = {}
}
