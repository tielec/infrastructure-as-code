#!/bin/bash
#
# スクリプト名: verify-deployment.sh
#
# 説明:
#   Lambda API環境のデプロイメント検証と動作確認を実行
#
# 使用方法:
#   ./verify-deployment.sh [環境名]
#
# 引数:
#   環境名     対象環境 (デフォルト: dev)
#
# 環境変数:
#   AWS_REGION    AWSリージョン (デフォルト: ap-northeast-1)
#   VERBOSE       詳細出力モード (1で有効、デフォルト: 0)
#   LOG_LEVEL     ログレベル (DEBUG|INFO|WARN|ERROR、デフォルト: INFO)
#
# 終了コード:
#   0   全チェック成功
#   1   一部チェック失敗
#   2   引数エラー
#   3   環境エラー
#
# 例:
#   ./verify-deployment.sh dev
#   VERBOSE=1 ./verify-deployment.sh staging
#
# 作成日: 2025-08-30

set -euo pipefail

# グローバル定数
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
readonly TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

# 設定可能な変数
ENV_NAME="${1:-dev}"
AWS_REGION="${AWS_REGION:-ap-northeast-1}"
VERBOSE="${VERBOSE:-0}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

# カラー設定
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# ログ関数
function log_debug() {
    [[ "$LOG_LEVEL" == "DEBUG" ]] && echo -e "[DEBUG] $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2
}

function log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2
}

function log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2
}

function log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2
}

function log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
}

# 引数チェック
if [[ "$ENV_NAME" != "dev" && "$ENV_NAME" != "staging" && "$ENV_NAME" != "prod" ]]; then
    log_error "Invalid environment: $ENV_NAME"
    echo "Usage: $0 [dev|staging|prod]" >&2
    exit 2
fi

# 必要なコマンドの存在確認（set -eを一時的に無効化）
set +e
which aws >/dev/null 2>&1
AWS_CHECK=$?
which jq >/dev/null 2>&1
JQ_CHECK=$?
set -e

if [ $AWS_CHECK -ne 0 ]; then
    log_error "AWS CLI is not installed"
    exit 3
fi

if [ $JQ_CHECK -ne 0 ]; then
    log_error "jq is not installed"
    exit 3
fi

# ヘッダー表示
echo "=========================================="
echo "Lambda API Deployment Verification"
echo "=========================================="
echo "Environment: ${ENV_NAME}"
echo "Region: ${AWS_REGION}"
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# デバッグ情報（LOG_LEVEL=DEBUGの場合のみ表示）
[[ "$LOG_LEVEL" == "DEBUG" ]] && {
    echo "[DEBUG] Script directory: $SCRIPT_DIR" >&2
    echo "[DEBUG] Verbose mode: $VERBOSE" >&2
}

# 結果格納用変数
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
SKIPPED_CHECKS=0

#######################################
# チェック結果を記録する関数
# Globals:
#   TOTAL_CHECKS, PASSED_CHECKS, FAILED_CHECKS, SKIPPED_CHECKS
# Arguments:
#   $1 - チェック項目名
#   $2 - 結果 (pass/fail/skip)
# Returns:
#   0 - 成功
#######################################
function check_result() {
    local check_name="${1:?Error: check name is required}"
    local result="${2:?Error: result is required}"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    if [[ "$result" == "pass" ]]; then
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        log_success "$check_name"
    elif [[ "$result" == "skip" ]]; then
        SKIPPED_CHECKS=$((SKIPPED_CHECKS + 1))
        log_warn "$check_name (Skipped)"
    else
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        log_error "$check_name"
    fi
}

# 1. SSMパラメータの確認
echo "1. Checking SSM Parameters"
echo "----------------------------"

