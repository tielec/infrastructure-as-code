#!/bin/bash
# Integration test: Validate ECS Fargate resources created for Jenkins agents.
# Verifies SSM outputs, ECS cluster status, ECR repository settings, task definition,
# IAM roles, and CloudWatch Logs retention to ensure Pulumi stack deployed correctly.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENVIRONMENT="${ENVIRONMENT:-dev}"
AWS_REGION="${AWS_REGION:-ap-northeast-1}"
SSM_PREFIX="/jenkins-infra/${ENVIRONMENT}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    log "ERROR: Required command '$1' not found"
    exit 1
  }
}

fetch_param() {
  local name="$1"
  local description="$2"
  local value

  value=$(aws ssm get-parameter \
    --name "$name" \
    --region "$AWS_REGION" \
    --query "Parameter.Value" \
    --output text 2>/dev/null || true)

  if [ -z "$value" ] || [ "$value" = "None" ]; then
    log "ERROR: Missing $description at $name"
    exit 1
  fi

  echo "$value"
}

require_cmd aws
require_cmd jq

log "=== INT-DEPLOY: ECS Fargate deployment validation (${ENVIRONMENT}) ==="

# Retrieve mandatory SSM parameters (fail fast if any are absent)
ECS_CLUSTER_ARN=$(fetch_param "${SSM_PREFIX}/agent/ecs-cluster-arn" "ECS Cluster ARN")
ECS_CLUSTER_NAME=$(fetch_param "${SSM_PREFIX}/agent/ecs-cluster-name" "ECS Cluster Name")
ECS_TASK_DEFINITION_ARN=$(fetch_param "${SSM_PREFIX}/agent/ecs-task-definition-arn" "Task Definition ARN")
ECS_EXECUTION_ROLE_ARN=$(fetch_param "${SSM_PREFIX}/agent/ecs-execution-role-arn" "Execution Role ARN")
ECS_TASK_ROLE_ARN=$(fetch_param "${SSM_PREFIX}/agent/ecs-task-role-arn" "Task Role ARN")
ECS_LOG_GROUP_NAME=$(fetch_param "${SSM_PREFIX}/agent/ecs-log-group-name" "Log Group Name")
ECR_REPOSITORY_URL=$(fetch_param "${SSM_PREFIX}/agent/ecr-repository-url" "ECR Repository URL")

log "SSM parameters retrieved successfully"

# ECS Cluster checks
log "Checking ECS Cluster status..."
CLUSTER_JSON=$(aws ecs describe-clusters \
  --clusters "$ECS_CLUSTER_ARN" \
  --region "$AWS_REGION" \
  --query "clusters[0]" \
  --output json)

CLUSTER_STATUS=$(echo "$CLUSTER_JSON" | jq -r '.status')
if [ "$CLUSTER_STATUS" != "ACTIVE" ]; then
  log "ERROR: ECS Cluster is not ACTIVE (current: $CLUSTER_STATUS)"
  exit 1
fi

INSIGHTS=$(echo "$CLUSTER_JSON" | jq -r '.settings[] | select(.name=="containerInsights") | .value')
if [ "$INSIGHTS" != "enabled" ]; then
  log "ERROR: Container Insights is not enabled on the cluster"
  exit 1
fi
log "ECS Cluster status ACTIVE with Container Insights enabled"

# ECR Repository checks
REPOSITORY_NAME=$(echo "$ECR_REPOSITORY_URL" | cut -d'/' -f2-)
log "Validating ECR repository ${REPOSITORY_NAME}..."

REPO_JSON=$(aws ecr describe-repositories \
  --repository-names "$REPOSITORY_NAME" \
  --region "$AWS_REGION" \
  --query "repositories[0]" \
  --output json 2>/dev/null || true)

if [ -z "$REPO_JSON" ] || [ "$REPO_JSON" = "null" ]; then
  log "ERROR: ECR repository ${REPOSITORY_NAME} not found"
  exit 1
fi

SCAN_ON_PUSH=$(echo "$REPO_JSON" | jq -r '.imageScanningConfiguration.scanOnPush')
if [ "$SCAN_ON_PUSH" != "true" ]; then
  log "ERROR: ECR scanOnPush is not enabled"
  exit 1
fi

# Lifecycle policy presence check
if ! aws ecr get-lifecycle-policy \
  --repository-name "$REPOSITORY_NAME" \
  --region "$AWS_REGION" \
  --query 'lifecyclePolicyText' \
  --output text >/dev/null; then
  log "ERROR: ECR lifecycle policy is missing"
  exit 1
