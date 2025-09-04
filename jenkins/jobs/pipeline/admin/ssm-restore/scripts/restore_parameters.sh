#!/bin/bash
# SSM Parameter Restore Script
# SSMパラメータをバックアップから復元
# 
# 使用方法:
#   このスクリプトは環境変数を通じて設定を受け取ります
#   必須環境変数:
#     - ENVIRONMENT: 復元対象の環境 (dev/prod)
#     - ENV_FILTER: パラメータフィルタ文字列 (/dev/, /prod/)
#     - AWS_REGION: AWSリージョン
#     - BACKUP_FILE: バックアップファイルのパス
#     - DRY_RUN: ドライランモード (true/false)
#     - FORCE_OVERWRITE: 強制上書きモード (true/false)
#     - DATA_DIR: データ出力ディレクトリ
#
# 戻り値:
#   0: 正常終了
#   1: エラー発生

set -euo pipefail

echo "======================================"
echo "SSM Parameter Restore Script"
echo "======================================"
echo "Environment: ${ENVIRONMENT}"
echo "Filter: ${ENV_FILTER}"
echo "Region: ${AWS_REGION}"
echo "Backup File: ${BACKUP_FILE}"
echo "Dry Run: ${DRY_RUN}"
echo "Force Overwrite: ${FORCE_OVERWRITE}"
echo "======================================"

# AWS認証情報の確認
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity --region ${AWS_REGION}; then
    echo "Error: Failed to get AWS credentials. Please check IAM role or credentials."
    exit 1
fi
echo "AWS credentials verified."

# バックアップファイルの読み込み
echo "Loading backup file..."
if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

# バックアップ情報の表示
BACKUP_INFO=$(jq -r '{
    backup_date: .backup_date,
    backup_timestamp: .backup_timestamp,
    environment: .environment,
    parameter_count: .parameter_count
}' "${BACKUP_FILE}")

echo "Backup Information:"
echo "${BACKUP_INFO}" | jq '.'

# パラメータのフィルタリング
echo "Filtering parameters containing '${ENV_FILTER}'..."
FILTERED_PARAMS=$(jq --arg filter "${ENV_FILTER}" \
    '[.parameters[] | select(.Name | contains($filter))]' \
    "${BACKUP_FILE}")

PARAM_COUNT=$(echo "${FILTERED_PARAMS}" | jq 'length')
echo "Found ${PARAM_COUNT} parameters to restore"

if [ "$PARAM_COUNT" -eq 0 ]; then
    echo "WARNING: No parameters found matching filter '${ENV_FILTER}'"
    exit 0
fi

# パラメータの分析
analyze_parameters() {
    echo "Analyzing parameters..."
    
    local to_create=()
    local to_update=()
    local unchanged=()
    local counter=0
    
    # 各パラメータを確認
    echo "${FILTERED_PARAMS}" | jq -c '.[]' | while IFS= read -r param; do
        counter=$((counter + 1))
        local param_name=$(echo "$param" | jq -r '.Name')
        local param_value=$(echo "$param" | jq -r '.Value')
        local param_type=$(echo "$param" | jq -r '.Type')
        
        # 進捗表示
        if [ $((counter % 10)) -eq 0 ]; then
            echo "  Analyzing... ${counter}/${PARAM_COUNT}" >&2
        fi
        
        # 現在の値を取得
        local current_value
        if current_value=$(aws ssm get-parameter \
            --name "${param_name}" \
            --with-decryption \
            --query 'Parameter.Value' \
            --output text \
            --region ${AWS_REGION} 2>/dev/null); then
            
            if [ "${current_value}" != "${param_value}" ]; then
                echo "UPDATE:${param_name}"
            else
                echo "UNCHANGED:${param_name}"
            fi
        else
            echo "CREATE:${param_name}"
        fi
    done
}

# 分析結果の保存
echo "Starting parameter analysis..."
ANALYSIS_RESULT=$(analyze_parameters)

