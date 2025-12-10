# AWS Deployment Guide — ProjectEPU

Complete step-by-step instructions for deploying ProjectEPU to AWS using ECS Fargate, RDS, S3, and managed services.

---

## Prerequisites

- AWS Account with admin access
- AWS CLI installed and configured (`aws configure`)
- Docker installed locally
- Domain name (for SSL certificate and email verification)
- GitHub account (for CI/CD)

---

## Architecture Overview

```
Internet
  ↓
Route 53 (DNS: yourdomain.com)
  ↓
CloudFront (CDN for static assets) [Optional but recommended]
  ↓
Application Load Balancer (HTTPS, port 443)
  ↓
ECS Fargate Service (2+ tasks for HA)
  ├─→ Container (port 4200)
  ├─→ RDS SQL Server (private subnet, port 1433)
  ├─→ ElastiCache Redis (private subnet, port 6379)
  └─→ S3 Buckets (uploads + static assets)
```

**Estimated Cost**: $140-200/month for small production setup (see end of guide for breakdown)

---

## Phase 1: AWS Infrastructure Setup

### Step 1.1: Create VPC and Networking

```bash
# Set your region
export AWS_REGION=us-east-1
export PROJECT_NAME=projectepu

# Create VPC with public and private subnets
aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=$PROJECT_NAME-vpc}]" \
  --region $AWS_REGION

# Save VPC ID
export VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=$PROJECT_NAME-vpc" --query "Vpcs[0].VpcId" --output text)

# Create Internet Gateway
aws ec2 create-internet-gateway \
  --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=$PROJECT_NAME-igw}]"

export IGW_ID=$(aws ec2 describe-internet-gateways --filters "Name=tag:Name,Values=$PROJECT_NAME-igw" --query "InternetGateways[0].InternetGatewayId" --output text)

# Attach IGW to VPC
aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID

# Create public subnets (for ALB)
aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone ${AWS_REGION}a \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-public-1a}]"

aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone ${AWS_REGION}b \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-public-1b}]"

# Create private subnets (for ECS, RDS, Redis)
aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.11.0/24 \
  --availability-zone ${AWS_REGION}a \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-private-1a}]"

aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.12.0/24 \
  --availability-zone ${AWS_REGION}b \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-private-1b}]"

# Create NAT Gateway (for private subnets to access internet)
# Allocate Elastic IP
aws ec2 allocate-address --domain vpc --tag-specifications "ResourceType=elastic-ip,Tags=[{Key=Name,Value=$PROJECT_NAME-nat-eip}]"

export EIP_ID=$(aws ec2 describe-addresses --filters "Name=tag:Name,Values=$PROJECT_NAME-nat-eip" --query "Addresses[0].AllocationId" --output text)

export PUBLIC_SUBNET_1A=$(aws ec2 describe-subnets --filters "Name=tag:Name,Values=$PROJECT_NAME-public-1a" --query "Subnets[0].SubnetId" --output text)

aws ec2 create-nat-gateway \
  --subnet-id $PUBLIC_SUBNET_1A \
  --allocation-id $EIP_ID \
  --tag-specifications "ResourceType=nat-gateway,Tags=[{Key=Name,Value=$PROJECT_NAME-nat}]"

export NAT_ID=$(aws ec2 describe-nat-gateways --filter "Name=tag:Name,Values=$PROJECT_NAME-nat" --query "NatGateways[0].NatGatewayId" --output text)

# Wait for NAT Gateway to be available (takes 2-3 minutes)
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_ID

# Create route tables
aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=$PROJECT_NAME-public-rt}]"

aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=$PROJECT_NAME-private-rt}]"

export PUBLIC_RT=$(aws ec2 describe-route-tables --filters "Name=tag:Name,Values=$PROJECT_NAME-public-rt" --query "RouteTables[0].RouteTableId" --output text)

export PRIVATE_RT=$(aws ec2 describe-route-tables --filters "Name=tag:Name,Values=$PROJECT_NAME-private-rt" --query "RouteTables[0].RouteTableId" --output text)

# Add routes
aws ec2 create-route --route-table-id $PUBLIC_RT --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
aws ec2 create-route --route-table-id $PRIVATE_RT --destination-cidr-block 0.0.0.0/0 --nat-gateway-id $NAT_ID

# Associate subnets with route tables
export PUBLIC_SUBNET_1B=$(aws ec2 describe-subnets --filters "Name=tag:Name,Values=$PROJECT_NAME-public-1b" --query "Subnets[0].SubnetId" --output text)
export PRIVATE_SUBNET_1A=$(aws ec2 describe-subnets --filters "Name=tag:Name,Values=$PROJECT_NAME-private-1a" --query "Subnets[0].SubnetId" --output text)
export PRIVATE_SUBNET_1B=$(aws ec2 describe-subnets --filters "Name=tag:Name,Values=$PROJECT_NAME-private-1b" --query "Subnets[0].SubnetId" --output text)

aws ec2 associate-route-table --route-table-id $PUBLIC_RT --subnet-id $PUBLIC_SUBNET_1A
aws ec2 associate-route-table --route-table-id $PUBLIC_RT --subnet-id $PUBLIC_SUBNET_1B
aws ec2 associate-route-table --route-table-id $PRIVATE_RT --subnet-id $PRIVATE_SUBNET_1A
aws ec2 associate-route-table --route-table-id $PRIVATE_RT --subnet-id $PRIVATE_SUBNET_1B
```

