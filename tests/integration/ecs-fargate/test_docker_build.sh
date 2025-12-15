#!/bin/bash
# Integration test: Validate local Docker build for Jenkins ECS agent image (INT-001).
# Ensures Dockerfile/entrypoint exist, build succeeds, and resulting image size stays under 1GB.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DOCKERFILE_DIR="${ROOT_DIR}/docker/jenkins-agent-ecs"
IMAGE_TAG="${IMAGE_TAG:-jenkins-agent-ecs:test}"
SIZE_LIMIT_BYTES=$((1024 * 1024 * 1024)) # 1GB limit

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    log "ERROR: Required command '$1' not found"
    exit 1
  }
}

human_size() {
  local bytes="$1"
  if command -v numfmt >/dev/null 2>&1; then
    numfmt --to=iec --suffix=B "$bytes"
  else
    # Fallback to MB with integer rounding
    echo "$(( (bytes + 1024 * 1024 - 1) / (1024 * 1024) ))MB"
  fi
}

require_cmd docker

log "=== INT-001: Docker image build validation (${IMAGE_TAG}) ==="

if [ ! -f "${DOCKERFILE_DIR}/Dockerfile" ]; then
  log "ERROR: Dockerfile not found at ${DOCKERFILE_DIR}/Dockerfile"
  exit 1
fi

if [ ! -f "${DOCKERFILE_DIR}/entrypoint.sh" ]; then
  log "ERROR: Entrypoint script not found at ${DOCKERFILE_DIR}/entrypoint.sh"
  exit 1
fi

log "Building Docker image from ${DOCKERFILE_DIR}..."
docker build -t "${IMAGE_TAG}" "${DOCKERFILE_DIR}"
log "Docker build completed"

log "Inspecting image size..."
IMAGE_SIZE_BYTES=$(docker image inspect "${IMAGE_TAG}" --format '{{.Size}}' 2>/dev/null || true)
if [ -z "${IMAGE_SIZE_BYTES}" ]; then
  log "ERROR: Unable to determine image size for ${IMAGE_TAG}"
  exit 1
fi

if [ "$IMAGE_SIZE_BYTES" -gt "$SIZE_LIMIT_BYTES" ]; then
  log "ERROR: Image size $(human_size "$IMAGE_SIZE_BYTES") exceeds 1GB limit"
  exit 1
fi

log "Docker image built successfully within size limit ($(human_size "$IMAGE_SIZE_BYTES"))"
