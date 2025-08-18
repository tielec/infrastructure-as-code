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

# Jenkinsの起動スクリプトが読み込む環境変数ファイルにパスワードを追記
# これにより、JenkinsのJVMが環境変数を認識できるようになる
JENKINS_ENV_FILE="/etc/sysconfig/jenkins"
if [ ! -f "$JENKINS_ENV_FILE" ]; then
    # Debian/Ubuntu系の場合
    JENKINS_ENV_FILE="/etc/default/jenkins"
fi

if [ -f "$JENKINS_ENV_FILE" ]; then
    log "Updating Jenkins environment file: $JENKINS_ENV_FILE"
    # 既存の設定を削除
    sed -i '/^export JENKINS_ADMIN_PASSWORD=/d' "$JENKINS_ENV_FILE"
    # 新しい設定を追記
    echo "export JENKINS_ADMIN_PASSWORD='${ADMIN_PASSWORD}'" >> "$JENKINS_ENV_FILE"
    log "JENKINS_ADMIN_PASSWORD set in environment file."
else
    log "WARNING: Jenkins environment file not found. Could not set JENKINS_ADMIN_PASSWORD."
fi

# Groovyスクリプトを配置
GROOVY_DIR="${JENKINS_HOME}/init.groovy.d"
mkdir -p "$GROOVY_DIR"

GROOVY_SCRIPT_SRC="${REPO_PATH}/scripts/jenkins/groovy/setup-admin-user.groovy"
GROOVY_SCRIPT_DST="${GROOVY_DIR}/02-setup-admin-user.groovy"

if [ ! -f "$GROOVY_SCRIPT_SRC" ]; then
    log "ERROR: Groovy script not found: $GROOVY_SCRIPT_SRC"
    exit 1
fi

log "Copying admin user setup script to $GROOVY_SCRIPT_DST"
cp "$GROOVY_SCRIPT_SRC" "$GROOVY_SCRIPT_DST"
chown jenkins:jenkins "$GROOVY_SCRIPT_DST"
chmod 644 "$GROOVY_SCRIPT_DST"

log "Admin user setup script prepared."
log "The admin user will be created or updated on the next Jenkins restart."

log "===== Admin User Setup Completed ====="