**Alternative (Simpler)**: Use AWS Console VPC Wizard → "VPC with Public and Private Subnets" template.

---

### Step 1.2: Create Security Groups

```bash
# ALB Security Group (allow HTTPS from internet)
aws ec2 create-security-group \
  --group-name $PROJECT_NAME-alb-sg \
  --description "ALB security group" \
  --vpc-id $VPC_ID

export ALB_SG=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$PROJECT_NAME-alb-sg" --query "SecurityGroups[0].GroupId" --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

# ECS Security Group (allow traffic from ALB only)
aws ec2 create-security-group \
  --group-name $PROJECT_NAME-ecs-sg \
  --description "ECS tasks security group" \
  --vpc-id $VPC_ID

export ECS_SG=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$PROJECT_NAME-ecs-sg" --query "SecurityGroups[0].GroupId" --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $ECS_SG \
  --protocol tcp \
  --port 4200 \
  --source-group $ALB_SG

# RDS Security Group (allow access from ECS only)
aws ec2 create-security-group \
  --group-name $PROJECT_NAME-rds-sg \
  --description "RDS security group" \
  --vpc-id $VPC_ID

export RDS_SG=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$PROJECT_NAME-rds-sg" --query "SecurityGroups[0].GroupId" --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $RDS_SG \
  --protocol tcp \
  --port 1433 \
  --source-group $ECS_SG

# Redis Security Group (allow access from ECS only)
aws ec2 create-security-group \
  --group-name $PROJECT_NAME-redis-sg \
  --description "ElastiCache Redis security group" \
  --vpc-id $VPC_ID

export REDIS_SG=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$PROJECT_NAME-redis-sg" --query "SecurityGroups[0].GroupId" --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $REDIS_SG \
  --protocol tcp \
  --port 6379 \
  --source-group $ECS_SG
```

---

### Step 1.3: Create RDS SQL Server Database

```bash
# Create DB subnet group
aws rds create-db-subnet-group \
  --db-subnet-group-name $PROJECT_NAME-db-subnet \
  --db-subnet-group-description "Subnet group for ProjectEPU RDS" \
  --subnet-ids $PRIVATE_SUBNET_1A $PRIVATE_SUBNET_1B

# Create RDS SQL Server instance
aws rds create-db-instance \
  --db-instance-identifier $PROJECT_NAME-db \
  --db-instance-class db.t3.small \
  --engine sqlserver-ex \
  --master-username admin \
  --master-user-password 'YOUR_STRONG_PASSWORD_HERE' \
  --allocated-storage 20 \
  --storage-type gp3 \
  --vpc-security-group-ids $RDS_SG \
  --db-subnet-group-name $PROJECT_NAME-db-subnet \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "mon:04:00-mon:05:00" \
  --publicly-accessible false \
  --storage-encrypted \
  --enable-cloudwatch-logs-exports '["error","agent"]' \
  --tags Key=Name,Value=$PROJECT_NAME-db

# Wait for RDS to be available (takes 10-15 minutes)
aws rds wait db-instance-available --db-instance-identifier $PROJECT_NAME-db

# Get RDS endpoint
export DB_ENDPOINT=$(aws rds describe-db-instances --db-instance-identifier $PROJECT_NAME-db --query "DBInstances[0].Endpoint.Address" --output text)

echo "RDS Endpoint: $DB_ENDPOINT"
```

**Important**: Save your master password securely. You'll need it for the connection string.

**Alternative (Cheaper)**: Use RDS PostgreSQL instead of SQL Server:
- Change `--engine` to `postgres`
- Use `--db-instance-class db.t4g.micro` (ARM-based, cheaper)
- Update app connection string to use `postgresql+psycopg2://` dialect
- Install `psycopg2-binary` in requirements.txt
- Test Alembic migrations against PostgreSQL locally first

