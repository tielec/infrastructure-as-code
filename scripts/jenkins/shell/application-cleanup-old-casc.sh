#!/bin/bash
# 古いJCasC設定ファイルのクリーンアップ
# Jenkins更新前に実行し、互換性のない旧設定による起動失敗を防止する
# SSM経由で実行されることを前提

# エラーハンドリング設定
set -e

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /var/log/jenkins-application-setup.log
}

# エラーハンドラー
error_exit() {
    log "ERROR: $1"
    exit 1
}

log "===== Cleaning up old JCasC configuration files ====="

# 環境変数の設定
JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"

# JENKINS_HOMEの存在確認
if [ ! -d "$JENKINS_HOME" ]; then
    error_exit "JENKINS_HOME directory not found: $JENKINS_HOME"
fi

log "JENKINS_HOME: $JENKINS_HOME"

# 削除対象ファイルの検索と削除
DELETED_COUNT=0

# jenkins.yaml の削除
if [ -f "$JENKINS_HOME/jenkins.yaml" ]; then
    log "Removing: $JENKINS_HOME/jenkins.yaml"
    rm -f "$JENKINS_HOME/jenkins.yaml"
    DELETED_COUNT=$((DELETED_COUNT + 1))
fi

# casc*.yaml パターンに一致するファイルの削除
for f in "$JENKINS_HOME"/casc*.yaml; do
    if [ -f "$f" ]; then
        log "Removing: $f"
        rm -f "$f"
        DELETED_COUNT=$((DELETED_COUNT + 1))
    fi
done

if [ "$DELETED_COUNT" -eq 0 ]; then
    log "古いJCasC設定ファイルは見つかりませんでした（クリーンな状態）"
else
    log "${DELETED_COUNT}個の古いJCasC設定ファイルを削除しました"
fi

log "===== JCasC cleanup completed ====="
