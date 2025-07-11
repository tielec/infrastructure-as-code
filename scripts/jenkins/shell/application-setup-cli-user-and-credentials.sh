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

if [ "$RESTART_JENKINS" = "true" ]; then
    # Jenkinsを再起動して実行
    log "Restarting Jenkins to setup CLI user and credentials..."
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
    
    # セットアップの完了を待機
    log "Waiting for CLI user and credentials setup to complete..."
    sleep 30
    
    # スクリプトを削除
    rm -f "$GROOVY_DIR/setup-cli-user-and-credentials.groovy"
    
    # 結果の確認
    if [ -f "${JENKINS_HOME}/credentials.xml" ]; then
        if grep -q "cli-user-token" "${JENKINS_HOME}/credentials.xml"; then
            log "✓ CLI user and credentials successfully configured"
        else
            log "✗ WARNING: credentials.xml exists but cli-user-token not found"
        fi
    else
        log "✗ WARNING: credentials.xml not found"
    fi
    
    # ユーザーの存在確認
    if [ -d "${JENKINS_HOME}/users/cli-user_"* ]; then
        log "✓ CLI user directory found"
    else
        log "✗ WARNING: CLI user directory not found"
    fi
else
    log "CLI user and credentials setup script prepared. Jenkins restart skipped."
    log "The CLI user and credentials will be created on the next Jenkins restart."
    log "Note: The Groovy script remains in place at: $GROOVY_DIR/setup-cli-user-and-credentials.groovy"
    
    log ""
    log "Expected changes on next restart:"
    log "  - CLI user 'cli-user' will be created"
    log "  - API token credential 'cli-user-token' will be generated"
    log "  - Both will be stored in Jenkins configuration"
fi

if [ "$RESTART_JENKINS" = "true" ]; then
    log "CLI user and credentials setup completed"
else
    log "CLI user and credentials setup prepared"
fi

if [ "$RESTART_JENKINS" != "true" ]; then
    log ""
    log "To apply the configuration now, restart Jenkins manually: systemctl restart jenkins"
fi
