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
CLEANUP_PHASE="${1:-all}"  # パラメータで特定のフェーズのみクリーンアップ可能

# クリーンアップ対象のGroovyスクリプト
declare -A GROOVY_SCRIPTS
GROOVY_SCRIPTS["plugins"]="install-plugins.groovy"
GROOVY_SCRIPTS["security"]="setup-cli-user-and-credentials.groovy setup-ssh-credentials.groovy"
GROOVY_SCRIPTS["seedjob"]="create-seed-job.groovy"

# テンポラリファイル
TEMP_FILES=(
    "/tmp/seed-job.xml"
    "/tmp/jenkins-plugins.txt"
    "/tmp/jenkins-cli.jar"
)

# クリーンアップ関数
cleanup_groovy_scripts() {
    local phase="$1"
    local scripts="$2"
    
    log "Cleaning up $phase scripts..."
    for script in $scripts; do
        local script_path="${GROOVY_DIR}/${script}"
        if [ -f "$script_path" ]; then
            log "  Removing: $script"
            rm -f "$script_path"
            
            # バックアップがある場合は削除
            if [ -f "${script_path}.bak" ]; then
                rm -f "${script_path}.bak"
                log "  Removed backup: ${script}.bak"
            fi
        else
            log "  Already removed: $script"
        fi
    done
}

# フェーズごとのクリーンアップ実行
case "$CLEANUP_PHASE" in
    "plugins")
        cleanup_groovy_scripts "plugins" "${GROOVY_SCRIPTS[plugins]}"
        ;;
    "security")
        cleanup_groovy_scripts "security" "${GROOVY_SCRIPTS[security]}"
        ;;
    "seedjob")
        cleanup_groovy_scripts "seedjob" "${GROOVY_SCRIPTS[seedjob]}"
        ;;
    "all")
        # すべてのGroovyスクリプトをクリーンアップ
        log "Performing complete cleanup..."
        for phase in "${!GROOVY_SCRIPTS[@]}"; do
            cleanup_groovy_scripts "$phase" "${GROOVY_SCRIPTS[$phase]}"
        done
        ;;
    *)
        log "Unknown cleanup phase: $CLEANUP_PHASE"
        log "Valid phases: plugins, security, seedjob, all"
        exit 1
        ;;
esac

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

# init.groovy.dディレクトリの確認
log ""
log "Checking init.groovy.d directory..."
if [ -d "$GROOVY_DIR" ]; then
    REMAINING_FILES=$(ls -1 "$GROOVY_DIR" 2>/dev/null | wc -l)
    if [ "$REMAINING_FILES" -eq 0 ]; then
        log "✓ init.groovy.d is clean (no remaining files)"
    else
        log "⚠ init.groovy.d contains $REMAINING_FILES file(s):"
        ls -la "$GROOVY_DIR" | grep -v "^total\|^d" | while read -r line; do
            log "    $line"
        done
    fi
else
    log "✓ init.groovy.d directory does not exist"
fi

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