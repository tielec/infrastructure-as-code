#!/bin/bash
# Integration test: Validate EC2 Image Builder resources for Jenkins ECS agent image (Issue #496).
# Covers SSM outputs, pipeline status, container recipe, distribution configuration,
# infrastructure configuration, and IAM policy attachments to ensure the Pulumi stack deployed correctly.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
source "${ROOT_DIR}/tests/integration/ecs-image/helpers.sh"

ENVIRONMENT="${ENVIRONMENT:-dev}"
AWS_REGION="${AWS_REGION:-ap-northeast-1}"
SSM_PREFIX="/jenkins-infra/${ENVIRONMENT}"

PIPELINE_ARN=""
COMPONENT_VERSION=""
RECIPE_VERSION=""
ECR_REPOSITORY_URL=""
CONTAINER_RECIPE_ARN=""
DISTRIBUTION_CONFIG_ARN=""
INFRA_CONFIG_ARN=""
COMPONENT_ARN=""
SUBNET_ID=""
SECURITY_GROUP_ID=""
INSTANCE_PROFILE_ROLE=""

test_ssm_parameters_exist() {
  log_section "INT-ECS-IMG-001: SSM parameter presence and format"
  local failed=0

  PIPELINE_ARN=$(fetch_param "${SSM_PREFIX}/agent-ecs-image/pipeline-arn" "pipeline ARN") || failed=1
  COMPONENT_VERSION=$(fetch_param "${SSM_PREFIX}/agent-ecs-image/component-version" "component version") || failed=1
  RECIPE_VERSION=$(fetch_param "${SSM_PREFIX}/agent-ecs-image/recipe-version" "recipe version") || failed=1
  ECR_REPOSITORY_URL=$(fetch_param "${SSM_PREFIX}/agent/ecr-repository-url" "ECR repository URL") || failed=1
  SUBNET_ID=$(fetch_param "${SSM_PREFIX}/network/public-subnet-a-id" "public subnet A ID") || failed=1
  SECURITY_GROUP_ID=$(fetch_param "${SSM_PREFIX}/security/jenkins-agent-sg-id" "jenkins agent security group ID") || failed=1

  [[ $failed -ne 0 ]] && return 1

  assert_regex "$PIPELINE_ARN" '^arn:aws:imagebuilder:' "Pipeline ARN must be an Image Builder ARN" || failed=1
  assert_regex "$COMPONENT_VERSION" '^1\.[0-9]{6}\.[0-9]+$' "Component version must follow 1.YYMMDD.seconds format" || failed=1
  assert_regex "$RECIPE_VERSION" '^1\.[0-9]{6}\.[0-9]+$' "Recipe version must follow 1.YYMMDD.seconds format" || failed=1

  return $failed
}

test_pipeline_status() {
  log_section "INT-ECS-IMG-002: Image Builder pipeline status"
  local pipeline_json status

  pipeline_json=$(aws imagebuilder get-image-pipeline \
    --image-pipeline-arn "$PIPELINE_ARN" \
    --region "$AWS_REGION" \
    --query "imagePipeline" \
    --output json 2>/dev/null || true)

  if [ -z "$pipeline_json" ] || [ "$pipeline_json" = "null" ]; then
    log_error "Image pipeline not found for ARN: ${PIPELINE_ARN}"
    return 1
  fi

  status=$(echo "$pipeline_json" | jq -r '.status // empty')
  if [ "$status" != "ENABLED" ]; then
    log_error "Pipeline status is not ENABLED (current: ${status})"
    return 1
  fi

  CONTAINER_RECIPE_ARN=$(echo "$pipeline_json" | jq -r '.containerRecipeArn // empty')
  DISTRIBUTION_CONFIG_ARN=$(echo "$pipeline_json" | jq -r '.distributionConfigurationArn // empty')
  INFRA_CONFIG_ARN=$(echo "$pipeline_json" | jq -r '.infrastructureConfigurationArn // empty')

  if [ -z "$CONTAINER_RECIPE_ARN" ] || [ -z "$DISTRIBUTION_CONFIG_ARN" ] || [ -z "$INFRA_CONFIG_ARN" ]; then
    log_error "Pipeline missing required references (container recipe, distribution config, or infrastructure config)."
    return 1
  fi

  log_info "Pipeline ENABLED with recipe: ${CONTAINER_RECIPE_ARN}"
  return 0
}

