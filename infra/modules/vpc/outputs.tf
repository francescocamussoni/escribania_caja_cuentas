output "vpc_id" {
  description = "VPC identifier."
  value       = aws_vpc.this.id
}

output "vpc_cidr" {
  description = "VPC CIDR block."
  value       = aws_vpc.this.cidr_block
}

output "public_subnet_ids" {
  description = "Public subnet IDs for EC2 (one per AZ)."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs for RDS subnet group."
  value       = aws_subnet.private[*].id
}

output "availability_zones" {
  description = "Availability zones used by subnets."
  value       = local.azs
}

output "api_security_group_id" {
  description = "Security group for API EC2 instance."
  value       = aws_security_group.api.id
}

output "rds_security_group_id" {
  description = "Security group for RDS instance."
  value       = aws_security_group.rds.id
}

output "internet_gateway_id" {
  description = "Internet gateway ID (no NAT gateway in lean architecture)."
  value       = aws_internet_gateway.this.id
}
