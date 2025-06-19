#!/bin/bash
# Jenkins セキュリティ設定
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

log "===== Configuring Jenkins Security Settings ====="

# 環境変数の確認
JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
REPO_PATH="${REPO_PATH:-/root/infrastructure-as-code}"

log "Environment:"
log "  JENKINS_HOME: $JENKINS_HOME"
log "  REPO_PATH: $REPO_PATH"

# セキュリティ設定パラメータ
export JENKINS_MARKUP_FORMATTER="${JENKINS_MARKUP_FORMATTER:-markdown}"
export JENKINS_ENABLE_SCRIPT_SECURITY="${JENKINS_ENABLE_SCRIPT_SECURITY:-false}"

log "Security Configuration:"
log "  Markup Formatter: $JENKINS_MARKUP_FORMATTER"
log "  Script Security: $JENKINS_ENABLE_SCRIPT_SECURITY"

# Markdown Formatterプラグインの確認
if [ -d "${JENKINS_HOME}/plugins/markdown-formatter" ]; then
    log "✓ Markdown Formatter plugin directory found"
else
    log "✗ WARNING: Markdown Formatter plugin directory not found"
    log "  Markup formatter will fallback to plain text"
fi

# Groovyスクリプトを配置
GROOVY_DIR="${JENKINS_HOME}/init.groovy.d"
mkdir -p "$GROOVY_DIR"

# Gitリポジトリからスクリプトをコピー
GROOVY_SCRIPT="${REPO_PATH}/scripts/jenkins/groovy/configure-security.groovy"

if [ ! -f "$GROOVY_SCRIPT" ]; then
    error_exit "Groovy script not found: $GROOVY_SCRIPT"
fi

# セキュリティ設定スクリプトをコピー
log "Copying security configuration script..."
cp "$GROOVY_SCRIPT" "$GROOVY_DIR/"
chown jenkins:jenkins "$GROOVY_DIR/configure-security.groovy"
chmod 644 "$GROOVY_DIR/configure-security.groovy"

# Jenkinsを再起動して実行
log "Restarting Jenkins to apply security settings..."
systemctl restart jenkins

# 起動を待機
log "Waiting for Jenkins to start..."
TIMEOUT=300
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if curl -sf http://localhost:8080/login > /dev/null 2>&1; then
        log "Jenkins is running"
        break
    fi
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    error_exit "Jenkins failed to start within timeout"
fi

# 設定の完了を待機
log "Waiting for security configuration to complete..."
sleep 30

# スクリプトを削除
rm -f "$GROOVY_DIR/configure-security.groovy"

# 設定ログの確認
if [ -f "/var/log/jenkins/jenkins.log" ]; then
    log "Recent Jenkins logs related to security:"
    grep -i "Security" /var/log/jenkins/jenkins.log | tail -20 || true
fi

log "Security configuration completed"
