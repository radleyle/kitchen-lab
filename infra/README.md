# KitchenLab on AWS

**Lesson analogy:** Docker Compose is cooking at home (one tray, everything on the counter). AWS is a small restaurant:

| Home (Compose) | Restaurant (AWS) | Job |
| -------------- | ---------------- | --- |
| `db` service | **RDS** Postgres | Pantry |
| `backend` / `frontend` containers | **ECS Fargate** tasks | Cooks / waiters |
| `media` volume | **S3** bucket | Photo shelf |
| Laptop Docker images | **ECR** | Walk-in fridge for images |
| localhost ports | **ALB** | Front door (port 80) |

Terraform describes the building. GitHub Actions builds lunchboxes and puts them in ECR. **Nothing here runs or bills you until you apply Terraform and leave resources up.**

## Cost warning (read this)

Even a tiny stack costs money while running, roughly:

- ALB ≈ $16+/mo
- RDS `db.t4g.micro` ≈ $12–15+/mo
- Fargate (2 tiny tasks) ≈ $10–20+/mo
- S3 / ECR / logs = usually small

**Destroy when you are done experimenting:**

```bash
cd infra/terraform
terraform destroy
```

This demo uses **public subnets + public IPs on Fargate** to avoid a NAT Gateway (~$32/mo). That is fine for learning; a hardened prod design would put tasks in private subnets.

## Prerequisites

1. An AWS account and IAM user/role with rights to create VPC, ECS, RDS, ECR, S3, IAM, ELB.
2. [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.5 and AWS CLI configured (`aws configure`).
3. Docker for building images.
4. This repo’s GitHub secrets for CD (optional): `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`.

## Deploy in three phases

### Phase 1 — Create the empty restaurant (no app containers yet)

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars: set db_password, secret_key, openai_api_key
# Leave backend_image and frontend_image as "" for the first apply.

terraform init
terraform plan
terraform apply
```

Note the outputs: `ecr_backend_url`, `ecr_frontend_url`, `alb_dns_name`, `s3_bucket`, `rds_endpoint`.

### Phase 2 — Build & push images to ECR

```bash
AWS_REGION=us-west-2
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_BACKEND=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/kitchenlab-backend
ECR_FRONTEND=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/kitchenlab-frontend

aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Backend
docker build -f backend/Dockerfile.prod -t $ECR_BACKEND:latest backend
docker push $ECR_BACKEND:latest

# Frontend — bake the ALB URL so the browser calls the right API host
ALB_URL=$(cd infra/terraform && terraform output -raw alb_url)
docker build -f frontend/Dockerfile.prod \
  --build-arg NEXT_PUBLIC_API_URL=$ALB_URL \
  -t $ECR_FRONTEND:latest frontend
docker push $ECR_FRONTEND:latest
```

Or push via GitHub Actions (`.github/workflows/deploy.yml`) after secrets are set.

### Phase 3 — Start ECS services

In `terraform.tfvars`:

```hcl
backend_image  = "<account>.dkr.ecr.us-west-2.amazonaws.com/kitchenlab-backend:latest"
frontend_image = "<account>.dkr.ecr.us-west-2.amazonaws.com/kitchenlab-frontend:latest"
```

```bash
terraform apply
```

Open `terraform output -raw alb_url` in a browser. API docs: `http://<alb>/docs`.

### One-shot migrations on RDS

Run Alembic once against RDS (from your laptop with security group temporarily open, or an ECS run-task). Then:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Re-run the same seed modules from the main README (`safety_seed`, `knowledge_seed`, …) with `DATABASE_URL` pointed at RDS.

## App env vars in production

| Variable | Purpose |
| -------- | ------- |
| `DATABASE_URL` | SQLAlchemy URL (`postgresql+psycopg://...`) |
| `SECRET_KEY` | JWT signing |
| `OPENAI_API_KEY` | Embeddings + chat |
| `STORAGE_BACKEND=s3` | Use S3 instead of local disk |
| `S3_BUCKET` | Bucket from Terraform |
| `AWS_REGION` | Region |
| `CORS_ORIGINS` | Comma-separated browser origins |

ECS task role (not access keys in the container) grants S3 access.

## Files in this folder

```
terraform/
  versions.tf / variables.tf / outputs.tf
  network.tf      VPC, subnets, security groups
  ecr_s3.tf       Image repos + media bucket
  rds.tf          Postgres 16
  iam.tf          ECS execution + task roles
  alb.tf          Load balancer + API path rules
  ecs.tf          Cluster, task defs, services
  terraform.tfvars.example
```

## What this intentionally skips (for later)

- HTTPS / ACM certificate / custom domain
- Private subnets + NAT
- Secrets Manager instead of plain task env vars
- Autoscaling and multi-AZ RDS
- Remote Terraform state bucket (commented stub in `versions.tf`)