---

### Step 1.4: Create ElastiCache Redis

```bash
# Create cache subnet group
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name $PROJECT_NAME-redis-subnet \
  --cache-subnet-group-description "Subnet group for ProjectEPU Redis" \
  --subnet-ids $PRIVATE_SUBNET_1A $PRIVATE_SUBNET_1B

# Create Redis cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id $PROJECT_NAME-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1 \
  --cache-subnet-group-name $PROJECT_NAME-redis-subnet \
  --security-group-ids $REDIS_SG \
  --tags Key=Name,Value=$PROJECT_NAME-redis

# Wait for Redis to be available (takes 5-10 minutes)
aws elasticache wait cache-cluster-available --cache-cluster-id $PROJECT_NAME-redis

# Get Redis endpoint
export REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters --cache-cluster-id $PROJECT_NAME-redis --show-cache-node-info --query "CacheClusters[0].CacheNodes[0].Endpoint.Address" --output text)

echo "Redis Endpoint: $REDIS_ENDPOINT"
```

---

### Step 1.5: Create S3 Buckets

```bash
export BUCKET_UPLOADS=$PROJECT_NAME-uploads
export BUCKET_STATIC=$PROJECT_NAME-static

# Create uploads bucket (private)
aws s3 mb s3://$BUCKET_UPLOADS --region $AWS_REGION

# Block public access
aws s3api put-public-access-block \
  --bucket $BUCKET_UPLOADS \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Enable versioning (recommended for rollback)
aws s3api put-bucket-versioning \
  --bucket $BUCKET_UPLOADS \
  --versioning-configuration Status=Enabled

# Enable server-side encryption
aws s3api put-bucket-encryption \
  --bucket $BUCKET_UPLOADS \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Create static assets bucket (public via CloudFront OAI)
aws s3 mb s3://$BUCKET_STATIC --region $AWS_REGION

# Block public access initially (CloudFront will access via OAI)
aws s3api put-public-access-block \
  --bucket $BUCKET_STATIC \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Upload existing static assets (from your local dev)
# Run this from your project root:
aws s3 sync static/ s3://$BUCKET_STATIC/static/ --delete
```

---

### Step 1.6: Create ECR Repository

```bash
# Create ECR repository for Docker images
aws ecr create-repository \
  --repository-name $PROJECT_NAME \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256

export ECR_REPO=$(aws ecr describe-repositories --repository-names $PROJECT_NAME --query "repositories[0].repositoryUri" --output text)

echo "ECR Repository: $ECR_REPO"

# Get login credentials and authenticate Docker
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO
```

---

## Phase 2: Application Code Updates

### Step 2.1: Migrate Storage to S3

You need to update the app to use S3 instead of local filesystem for uploads.

**Install boto3** (add to `requirements.txt`):
```txt
boto3>=1.28.0
```

**Create S3 storage service** (`app/services/s3_storage.py`):

```python
"""S3 storage abstraction for uploads."""
import boto3
from botocore.exceptions import ClientError
from app.core.settings import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize S3 client
s3_client = boto3.client('s3', region_name=settings.AWS_REGION)
BUCKET_NAME = settings.S3_UPLOADS_BUCKET


def upload_file(file_data: bytes, s3_key: str, content_type: str = "application/octet-stream") -> str:
    """Upload file to S3 and return the S3 key."""
    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=file_data,
            ContentType=content_type,
            ServerSideEncryption='AES256'
        )
        logger.info(f"Uploaded to S3: {s3_key}")
        return s3_key
    except ClientError as e:
        logger.error(f"S3 upload failed: {e}")
        raise


def download_file(s3_key: str) -> bytes:
    """Download file from S3."""
    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        return response['Body'].read()
    except ClientError as e:
        logger.error(f"S3 download failed: {e}")
        raise


def generate_presigned_url(s3_key: str, expiration: int = 3600) -> str:
    """Generate presigned URL for temporary access."""
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        logger.error(f"Presigned URL generation failed: {e}")
        raise


def delete_file(s3_key: str):
    """Delete file from S3."""
    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
        logger.info(f"Deleted from S3: {s3_key}")
    except ClientError as e:
        logger.error(f"S3 delete failed: {e}")
        raise
```

**Update settings** (`app/core/settings.py`):
```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # AWS S3
    AWS_REGION: str = "us-east-1"
    S3_UPLOADS_BUCKET: str
    S3_STATIC_BUCKET: str = ""  # Optional
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

**Update upload handler** (in `app/api/uploads.py` or wherever uploads are handled):

Replace filesystem writes with S3 uploads:
```python
from app.services.s3_storage import upload_file, generate_presigned_url

