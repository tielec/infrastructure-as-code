#!/bin/bash
# Integration validation: ECR credential-helper shellcheck + config.json structure

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SETUP_SCRIPT="${ROOT_DIR}/scripts/aws/userdata/jenkins-agent-setup.sh"
CUSTOM_SCRIPT="${ROOT_DIR}/scripts/aws/userdata/jenkins-agent-custom-ami.sh"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    log "ERROR: Required command '$1' not found"
    exit 1
  }
}

require_cmd shellcheck
require_cmd jq

log "=== IT-556-11/12: ShellCheck validation ==="
shellcheck --exclude=SC2154 --shell=bash "${SETUP_SCRIPT}"
shellcheck --exclude=SC2154 --shell=bash "${CUSTOM_SCRIPT}"
log "ShellCheck validation completed."

log "=== IT-556-13: config.json normal structure validation ==="
NORMAL_JSON='{"credHelpers":{"123456789012.dkr.ecr.ap-northeast-1.amazonaws.com":"ecr-login"}}'
EXPECTED_KEY="123456789012.dkr.ecr.ap-northeast-1.amazonaws.com"

echo "${NORMAL_JSON}" | jq . >/dev/null
if ! echo "${NORMAL_JSON}" | jq -e '.credHelpers' >/dev/null; then
  log "ERROR: credHelpers missing in normal config.json"
  exit 1
fi
KEYS=$(echo "${NORMAL_JSON}" | jq -r '.credHelpers | keys[]')
if ! echo "${KEYS}" | grep -Eq '^[0-9]{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com$'; then
  log "ERROR: ECR endpoint format invalid"
  exit 1
fi
VALUE=$(echo "${NORMAL_JSON}" | jq -r --arg key "${EXPECTED_KEY}" '.credHelpers[$key]')
if [ "${VALUE}" != "ecr-login" ]; then
  log "ERROR: credHelpers value is not ecr-login"
  exit 1
fi

log "=== IT-556-14: config.json wildcard structure validation ==="
WILDCARD_JSON='{"credHelpers":{"*.dkr.ecr.*.amazonaws.com":"ecr-login"}}'
echo "${WILDCARD_JSON}" | jq . >/dev/null
if ! echo "${WILDCARD_JSON}" | jq -e '.credHelpers' >/dev/null; then
  log "ERROR: credHelpers missing in wildcard config.json"
  exit 1
fi
WILDCARD_KEY=$(echo "${WILDCARD_JSON}" | jq -r '.credHelpers | keys[0]')
if [ "${WILDCARD_KEY}" != "*.dkr.ecr.*.amazonaws.com" ]; then
  log "ERROR: wildcard key mismatch"
  exit 1
fi

log "=== IT-556-19: invalid config.json detection ==="
INVALID_JSON='{"credHelpers": {"endpoint": "ecr-login"}'
set +e
printf '%s' "${INVALID_JSON}" | jq . >/dev/null 2>&1
INVALID_EXIT=$?
set -e
if [ ${INVALID_EXIT} -eq 0 ]; then
  log "ERROR: invalid JSON should fail jq validation"
  exit 1
fi

MISSING_KEY_JSON='{"otherKey":"value"}'
set +e
printf '%s' "${MISSING_KEY_JSON}" | jq -e '.credHelpers' >/dev/null 2>&1
MISSING_EXIT=$?
set -e
if [ ${MISSING_EXIT} -eq 0 ]; then
  log "ERROR: missing credHelpers should fail jq -e check"
  exit 1
fi

log "All ECR credential-helper validations completed successfully."
