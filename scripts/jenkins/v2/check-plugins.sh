#!/bin/bash
# 現在インストールされているプラグインを確認するスクリプト

set -e

JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"

echo "===== Checking Installed Plugins ====="

if [ ! -d "${JENKINS_HOME}/plugins" ]; then
    echo "Plugins directory does not exist"
    exit 0
fi

# インストール済みプラグインのリスト
PLUGINS=$(ls -1 "${JENKINS_HOME}/plugins/" 2>/dev/null | grep -E '\.jpi$|\.hpi$' | sed 's/\.[jh]pi$//' || true)

if [ -z "$PLUGINS" ]; then
    echo "No plugins installed"
else
    echo "Installed plugins:"
    for plugin in $PLUGINS; do
        echo "INSTALLED: $plugin"
    done
    
    # プラグイン数
    PLUGIN_COUNT=$(echo "$PLUGINS" | wc -l)
    echo "Total: $PLUGIN_COUNT plugins"
fi

exit 0