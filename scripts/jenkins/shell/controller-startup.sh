#!/bin/bash
# Jenkinsコントローラー起動スクリプト
# SSM用に最適化されたバージョン - EFSマウント、インストール、設定後の実行を前提

# エラーハンドリング設定
set -e

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /var/log/jenkins-startup.log
}

# エラーハンドラー
error_exit() {
    log "ERROR: $1"
    exit 1
}

# 引数または環境変数から設定を取得
# ScriptArgsから渡される場合: JENKINS_COLOR=xxx
for arg in "$@"; do
    if [[ $arg == *"="* ]]; then
        export "$arg"
    fi
done

# 環境変数
JENKINS_COLOR="${JENKINS_COLOR:-blue}"
JENKINS_HOME_DIR="/mnt/efs/jenkins"

log "Starting Jenkins service"

# 前提条件の確認
if ! df -h | grep -q "/mnt/efs"; then
  error_exit "EFSがマウントされていません。起動を中止します。"
fi

if ! rpm -q jenkins &>/dev/null; then
  error_exit "Jenkinsがインストールされていません。起動を中止します。"
fi

if [ ! -d "$JENKINS_HOME_DIR/init.groovy.d" ]; then
  log "警告: Jenkinsの設定ディレクトリが見つかりません。設定が完了していない可能性があります。"
fi

# サービス定義ファイルの確認
if [ ! -f "/etc/systemd/system/jenkins.service" ]; then
  error_exit "Jenkinsサービス定義が見つかりません。起動を中止します。"
fi

# ログディレクトリの確認と準備
log "ログディレクトリの確認"
if [ ! -d "$JENKINS_HOME_DIR/logs" ]; then
  log "ログディレクトリを作成します: $JENKINS_HOME_DIR/logs"
  mkdir -p "$JENKINS_HOME_DIR/logs"
  chown jenkins:jenkins "$JENKINS_HOME_DIR/logs"
  chmod 755 "$JENKINS_HOME_DIR/logs"
fi

# ホームディレクトリの権限最終確認
log "Jenkinsホームディレクトリの権限最終確認"
chown jenkins:jenkins "$JENKINS_HOME_DIR"
chmod 755 "$JENKINS_HOME_DIR"

# Jenkinsの起動と起動確認
log "systemdデーモンの再読み込み"
systemctl daemon-reload

log "Jenkinsサービスの有効化"
systemctl enable jenkins

log "Jenkinsサービスの起動"
if ! systemctl start jenkins; then
  log "Jenkinsサービスの起動に失敗しました。ログを確認します:"
  journalctl -u jenkins --no-pager -n 100
  if [ -f "$JENKINS_HOME_DIR/logs/jenkins.log" ]; then
    log "Jenkins独自のログも確認します:"
    tail -n 100 "$JENKINS_HOME_DIR/logs/jenkins.log"
  fi
  error_exit "Jenkinsサービスの起動に失敗しました"
fi

# 起動確認
TIMEOUT=900
INTERVAL=10
ELAPSED=0
log "Jenkinsが完全に起動するのを待機しています..."

while [ $ELAPSED -lt $TIMEOUT ]; do
  if curl -s -f http://localhost:8080/login > /dev/null; then
    log "Jenkinsが正常に起動しました（$ELAPSED 秒経過）"
    break
  fi
  
  # サービス状態の確認
  if ! systemctl is-active jenkins > /dev/null; then
    log "警告: Jenkinsサービスが実行されていません。ログを確認します:"
    systemctl status jenkins --no-pager
    journalctl -u jenkins --no-pager -n 100
    
    if [ -f "$JENKINS_HOME_DIR/logs/jenkins.log" ]; then
      log "Jenkins独自のログも確認します:"
      tail -n 100 "$JENKINS_HOME_DIR/logs/jenkins.log"
    else
      log "Jenkinsログファイルが見つかりません"
    fi
    
    log "サービスを再起動します..."
    systemctl restart jenkins
  fi
  
  log "まだ起動中です... ($ELAPSED 秒経過)"
  sleep $INTERVAL
  ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
  log "エラー: Jenkinsがタイムアウト時間内に起動しませんでした"
  systemctl status jenkins --no-pager
  log "最終的な状態チェック:"
  curl -v http://localhost:8080/ || true
  error_exit "Jenkinsがタイムアウト時間内に起動しませんでした"
fi

# 正常起動の場合はステータス情報を記録
log "Jenkinsが正常に起動しました"

# インスタンスメタデータ取得（IMDSv2対応）
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)

# Jenkinsバージョン情報の取得
JENKINS_VERSION=$(java -jar /usr/share/java/jenkins.war --version 2>/dev/null || echo "バージョン不明")

# SSMパラメータに状態を報告
log "SSMパラメータに起動状態を報告"
STATUS_MESSAGE="$(date '+%Y-%m-%d %H:%M:%S') - Jenkins $JENKINS_VERSION 起動完了 (インスタンス: $INSTANCE_ID)"

aws ssm put-parameter \
  --region $REGION \
  --name "/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/status/${JENKINS_COLOR}" \
  --value "$STATUS_MESSAGE" \
  --type String \
  --overwrite || log "警告: SSMパラメータの更新に失敗しました"

# 起動完了マーカーファイル作成
echo "$STATUS_MESSAGE" > "$JENKINS_HOME_DIR/.startup-complete"
chown jenkins:jenkins "$JENKINS_HOME_DIR/.startup-complete"

log "Jenkins startup completed successfully"