# 結果の集計
TO_CREATE=$(echo "${ANALYSIS_RESULT}" | grep "^CREATE:" | cut -d: -f2- | sort)
TO_UPDATE=$(echo "${ANALYSIS_RESULT}" | grep "^UPDATE:" | cut -d: -f2- | sort)
UNCHANGED=$(echo "${ANALYSIS_RESULT}" | grep "^UNCHANGED:" | cut -d: -f2- | sort)

CREATE_COUNT=$(echo "${TO_CREATE}" | grep -c . || echo 0)
UPDATE_COUNT=$(echo "${TO_UPDATE}" | grep -c . || echo 0)
UNCHANGED_COUNT=$(echo "${UNCHANGED}" | grep -c . || echo 0)

echo "======================================"
echo "Analysis Results:"
echo "======================================"
echo "To Create: ${CREATE_COUNT} parameters"
echo "To Update: ${UPDATE_COUNT} parameters"
echo "Unchanged: ${UNCHANGED_COUNT} parameters"

# 詳細表示
if [ "${CREATE_COUNT}" -gt 0 ]; then
    echo ""
    echo "Parameters to create:"
    echo "${TO_CREATE}" | while read -r name; do
        [ -n "$name" ] && echo "  - $name"
    done
fi

if [ "${UPDATE_COUNT}" -gt 0 ]; then
    echo ""
    echo "Parameters to update:"
    echo "${TO_UPDATE}" | while read -r name; do
        [ -n "$name" ] && echo "  - $name"
    done
fi

# ドライラン時は分析のみで終了
if [ "${DRY_RUN}" = "true" ]; then
    echo ""
    echo "======================================"
    echo "DRY RUN - No changes will be made"
    echo "======================================"
    
    # 分析結果をファイルに保存
    jq -n \
        --arg create_count "${CREATE_COUNT}" \
        --arg update_count "${UPDATE_COUNT}" \
        --arg unchanged_count "${UNCHANGED_COUNT}" \
        --argjson to_create "$(echo "${TO_CREATE}" | jq -Rs 'split("\n") | map(select(length > 0))')" \
        --argjson to_update "$(echo "${TO_UPDATE}" | jq -Rs 'split("\n") | map(select(length > 0))')" \
        '{
            analysis_date: now | todate,
            create_count: $create_count | tonumber,
            update_count: $update_count | tonumber,
            unchanged_count: $unchanged_count | tonumber,
            to_create: $to_create,
            to_update: $to_update
        }' > "${DATA_DIR}/analysis.json"
    
    exit 0
fi

# パラメータの復元
echo ""
echo "======================================"
echo "Starting Parameter Restore"
echo "======================================"

SUCCESS_COUNT=0
FAILED_COUNT=0
FAILED_PARAMS=()

# 復元処理
echo "${FILTERED_PARAMS}" | jq -c '.[]' | while IFS= read -r param; do
    PARAM_NAME=$(echo "$param" | jq -r '.Name')
    PARAM_VALUE=$(echo "$param" | jq -r '.Value')
    PARAM_TYPE=$(echo "$param" | jq -r '.Type')
    
    # このパラメータを処理するか判定
    SHOULD_PROCESS=false
    
    if echo "${TO_CREATE}" | grep -q "^${PARAM_NAME}$"; then
        SHOULD_PROCESS=true
        ACTION="CREATE"
    elif echo "${TO_UPDATE}" | grep -q "^${PARAM_NAME}$"; then
        if [ "${FORCE_OVERWRITE}" = "true" ]; then
            SHOULD_PROCESS=true
            ACTION="UPDATE"
        else
            echo "⊝ Skipped (update requires --force): ${PARAM_NAME}"
            continue
        fi
    else
        # 変更なしのパラメータはスキップ
        continue
    fi
    
    if [ "${SHOULD_PROCESS}" = "true" ]; then
        echo -n "[${ACTION}] ${PARAM_NAME} ... "
        
        # put-parameterコマンドの実行
        OVERWRITE_FLAG=""
        if [ "${ACTION}" = "UPDATE" ] || [ "${FORCE_OVERWRITE}" = "true" ]; then
            OVERWRITE_FLAG="--overwrite"
        fi
        
        if aws ssm put-parameter \
            --name "${PARAM_NAME}" \
            --value "${PARAM_VALUE}" \
            --type "${PARAM_TYPE}" \
            ${OVERWRITE_FLAG} \
            --region ${AWS_REGION} >/dev/null 2>&1; then
            echo "✓ Success"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            echo "✗ Failed"
            FAILED_COUNT=$((FAILED_COUNT + 1))
            FAILED_PARAMS+=("${PARAM_NAME}")
        fi
    fi
