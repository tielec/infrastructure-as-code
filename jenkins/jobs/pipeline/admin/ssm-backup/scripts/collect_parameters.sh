#!/bin/bash
# SSM Parameter Collection and Backup Script
# SSMパラメータを収集してバックアップファイルを作成
# 
# 使用方法:
#   このスクリプトは環境変数を通じて設定を受け取ります
#   必須環境変数:
#     - ENVIRONMENT: バックアップ対象の環境 (dev/prod)
#     - ENV_FILTER: パラメータフィルタ文字列 (/dev/, /prod/)
#     - AWS_REGION: AWSリージョン
#     - BACKUP_DATE: バックアップ日付 (YYYY-MM-DD)
#     - BACKUP_TIMESTAMP: バックアップタイムスタンプ
#     - DATA_DIR: データ出力ディレクトリ
#
# 戻り値:
#   0: 正常終了
#   1: エラー発生

set -euo pipefail

echo "======================================"
echo "SSM Parameter Collection Script"
echo "======================================"
echo "Environment: ${ENVIRONMENT}"
echo "Filter: ${ENV_FILTER}"
echo "Region: ${AWS_REGION}"
echo "Backup Date: ${BACKUP_DATE}"
echo "Backup Timestamp: ${BACKUP_TIMESTAMP}"
echo "======================================"

# AWS認証情報の確認
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity --region ${AWS_REGION}; then
    echo "Error: Failed to get AWS credentials. Please check IAM role or credentials."
    exit 1
fi
echo "AWS credentials verified."

# AWS API呼び出しのリトライ機能
aws_cli_with_retry() {
    local max_retries=5
    local retry_delay=3  # 初期待機時間を長めに設定
    local retry_count=0
    
    # AWS CLIのページネーション設定を明示的に無効化
    unset AWS_PAGER
    export AWS_PAGER=""
    
    while [ $retry_count -lt $max_retries ]; do
        if output=$("$@" 2>&1); then
            echo "$output"
            return 0
        else
            if echo "$output" | grep -q "ThrottlingException\|Rate exceeded"; then
                retry_count=$((retry_count + 1))
                echo "  Rate limit hit. Retry ${retry_count}/${max_retries} after ${retry_delay}s..." >&2
                sleep $retry_delay
                retry_delay=$((retry_delay * 2))  # Exponential backoff
                if [ $retry_delay -gt 60 ]; then
                    retry_delay=60  # Max delay 60s
                fi
            else
                echo "Error: $output" >&2
                return 1
            fi
        fi
    done
    
    echo "Error: Max retries reached" >&2
    return 1
}

