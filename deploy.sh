#!/bin/bash
# AI Health Navigator - AWS Deployment Script
# This script builds and deploys the application to AWS ECS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default values
AWS_REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="${STACK_NAME:-health-navigator}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AI Health Navigator - AWS Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Check required environment variables
check_env() {
    local var_name=$1
    if [ -z "${!var_name}" ]; then
        echo -e "${RED}Error: $var_name is not set${NC}"
        exit 1
    fi
}

# Function to display usage
usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  build       Build Docker images locally"
    echo "  push        Push images to ECR"
    echo "  deploy      Deploy CloudFormation stack"
    echo "  update      Update existing deployment"
    echo "  status      Check deployment status"
    echo "  logs        View application logs"
    echo "  destroy     Delete the CloudFormation stack"
    echo "  local       Run locally with docker-compose"
    echo ""
}

# Build Docker images
build_images() {
    echo -e "${YELLOW}Building Docker images...${NC}"

    docker build -f Dockerfile.api -t health-navigator-api:latest .
    docker build -f Dockerfile.streamlit -t health-navigator-streamlit:latest .

    echo -e "${GREEN}Images built successfully!${NC}"
}

# Create ECR repositories if they don't exist
create_ecr_repos() {
    echo -e "${YELLOW}Creating ECR repositories...${NC}"

    aws ecr describe-repositories --repository-names health-navigator-api --region $AWS_REGION 2>/dev/null || \
        aws ecr create-repository --repository-name health-navigator-api --region $AWS_REGION

    aws ecr describe-repositories --repository-names health-navigator-streamlit --region $AWS_REGION 2>/dev/null || \
        aws ecr create-repository --repository-name health-navigator-streamlit --region $AWS_REGION

    echo -e "${GREEN}ECR repositories ready!${NC}"
}

# Push images to ECR
push_images() {
    check_env "AWS_ACCOUNT_ID"

    ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

    echo -e "${YELLOW}Logging into ECR...${NC}"
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

    create_ecr_repos

    echo -e "${YELLOW}Tagging and pushing images...${NC}"

    # Tag and push API image
    docker tag health-navigator-api:latest ${ECR_REGISTRY}/health-navigator-api:latest
    docker push ${ECR_REGISTRY}/health-navigator-api:latest

    # Tag and push Streamlit image
    docker tag health-navigator-streamlit:latest ${ECR_REGISTRY}/health-navigator-streamlit:latest
    docker push ${ECR_REGISTRY}/health-navigator-streamlit:latest

    echo -e "${GREEN}Images pushed to ECR!${NC}"

    # Export URIs for CloudFormation
    export API_IMAGE_URI="${ECR_REGISTRY}/health-navigator-api:latest"
    export STREAMLIT_IMAGE_URI="${ECR_REGISTRY}/health-navigator-streamlit:latest"
}

# Deploy CloudFormation stack
deploy_stack() {
    check_env "AWS_ACCOUNT_ID"
    check_env "MONGODB_URI"
    check_env "PINECONE_API_KEY"

    ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    API_IMAGE_URI="${ECR_REGISTRY}/health-navigator-api:latest"
    STREAMLIT_IMAGE_URI="${ECR_REGISTRY}/health-navigator-streamlit:latest"

    echo -e "${YELLOW}Deploying CloudFormation stack: ${STACK_NAME}...${NC}"

    aws cloudformation deploy \
        --template-file aws/cloudformation.yaml \
        --stack-name $STACK_NAME \
        --parameter-overrides \
            Environment=production \
            MongoDBUri="$MONGODB_URI" \
            PineconeApiKey="$PINECONE_API_KEY" \
            ApiImageUri="$API_IMAGE_URI" \
            StreamlitImageUri="$STREAMLIT_IMAGE_URI" \
        --capabilities CAPABILITY_IAM \
        --region $AWS_REGION

    echo -e "${GREEN}Stack deployed successfully!${NC}"

    # Get outputs
    echo -e "${YELLOW}Getting stack outputs...${NC}"
    aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].Outputs' \
        --output table \
        --region $AWS_REGION
}

# Update existing deployment
update_deployment() {
    echo -e "${YELLOW}Updating deployment...${NC}"

    build_images
    push_images

    # Force new deployment
    aws ecs update-service \
        --cluster ${STACK_NAME}-cluster \
        --service ${STACK_NAME}-api-service \
        --force-new-deployment \
        --region $AWS_REGION

    aws ecs update-service \
        --cluster ${STACK_NAME}-cluster \
        --service ${STACK_NAME}-streamlit-service \
        --force-new-deployment \
        --region $AWS_REGION

    echo -e "${GREEN}Deployment update initiated!${NC}"
}

# Check deployment status
check_status() {
    echo -e "${YELLOW}Checking deployment status...${NC}"

    echo -e "\n${GREEN}CloudFormation Stack Status:${NC}"
    aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].StackStatus' \
        --output text \
        --region $AWS_REGION 2>/dev/null || echo "Stack not found"

    echo -e "\n${GREEN}ECS Services:${NC}"
    aws ecs describe-services \
        --cluster ${STACK_NAME}-cluster \
        --services ${STACK_NAME}-api-service ${STACK_NAME}-streamlit-service \
        --query 'services[*].{Name:serviceName,Status:status,Running:runningCount,Desired:desiredCount}' \
        --output table \
        --region $AWS_REGION 2>/dev/null || echo "Services not found"

    echo -e "\n${GREEN}Application URLs:${NC}"
    aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].Outputs[*].{Key:OutputKey,Value:OutputValue}' \
        --output table \
        --region $AWS_REGION 2>/dev/null || echo "Stack outputs not available"
}

# View logs
view_logs() {
    local service="${1:-streamlit}"

    echo -e "${YELLOW}Fetching logs for ${service}...${NC}"

    aws logs tail /ecs/${STACK_NAME}/${service} \
        --follow \
        --region $AWS_REGION
}

# Destroy stack
destroy_stack() {
    echo -e "${RED}WARNING: This will delete all resources!${NC}"
    read -p "Are you sure? (yes/no): " confirm

    if [ "$confirm" = "yes" ]; then
        echo -e "${YELLOW}Deleting CloudFormation stack...${NC}"
        aws cloudformation delete-stack --stack-name $STACK_NAME --region $AWS_REGION

        echo -e "${YELLOW}Waiting for stack deletion...${NC}"
        aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME --region $AWS_REGION

        echo -e "${GREEN}Stack deleted!${NC}"
    else
        echo "Cancelled."
    fi
}

# Run locally with docker-compose
run_local() {
    echo -e "${YELLOW}Starting local environment with docker-compose...${NC}"
    docker-compose up --build
}

# Main command handler
case "${1:-}" in
    build)
        build_images
        ;;
    push)
        build_images
        push_images
        ;;
    deploy)
        build_images
        push_images
        deploy_stack
        ;;
    update)
        update_deployment
        ;;
    status)
        check_status
        ;;
    logs)
        view_logs "${2:-streamlit}"
        ;;
    destroy)
        destroy_stack
        ;;
    local)
        run_local
        ;;
    *)
        usage
        ;;
esac
