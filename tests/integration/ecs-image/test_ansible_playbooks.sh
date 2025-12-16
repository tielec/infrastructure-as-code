#!/bin/bash
# Integration test: Validate Ansible playbooks for jenkins-agent-ecs-image stack (Issue #496).
# Ensures deploy/remove playbooks pass syntax checks and removal playbook enforces confirm flag.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ANSIBLE_DIR="${ROOT_DIR}/ansible"
PLAYBOOK_DEPLOY="playbooks/jenkins/deploy/deploy_jenkins_agent_ecs_image.yml"
PLAYBOOK_REMOVE="playbooks/jenkins/remove/remove_jenkins_agent_ecs_image.yml"
ENVIRONMENT="${ENVIRONMENT:-dev}"

log_info() {
  echo "[INFO] $*"
}

log_error() {
  echo "[ERROR] $*" >&2
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    log_error "Required command '$1' not found in PATH"
    exit 1
  }
}

run_test() {
  local name="$1"
  shift
  TOTAL=$((TOTAL + 1))
  if "$@"; then
    PASSED=$((PASSED + 1))
  else
    FAILED=$((FAILED + 1))
  fi
}

test_syntax_checks() {
  log_info "INT-ECS-IMG-011/012: Running ansible-playbook --syntax-check"
  ANSIBLE_CONFIG="${ANSIBLE_DIR}/ansible.cfg" \
    ANSIBLE_STDOUT_CALLBACK=default \
    ansible-playbook --syntax-check "${PLAYBOOK_DEPLOY}"

  ANSIBLE_CONFIG="${ANSIBLE_DIR}/ansible.cfg" \
    ANSIBLE_STDOUT_CALLBACK=default \
    ansible-playbook --syntax-check "${PLAYBOOK_REMOVE}"
}

test_remove_requires_confirmation() {
  log_info "INT-ECS-IMG-012: Verifying remove playbook requires confirm=true"
  local rc=0

  set +e
  ANSIBLE_CONFIG="${ANSIBLE_DIR}/ansible.cfg" \
    ANSIBLE_STDOUT_CALLBACK=default \
    ansible-playbook "${PLAYBOOK_REMOVE}" \
    -e "env=${ENVIRONMENT}" \
    --check >/dev/null
  rc=$?
  set -e

  if [ $rc -eq 0 ]; then
    log_error "Removal playbook ran without confirm=true but should fail fast"
    return 1
  fi

  log_info "Removal playbook correctly blocks execution without confirm flag"
  return 0
}

main() {
  require_cmd ansible-playbook
  cd "${ANSIBLE_DIR}"

  TOTAL=0
  PASSED=0
  FAILED=0

  echo "=============================================="
  echo "Ansible playbook validation for ECS image stack"
  echo "Environment: ${ENVIRONMENT}"
  echo "Ansible dir: ${ANSIBLE_DIR}"
  echo "=============================================="

  run_test "Ansible syntax checks" test_syntax_checks
  run_test "Removal requires confirmation" test_remove_requires_confirmation

  echo
  echo "=============================================="
  echo "Test summary: ${PASSED}/${TOTAL} passed, ${FAILED} failed"
  echo "=============================================="

  if [ "$FAILED" -ne 0 ]; then
    exit 1
  fi
}

main "$@"
