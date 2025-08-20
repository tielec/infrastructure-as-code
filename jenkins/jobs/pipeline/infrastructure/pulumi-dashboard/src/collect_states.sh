#!/bin/bash
# collect_states.sh - S3からPulumiステートファイルを収集

set -e

# 環境変数のチェック
: ${S3_BUCKET:?S3_BUCKET is required}
: ${DATA_DIR:?DATA_DIR is required}
: ${PROJECT_FILTER:="*"}
: ${STACK_FILTER:="*"}

echo "=== Pulumi State Collection ==="
echo "S3 Bucket: ${S3_BUCKET}"
echo "Project Filter: ${PROJECT_FILTER}"
echo "Stack Filter: ${STACK_FILTER}"

# S3バケットからプロジェクト一覧を取得
echo "Fetching project list from S3..."
aws s3 ls "s3://${S3_BUCKET}/.pulumi/stacks/" --recursive | grep -E '\.json$' > "${DATA_DIR}/s3_files.txt" || true

if [ ! -s "${DATA_DIR}/s3_files.txt" ]; then
    echo "Warning: No state files found"
    echo "[]" > "${DATA_DIR}/projects.json"
    exit 0
fi

echo "Found $(wc -l < ${DATA_DIR}/s3_files.txt) files"

# プロジェクトリストを作成
> "${DATA_DIR}/project_list.jsonl"

# ステートファイルをダウンロード
cat "${DATA_DIR}/s3_files.txt" | awk '{print $4}' | while read -r filepath; do
    # パスから プロジェクト名とスタック名を抽出
    project=$(echo "$filepath" | cut -d'/' -f3)
    stack=$(echo "$filepath" | cut -d'/' -f4 | sed 's/\.json$//')
    
    # フィルタリング
    if [ "${PROJECT_FILTER}" != "*" ]; then
        if ! echo "$project" | grep -q "${PROJECT_FILTER}"; then
            continue
        fi
    fi
    
    if [ "${STACK_FILTER}" != "*" ]; then
        if ! echo "$stack" | grep -q "${STACK_FILTER}"; then
            continue
        fi
    fi
    
    echo "Processing: Project=$project, Stack=$stack"
    
    # ステートファイルをダウンロード
    mkdir -p "${DATA_DIR}/states/${project}"
    aws s3 cp "s3://${S3_BUCKET}/${filepath}" "${DATA_DIR}/states/${project}/${stack}.json" --quiet
    
    # メタデータを保存
    echo "{\"project\": \"$project\", \"stack\": \"$stack\", \"path\": \"$filepath\"}" >> "${DATA_DIR}/project_list.jsonl"
done

# JSONLをJSONに変換
if [ -f "${DATA_DIR}/project_list.jsonl" ]; then
    jq -s '.' "${DATA_DIR}/project_list.jsonl" > "${DATA_DIR}/projects.json"
else
    echo "[]" > "${DATA_DIR}/projects.json"
fi

echo "Collection complete: $(jq '. | length' ${DATA_DIR}/projects.json) projects"

echo "=== Collection Complete ==="