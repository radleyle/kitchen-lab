variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-west-2"
}

variable "project" {
  description = "Name prefix for resources"
  type        = string
  default     = "kitchenlab"
}

variable "environment" {
  description = "Environment tag (dev / staging / prod)"
  type        = string
  default     = "dev"
}

variable "db_username" {
  description = "Master username for RDS Postgres"
  type        = string
  default     = "kitchenlab"
}

variable "db_password" {
  description = "Master password for RDS (set via TF_VAR_db_password or tfvars; never commit)"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "JWT signing secret for the FastAPI app"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key injected into the backend task"
  type        = string
  sensitive   = true
  default     = ""
}

variable "backend_image" {
  description = "ECR image URI for the backend (set after first push, or leave empty to skip ECS services)"
  type        = string
  default     = ""
}

variable "frontend_image" {
  description = "ECR image URI for the frontend"
  type        = string
  default     = ""
}

variable "frontend_cpu" {
  type    = number
  default = 256
}

variable "frontend_memory" {
  type    = number
  default = 512
}

variable "backend_cpu" {
  type    = number
  default = 256
}

variable "backend_memory" {
  type    = number
  default = 512
}

variable "desired_count" {
  description = "Number of tasks per service"
  type        = number
  default     = 1
}
