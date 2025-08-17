#!/bin/bash
# Jenkinsセキュリティ設定の検証
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

log "===== Verifying Jenkins Security Settings ====="

# 環境変数の設定
JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
VERIFICATION_FAILED=false

# 1. CLIユーザーの存在確認
log "Checking CLI user..."
if [ -d "${JENKINS_HOME}/users/cli-user_"* ]; then
    log "✓ CLI user directory found"
    
    # config.xmlの存在確認
    CLI_USER_DIR=$(ls -d "${JENKINS_HOME}/users/cli-user_"* 2>/dev/null | head -1)
    if [ -f "${CLI_USER_DIR}/config.xml" ]; then
        log "✓ CLI user config.xml exists"
    else
        log "✗ CLI user config.xml not found"
        VERIFICATION_FAILED=true
    fi
else
    log "✗ CLI user directory not found"
    VERIFICATION_FAILED=true
fi

# 2. クレデンシャルの存在確認
log ""
log "Checking credentials..."

# credentials.xmlの存在確認
if [ -f "${JENKINS_HOME}/credentials.xml" ]; then
    log "✓ credentials.xml exists"
    
    # CLIユーザートークンの確認
    if grep -q "cli-user-token" "${JENKINS_HOME}/credentials.xml" 2>/dev/null; then
        log "✓ CLI user token credential found"
    else
        log "✗ CLI user token credential not found"
        VERIFICATION_FAILED=true
    fi
    
    # EC2エージェントSSHキーの確認
    if grep -q "ec2-agent-keypair" "${JENKINS_HOME}/credentials.xml" 2>/dev/null; then
        log "✓ EC2 agent SSH credential found"
    else
        log "✗ EC2 agent SSH credential not found"
        VERIFICATION_FAILED=true
    fi
    
    # BootstrapワークターミナルSSHキーの確認
    if grep -q "ec2-bootstrap-workterminal-keypair" "${JENKINS_HOME}/credentials.xml" 2>/dev/null; then
        log "✓ Bootstrap workterminal SSH credential found"
    else
        log "✗ Bootstrap workterminal SSH credential not found"
        VERIFICATION_FAILED=true
    fi
else
    log "✗ credentials.xml not found"
    VERIFICATION_FAILED=true
fi

# 3. セキュリティレルムの確認
log ""
log "Checking security realm..."
if [ -f "${JENKINS_HOME}/config.xml" ]; then
    if grep -q "<securityRealm" "${JENKINS_HOME}/config.xml" 2>/dev/null; then
        log "✓ Security realm configured"
    else
        log "✗ Security realm not configured"
        VERIFICATION_FAILED=true
    fi
    
    # 認証戦略の確認
    if grep -q "<authorizationStrategy" "${JENKINS_HOME}/config.xml" 2>/dev/null; then
        log "✓ Authorization strategy configured"
    else
        log "✗ Authorization strategy not configured"
        VERIFICATION_FAILED=true
    fi
else
    log "✗ Jenkins config.xml not found"
    VERIFICATION_FAILED=true
fi

# 4. APIトークンの確認（パラメータストアに保存されているか）
log ""
log "Checking API token in Parameter Store..."
REGION=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" | xargs -I {} curl -s -H "X-aws-ec2-metadata-token: {}" http://169.254.169.254/latest/meta-data/placement/region)

if aws ssm get-parameter --region $REGION --name "/${PROJECT_NAME:-jenkins-infra}/${ENVIRONMENT:-dev}/jenkins/cli-user-token" --with-decryption >/dev/null 2>&1; then
    log "✓ CLI user token exists in Parameter Store"
else
    log "✗ CLI user token not found in Parameter Store"
    # これは警告のみ（必須ではない）
fi

# 検証結果の判定
log ""
if [ "$VERIFICATION_FAILED" = "true" ]; then
    log "WARNING: Security configuration verification failed"
    
    # SSMパラメータに警告を記録
    aws ssm put-parameter \
        --region $REGION \
        --name "/${PROJECT_NAME:-jenkins-infra}/${ENVIRONMENT:-dev}/jenkins/status/security-verification" \
        --value "WARNING: Security configuration incomplete" \
        --type String \
        --overwrite 2>/dev/null || true
    
    exit 1
else
    log "SUCCESS: All security settings are configured correctly"
    
    # SSMパラメータに成功を記録
    aws ssm put-parameter \
        --region $REGION \
        --name "/${PROJECT_NAME:-jenkins-infra}/${ENVIRONMENT:-dev}/jenkins/status/security-verification" \
        --value "SUCCESS: Security configuration complete" \
        --type String \
        --overwrite 2>/dev/null || true
fi

log "===== Security Verification Completed ====="