#!/bin/bash
# Jenkinsクレデンシャルの一括セットアップ
# SSM経由で実行されることを前提

set -e

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /var/log/jenkins-application-setup.log
}

log "===== Setting up Jenkins Credentials ====="

# 環境変数の確認
JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
REPO_PATH="${REPO_PATH:-/root/infrastructure-as-code}"

log "Environment:"
log "  JENKINS_HOME: $JENKINS_HOME"
log "  REPO_PATH: $REPO_PATH"

# Groovyスクリプトのソースパス
GROOVY_SCRIPT_SRC="${REPO_PATH}/scripts/jenkins/groovy/setup-credentials.groovy"

if [ ! -f "$GROOVY_SCRIPT_SRC" ]; then
    log "ERROR: Groovy script not found: $GROOVY_SCRIPT_SRC"
    exit 1
fi

log "Groovy script found: $GROOVY_SCRIPT_SRC"

# Groovyスクリプトの配置先
GROOVY_DIR="${JENKINS_HOME}/init.groovy.d"
mkdir -p "$GROOVY_DIR"

GROOVY_SCRIPT_DST="${GROOVY_DIR}/02-setup-credentials.groovy"

# Groovyスクリプトをコピー
log "Copying credentials setup script to $GROOVY_SCRIPT_DST"
cp "$GROOVY_SCRIPT_SRC" "$GROOVY_SCRIPT_DST"

chown jenkins:jenkins "$GROOVY_SCRIPT_DST"
chmod 644 "$GROOVY_SCRIPT_DST"

log "Credentials setup script prepared."
log "All credentials will be created or updated on the next Jenkins restart."
log "The script will retrieve secrets directly from SSM Parameter Store."

log "===== Jenkins Credentials Setup Complete ====="

exit 0