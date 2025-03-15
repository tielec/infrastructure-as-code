#!/bin/bash
# Jenkinsコントローラー設定スクリプト
# SSM用に最適化されたバージョン

# エラーハンドリングとログ設定
set -e
exec > >(tee /var/log/jenkins-configure.log|logger -t jenkins-configure -s 2>/dev/console) 2>&1
set -x

# 環境変数
JENKINS_MODE="${JENKINS_MODE:-normal}"
JENKINS_COLOR="${JENKINS_COLOR:-blue}"

echo "Configuring Jenkins in ${JENKINS_MODE} mode for ${JENKINS_COLOR} environment"

# Groovyスクリプトディレクトリの準備
GROOVY_DIR="/mnt/efs/jenkins/init.groovy.d"
mkdir -p $GROOVY_DIR
rm -f $GROOVY_DIR/*.groovy

# SSMパラメータストアから設定を取得
PARAMETER_PATH="/${PROJECT_NAME}/${ENVIRONMENT}/jenkins"

# CLI無効化スクリプト取得
DISABLE_CLI_GROOVY=$(aws ssm get-parameter --name "${PARAMETER_PATH}/groovy/disable-cli" --with-decryption --query "Parameter.Value" --output text || echo "")
if [ -n "$DISABLE_CLI_GROOVY" ]; then
  echo "Creating disable-cli.groovy from SSM parameter"
  echo "$DISABLE_CLI_GROOVY" > $GROOVY_DIR/disable-cli.groovy
fi

# 基本設定スクリプト取得
BASIC_SETTINGS_GROOVY=$(aws ssm get-parameter --name "${PARAMETER_PATH}/groovy/basic-settings" --with-decryption --query "Parameter.Value" --output text || echo "")
if [ -n "$BASIC_SETTINGS_GROOVY" ]; then
  echo "Creating basic-settings.groovy from SSM parameter"
  echo "$BASIC_SETTINGS_GROOVY" > $GROOVY_DIR/basic-settings.groovy
fi

# リカバリーモードスクリプト取得
if [ "$JENKINS_MODE" = "recovery" ]; then
  RECOVERY_MODE_GROOVY=$(aws ssm get-parameter --name "${PARAMETER_PATH}/groovy/recovery-mode" --with-decryption --query "Parameter.Value" --output text || echo "")
  if [ -n "$RECOVERY_MODE_GROOVY" ]; then
    echo "Creating recovery-mode.groovy from SSM parameter"
    echo "$RECOVERY_MODE_GROOVY" > $GROOVY_DIR/basic-security.groovy
  fi
fi

# ファイル権限の設定
chmod 644 $GROOVY_DIR/*.groovy
chown jenkins:jenkins $GROOVY_DIR/*.groovy

# モード特有の設定
if [ "$JENKINS_MODE" = "recovery" ]; then
  echo "Setting up recovery mode configuration"
  # 既存のJCasC設定をクリーンアップ
  rm -f /mnt/efs/jenkins/jenkins.yaml
  rm -f /mnt/efs/jenkins/casc*.yaml
else
  echo "Setting up normal mode configuration"
  # 通常モードでの追加設定
fi

echo "Jenkins configuration completed"
