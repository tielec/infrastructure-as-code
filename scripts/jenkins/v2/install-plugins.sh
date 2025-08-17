#!/bin/bash
# Jenkinsプラグインをインストールするスクリプト（冪等）

set -e

JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
REPO_PATH="${REPO_PATH:-/root/infrastructure-as-code}"
PROJECT_NAME="${PROJECT_NAME:-jenkins-infra}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

echo "===== Installing Jenkins Plugins ====="

# AWS リージョンの取得
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
AWS_REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)

# 必要なプラグインリストを取得
REQUIRED_PLUGINS=$(aws ssm get-parameter \
    --name "/jenkins-infra/${ENVIRONMENT}/application/required-plugins" \
    --region "$AWS_REGION" \
    --query "Parameter.Value" \
    --output text 2>/dev/null || echo "configuration-as-code,job-dsl,workflow-aggregator,git")

# カンマ区切りを配列に変換
IFS=',' read -ra PLUGIN_ARRAY <<< "$REQUIRED_PLUGINS"

# 現在インストール済みのプラグインを確認
INSTALLED_PLUGINS=""
if [ -d "${JENKINS_HOME}/plugins" ]; then
    INSTALLED_PLUGINS=$(ls -1 "${JENKINS_HOME}/plugins/" 2>/dev/null | grep -E '\.jpi$|\.hpi$' | sed 's/\.[jh]pi$//' || true)
fi

# インストールが必要なプラグインを特定
PLUGINS_TO_INSTALL=()
for plugin in "${PLUGIN_ARRAY[@]}"; do
    plugin=$(echo "$plugin" | xargs) # trim whitespace
    if ! echo "$INSTALLED_PLUGINS" | grep -q "^${plugin}$"; then
        PLUGINS_TO_INSTALL+=("$plugin")
        echo "Need to install: $plugin"
    else
        echo "Already installed: $plugin"
    fi
done

# インストールが必要なプラグインがない場合
if [ ${#PLUGINS_TO_INSTALL[@]} -eq 0 ]; then
    echo "All required plugins are already installed"
    echo "NO_RESTART_REQUIRED"
    exit 0
fi

# Groovyスクリプトを作成してプラグインをインストール
GROOVY_DIR="${JENKINS_HOME}/init.groovy.d"
mkdir -p "$GROOVY_DIR"

cat > "$GROOVY_DIR/install-plugins.groovy" << 'EOF'
#!groovy
import jenkins.model.*
import java.util.logging.Logger

def logger = Logger.getLogger("")
def installed = false
def pluginManager = Jenkins.instance.pluginManager
def uc = Jenkins.instance.updateCenter
def plugins = System.getenv("PLUGINS_TO_INSTALL")?.split(",") ?: []

logger.info("==== Installing Jenkins Plugins ====")

// Update Centerを更新
if (!uc.getSites()) {
    uc.updateAllSites()
    Thread.sleep(5000)
}

plugins.each { pluginName ->
    pluginName = pluginName.trim()
    if (pluginName) {
        def plugin = uc.getPlugin(pluginName)
        if (plugin) {
            logger.info("Installing plugin: ${pluginName}")
            def installFuture = plugin.deploy(true)
            installFuture.get()
            installed = true
        } else {
            logger.warning("Plugin not found in update center: ${pluginName}")
        }
    }
}

if (installed) {
    logger.info("Plugins installed, restart required")
    Jenkins.instance.save()
}
EOF

# プラグインリストを環境変数として設定
export PLUGINS_TO_INSTALL=$(IFS=','; echo "${PLUGINS_TO_INSTALL[*]}")

# 権限設定
chown jenkins:jenkins "$GROOVY_DIR/install-plugins.groovy"
chmod 644 "$GROOVY_DIR/install-plugins.groovy"

echo "Groovy script created for plugin installation"
echo "Plugins to install: $PLUGINS_TO_INSTALL"
echo "RESTART_REQUIRED"
echo "PLUGINS_INSTALLED"

exit 0