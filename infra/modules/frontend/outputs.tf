output "bucket_name" {
  description = "S3 bucket name for frontend static assets."
  value       = aws_s3_bucket.frontend.id
}

output "bucket_arn" {
  description = "S3 bucket ARN."
  value       = aws_s3_bucket.frontend.arn
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID."
  value       = aws_cloudfront_distribution.frontend.id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name (HTTPS URL host)."
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_distribution_arn" {
  description = "CloudFront distribution ARN."
  value       = aws_cloudfront_distribution.frontend.arn
}

output "public_url" {
  description = "Public HTTPS URL for users."
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "cors_origins_parameter_name" {
  description = "SSM parameter name for CORS_ORIGINS (CloudFront URL)."
  value       = aws_ssm_parameter.cors_origins.name
}