test_container_recipe() {
  log_section "INT-ECS-IMG-003: Container recipe configuration"
  local recipe_json container_type target_repo_name component_arn_from_recipe repo_name

  recipe_json=$(aws imagebuilder get-container-recipe \
    --container-recipe-arn "$CONTAINER_RECIPE_ARN" \
    --region "$AWS_REGION" \
    --query "containerRecipe" \
    --output json 2>/dev/null || true)

  if [ -z "$recipe_json" ] || [ "$recipe_json" = "null" ]; then
    log_error "Container recipe not found: ${CONTAINER_RECIPE_ARN}"
    return 1
  fi

  container_type=$(echo "$recipe_json" | jq -r '.containerType // empty')
  if [ "$container_type" != "DOCKER" ]; then
    log_error "Unexpected containerType: ${container_type}"
    return 1
  fi

  repo_name=$(echo "$ECR_REPOSITORY_URL" | cut -d'/' -f2-)
  target_repo_name=$(echo "$recipe_json" | jq -r '.targetRepository.repositoryName // empty')
  if [ "$target_repo_name" != "$repo_name" ]; then
    log_error "Target repository mismatch (${target_repo_name}) expected ${repo_name}"
    return 1
  fi

  component_arn_from_recipe=$(echo "$recipe_json" | jq -r '.components[0].componentArn // empty')
  if [ -z "$component_arn_from_recipe" ]; then
    log_error "No component reference found in container recipe"
    return 1
  fi

  COMPONENT_ARN="$component_arn_from_recipe"
  log_info "Container recipe validated with component: ${COMPONENT_ARN}"
  return 0
}

test_distribution_configuration() {
  log_section "INT-ECS-IMG-004: Distribution configuration targets"
  local dist_json repo_name target_repo tag_list

  dist_json=$(aws imagebuilder get-distribution-configuration \
    --distribution-configuration-arn "$DISTRIBUTION_CONFIG_ARN" \
    --region "$AWS_REGION" \
    --query "distributionConfiguration" \
    --output json 2>/dev/null || true)

  if [ -z "$dist_json" ] || [ "$dist_json" = "null" ]; then
    log_error "Distribution configuration not found: ${DISTRIBUTION_CONFIG_ARN}"
    return 1
  fi

  repo_name=$(echo "$ECR_REPOSITORY_URL" | cut -d'/' -f2-)
  target_repo=$(echo "$dist_json" | jq -r '.distributions[0].containerDistributionConfiguration.targetRepository.repositoryName // empty')
  if [ "$target_repo" != "$repo_name" ]; then
    log_error "Distribution target repository mismatch (${target_repo}) expected ${repo_name}"
    return 1
  fi

  tag_list=$(echo "$dist_json" | jq -r '.distributions[0].containerDistributionConfiguration.containerTags | join(",")')
  if [[ "$tag_list" != *"latest"* ]] || [[ "$tag_list" != *"{{imagebuilder:buildDate}}"* ]]; then
    log_error "Container tags missing expected values (latest, {{imagebuilder:buildDate}})"
    return 1
  fi

  log_info "Distribution configuration points to ${repo_name} with expected tags"
  return 0
}

