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

# ログにスタックロックのエラーが含まれるかを判定する
# Pulumiのロックエラーメッセージ例:
#   error: the stack is currently locked by 1 lock(s). Either wait for the other
#   process(es) to end or delete the lock file with `pulumi cancel`.
contains_lock_error() {
    local target=$1

    if [ ! -f "$target" ]; then
        return 1
    fi

    grep -qE "currently locked|delete the lock file" "$target"
}

# スタックのロックを解除する
unlock_stack() {
    echo "ロックを解除します（pulumi cancel）..."

    if pulumi cancel --yes 2>&1; then
        echo "✅ ロック解除に成功しました"
        sleep 5
        return 0
    fi

    echo "⚠️ ロック解除に失敗しました"
    sleep 3
    return 1
}

# スタックロックを事前確認し、検出された場合は解除する
# 注意: pulumi stack はロックを取得しないため、ここでロックを検出できない場合がある。
#       実際のロック検出は各コマンド実行後の retry_on_lock_error が担う。
check_and_unlock_stack() {
    echo "スタックロックの事前確認..."

    # スタック状態の取得（失敗してもここでは中断しない）
    local stack_status
    stack_status=$(pulumi stack 2>&1 || true)

    if echo "$stack_status" | grep -qE "currently locked|delete the lock file"; then
        echo "警告: スタックがロックされています。"

        # ロック情報の詳細を表示
        echo "$stack_status" | grep -E "(locked|pid|created by)" || true

        unlock_stack || echo "続行を試みます..."
    else
        echo "事前確認ではロックを検出しませんでした（実行時に検出された場合は自動で解除を試みます）"
    fi
}

# ロックエラーの場合に再試行する
# 注意: errexit（set -e）は呼び出し側で無効化しておくこと。
#       また、戻り値で結果を返すため、コマンド置換ではなく直接呼び出して $? を参照すること。
retry_on_lock_error() {
    local action=$1
    local log_file=$2
    local exit_code=$3

    # ロックエラー時の終了コードはPulumiのバージョンや実行経路により異なる（1 や 255 など）ため、
    # 終了コードでは判定せず、ログの内容でロックエラーを判定する
    if [ "${exit_code}" -ne 0 ] && contains_lock_error "$log_file"; then
        echo "========================================"
        echo "ロックエラーを検出しました（終了コード: ${exit_code}）"
        grep -E "created by|pid|locks/" "$log_file" || true
        echo "========================================"

        unlock_stack || true
        sleep 10

        echo "再実行を試みます..."
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

        # 再実行でもロックが解消しない場合は、手動対応が必要なため案内を出す
        if [ ${retry_exit_code} -ne 0 ] && contains_lock_error "${log_file}.retry"; then
            echo "========================================"
            echo "⚠️ 再実行後もロックが解消されませんでした"
            echo "他のプロセスが実行中の可能性があります。以下を確認してください:"
            echo "  1. 同じスタックを操作している他のJenkinsジョブが実行中でないか"
            echo "  2. 上記のロック情報（作成者・PID・作成時刻）"
            echo "実行中のプロセスがない場合は、手動で 'pulumi cancel' を実行してください"
            echo "========================================"
        fi

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
        # 注意: コマンド置換で呼び出すと戻り値ではなく標準出力を取得してしまうため、直接呼び出して $? を使う
        set +e
        retry_on_lock_error "preview" "${WORKSPACE}/${ARTIFACTS_DIR}/pulumi-preview.log" ${PULUMI_EXIT_CODE}
        PULUMI_EXIT_CODE=$?
        set -e

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
        # 注意: コマンド置換で呼び出すと戻り値ではなく標準出力を取得してしまうため、直接呼び出して $? を使う
        set +e
        retry_on_lock_error "deploy" "${WORKSPACE}/${ARTIFACTS_DIR}/pulumi-up.log" ${PULUMI_EXIT_CODE}
        PULUMI_EXIT_CODE=$?
        set -e

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
        # 注意: コマンド置換で呼び出すと戻り値ではなく標準出力を取得してしまうため、直接呼び出して $? を使う
        set +e
        retry_on_lock_error "refresh" "${WORKSPACE}/${ARTIFACTS_DIR}/pulumi-refresh.log" ${PULUMI_EXIT_CODE}
        PULUMI_EXIT_CODE=$?
        set -e

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
        # 注意: コマンド置換で呼び出すと戻り値ではなく標準出力を取得してしまうため、直接呼び出して $? を使う
        set +e
        retry_on_lock_error "destroy" "${WORKSPACE}/${ARTIFACTS_DIR}/pulumi-destroy.log" ${PULUMI_EXIT_CODE}
        PULUMI_EXIT_CODE=$?
        set -e

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