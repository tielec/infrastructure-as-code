#!/bin/bash
# Jenkinsプラグインのインストール
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

log "===== Installing Jenkins Plugins ====="

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
GROOVY_SCRIPT="${REPO_PATH}/scripts/jenkins/groovy/install-plugins.groovy"

if [ ! -f "$GROOVY_SCRIPT" ]; then
    error_exit "Groovy script not found: $GROOVY_SCRIPT"
fi

# プラグインインストールスクリプトをコピー
log "Copying plugin installation script..."
cp "$GROOVY_SCRIPT" "$GROOVY_DIR/"
chown jenkins:jenkins "$GROOVY_DIR/install-plugins.groovy"
chmod 644 "$GROOVY_DIR/install-plugins.groovy"

# 現在のプラグイン数を記録
PLUGINS_BEFORE=$(ls -1 "${JENKINS_HOME}/plugins/" 2>/dev/null | wc -l || echo "0")
log "Current plugin count: $PLUGINS_BEFORE"

if [ "$RESTART_JENKINS" = "true" ]; then
    # Jenkinsを再起動してプラグインをインストール
    log "Restarting Jenkins to install plugins..."
    systemctl restart jenkins
    
    # 起動を待機（プラグインインストールは時間がかかる）
    log "Waiting for Jenkins to start and install plugins..."
    TIMEOUT=600
    ELAPSED=0
    while [ $ELAPSED -lt $TIMEOUT ]; do
        if curl -sf http://localhost:8080/login > /dev/null 2>&1; then
            log "Jenkins is running"
            break
        fi
        sleep 10
        ELAPSED=$((ELAPSED + 10))
        
        # 進捗表示
        if [ $((ELAPSED % 30)) -eq 0 ]; then
            log "Still waiting... ($ELAPSED seconds elapsed)"
        fi
    done
    
    if [ $ELAPSED -ge $TIMEOUT ]; then
        error_exit "Jenkins failed to start within timeout"
    fi
    
    # プラグインインストールの完了を待機
    log "Waiting for plugin installation to complete..."
    sleep 60
    
    # スクリプトを削除
    rm -f "$GROOVY_DIR/install-plugins.groovy"
    
    # インストール結果の確認
    PLUGINS_AFTER=$(ls -1 "${JENKINS_HOME}/plugins/" 2>/dev/null | wc -l || echo "0")
    log "Plugin count after installation: $PLUGINS_AFTER"
    log "Plugins installed/updated: $((PLUGINS_AFTER - PLUGINS_BEFORE))"
else
    log "Plugin installation script prepared. Jenkins restart skipped."
    log "The plugins will be installed on the next Jenkins restart."
    log "Note: The Groovy script remains in place at: $GROOVY_DIR/install-plugins.groovy"
    
    # スクリプトの内容から必要なプラグインリストを抽出して表示
    log "Plugins to be installed on next restart:"
    if grep -E "installPlugin\('|installPlugin\(\"" "$GROOVY_DIR/install-plugins.groovy" > /dev/null 2>&1; then
        grep -E "installPlugin\('|installPlugin\(\"" "$GROOVY_DIR/install-plugins.groovy" | \
            sed -E "s/.*installPlugin\(['\"]([^'\"]+)['\"].*/  - \1/" || true
    fi
fi

# 重要なプラグインの確認
IMPORTANT_PLUGINS=("git" "workflow-aggregator" "job-dsl" "configuration-as-code")
log "Checking important plugins:"
for plugin in "${IMPORTANT_PLUGINS[@]}"; do
    if [ -d "${JENKINS_HOME}/plugins/${plugin}" ]; then
        log "  ✓ $plugin: installed"
    else
        if [ "$RESTART_JENKINS" = "true" ]; then
            log "  ✗ $plugin: not found"
        else
            log "  - $plugin: will be installed on next restart"
        fi
    fi
done

if [ "$RESTART_JENKINS" = "true" ]; then
    log "Plugin installation completed"
else
    log "Plugin installation prepared"
fi

if [ "$RESTART_JENKINS" != "true" ]; then
    log ""
    log "To install the plugins now, restart Jenkins manually: systemctl restart jenkins"
fi