# API Gateway設定の確認（新しいSSM構造に対応）
# プロジェクト名を取得
if aws ssm get-parameter --name "/lambda-api/${ENV_NAME}/common/project-name" --query 'Parameter.Value' --output text >/dev/null 2>&1; then
    PROJECT_NAME=$(aws ssm get-parameter --name "/lambda-api/${ENV_NAME}/common/project-name" --query 'Parameter.Value' --output text)
    
    # API IDを取得
    if aws ssm get-parameter --name "/${PROJECT_NAME}/${ENV_NAME}/api-gateway/api-id" --query 'Parameter.Value' --output text >/dev/null 2>&1; then
        API_ID=$(aws ssm get-parameter --name "/${PROJECT_NAME}/${ENV_NAME}/api-gateway/api-id" --query 'Parameter.Value' --output text)
        log_info "API ID: ${API_ID}"
        check_result "API ID in SSM" "pass"
    else
        check_result "API ID in SSM" "fail"
        API_ID=""
    fi
    
    # API Endpointを取得
    if aws ssm get-parameter --name "/${PROJECT_NAME}/${ENV_NAME}/api-gateway/endpoint" --query 'Parameter.Value' --output text >/dev/null 2>&1; then
        API_ENDPOINT=$(aws ssm get-parameter --name "/${PROJECT_NAME}/${ENV_NAME}/api-gateway/endpoint" --query 'Parameter.Value' --output text)
        log_info "API Endpoint: ${API_ENDPOINT}"
        check_result "API Endpoint in SSM" "pass"
    else
        check_result "API Endpoint in SSM" "fail"
        API_ENDPOINT=""
    fi
else
    check_result "Project Name in SSM" "fail"
    API_ID=""
    API_ENDPOINT=""
fi

# APIキーの確認（プロジェクト名が取得できている場合のみ）
if [ -n "${PROJECT_NAME:-}" ]; then
    SSM_KEY_PATH="/${PROJECT_NAME}/${ENV_NAME}/api-gateway/keys"
    if aws ssm get-parameter --name "${SSM_KEY_PATH}" --with-decryption --query 'Parameter.Value' --output text >/dev/null 2>&1; then
        API_KEYS=$(aws ssm get-parameter --name "${SSM_KEY_PATH}" --with-decryption --query 'Parameter.Value' --output text)
        
        # JSON形式を確認
        if echo "$API_KEYS" | jq . >/dev/null 2>&1; then
            # 配列形式（新Lambda実装）のチェック
            if echo "$API_KEYS" | jq -e 'type == "array"' >/dev/null 2>&1; then
                # 配列からbubbleクライアントのキーを取得
                BUBBLE_KEY=$(echo "$API_KEYS" | jq -r '.[] | select(.clientId == "bubble" or .clientId == "bubble.io") | select(.enabled == true) | .apiKey // empty' | head -1)
                # bubbleキーがない場合は最初の有効なキーを使用
                if [ -z "$BUBBLE_KEY" ]; then
                    BUBBLE_KEY=$(echo "$API_KEYS" | jq -r '.[] | select(.enabled == true) | .apiKey // empty' | head -1)
                fi
                # 外部用キーも同様に取得
                EXTERNAL_KEY=$(echo "$API_KEYS" | jq -r '.[] | select(.clientId == "external") | select(.enabled == true) | .apiKey // empty' | head -1)
            else
                # オブジェクト形式（旧形式）のフォールバック
                BUBBLE_KEY=$(echo "$API_KEYS" | jq -r '.bubble.key // empty')
                EXTERNAL_KEY=$(echo "$API_KEYS" | jq -r '.external.key // empty')
            fi
            
            if [ -n "$BUBBLE_KEY" ] || [ -n "$EXTERNAL_KEY" ]; then
                check_result "API Keys in SSM" "pass"
                if [ "$VERBOSE" == "1" ]; then
                    if [ -n "$BUBBLE_KEY" ]; then
                        log_info "Bubble.io API Key found: ${BUBBLE_KEY:0:10}..."
                    else
                        log_warn "Bubble.io API Key not found in SSM"
                    fi
                    if [ -n "$EXTERNAL_KEY" ]; then
                        log_info "External API Key found: ${EXTERNAL_KEY:0:10}..."
                    else
                        log_warn "External API Key not found in SSM"
                    fi
                fi
            else
                log_warn "API keys found in SSM but values are empty"
                check_result "API Keys in SSM" "fail"
                BUBBLE_KEY=""
                EXTERNAL_KEY=""
            fi
        else
            log_error "Invalid JSON format in SSM parameter: ${SSM_KEY_PATH}"
            check_result "API Keys in SSM" "fail"
            BUBBLE_KEY=""
            EXTERNAL_KEY=""
        fi
    else
        log_warn "SSM parameter not found: ${SSM_KEY_PATH}"
        check_result "API Keys in SSM" "fail"
        BUBBLE_KEY=""
        EXTERNAL_KEY=""
    fi
