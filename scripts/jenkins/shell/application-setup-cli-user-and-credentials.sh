#!/bin/bash
# Jenkins CLIユーザーとクレデンシャルの統合セットアップ
# SSM経由で実行されることを前提

# エラーハンドリング設定
set -e

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /var/log/jenkins-application-setup.log
}

# エラーハンドラー
error_exit() {
    log "ERROR: $1"
    exit 1
}

log "===== Setting up Jenkins CLI User and Credentials ====="

# 環境変数の確認
JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
REPO_PATH="${REPO_PATH:-/root/infrastructure-as-code}"
RESTART_JENKINS="${RESTART_JENKINS:-false}"

log "JENKINS_HOME: $JENKINS_HOME"
log "REPO_PATH: $REPO_PATH"
log "RESTART_JENKINS: $RESTART_JENKINS"

# Groovyスクリプトを配置
GROOVY_DIR="${JENKINS_HOME}/init.groovy.d"
mkdir -p "$GROOVY_DIR"

# Gitリポジトリからスクリプトをコピー
GROOVY_SCRIPT="${REPO_PATH}/scripts/jenkins/groovy/setup-cli-user-and-credentials.groovy"

if [ ! -f "$GROOVY_SCRIPT" ]; then
    error_exit "Groovy script not found: $GROOVY_SCRIPT"
fi

# 統合スクリプトをコピー
log "Copying CLI user and credentials setup script..."
cp "$GROOVY_SCRIPT" "$GROOVY_DIR/"
chown jenkins:jenkins "$GROOVY_DIR/setup-cli-user-and-credentials.groovy"
chmod 644 "$GROOVY_DIR/setup-cli-user-and-credentials.groovy"

log "CLI user and credentials setup script prepared."
log "The CLI user and credentials will be created on the next Jenkins restart."
log "Note: The Groovy script is placed at: $GROOVY_DIR/setup-cli-user-and-credentials.groovy"

log ""
log "Expected changes on next restart:"
log "  - CLI user 'cli-user' will be created"
log "  - API token credential 'cli-user-token' will be generated"
log "  - Both will be stored in Jenkins configuration"
log ""
log "CLI user and credentials setup prepared successfully"