# Old code:
# storage_path = Path(f"storage/{user_id}/{event_id}/uploads")
# storage_path.mkdir(parents=True, exist_ok=True)
# file_path = storage_path / filename
# async with aiofiles.open(file_path, 'wb') as f:
#     await f.write(contents)

# New code:
s3_key = f"{user_id}/{event_id}/uploads/{filename}"
upload_file(await file.read(), s3_key, content_type=file.content_type)
```

**Update download/serving** (in gallery routes):

Replace direct file serving with presigned URLs:
```python
# Old code:
# return FileResponse(f"storage/{user_id}/{event_id}/uploads/{filename}")

# New code:
s3_key = f"{user_id}/{event_id}/uploads/{filename}"
presigned_url = generate_presigned_url(s3_key, expiration=300)  # 5 minutes
return RedirectResponse(presigned_url)
```

**Migration script** (`scripts/migrate_storage_to_s3.py`):

```python
"""One-time migration: Upload existing storage/ files to S3."""
import boto3
from pathlib import Path
import os

s3_client = boto3.client('s3')
BUCKET_NAME = os.getenv('S3_UPLOADS_BUCKET', 'projectepu-uploads')

storage_path = Path('storage')
for file_path in storage_path.rglob('*'):
    if file_path.is_file():
        s3_key = str(file_path.relative_to(storage_path)).replace('\\', '/')
        print(f"Uploading {file_path} → s3://{BUCKET_NAME}/{s3_key}")
        s3_client.upload_file(str(file_path), BUCKET_NAME, s3_key)

print("Migration complete!")
```

---

### Step 2.2: Update Environment Variables for AWS

Add to your `.env.production` (use AWS Secrets Manager for actual deployment):

```env
# Database (RDS endpoint from Step 1.3)
DB_SERVER=<RDS_ENDPOINT>  # e.g., projectepu-db.xxxxx.us-east-1.rds.amazonaws.com
DB_NAME=EPU
DB_USER=admin
DB_PASSWORD=<YOUR_RDS_PASSWORD>
DB_DRIVER=ODBC Driver 18 for SQL Server

# S3 Storage
AWS_REGION=us-east-1
S3_UPLOADS_BUCKET=projectepu-uploads
S3_STATIC_BUCKET=projectepu-static

# Redis (ElastiCache endpoint from Step 1.4)
REDIS_URL=redis://<REDIS_ENDPOINT>:6379/0  # e.g., redis://projectepu-redis.xxxxx.cache.amazonaws.com:6379/0

# Application
BASE_URL=https://yourdomain.com
SECRET_KEY=<GENERATE_64_CHAR_RANDOM_STRING>
COOKIE_SECURE=true

# Email (use SES instead of Gmail)
GMAIL_USER=noreply@yourdomain.com
GMAIL_APP_PASSWORD=<SES_SMTP_PASSWORD>
SUPPORT_EMAIL_TO=support@yourdomain.com

# Stripe
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Logging
LOG_LEVEL=INFO
LOG_JSON=true
SENTRY_DSN=<YOUR_SENTRY_DSN>

# Rate Limiting
RATE_LIMIT_LOGIN_ATTEMPTS=5
RATE_LIMIT_LOGIN_WINDOW_SECONDS=900
```

---

### Step 2.3: Store Secrets in AWS Secrets Manager

```bash
# Create secret with all environment variables
aws secretsmanager create-secret \
  --name $PROJECT_NAME/production/env \
  --secret-string file://.env.production \
  --description "Production environment variables for ProjectEPU"

export SECRET_ARN=$(aws secretsmanager describe-secret --secret-id $PROJECT_NAME/production/env --query "ARN" --output text)

echo "Secret ARN: $SECRET_ARN"
```

---

## Phase 3: CI/CD Pipeline Setup

### Step 3.1: Create GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to AWS ECS

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: projectepu
  ECS_CLUSTER: projectepu-cluster
  ECS_SERVICE: projectepu-service
  CONTAINER_NAME: projectepu-app

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run linter
        run: ruff check .
      
      - name: Run tests
        run: pytest -q

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Build, tag, and push image to ECR
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT
      
      - name: Run database migrations
        env:
          SECRET_ARN: ${{ secrets.AWS_SECRET_ARN }}
        run: |
          # Pull secrets from AWS Secrets Manager
          aws secretsmanager get-secret-value --secret-id $SECRET_ARN --query SecretString --output text > .env
          
          # Run migrations in container
          docker run --env-file .env ${{ steps.build-image.outputs.image }} \
            alembic upgrade head
      
      - name: Update ECS service
        run: |
          aws ecs update-service \
            --cluster $ECS_CLUSTER \
            --service $ECS_SERVICE \
            --force-new-deployment \
            --region $AWS_REGION
```