done

# 復元結果のサマリー
echo ""
echo "======================================"
echo "Restore Summary"
echo "======================================"
echo "Successfully restored: ${SUCCESS_COUNT}"
echo "Failed: ${FAILED_COUNT}"

if [ "${FAILED_COUNT}" -gt 0 ]; then
    echo ""
    echo "Failed parameters:"
    for param in "${FAILED_PARAMS[@]}"; do
        echo "  - ${param}"
    done
fi

# 検証
echo ""
echo "======================================"
echo "Verifying Restored Parameters"
echo "======================================"

VERIFY_FAILED=0

# 作成・更新対象のパラメータを検証
{ echo "${TO_CREATE}"; [ "${FORCE_OVERWRITE}" = "true" ] && echo "${TO_UPDATE}"; } | sort -u | while read -r param_name; do
    [ -z "${param_name}" ] && continue
    
    echo -n "Verifying ${param_name} ... "
    
    # バックアップから期待値を取得
    EXPECTED_VALUE=$(echo "${FILTERED_PARAMS}" | jq -r --arg name "${param_name}" \
        '.[] | select(.Name == $name) | .Value')
    
    # 現在の値を取得
    if CURRENT_VALUE=$(aws ssm get-parameter \
        --name "${param_name}" \
        --with-decryption \
        --query 'Parameter.Value' \
        --output text \
        --region ${AWS_REGION} 2>/dev/null); then
        
        if [ "${CURRENT_VALUE}" = "${EXPECTED_VALUE}" ]; then
            echo "✓ OK"
        else
            echo "✗ Value mismatch"
            VERIFY_FAILED=$((VERIFY_FAILED + 1))
        fi
    else
        echo "✗ Not found"
        VERIFY_FAILED=$((VERIFY_FAILED + 1))
    fi
done

echo ""
echo "======================================"
echo "Verification Summary"
echo "======================================"
if [ "${VERIFY_FAILED}" -eq 0 ]; then
    echo "✅ All parameters verified successfully"
else
    echo "⚠️ Verification failed for ${VERIFY_FAILED} parameters"
fi

# 最終結果の保存
jq -n \
    --arg success_count "${SUCCESS_COUNT}" \
    --arg failed_count "${FAILED_COUNT}" \
    --arg verify_failed "${VERIFY_FAILED}" \
    --argjson failed_params "$(printf '%s\n' "${FAILED_PARAMS[@]}" | jq -Rs 'split("\n") | map(select(length > 0))')" \
    '{
        restore_date: now | todate,
        success_count: $success_count | tonumber,
        failed_count: $failed_count | tonumber,
        verification_failed: $verify_failed | tonumber,
        failed_parameters: $failed_params
    }' > "${DATA_DIR}/restore_result.json"

# エラーがあった場合は非ゼロで終了
if [ "${FAILED_COUNT}" -gt 0 ] || [ "${VERIFY_FAILED}" -gt 0 ]; then
    exit 1
fi

echo ""
echo "======================================"
echo "✅ Restore completed successfully"
echo "======================================"