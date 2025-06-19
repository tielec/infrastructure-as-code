#!/bin/bash
# Jenkins EC2 Fleet Cloud設定
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

log "===== Configuring EC2 Fleet Cloud ====="

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

# EC2 Fleetプラグインの確認
if [ -d "${JENKINS_HOME}/plugins/ec2-fleet" ]; then
    log "✓ EC2 Fleet plugin directory found"
else
    log "✗ WARNING: EC2 Fleet plugin directory not found"
    log "  Please ensure the EC2 Fleet plugin is installed"
fi

# アクティブなEC2 Fleetの検索
log "Searching for active EC2 Fleets..."
FLEET_ID=$(aws ec2 describe-fleets \
    --region "$AWS_REGION" \
    --filters "Name=state,Values=active" \
    --query "Fleets[?Tags[?Key=='Project' && Value=='${PROJECT_NAME}']].FleetId" \
    --output text | head -1 || echo "")

if [ -n "$FLEET_ID" ]; then
    log "✓ Found active EC2 Fleet: $FLEET_ID"
    export EC2_FLEET_ID="$FLEET_ID"
else
    log "✗ WARNING: No active EC2 Fleet found for project ${PROJECT_NAME}"
    log "  Checking SSM parameter store for Fleet ID..."
    
    FLEET_ID=$(aws ssm get-parameter \
        --name "/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/agent/spotFleetRequestId" \
        --region "$AWS_REGION" \
        --query "Parameter.Value" \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$FLEET_ID" ]; then
        log "✓ Found Fleet ID in SSM parameter store: $FLEET_ID"
        export EC2_FLEET_ID="$FLEET_ID"
    else
        log "✗ WARNING: No Fleet ID found in SSM parameter store"
    fi
fi

# EC2 Fleet設定パラメータの設定（環境変数またはデフォルト値）
export EC2_FLEET_CLOUD_NAME="${EC2_FLEET_CLOUD_NAME:-ec2-fleet}"
export EC2_FLEET_REGION="${EC2_FLEET_REGION:-$AWS_REGION}"
export EC2_FLEET_SSH_CREDENTIAL="${EC2_FLEET_SSH_CREDENTIAL:-ec2-agent-keypair}"
export EC2_FLEET_NUM_EXECUTORS="${EC2_FLEET_NUM_EXECUTORS:-3}"
export EC2_FLEET_MAX_IDLE_MINUTES="${EC2_FLEET_MAX_IDLE_MINUTES:-15}"
export EC2_FLEET_MIN_SIZE="${EC2_FLEET_MIN_SIZE:-0}"
export EC2_FLEET_MAX_SIZE="${EC2_FLEET_MAX_SIZE:-1}"
export EC2_FLEET_MAX_INIT_TIMEOUT="${EC2_FLEET_MAX_INIT_TIMEOUT:-900}"
export EC2_FLEET_STATUS_INTERVAL="${EC2_FLEET_STATUS_INTERVAL:-30}"

# 既存の設定を更新するかどうか
export UPDATE_EXISTING_CLOUD="${UPDATE_EXISTING_CLOUD:-true}"

log "EC2 Fleet Configuration:"
log "  Cloud Name: $EC2_FLEET_CLOUD_NAME"
log "  Fleet ID: ${EC2_FLEET_ID:-Not set}"
log "  Region: $EC2_FLEET_REGION"
log "  SSH Credential: $EC2_FLEET_SSH_CREDENTIAL"
log "  Executors per Node: $EC2_FLEET_NUM_EXECUTORS"
log "  Max Idle Minutes: $EC2_FLEET_MAX_IDLE_MINUTES"
log "  Min Size: $EC2_FLEET_MIN_SIZE"
log "  Max Size: $EC2_FLEET_MAX_SIZE"

# Groovyスクリプトを配置
GROOVY_DIR="${JENKINS_HOME}/init.groovy.d"
mkdir -p "$GROOVY_DIR"

# Gitリポジトリからスクリプトをコピー
GROOVY_SCRIPT="${REPO_PATH}/scripts/jenkins/groovy/configure-ec2-fleet.groovy"

if [ ! -f "$GROOVY_SCRIPT" ]; then
    error_exit "Groovy script not found: $GROOVY_SCRIPT"
fi

# EC2 Fleet設定スクリプトをコピー
log "Copying EC2 Fleet configuration script..."
cp "$GROOVY_SCRIPT" "$GROOVY_DIR/"
chown jenkins:jenkins "$GROOVY_DIR/configure-ec2-fleet.groovy"
chmod 644 "$GROOVY_DIR/configure-ec2-fleet.groovy"

# Jenkinsを再起動して実行
log "Restarting Jenkins to configure EC2 Fleet..."
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
log "Waiting for EC2 Fleet configuration to complete..."
sleep 30

# スクリプトを削除
rm -f "$GROOVY_DIR/configure-ec2-fleet.groovy"

# 設定ログの確認
if [ -f "/var/log/jenkins/jenkins.log" ]; then
    log "Recent Jenkins logs related to EC2 Fleet:"
    grep -i "EC2 Fleet" /var/log/jenkins/jenkins.log | tail -20 || true
fi

log "EC2 Fleet Cloud configuration completed"