else
    log_warn "Skipping API key check (project name not found)"
    BUBBLE_KEY=""
    EXTERNAL_KEY=""
fi

echo ""

# 2. Lambda関数の確認
echo "2. Checking Lambda Functions"
echo "----------------------------"

FUNCTION_NAME="lambda-api-main-${ENV_NAME}"

# Lambda関数の存在確認
if aws lambda get-function --function-name "$FUNCTION_NAME" >/dev/null 2>&1; then
    FUNCTION_INFO=$(aws lambda get-function-configuration --function-name "$FUNCTION_NAME")
    FUNCTION_STATE=$(echo "$FUNCTION_INFO" | jq -r '.State')
    FUNCTION_RUNTIME=$(echo "$FUNCTION_INFO" | jq -r '.Runtime')
    FUNCTION_MEMORY=$(echo "$FUNCTION_INFO" | jq -r '.MemorySize')
    FUNCTION_TIMEOUT=$(echo "$FUNCTION_INFO" | jq -r '.Timeout')
    
    log_info "Function: ${FUNCTION_NAME}"
    log_info "State: ${FUNCTION_STATE}"
    log_info "Runtime: ${FUNCTION_RUNTIME}"
    log_info "Memory: ${FUNCTION_MEMORY}MB"
    log_info "Timeout: ${FUNCTION_TIMEOUT}s"
    
    if [ "$FUNCTION_STATE" == "Active" ]; then
        check_result "Lambda Function Status" "pass"
    else
        check_result "Lambda Function Status" "fail"
    fi
else
    check_result "Lambda Function Exists" "fail"
fi

# Lambda実行テスト
echo ""
log_info "Testing Lambda function execution..."
TEST_PAYLOAD='{"test":"verification"}'
ENCODED_PAYLOAD=$(echo "$TEST_PAYLOAD" | base64)
TEMP_FILE="/tmp/lambda-response-$$.json"

if aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --payload "$ENCODED_PAYLOAD" \
    "$TEMP_FILE" \
    --query 'StatusCode' \
    --output text >/dev/null 2>&1; then
    
    RESPONSE=$(cat "$TEMP_FILE")
    rm -f "$TEMP_FILE"
    
    if echo "$RESPONSE" | jq -e '.statusCode == 200' >/dev/null 2>&1; then
        check_result "Lambda Function Execution" "pass"
        log_info "Lambda Response: $(echo "$RESPONSE" | jq -c .)"
    else
        check_result "Lambda Function Execution" "fail"
        log_warn "Lambda Response: $(echo "$RESPONSE" | jq -c .)"
    fi
else
    check_result "Lambda Function Execution" "fail"
    rm -f "$TEMP_FILE" 2>/dev/null || true
fi

echo ""

# 3. API Gatewayの確認
echo "3. Checking API Gateway"
echo "----------------------------"

if [ -n "$API_ID" ]; then
    # API Gateway存在確認
    if aws apigateway get-rest-api --rest-api-id "$API_ID" >/dev/null 2>&1; then
        check_result "API Gateway Exists" "pass"
        
        # リソース確認
        RESOURCES=$(aws apigateway get-resources --rest-api-id "$API_ID" --query 'items[].path' --output json)
        log_info "API Resources: $(echo "$RESOURCES" | jq -c .)"
        
        # デプロイメント確認
        if aws apigateway get-stage --rest-api-id "$API_ID" --stage-name "$ENV_NAME" >/dev/null 2>&1; then
            check_result "API Gateway Stage Deployed" "pass"
        else
            check_result "API Gateway Stage Deployed" "fail"
        fi
    else
        check_result "API Gateway Exists" "fail"
    fi
