#!/bin/bash
# Jenkins 管理者ユーザーを作成するスクリプト（冪等）

set -e

JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
ADMIN_USER="${ADMIN_USER:-admin}"

echo "===== Creating Jenkins Admin User ====="

# ユーザーディレクトリの存在確認
if [ -d "${JENKINS_HOME}/users/${ADMIN_USER}_"* ]; then
    echo "Admin user already exists"
    echo "ADMIN_EXISTS"
    exit 0
fi

# パスワード生成（16文字のランダム文字列）
ADMIN_PASSWORD=$(openssl rand -base64 12 | tr -d "=+/" | cut -c1-16)

# Groovyスクリプトでユーザーを作成
GROOVY_DIR="${JENKINS_HOME}/init.groovy.d"
mkdir -p "$GROOVY_DIR"

cat > "$GROOVY_DIR/create-admin-user.groovy" << EOF
#!groovy
import jenkins.model.*
import hudson.security.*
import hudson.model.*
import java.util.logging.Logger

def logger = Logger.getLogger("")
def instance = Jenkins.getInstance()

logger.info("==== Creating Admin User ====")

// ローカルセキュリティレルムを確認/作成
def hudsonRealm = instance.getSecurityRealm()
if (!(hudsonRealm instanceof HudsonPrivateSecurityRealm)) {
    hudsonRealm = new HudsonPrivateSecurityRealm(false)
    instance.setSecurityRealm(hudsonRealm)
}

// adminユーザーを作成
def adminUser = hudsonRealm.createAccount("${ADMIN_USER}", "${ADMIN_PASSWORD}")
adminUser.save()

logger.info("Admin user created: ${ADMIN_USER}")

// CLIユーザーも作成（必要に応じて）
def cliUser = hudsonRealm.createAccount("jenkins-cli", "${ADMIN_PASSWORD}")
cliUser.save()
logger.info("CLI user created: jenkins-cli")

instance.save()
logger.info("Users saved successfully")
EOF

# 権限設定
chown jenkins:jenkins "$GROOVY_DIR/create-admin-user.groovy"
chmod 644 "$GROOVY_DIR/create-admin-user.groovy"

# Jenkinsを再起動してユーザーを作成
echo "Restarting Jenkins to create admin user..."
systemctl restart jenkins

# 起動を待機
TIMEOUT=120
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if systemctl is-active jenkins > /dev/null; then
        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/json 2>/dev/null || echo "000")
        if [ "$HTTP_STATUS" = "200" ]; then
            echo "Jenkins is running"
            break
        fi
    fi
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

# ユーザー作成の確認
sleep 10
if [ -d "${JENKINS_HOME}/users/${ADMIN_USER}_"* ]; then
    echo "Admin user created successfully"
    echo "ADMIN_CREATED"
    echo "ADMIN_PASSWORD: $ADMIN_PASSWORD"
    
    # Groovyスクリプトを削除
    rm -f "$GROOVY_DIR/create-admin-user.groovy"
else
    echo "Failed to create admin user"
    exit 1
fi

echo "===== Admin User Creation Complete ====="
exit 0