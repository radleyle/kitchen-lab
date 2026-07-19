output "alb_dns_name" {
  description = "Open this in a browser after services are running"
  value       = aws_lb.main.dns_name
}

output "alb_url" {
  value = "http://${aws_lb.main.dns_name}"
}

output "ecr_backend_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "s3_bucket" {
  value = aws_s3_bucket.media.id
}

output "rds_endpoint" {
  value = aws_db_instance.main.address
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "database_url_hint" {
  description = "Shape of DATABASE_URL (password redacted)"
  value       = "postgresql+psycopg://${var.db_username}:****@${aws_db_instance.main.address}:5432/${aws_db_instance.main.db_name}"
}
