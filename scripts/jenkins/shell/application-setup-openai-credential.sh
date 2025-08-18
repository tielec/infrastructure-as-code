#!/bin/bash
# Jenkins OpenAI APIキークレデンシャルのセットアップ
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

log "===== Setting up OpenAI API Key Credential ====="

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

# Jenkins CLI設定
JENKINS_CLI="java -jar $JENKINS_HOME/jenkins-cli.jar"
JENKINS_URL="http://localhost:8080"
JENKINS_INIT_GROOVY="$JENKINS_HOME/init.groovy.d"

# Groovyスクリプトのソースパス
GROOVY_SOURCE="$REPO_PATH/scripts/jenkins/groovy/setup-openai-credential.groovy"

# Groovyスクリプトの存在確認
if [ ! -f "$GROOVY_SOURCE" ]; then
    error_exit "Groovy script not found: $GROOVY_SOURCE"
fi

log "Groovy script found: $GROOVY_SOURCE"

# Jenkins CLI用の認証情報を取得
log "Retrieving Jenkins CLI credentials from SSM..."
CLI_USERNAME=$(aws ssm get-parameter --name "/$PROJECT_NAME/$ENVIRONMENT/jenkins/cli-username" --region "$AWS_REGION" --query 'Parameter.Value' --output text 2>/dev/null || echo "")
CLI_PASSWORD=$(aws ssm get-parameter --name "/$PROJECT_NAME/$ENVIRONMENT/jenkins/cli-password" --with-decryption --region "$AWS_REGION" --query 'Parameter.Value' --output text 2>/dev/null || echo "")

if [ -z "$CLI_USERNAME" ] || [ -z "$CLI_PASSWORD" ]; then
    log "CLI credentials not found in SSM. Using init.groovy.d method..."
    AUTH_METHOD="init"
else
    log "CLI credentials found. Using Jenkins CLI method..."
    AUTH_METHOD="cli"
fi

# OpenAI APIキーをSSMから取得
log "Retrieving OpenAI API key from SSM Parameter Store..."
OPENAI_API_KEY=$(aws ssm get-parameter --name "/bootstrap/openai/api-key" --with-decryption --region "$AWS_REGION" --query 'Parameter.Value' --output text 2>/dev/null || echo "")

if [ -z "$OPENAI_API_KEY" ]; then
    log "WARNING: OpenAI API key not found in SSM Parameter Store at /bootstrap/openai/api-key"
    log "Skipping OpenAI credential setup. To enable, set the API key using:"
    log "  aws ssm put-parameter --name '/bootstrap/openai/api-key' --value 'sk-...' --type SecureString"
    exit 0
fi

log "✓ OpenAI API key retrieved successfully"

# 環境変数としてAPIキーを設定
export OPENAI_API_KEY="$OPENAI_API_KEY"

if [ "$AUTH_METHOD" = "cli" ]; then
    # Jenkins CLIを使用してGroovyスクリプトを実行
    log "Executing Groovy script via Jenkins CLI..."
    
    if $JENKINS_CLI -s "$JENKINS_URL" -auth "$CLI_USERNAME:$CLI_PASSWORD" groovy = < "$GROOVY_SOURCE"; then
        log "✓ Groovy script executed successfully via CLI"
    else
        error_exit "Failed to execute Groovy script via CLI"
    fi
else
    # init.groovy.dディレクトリにコピーして実行
    log "Copying Groovy script to init.groovy.d..."
    
    # init.groovy.dディレクトリの作成
    mkdir -p "$JENKINS_INIT_GROOVY"
    
    # スクリプトをコピー
    cp "$GROOVY_SOURCE" "$JENKINS_INIT_GROOVY/setup-openai-credential.groovy"
    
    # 実行権限を設定
    chmod 644 "$JENKINS_INIT_GROOVY/setup-openai-credential.groovy"
    chown jenkins:jenkins "$JENKINS_INIT_GROOVY/setup-openai-credential.groovy"
    
    log "✓ Groovy script copied to: $JENKINS_INIT_GROOVY/setup-openai-credential.groovy"
    log "The credential will be created on next Jenkins restart"
fi

# 環境変数をクリア（セキュリティのため）
unset OPENAI_API_KEY

# クレデンシャルの検証（CLIが使用可能な場合）
if [ "$AUTH_METHOD" = "cli" ]; then
    log "Verifying credential creation..."
    
    # 少し待機してからクレデンシャルを確認
    sleep 2
    
    # クレデンシャルリストを確認
    CREDENTIAL_CHECK=$($JENKINS_CLI -s "$JENKINS_URL" -auth "$CLI_USERNAME:$CLI_PASSWORD" list-credentials system::system::jenkins 2>/dev/null | grep "openai-api-key" || echo "")
    
    if [ -n "$CREDENTIAL_CHECK" ]; then
        log "✓ Credential 'openai-api-key' verified in Jenkins"
    else
        log "Note: Credential verification pending. Will be available after Jenkins restart."
    fi
fi

log "===== OpenAI API Key Credential Setup Complete ====="
log "Credential ID: openai-api-key"
log "Scope: Global"
log "Type: Secret Text"

# 成功終了
exit 0