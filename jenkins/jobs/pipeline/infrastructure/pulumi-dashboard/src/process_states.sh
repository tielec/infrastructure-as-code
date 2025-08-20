#!/bin/bash
# process_states.sh - Pulumiステートデータの処理と集計

set -e

# 環境変数のチェック
: ${DATA_DIR:?DATA_DIR is required}

echo "=== Processing State Data ==="

# 結果を格納するJSONファイルを初期化
echo "[]" > "${DATA_DIR}/processed_states.json"

# 各プロジェクトのステートを処理
for project_dir in ${DATA_DIR}/states/*/; do
    if [ -d "$project_dir" ]; then
        project_name=$(basename "$project_dir")
        echo "Processing: $project_name"
        
        for state_file in "$project_dir"/*.json; do
            if [ -f "$state_file" ]; then
                stack_name=$(basename "$state_file" .json)
                
                # ステート情報を抽出
                jq --arg project "$project_name" --arg stack "$stack_name" '
                    {
                        project: $project,
                        stack: $stack,
                        checkpoint: .checkpoint,
                        resources: (
                            if .checkpoint.latest.resources then
                                .checkpoint.latest.resources | length
                            else
                                0
                            end
                        ),
                        last_updated: (
                            if .checkpoint.latest then
                                .checkpoint.latest.manifest.time
                            else
                                null
                            end
                        ),
                        last_operation_result: (
                            if .checkpoint.latest.manifest.result then
                                .checkpoint.latest.manifest.result
                            else
                                null
                            end
                        ),
                        last_operation_errors: (
                            if .checkpoint.latest.manifest.errors then
                                .checkpoint.latest.manifest.errors
                            else
                                null
                            end
                        ),
                        version: .version,
                        resource_types: (
                            if .checkpoint.latest.resources then
                                [.checkpoint.latest.resources[].type] | group_by(.) | map({type: .[0], count: length}) | sort_by(.count) | reverse
                            else
                                []
                            end
                        ),
                        outputs: (
                            if .checkpoint.latest.resources then
                                [.checkpoint.latest.resources[] | select(.outputs)] | length
                            else
                                0
                            end
                        )
                    }
                ' "$state_file" > "${DATA_DIR}/temp_state.json" || echo "{\"error\": \"Failed to process $state_file\"}" > "${DATA_DIR}/temp_state.json"
                
                # 処理結果を追加
                jq -s '.[0] + [.[1]]' "${DATA_DIR}/processed_states.json" "${DATA_DIR}/temp_state.json" > "${DATA_DIR}/processed_states_tmp.json"
                mv "${DATA_DIR}/processed_states_tmp.json" "${DATA_DIR}/processed_states.json"
            fi
        done
    fi
done

echo "Processed: $(jq '. | length' ${DATA_DIR}/processed_states.json) stacks"

# サマリー情報を生成
echo "Generating summary..."
jq '
    {
        total_projects: (map(.project) | unique | length),
        total_stacks: length,
        total_resources: (map(.resources) | add),
        projects: (
            group_by(.project) | 
            map({
                name: .[0].project,
                stacks: length,
                total_resources: (map(.resources) | add),
                last_updated: (map(.last_updated) | max)
            })
        ),
        resource_summary: (
            map({project: .project, types: .resource_types}) |
            map(.types[] as $type | {project: .project, type: $type.type, count: $type.count}) |
            group_by(.type) | 
            map({
                type: .[0].type,
                total: (map(.count) | add),
                projects: (map(.project) | unique | sort)
            }) |
            sort_by(.total) |
            reverse
        )
    }
' "${DATA_DIR}/processed_states.json" > "${DATA_DIR}/summary.json"

echo "Summary generated:"
cat "${DATA_DIR}/summary.json" | jq '.'

# クリーンアップ
rm -f "${DATA_DIR}/temp_state.json"

echo "=== Processing Complete ==="