fi
log "ECR repository verified (scanOnPush enabled, lifecycle policy present)"

# Task Definition checks
log "Validating task definition ${ECS_TASK_DEFINITION_ARN}..."
TASK_JSON=$(aws ecs describe-task-definition \
  --task-definition "$ECS_TASK_DEFINITION_ARN" \
  --region "$AWS_REGION" \
  --output json)

CPU=$(echo "$TASK_JSON" | jq -r '.taskDefinition.cpu')
MEMORY=$(echo "$TASK_JSON" | jq -r '.taskDefinition.memory')
NETWORK_MODE=$(echo "$TASK_JSON" | jq -r '.taskDefinition.networkMode')
REQUIRES_FARGATE=$(echo "$TASK_JSON" | jq -r '[.taskDefinition.requiresCompatibilities[] | select(.=="FARGATE")] | length')

if [ "$CPU" != "512" ] || [ "$MEMORY" != "1024" ]; then
  log "ERROR: Task definition cpu/memory mismatch (cpu=${CPU}, memory=${MEMORY})"
  exit 1
fi

if [ "$NETWORK_MODE" != "awsvpc" ] || [ "$REQUIRES_FARGATE" -eq 0 ]; then
  log "ERROR: Task definition must target FARGATE with awsvpc network mode"
  exit 1
fi

CONTAINER_IMAGE=$(echo "$TASK_JSON" | jq -r '.taskDefinition.containerDefinitions[0].image')
if [[ "$CONTAINER_IMAGE" != "${ECR_REPOSITORY_URL}:latest" ]]; then
  log "ERROR: Container image does not point to ECR latest tag (${CONTAINER_IMAGE})"
  exit 1
fi

TASK_LOG_GROUP=$(echo "$TASK_JSON" | jq -r '.taskDefinition.containerDefinitions[0].logConfiguration.options["awslogs-group"]')
if [ "$TASK_LOG_GROUP" != "$ECS_LOG_GROUP_NAME" ]; then
  log "ERROR: Log group mismatch in task definition (${TASK_LOG_GROUP} != ${ECS_LOG_GROUP_NAME})"
  exit 1
fi
log "Task definition configuration verified (cpu/memory/network/logs/image)"

# IAM Role checks
log "Validating IAM execution role attachments..."
EXEC_POLICIES=$(aws iam list-attached-role-policies \
  --role-name "$(basename "$ECS_EXECUTION_ROLE_ARN")" \
  --query 'AttachedPolicies[].PolicyArn' \
  --output text)

if ! echo "$EXEC_POLICIES" | grep -q "AmazonECSTaskExecutionRolePolicy"; then
  log "ERROR: AmazonECSTaskExecutionRolePolicy is not attached to execution role"
  exit 1
fi

TRUST_EXEC=$(aws iam get-role --role-name "$(basename "$ECS_EXECUTION_ROLE_ARN")" --query 'Role.AssumeRolePolicyDocument.Statement[0].Principal.Service' --output text)
if [[ "$TRUST_EXEC" != *"ecs-tasks.amazonaws.com"* ]]; then
  log "ERROR: Execution role trust policy is not scoped to ecs-tasks.amazonaws.com"
  exit 1
fi

TRUST_TASK=$(aws iam get-role --role-name "$(basename "$ECS_TASK_ROLE_ARN")" --query 'Role.AssumeRolePolicyDocument.Statement[0].Principal.Service' --output text)
if [[ "$TRUST_TASK" != *"ecs-tasks.amazonaws.com"* ]]; then
  log "ERROR: Task role trust policy is not scoped to ecs-tasks.amazonaws.com"
  exit 1
fi
log "IAM roles verified (trust policies and execution policy attachment)"

# CloudWatch Logs retention check
log "Checking CloudWatch Logs retention..."
RETENTION=$(aws logs describe-log-groups \
  --log-group-name-prefix "$ECS_LOG_GROUP_NAME" \
  --region "$AWS_REGION" \
  --query "logGroups[?logGroupName=='${ECS_LOG_GROUP_NAME}'].retentionInDays | [0]" \
  --output text)

if [ "$RETENTION" != "30" ]; then
  log "ERROR: Log group retention is not 30 days (current: ${RETENTION})"
  exit 1
fi

log "All ECS Fargate deployment checks passed."
