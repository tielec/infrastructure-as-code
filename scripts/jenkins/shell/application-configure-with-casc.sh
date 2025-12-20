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

# Fleet IDの取得（後方互換性のため既存パラメータも取得）
EC2_FLEET_ID=$(retrieve_ssm_parameter \
    "/jenkins-infra/${ENVIRONMENT}/agent/spotFleetRequestId" \
    "Fleet ID (legacy)" \
    "false")

# Medium Fleet IDの取得
EC2_FLEET_MEDIUM_ID=$(retrieve_ssm_parameter \
    "/jenkins-infra/${ENVIRONMENT}/agent/spotFleetRequestId-medium" \
    "Medium Fleet ID" \
    "false")

# Small Fleet IDの取得
EC2_FLEET_SMALL_ID=$(retrieve_ssm_parameter \
    "/jenkins-infra/${ENVIRONMENT}/agent/spotFleetRequestId-small" \
    "Small Fleet ID" \
    "false")

# Micro Fleet IDの取得
EC2_FLEET_MICRO_ID=$(retrieve_ssm_parameter \
    "/jenkins-infra/${ENVIRONMENT}/agent/spotFleetRequestId-micro" \
    "Micro Fleet ID" \
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

# ECS Fargate関連のパラメータ取得
log "Retrieving ECS Fargate configuration from SSM Parameter Store..."
ECS_CLUSTER_ARN=$(retrieve_ssm_parameter \
    "/jenkins-infra/${ENVIRONMENT}/agent/ecs-cluster-arn" \
    "ECS Cluster ARN" \
    "false")

ECS_TASK_DEFINITION_ARN=$(retrieve_ssm_parameter \
    "/jenkins-infra/${ENVIRONMENT}/agent/ecs-task-definition-arn" \
    "ECS Task Definition ARN" \
    "false")

ECS_EXECUTION_ROLE_ARN=$(retrieve_ssm_parameter \
    "/jenkins-infra/${ENVIRONMENT}/agent/ecs-execution-role-arn" \
    "ECS Execution Role ARN" \
    "false")

ECS_TASK_ROLE_ARN=$(retrieve_ssm_parameter \
    "/jenkins-infra/${ENVIRONMENT}/agent/ecs-task-role-arn" \
    "ECS Task Role ARN" \
    "false")

JENKINS_AGENT_SG_ID=$(retrieve_ssm_parameter \
    "/jenkins-infra/${ENVIRONMENT}/security/jenkins-agent-sg-id" \
    "Jenkins Agent Security Group ID" \
    "false")

PRIVATE_SUBNET_A_ID=$(retrieve_ssm_parameter \
    "/jenkins-infra/${ENVIRONMENT}/network/private-subnet-a-id" \
    "Private Subnet A ID" \
    "false")

PRIVATE_SUBNET_B_ID=$(retrieve_ssm_parameter \
    "/jenkins-infra/${ENVIRONMENT}/network/private-subnet-b-id" \
    "Private Subnet B ID" \
    "false")

# 環境変数の設定（まだexportしない）
SHARED_LIBRARY_REPO="${SHARED_LIBRARY_REPO:-https://github.com/tielec/infrastructure-as-code}"
SHARED_LIBRARY_BRANCH="${SHARED_LIBRARY_BRANCH:-main}"
SHARED_LIBRARY_PATH="${SHARED_LIBRARY_PATH:-jenkins/jobs/shared/}"
EC2_IDLE_MINUTES="${EC2_IDLE_MINUTES:-15}"
# 後方互換性のための既存変数
EC2_MIN_SIZE="${EC2_MIN_SIZE:-0}"
EC2_MAX_SIZE="${EC2_MAX_SIZE:-1}"
# インスタンスサイズ別の設定（デフォルト値）
EC2_FLEET_MEDIUM_MIN_SIZE="${EC2_FLEET_MEDIUM_MIN_SIZE:-0}"
EC2_FLEET_MEDIUM_MAX_SIZE="${EC2_FLEET_MEDIUM_MAX_SIZE:-1}"
EC2_FLEET_SMALL_MIN_SIZE="${EC2_FLEET_SMALL_MIN_SIZE:-0}"
EC2_FLEET_SMALL_MAX_SIZE="${EC2_FLEET_SMALL_MAX_SIZE:-1}"
EC2_FLEET_MICRO_MIN_SIZE="${EC2_FLEET_MICRO_MIN_SIZE:-0}"
EC2_FLEET_MICRO_MAX_SIZE="${EC2_FLEET_MICRO_MAX_SIZE:-1}"
# 後方互換性のためのExecutor数（mediumと同じ）
EC2_NUM_EXECUTORS="${EC2_NUM_EXECUTORS:-3}"
# インスタンスサイズ別のExecutor数
EC2_FLEET_MEDIUM_NUM_EXECUTORS="${EC2_FLEET_MEDIUM_NUM_EXECUTORS:-3}"
EC2_FLEET_SMALL_NUM_EXECUTORS="${EC2_FLEET_SMALL_NUM_EXECUTORS:-2}"
EC2_FLEET_MICRO_NUM_EXECUTORS="${EC2_FLEET_MICRO_NUM_EXECUTORS:-1}"

# Jenkins URLの取得
ALB_DNS=$(retrieve_ssm_parameter \
    "/jenkins-infra/${ENVIRONMENT}/loadbalancer/jenkins-url" \
    "ALB DNS" \
    "false")

# VPC内部用のプライベートURL取得（新規追加 - Issue #497対応）
ALB_INTERNAL_DNS=$(retrieve_ssm_parameter \
    "/jenkins-infra/${ENVIRONMENT}/loadbalancer/jenkins-internal-url" \
    "ALB Internal DNS" \
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

# VPC内部用URL設定関数（新規追加 - Issue #497対応）
# ECS FargateエージェントがNAT Instance経由せずにALBに直接接続するため
setup_jenkins_internal_url() {
    if [ -n "$ALB_INTERNAL_DNS" ] && [ "$ALB_INTERNAL_DNS" != "None" ]; then
        echo "${ALB_INTERNAL_DNS}"
    else
        # フォールバック：プライベートURLがなければパブリックURLを使用
        setup_jenkins_url
    fi
}

JENKINS_URL=$(setup_jenkins_url)
log "✓ Jenkins URL: $JENKINS_URL"

JENKINS_INTERNAL_URL=$(setup_jenkins_internal_url)
log "✓ Jenkins Internal URL: $JENKINS_INTERNAL_URL"

# すべての環境変数を一度にエクスポート（envsubstで使用するため）
export JENKINS_URL
export JENKINS_INTERNAL_URL
# Fleet ID（後方互換性）
export EC2_FLEET_ID
# インスタンスサイズ別Fleet ID
export EC2_FLEET_MEDIUM_ID
export EC2_FLEET_SMALL_ID
export EC2_FLEET_MICRO_ID
export WORKTERMINAL_HOST
export AWS_REGION
export AWS_PROD_ACCOUNT_IDS
export AWS_DEV_ACCOUNT_IDS
export SHARED_LIBRARY_REPO
export SHARED_LIBRARY_BRANCH
export SHARED_LIBRARY_PATH
export EC2_IDLE_MINUTES
# Fleet サイズ設定（後方互換性）
export EC2_MIN_SIZE
export EC2_MAX_SIZE
# インスタンスサイズ別Fleet サイズ設定
export EC2_FLEET_MEDIUM_MIN_SIZE
export EC2_FLEET_MEDIUM_MAX_SIZE
export EC2_FLEET_SMALL_MIN_SIZE
export EC2_FLEET_SMALL_MAX_SIZE
export EC2_FLEET_MICRO_MIN_SIZE
export EC2_FLEET_MICRO_MAX_SIZE
export EC2_NUM_EXECUTORS
# インスタンスサイズ別のExecutor数
export EC2_FLEET_MEDIUM_NUM_EXECUTORS
export EC2_FLEET_SMALL_NUM_EXECUTORS
export EC2_FLEET_MICRO_NUM_EXECUTORS
export ECS_CLUSTER_ARN
export ECS_TASK_DEFINITION_ARN
export ECS_EXECUTION_ROLE_ARN
export ECS_TASK_ROLE_ARN
export JENKINS_AGENT_SG_ID
export PRIVATE_SUBNET_A_ID
export PRIVATE_SUBNET_B_ID

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
        log "  JENKINS_INTERNAL_URL: $JENKINS_INTERNAL_URL"
        log "  EC2_FLEET_ID: $EC2_FLEET_ID (legacy)"
        log "  EC2_FLEET_MEDIUM_ID: ${EC2_FLEET_MEDIUM_ID:-not set}"
        log "  EC2_FLEET_SMALL_ID: ${EC2_FLEET_SMALL_ID:-not set}"
        log "  EC2_FLEET_MICRO_ID: ${EC2_FLEET_MICRO_ID:-not set}"
        log "  WORKTERMINAL_HOST: $WORKTERMINAL_HOST"
        log "  AWS_PROD_ACCOUNT_IDS: ${AWS_PROD_ACCOUNT_IDS:-not set}"
        log "  AWS_DEV_ACCOUNT_IDS: ${AWS_DEV_ACCOUNT_IDS:-not set}"
        log "  SHARED_LIBRARY_REPO: $SHARED_LIBRARY_REPO"
        log "  SHARED_LIBRARY_PATH: $SHARED_LIBRARY_PATH"
        log "  ECS_CLUSTER_ARN: ${ECS_CLUSTER_ARN:-not set}"
        log "  ECS_TASK_DEFINITION_ARN: ${ECS_TASK_DEFINITION_ARN:-not set}"
        log "  ECS_EXECUTION_ROLE_ARN: ${ECS_EXECUTION_ROLE_ARN:-not set}"
        log "  ECS_TASK_ROLE_ARN: ${ECS_TASK_ROLE_ARN:-not set}"
        log "  JENKINS_AGENT_SG_ID: ${JENKINS_AGENT_SG_ID:-not set}"
        log "  PRIVATE_SUBNET_A_ID: ${PRIVATE_SUBNET_A_ID:-not set}"
        log "  PRIVATE_SUBNET_B_ID: ${PRIVATE_SUBNET_B_ID:-not set}"
    fi
}

log_debug_info

# テンプレートから設定ファイルを生成
# shellcheckを無効化して変数リストを明示的に指定
# shellcheck disable=SC2016
envsubst '$JENKINS_URL $JENKINS_INTERNAL_URL $EC2_FLEET_ID $EC2_FLEET_MEDIUM_ID $EC2_FLEET_SMALL_ID $EC2_FLEET_MICRO_ID $WORKTERMINAL_HOST $AWS_REGION $AWS_PROD_ACCOUNT_IDS $AWS_DEV_ACCOUNT_IDS $SHARED_LIBRARY_REPO $SHARED_LIBRARY_BRANCH $SHARED_LIBRARY_PATH $EC2_IDLE_MINUTES $EC2_MIN_SIZE $EC2_MAX_SIZE $EC2_FLEET_MEDIUM_MIN_SIZE $EC2_FLEET_MEDIUM_MAX_SIZE $EC2_FLEET_SMALL_MIN_SIZE $EC2_FLEET_SMALL_MAX_SIZE $EC2_FLEET_MICRO_MIN_SIZE $EC2_FLEET_MICRO_MAX_SIZE $EC2_NUM_EXECUTORS $EC2_FLEET_MEDIUM_NUM_EXECUTORS $EC2_FLEET_SMALL_NUM_EXECUTORS $EC2_FLEET_MICRO_NUM_EXECUTORS $ECS_CLUSTER_ARN $ECS_TASK_DEFINITION_ARN $ECS_EXECUTION_ROLE_ARN $ECS_TASK_ROLE_ARN $JENKINS_AGENT_SG_ID $PRIVATE_SUBNET_A_ID $PRIVATE_SUBNET_B_ID' < "$TEMPLATE_FILE" > "$CASC_CONFIG_FILE"

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
    log "  - EC2 Fleet Cloud (legacy): ${EC2_FLEET_ID:-Not configured}"
    log "  - EC2 Fleet Cloud (medium): ${EC2_FLEET_MEDIUM_ID:-Not configured}"
    log "  - EC2 Fleet Cloud (small): ${EC2_FLEET_SMALL_ID:-Not configured}"
    log "  - EC2 Fleet Cloud (micro): ${EC2_FLEET_MICRO_ID:-Not configured}"
    log "  - Workterminal node: ${WORKTERMINAL_HOST:-Not configured}"
    log "  - ECS Fargate Cloud: ${ECS_CLUSTER_ARN:-Not configured}"
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
