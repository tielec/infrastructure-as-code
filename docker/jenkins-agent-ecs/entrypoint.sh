#!/bin/bash
# Jenkins Agent JNLP Entrypoint for ECS Fargate
# amazon-ecsプラグインからコマンドライン引数を受け取る形式
# プラグインが渡す引数: -url <jenkins-url> <secret> <agent-name>

set -e

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Starting Jenkins Agent..."

JENKINS_AGENT_HOME="${JENKINS_AGENT_HOME:-/home/jenkins}"
WORKDIR="${JENKINS_AGENT_HOME}/agent"
mkdir -p "${WORKDIR}"

log "Received arguments: $*"
log "Working directory: ${WORKDIR}"

# amazon-ecsプラグインが渡したコマンドライン引数をそのまま使用
exec java -jar "${JENKINS_AGENT_HOME}/agent.jar" \
    -workDir "${WORKDIR}" \
    "$@"
