# AI Health Navigator - AWS Deployment Guide

This guide covers deploying the AI Health Navigator application to AWS using ECS Fargate.

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Docker** installed and running
3. **MongoDB Atlas** account (for production database)
4. **Pinecone** account (for RAG vector database)

## Quick Start

### 1. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your values
nano .env
```

Required variables:
- `AWS_ACCOUNT_ID` - Your AWS account ID
- `AWS_REGION` - Target region (default: us-east-1)
- `MONGODB_URI` - MongoDB Atlas connection string
- `PINECONE_API_KEY` - Pinecone API key

### 2. Deploy

```bash
# Full deployment (build, push, deploy)
./deploy.sh deploy
```

This will:
1. Build Docker images locally
2. Create ECR repositories
3. Push images to ECR
4. Deploy CloudFormation stack with ECS, ALB, etc.

### 3. Access Application

After deployment completes, get the URLs:

```bash
./deploy.sh status
```

## Deployment Commands

| Command | Description |
|---------|-------------|
| `./deploy.sh build` | Build Docker images locally |
| `./deploy.sh push` | Build and push images to ECR |
| `./deploy.sh deploy` | Full deployment |
| `./deploy.sh update` | Update existing deployment with new images |
| `./deploy.sh status` | Check deployment status and URLs |
| `./deploy.sh logs` | View application logs |
| `./deploy.sh logs api` | View API logs |
| `./deploy.sh destroy` | Delete all resources |
| `./deploy.sh local` | Run locally with docker-compose |

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │              AWS Cloud                   │
                    │                                         │
    Internet ──────►│  ┌─────────────┐    ┌─────────────┐    │
                    │  │ ALB (UI)    │    │ ALB (API)   │    │
                    │  └──────┬──────┘    └──────┬──────┘    │
                    │         │                  │           │
                    │  ┌──────▼──────┐    ┌──────▼──────┐    │
                    │  │ ECS Fargate │    │ ECS Fargate │    │
                    │  │ (Streamlit) │───►│ (FastAPI)   │    │
                    │  └─────────────┘    └──────┬──────┘    │
                    │                            │           │
                    └────────────────────────────┼───────────┘
                                                 │
                    ┌────────────────────────────┼───────────┐
                    │          External Services │           │
                    │                            ▼           │
                    │  ┌─────────────┐    ┌─────────────┐    │
                    │  │  Pinecone   │    │ MongoDB     │    │
                    │  │  (RAG)      │    │ Atlas       │    │
                    │  └─────────────┘    └─────────────┘    │
                    └────────────────────────────────────────┘
```

## Infrastructure Components

### ECS Cluster
- **Capacity Provider**: Fargate (serverless containers)
- **Services**:
  - `health-navigator-api-service` (2 tasks)
  - `health-navigator-streamlit-service` (2 tasks)

### Load Balancers
- **API ALB**: Routes traffic to FastAPI containers (port 8000)
- **Streamlit ALB**: Routes traffic to Streamlit containers (port 8501)

### Security
- VPC with public subnets
- Security groups limiting access
- Non-root container users
- IAM roles with minimal permissions

## Cost Estimation

| Resource | Estimate (monthly) |
|----------|-------------------|
| ECS Fargate (4 tasks, 0.5 vCPU, 1GB) | ~$50 |
| ALB (2 load balancers) | ~$35 |
| ECR Storage | ~$1 |
| CloudWatch Logs | ~$5 |
| **Total** | **~$90/month** |

*Note: MongoDB Atlas and Pinecone costs are separate.*

## Scaling

### Manual Scaling
```bash
aws ecs update-service \
  --cluster health-navigator-cluster \
  --service health-navigator-streamlit-service \
  --desired-count 4
```

### Auto Scaling (Optional)
Add to CloudFormation template:
```yaml
ScalingTarget:
  Type: AWS::ApplicationAutoScaling::ScalableTarget
  Properties:
    MaxCapacity: 10
    MinCapacity: 2
    ResourceId: !Sub 'service/${ECSCluster}/${StreamlitService}'
    ScalableDimension: ecs:service:DesiredCount
    ServiceNamespace: ecs

ScalingPolicy:
  Type: AWS::ApplicationAutoScaling::ScalingPolicy
  Properties:
    PolicyName: cpu-scaling
    PolicyType: TargetTrackingScaling
    ScalingTargetId: !Ref ScalingTarget
    TargetTrackingScalingPolicyConfiguration:
      PredefinedMetricSpecification:
        PredefinedMetricType: ECSServiceAverageCPUUtilization
      TargetValue: 70
```

## Monitoring

### CloudWatch Logs
```bash
# View Streamlit logs
./deploy.sh logs streamlit

# View API logs
./deploy.sh logs api
```

### CloudWatch Metrics
- CPU/Memory utilization
- Request count
- Response times
- Error rates

## Troubleshooting

### Container Not Starting
```bash
# Check task status
aws ecs describe-tasks \
  --cluster health-navigator-cluster \
  --tasks $(aws ecs list-tasks --cluster health-navigator-cluster --query 'taskArns[0]' --output text)
```

### Health Check Failures
1. Verify MongoDB URI is correct
2. Check Pinecone API key
3. Review CloudWatch logs for errors

### Connection Issues
1. Verify security group rules
2. Check VPC configuration
3. Ensure MongoDB Atlas allows AWS IP ranges

## Alternative: AWS App Runner

For simpler deployment without managing infrastructure:

```bash
# Configure App Runner
aws apprunner create-service \
  --service-name health-navigator \
  --source-configuration file://aws/apprunner-config.json
```

## Cleanup

```bash
# Delete all AWS resources
./deploy.sh destroy

# Delete ECR images (optional)
aws ecr delete-repository --repository-name health-navigator-api --force
aws ecr delete-repository --repository-name health-navigator-streamlit --force
```
