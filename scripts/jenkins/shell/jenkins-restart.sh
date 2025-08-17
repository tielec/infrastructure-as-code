#!/bin/bash
# Jenkins再起動スクリプト
# SSM経由で実行されることを前提

# エラーハンドリング設定
set -e

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /var/log/jenkins-restart.log
}

# エラーハンドラー
error_exit() {
    log "ERROR: $1"
    exit 1
}

log "===== Jenkins Service Restart Script ====="

# Jenkinsを停止
log "Stopping Jenkins service..."
systemctl stop jenkins

# 停止確認
log "Verifying Jenkins has stopped..."
STOP_TIMEOUT=60
STOP_ELAPSED=0
while [ $STOP_ELAPSED -lt $STOP_TIMEOUT ]; do
    if ! systemctl is-active jenkins > /dev/null 2>&1; then
        log "✓ Jenkins service stopped successfully"
        break
    fi
    sleep 5
    STOP_ELAPSED=$((STOP_ELAPSED + 5))
    log "Waiting for Jenkins to stop... ($STOP_ELAPSED seconds)"
done

if [ $STOP_ELAPSED -ge $STOP_TIMEOUT ]; then
    log "WARNING: Jenkins did not stop cleanly within timeout"
    log "Force killing Jenkins processes..."
    pkill -9 -f jenkins || true
    sleep 5
fi

# プロセスが完全に終了したことを確認
if pgrep -f jenkins > /dev/null; then
    log "WARNING: Jenkins processes still running, force killing..."
    pkill -9 -f jenkins || true
    sleep 5
fi

# ポートが解放されているか確認
if netstat -tlpn 2>/dev/null | grep -q ':8080'; then
    log "Waiting for port 8080 to be released..."
    sleep 5
fi

log "Jenkins stopped completely"

# Jenkinsを起動
log "Starting Jenkins service..."
systemctl start jenkins

# 起動確認
log "Verifying Jenkins has started..."
START_TIMEOUT=300
START_ELAPSED=0
SERVICE_ACTIVE=false
WEB_RESPONSIVE=false

while [ $START_ELAPSED -lt $START_TIMEOUT ]; do
    # サービスの状態確認
    if systemctl is-active jenkins > /dev/null 2>&1; then
        if [ "$SERVICE_ACTIVE" = "false" ]; then
            log "✓ Jenkins service is active"
            SERVICE_ACTIVE=true
        fi
        
        # Webインターフェースの確認
        if curl -s -f http://localhost:8080/login > /dev/null 2>&1; then
            log "✓ Jenkins web interface is responsive"
            WEB_RESPONSIVE=true
            break
        else
            if [ $((START_ELAPSED % 20)) -eq 0 ] && [ $START_ELAPSED -gt 0 ]; then
                log "Jenkins service is active but web interface not ready yet..."
            fi
        fi
    else
        if [ $((START_ELAPSED % 20)) -eq 0 ] && [ $START_ELAPSED -gt 0 ]; then
            log "Waiting for Jenkins service to become active..."
        fi
    fi
    
    sleep 10
    START_ELAPSED=$((START_ELAPSED + 10))
    
    # 進捗表示
    if [ $((START_ELAPSED % 30)) -eq 0 ] && [ $START_ELAPSED -gt 0 ]; then
        log "Still waiting... ($START_ELAPSED seconds elapsed)"
    fi
done

# タイムアウトチェック
if [ $START_ELAPSED -ge $START_TIMEOUT ]; then
    log "ERROR: Jenkins failed to start within timeout"
    log "Checking Jenkins service status..."
    systemctl status jenkins --no-pager || true
    log ""
    log "Recent Jenkins logs:"
    journalctl -u jenkins --no-pager -n 50 || true
    error_exit "Jenkins startup failed"
fi

# 最終確認
if [ "$SERVICE_ACTIVE" = "true" ] && [ "$WEB_RESPONSIVE" = "true" ]; then
    log ""
    log "===== Jenkins Restart Completed Successfully ====="
    log "Service Status: Active"
    log "Web Interface: Responsive"
    log "Restart Time: $START_ELAPSED seconds"
    log "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
    
    # SSMパラメータに成功を記録（オプション）
    if [ -n "$PROJECT_NAME" ] && [ -n "$ENVIRONMENT" ]; then
        REGION=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" | xargs -I {} curl -s -H "X-aws-ec2-metadata-token: {}" http://169.254.169.254/latest/meta-data/placement/region)
        aws ssm put-parameter \
            --region $REGION \
            --name "/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/status/last-restart" \
            --value "SUCCESS: $(date '+%Y-%m-%d %H:%M:%S')" \
            --type String \
            --overwrite 2>/dev/null || true
    fi
else
    error_exit "Jenkins restart verification failed"
fi