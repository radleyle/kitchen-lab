# RDS = managed Postgres pantry. After first boot, enable pgvector:
#   CREATE EXTENSION IF NOT EXISTS vector;
# (RDS Postgres 15/16 commonly supports it — confirm in your region.)

resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-db"
  subnet_ids = aws_subnet.public[*].id
}

resource "aws_db_instance" "main" {
  identifier     = "${var.project}-${var.environment}"
  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t4g.micro"

  allocated_storage     = 20
  max_allocated_storage = 50
  storage_type          = "gp3"

  db_name  = "kitchenlab"
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  multi_az               = false

  backup_retention_period = 1
  skip_final_snapshot     = true
  deletion_protection     = false

  # pgvector lives as an extension inside the DB, not a separate engine.
  enabled_cloudwatch_logs_exports = ["postgresql"]
}
