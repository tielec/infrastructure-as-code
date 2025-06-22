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

# Gitリポジトリからgroovyスクリプトをコピー
REPO_PATH="${REPO_PATH:-/root/infrastructure-as-code}"
GROOVY_SOURCE_DIR="$REPO_PATH/scripts/jenkins/groovy"

log "Groovyスクリプトをコピー中..."

if [ -f "$GROOVY_SOURCE_DIR/basic-settings.groovy" ]; then
  cp "$GROOVY_SOURCE_DIR/basic-settings.groovy" "$GROOVY_DIR/"
  log "✓ basic-settings.groovy をコピーしました"
else
  log "警告: basic-settings.groovy が見つかりません"
fi

# リカバリーモードの場合のみリカバリースクリプトをコピー
if [ "$JENKINS_MODE" = "recovery" ]; then
  if [ -f "$GROOVY_SOURCE_DIR/recovery-mode.groovy" ]; then
    cp "$GROOVY_SOURCE_DIR/recovery-mode.groovy" "$GROOVY_DIR/basic-security.groovy"
    log "✓ recovery-mode.groovy を basic-security.groovy としてコピーしました"
  else
    log "警告: recovery-mode.groovy が見つかりません"
  fi
fi

# ファイル権限の設定
chown -R jenkins:jenkins $GROOVY_DIR
chmod 644 $GROOVY_DIR/*.groovy 2>/dev/null || true

log "Groovyスクリプトの配置が完了しました"

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
