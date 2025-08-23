#!/bin/bash
# SSM Parameter Collection Script
# SSMパラメータストアからパラメータを収集するスクリプト

set -e

echo "======================================"
echo "SSMパラメータ収集スクリプト"
echo "======================================"
echo "環境: ${ENVIRONMENT}"
echo "パス: ${PARAMETER_PATH}"
echo "フィルタ: ${NAME_FILTER}"
echo "タイプ: ${TYPE_FILTER}"
echo "最大件数: ${MAX_RESULTS}"
echo "======================================"

# 基本のクエリコマンド構築
build_query_command() {
    local cmd="aws ssm describe-parameters"
    
    # パスフィルタの適用
    if [ "${PARAMETER_PATH}" != "/" ]; then
        cmd="$cmd --path ${PARAMETER_PATH}"
        if [ "${RECURSIVE}" = "true" ]; then
            cmd="$cmd --recursive"
        fi
    fi
    
    # 最大件数の設定
    cmd="$cmd --max-results ${MAX_RESULTS}"
    
    echo "$cmd"
}

# パラメータ一覧の取得
fetch_parameters_list() {
    echo "パラメータ一覧を取得中..."
    local query_cmd=$(build_query_command)
    
    # ページネーション対応
    local next_token=""
    local all_params="[]"
    local page=1
    
    while true; do
        echo "  ページ ${page} を取得中..."
        
        if [ -n "$next_token" ]; then
            local result=$($query_cmd --next-token "$next_token" --output json)
        else
            local result=$($query_cmd --output json)
        fi
        
        # パラメータを追加
        local params=$(echo "$result" | jq -r '.Parameters')
        all_params=$(echo "$all_params" | jq ". + $params")
        
        # 次のトークンを確認
        next_token=$(echo "$result" | jq -r '.NextToken // empty')
        
        if [ -z "$next_token" ]; then
            break
        fi
        
        page=$((page + 1))
    done
    
    # フィルタリング（名前フィルタ）
    if [ "${NAME_FILTER}" != "*" ] && [ -n "${NAME_FILTER}" ]; then
        echo "  名前フィルタを適用中: ${NAME_FILTER}"
        # ワイルドカードを正規表現に変換
        local pattern=$(echo "${NAME_FILTER}" | sed 's/\*/.*/')
        all_params=$(echo "$all_params" | jq "[.[] | select(.Name | test(\"$pattern\"))]")
    fi
    
    # フィルタリング（タイプフィルタ）
    if [ "${TYPE_FILTER}" != "All" ] && [ -n "${TYPE_FILTER}" ]; then
        echo "  タイプフィルタを適用中: ${TYPE_FILTER}"
        all_params=$(echo "$all_params" | jq "[.[] | select(.Type == \"${TYPE_FILTER}\")]")
    fi
    
    # 結果を保存
    echo "$all_params" | jq '{Parameters: .}' > "${DATA_DIR}/parameters_list.json"
    
    local param_count=$(echo "$all_params" | jq 'length')
    echo "✅ ${param_count} 個のパラメータを取得しました"
    
    return 0
}

