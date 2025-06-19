#!/bin/bash
# Jenkinsコントローラー設定スクリプト
# SSM用に最適化されたバージョン - EFSマウント後・Jenkinsインストール後の実行を前提

# エラーハンドリング設定
set -e

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /var/log/jenkins-configure.log
}

# エラーハンドラー
error_exit() {
    log "ERROR: $1"
    exit 1
}

# 引数または環境変数から設定を取得
# ScriptArgsから渡される場合: JENKINS_MODE=xxx JENKINS_COLOR=yyy
for arg in "$@"; do
    if [[ $arg == *"="* ]]; then
        export "$arg"
    fi
done

# 環境変数
JENKINS_MODE="${JENKINS_MODE:-normal}"
JENKINS_COLOR="${JENKINS_COLOR:-blue}"
JENKINS_HOME_DIR="/mnt/efs/jenkins"

log "Jenkinsを設定: ${JENKINS_MODE}モード, ${JENKINS_COLOR}環境"

# EFSマウントの確認
if ! df -h | grep -q "/mnt/efs"; then
  error_exit "EFSがマウントされていません。先にEFSマウントスクリプトを実行してください。"
fi

# Jenkinsディレクトリの確認
if [ ! -d "$JENKINS_HOME_DIR" ]; then
  error_exit "Jenkinsディレクトリが存在しません: $JENKINS_HOME_DIR"
fi

# 前回の設定との比較用に設定情報を保存
mkdir -p "$JENKINS_HOME_DIR/.config"
CURRENT_CONFIG="$JENKINS_HOME_DIR/.config/current_config.json"
CONFIG_DATA="{\"mode\":\"$JENKINS_MODE\",\"color\":\"$JENKINS_COLOR\",\"timestamp\":\"$(date +%Y%m%d%H%M%S)\"}"

# 前回の設定を読み込む
if [ -f "$CURRENT_CONFIG" ]; then
  PREV_CONFIG=$(cat "$CURRENT_CONFIG")
  log "前回の設定: $PREV_CONFIG"
  log "現在の設定: $CONFIG_DATA"
  
  # 設定が変更されたか確認
  PREV_MODE=$(echo $PREV_CONFIG | jq -r '.mode // ""')
  
  if [ "$PREV_MODE" = "$JENKINS_MODE" ]; then
    log "前回と同じモード設定です。既存の設定を更新します。"
  else
    log "モード設定が変更されました: $PREV_MODE -> $JENKINS_MODE"
  fi
else
  log "初回設定を実行します"
fi

# 現在の設定を保存
echo "$CONFIG_DATA" > "$CURRENT_CONFIG"
chown jenkins:jenkins "$CURRENT_CONFIG"

# Groovyスクリプトディレクトリの準備
GROOVY_DIR="$JENKINS_HOME_DIR/init.groovy.d"
mkdir -p $GROOVY_DIR
rm -f $GROOVY_DIR/*.groovy

# SSMパラメータストアから設定を取得
PARAMETER_PATH="/${PROJECT_NAME}/${ENVIRONMENT}/jenkins"

# 必須パラメータの取得
SCRIPTS_OBTAINED=false
SCRIPT_FAILURES=0

# CLI無効化スクリプト取得
log "CLI無効化スクリプトを取得"
DISABLE_CLI_GROOVY=$(aws ssm get-parameter --name "${PARAMETER_PATH}/groovy/disable-cli" --with-decryption --query "Parameter.Value" --output text 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$DISABLE_CLI_GROOVY" ]; then
  echo "$DISABLE_CLI_GROOVY" > $GROOVY_DIR/disable-cli.groovy
  SCRIPTS_OBTAINED=true
else
  log "エラー: CLI無効化スクリプトの取得に失敗しました"
  SCRIPT_FAILURES=$((SCRIPT_FAILURES+1))
fi

# 基本設定スクリプト取得
log "基本設定スクリプトを取得"
BASIC_SETTINGS_GROOVY=$(aws ssm get-parameter --name "${PARAMETER_PATH}/groovy/basic-settings" --with-decryption --query "Parameter.Value" --output text 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$BASIC_SETTINGS_GROOVY" ]; then
  echo "$BASIC_SETTINGS_GROOVY" > $GROOVY_DIR/basic-settings.groovy
  SCRIPTS_OBTAINED=true
else
  log "エラー: 基本設定スクリプトの取得に失敗しました"
  SCRIPT_FAILURES=$((SCRIPT_FAILURES+1))
fi

# リカバリーモードスクリプト取得（条件付き）
if [ "$JENKINS_MODE" = "recovery" ]; then
  log "リカバリーモードスクリプトを取得"
  RECOVERY_MODE_GROOVY=$(aws ssm get-parameter --name "${PARAMETER_PATH}/groovy/recovery-mode" --with-decryption --query "Parameter.Value" --output text 2>/dev/null)
  if [ $? -eq 0 ] && [ -n "$RECOVERY_MODE_GROOVY" ]; then
    echo "$RECOVERY_MODE_GROOVY" > $GROOVY_DIR/basic-security.groovy
    SCRIPTS_OBTAINED=true
  else
    log "エラー: リカバリーモードスクリプトの取得に失敗しました"
    SCRIPT_FAILURES=$((SCRIPT_FAILURES+1))
  fi
fi

# 少なくとも1つのスクリプトが取得できたか確認
if [ "$SCRIPTS_OBTAINED" != "true" ]; then
  error_exit "必要なスクリプトの取得に失敗しました。設定を中止します。"
fi

# スクリプト取得の警告を表示
if [ $SCRIPT_FAILURES -gt 0 ]; then
  log "警告: $SCRIPT_FAILURES 個のスクリプト取得に失敗しましたが、一部のスクリプトは取得できました。"
fi

# ファイル権限の設定
chown -R jenkins:jenkins $GROOVY_DIR
chmod 644 $GROOVY_DIR/*.groovy 2>/dev/null || true

# モード特有の設定
if [ "$JENKINS_MODE" = "recovery" ]; then
  log "リカバリーモード用の追加設定"
  # JCasC設定ファイルのクリーンアップ
  rm -f $JENKINS_HOME_DIR/jenkins.yaml
  rm -f $JENKINS_HOME_DIR/casc*.yaml
  
  # セキュリティリセットマーカーファイルの作成
  touch $JENKINS_HOME_DIR/recovery-mode-enabled
  chown jenkins:jenkins $JENKINS_HOME_DIR/recovery-mode-enabled
else
  log "通常モード用の設定"
  # リカバリーモードマーカーの削除（存在する場合）
  rm -f $JENKINS_HOME_DIR/recovery-mode-enabled
fi

# Jenkinsログディレクトリの権限確保
chmod 755 $JENKINS_HOME_DIR/logs
chown -R jenkins:jenkins $JENKINS_HOME_DIR/logs

# 設定完了を示すマーカーファイル
echo "$(date '+%Y-%m-%d %H:%M:%S')" > $JENKINS_HOME_DIR/.configuration-complete
chown jenkins:jenkins $JENKINS_HOME_DIR/.configuration-complete

log "Jenkins設定が完了しました"
exit 0