**Add GitHub Secrets** (Repository Settings → Secrets → Actions):
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SECRET_ARN` (from Step 2.3)

---

### Step 3.2: Create IAM User for GitHub Actions

```bash
# Create IAM policy for GitHub Actions
cat > github-actions-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:UpdateService",
        "ecs:DescribeServices"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "$SECRET_ARN"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name ${PROJECT_NAME}-github-actions \
  --policy-document file://github-actions-policy.json

# Create IAM user
aws iam create-user --user-name ${PROJECT_NAME}-github-actions

# Attach policy
export POLICY_ARN=$(aws iam list-policies --query "Policies[?PolicyName=='${PROJECT_NAME}-github-actions'].Arn" --output text)
aws iam attach-user-policy --user-name ${PROJECT_NAME}-github-actions --policy-arn $POLICY_ARN

# Create access keys
aws iam create-access-key --user-name ${PROJECT_NAME}-github-actions
```

Save the AccessKeyId and SecretAccessKey output — add them to GitHub Secrets.

---

## Phase 4: ECS Deployment

### Step 4.1: Create IAM Roles for ECS

**Task Execution Role** (for ECS to pull images and write logs):

```bash
cat > task-execution-role-trust.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name ${PROJECT_NAME}-task-execution-role \
  --assume-role-policy-document file://task-execution-role-trust.json

aws iam attach-role-policy \
  --role-name ${PROJECT_NAME}-task-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Add permission to read secrets
cat > secrets-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "$SECRET_ARN"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name ${PROJECT_NAME}-task-execution-role \
  --policy-name SecretsAccess \
  --policy-document file://secrets-policy.json

export TASK_EXECUTION_ROLE_ARN=$(aws iam get-role --role-name ${PROJECT_NAME}-task-execution-role --query "Role.Arn" --output text)
```

**Task Role** (for app to access S3, SES, etc.):

```bash
aws iam create-role \
  --role-name ${PROJECT_NAME}-task-role \
  --assume-role-policy-document file://task-execution-role-trust.json

cat > task-role-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::$BUCKET_UPLOADS",
        "arn:aws:s3:::$BUCKET_UPLOADS/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name ${PROJECT_NAME}-task-role \
  --policy-name AppPermissions \
  --policy-document file://task-role-policy.json

export TASK_ROLE_ARN=$(aws iam get-role --role-name ${PROJECT_NAME}-task-role --query "Role.Arn" --output text)
```

---

### Step 4.2: Create Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name $PROJECT_NAME-alb \
  --subnets $PUBLIC_SUBNET_1A $PUBLIC_SUBNET_1B \
  --security-groups $ALB_SG \
  --scheme internet-facing \
  --type application \
  --ip-address-type ipv4

export ALB_ARN=$(aws elbv2 describe-load-balancers --names $PROJECT_NAME-alb --query "LoadBalancers[0].LoadBalancerArn" --output text)
export ALB_DNS=$(aws elbv2 describe-load-balancers --names $PROJECT_NAME-alb --query "LoadBalancers[0].DNSName" --output text)

echo "ALB DNS: $ALB_DNS"

# Create target group
aws elbv2 create-target-group \
  --name $PROJECT_NAME-tg \
  --protocol HTTP \
  --port 4200 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

export TG_ARN=$(aws elbv2 describe-target-groups --names $PROJECT_NAME-tg --query "TargetGroups[0].TargetGroupArn" --output text)

# Create HTTPS listener (requires SSL certificate — see Step 4.3)
# Placeholder: Create HTTP listener for now
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN
```

---

### Step 4.3: Request SSL Certificate

```bash
# Request certificate via AWS Certificate Manager (ACM)
aws acm request-certificate \
  --domain-name yourdomain.com \
  --subject-alternative-names www.yourdomain.com \
  --validation-method DNS \
  --region $AWS_REGION

export CERT_ARN=$(aws acm list-certificates --query "CertificateSummaryList[?DomainName=='yourdomain.com'].CertificateArn" --output text)

# Get validation CNAME records
aws acm describe-certificate --certificate-arn $CERT_ARN

# Add CNAME records to your DNS (Route 53 or your domain registrar)
# Wait for validation (can take 5-30 minutes)
aws acm wait certificate-validated --certificate-arn $CERT_ARN

# Create HTTPS listener
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=$CERT_ARN \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN

# Update HTTP listener to redirect to HTTPS
export HTTP_LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn $ALB_ARN --query "Listeners[?Port==\`80\`].ListenerArn" --output text)

aws elbv2 modify-listener \
  --listener-arn $HTTP_LISTENER_ARN \
  --default-actions Type=redirect,RedirectConfig={Protocol=HTTPS,Port=443,StatusCode=HTTP_301}
```

