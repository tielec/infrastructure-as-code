#!/bin/bash
set -euo pipefail

# =====================================================
# Pulumi実行スクリプト
# =====================================================
# 説明: Pulumiアクション（preview/deploy/destroy）を実行
# 使用方法: ./execute-pulumi.sh <action> <workspace> <artifacts_dir>
# 引数:
#   $1: action (preview/deploy/destroy)
#   $2: workspace path
#   $3: artifacts directory
# =====================================================

ACTION="${1:-preview}"
WORKSPACE="${2:-$WORKSPACE}"
ARTIFACTS_DIR="${3:-$ARTIFACTS_DIR}"

# 引数チェック
if [ -z "$ACTION" ] || [ -z "$WORKSPACE" ] || [ -z "$ARTIFACTS_DIR" ]; then
    echo "エラー: 必要な引数が不足しています"
    echo "使用方法: $0 <action> <workspace> <artifacts_dir>"
    exit 1
fi

echo "Pulumiアクション実行: $ACTION"

# 認証情報のセットアップ（sourceで実行して環境変数を引き継ぐ）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/setup-aws-credentials.sh"

# =====================================================
# 共通関数
# =====================================================

# スタックロックを確認し、必要に応じて解除する
check_and_unlock_stack() {
    echo "スタックロックの確認..."

    # スタック状態の取得
    local stack_status
    stack_status=$(pulumi stack 2>&1)

    if echo "$stack_status" | grep -q "currently locked"; then
        echo "警告: スタックがロックされています。"

        # ロック情報の詳細を表示
        echo "$stack_status" | grep -E "(locked|pid|created by)" || true

        echo "ロックを解除します..."
        if pulumi cancel --yes 2>&1; then
            echo "✅ ロック解除に成功しました"
            sleep 5
        else
            echo "⚠️ ロック解除に失敗しました。続行を試みます..."
            sleep 3
        fi
    else
        echo "✅ スタックはロックされていません"
    fi
}

# ロックエラーの場合に再試行する
retry_on_lock_error() {
    local action=$1
    local log_file=$2
    local exit_code=$3

    if [ ${exit_code} -eq 255 ] && grep -q "currently locked" "$log_file"; then
        echo "ロックエラーが検出されました。再度ロック解除を試みます..."
        pulumi cancel --yes || true
        sleep 10

        echo "再実行を試みます..."
        set +e
        case "$action" in
            refresh)
                pulumi refresh --yes --diff 2>&1 | tee "${log_file}.retry"
                ;;
            preview)
                pulumi preview --diff --save-plan=plan.json 2>&1 | tee "${log_file}.retry"
                ;;
            deploy)
                pulumi up --yes --diff 2>&1 | tee "${log_file}.retry"
                ;;
            destroy)
                pulumi destroy --yes 2>&1 | tee "${log_file}.retry"
                ;;
        esac
        local retry_exit_code=${PIPESTATUS[0]}
        set -e
        return ${retry_exit_code}
    fi
    return ${exit_code}
}

