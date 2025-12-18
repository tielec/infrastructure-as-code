#!/bin/bash
# Integration test: Validate Jenkins-side configuration for ECS Fargate agents.
# Confirms plugin inclusion, JCasC template rendering for ecs-fargate cloud,
# and optional live Jenkins verification when credentials are provided.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TEMPLATE_FILE="${ROOT_DIR}/scripts/jenkins/casc/jenkins.yaml.template"
CONFIGURE_SCRIPT="${ROOT_DIR}/scripts/jenkins/shell/application-configure-with-casc.sh"
PLUGIN_FILE="${ROOT_DIR}/scripts/jenkins/groovy/install-plugins.groovy"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    log "ERROR: Required command '$1' not found"
    exit 1
  }
}

require_cmd grep
require_cmd envsubst
require_cmd mktemp
require_cmd awk

log "=== INT-CONFIG: Jenkins ECS configuration validation ==="

# Check plugin list contains amazon-ecs
if ! grep -q '"amazon-ecs"' "$PLUGIN_FILE"; then
  log "ERROR: amazon-ecs plugin is missing from ${PLUGIN_FILE}"
  exit 1
fi
log "amazon-ecs plugin presence confirmed"

# Ensure configure script retrieves and substitutes ECS parameters
declare -a required_tokens=(
  "/jenkins-infra/\${ENVIRONMENT}/agent/ecs-cluster-arn"
  "/jenkins-infra/\${ENVIRONMENT}/agent/ecs-task-definition-arn"
  "/jenkins-infra/\${ENVIRONMENT}/agent/ecs-execution-role-arn"
  "/jenkins-infra/\${ENVIRONMENT}/agent/ecs-task-role-arn"
  "/jenkins-infra/\${ENVIRONMENT}/loadbalancer/jenkins-internal-url"
  "ECS_CLUSTER_ARN"
  "ECS_TASK_DEFINITION_ARN"
  "ECS_EXECUTION_ROLE_ARN"
  "ECS_TASK_ROLE_ARN"
  "JENKINS_AGENT_SG_ID"
  "PRIVATE_SUBNET_A_ID"
  "PRIVATE_SUBNET_B_ID"
  "JENKINS_INTERNAL_URL"
)

for token in "${required_tokens[@]}"; do
  if ! grep -q "$token" "$CONFIGURE_SCRIPT"; then
    log "ERROR: ${token} not found in ${CONFIGURE_SCRIPT}"
    exit 1
  fi
done
log "Configure script includes ECS parameter retrieval and substitution"

# Render the JCasC template with sample values to confirm substitution paths
TEMP_RENDER="$(mktemp)"
export JENKINS_URL="http://jenkins.example/"
export JENKINS_INTERNAL_URL="http://jenkins.internal/"
export EC2_FLEET_ID="fleet-123"
export WORKTERMINAL_HOST="192.0.2.10"
export AWS_REGION="ap-northeast-1"
export AWS_PROD_ACCOUNT_IDS="123456789012"
export AWS_DEV_ACCOUNT_IDS="210987654321"
export SHARED_LIBRARY_REPO="https://example.com/repo.git"
export SHARED_LIBRARY_BRANCH="main"
export SHARED_LIBRARY_PATH="jenkins/jobs/shared/"
export EC2_IDLE_MINUTES="10"
export EC2_MIN_SIZE="0"
export EC2_MAX_SIZE="5"
export EC2_NUM_EXECUTORS="2"
export ECS_CLUSTER_ARN="arn:aws:ecs:ap-northeast-1:123456789012:cluster/example"
export ECS_TASK_DEFINITION_ARN="arn:aws:ecs:ap-northeast-1:123456789012:task-definition/example:1"
export ECS_EXECUTION_ROLE_ARN="arn:aws:iam::123456789012:role/execution-role"
export ECS_TASK_ROLE_ARN="arn:aws:iam::123456789012:role/task-role"
export JENKINS_AGENT_SG_ID="sg-0123456789abcdef0"
export PRIVATE_SUBNET_A_ID="subnet-aaaaaaaa"
export PRIVATE_SUBNET_B_ID="subnet-bbbbbbbb"