fi

echo ""

# 4. エンドポイントテスト
echo "4. Testing API Endpoints"
echo "----------------------------"

if [ -n "$API_ENDPOINT" ] && [ -n "$BUBBLE_KEY" ]; then
    # ヘルスチェックエンドポイント
    log_info "Testing health endpoint..."
    HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X GET "${API_ENDPOINT}/health" \
        -H "x-api-key: ${BUBBLE_KEY}" 2>/dev/null || echo "000")
    
    if [ "$HEALTH_RESPONSE" == "200" ]; then
        check_result "Health Endpoint" "pass"
        HEALTH_BODY=$(curl -s -X GET "${API_ENDPOINT}/health" -H "x-api-key: ${BUBBLE_KEY}")
        log_info "Health Response: $HEALTH_BODY"
    else
        check_result "Health Endpoint (HTTP $HEALTH_RESPONSE)" "fail"
    fi
    
    # バージョンAPIエンドポイント
    log_info "Testing version API endpoint..."
    VERSION_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X GET "${API_ENDPOINT}/api/version" \
        -H "x-api-key: ${BUBBLE_KEY}" 2>/dev/null || echo "000")
    
    if [ "$VERSION_RESPONSE" == "200" ]; then
        check_result "Version API Endpoint" "pass"
        VERSION_BODY=$(curl -s -X GET "${API_ENDPOINT}/api/version" -H "x-api-key: ${BUBBLE_KEY}")
        log_info "Version Response: $VERSION_BODY"
    else
        check_result "Version API Endpoint (HTTP $VERSION_RESPONSE)" "fail"
    fi
    
    # エコーAPIエンドポイント（POSTテスト）
    log_info "Testing echo API endpoint..."
    
    # まず認証なしでテスト（401が期待される）
    ECHO_RESPONSE_NO_AUTH=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "${API_ENDPOINT}/api/echo" \
        -H "Content-Type: application/json" \
        -d '{"test":"verification"}' 2>/dev/null || echo "000")
    
    if [ "$ECHO_RESPONSE_NO_AUTH" == "401" ] || [ "$ECHO_RESPONSE_NO_AUTH" == "403" ]; then
        log_info "Echo API correctly requires authentication ($ECHO_RESPONSE_NO_AUTH without key)"
        
        # APIキーがある場合は認証付きでテスト
        if [ -n "${BUBBLE_KEY}" ]; then
            # デバッグ情報出力（-vオプション時）
            if [ "$VERBOSE" == "1" ]; then
                log_info "Using API key: ${BUBBLE_KEY:0:10}..."
            fi
            
            # 認証付きエコーAPIリクエスト
            ECHO_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
                -X POST "${API_ENDPOINT}/api/echo" \
                -H "x-api-key: ${BUBBLE_KEY}" \
                -H "Content-Type: application/json" \
                -d '{"test":"verification"}' 2>/dev/null || echo "000")
            
            if [ "$ECHO_RESPONSE" == "200" ]; then
                check_result "Echo API Endpoint" "pass"
                ECHO_BODY=$(curl -s -X POST "${API_ENDPOINT}/api/echo" \
                    -H "x-api-key: ${BUBBLE_KEY}" \
                    -H "Content-Type: application/json" \
                    -d '{"test":"verification"}')
                log_info "Echo Response: $ECHO_BODY"
            else
                log_error "Echo API failed with valid key (HTTP $ECHO_RESPONSE)"
                check_result "Echo API Endpoint" "fail"
            fi
        else
            # APIキーがない場合でも、認証が必要なことが確認できればOK
            log_info "No API key in SSM, but authentication requirement verified"
            check_result "Echo API Endpoint (Auth Check)" "pass"
        fi
    else
        # 認証なしで401/403以外が返った場合はエラー
        log_error "Echo API should return 401 or 403 without authentication, got HTTP $ECHO_RESPONSE_NO_AUTH"
        check_result "Echo API Endpoint" "fail"
    fi
