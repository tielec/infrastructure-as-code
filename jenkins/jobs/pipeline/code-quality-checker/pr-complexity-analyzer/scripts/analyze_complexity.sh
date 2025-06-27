#!/bin/bash

# 複雑度解析スクリプト
# rust-code-analysisを使用してPRの変更ファイルを解析し、結果をJSONに結合する

set -e

# cargo binディレクトリをPATHに追加（複数の可能性があるパスを追加）
export PATH="$HOME/.cargo/bin:/root/.cargo/bin:$PATH"

# RUST_CODE_ANALYSIS_CLI環境変数が設定されている場合は使用
if [ -n "${RUST_CODE_ANALYSIS_CLI}" ]; then
    echo "環境変数RUST_CODE_ANALYSIS_CLIが設定されています: ${RUST_CODE_ANALYSIS_CLI}"
    RUST_CMD="${RUST_CODE_ANALYSIS_CLI}"
else
    RUST_CMD="rust-code-analysis-cli"
fi

# 引数の確認
if [ $# -lt 3 ]; then
    echo "Usage: $0 <source_dir> <analysis_dir> <changed_files_file>"
    exit 1
fi

SOURCE_DIR="$1"
ANALYSIS_DIR="$2"
CHANGED_FILES_FILE="$3"

echo "=== 解析前の診断情報 ==="
echo "現在のディレクトリ: $(pwd)"
echo "ソースディレクトリ: ${SOURCE_DIR}"
echo "解析結果ディレクトリ: ${ANALYSIS_DIR}"
echo "変更ファイルリスト: ${CHANGED_FILES_FILE}"
echo "PATH: ${PATH}"

# rust-code-analysis-cliのバージョン確認
echo "rust-code-analysis-cli version:"
if [ -x "${RUST_CMD}" ]; then
    ${RUST_CMD} --version || echo "バージョン確認失敗"
elif command -v ${RUST_CMD} > /dev/null 2>&1; then
    ${RUST_CMD} --version || echo "バージョン確認失敗"
else
    echo "エラー: rust-code-analysis-cliが見つかりません"
    echo "RUST_CMD: ${RUST_CMD}"
    echo "インストール確認:"
    ls -la "$HOME/.cargo/bin/" | grep rust-code-analysis || echo "- $HOME/.cargo/bin/ にありません"
    ls -la "/root/.cargo/bin/" | grep rust-code-analysis || echo "- /root/.cargo/bin/ にありません"
    exit 1
fi

# 変更されたファイルの詳細
echo "変更されたファイル:"
cat "${CHANGED_FILES_FILE}"
# wcの問題を回避するため、grep -cを使用（または最後に改行を追加）
CHANGED_FILES_COUNT=$(grep -c . "${CHANGED_FILES_FILE}" || echo "0")
echo "解析対象ファイル数: ${CHANGED_FILES_COUNT}"

echo "=== rust-code-analysis実行 ==="

# 解析結果ディレクトリを作成
mkdir -p "${ANALYSIS_DIR}"

# 結果ファイルの初期化
echo '[' > "${ANALYSIS_DIR}/complexity_metrics.json"

FIRST=true

# 変更されたファイルを1つずつ処理
while IFS= read -r file; do
    # 空行をスキップ
    [ -z "$file" ] && continue
    
    # ファイルの存在確認
    FULL_PATH="${SOURCE_DIR}/${file}"
    if [ -f "${FULL_PATH}" ]; then
        echo "処理中: ${file}"
        
        # カンマの追加
        if [ "$FIRST" = false ]; then
            echo ',' >> "${ANALYSIS_DIR}/complexity_metrics.json"
        fi
        FIRST=false
        
        # 一時ディレクトリを作成
        TEMP_DIR="${ANALYSIS_DIR}/temp_$_$(date +%s)"
        mkdir -p "${TEMP_DIR}"
        
        # 個別ファイルを解析
        if ${RUST_CMD} \
            -m \
            -O json \
            --pr \
            -o "${TEMP_DIR}" \
            -p "${FULL_PATH}" 2>/dev/null; then
            
            # 出力されたJSONファイルを探す
            OUTPUT_JSON=$(find "${TEMP_DIR}" -name "*.json" -type f | head -1)
            
            if [ -n "${OUTPUT_JSON}" ] && [ -f "${OUTPUT_JSON}" ]; then
                echo "JSONファイルが見つかりました: ${OUTPUT_JSON}"
                
                # JSONの構造を確認して適切に処理
                if jq -e 'type == "array"' "${OUTPUT_JSON}" >/dev/null 2>&1; then
                    # 配列の場合
                    if jq -e '.[0]' "${OUTPUT_JSON}" >/dev/null 2>&1; then
                        # 配列に要素がある場合は最初の要素を取得
                        jq '.[0]' "${OUTPUT_JSON}" >> "${ANALYSIS_DIR}/complexity_metrics.json"
                    else
                        # 空の配列の場合はデフォルト値
                        echo "{\"name\": \"${file}\", \"spaces\": []}" >> "${ANALYSIS_DIR}/complexity_metrics.json"
                    fi
                else
                    # オブジェクトの場合はそのまま追加
                    cat "${OUTPUT_JSON}" >> "${ANALYSIS_DIR}/complexity_metrics.json"
                fi
            else
                echo "警告: ${file} の解析結果が見つかりませんでした"
                echo "{\"name\": \"${file}\", \"spaces\": []}" >> "${ANALYSIS_DIR}/complexity_metrics.json"
            fi
        else
            echo "警告: ${file} の解析に失敗しました"
            echo "{\"name\": \"${file}\", \"spaces\": []}" >> "${ANALYSIS_DIR}/complexity_metrics.json"
        fi
        
        # 一時ディレクトリをクリーンアップ
        rm -rf "${TEMP_DIR}"
    else
        echo "警告: ファイルが見つかりません: ${FULL_PATH}"
        # ファイルが見つからない場合もエントリを追加（ただしカンマは追加しない）
        if [ "$FIRST" = false ]; then
            echo ',' >> "${ANALYSIS_DIR}/complexity_metrics.json"
        fi
        FIRST=false
        echo "{\"name\": \"${file}\", \"spaces\": []}" >> "${ANALYSIS_DIR}/complexity_metrics.json"
    fi
done < "${CHANGED_FILES_FILE}"

# JSON配列を閉じる
echo ']' >> "${ANALYSIS_DIR}/complexity_metrics.json"

# JSONを整形
echo "=== JSON整形 ==="
if jq '.' "${ANALYSIS_DIR}/complexity_metrics.json" > "${ANALYSIS_DIR}/temp.json" 2>/dev/null; then
    mv "${ANALYSIS_DIR}/temp.json" "${ANALYSIS_DIR}/complexity_metrics.json"
    echo "JSON整形成功"
else
    echo "警告: JSON形式が不正です"
    # 空の配列を作成
    echo '[]' > "${ANALYSIS_DIR}/complexity_metrics.json"
fi

# 結果の確認
echo "=== 解析結果 ==="
if [ -s "${ANALYSIS_DIR}/complexity_metrics.json" ]; then
    FILE_SIZE=$(wc -c < "${ANALYSIS_DIR}/complexity_metrics.json")
    echo "解析結果: ${FILE_SIZE} bytes"
    
    if [ ${FILE_SIZE} -gt 10 ]; then
        echo "結果のプレビュー:"
        jq '.' "${ANALYSIS_DIR}/complexity_metrics.json" | head -100
        
        echo ""
        echo "解析されたファイル数:"
        jq 'length' "${ANALYSIS_DIR}/complexity_metrics.json" || echo "0"
    else
        echo "警告: 解析結果が非常に小さい"
        cat "${ANALYSIS_DIR}/complexity_metrics.json"
    fi
else
    echo "警告: 解析結果が空です"
    echo '[]' > "${ANALYSIS_DIR}/complexity_metrics.json"
fi

echo "=== 複雑度解析完了 ==="
