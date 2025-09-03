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

# Pulumiコマンドの実行
case "$ACTION" in
    preview)
        echo "変更内容のプレビュー..."
        set +e
        pulumi preview --diff --save-plan=plan.json 2>&1 | tee "${WORKSPACE}/${ARTIFACTS_DIR}/pulumi-preview.log"
        PULUMI_EXIT_CODE=${PIPESTATUS[0]}
        set -e
        
        if [ ${PULUMI_EXIT_CODE} -ne 0 ]; then
            echo "Pulumiプレビューが失敗しました（終了コード: ${PULUMI_EXIT_CODE}）"
            exit ${PULUMI_EXIT_CODE}
        fi
        ;;
        
    deploy)
        echo "リソースのデプロイ..."
        set +e
        pulumi up --yes --diff 2>&1 | tee "${WORKSPACE}/${ARTIFACTS_DIR}/pulumi-up.log"
        PULUMI_EXIT_CODE=${PIPESTATUS[0]}
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
        
        # refresh前の状態を保存
        echo "同期前の状態を保存..."
        pulumi stack export --file "${WORKSPACE}/${ARTIFACTS_DIR}/stack-state-before-refresh.json" 2>/dev/null || true
        
        set +e
        pulumi refresh --yes --diff 2>&1 | tee "${WORKSPACE}/${ARTIFACTS_DIR}/pulumi-refresh.log"
        PULUMI_EXIT_CODE=${PIPESTATUS[0]}
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
        set +e
        pulumi destroy --yes 2>&1 | tee "${WORKSPACE}/${ARTIFACTS_DIR}/pulumi-destroy.log"
        PULUMI_EXIT_CODE=${PIPESTATUS[0]}
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