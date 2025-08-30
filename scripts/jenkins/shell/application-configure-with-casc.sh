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

# JCasCプラグインの確認
if [ -d "${JENKINS_HOME}/plugins/configuration-as-code" ]; then
    log "✓ Configuration as Code plugin directory found"
else
    log "✗ ERROR: Configuration as Code plugin not installed"
    error_exit "Please install the configuration-as-code plugin first"
fi

# SSMパラメータから各種設定を取得する関数
retrieve_ssm_parameter() {
    local param_name=$1
    local description=$2
    local required=${3:-false}
    
    local value=$(aws ssm get-parameter \
        --name "$param_name" \
        --region "$AWS_REGION" \
        --query "Parameter.Value" \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$value" ] || [ "$value" = "None" ]; then
        if [ "$required" = "true" ]; then
            log "✗ ERROR: $description not found at $param_name" >&2
            return 1
        else
            log "✗ WARNING: $description not found at $param_name" >&2
        fi
        echo ""  # 空の値を返す
    else
        log "✓ Found $description: $value" >&2
        echo "$value"  # 値のみを返す
    fi
}

# 必要なパラメータをSSMから取得
log "Retrieving configuration from SSM Parameter Store..."

# Fleet IDの取得
EC2_FLEET_ID=$(retrieve_ssm_parameter \
    "/jenkins-infra/${ENVIRONMENT}/agent/spotFleetRequestId" \
    "Fleet ID" \
    "false")

# Workterminal IPの取得
WORKTERMINAL_HOST=$(retrieve_ssm_parameter \
    "/bootstrap/workterminal/public-ip" \
    "Workterminal IP" \
    "false")

# AWSアカウントIDの取得
AWS_PROD_ACCOUNT_IDS=$(retrieve_ssm_parameter \
    "/bootstrap/aws/prod-account-ids" \
    "Production Account IDs" \
    "false")

AWS_DEV_ACCOUNT_IDS=$(retrieve_ssm_parameter \
    "/bootstrap/aws/dev-account-ids" \
    "Development Account IDs" \
    "false")

# 環境変数の設定（まだexportしない）
SHARED_LIBRARY_REPO="${SHARED_LIBRARY_REPO:-https://github.com/tielec/infrastructure-as-code}"
SHARED_LIBRARY_BRANCH="${SHARED_LIBRARY_BRANCH:-main}"
SHARED_LIBRARY_PATH="${SHARED_LIBRARY_PATH:-jenkins/jobs/shared/}"
EC2_IDLE_MINUTES="${EC2_IDLE_MINUTES:-15}"
EC2_MIN_SIZE="${EC2_MIN_SIZE:-0}"
EC2_MAX_SIZE="${EC2_MAX_SIZE:-1}"
EC2_NUM_EXECUTORS="${EC2_NUM_EXECUTORS:-3}"

# Jenkins URLの取得
ALB_DNS=$(retrieve_ssm_parameter \
    "/jenkins-infra/${ENVIRONMENT}/loadbalancer/jenkins-url" \
    "ALB DNS" \
    "false")

# Jenkins URLの設定
setup_jenkins_url() {
    if [ -n "$ALB_DNS" ] && [ "$ALB_DNS" != "None" ]; then
        # ALB DNSにプロトコルが含まれていない場合はhttp://を追加
        if [[ "$ALB_DNS" =~ ^https?:// ]]; then
            echo "${ALB_DNS}"
        else
            echo "http://${ALB_DNS}/"
        fi
    else
        echo "http://localhost:8080/"
    fi
}

JENKINS_URL=$(setup_jenkins_url)
log "✓ Jenkins URL: $JENKINS_URL"

# すべての環境変数を一度にエクスポート（envsubstで使用するため）
export JENKINS_URL
export EC2_FLEET_ID
export WORKTERMINAL_HOST
export AWS_REGION
export AWS_PROD_ACCOUNT_IDS
export AWS_DEV_ACCOUNT_IDS
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

# デバッグ情報を出力する関数
log_debug_info() {
    if [ "${DEBUG_CASC:-false}" = "true" ]; then
        log "Environment variables for template substitution:"
        log "  JENKINS_URL: $JENKINS_URL"
        log "  EC2_FLEET_ID: $EC2_FLEET_ID"
        log "  WORKTERMINAL_HOST: $WORKTERMINAL_HOST"
        log "  AWS_PROD_ACCOUNT_IDS: ${AWS_PROD_ACCOUNT_IDS:-not set}"
        log "  AWS_DEV_ACCOUNT_IDS: ${AWS_DEV_ACCOUNT_IDS:-not set}"
        log "  SHARED_LIBRARY_REPO: $SHARED_LIBRARY_REPO"
        log "  SHARED_LIBRARY_PATH: $SHARED_LIBRARY_PATH"
    fi
}

log_debug_info

# テンプレートから設定ファイルを生成
# shellcheckを無効化して変数リストを明示的に指定
# shellcheck disable=SC2016
envsubst '$JENKINS_URL $EC2_FLEET_ID $WORKTERMINAL_HOST $AWS_REGION $AWS_PROD_ACCOUNT_IDS $AWS_DEV_ACCOUNT_IDS $SHARED_LIBRARY_REPO $SHARED_LIBRARY_BRANCH $SHARED_LIBRARY_PATH $EC2_IDLE_MINUTES $EC2_MIN_SIZE $EC2_MAX_SIZE $EC2_NUM_EXECUTORS' < "$TEMPLATE_FILE" > "$CASC_CONFIG_FILE"

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

# 最終サマリーを出力する関数
print_configuration_summary() {
    log "JCasC configuration file generated."
    log "Configuration will be applied on the next Jenkins restart."
    log "Note: The configuration can also be reloaded from Jenkins UI:"
    log "  Manage Jenkins > Configuration as Code > Reload existing configuration"
    
    log ""
    log "===== Configuration Summary ====="
    
    if [ "$RESTART_JENKINS" = "true" ]; then
        log "Status: Configuration applied"
    else
        log "Status: Configuration prepared (restart required)"
    fi
    
    log ""
    log "Components configured:"
    log "  - EC2 Fleet Cloud: ${EC2_FLEET_ID:-Not configured}"
    log "  - Workterminal node: ${WORKTERMINAL_HOST:-Not configured}"
    log "  - Shared Library: ${SHARED_LIBRARY_REPO##*/}"
    log "  - Security: Markdown formatter enabled"
    
    if [ -n "$AWS_PROD_ACCOUNT_IDS" ] || [ -n "$AWS_DEV_ACCOUNT_IDS" ]; then
        log "  - AWS Account validation: Enabled"
        [ -n "$AWS_PROD_ACCOUNT_IDS" ] && log "    - Production: $(echo $AWS_PROD_ACCOUNT_IDS | tr ',' ' ')"
        [ -n "$AWS_DEV_ACCOUNT_IDS" ] && log "    - Development: $(echo $AWS_DEV_ACCOUNT_IDS | tr ',' ' ')"
    else
        log "  - AWS Account validation: Not configured"
    fi
    
    log ""
    if [ "$RESTART_JENKINS" != "true" ]; then
        log "Next steps:"
        log "  1. Restart Jenkins service: sudo systemctl restart jenkins"
        log "  2. Or reload from UI: Manage Jenkins > Configuration as Code > Reload"
    fi
    
    log "================================="
}

print_configuration_summary