---

### Step 4.4: Create ECS Cluster and Task Definition

```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name $PROJECT_NAME-cluster

# Register task definition
cat > task-definition.json <<EOF
{
  "family": "$PROJECT_NAME-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "$TASK_EXECUTION_ROLE_ARN",
  "taskRoleArn": "$TASK_ROLE_ARN",
  "containerDefinitions": [
    {
      "name": "$PROJECT_NAME-app",
      "image": "$ECR_REPO:latest",
      "portMappings": [
        {
          "containerPort": 4200,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [],
      "secrets": [
        {
          "name": "DB_SERVER",
          "valueFrom": "$SECRET_ARN:DB_SERVER::"
        },
        {
          "name": "DB_NAME",
          "valueFrom": "$SECRET_ARN:DB_NAME::"
        },
        {
          "name": "DB_USER",
          "valueFrom": "$SECRET_ARN:DB_USER::"
        },
        {
          "name": "DB_PASSWORD",
          "valueFrom": "$SECRET_ARN:DB_PASSWORD::"
        },
        {
          "name": "DB_DRIVER",
          "valueFrom": "$SECRET_ARN:DB_DRIVER::"
        },
        {
          "name": "SECRET_KEY",
          "valueFrom": "$SECRET_ARN:SECRET_KEY::"
        },
        {
          "name": "BASE_URL",
          "valueFrom": "$SECRET_ARN:BASE_URL::"
        },
        {
          "name": "REDIS_URL",
          "valueFrom": "$SECRET_ARN:REDIS_URL::"
        },
        {
          "name": "AWS_REGION",
          "valueFrom": "$SECRET_ARN:AWS_REGION::"
        },
        {
          "name": "S3_UPLOADS_BUCKET",
          "valueFrom": "$SECRET_ARN:S3_UPLOADS_BUCKET::"
        },
        {
          "name": "STRIPE_SECRET_KEY",
          "valueFrom": "$SECRET_ARN:STRIPE_SECRET_KEY::"
        },
        {
          "name": "GMAIL_USER",
          "valueFrom": "$SECRET_ARN:GMAIL_USER::"
        },
        {
          "name": "GMAIL_APP_PASSWORD",
          "valueFrom": "$SECRET_ARN:GMAIL_APP_PASSWORD::"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/$PROJECT_NAME",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:4200/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

# Create CloudWatch log group
aws logs create-log-group --log-group-name /ecs/$PROJECT_NAME
aws logs put-retention-policy --log-group-name /ecs/$PROJECT_NAME --retention-in-days 30

# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

**Note**: For production, split secrets into individual keys in Secrets Manager for better granularity. The above uses JSON secret parsing.

---

### Step 4.5: Create ECS Service

```bash
# Create ECS service
aws ecs create-service \
  --cluster $PROJECT_NAME-cluster \
  --service-name $PROJECT_NAME-service \
  --task-definition $PROJECT_NAME-task \
  --desired-count 2 \
  --launch-type FARGATE \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={subnets=[$PRIVATE_SUBNET_1A,$PRIVATE_SUBNET_1B],securityGroups=[$ECS_SG],assignPublicIp=DISABLED}" \
  --load-balancers "targetGroupArn=$TG_ARN,containerName=$PROJECT_NAME-app,containerPort=4200" \
  --health-check-grace-period-seconds 60

# Enable auto-scaling (optional)
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/$PROJECT_NAME-cluster/$PROJECT_NAME-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10

aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/$PROJECT_NAME-cluster/$PROJECT_NAME-service \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name cpu-target-tracking \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'
```

---

## Phase 5: DNS and CDN Setup

### Step 5.1: Configure Route 53

```bash
# Create hosted zone (if not already created)
aws route53 create-hosted-zone \
  --name yourdomain.com \
  --caller-reference $(date +%s)

export HOSTED_ZONE_ID=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='yourdomain.com.'].Id" --output text | cut -d'/' -f3)

# Create A record pointing to ALB
cat > route53-record.json <<EOF
{
  "Changes": [
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "yourdomain.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "$(aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN --query 'LoadBalancers[0].CanonicalHostedZoneId' --output text)",
          "DNSName": "$ALB_DNS",
          "EvaluateTargetHealth": true
        }
      }
    }
  ]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch file://route53-record.json
