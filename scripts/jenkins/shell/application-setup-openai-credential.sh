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

# Groovyスクリプトのソースパス
GROOVY_SOURCE="$REPO_PATH/scripts/jenkins/groovy/setup-openai-credential.groovy"

# Groovyスクリプトの存在確認
if [ ! -f "$GROOVY_SOURCE" ]; then
    error_exit "Groovy script not found: $GROOVY_SOURCE"
fi

log "Groovy script found: $GROOVY_SOURCE"

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
# APIキーの長さを確認（デバッグ用）
log "API key length: ${#OPENAI_API_KEY} characters"

# Groovyスクリプトの配置先
GROOVY_DIR="${JENKINS_HOME}/init.groovy.d"
mkdir -p "$GROOVY_DIR"

GROOVY_SCRIPT_DST="${GROOVY_DIR}/03-setup-openai-credential.groovy"

log "Replacing placeholder and copying OpenAI credential setup script to $GROOVY_SCRIPT_DST"

# APIキー内の特殊文字 `&`, `/`, `\` をsedのためにエスケープ
ESCAPED_API_KEY=$(printf '%s\n' "$OPENAI_API_KEY" | sed -e 's/[&/\\]/\\&/g')

# プレースホルダーを実際のAPIキーに置換して、新しいスクリプトファイルを作成
sed "s/##OPENAI_API_KEY_PLACEHOLDER##/${ESCAPED_API_KEY}/g" "$GROOVY_SOURCE" > "$GROOVY_SCRIPT_DST"

chown jenkins:jenkins "$GROOVY_SCRIPT_DST"
chmod 644 "$GROOVY_SCRIPT_DST"

log "OpenAI credential setup script prepared."
log "The credential will be created or updated on the next Jenkins restart."

log "===== OpenAI API Key Credential Setup Complete ====="

# 成功終了
exit 0