test_infrastructure_configuration() {
  log_section "INT-ECS-IMG-005: Infrastructure configuration and IAM role"
  local infra_json profile_name instance_type subnet_id security_groups terminate role_name policies

  infra_json=$(aws imagebuilder get-infrastructure-configuration \
    --infrastructure-configuration-arn "$INFRA_CONFIG_ARN" \
    --region "$AWS_REGION" \
    --query "infrastructureConfiguration" \
    --output json 2>/dev/null || true)

  if [ -z "$infra_json" ] || [ "$infra_json" = "null" ]; then
    log_error "Infrastructure configuration not found: ${INFRA_CONFIG_ARN}"
    return 1
  fi

  profile_name=$(echo "$infra_json" | jq -r '.instanceProfileName // empty')
  instance_type=$(echo "$infra_json" | jq -r '.instanceTypes[0] // empty')
  subnet_id=$(echo "$infra_json" | jq -r '.subnetId // empty')
  security_groups=$(echo "$infra_json" | jq -r '.securityGroupIds | join(",")')
  terminate=$(echo "$infra_json" | jq -r '.terminateInstanceOnFailure // empty')

  if [ -z "$profile_name" ] || [ -z "$instance_type" ] || [ -z "$subnet_id" ] || [ -z "$security_groups" ]; then
    log_error "Infrastructure configuration missing required fields"
    return 1
  fi

  if [ "$instance_type" != "t3.medium" ]; then
    log_error "Unexpected instance type: ${instance_type}"
    return 1
  fi

  if [ "$subnet_id" != "$SUBNET_ID" ]; then
    log_error "Subnet mismatch (${subnet_id}) expected ${SUBNET_ID}"
    return 1
  fi

  if ! echo "$security_groups" | tr ',' '\n' | grep -q "$SECURITY_GROUP_ID"; then
    log_error "Security group ${SECURITY_GROUP_ID} not attached to infrastructure configuration"
    return 1
  fi

  if [ "$terminate" != "true" ]; then
    log_error "terminateInstanceOnFailure must be true"
    return 1
  fi

  role_name=$(aws iam get-instance-profile \
    --instance-profile-name "$profile_name" \
    --query "InstanceProfile.Roles[0].RoleName" \
    --output text 2>/dev/null || true)

  if [ -z "$role_name" ] || [ "$role_name" = "None" ]; then
    log_error "IAM role not found for instance profile ${profile_name}"
    return 1
  fi

  INSTANCE_PROFILE_ROLE="$role_name"
  policies=$(aws iam list-attached-role-policies \
    --role-name "$role_name" \
    --query "AttachedPolicies[].PolicyArn" \
    --output text 2>/dev/null || true)

  for required in \
    "EC2InstanceProfileForImageBuilder" \
    "AmazonSSMManagedInstanceCore" \
    "EC2InstanceProfileForImageBuilderECRContainerBuilds"; do
    if ! echo "$policies" | grep -q "$required"; then
      log_error "Required IAM policy missing from role ${role_name}: ${required}"
      return 1
    fi
  done

  if ! echo "$policies" | grep -q "imagebuilder-ecr-policy"; then
    log_error "Custom ECR push policy is not attached to role ${role_name}"
    return 1
  fi

  log_info "Infrastructure configuration and IAM role validated (profile: ${profile_name}, role: ${role_name})"
  return 0
}

test_component_definition() {
  log_section "INT-ECS-IMG-007: Component definition validation"
  local component_json platform has_build has_validate

  component_json=$(aws imagebuilder get-component \
    --component-build-version-arn "$COMPONENT_ARN" \
    --region "$AWS_REGION" \
    --query "component" \
    --output json 2>/dev/null || true)

  if [ -z "$component_json" ] || [ "$component_json" = "null" ]; then
    log_error "Component not found: ${COMPONENT_ARN}"
    return 1
  fi

  platform=$(echo "$component_json" | jq -r '.platform // empty')
  if [ "$platform" != "Linux" ]; then
    log_error "Component platform must be Linux (current: ${platform})"
    return 1
  fi

  component_data=$(echo "$component_json" | jq -r '.data // empty')
  if [ -z "$component_data" ] || [ "$component_data" = "null" ]; then
    log_error "Component data payload is empty"
    return 1
  fi

  has_build=$(echo "$component_data" | grep -cE '^[[:space:]]*- name: build' || true)
  has_validate=$(echo "$component_data" | grep -cE '^[[:space:]]*- name: validate' || true)

  if [ "$has_build" -eq 0 ] || [ "$has_validate" -eq 0 ]; then
    log_error "Component is missing build or validate phase definitions in data payload"
    return 1
  fi

  log_info "Component phases validated (build/validate present)"
  return 0
}

main() {
  require_cmd aws
  require_cmd jq

  init_summary

  echo "=============================================="
  echo "ECS Image Builder Pipeline Integration Tests"
  echo "Environment: ${ENVIRONMENT}"
  echo "Region: ${AWS_REGION}"
  echo "=============================================="

  run_test "INT-ECS-IMG-001 SSM parameters" test_ssm_parameters_exist
  run_test "INT-ECS-IMG-002 Pipeline status" test_pipeline_status
  run_test "INT-ECS-IMG-003 Container recipe" test_container_recipe
  run_test "INT-ECS-IMG-004 Distribution configuration" test_distribution_configuration
  run_test "INT-ECS-IMG-005 Infrastructure configuration" test_infrastructure_configuration
  run_test "INT-ECS-IMG-007 Component definition" test_component_definition

  echo
  echo "=============================================="
  echo "Test summary: ${PASSED}/${TOTAL} passed, ${FAILED} failed"
  echo "=============================================="

  if [ "$FAILED" -ne 0 ]; then
    exit 1
  fi
}

main "$@"
