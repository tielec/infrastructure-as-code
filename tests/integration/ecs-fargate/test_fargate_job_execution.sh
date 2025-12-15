#!/bin/bash
# Integration test: Validate ECS agent image availability and Jenkins job execution on ecs-agent label.
# Confirms ECR repository has a latest tag, keeps ec2-fleet label intact for coexistence,
# and optionally runs a smoke pipeline on Jenkins when credentials are supplied.

set -euo pipefail

ENVIRONMENT="${ENVIRONMENT:-dev}"
AWS_REGION="${AWS_REGION:-ap-northeast-1}"
SSM_PREFIX="/jenkins-infra/${ENVIRONMENT}"
AGENT_LABEL="${AGENT_LABEL:-ecs-agent}"
JOB_TIMEOUT_MINUTES="${JOB_TIMEOUT_MINUTES:-15}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TEMPLATE_FILE="${ROOT_DIR}/scripts/jenkins/casc/jenkins.yaml.template"

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

log "=== INT-JOB: ECS agent image and job execution validation (${ENVIRONMENT}) ==="

# Coexistence check: ec2-fleet label must remain in JCasC template
if ! grep -q 'labelString: "ec2-fleet"' "$TEMPLATE_FILE"; then
  log "ERROR: ec2-fleet label missing from ${TEMPLATE_FILE} (Spot Fleet coexistence broken)"
  exit 1
fi
log "ec2-fleet label still defined in JCasC template"

# ECR image availability (ensures latest image exists before running jobs)
ECR_REPOSITORY_URL=$(fetch_param "${SSM_PREFIX}/agent/ecr-repository-url" "ECR Repository URL")
REPOSITORY_NAME=$(echo "$ECR_REPOSITORY_URL" | cut -d'/' -f2-)

log "Checking ECR image availability for ${REPOSITORY_NAME}..."
LATEST_COUNT=$(aws ecr describe-images \
  --repository-name "$REPOSITORY_NAME" \
  --region "$AWS_REGION" \
  --query "length(imageDetails[?contains(imageTags, \`latest\`)])" \
  --output text)

if [ "$LATEST_COUNT" -lt 1 ]; then
  log "ERROR: No image with tag 'latest' found in ${REPOSITORY_NAME}"
  exit 1
fi
log "ECR repository contains at least one 'latest' image"

# Optional Jenkins smoke job (requires credentials)
if [[ -n "${JENKINS_URL:-}" && -n "${JENKINS_USER:-}" && -n "${JENKINS_TOKEN:-}" ]]; then
  require_cmd curl

  BASE_URL="${JENKINS_URL%/}"
  JOB_NAME="ecs-agent-smoke-$(date +%s)"

  log "Running Jenkins smoke job ${JOB_NAME} on label ${AGENT_LABEL}..."

  # Obtain crumb for CSRF protection
  CRUMB_JSON=$(curl -sf -u "${JENKINS_USER}:${JENKINS_TOKEN}" "${BASE_URL}/crumbIssuer/api/json")
  CRUMB=$(echo "$CRUMB_JSON" | jq -r '.crumb')
  CRUMB_FIELD=$(echo "$CRUMB_JSON" | jq -r '.crumbRequestField')

  # Create a temporary pipeline job pinned to ecs-agent label
  cat <<EOF | curl -sf -u "${JENKINS_USER}:${JENKINS_TOKEN}" \
    -H "${CRUMB_FIELD}: ${CRUMB}" \
    -H "Content-Type: application/xml" \
    --data-binary @- \
    "${BASE_URL}/createItem?name=${JOB_NAME}"
<flow-definition plugin="workflow-job">
  <description>Smoke test for ECS Fargate agent connectivity</description>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps">
    <script>pipeline {
      agent { label '${AGENT_LABEL}' }
      options { timeout(time: ${JOB_TIMEOUT_MINUTES}, unit: 'MINUTES') }
      stages {
        stage('Smoke') {
          steps {
            echo 'ECS agent smoke test'
            sh 'uname -a'
          }
        }
      }
    }</script>
    <sandbox>true</sandbox>
  </definition>
  <triggers/>
  <disabled>false</disabled>
</flow-definition>
EOF

  # Trigger the job
  curl -sf -u "${JENKINS_USER}:${JENKINS_TOKEN}" \
    -H "${CRUMB_FIELD}: ${CRUMB}" \
    -X POST "${BASE_URL}/job/${JOB_NAME}/build" >/dev/null

  # Wait for build number assignment
  BUILD_NUMBER=""
  for _ in $(seq 1 30); do
    BUILD_NUMBER=$(curl -sf -u "${JENKINS_USER}:${JENKINS_TOKEN}" \
      "${BASE_URL}/job/${JOB_NAME}/api/json" | jq -r '.lastBuild.number // empty')
    [ -n "$BUILD_NUMBER" ] && break
    sleep 5
  done

  if [ -z "$BUILD_NUMBER" ]; then
    log "ERROR: Build did not start for ${JOB_NAME}"
    exit 1
  fi

  # Poll until build finishes or timeout reached
  RESULT=""
  for _ in $(seq 1 60); do
    BUILD_JSON=$(curl -sf -u "${JENKINS_USER}:${JENKINS_TOKEN}" \
      "${BASE_URL}/job/${JOB_NAME}/lastBuild/api/json")
    BUILDING=$(echo "$BUILD_JSON" | jq -r '.building')
    RESULT=$(echo "$BUILD_JSON" | jq -r '.result // empty')
    BUILT_ON=$(echo "$BUILD_JSON" | jq -r '.builtOn // empty')

    if [ "$BUILDING" = "false" ] && [ -n "$RESULT" ]; then
      break
    fi
    sleep 10
  done

  if [ "$RESULT" != "SUCCESS" ]; then
    log "ERROR: Jenkins smoke job failed (result=${RESULT:-unknown})"
    # Cleanup even on failure
    curl -sf -u "${JENKINS_USER}:${JENKINS_TOKEN}" \
      -H "${CRUMB_FIELD}: ${CRUMB}" \
      -X POST "${BASE_URL}/job/${JOB_NAME}/doDelete" >/dev/null || true
    exit 1
  fi

  log "Jenkins smoke job succeeded on node ${BUILT_ON:-unknown}"

  # Cleanup job
  curl -sf -u "${JENKINS_USER}:${JENKINS_TOKEN}" \
    -H "${CRUMB_FIELD}: ${CRUMB}" \
    -X POST "${BASE_URL}/job/${JOB_NAME}/doDelete" >/dev/null || true
else
  log "Skipping Jenkins smoke job (JENKINS_URL/JENKINS_USER/JENKINS_TOKEN not set)"
fi

log "ECS agent job execution checks completed successfully."