# 各パラメータの詳細を取得
fetch_parameter_details() {
    echo "パラメータの詳細を取得中..."
    
    # パラメータリストを読み込み
    local params=$(jq -r '.Parameters[].Name' "${DATA_DIR}/parameters_list.json")
    local total=$(echo "$params" | wc -l)
    local count=0
    
    # バッチ処理用の配列
    local batch_size=10
    local batch=()
    
    echo "$params" | while IFS= read -r param_name; do
        count=$((count + 1))
        echo "  [${count}/${total}] 取得中: ${param_name}"
        
        # パラメータのハッシュ値を生成（ファイル名用）
        local param_hash=$(echo -n "$param_name" | md5sum | cut -d' ' -f1)
        
        # パラメータ値の取得
        if [ "${SHOW_SECURE_VALUES}" = "true" ]; then
            # SecureStringも復号化して取得
            aws ssm get-parameter \
                --name "$param_name" \
                --with-decryption \
                --output json > "${DATA_DIR}/param_${param_hash}.json" 2>/dev/null || \
            echo "{\"Parameter\": {\"Name\": \"$param_name\", \"Value\": \"[ERROR]\", \"Type\": \"Unknown\"}}" > "${DATA_DIR}/param_${param_hash}.json"
        else
            # SecureStringは復号化しない
            aws ssm get-parameter \
                --name "$param_name" \
                --output json > "${DATA_DIR}/param_${param_hash}.json" 2>/dev/null || \
            {
                # SecureStringの場合は値を隠蔽
                local param_type=$(jq -r ".Parameters[] | select(.Name == \"$param_name\") | .Type" "${DATA_DIR}/parameters_list.json")
                if [ "$param_type" = "SecureString" ]; then
                    echo "{\"Parameter\": {\"Name\": \"$param_name\", \"Value\": \"[SECURE]\", \"Type\": \"SecureString\"}}" > "${DATA_DIR}/param_${param_hash}.json"
                else
                    echo "{\"Parameter\": {\"Name\": \"$param_name\", \"Value\": \"[ERROR]\", \"Type\": \"$param_type\"}}" > "${DATA_DIR}/param_${param_hash}.json"
                fi
            }
        fi
        
        # 進捗表示（10件ごと）
        if [ $((count % 10)) -eq 0 ] || [ $count -eq $total ]; then
            echo "    進捗: ${count}/${total} ($(( count * 100 / total ))%)"
        fi
    done
    
    echo "✅ パラメータ詳細の取得完了"
}

# タグ情報の取得
fetch_tags() {
    echo "タグ情報を取得中..."
    
    local params=$(jq -r '.Parameters[].Name' "${DATA_DIR}/parameters_list.json")
    local total=$(echo "$params" | wc -l)
    local count=0
    
    echo "$params" | while IFS= read -r param_name; do
        count=$((count + 1))
        local param_hash=$(echo -n "$param_name" | md5sum | cut -d' ' -f1)
        
        # タグの取得（エラーは無視）
        aws ssm list-tags-for-resource \
            --resource-type "Parameter" \
            --resource-id "$param_name" \
            --output json > "${DATA_DIR}/tags_${param_hash}.json" 2>/dev/null || \
        echo '{"TagList": []}' > "${DATA_DIR}/tags_${param_hash}.json"
        
        # 進捗表示（20件ごと）
        if [ $((count % 20)) -eq 0 ] || [ $count -eq $total ]; then
            echo "  タグ取得進捗: ${count}/${total}"
        fi
    done
    
    echo "✅ タグ情報の取得完了"
}

# タグフィルタの適用
apply_tag_filters() {
    if [ -z "${TAG_FILTERS}" ]; then
        return 0
    fi
    
    echo "タグフィルタを適用中..."
    
    # TAG_FILTERSをパースして適用
    # 形式: "Key1=Value1\nKey2=Value2"
    
    # 実装は必要に応じて追加
    echo "  タグフィルタ機能は今後実装予定です"
}

# メイン処理
main() {
    # ディレクトリの確認
    if [ ! -d "${DATA_DIR}" ]; then
        mkdir -p "${DATA_DIR}"
    fi
    
    # AWS認証情報の確認
    if [ -z "${AWS_ACCESS_KEY_ID}" ] && [ -z "${AWS_DEFAULT_REGION}" ]; then
        echo "⚠️  AWS認証情報が設定されていません。IAMロールを使用します。"
    fi
    
    # パラメータ一覧の取得
    fetch_parameters_list
    
    # 詳細情報の取得
    fetch_parameter_details
    
    # タグ情報の取得
    if [ "${FETCH_TAGS}" = "true" ]; then
        fetch_tags
    fi
    
    # タグフィルタの適用
    apply_tag_filters
    
    echo "======================================"
    echo "✅ すべての処理が完了しました"
    echo "======================================"
}

# スクリプトの実行
main "$@"