else
    log_warn "Skipping endpoint tests (missing API endpoint or key)"
fi

echo ""

# 5. CloudWatchログの確認
echo "5. Checking CloudWatch Logs"
echo "----------------------------"

LOG_GROUP="/aws/lambda/${FUNCTION_NAME}"
if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" --query "logGroups[?logGroupName=='$LOG_GROUP'].logGroupName" --output text | grep -q "$LOG_GROUP"; then
    check_result "CloudWatch Log Group Exists" "pass"
    
    # 最新のログストリーム確認
    LATEST_STREAM=$(aws logs describe-log-streams \
        --log-group-name "$LOG_GROUP" \
        --order-by LastEventTime \
        --descending \
        --limit 1 \
        --query 'logStreams[0].logStreamName' \
        --output text 2>/dev/null)
    
    if [ "$LATEST_STREAM" != "None" ] && [ -n "$LATEST_STREAM" ]; then
        log_info "Latest log stream: $LATEST_STREAM"
        check_result "CloudWatch Logs Available" "pass"
    else
        check_result "CloudWatch Logs Available" "fail"
    fi
else
    check_result "CloudWatch Log Group Exists" "fail"
fi

echo ""

# 6. ネットワーク設定の確認
echo "6. Checking Network Configuration"
echo "----------------------------"

if [ -n "$FUNCTION_NAME" ]; then
    VPC_CONFIG=$(aws lambda get-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --query 'VpcConfig' \
        --output json 2>/dev/null || echo "{}")
    
    if echo "$VPC_CONFIG" | jq -e '.VpcId' >/dev/null 2>&1; then
        VPC_ID=$(echo "$VPC_CONFIG" | jq -r '.VpcId')
        SUBNET_IDS=$(echo "$VPC_CONFIG" | jq -r '.SubnetIds[]' | tr '\n' ' ')
        SG_IDS=$(echo "$VPC_CONFIG" | jq -r '.SecurityGroupIds[]' | tr '\n' ' ')
        
        log_info "VPC: $VPC_ID"
        log_info "Subnets: $SUBNET_IDS"
        log_info "Security Groups: $SG_IDS"
        check_result "VPC Configuration" "pass"
    else
        log_info "Lambda is not VPC-connected"
        check_result "VPC Configuration" "pass"
    fi
fi

echo ""

# 7. DLQ設定の確認
echo "7. Checking Dead Letter Queue"
echo "----------------------------"

DLQ_ARN=$(aws lambda get-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --query 'DeadLetterConfig.TargetArn' \
    --output text 2>/dev/null || echo "")

if [ "$DLQ_ARN" != "" ] && [ "$DLQ_ARN" != "None" ]; then
    log_info "DLQ ARN: $DLQ_ARN"
    check_result "Dead Letter Queue Configured" "pass"
else
    log_warn "No Dead Letter Queue configured"
    check_result "Dead Letter Queue Configured" "fail"
fi

echo ""
echo "=========================================="
echo "Verification Summary"
echo "=========================================="
echo "Total Checks: $TOTAL_CHECKS"
echo -e "${GREEN}Passed: $PASSED_CHECKS${NC}"
if [ $SKIPPED_CHECKS -gt 0 ]; then
    echo -e "${YELLOW}Skipped: $SKIPPED_CHECKS${NC}"
fi
if [ $FAILED_CHECKS -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED_CHECKS${NC}"
else
    echo -e "${GREEN}Failed: 0${NC}"
fi

# 全体の結果判定
if [ $FAILED_CHECKS -eq 0 ]; then
    echo ""
    log_success "All checks passed! Lambda API environment is fully operational."
    echo ""
    echo "Next Steps:"
    echo "  1. Test your API endpoints with: curl -X GET ${API_ENDPOINT}/health -H \"x-api-key: YOUR_KEY\""
    echo "  2. Monitor logs: aws logs tail $LOG_GROUP --follow"
    echo "  3. Check metrics in CloudWatch Console"
    exit 0
else
    echo ""
    log_warn "Some checks failed. Please review the issues above."
    exit 1
fi