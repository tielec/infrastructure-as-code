#!/bin/bash
# Jenkins adminユーザーをセットアップする
# SSM経由で実行されることを前提

set -e

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "===== Setting up Jenkins Admin User ====="

# 環境変数の確認
JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
REPO_PATH="${REPO_PATH:-/root/infrastructure-as-code}"
PROJECT_NAME="${PROJECT_NAME:-jenkins-infra}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

# AWSリージョンを取得
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
AWS_REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)

# SSMからadminパスワードを取得
log "Retrieving admin password from SSM Parameter Store..."
ADMIN_PASSWORD=$(aws ssm get-parameter \
    --name "/${PROJECT_NAME}/${ENVIRONMENT}/config/admin-password" \
    --with-decryption \
    --region "${AWS_REGION}" \
    --query "Parameter.Value" \
    --output text 2>/dev/null)

if [ -z "$ADMIN_PASSWORD" ] || [ "$ADMIN_PASSWORD" = "None" ]; then
    log "ERROR: Admin password not found in SSM Parameter Store. Skipping setup."
    exit 1
fi

log "Admin password retrieved successfully."

# Groovyスクリプトを配置
GROOVY_DIR="${JENKINS_HOME}/init.groovy.d"
mkdir -p "$GROOVY_DIR"

GROOVY_SCRIPT_SRC="${REPO_PATH}/scripts/jenkins/groovy/setup-admin-user.groovy"
GROOVY_SCRIPT_DST="${GROOVY_DIR}/02-setup-admin-user.groovy"

if [ ! -f "$GROOVY_SCRIPT_SRC" ]; then
    log "ERROR: Groovy script not found: $GROOVY_SCRIPT_SRC"
    exit 1
fi

log "Replacing placeholder and copying admin user setup script to $GROOVY_SCRIPT_DST"

# パスワード内の特殊文字 `&`, `/`, `` をsedのためにエスケープ
ESCAPED_PASSWORD=$(printf '%s
' "$ADMIN_PASSWORD" | sed -e 's/[&/\\]/\\&/g')

# プレースホルダーを実際のパスワードに置換して、新しいスクリプトファイルを作成
sed "s/##JENKINS_ADMIN_PASSWORD_PLACEHOLDER##/${ESCAPED_PASSWORD}/g" "$GROOVY_SCRIPT_SRC" > "$GROOVY_SCRIPT_DST"

chown jenkins:jenkins "$GROOVY_SCRIPT_DST"
chmod 644 "$GROOVY_SCRIPT_DST"

log "Admin user setup script prepared."
log "The admin user will be created or updated on the next Jenkins restart."

log "===== Admin User Setup Completed ====="