# パラメータ一覧の取得（ページネーション対応、フィルタリング最適化）
fetch_all_parameters() {
    local next_token=""
    local page=1
    local all_params="[]"
    
    # 初回実行前に待機（レート制限対策）
    echo "Waiting 2 seconds before API calls to avoid rate limiting..." >&2
    sleep 2
    
    while true; do
        echo "Fetching page ${page}..." >&2
        
        # AWS CLIコマンドの実行とエラーハンドリング
        local result
        local error_msg
        
        if [ -n "$next_token" ]; then
            echo "  Executing: aws ssm describe-parameters with filter --region ${AWS_REGION}" >&2
            # パラメータフィルタの値を変数に格納
            local filter_value="${ENV_FILTER:1:-1}"  # /dev/ -> dev
            if ! result=$(aws_cli_with_retry aws ssm describe-parameters \
                --starting-token "$next_token" \
                --max-results 50 \
                --parameter-filters "Key=Name,Option=Contains,Values=$filter_value" \
                --query '{Parameters: Parameters, NextToken: NextToken}' \
                --output json \
                --region ${AWS_REGION}); then
                echo "Error: Failed to describe parameters" >&2
                echo '{"Parameters": [], "NextToken": null}'
                return 1
            fi
        else
            echo "  Executing: aws ssm describe-parameters with filter --region ${AWS_REGION}" >&2
            # パラメータフィルタの値を変数に格納
            local filter_value="${ENV_FILTER:1:-1}"  # /dev/ -> dev
            if ! result=$(aws_cli_with_retry aws ssm describe-parameters \
                --max-results 50 \
                --parameter-filters "Key=Name,Option=Contains,Values=$filter_value" \
                --query '{Parameters: Parameters, NextToken: NextToken}' \
                --output json \
                --region ${AWS_REGION}); then
                echo "Error: Failed to describe parameters" >&2
                echo '{"Parameters": [], "NextToken": null}'
                return 1
            fi
        fi
        
        # 結果が空またはエラーメッセージの場合の処理
        if [ -z "$result" ]; then
            echo "Warning: Empty response received" >&2
            result='{"Parameters": [], "NextToken": null}'
        elif ! echo "$result" | jq empty 2>/dev/null; then
            echo "Warning: Invalid JSON response: ${result:0:100}..." >&2
            result='{"Parameters": [], "NextToken": null}'
        fi
        
        # デバッグ: パラメータ数を表示
        local param_count=$(echo "$result" | jq '.Parameters | length' 2>/dev/null || echo "0")
        echo "  Found ${param_count} parameters on page ${page}" >&2
        
        # パラメータを追加
        local params
        if params=$(echo "$result" | jq '.Parameters // []' 2>/dev/null); then
            if [ "$params" != "null" ] && [ "$params" != "[]" ] && [ -n "$params" ]; then
                all_params=$(echo "$all_params" | jq --argjson new_params "$params" '. + $new_params')
                echo "  Total accumulated parameters: $(echo "$all_params" | jq 'length')" >&2
            fi
        else
            echo "Warning: Failed to parse parameters from response" >&2
        fi
        
        # 次のトークンを確認
        next_token=$(echo "$result" | jq -r '.NextToken // empty' 2>/dev/null || echo "")
        
        if [ -z "$next_token" ]; then
            break
        fi
        
        page=$((page + 1))
        
        # APIレート制限対策（ページ間の待機時間を長めに）
        sleep 2
    done
    
    echo "$all_params"
}

# メイン処理
echo "Starting parameter collection..."

# AWS CLIのページネーション設定を無効化
export AWS_PAGER=""

# フィルタリングされたパラメータを取得（API側でフィルタリング済み）
FILTERED_PARAMS=$(fetch_all_parameters)
if [ $? -ne 0 ] || [ -z "$FILTERED_PARAMS" ]; then
    echo "Warning: fetch_all_parameters failed or returned empty" >&2
    FILTERED_PARAMS='[]'
fi

# JSONの検証
if ! echo "$FILTERED_PARAMS" | jq empty 2>/dev/null; then
    echo "Warning: Invalid JSON received from fetch_all_parameters" >&2
    echo "Received data (first 200 chars): ${FILTERED_PARAMS:0:200}" >&2
    FILTERED_PARAMS='[]'
fi

PARAM_COUNT=$(echo "$FILTERED_PARAMS" | jq 'length' 2>/dev/null || echo "0")
echo "Found ${PARAM_COUNT} parameters for environment ${ENVIRONMENT}"

if [ "$PARAM_COUNT" = "0" ]; then
    echo "WARNING: No parameters found matching filter '${ENV_FILTER}'"
    # 空のバックアップファイルを作成
    jq -n \
        --arg date "${BACKUP_DATE}" \
        --arg timestamp "${BACKUP_TIMESTAMP}" \
        --arg environment "${ENVIRONMENT}" \
        '{
            backup_date: $date,
            backup_timestamp: $timestamp,
            environment: $environment,
            parameter_count: 0,
            parameters: []
        }' > ${DATA_DIR}/backup.json
    exit 0
fi

# パラメータ名の一覧を保存
echo "$FILTERED_PARAMS" | jq -r '.[].Name' > ${DATA_DIR}/parameter_names.txt

# パラメータ取得前に待機（レート制限対策）
echo "Waiting before fetching parameter values..."
sleep 2

