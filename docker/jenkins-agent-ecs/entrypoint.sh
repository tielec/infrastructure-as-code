#!/bin/bash
# Jenkins Agent JNLP Entrypoint for ECS Fargate

set -e

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Starting Jenkins Agent..."

if [ -z "${JENKINS_URL}" ]; then
    log "ERROR: JENKINS_URL is not set"
    exit 1
fi

if [ -z "${JENKINS_AGENT_NAME}" ]; then
    log "ERROR: JENKINS_AGENT_NAME is not set"
    exit 1
fi

if [ -z "${JENKINS_SECRET}" ]; then
    log "ERROR: JENKINS_SECRET is not set"
    exit 1
fi

JENKINS_URL="${JENKINS_URL%/}"

log "Jenkins URL: ${JENKINS_URL}"
log "Agent Name: ${JENKINS_AGENT_NAME}"

TUNNEL_ARG=""
if [ -n "${JENKINS_TUNNEL}" ]; then
    TUNNEL_ARG="-tunnel ${JENKINS_TUNNEL}"
    log "Tunnel: ${JENKINS_TUNNEL}"
fi

WORKDIR="${JENKINS_AGENT_HOME:-/home/jenkins}/agent"
mkdir -p "${WORKDIR}"

log "Starting JNLP agent..."

exec java \
    -jar "${JENKINS_AGENT_HOME:-/home/jenkins}/agent.jar" \
    -url "${JENKINS_URL}" \
    -secret "${JENKINS_SECRET}" \
    -name "${JENKINS_AGENT_NAME}" \
    -workDir "${WORKDIR}" \
    ${TUNNEL_ARG}
