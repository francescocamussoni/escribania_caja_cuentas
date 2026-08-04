provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Feature     = var.feature
  }

  ssm_base_path                   = trimsuffix(var.ssm_parameter_path_prefix, "/")
  ssm_cors_origins_parameter_name = "${local.ssm_base_path}/cors_origins"
}

module "vpc" {
  source = "./modules/vpc"

  name_prefix = var.name_prefix
  vpc_cidr    = var.vpc_cidr
  tags        = local.common_tags
}

module "secrets" {
  source = "./modules/secrets"

  name_prefix           = var.name_prefix
  parameter_path_prefix = var.ssm_parameter_path_prefix
  jwt_secret            = var.jwt_secret
  db_password           = var.db_password
  admin_username        = var.admin_username
  admin_password        = var.admin_password
  tags                  = local.common_tags
}

module "rds" {
  source = "./modules/rds"

  name_prefix           = var.name_prefix
  private_subnet_ids    = module.vpc.private_subnet_ids
  security_group_ids    = [module.vpc.rds_security_group_id]
  database_name         = var.rds_database_name
  engine_version        = var.rds_engine_version
  instance_class        = var.rds_instance_class
  allocated_storage_gb  = var.rds_allocated_storage_gb
  backup_retention_days = var.rds_backup_retention_days
  multi_az              = var.rds_multi_az
  master_username       = var.rds_master_username
  master_password       = var.db_password
  tags                  = local.common_tags

  depends_on = [module.secrets]
}

module "compute" {
  source = "./modules/compute"

  name_prefix                       = var.name_prefix
  subnet_id                         = module.vpc.public_subnet_ids[0]
  security_group_ids                = [module.vpc.api_security_group_id]
  instance_type                     = var.ec2_instance_type
  root_volume_gb                    = var.ec2_root_volume_gb
  ssm_parameter_path_prefix         = var.ssm_parameter_path_prefix
  rds_address                       = module.rds.address
  rds_port                          = module.rds.port
  rds_database_name                 = module.rds.database_name
  rds_master_username               = var.rds_master_username
  ssm_jwt_parameter_name            = module.secrets.jwt_secret_parameter_name
  ssm_db_password_parameter_name    = module.secrets.db_password_parameter_name
  ssm_admin_username_parameter_name = module.secrets.admin_username_parameter_name
  ssm_admin_password_parameter_name = module.secrets.admin_password_parameter_name
  ssm_cors_origins_parameter_name   = local.ssm_cors_origins_parameter_name
  cors_origins                      = var.cors_origins
  health_check_path                 = "/health"
  tags                              = local.common_tags

  depends_on = [module.rds, module.secrets]
}

module "frontend" {
  source = "./modules/frontend"

  name_prefix               = var.name_prefix
  bucket_name_suffix        = var.frontend_bucket_name_suffix
  ssm_parameter_path_prefix = var.ssm_parameter_path_prefix
  api_origin_domain_name    = module.compute.public_dns
  api_origin_port           = 8000
  tags                      = local.common_tags

  depends_on = [module.compute]
}
