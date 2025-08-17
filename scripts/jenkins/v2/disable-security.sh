#!/bin/bash
# Jenkins セキュリティを無効化するスクリプト（冪等）

set -e

JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"

echo "===== Disabling Jenkins Security ====="

# 現在の設定をバックアップ
if [ -f "${JENKINS_HOME}/jenkins.yaml" ]; then
    echo "Backing up current configuration..."
    cp "${JENKINS_HOME}/jenkins.yaml" "${JENKINS_HOME}/jenkins.yaml.backup-$(date +%Y%m%d-%H%M%S)"
fi

# セキュリティ無効の最小設定を作成
cat > "${JENKINS_HOME}/jenkins.yaml" << 'EOF'
jenkins:
  systemMessage: "Jenkins Setup in Progress - Security Disabled"
  numExecutors: 1
  mode: NORMAL
  authorizationStrategy:
    unsecured: {}
  securityRealm:
    local:
      allowsSignup: false
      enableCaptcha: false
  crumbIssuer:
    standard:
      excludeClientIPFromCrumb: true
  markupFormatter:
    markdownFormatter:
      disableSyntaxHighlighting: false
  disableRememberMe: false

unclassified:
  location:
    adminAddress: "jenkins-admin@example.com"
    url: "http://localhost:8080/"

tool:
  git:
    installations:
      - name: "Default"
        home: "git"
EOF

# 権限設定
chown jenkins:jenkins "${JENKINS_HOME}/jenkins.yaml"
chmod 600 "${JENKINS_HOME}/jenkins.yaml"

# セットアップウィザードを完了としてマーク
echo "Marking setup wizard as completed..."
if [ -f "${JENKINS_HOME}/config.xml" ]; then
    JENKINS_VERSION=$(grep -oP '(?<=<version>)[^<]+' "${JENKINS_HOME}/config.xml" 2>/dev/null || echo "2.516.1")
else
    JENKINS_VERSION="2.516.1"
fi

echo "$JENKINS_VERSION" > "${JENKINS_HOME}/jenkins.install.InstallUtil.lastExecVersion"
echo "2.0" > "${JENKINS_HOME}/jenkins.install.UpgradeWizard.state"
chown jenkins:jenkins "${JENKINS_HOME}/jenkins.install.InstallUtil.lastExecVersion" 2>/dev/null || true
chown jenkins:jenkins "${JENKINS_HOME}/jenkins.install.UpgradeWizard.state" 2>/dev/null || true

# Jenkinsを再起動
echo "Restarting Jenkins..."
systemctl restart jenkins

# 起動を待機
echo "Waiting for Jenkins to start..."
TIMEOUT=120
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if systemctl is-active jenkins > /dev/null; then
        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/json 2>/dev/null || echo "000")
        if [ "$HTTP_STATUS" = "200" ]; then
            echo "Jenkins is running and accessible without authentication"
            break
        fi
    fi
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "ERROR: Jenkins failed to start within timeout"
    exit 1
fi

echo "===== Security Disabled Successfully ====="
exit 0