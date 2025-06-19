#!/bin/bash
# Jenkins Configuration as Code (JCasC) を使用した設定
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

log "===== Configuring Jenkins with JCasC ====="

# 環境変数の確認
JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
REPO_PATH="${REPO_PATH:-/root/infrastructure-as-code}"
PROJECT_NAME="${PROJECT_NAME:-jenkins-infra}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

# インスタンスメタデータ取得（IMDSv2対応）
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
AWS_REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)

export AWS_REGION
export PROJECT_NAME
export ENVIRONMENT

log "Environment:"
log "  JENKINS_HOME: $JENKINS_HOME"
log "  REPO_PATH: $REPO_PATH"
log "  PROJECT_NAME: $PROJECT_NAME"
log "  ENVIRONMENT: $ENVIRONMENT"
log "  AWS_REGION: $AWS_REGION"

# JCasCプラグインの確認
if [ -d "${JENKINS_HOME}/plugins/configuration-as-code" ]; then
    log "✓ Configuration as Code plugin directory found"
else
    log "✗ ERROR: Configuration as Code plugin not installed"
    error_exit "Please install the configuration-as-code plugin first"
fi

# Fleet IDの取得
log "Retrieving Fleet ID..."
EC2_FLEET_ID=$(aws ssm get-parameter \
    --name "/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/agent/spotFleetRequestId" \
    --region "$AWS_REGION" \
    --query "Parameter.Value" \
    --output text 2>/dev/null || echo "")

if [ -z "$EC2_FLEET_ID" ]; then
    log "✗ WARNING: Fleet ID not found in Parameter Store"
else
    log "✓ Found Fleet ID: $EC2_FLEET_ID"
fi

# WorkterminalのホストIPを取得
log "Retrieving Bootstrap-Instance Public IP..."
WORKTERMINAL_HOST=$(aws ec2 describe-instances \
    --region "$AWS_REGION" \
    --filters \
    "Name=tag:Name,Values=Bootstrap-Instance" \
    "Name=instance-state-name,Values=running" \
    --query "Reservations[0].Instances[0].PublicIpAddress" \
    --output text 2>/dev/null | grep -v "None" | grep -v "null" || echo "")

if [ -z "$WORKTERMINAL_HOST" ] || [ "$WORKTERMINAL_HOST" = "None" ]; then
    log "✗ WARNING: Bootstrap-Instance not found or has no public IP"
else
    log "✓ Found Bootstrap-Instance IP: $WORKTERMINAL_HOST"
fi

# 環境変数の設定
export EC2_FLEET_ID
export WORKTERMINAL_HOST
export AWS_REGION
export SHARED_LIBRARY_REPO="${SHARED_LIBRARY_REPO:-https://github.com/tielec/infrastructure-as-code}"
export SHARED_LIBRARY_BRANCH="${SHARED_LIBRARY_BRANCH:-main}"
export EC2_IDLE_MINUTES="${EC2_IDLE_MINUTES:-15}"
export EC2_MIN_SIZE="${EC2_MIN_SIZE:-0}"
export EC2_MAX_SIZE="${EC2_MAX_SIZE:-1}"
export EC2_NUM_EXECUTORS="${EC2_NUM_EXECUTORS:-3}"

# Jenkins URLの設定（ALB経由の場合）
JENKINS_URL=$(aws ssm get-parameter \
    --name "/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/url" \
    --region "$AWS_REGION" \
    --query "Parameter.Value" \
    --output text 2>/dev/null || echo "http://localhost:8080/")

# URLが正しく取得できたかログ出力
log "✓ Found Jenkins URL: $JENKINS_URL"

# すべての環境変数をエクスポート（envsubstで使用するため）
export JENKINS_URL
export EC2_FLEET_ID
export WORKTERMINAL_HOST
export AWS_REGION
export SHARED_LIBRARY_REPO
export SHARED_LIBRARY_BRANCH
export SHARED_LIBRARY_PATH
export EC2_IDLE_MINUTES
export EC2_MIN_SIZE
export EC2_MAX_SIZE
export EC2_NUM_EXECUTORS

# JCasC設定ファイルの生成
log "Generating JCasC configuration file..."
TEMPLATE_FILE="${REPO_PATH}/scripts/jenkins/casc/jenkins.yaml.template"
CASC_CONFIG_FILE="${JENKINS_HOME}/jenkins.yaml"

if [ ! -f "$TEMPLATE_FILE" ]; then
    error_exit "JCasC template not found: $TEMPLATE_FILE"
fi

# デバッグ: 環境変数の確認
log "Environment variables for template substitution:"
log "  JENKINS_URL: $JENKINS_URL"
log "  EC2_FLEET_ID: $EC2_FLEET_ID"
log "  WORKTERMINAL_HOST: $WORKTERMINAL_HOST"
log "  SHARED_LIBRARY_REPO: $SHARED_LIBRARY_REPO"
log "  SHARED_LIBRARY_PATH: $SHARED_LIBRARY_PATH"

# テンプレートから設定ファイルを生成
# shellcheckを無効化して変数リストを明示的に指定
# shellcheck disable=SC2016
envsubst '$JENKINS_URL $EC2_FLEET_ID $WORKTERMINAL_HOST $AWS_REGION $SHARED_LIBRARY_REPO $SHARED_LIBRARY_BRANCH $SHARED_LIBRARY_PATH $EC2_IDLE_MINUTES $EC2_MIN_SIZE $EC2_MAX_SIZE $EC2_NUM_EXECUTORS' < "$TEMPLATE_FILE" > "$CASC_CONFIG_FILE"

# 権限設定
chown jenkins:jenkins "$CASC_CONFIG_FILE"
chmod 600 "$CASC_CONFIG_FILE"

# デバッグ: 生成されたファイルの一部を確認
if [ "${DEBUG_CASC:-false}" = "true" ]; then
    log "Generated JCasC configuration (first 50 lines):"
    head -n 50 "$CASC_CONFIG_FILE" | while IFS= read -r line; do
        log "  $line"
    done
fi

# JCasC設定を適用（Jenkinsを再起動）
log "Applying JCasC configuration by restarting Jenkins..."
systemctl restart jenkins

# 起動を待機
log "Waiting for Jenkins to apply configuration..."
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

# 設定の適用を待機
sleep 30

log "JCasC configuration completed"
log ""
log "Configuration applied:"
log "  - EC2 Fleet Cloud configured (Fleet ID: ${EC2_FLEET_ID:-Not set})"
log "  - Shared Library configured"
log "  - Security settings applied (Markdown formatter)"
log "  - Workterminal node added (Host: ${WORKTERMINAL_HOST:-Not set})"
log ""
log "Check Jenkins UI to verify all settings are properly applied"
