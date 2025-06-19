#!/bin/bash
# Jenkins Workterminalノード追加
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

log "===== Adding Workterminal Node to Jenkins ====="

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

# Workterminalノード設定パラメータ
export WORKTERMINAL_NODE_NAME="${WORKTERMINAL_NODE_NAME:-bootstrap-workterminal}"
export WORKTERMINAL_NODE_DESCRIPTION="${WORKTERMINAL_NODE_DESCRIPTION:-Bootstrap Workterminal Node}"
export WORKTERMINAL_USER="${WORKTERMINAL_USER:-ec2-user}"
export WORKTERMINAL_CREDENTIAL_ID="${WORKTERMINAL_CREDENTIAL_ID:-ec2-bootstrap-workterminal-keypair}"
export WORKTERMINAL_REMOTE_FS="${WORKTERMINAL_REMOTE_FS:-/home/ec2-user/jenkins-agent}"
export WORKTERMINAL_LABELS="${WORKTERMINAL_LABELS:-bootstrap-workterminal}"
export WORKTERMINAL_EXECUTORS="${WORKTERMINAL_EXECUTORS:-1}"
export WORKTERMINAL_PORT="${WORKTERMINAL_PORT:-22}"
export UPDATE_EXISTING_NODE="${UPDATE_EXISTING_NODE:-true}"

# WorkterminalのホストIPを取得（Bootstrap-Instanceから）
log "Retrieving Bootstrap-Instance Public IP..."

# まずBootstrap-Instanceを検索
WORKTERMINAL_HOST=$(aws ec2 describe-instances \
    --region "$AWS_REGION" \
    --filters \
    "Name=tag:Name,Values=Bootstrap-Instance" \
    "Name=instance-state-name,Values=running" \
    --query "Reservations[0].Instances[0].PublicIpAddress" \
    --output text 2>/dev/null | grep -v "None" | grep -v "null" || echo "")

if [ -n "$WORKTERMINAL_HOST" ] && [ "$WORKTERMINAL_HOST" != "None" ] && [ "$WORKTERMINAL_HOST" != "null" ]; then
    log "✓ Found Bootstrap-Instance Public IP: $WORKTERMINAL_HOST"
    export WORKTERMINAL_HOST
else
    log "✗ Bootstrap-Instance not found or has no public IP"
    log "  Falling back to SSM Parameter Store..."
    
    # SSMパラメータから取得を試みる
    WORKTERMINAL_HOST=$(aws ssm get-parameter \
        --name "/bootstrap/workterminal/public-ip" \
        --region "$AWS_REGION" \
        --query "Parameter.Value" \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$WORKTERMINAL_HOST" ]; then
        log "✓ Found Workterminal host IP in Parameter Store: $WORKTERMINAL_HOST"
        export WORKTERMINAL_HOST
    else
        log "✗ WARNING: Workterminal host IP not found in Parameter Store"
        log "  Checked parameter: /bootstrap/workterminal/public-ip"
        
        # 環境変数から取得を試みる
        if [ -n "${WORKTERMINAL_HOST_OVERRIDE}" ]; then
            export WORKTERMINAL_HOST="${WORKTERMINAL_HOST_OVERRIDE}"
            log "  Using override host: $WORKTERMINAL_HOST"
        else
            log "  Node will be created without host configuration"
        fi
    fi
fi

log "Workterminal Node Configuration:"
log "  Name: $WORKTERMINAL_NODE_NAME"
log "  Host: ${WORKTERMINAL_HOST:-Not set}"
log "  Port: $WORKTERMINAL_PORT"
log "  User: $WORKTERMINAL_USER"
log "  Credential ID: $WORKTERMINAL_CREDENTIAL_ID"
log "  Remote FS: $WORKTERMINAL_REMOTE_FS"
log "  Labels: $WORKTERMINAL_LABELS"
log "  Executors: $WORKTERMINAL_EXECUTORS"

# SSHプラグインの確認
if [ -d "${JENKINS_HOME}/plugins/ssh-slaves" ]; then
    log "✓ SSH Slaves plugin directory found"
else
    log "✗ WARNING: SSH Slaves plugin directory not found"
    log "  Please ensure the ssh-slaves plugin is installed"
fi

# Groovyスクリプトを配置
GROOVY_DIR="${JENKINS_HOME}/init.groovy.d"
mkdir -p "$GROOVY_DIR"

# Gitリポジトリからスクリプトをコピー
GROOVY_SCRIPT="${REPO_PATH}/scripts/jenkins/groovy/add-workterminal-node.groovy"

if [ ! -f "$GROOVY_SCRIPT" ]; then
    error_exit "Groovy script not found: $GROOVY_SCRIPT"
fi

# Workterminalノード追加スクリプトをコピー
log "Copying Workterminal node configuration script..."
cp "$GROOVY_SCRIPT" "$GROOVY_DIR/"
chown jenkins:jenkins "$GROOVY_DIR/add-workterminal-node.groovy"
chmod 644 "$GROOVY_DIR/add-workterminal-node.groovy"

# Jenkinsを再起動して実行
log "Restarting Jenkins to add Workterminal node..."
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

# ノード追加の完了を待機
log "Waiting for Workterminal node configuration to complete..."
sleep 30

# スクリプトを削除
rm -f "$GROOVY_DIR/add-workterminal-node.groovy"

# 結果の確認
log "Verifying Workterminal node configuration..."

# ノードディレクトリの存在確認
if [ -d "${JENKINS_HOME}/nodes/${WORKTERMINAL_NODE_NAME}" ]; then
    log "✓ Workterminal node directory found"
    
    # config.xmlの確認
    if [ -f "${JENKINS_HOME}/nodes/${WORKTERMINAL_NODE_NAME}/config.xml" ]; then
        log "✓ Node config.xml exists"
        
        if [ -n "$WORKTERMINAL_HOST" ]; then
            if grep -q "$WORKTERMINAL_HOST" "${JENKINS_HOME}/nodes/${WORKTERMINAL_NODE_NAME}/config.xml"; then
                log "✓ Host correctly configured: $WORKTERMINAL_HOST"
            else
                log "✗ WARNING: Host not found in config.xml"
            fi
        fi
    fi
else
    log "✗ WARNING: Workterminal node directory not found"
fi

# 設定ログの確認
if [ -f "/var/log/jenkins/jenkins.log" ]; then
    log "Recent Jenkins logs related to Workterminal node:"
    grep -i "workterminal" /var/log/jenkins/jenkins.log | tail -20 || true
fi

log "Workterminal node configuration completed"
log ""
log "Next steps:"
log "1. Check node status in Jenkins UI: Manage Jenkins > Nodes"
log "2. Ensure the Bootstrap-Instance is accessible from Jenkins"
log "3. If the node is offline, check:"
log "   - Bootstrap-Instance is running with proper Name tag"
log "   - Security groups allow SSH from Jenkins instance"
log "   - SSH key permissions are correct"
