#!/bin/bash
# Jenkinsを安全に再起動するスクリプト

set -e

echo "===== Restarting Jenkins ====="

# 現在の状態を確認
if systemctl is-active jenkins > /dev/null; then
    echo "Jenkins is currently running"
else
    echo "Jenkins is not running"
fi

# 再起動
echo "Restarting Jenkins service..."
systemctl restart jenkins

# 起動を待機
echo "Waiting for Jenkins to start..."
TIMEOUT=300
ELAPSED=0

while [ $ELAPSED -lt $TIMEOUT ]; do
    if systemctl is-active jenkins > /dev/null; then
        # HTTPレスポンスを確認
        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/json 2>/dev/null || echo "000")
        if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "401" ] || [ "$HTTP_STATUS" = "403" ]; then
            echo "Jenkins is running and responsive (HTTP $HTTP_STATUS)"
            
            # プラグインの読み込み完了を待つ
            echo "Waiting for plugins to be fully loaded..."
            sleep 30
            
            # init.groovy.dのスクリプトがあれば実行後に削除
            if [ -f "/mnt/efs/jenkins/init.groovy.d/install-plugins.groovy" ]; then
                echo "Removing plugin installation script..."
                rm -f "/mnt/efs/jenkins/init.groovy.d/install-plugins.groovy"
            fi
            
            echo "Jenkins restart completed successfully"
            exit 0
        fi
    fi
    
    sleep 10
    ELAPSED=$((ELAPSED + 10))
    
    if [ $((ELAPSED % 30)) -eq 0 ]; then
        echo "Still waiting... ($ELAPSED seconds elapsed)"
    fi
done

echo "ERROR: Jenkins failed to start within timeout"
exit 1