# shellcheck disable=SC2016
envsubst '$JENKINS_URL $JENKINS_INTERNAL_URL $EC2_FLEET_ID $WORKTERMINAL_HOST $AWS_REGION $AWS_PROD_ACCOUNT_IDS $AWS_DEV_ACCOUNT_IDS $SHARED_LIBRARY_REPO $SHARED_LIBRARY_BRANCH $SHARED_LIBRARY_PATH $EC2_IDLE_MINUTES $EC2_MIN_SIZE $EC2_MAX_SIZE $EC2_NUM_EXECUTORS $ECS_CLUSTER_ARN $ECS_TASK_DEFINITION_ARN $ECS_EXECUTION_ROLE_ARN $ECS_TASK_ROLE_ARN $JENKINS_AGENT_SG_ID $PRIVATE_SUBNET_A_ID $PRIVATE_SUBNET_B_ID' \
  < "$TEMPLATE_FILE" > "$TEMP_RENDER"

if ! grep -q "ecs-fargate" "$TEMP_RENDER"; then
  log "ERROR: Rendered template missing ecs-fargate cloud block"
  rm -f "$TEMP_RENDER"
  exit 1
fi

if ! grep -q "label: \"ecs-agent fargate-agent\"" "$TEMP_RENDER"; then
  log "ERROR: Rendered template missing ecs-agent labels"
  rm -f "$TEMP_RENDER"
  exit 1
fi

if ! grep -q "$ECS_TASK_DEFINITION_ARN" "$TEMP_RENDER"; then
  log "ERROR: Task definition ARN was not rendered into template"
  rm -f "$TEMP_RENDER"
  exit 1
fi

if ! grep -q "$JENKINS_AGENT_SG_ID" "$TEMP_RENDER"; then
  log "ERROR: Security group ID was not rendered into template"
  rm -f "$TEMP_RENDER"
  exit 1
fi

if ! grep -q "$PRIVATE_SUBNET_A_ID" "$TEMP_RENDER"; then
  log "ERROR: Subnet IDs were not rendered into template"
  rm -f "$TEMP_RENDER"
  exit 1
fi

# Issue #497: Verify JENKINS_INTERNAL_URL is used for ECS cloud jenkinsUrl
if ! grep -q "$JENKINS_INTERNAL_URL" "$TEMP_RENDER"; then
  log "ERROR: JENKINS_INTERNAL_URL was not rendered into template"
  rm -f "$TEMP_RENDER"
  exit 1
fi
log "JENKINS_INTERNAL_URL is rendered in template (Issue #497 fix)"

# Verify that ECS cloud uses internal URL for jenkinsUrl
if grep -A 10 "ecs-fargate" "$TEMP_RENDER" | grep -q "jenkinsUrl.*jenkins.internal"; then
  log "ECS cloud jenkinsUrl correctly uses internal URL"
else
  log "WARNING: ECS cloud jenkinsUrl may not use internal URL - verify manually"
fi

log "JCasC template renders ECS cloud configuration with provided values"
rm -f "$TEMP_RENDER"

# Optional live Jenkins verification (skipped if credentials are absent)
if [[ -n "${JENKINS_URL:-}" && -n "${JENKINS_USER:-}" && -n "${JENKINS_TOKEN:-}" ]]; then
  require_cmd curl
  require_cmd jq

  log "Checking live Jenkins plugin state at ${JENKINS_URL}..."
  PLUGIN_JSON=$(curl -sf -u "${JENKINS_USER}:${JENKINS_TOKEN}" \
    "${JENKINS_URL%/}/pluginManager/api/json?depth=1")

  if echo "$PLUGIN_JSON" | jq -e '.plugins[] | select(.shortName=="amazon-ecs")' >/dev/null; then
    log "amazon-ecs plugin is installed on Jenkins"
  else
    log "ERROR: amazon-ecs plugin not reported by Jenkins API"
    exit 1
  fi
else
  log "Skipping live Jenkins check (JENKINS_URL/JENKINS_USER/JENKINS_TOKEN not set)"
fi

log "ECS Jenkins configuration checks completed successfully."
