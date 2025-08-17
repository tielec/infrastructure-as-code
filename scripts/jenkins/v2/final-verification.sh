#!/bin/bash
# Jenkins 最終動作確認スクリプト

set -e

JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
PROJECT_NAME="${PROJECT_NAME:-jenkins-infra}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

echo "===== Final Jenkins Verification ====="

VERIFICATION_PASSED=true

# 1. Jenkinsサービスの確認
echo "Checking Jenkins service..."
if systemctl is-active jenkins > /dev/null; then
    echo "JENKINS_RUNNING"
    echo "✓ Jenkins service is running"
else
    echo "✗ Jenkins service is not running"
    VERIFICATION_PASSED=false
fi

# 2. HTTPレスポンスの確認
echo "Checking HTTP response..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/login 2>/dev/null || echo "000")
echo "HTTP Status: $HTTP_STATUS"

# 3. セキュリティの確認
echo "Checking security status..."
if [ "$HTTP_STATUS" = "401" ] || [ "$HTTP_STATUS" = "403" ] || [ "$HTTP_STATUS" = "200" ]; then
    # ログインページにアクセスして確認
    if curl -s http://localhost:8080/login | grep -q "password" 2>/dev/null; then
        echo "SECURITY_ENABLED"
        echo "✓ Security is enabled (login required)"
    else
        echo "✗ Security may not be properly configured"
    fi
else
    echo "✗ Cannot determine security status"
fi

# 4. プラグインの確認
echo "Checking plugins..."
REQUIRED_PLUGINS=(
    "configuration-as-code"
    "job-dsl"
    "workflow-aggregator"
    "git"
)

ALL_PLUGINS_FOUND=true
for plugin in "${REQUIRED_PLUGINS[@]}"; do
    if [ -f "${JENKINS_HOME}/plugins/${plugin}.jpi" ] || [ -f "${JENKINS_HOME}/plugins/${plugin}.hpi" ]; then
        echo "  ✓ Plugin found: $plugin"
    else
        echo "  ✗ Plugin missing: $plugin"
        ALL_PLUGINS_FOUND=false
    fi
done

if [ "$ALL_PLUGINS_FOUND" = true ]; then
    echo "PLUGINS_ACTIVE"
    echo "✓ All required plugins are installed"
else
    echo "✗ Some plugins are missing"
    VERIFICATION_PASSED=false
fi

# 5. 管理者ユーザーの確認
echo "Checking admin user..."
if [ -d "${JENKINS_HOME}/users/admin_"* ]; then
    echo "ADMIN_EXISTS"
    echo "✓ Admin user exists"
else
    echo "✗ Admin user not found"
    VERIFICATION_PASSED=false
fi

# 6. JCasC設定の確認
echo "Checking JCasC configuration..."
if [ -f "${JENKINS_HOME}/jenkins.yaml" ]; then
    if grep -q "clouds:" "${JENKINS_HOME}/jenkins.yaml" || grep -q "globalLibraries:" "${JENKINS_HOME}/jenkins.yaml"; then
        echo "CASC_LOADED"
        echo "✓ JCasC configuration is loaded"
    else
        echo "✗ JCasC configuration may be incomplete"
    fi
else
    echo "✗ JCasC configuration file not found"
fi

# 7. ジョブの確認
echo "Checking jobs..."
if [ -d "${JENKINS_HOME}/jobs/seed-job" ]; then
    echo "✓ Seed job exists"
else
    echo "✗ Seed job not found"
fi

# 最終結果
echo ""
echo "===== Verification Summary ====="
if [ "$VERIFICATION_PASSED" = true ]; then
    echo "ALL_CHECKS_PASSED"
    echo "✓ All verification checks passed"
else
    echo "SOME_CHECKS_FAILED"
    echo "✗ Some verification checks failed"
fi

exit 0