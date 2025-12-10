#!/bin/bash
# Integration test: Validate required tooling is available inside Jenkins ECS agent image (INT-002).
# Confirms Java 21, Docker CLI, AWS CLI v2, Node.js 20, Python 3.11, Git, jq, Pulumi, and Ansible are installed.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DOCKERFILE_DIR="${ROOT_DIR}/docker/jenkins-agent-ecs"
IMAGE_TAG="${IMAGE_TAG:-jenkins-agent-ecs:test}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    log "ERROR: Required command '$1' not found"
    exit 1
  }
}

run_in_container() {
  docker run --rm "${IMAGE_TAG}" "$@"
}

require_cmd docker

log "=== INT-002: Container tool verification (${IMAGE_TAG}) ==="

# Ensure base image exists (reuse INT-001 build or create on demand)
if ! docker image inspect "${IMAGE_TAG}" >/dev/null 2>&1; then
  log "Image ${IMAGE_TAG} not found; building from ${DOCKERFILE_DIR}..."
  if [ ! -d "$DOCKERFILE_DIR" ]; then
    log "ERROR: Dockerfile directory missing at ${DOCKERFILE_DIR}"
    exit 1
  fi
  docker build -t "${IMAGE_TAG}" "${DOCKERFILE_DIR}"
fi

# Java
JAVA_OUTPUT=$(run_in_container java -version 2>&1 | head -1)
log "Java: ${JAVA_OUTPUT}"
if ! echo "${JAVA_OUTPUT}" | grep -q "21"; then
  log "ERROR: Java 21 not detected"
  exit 1
fi

# Docker CLI
DOCKER_OUTPUT=$(run_in_container docker --version 2>&1)
log "Docker: ${DOCKER_OUTPUT}"

# AWS CLI v2
AWS_OUTPUT=$(run_in_container aws --version 2>&1)
log "AWS CLI: ${AWS_OUTPUT}"
if ! echo "${AWS_OUTPUT}" | grep -q "aws-cli/2"; then
  log "ERROR: AWS CLI v2 not detected"
  exit 1
fi

# Node.js 20
NODE_OUTPUT=$(run_in_container node --version 2>&1)
log "Node.js: ${NODE_OUTPUT}"
if ! echo "${NODE_OUTPUT}" | grep -q "^v20"; then
  log "ERROR: Node.js 20 not detected"
  exit 1
fi

# Python 3.11
PY_OUTPUT=$(run_in_container python3 --version 2>&1)
log "Python: ${PY_OUTPUT}"
if ! echo "${PY_OUTPUT}" | grep -q "3.11"; then
  log "ERROR: Python 3.11 not detected"
  exit 1
fi

# Git
GIT_OUTPUT=$(run_in_container git --version 2>&1)
log "Git: ${GIT_OUTPUT}"

# jq
JQ_OUTPUT=$(run_in_container jq --version 2>&1)
log "jq: ${JQ_OUTPUT}"

# Pulumi
PULUMI_OUTPUT=$(run_in_container pulumi version 2>&1)
log "Pulumi: ${PULUMI_OUTPUT}"

# Ansible
ANSIBLE_OUTPUT=$(run_in_container ansible --version 2>&1 | head -1)
log "Ansible: ${ANSIBLE_OUTPUT}"

log "All required tools are present inside the container image."
