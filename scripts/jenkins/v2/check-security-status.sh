#!/bin/bash
# Jenkins セキュリティ状態を確認するスクリプト

set -e

JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"

# HTTPステータスコードで判定
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/json 2>/dev/null || echo "000")

echo "HTTP Status: $HTTP_STATUS"

if [ "$HTTP_STATUS" = "200" ]; then
    echo "STATUS: UNSECURED"
    echo "Jenkins is accessible without authentication"
elif [ "$HTTP_STATUS" = "401" ] || [ "$HTTP_STATUS" = "403" ]; then
    echo "STATUS: SECURED"
    echo "Jenkins requires authentication"
else
    echo "STATUS: UNKNOWN"
    echo "Jenkins may not be running or accessible"
fi

# jenkins.yamlの存在と内容も確認
if [ -f "${JENKINS_HOME}/jenkins.yaml" ]; then
    if grep -q "unsecured: {}" "${JENKINS_HOME}/jenkins.yaml" 2>/dev/null; then
        echo "Configuration: Unsecured mode found in jenkins.yaml"
    elif grep -q "loggedInUsersCanDoAnything" "${JENKINS_HOME}/jenkins.yaml" 2>/dev/null; then
        echo "Configuration: Security enabled in jenkins.yaml"
    fi
fi

exit 0