#!/bin/bash
# SSM Parameter Collection and Backup Script
# SSMパラメータを収集してバックアップファイルを作成

set -e

echo "======================================"
echo "SSM Parameter Collection Script"
echo "======================================"
echo "Environment: ${ENVIRONMENT}"
echo "Filter: ${ENV_FILTER}"
echo "Region: ${AWS_REGION}"
echo "Backup Date: ${BACKUP_DATE}"
echo "Backup Timestamp: ${BACKUP_TIMESTAMP}"
echo "======================================"

# パラメータ一覧の取得（ページネーション対応）
fetch_all_parameters() {
    local next_token=""
    local page=1
    local all_params="[]"
    
    while true; do
        echo "Fetching page ${page}..."
        
        if [ -n "$next_token" ]; then
            local result=$(aws ssm describe-parameters \
                --starting-token "$next_token" \
                --query "{Parameters: Parameters, NextToken: NextToken}" \
                --output json \
                --region ${AWS_REGION})
        else
            local result=$(aws ssm describe-parameters \
                --query "{Parameters: Parameters, NextToken: NextToken}" \
                --output json \
                --region ${AWS_REGION})
        fi
        
        # パラメータを追加
        local params=$(echo "$result" | jq -r '.Parameters // []')
        all_params=$(echo "$all_params" | jq ". + $params")
        
        # 次のトークンを確認
        next_token=$(echo "$result" | jq -r '.NextToken // empty')
        
        if [ -z "$next_token" ]; then
            break
        fi
        
        page=$((page + 1))
        
        # APIレート制限対策
        sleep 0.5
    done
    
    echo "$all_params"
}

# メイン処理
echo "Starting parameter collection..."

# すべてのパラメータを取得
ALL_PARAMS=$(fetch_all_parameters)
TOTAL_COUNT=$(echo "$ALL_PARAMS" | jq 'length')
echo "Total parameters found: ${TOTAL_COUNT}"

# 環境フィルタを適用
echo "Filtering parameters containing '${ENV_FILTER}'..."
FILTERED_PARAMS=$(echo "$ALL_PARAMS" | jq --arg filter "${ENV_FILTER}" \
    '[.[] | select(.Name | contains($filter))]')

PARAM_COUNT=$(echo "$FILTERED_PARAMS" | jq 'length')
echo "Found ${PARAM_COUNT} parameters for environment ${ENVIRONMENT}"

if [ "$PARAM_COUNT" -eq 0 ]; then
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

# パラメータを取得してバックアップデータを作成
echo "Fetching parameter values..."
BACKUP_DATA="[]"
BATCH_SIZE=10
COUNTER=0
FAILED_COUNT=0

while IFS= read -r param_name; do
    if [ $((COUNTER % BATCH_SIZE)) -eq 0 ] && [ $COUNTER -gt 0 ]; then
        echo "Processed ${COUNTER}/${PARAM_COUNT} parameters..."
        sleep 1  # APIレート制限対策
    fi
    
    # パラメータの値を取得（エラー時はスキップ）
    PARAM_DATA=$(aws ssm get-parameter \
        --name "$param_name" \
        --with-decryption \
        --query 'Parameter' \
        --output json \
        --region ${AWS_REGION} 2>/dev/null || echo '{}')
    
    if [ "$PARAM_DATA" != '{}' ]; then
        BACKUP_DATA=$(echo "$BACKUP_DATA" | jq ". + [$PARAM_DATA]")
    else
        echo "Warning: Failed to get parameter: $param_name"
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
    
    COUNTER=$((COUNTER + 1))
done < ${DATA_DIR}/parameter_names.txt

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