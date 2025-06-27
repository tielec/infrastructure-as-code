#!/bin/bash
# Jenkins SSHクレデンシャルのセットアップ（パラメータストアから）
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

log "===== Setting up SSH Credentials from Parameter Store ====="

# 環境変数の確認
JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
REPO_PATH="${REPO_PATH:-/root/infrastructure-as-code}"
PROJECT_NAME="${PROJECT_NAME:-jenkins-infra}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
RESTART_JENKINS="${RESTART_JENKINS:-false}"

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
log "  RESTART_JENKINS: $RESTART_JENKINS"

# パラメータストアへのアクセス確認
log "Checking Parameter Store access..."

# EC2 Agent用秘密鍵の存在確認
AGENT_KEY_PATH="/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/agent/private-key"
if aws ssm get-parameter --name "$AGENT_KEY_PATH" --region "$AWS_REGION" --query "Parameter.Name" --output text >/dev/null 2>&1; then
    log "✓ EC2 Agent private key found at: $AGENT_KEY_PATH"
else
    log "✗ WARNING: EC2 Agent private key not found at: $AGENT_KEY_PATH"
fi

# Bootstrap Workterminal用秘密鍵の存在確認
WORKTERMINAL_KEY_PATH="/bootstrap/workterminal/private-key"
if aws ssm get-parameter --name "$WORKTERMINAL_KEY_PATH" --region "$AWS_REGION" --query "Parameter.Name" --output text >/dev/null 2>&1; then
    log "✓ Bootstrap Workterminal private key found at: $WORKTERMINAL_KEY_PATH"
else
    log "✗ WARNING: Bootstrap Workterminal private key not found at: $WORKTERMINAL_KEY_PATH"
fi

# Groovyスクリプトを配置
GROOVY_DIR="${JENKINS_HOME}/init.groovy.d"
mkdir -p "$GROOVY_DIR"

# Gitリポジトリからスクリプトをコピー
GROOVY_SCRIPT="${REPO_PATH}/scripts/jenkins/groovy/setup-ssh-credentials.groovy"

if [ ! -f "$GROOVY_SCRIPT" ]; then
    error_exit "Groovy script not found: $GROOVY_SCRIPT"
fi

# SSHクレデンシャル設定スクリプトをコピー
log "Copying SSH credentials setup script..."
cp "$GROOVY_SCRIPT" "$GROOVY_DIR/"
chown jenkins:jenkins "$GROOVY_DIR/setup-ssh-credentials.groovy"
chmod 644 "$GROOVY_DIR/setup-ssh-credentials.groovy"

# 既存のクレデンシャルを更新するかどうかの設定
if [ "${UPDATE_EXISTING_CREDENTIALS:-false}" = "true" ]; then
    export UPDATE_EXISTING_CREDENTIALS=true
    log "Will update existing credentials if found"
else
    export UPDATE_EXISTING_CREDENTIALS=false
    log "Will skip existing credentials"
fi

# カスタムクレデンシャルマッピング（オプション）
# 追加のSSHクレデンシャルが必要な場合は、JSON形式で環境変数に設定可能
if [ -n "$ADDITIONAL_SSH_CREDENTIALS" ]; then
    export ADDITIONAL_SSH_CREDENTIALS
    log "Additional SSH credential mappings provided"
fi

if [ "$RESTART_JENKINS" = "true" ]; then
    # Jenkinsを再起動して実行
    log "Restarting Jenkins to setup SSH credentials..."
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
    log "Waiting for SSH credentials setup to complete..."
    sleep 30
    
    # スクリプトを削除
    rm -f "$GROOVY_DIR/setup-ssh-credentials.groovy"
    
    # 結果の確認
    log "Verifying SSH credentials setup..."
    
    # クレデンシャルの存在を確認
    if [ -f "${JENKINS_HOME}/credentials.xml" ]; then
        if grep -q "ec2-agent-keypair" "${JENKINS_HOME}/credentials.xml"; then
            log "✓ EC2 Agent SSH credential found"
        else
            log "✗ WARNING: EC2 Agent SSH credential not found in credentials.xml"
        fi
        
        if grep -q "ec2-bootstrap-workterminal-keypair" "${JENKINS_HOME}/credentials.xml"; then
            log "✓ Bootstrap Workterminal SSH credential found"
        else
            log "✗ WARNING: Bootstrap Workterminal SSH credential not found in credentials.xml"
        fi
    else
        log "✗ WARNING: credentials.xml not found"
    fi
    
    # セットアップログの最終行を確認
    if [ -f "/var/log/jenkins/jenkins.log" ]; then
        log "Recent Jenkins logs related to SSH credentials:"
        grep -i "SSH Credentials Setup" /var/log/jenkins/jenkins.log | tail -20 || true
    fi
else
    log "SSH credentials setup script prepared. Jenkins restart skipped."
    log "The SSH credentials will be configured on the next Jenkins restart."
    log "Note: The Groovy script remains in place at: $GROOVY_DIR/setup-ssh-credentials.groovy"
    
    log ""
    log "Expected SSH credentials to be created on next restart:"
    log "  - EC2 Agent keypair (ID: ec2-agent-keypair)"
    log "  - Bootstrap Workterminal keypair (ID: ec2-bootstrap-workterminal-keypair)"
    
    if [ -n "$ADDITIONAL_SSH_CREDENTIALS" ]; then
        log "  - Additional credentials as specified in ADDITIONAL_SSH_CREDENTIALS"
    fi
fi

log "SSH credentials setup ${RESTART_JENKINS == 'true' ? 'completed' : 'prepared'}"

if [ "$RESTART_JENKINS" != "true" ]; then
    log ""
    log "To apply the configuration now, restart Jenkins manually: systemctl restart jenkins"
fi
