#!/bin/bash
# Integration test: Validate component.yml syntax and required install steps for ECS agent image.
# Covers INT-ECS-IMG-015 (YAML syntax and required fields) and INT-ECS-IMG-016 (tool install steps).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
source "${ROOT_DIR}/tests/integration/ecs-image/helpers.sh"

COMPONENT_FILE="${ROOT_DIR}/pulumi/jenkins-agent-ecs-image/component.yml"

test_component_yaml_syntax() {
  log_section "INT-ECS-IMG-015: component.yml syntax and required fields"
  local failed=0

  if [ ! -f "$COMPONENT_FILE" ]; then
    log_error "Component file not found at ${COMPONENT_FILE}"
    return 1
  fi

  if ! yamllint "$COMPONENT_FILE"; then
    log_error "yamllint reported errors for component.yml"
    return 1
  fi

  for key in name: description: schemaVersion:; do
    if ! grep -q "^${key}" "$COMPONENT_FILE"; then
      log_error "Missing required top-level field: ${key%:}"
      failed=1
    fi
  done

  if ! grep -q "^[[:space:]]*- name: build" "$COMPONENT_FILE"; then
    log_error "build phase is not defined in component.yml"
    failed=1
  fi

  if ! grep -q "^[[:space:]]*- name: validate" "$COMPONENT_FILE"; then
    log_error "validate phase is not defined in component.yml"
    failed=1
  fi

  return $failed
}

test_component_install_steps() {
  log_section "INT-ECS-IMG-016: component.yml includes required install steps"
  local content failed=0

  if [ ! -f "$COMPONENT_FILE" ]; then
    log_error "Component file not found at ${COMPONENT_FILE}"
    return 1
  fi

  content=$(cat "$COMPONENT_FILE")

  assert_contains "$content" "java-21-amazon-corretto" "Java 21 install step missing" || failed=1
  assert_contains "$content" "setup_20.x" "Node.js 20 install step missing" || failed=1
  assert_contains "$content" "awscli-exe-linux-x86_64.zip" "AWS CLI v2 install step missing" || failed=1
  assert_contains "$content" "pulumi-v3" "Pulumi install step missing" || failed=1
  assert_contains "$content" "pip3 install --no-cache-dir ansible" "Ansible install step missing" || failed=1
  assert_contains "$content" "git --version" "Git verification step missing" || failed=1
  assert_contains "$content" "python3 --version" "Python3 verification step missing" || failed=1
  assert_contains "$content" "groupadd -g 1000 jenkins" "jenkins user creation step missing" || failed=1
  assert_contains "$content" "/entrypoint.sh" "entrypoint.sh placement step missing" || failed=1

  return $failed
}

main() {
  require_cmd yamllint

  init_summary

  echo "=============================================="
  echo "Component YAML validation for ECS agent image"
  echo "Component file: ${COMPONENT_FILE}"
  echo "=============================================="

  run_test "INT-ECS-IMG-015 Component YAML syntax" test_component_yaml_syntax
  run_test "INT-ECS-IMG-016 Component tool steps" test_component_install_steps

  echo
  echo "=============================================="
  echo "Test summary: ${PASSED}/${TOTAL} passed, ${FAILED} failed"
  echo "=============================================="

  if [ "$FAILED" -ne 0 ]; then
    exit 1
  fi
}

main "$@"
