#!/bin/bash
# Jenkins Groovyスクリプトのクリーンアップ
# SSM経由で実行されることを前提

# エラーハンドリング設定
set -e

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /var/log/jenkins-application-cleanup.log
}

# エラーハンドラー
error_exit() {
    log "ERROR: $1"
    exit 1
}

log "===== Cleaning up Jenkins Groovy Scripts ====="

# 環境変数の設定
JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
GROOVY_DIR="${JENKINS_HOME}/init.groovy.d"
CLEANUP_PHASE="${1:-all}"  # パラメータで後方互換性を維持

# テンポラリファイル
TEMP_FILES=(
    "/tmp/seed-job.xml"
    "/tmp/jenkins-plugins.txt"
    "/tmp/jenkins-cli.jar"
)

# init.groovy.dディレクトリのクリーンアップ
log ""
log "Cleaning up init.groovy.d directory..."
if [ -d "$GROOVY_DIR" ]; then
    # ディレクトリ内のファイル数を確認
    FILE_COUNT=$(find "$GROOVY_DIR" -type f -name "*.groovy" 2>/dev/null | wc -l)
    
    if [ "$FILE_COUNT" -gt 0 ]; then
        log "Found $FILE_COUNT Groovy script(s) in init.groovy.d"
        
        # すべての.groovyファイルを削除
        find "$GROOVY_DIR" -type f -name "*.groovy" | while read -r script; do
            script_name=$(basename "$script")
            log "  Removing: $script_name"
            rm -f "$script"
            
            # バックアップファイルがある場合も削除
            if [ -f "${script}.bak" ]; then
                rm -f "${script}.bak"
                log "  Removed backup: ${script_name}.bak"
            fi
        done
        
        log "✓ Removed all Groovy scripts from init.groovy.d"
    else
        log "✓ init.groovy.d is already clean (no Groovy scripts found)"
    fi
    
    # その他の残存ファイルを確認
    REMAINING_FILES=$(ls -1 "$GROOVY_DIR" 2>/dev/null | wc -l)
    if [ "$REMAINING_FILES" -gt 0 ]; then
        log "⚠ init.groovy.d still contains $REMAINING_FILES non-Groovy file(s):"
        ls -la "$GROOVY_DIR" | grep -v "^total\|^d" | while read -r line; do
            log "    $line"
        done
    fi
else
    log "✓ init.groovy.d directory does not exist"
fi

# テンポラリファイルのクリーンアップ
log ""
log "Cleaning up temporary files..."
for temp_file in "${TEMP_FILES[@]}"; do
    if [ -f "$temp_file" ]; then
        log "  Removing: $temp_file"
        rm -f "$temp_file"
    else
        log "  Already removed: $temp_file"
    fi
done

# ログファイルのローテーション（サイズが大きい場合）
LOG_FILE="/var/log/jenkins-application-cleanup.log"
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(du -k "$LOG_FILE" | cut -f1)
    if [ "$LOG_SIZE" -gt 10240 ]; then  # 10MB以上
        log "Rotating cleanup log file (size: ${LOG_SIZE}KB)"
        mv "$LOG_FILE" "${LOG_FILE}.$(date '+%Y%m%d%H%M%S')"
        touch "$LOG_FILE"
        chown jenkins:jenkins "$LOG_FILE"
    fi
fi

# クリーンアップ完了の記録
REGION=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" | xargs -I {} curl -s -H "X-aws-ec2-metadata-token: {}" http://169.254.169.254/latest/meta-data/placement/region)
PROJECT_NAME="${PROJECT_NAME:-jenkins-infra}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

aws ssm put-parameter \
    --region $REGION \
    --name "/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/status/last-cleanup" \
    --value "$(date '+%Y-%m-%d %H:%M:%S') - Phase: $CLEANUP_PHASE" \
    --type String \
    --overwrite 2>/dev/null || true

log ""
log "===== Cleanup Completed Successfully ====="
log "Cleanup phase: $CLEANUP_PHASE"
log "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"