```

Update your domain registrar's nameservers to point to Route 53 NS records (get from `aws route53 get-hosted-zone --id $HOSTED_ZONE_ID`).

---

### Step 5.2: Create CloudFront Distribution (Optional)

For faster static asset delivery:

```bash
# Create CloudFront Origin Access Identity (OAI)
aws cloudfront create-cloud-front-origin-access-identity \
  --cloud-front-origin-access-identity-config \
    "CallerReference=$(date +%s),Comment=OAI for $PROJECT_NAME"

export OAI_ID=$(aws cloudfront list-cloud-front-origin-access-identities --query "CloudFrontOriginAccessIdentityList.Items[?Comment=='OAI for $PROJECT_NAME'].Id" --output text)

# Update S3 bucket policy to allow CloudFront OAI
cat > s3-bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::cloudfront:user/CloudFront Origin Access Identity $OAI_ID"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::$BUCKET_STATIC/*"
    }
  ]
}
EOF

aws s3api put-bucket-policy --bucket $BUCKET_STATIC --policy file://s3-bucket-policy.json

# Create CloudFront distribution (simplified; use AWS Console for full config)
aws cloudfront create-distribution --distribution-config file://cloudfront-config.json
```

Update templates to reference CloudFront URL: `https://d1234567890.cloudfront.net/static/`

---

## Phase 6: Final Steps

### Step 6.1: Run Database Migrations

```bash
# Build and push initial image
docker build -t $ECR_REPO:latest .
docker push $ECR_REPO:latest

# Run migration as one-time ECS task
aws ecs run-task \
  --cluster $PROJECT_NAME-cluster \
  --launch-type FARGATE \
  --task-definition $PROJECT_NAME-task \
  --network-configuration "awsvpcConfiguration={subnets=[$PRIVATE_SUBNET_1A],securityGroups=[$ECS_SG],assignPublicIp=DISABLED}" \
  --overrides '{
    "containerOverrides": [{
      "name": "'$PROJECT_NAME'-app",
      "command": ["alembic", "upgrade", "head"]
    }]
  }'
```

Monitor CloudWatch Logs to verify migrations succeeded.

---

### Step 6.2: Migrate Existing Data to S3

```bash
# Run migration script locally (with AWS credentials configured)
python scripts/migrate_storage_to_s3.py
```

---

### Step 6.3: Configure Amazon SES for Email

```bash
# Verify domain identity
aws ses verify-domain-identity --domain yourdomain.com

# Add TXT record to DNS for verification (check SES console for value)

# Request production access (exit sandbox mode)
# Go to SES Console → Account Dashboard → Request Production Access

# Generate SMTP credentials
aws ses create-smtp-user --user-name ses-smtp-user

# Update .env with SES SMTP endpoint:
# GMAIL_USER=noreply@yourdomain.com
# GMAIL_APP_PASSWORD=<SES_SMTP_PASSWORD>
# SMTP Host: email-smtp.us-east-1.amazonaws.com
```

Update `app/services/email_utils.py` to use SES SMTP host instead of `smtp.gmail.com`.

---

### Step 6.4: Test Deployment

1. **Check ECS service status**:
   ```bash
   aws ecs describe-services --cluster $PROJECT_NAME-cluster --services $PROJECT_NAME-service
   ```

2. **Check target health**:
   ```bash
   aws elbv2 describe-target-health --target-group-arn $TG_ARN
   ```

3. **Access application**:
   - Via ALB: `https://$ALB_DNS`
   - Via domain: `https://yourdomain.com`

4. **Monitor logs**:
   ```bash
   aws logs tail /ecs/$PROJECT_NAME --follow
   ```

5. **Test features**:
   - Sign up / login
   - Create event
   - Upload photo
   - View gallery
   - Live slideshow

---

## Monitoring and Maintenance

### CloudWatch Alarms

```bash
# CPU utilization alarm
aws cloudwatch put-metric-alarm \
  --alarm-name $PROJECT_NAME-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ClusterName,Value=$PROJECT_NAME-cluster Name=ServiceName,Value=$PROJECT_NAME-service \
  --evaluation-periods 2

# Target health alarm
aws cloudwatch put-metric-alarm \
  --alarm-name $PROJECT_NAME-unhealthy-targets \
  --alarm-description "Alert when targets are unhealthy" \
  --metric-name UnHealthyHostCount \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 60 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --dimensions Name=TargetGroup,Value=$(echo $TG_ARN | cut -d':' -f6) Name=LoadBalancer,Value=$(echo $ALB_ARN | cut -d':' -f6 | cut -d'/' -f2-) \
  --evaluation-periods 2
```

