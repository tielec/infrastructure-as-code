#!/bin/bash
# Jenkins Agent JNLP Entrypoint for ECS Fargate
# amazon-ecsプラグインからコマンドライン引数を受け取る形式
# プラグインが渡す古い形式: -url <jenkins-url> <secret> <agent-name>
# 新しい形式に変換: -url <jenkins-url> -secret <secret> -name <agent-name>

set -e

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Starting Jenkins Agent..."

JENKINS_AGENT_HOME="${JENKINS_AGENT_HOME:-/home/jenkins}"
WORKDIR="${JENKINS_AGENT_HOME}/agent"
mkdir -p "${WORKDIR}"

log "Received arguments: $*"

# amazon-ecsプラグインが渡す引数形式を想定: -url <url> <secret> <name>
# $1 = -url
# $2 = <jenkins-url>
# $3 = <secret>
# $4 = <agent-name>

if [ "$1" = "-url" ] && [ $# -eq 4 ]; then
    JENKINS_URL="$2"
    SECRET="$3"
    AGENT_NAME="$4"

    log "Converted to new format with WebSocket:"
    log "  URL: ${JENKINS_URL}"
    log "  Agent Name: ${AGENT_NAME}"
    log "  Working directory: ${WORKDIR}"

    exec java -jar "${JENKINS_AGENT_HOME}/agent.jar" \
        -url "${JENKINS_URL}" \
        -secret "${SECRET}" \
        -name "${AGENT_NAME}" \
        -workDir "${WORKDIR}" \
        -webSocket
else
    # 既に新しい形式の場合はそのまま渡す
    log "Using arguments as-is"
    log "Working directory: ${WORKDIR}"

    exec java -jar "${JENKINS_AGENT_HOME}/agent.jar" \
        -workDir "${WORKDIR}" \
        "$@"
fi
