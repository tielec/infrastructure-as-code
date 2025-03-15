#!/bin/bash
# Jenkinsコントローラー設定スクリプト
# SSM用に最適化されたバージョン - EFSマウント後・Jenkinsインストール後の実行を前提

# エラーハンドリングとログ設定
set -e
exec > >(tee /var/log/jenkins-configure.log|logger -t jenkins-configure -s 2>/dev/console) 2>&1
set -x

# 環境変数
JENKINS_MODE="${JENKINS_MODE:-normal}"
JENKINS_COLOR="${JENKINS_COLOR:-blue}"
JENKINS_HOME_DIR="/mnt/efs/jenkins"

echo "Configuring Jenkins in ${JENKINS_MODE} mode for ${JENKINS_COLOR} environment"

# EFSマウントとJenkinsインストールの確認
if ! df -h | grep -q "/mnt/efs"; then
  echo "エラー: EFSがマウントされていません。設定を中止します。"
  exit 1
fi

if ! rpm -q jenkins &>/dev/null; then
  echo "エラー: Jenkinsがインストールされていません。設定を中止します。"
  exit 1
fi

# Jenkinsユーザーとグループの確認
if ! getent group jenkins > /dev/null; then
  echo "Jenkinsグループが存在しません。作成します。"
  groupadd -f jenkins
fi

if ! id -u jenkins > /dev/null 2>&1; then
  echo "Jenkinsユーザーが存在しません。作成します。"
  useradd -m -d $JENKINS_HOME_DIR -g jenkins jenkins
  usermod -aG docker jenkins 2>/dev/null || true
fi

# UID/GIDの取得
JENKINS_UID=$(id -u jenkins)
JENKINS_GID=$(getent group jenkins | cut -d: -f3)
echo "Jenkins UID:GID = $JENKINS_UID:$JENKINS_GID"

# Jenkinsディレクトリ構造の確認
echo "Jenkinsディレクトリ構造の確認"
for dir in init.groovy.d logs plugins jobs secrets nodes; do
  if [ ! -d "$JENKINS_HOME_DIR/$dir" ]; then
    echo "ディレクトリ作成: $JENKINS_HOME_DIR/$dir"
    mkdir -p "$JENKINS_HOME_DIR/$dir"
  fi
done

# Groovyスクリプトディレクトリの準備
GROOVY_DIR="$JENKINS_HOME_DIR/init.groovy.d"
echo "Groovyスクリプトディレクトリの準備: $GROOVY_DIR"
mkdir -p $GROOVY_DIR
rm -f $GROOVY_DIR/*.groovy

# SSMパラメータストアから設定を取得
PARAMETER_PATH="/${PROJECT_NAME}/${ENVIRONMENT}/jenkins"

# CLI無効化スクリプト取得
echo "CLI無効化Groovyスクリプトの取得"
DISABLE_CLI_GROOVY=$(aws ssm get-parameter --name "${PARAMETER_PATH}/groovy/disable-cli" --with-decryption --query "Parameter.Value" --output text)
echo "$DISABLE_CLI_GROOVY" > $GROOVY_DIR/disable-cli.groovy

# 基本設定スクリプト取得
echo "基本設定Groovyスクリプトの取得"
BASIC_SETTINGS_GROOVY=$(aws ssm get-parameter --name "${PARAMETER_PATH}/groovy/basic-settings" --with-decryption --query "Parameter.Value" --output text)
echo "$BASIC_SETTINGS_GROOVY" > $GROOVY_DIR/basic-settings.groovy

# プラグインインストールスクリプト取得
echo "プラグインインストールGroovyスクリプトの取得"
INSTALL_PLUGINS_GROOVY=$(aws ssm get-parameter --name "${PARAMETER_PATH}/groovy/install-plugins" --with-decryption --query "Parameter.Value" --output text)
echo "$INSTALL_PLUGINS_GROOVY" > $GROOVY_DIR/install-plugins.groovy

# リカバリーモードスクリプト取得（条件付き）
if [ "$JENKINS_MODE" = "recovery" ]; then
  echo "リカバリーモードGroovyスクリプトの取得"
  RECOVERY_MODE_GROOVY=$(aws ssm get-parameter --name "${PARAMETER_PATH}/groovy/recovery-mode" --with-decryption --query "Parameter.Value" --output text)
  echo "$RECOVERY_MODE_GROOVY" > $GROOVY_DIR/basic-security.groovy
fi

# ファイル権限の設定
echo "Groovyスクリプトのパーミッション設定"
chmod 644 $GROOVY_DIR/*.groovy
chown -R $JENKINS_UID:$JENKINS_GID $GROOVY_DIR

# Jenkinsディレクトリの権限再確認
echo "Jenkinsディレクトリの権限設定"
chown -R $JENKINS_UID:$JENKINS_GID $JENKINS_HOME_DIR
find $JENKINS_HOME_DIR -type d -exec chmod 755 {} \; 2>/dev/null || true
find $JENKINS_HOME_DIR -type f -exec chmod 644 {} \; 2>/dev/null || true

# モード特有の設定
if [ "$JENKINS_MODE" = "recovery" ]; then
  echo "リカバリーモード用の追加設定"
  # JCasC設定ファイルのクリーンアップ
  rm -f $JENKINS_HOME_DIR/jenkins.yaml
  rm -f $JENKINS_HOME_DIR/casc*.yaml
  
  # セキュリティリセットマーカーファイルの作成
  touch $JENKINS_HOME_DIR/recovery-mode-enabled
  chown jenkins:jenkins $JENKINS_HOME_DIR/recovery-mode-enabled
else
  echo "通常モード用の設定"
  # リカバリーモードマーカーの削除（存在する場合）
  rm -f $JENKINS_HOME_DIR/recovery-mode-enabled
fi

# Jenkinsログディレクトリの権限確保
echo "ログディレクトリの権限確認"
chmod 755 $JENKINS_HOME_DIR/logs
chown -R $JENKINS_UID:$JENKINS_GID $JENKINS_HOME_DIR/logs

# 設定完了を示すマーカーファイル
echo "設定完了マーカーの作成"
echo "$(date '+%Y-%m-%d %H:%M:%S')" > $JENKINS_HOME_DIR/.configuration-complete
chown jenkins:jenkins $JENKINS_HOME_DIR/.configuration-complete

echo "Jenkins configuration completed"