### Backups

```bash
# Enable automated RDS snapshots (already enabled with --backup-retention-period 7)
# Manual snapshot:
aws rds create-db-snapshot \
  --db-instance-identifier $PROJECT_NAME-db \
  --db-snapshot-identifier $PROJECT_NAME-db-snapshot-$(date +%Y%m%d)

# S3 versioning is already enabled for rollback
```

### Log Aggregation

- **Sentry**: Add `SENTRY_DSN` to secrets for error tracking
- **CloudWatch Insights**: Query structured JSON logs
- **X-Ray** (optional): Add AWS X-Ray SDK for distributed tracing

---

## Cost Breakdown (Estimated Monthly)

**Small Production Setup**:
- **ECS Fargate**: 2 tasks × 0.5 vCPU, 1GB RAM × 730 hours = ~$30
- **ALB**: 1 ALB + ~1M LCU-hours = ~$25
- **RDS SQL Server Express**: db.t3.small (2 vCPU, 2GB) = ~$60
- **ElastiCache Redis**: cache.t3.micro (0.5GB) = ~$12
- **S3 Storage**: 50GB uploads + 5GB static = ~$1.50
- **S3 Requests**: 1M PUT/GET = ~$5
- **CloudFront**: 10GB transfer + 1M requests = ~$2
- **Route 53**: 1 hosted zone = ~$0.50
- **CloudWatch Logs**: 5GB ingestion + 30-day retention = ~$2.50
- **Secrets Manager**: 5 secrets × $0.40 = ~$2
- **NAT Gateway**: 730 hours + 5GB data = ~$35
- **Data Transfer Out**: 20GB = ~$1.80

**Total: ~$177/month**

**Cost Optimization Tips**:
- Use Fargate Spot for non-critical tasks (50% savings)
- Use RDS PostgreSQL instead of SQL Server (~$15/month for db.t4g.micro)
- Remove NAT Gateway and use VPC endpoints for AWS services
- Use S3 Intelligent-Tiering for old uploads
- Enable CloudWatch log filtering to reduce ingestion

---

## Rollback Plan

If deployment fails:

1. **Revert ECS service**:
   ```bash
   # Deploy previous task definition revision
   aws ecs update-service \
     --cluster $PROJECT_NAME-cluster \
     --service $PROJECT_NAME-service \
     --task-definition $PROJECT_NAME-task:<PREVIOUS_REVISION>
   ```

2. **Restore RDS from snapshot**:
   ```bash
   aws rds restore-db-instance-from-db-snapshot \
     --db-instance-identifier $PROJECT_NAME-db-restored \
     --db-snapshot-identifier $PROJECT_NAME-db-snapshot-YYYYMMDD
   ```

3. **Revert Alembic migrations**:
   ```bash
   alembic downgrade <PREVIOUS_REVISION>
   ```

---

## Troubleshooting

### ECS tasks fail to start

- Check CloudWatch logs: `aws logs tail /ecs/$PROJECT_NAME --follow`
- Check task execution role has ECR and Secrets Manager permissions
- Verify security groups allow ECS → RDS and ECS → Redis

### Health checks failing

- Test health endpoint: `curl http://<TASK_IP>:4200/health`
- Check RDS connectivity from ECS task
- Verify container is listening on port 4200

### Database connection errors

- Verify RDS security group allows traffic from ECS security group on port 1433
- Check `DB_SERVER` value in Secrets Manager (should be RDS endpoint)
- Test ODBC connection: `docker exec <CONTAINER_ID> isql -v`

### S3 access denied

- Verify task role has `s3:GetObject`, `s3:PutObject` permissions
- Check bucket name matches `S3_UPLOADS_BUCKET` env var
- Test with AWS CLI: `aws s3 ls s3://$BUCKET_UPLOADS`

---

## Next Steps

1. **Set up staging environment**: Duplicate infrastructure with smaller instance sizes
2. **Implement blue-green deployments**: Use ECS service deployment circuit breaker
3. **Add WAF**: Attach AWS WAF to ALB for DDoS protection
4. **Enable CloudTrail**: Audit all AWS API calls
5. **Set up backups**: Automate S3 sync to Glacier for long-term storage
6. **Performance tuning**: Add ElastiCache for query results, use CloudFront for media
7. **Monitoring dashboard**: Create CloudWatch dashboard with key metrics

---

## Support

For issues with this deployment guide, refer to:
- AWS ECS documentation: https://docs.aws.amazon.com/ecs/
- ProjectEPU README: `README.md`
- Deployment checklist: `DEPLOYMENT.md`

**Cost Estimate Calculator**: https://calculator.aws/
