data "aws_ami" "amazon_linux_arm" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-kernel-*-arm64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

locals {
  ssm_path_arn = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter${trimsuffix(var.ssm_parameter_path_prefix, "/")}/*"

  # T030: production runtime — container .env is built from SSM by load-env-from-ssm.sh
  app_environment = "production"

  default_user_data = templatefile("${path.module}/user_data.sh.tpl", {
    aws_region                        = data.aws_region.current.name
    app_environment                   = local.app_environment
    rds_host                          = var.rds_address
    rds_port                          = var.rds_port
    rds_database_name                 = var.rds_database_name
    rds_master_username               = var.rds_master_username
    ssm_jwt_parameter_name            = var.ssm_jwt_parameter_name
    ssm_db_password_parameter_name    = var.ssm_db_password_parameter_name
    ssm_admin_username_parameter_name = var.ssm_admin_username_parameter_name
    ssm_admin_password_parameter_name = var.ssm_admin_password_parameter_name
    cors_origins                      = var.cors_origins
    ssm_cors_origins_parameter_name   = var.ssm_cors_origins_parameter_name
    docker_compose_yml                = chomp(file("${path.module}/../../docker-compose.prod.yml"))
    load_env_script                   = chomp(file("${path.module}/files/load-env-from-ssm.sh"))
  })

  instance_user_data = var.user_data != "" ? var.user_data : local.default_user_data
}

resource "aws_iam_role" "api" {
  name = "${var.name_prefix}-api-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-api-role"
  })
}

resource "aws_iam_role_policy" "api_ssm_logs" {
  name = "${var.name_prefix}-api-ssm-logs"
  role = aws_iam_role.api.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadProductionParameters"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = local.ssm_path_arn
      },
      {
        Sid    = "DecryptSecureStrings"
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "ssm.${data.aws_region.current.name}.amazonaws.com"
          }
        }
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/escribania/*"
      },
      {
        Sid    = "DeployArtifactRead"
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = "arn:aws:s3:::${var.name_prefix}-frontend-*/${trimsuffix(var.deploy_artifact_prefix, "/")}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "api_ssm_managed" {
  role       = aws_iam_role.api.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "api" {
  name = "${var.name_prefix}-api-profile"
  role = aws_iam_role.api.name

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-api-profile"
  })
}

resource "aws_instance" "api" {
  ami                    = data.aws_ami.amazon_linux_arm.id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = var.security_group_ids
  iam_instance_profile   = aws_iam_instance_profile.api.name

  associate_public_ip_address = true

  user_data                   = local.instance_user_data
  user_data_replace_on_change = true

  root_block_device {
    volume_size = var.root_volume_gb
    volume_type = "gp3"
    encrypted   = true
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  tags = merge(var.tags, {
    Name            = "${var.name_prefix}-api"
    HealthCheckPath = var.health_check_path
    HealthCheckPort = "8000"
  })

  lifecycle {
    ignore_changes = [ami]
  }
}
