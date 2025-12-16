#!/bin/bash
# Integration test: Validate Pulumi preview and idempotence for Jenkins ECS agent image stack.
# Covers INT-ECS-IMG-013 (pulumi preview) and INT-ECS-IMG-014 (idempotent pulumi up).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
source "${ROOT_DIR}/tests/integration/ecs-image/helpers.sh"

PULUMI_DIR="${ROOT_DIR}/pulumi/jenkins-agent-ecs-image"
ENVIRONMENT="${ENVIRONMENT:-dev}"
PULUMI_STACK="${PULUMI_STACK:-$ENVIRONMENT}"

ensure_requirements() {
  require_cmd pulumi
  require_cmd npm
  require_cmd jq
}

install_node_modules() {
  if [ ! -d "$PULUMI_DIR" ]; then
    log_error "Pulumi directory not found: ${PULUMI_DIR}"
    return 1
  fi

  if [ -d "${PULUMI_DIR}/node_modules" ]; then
    log_info "node_modules already present; skipping npm install"
    return 0
  fi

  log_info "Installing npm dependencies in ${PULUMI_DIR}"
  if ! (cd "$PULUMI_DIR" && npm install); then
    log_error "npm install failed in ${PULUMI_DIR}"
    return 1
  fi
}

select_stack() {
  log_info "Selecting Pulumi stack ${PULUMI_STACK}"
  if ! (cd "$PULUMI_DIR" && pulumi stack select "$PULUMI_STACK" --non-interactive); then
    log_error "Pulumi stack selection failed for ${PULUMI_STACK}"
    return 1
  fi
}

test_pulumi_preview() {
  log_section "INT-ECS-IMG-013: Pulumi preview executes without errors"
  local preview_json resource_types types_joined failed=0

  if ! preview_json=$(cd "$PULUMI_DIR" && pulumi preview --stack "$PULUMI_STACK" --non-interactive --json); then
    log_error "pulumi preview failed for stack ${PULUMI_STACK}"
    return 1
  fi

  resource_types=$(echo "$preview_json" | jq -r '
    select(.sequenceEventType=="resource-pre" or .sequenceEventType=="resource-change")
    | (.resourcePre.type // .resourceChange.resourceType // .resourceChange.type // empty)
  ' | sort -u)

  # If the stack is already up-to-date, preview may show no planned changes; fall back to current URNs.
  if [ -z "$resource_types" ]; then
    resource_types=$(cd "$PULUMI_DIR" && pulumi stack --stack "$PULUMI_STACK" --show-urns \
      | awk -F:: '/^urn:/{print $(NF-1)}' | sort -u)
  fi

  if [ -z "$resource_types" ]; then
    log_error "No resources detected from pulumi preview or existing stack state"
    return 1
  fi

  types_joined=$(echo "$resource_types" | tr '\n' ' ')
  log_info "Detected Pulumi resource types: ${types_joined}"

  for expected in \
    "aws:imagebuilder/component:Component" \
    "aws:imagebuilder/containerRecipe:ContainerRecipe" \
    "aws:imagebuilder/infrastructureConfiguration:InfrastructureConfiguration" \
    "aws:imagebuilder/distributionConfiguration:DistributionConfiguration" \
    "aws:imagebuilder/imagePipeline:ImagePipeline" \
    "aws:iam/role:Role" \
    "aws:iam/instanceProfile:InstanceProfile" \
    "aws:ssm/parameter:Parameter"; do
    assert_contains "$types_joined" "$expected" "Missing expected resource type in preview/stack" || failed=1
  done

  return $failed
}

test_pulumi_idempotence() {
  log_section "INT-ECS-IMG-014: Pulumi stack is idempotent"
  local second_output

  log_info "Running first pulumi up --yes --skip-preview"
  if ! (cd "$PULUMI_DIR" && pulumi up --stack "$PULUMI_STACK" --yes --non-interactive --skip-preview); then
    log_error "Initial pulumi up failed for stack ${PULUMI_STACK}"
    return 1
  fi

  log_info "Running second pulumi up to confirm no changes"
  if ! second_output=$(cd "$PULUMI_DIR" && pulumi up --stack "$PULUMI_STACK" --yes --non-interactive --skip-preview 2>&1); then
    log_error "Second pulumi up failed for stack ${PULUMI_STACK}"
    return 1
  fi

  if ! echo "$second_output" | grep -qi "no changes"; then
    log_error "Second pulumi up did not report 'no changes'"
    return 1
  fi

  log_info "Pulumi up reported no changes on the second run"
  return 0
}

main() {
  ensure_requirements
  install_node_modules
  select_stack

  init_summary

  echo "=============================================="
  echo "Pulumi validation for ECS agent image stack"
  echo "Environment/Stack: ${PULUMI_STACK}"
  echo "Pulumi dir: ${PULUMI_DIR}"
  echo "=============================================="

  run_test "INT-ECS-IMG-013 Pulumi preview" test_pulumi_preview
  run_test "INT-ECS-IMG-014 Pulumi idempotence" test_pulumi_idempotence

  echo
  echo "=============================================="
  echo "Test summary: ${PASSED}/${TOTAL} passed, ${FAILED} failed"
  echo "=============================================="

  if [ "$FAILED" -ne 0 ]; then
    exit 1
  fi
}

main "$@"
