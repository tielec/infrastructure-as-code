#!/bin/bash
# Jenkinsプラグインのインストール検証
# SSM経由で実行されることを前提

# エラーハンドリング設定
set -e

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /var/log/jenkins-application-verify.log
}

# エラーハンドラー
error_exit() {
    log "ERROR: $1"
    exit 1
}

log "===== Verifying Jenkins Plugin Installation ====="

# 環境変数の設定
JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"

# 必須プラグインのリスト
REQUIRED_PLUGINS=(
    "git"
    "workflow-aggregator"
    "job-dsl"
    "configuration-as-code"
    "ec2-fleet"
    "ssh-credentials"
    "credentials-binding"
    "pipeline-stage-view"
    "timestamper"
    "ws-cleanup"
)

# プラグインの検証
FAILED_PLUGINS=()
SUCCESS_PLUGINS=()

log "Checking required plugins..."
for plugin in "${REQUIRED_PLUGINS[@]}"; do
    if [ -d "${JENKINS_HOME}/plugins/${plugin}" ]; then
        # プラグインディレクトリが存在する
        if [ -f "${JENKINS_HOME}/plugins/${plugin}.jpi" ] || [ -f "${JENKINS_HOME}/plugins/${plugin}.hpi" ]; then
            log "✓ $plugin: installed successfully"
            SUCCESS_PLUGINS+=("$plugin")
        else
            log "✗ $plugin: directory exists but no .jpi/.hpi file found"
            FAILED_PLUGINS+=("$plugin")
        fi
    else
        log "✗ $plugin: not installed"
        FAILED_PLUGINS+=("$plugin")
    fi
done

# 実際のプラグイン数をカウント
TOTAL_PLUGINS=$(find "${JENKINS_HOME}/plugins/" -maxdepth 1 \( -name "*.jpi" -o -name "*.hpi" \) 2>/dev/null | wc -l || echo "0")
log ""
log "Total plugins installed: $TOTAL_PLUGINS"
log "Required plugins verified: ${#SUCCESS_PLUGINS[@]}/${#REQUIRED_PLUGINS[@]}"

# 検証結果の判定
if [ ${#FAILED_PLUGINS[@]} -gt 0 ]; then
    log ""
    log "WARNING: The following required plugins are missing or incomplete:"
    for plugin in "${FAILED_PLUGINS[@]}"; do
        log "  - $plugin"
    done
    
    # SSMパラメータに警告を記録
    INSTANCE_ID=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" | xargs -I {} curl -s -H "X-aws-ec2-metadata-token: {}" http://169.254.169.254/latest/meta-data/instance-id)
    REGION=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" | xargs -I {} curl -s -H "X-aws-ec2-metadata-token: {}" http://169.254.169.254/latest/meta-data/placement/region)
    
    aws ssm put-parameter \
        --region $REGION \
        --name "/${PROJECT_NAME:-jenkins-infra}/${ENVIRONMENT:-dev}/jenkins/status/plugin-verification" \
        --value "WARNING: ${#FAILED_PLUGINS[@]} required plugins missing" \
        --type String \
        --overwrite 2>/dev/null || true
    
    exit 1
else
    log ""
    log "SUCCESS: All required plugins are installed correctly"
    
    # SSMパラメータに成功を記録
    INSTANCE_ID=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" | xargs -I {} curl -s -H "X-aws-ec2-metadata-token: {}" http://169.254.169.254/latest/meta-data/instance-id)
    REGION=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" | xargs -I {} curl -s -H "X-aws-ec2-metadata-token: {}" http://169.254.169.254/latest/meta-data/placement/region)
    
    aws ssm put-parameter \
        --region $REGION \
        --name "/${PROJECT_NAME:-jenkins-infra}/${ENVIRONMENT:-dev}/jenkins/status/plugin-verification" \
        --value "SUCCESS: All required plugins installed" \
        --type String \
        --overwrite 2>/dev/null || true
fi

log "===== Plugin Verification Completed ====="