data "aws_caller_identity" "current" {}

locals {
  bucket_name   = var.bucket_name_suffix != "" ? "${var.name_prefix}-frontend-${var.bucket_name_suffix}" : "${var.name_prefix}-frontend-${data.aws_caller_identity.current.account_id}"
  ssm_base_path = trimsuffix(var.ssm_parameter_path_prefix, "/")
}

resource "aws_s3_bucket" "frontend" {
  bucket = local.bucket_name

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-frontend"
  })
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "${var.name_prefix}-frontend-oac"
  description                       = "OAC for ${var.name_prefix} frontend bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# Rewrites /api/health → /health on the EC2 origin (backend exposes /health only).
resource "aws_cloudfront_function" "api_health_rewrite" {
  name    = "${replace(var.name_prefix, "-", "_")}_api_health_rewrite"
  runtime = "cloudfront-js-2.0"
  comment = "Rewrite /api/health to /health for EC2 API origin"
  publish = true
  code    = <<-EOF
function handler(event) {
    var request = event.request;
    if (request.uri === "/api/health" || request.uri.startsWith("/api/health?")) {
        var query = request.uri.indexOf("?") >= 0 ? request.uri.substring(request.uri.indexOf("?")) : "";
        request.uri = "/health" + query;
    }
    return request;
}
EOF
}

resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = var.default_root_object
  comment             = "${var.name_prefix} SPA"

  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id                = "s3-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }

  origin {
    domain_name = var.api_origin_domain_name
    origin_id   = "ec2-api"

    custom_origin_config {
      http_port              = var.api_origin_port
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "s3-frontend"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true
    cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6" # AWS Managed-CachingOptimized
  }

  ordered_cache_behavior {
    path_pattern           = var.api_path_pattern
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "ec2-api"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad" # AWS Managed-CachingDisabled
    origin_request_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac" # AWS Managed-AllViewerExceptHostHeader

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.api_health_rewrite.arn
    }
  }

  # SPA client-side routing: S3 returns 403/404 for unknown paths; serve index.html with 200.
  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/${var.default_root_object}"
    error_caching_min_ttl = var.spa_error_caching_min_ttl
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/${var.default_root_object}"
    error_caching_min_ttl = var.spa_error_caching_min_ttl
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-cdn"
  })
}

resource "aws_ssm_parameter" "cors_origins" {
  name        = "${local.ssm_base_path}/cors_origins"
  description = "CORS_ORIGINS for API (${var.name_prefix} CloudFront URL)"
  type        = "String"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-cors-origins"
  })
}

data "aws_iam_policy_document" "frontend_bucket" {
  statement {
    sid    = "AllowCloudFrontServiceRead"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.frontend.arn}/*"]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.frontend.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = data.aws_iam_policy_document.frontend_bucket.json
}
