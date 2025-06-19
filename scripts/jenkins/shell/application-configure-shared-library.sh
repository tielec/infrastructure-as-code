#!/bin/bash
# Jenkins Shared Library設定
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

log "===== Configuring Jenkins Shared Library ====="

# 環境変数の確認
JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
REPO_PATH="${REPO_PATH:-/root/infrastructure-as-code}"
PROJECT_NAME="${PROJECT_NAME:-jenkins-infra}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

log "Environment:"
log "  JENKINS_HOME: $JENKINS_HOME"
log "  REPO_PATH: $REPO_PATH"
log "  PROJECT_NAME: $PROJECT_NAME"
log "  ENVIRONMENT: $ENVIRONMENT"

# Shared Library設定パラメータ
export SHARED_LIBRARY_NAME="${SHARED_LIBRARY_NAME:-jenkins-shared-lib}"
export SHARED_LIBRARY_REPO="${SHARED_LIBRARY_REPO:-https://github.com/tielec/infrastructure-as-code}"
export SHARED_LIBRARY_BRANCH="${SHARED_LIBRARY_BRANCH:-main}"
export SHARED_LIBRARY_PATH="${SHARED_LIBRARY_PATH:-jenkins/jobs/shared/}"
export SHARED_LIBRARY_ALLOW_OVERRIDE="${SHARED_LIBRARY_ALLOW_OVERRIDE:-true}"
export SHARED_LIBRARY_INCLUDE_CHANGELOG="${SHARED_LIBRARY_INCLUDE_CHANGELOG:-true}"
export SHARED_LIBRARY_CACHE="${SHARED_LIBRARY_CACHE:-false}"
export UPDATE_EXISTING_LIBRARY="${UPDATE_EXISTING_LIBRARY:-true}"

log "Shared Library Configuration:"
log "  Name: $SHARED_LIBRARY_NAME"
log "  Repository: $SHARED_LIBRARY_REPO"
log "  Branch: $SHARED_LIBRARY_BRANCH"
log "  Path: $SHARED_LIBRARY_PATH"
log "  Allow Override: $SHARED_LIBRARY_ALLOW_OVERRIDE"
log "  Include in Changelog: $SHARED_LIBRARY_INCLUDE_CHANGELOG"

# Pipeline プラグインの確認
if [ -d "${JENKINS_HOME}/plugins/workflow-cps-global-lib" ]; then
    log "✓ Pipeline Shared Libraries plugin directory found"
else
    log "✗ WARNING: Pipeline Shared Libraries plugin directory not found"
    log "  Please ensure the workflow-cps-global-lib plugin is installed"
fi

# Groovyスクリプトを配置
GROOVY_DIR="${JENKINS_HOME}/init.groovy.d"
mkdir -p "$GROOVY_DIR"

# Gitリポジトリからスクリプトをコピー
GROOVY_SCRIPT="${REPO_PATH}/scripts/jenkins/groovy/configure-shared-library.groovy"

if [ ! -f "$GROOVY_SCRIPT" ]; then
    error_exit "Groovy script not found: $GROOVY_SCRIPT"
fi

# Shared Library設定スクリプトをコピー
log "Copying Shared Library configuration script..."
cp "$GROOVY_SCRIPT" "$GROOVY_DIR/"
chown jenkins:jenkins "$GROOVY_DIR/configure-shared-library.groovy"
chmod 644 "$GROOVY_DIR/configure-shared-library.groovy"

# Jenkinsを再起動して実行
log "Restarting Jenkins to configure Shared Library..."
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
log "Waiting for Shared Library configuration to complete..."
sleep 30

# スクリプトを削除
rm -f "$GROOVY_DIR/configure-shared-library.groovy"

# 設定ログの確認
if [ -f "/var/log/jenkins/jenkins.log" ]; then
    log "Recent Jenkins logs related to Shared Library:"
    grep -i "Shared Library" /var/log/jenkins/jenkins.log | tail -20 || true
fi

log "Shared Library configuration completed"
log ""
log "To use this library in your Jenkinsfile:"
log "  @Library('$SHARED_LIBRARY_NAME') _"
log ""
log "Or with a specific version:"
log "  @Library('$SHARED_LIBRARY_NAME@$SHARED_LIBRARY_BRANCH') _"
