output "instance_id" {
  description = "RDS instance identifier."
  value       = aws_db_instance.this.id
}

output "endpoint" {
  description = "RDS connection endpoint (host:port)."
  value       = aws_db_instance.this.endpoint
  sensitive   = true
}

output "address" {
  description = "RDS hostname."
  value       = aws_db_instance.this.address
  sensitive   = true
}

output "port" {
  description = "RDS port."
  value       = aws_db_instance.this.port
}

output "database_name" {
  description = "Logical database name."
  value       = aws_db_instance.this.db_name
}

output "master_username" {
  description = "RDS master username."
  value       = aws_db_instance.this.username
}

output "subnet_group_name" {
  description = "DB subnet group name."
  value       = aws_db_subnet_group.this.name
}