# Pulumiコマンドの実行
case "$ACTION" in
    preview)
        echo "変更内容のプレビュー..."

        # スタックロック確認と解除
        check_and_unlock_stack

        set +e
        pulumi preview --diff --save-plan=plan.json 2>&1 | tee "${WORKSPACE}/${ARTIFACTS_DIR}/pulumi-preview.log"
        PULUMI_EXIT_CODE=${PIPESTATUS[0]}
        set -e

        # ロックエラーの場合は再試行
        PULUMI_EXIT_CODE=$(retry_on_lock_error "preview" "${WORKSPACE}/${ARTIFACTS_DIR}/pulumi-preview.log" ${PULUMI_EXIT_CODE})

        if [ ${PULUMI_EXIT_CODE} -ne 0 ]; then
            echo "Pulumiプレビューが失敗しました（終了コード: ${PULUMI_EXIT_CODE}）"
            exit ${PULUMI_EXIT_CODE}
        fi
        ;;
        
    deploy)
        echo "リソースのデプロイ..."

        # スタックロック確認と解除
        check_and_unlock_stack

        set +e
        pulumi up --yes --diff 2>&1 | tee "${WORKSPACE}/${ARTIFACTS_DIR}/pulumi-up.log"
        PULUMI_EXIT_CODE=${PIPESTATUS[0]}
        set -e

        # ロックエラーの場合は再試行
        PULUMI_EXIT_CODE=$(retry_on_lock_error "deploy" "${WORKSPACE}/${ARTIFACTS_DIR}/pulumi-up.log" ${PULUMI_EXIT_CODE})

        if [ ${PULUMI_EXIT_CODE} -ne 0 ]; then
            echo "Pulumiデプロイが失敗しました（終了コード: ${PULUMI_EXIT_CODE}）"
            exit ${PULUMI_EXIT_CODE}
        fi
        
        echo "デプロイ完了後のスタック出力:"
        pulumi stack output --json > "${WORKSPACE}/${ARTIFACTS_DIR}/stack-outputs-post-action.json" || echo "{}" > "${WORKSPACE}/${ARTIFACTS_DIR}/stack-outputs-post-action.json"
        cat "${WORKSPACE}/${ARTIFACTS_DIR}/stack-outputs-post-action.json" | jq '.' || true
        ;;
        
    refresh)
        echo "実インフラとPulumi状態の同期..."

        # スタックロック確認と解除
        check_and_unlock_stack

        # refresh前の状態を保存
        echo "同期前の状態を保存..."
        pulumi stack export --file "${WORKSPACE}/${ARTIFACTS_DIR}/stack-state-before-refresh.json" 2>/dev/null || true

        set +e
        pulumi refresh --yes --diff 2>&1 | tee "${WORKSPACE}/${ARTIFACTS_DIR}/pulumi-refresh.log"
        PULUMI_EXIT_CODE=${PIPESTATUS[0]}
        set -e

        # ロックエラーの場合は再試行
        PULUMI_EXIT_CODE=$(retry_on_lock_error "refresh" "${WORKSPACE}/${ARTIFACTS_DIR}/pulumi-refresh.log" ${PULUMI_EXIT_CODE})

        if [ ${PULUMI_EXIT_CODE} -ne 0 ]; then
            echo "Pulumi refreshが失敗しました（終了コード: ${PULUMI_EXIT_CODE}）"
            exit ${PULUMI_EXIT_CODE}
        fi
        
        # refresh後の状態を保存
        echo "同期後の状態を保存..."
        pulumi stack export --file "${WORKSPACE}/${ARTIFACTS_DIR}/stack-state-after-refresh.json" 2>/dev/null || true
        
        echo "同期後のスタック出力:"
        pulumi stack output --json > "${WORKSPACE}/${ARTIFACTS_DIR}/stack-outputs-post-action.json" || echo "{}" > "${WORKSPACE}/${ARTIFACTS_DIR}/stack-outputs-post-action.json"
        cat "${WORKSPACE}/${ARTIFACTS_DIR}/stack-outputs-post-action.json" | jq '.' || true
        ;;
        
    destroy)
        echo "リソースの削除..."

        # スタックロック確認と解除
        check_and_unlock_stack

        set +e
        pulumi destroy --yes 2>&1 | tee "${WORKSPACE}/${ARTIFACTS_DIR}/pulumi-destroy.log"
        PULUMI_EXIT_CODE=${PIPESTATUS[0]}
        set -e

        # ロックエラーの場合は再試行
        PULUMI_EXIT_CODE=$(retry_on_lock_error "destroy" "${WORKSPACE}/${ARTIFACTS_DIR}/pulumi-destroy.log" ${PULUMI_EXIT_CODE})

        if [ ${PULUMI_EXIT_CODE} -ne 0 ]; then
            echo "Pulumi削除が失敗しました（終了コード: ${PULUMI_EXIT_CODE}）"
            exit ${PULUMI_EXIT_CODE}
        fi
        
        echo "リソースが削除されました"
        ;;
        
    *)
        echo "エラー: 不明なアクション: $ACTION"
        exit 1
        ;;
esac

echo "Pulumiアクション完了: $ACTION"