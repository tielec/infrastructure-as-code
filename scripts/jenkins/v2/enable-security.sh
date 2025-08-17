#!/bin/bash
# Jenkins セキュリティを有効化するスクリプト

set -e

JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
PROJECT_NAME="${PROJECT_NAME:-jenkins-infra}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

echo "===== Enabling Jenkins Security ====="

# AWS メタデータを取得
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
AWS_REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)

# 現在の設定をバックアップ
cp "${JENKINS_HOME}/jenkins.yaml" "${JENKINS_HOME}/jenkins.yaml.backup-security-$(date +%Y%m%d-%H%M%S)"

# jenkins.yamlを読み込んで、セキュリティセクションのみ更新
# sedを使って authorizationStrategy と securityRealm を更新
sed -i '
/authorizationStrategy:/,/^[^ ]/ {
  /authorizationStrategy:/ {
    a\    loggedInUsersCanDoAnything:\
      allowAnonymousRead: false
    :loop
    n
    /^[^ ]/!d
    /^[^ ]/!b loop
  }
  /unsecured: {}/d
}
' "${JENKINS_HOME}/jenkins.yaml"

# securityRealmが存在しない場合は追加（すでにlocalが設定されているはず）
if ! grep -q "securityRealm:" "${JENKINS_HOME}/jenkins.yaml"; then
    # authorizationStrategyの後にsecurityRealmを追加
    sed -i '/authorizationStrategy:/a\  securityRealm:\n    local:\n      allowsSignup: false\n      enableCaptcha: false' "${JENKINS_HOME}/jenkins.yaml"
fi

echo "Security configuration updated in jenkins.yaml"

# Jenkinsを再起動してセキュリティを適用
echo "Restarting Jenkins to apply security..."
systemctl restart jenkins

# 起動を待機
echo "Waiting for Jenkins to start with security enabled..."
TIMEOUT=300
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if systemctl is-active jenkins > /dev/null; then
        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/json 2>/dev/null || echo "000")
        if [ "$HTTP_STATUS" = "401" ] || [ "$HTTP_STATUS" = "403" ]; then
            echo "Jenkins is running with security enabled (HTTP $HTTP_STATUS)"
            break
        elif [ "$HTTP_STATUS" = "200" ]; then
            echo "WARNING: Jenkins is still accessible without authentication"
            echo "Waiting for security to be applied..."
        fi
    fi
    sleep 10
    ELAPSED=$((ELAPSED + 10))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "ERROR: Jenkins failed to start within timeout"
    exit 1
fi

# 最終確認
sleep 10
HTTP_FINAL=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/json 2>/dev/null || echo "000")
if [ "$HTTP_FINAL" = "401" ] || [ "$HTTP_FINAL" = "403" ]; then
    echo "SECURITY_ENABLED"
    echo "Jenkins security has been successfully enabled"
else
    echo "ERROR: Security was not properly enabled"
    exit 1
fi

echo "===== Security Enable Complete ====="
exit 0