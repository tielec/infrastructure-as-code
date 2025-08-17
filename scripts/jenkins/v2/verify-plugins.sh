#!/bin/bash
# プラグインが正しくインストールされたか確認するスクリプト

set -e

JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
PROJECT_NAME="${PROJECT_NAME:-jenkins-infra}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

echo "===== Verifying Jenkins Plugins ====="

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

# 各プラグインの存在を確認
ALL_ACTIVE=true
MISSING_PLUGINS=()

for plugin in "${PLUGIN_ARRAY[@]}"; do
    plugin=$(echo "$plugin" | xargs) # trim whitespace
    
    # .jpi または .hpi ファイルの存在確認
    if [ -f "${JENKINS_HOME}/plugins/${plugin}.jpi" ] || [ -f "${JENKINS_HOME}/plugins/${plugin}.hpi" ]; then
        echo "✓ Plugin active: $plugin"
    else
        echo "✗ Plugin missing or inactive: $plugin"
        ALL_ACTIVE=false
        MISSING_PLUGINS+=("$plugin")
    fi
done

# 結果を出力
if [ "$ALL_ACTIVE" = true ]; then
    echo "ALL_PLUGINS_ACTIVE"
    echo "All required plugins are installed and active"
else
    echo "MISSING_PLUGINS: ${MISSING_PLUGINS[*]}"
    echo "Some plugins are missing or inactive"
    exit 1
fi

# プラグインの総数も出力
TOTAL_PLUGINS=$(ls -1 "${JENKINS_HOME}/plugins/" 2>/dev/null | grep -E '\.jpi$|\.hpi$' | wc -l || echo "0")
echo "Total plugins installed: $TOTAL_PLUGINS"

exit 0