# パラメータを取得してバックアップデータを作成（バッチ処理で高速化）
echo "Fetching parameter values..."
BACKUP_DATA="[]"
BATCH_SIZE=10  # AWS APIの制限により最大10個
FAILED_COUNT=0
FAILED_PARAMS=()

# パラメータ名を配列に読み込み
mapfile -t PARAM_NAMES < ${DATA_DIR}/parameter_names.txt
TOTAL_PARAMS=${#PARAM_NAMES[@]}

# バッチ処理でパラメータを取得
for ((i=0; i<$TOTAL_PARAMS; i+=BATCH_SIZE)); do
    # バッチの終了インデックスを計算
    end=$((i + BATCH_SIZE))
    if [ $end -gt $TOTAL_PARAMS ]; then
        end=$TOTAL_PARAMS
    fi
    
    # 進捗表示
    echo "Fetching parameters $((i + 1))-$end of ${TOTAL_PARAMS}..."
    
    # バッチ用のパラメータ名を準備
    batch_params=()
    for ((j=i; j<end; j++)); do
        batch_params+=("${PARAM_NAMES[$j]}")
    done
    
    # get-parameters（複数形）でバッチ取得
    if [ ${#batch_params[@]} -gt 0 ]; then
        # AWS CLIコマンドを直接実行（xargsを使わない）
        BATCH_RESULT=$(aws ssm get-parameters \
            --names "${batch_params[@]}" \
            --with-decryption \
            --output json \
            --region ${AWS_REGION} 2>/dev/null || echo '{"Parameters": [], "InvalidParameters": []}')
        
        # 取得成功したパラメータを追加
        VALID_PARAMS=$(echo "$BATCH_RESULT" | jq '.Parameters // []')
        if [ "$VALID_PARAMS" != "[]" ] && [ "$VALID_PARAMS" != "null" ]; then
            BACKUP_DATA=$(echo "$BACKUP_DATA" | jq --argjson new_params "$VALID_PARAMS" '. + $new_params')
        fi
        
        # 取得失敗したパラメータを記録
        INVALID_PARAMS=$(echo "$BATCH_RESULT" | jq -r '.InvalidParameters[]?' 2>/dev/null)
        if [ -n "$INVALID_PARAMS" ]; then
            while IFS= read -r invalid_param; do
                echo "Warning: Failed to get parameter: $invalid_param"
                FAILED_PARAMS+=("$invalid_param")
                FAILED_COUNT=$((FAILED_COUNT + 1))
            done <<< "$INVALID_PARAMS"
        fi
    fi
    
    # APIレート制限対策（バッチ間の待機時間を長めに）
    if [ $end -lt $TOTAL_PARAMS ]; then
        sleep 2
    fi
done

COUNTER=$TOTAL_PARAMS

echo "Successfully fetched $((COUNTER - FAILED_COUNT)) parameters"
if [ "$FAILED_COUNT" -gt 0 ]; then
    echo "Failed to fetch ${FAILED_COUNT} parameters"
fi

# バックアップファイルの作成
echo "Creating backup file..."
BACKUP_JSON=$(jq -n \
    --arg date "${BACKUP_DATE}" \
    --arg timestamp "${BACKUP_TIMESTAMP}" \
    --arg environment "${ENVIRONMENT}" \
    --arg count "$((COUNTER - FAILED_COUNT))" \
    --argjson parameters "$BACKUP_DATA" \
    '{
        backup_date: $date,
        backup_timestamp: $timestamp,
        environment: $environment,
        parameter_count: $count | tonumber,
        parameters: $parameters
    }')

echo "$BACKUP_JSON" | jq '.' > ${DATA_DIR}/backup.json

echo "======================================"
echo "Backup Summary"
echo "======================================"
echo "Backup file created: ${DATA_DIR}/backup.json"
echo "Total parameters backed up: $(echo "$BACKUP_JSON" | jq '.parameter_count')"
echo "Failed parameters: ${FAILED_COUNT}"
echo "======================================"