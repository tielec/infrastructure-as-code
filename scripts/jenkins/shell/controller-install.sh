#!/bin/bash
# Jenkinsコントローラーインストールスクリプト
# SSM用に最適化されたバージョン（EFSマウント後の実行を前提）

# エラーハンドリング設定
set -e

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /var/log/jenkins-install.log
}

# エラーハンドラー
error_exit() {
    log "ERROR: $1"
    exit 1
}

# 引数または環境変数から設定を取得
# 位置引数: $1=JENKINS_VERSION, $2=JENKINS_COLOR
JENKINS_VERSION="${1:-${JENKINS_VERSION:-latest}}"
JENKINS_COLOR="${2:-${JENKINS_COLOR:-blue}}"
JENKINS_HOME_DIR="/mnt/efs/jenkins" # EFSマウント済みであることを前提

log "Starting Jenkins installation script for ${JENKINS_COLOR} environment"

#---------------------------------------
# EBS Volume Expansion (最初に実行)
#---------------------------------------
log "Expanding EBS volume to use full capacity..."

# ルートデバイスの情報を取得
ROOT_DEVICE=$(df / | tail -1 | awk '{print $1}')
log "Root device: $ROOT_DEVICE"

# デバイス名からパーティション番号を取得
if [[ "$ROOT_DEVICE" =~ nvme ]]; then
    DEVICE_NAME=$(echo "$ROOT_DEVICE" | sed 's/p[0-9]*$//')
    PARTITION_NUM=$(echo "$ROOT_DEVICE" | grep -o '[0-9]*$')
else
    DEVICE_NAME=$(echo "$ROOT_DEVICE" | sed 's/[0-9]*$//')
    PARTITION_NUM=$(echo "$ROOT_DEVICE" | grep -o '[0-9]*$')
fi

# cloud-utils-growpartのインストール
dnf install -y cloud-utils-growpart || yum install -y cloud-utils-growpart

# パーティションの拡張
growpart "$DEVICE_NAME" "$PARTITION_NUM" || log "Partition might already be expanded"

# ファイルシステムの拡張
FS_TYPE=$(blkid -o value -s TYPE "$ROOT_DEVICE")
if [[ "$FS_TYPE" =~ ext[234] ]]; then
    resize2fs "$ROOT_DEVICE"
elif [[ "$FS_TYPE" == "xfs" ]]; then
    xfs_growfs -d /
fi

log "Disk usage after expansion:"
df -h / | tee -a /var/log/jenkins-install.log

# EFSマウント確認
if ! df -h | grep -q "/mnt/efs"; then
  error_exit "EFSがマウントされていません。先にEFSマウントスクリプトを実行してください。"
fi

# システムのアップデートと必要なパッケージのインストール
log "システムの更新と必要なパッケージのインストール"
dnf update -y
dnf install -y java-21-amazon-corretto docker git jq wget amazon-ssm-agent aws-cfn-bootstrap

# サービスの有効化
log "システムサービスの有効化"
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent
systemctl enable docker
systemctl start docker

# Jenkinsユーザーの設定（EFSマウント済みを前提）
log "Jenkinsユーザーとグループの設定"
groupadd -f jenkins
# EFSマウント済みのディレクトリをホームに指定
useradd -m -d $JENKINS_HOME_DIR -g jenkins jenkins 2>/dev/null || true
usermod -aG docker jenkins

# UID/GIDを取得
JENKINS_UID=$(id -u jenkins)
JENKINS_GID=$(getent group jenkins | cut -d: -f3)
log "Jenkins UID:GID = $JENKINS_UID:$JENKINS_GID"

# Jenkinsディレクトリ所有権確認
log "Jenkinsディレクトリの所有権を確認"

# 初回セットアップフラグの確認（EFS上の大量ファイルに対するchown -Rを避けるため）
SETUP_FLAG="$JENKINS_HOME_DIR/.ownership_set"

if [ ! -f "$SETUP_FLAG" ]; then
    log "初回セットアップ: 全ファイルの所有権を設定します（時間がかかる場合があります）"
    chown -R jenkins:jenkins $JENKINS_HOME_DIR
    # フラグファイルを作成
    touch "$SETUP_FLAG"
    chown jenkins:jenkins "$SETUP_FLAG"
    log "所有権の設定が完了しました"
else
    log "所有権は既に設定済みです。トップレベルディレクトリのみ確認します"
    # トップレベルディレクトリの所有権のみ確認（高速）
    chown jenkins:jenkins $JENKINS_HOME_DIR
    # 新規作成される可能性のあるディレクトリのみ確認
    [ -d "$JENKINS_HOME_DIR/logs" ] && chown jenkins:jenkins "$JENKINS_HOME_DIR/logs"
    [ -d "$JENKINS_HOME_DIR/plugins" ] && chown jenkins:jenkins "$JENKINS_HOME_DIR/plugins"
fi

# Jenkinsのインストール
log "Jenkinsパッケージリポジトリの設定"
wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io-2023.key

# バージョン指定がある場合
if [ "${JENKINS_VERSION}" != "latest" ]; then
  log "指定されたバージョンのJenkinsをインストール: ${JENKINS_VERSION}"
  dnf install -y jenkins-${JENKINS_VERSION}
else
  log "最新バージョンのJenkinsをインストール"
  dnf install -y jenkins
fi

# インストールされたバージョンを確認
INSTALLED_VERSION=$(rpm -q jenkins --queryformat '%{VERSION}')
log "インストールされたJenkinsバージョン: $INSTALLED_VERSION"

# Jenkinsサービス定義を上書き（EFSをJENKINS_HOMEとして使用）
log "Jenkinsサービス定義の作成"
cat > /etc/systemd/system/jenkins.service << EOF
[Unit]
Description=Jenkins Automation Server
After=network.target

[Service]
Type=simple
User=jenkins
Group=jenkins
Environment="JENKINS_HOME=$JENKINS_HOME_DIR"
Environment="JENKINS_WAR=/usr/share/java/jenkins.war"
Environment="JENKINS_LOG=$JENKINS_HOME_DIR/logs/jenkins.log"
Environment="JAVA_OPTS=-Djava.awt.headless=true -Djenkins.install.runSetupWizard=false -Dhudson.model.DownloadService.noSignatureCheck=true -Djenkins.security.canSetSecurityRealm=true -Djenkins.websocket.pingInterval=15 -Djenkins.websocket.idleTimeout=600 -Dhudson.slaves.ChannelPinger.pingIntervalSeconds=15 -Dhudson.slaves.ChannelPinger.timeoutSeconds=60"
Environment="JENKINS_OPTS=--httpPort=8080"
WorkingDirectory=$JENKINS_HOME_DIR
StandardOutput=append:$JENKINS_HOME_DIR/logs/jenkins.log
StandardError=append:$JENKINS_HOME_DIR/logs/jenkins.log
LimitNOFILE=8192
TimeoutStartSec=900
Restart=on-failure
RestartSec=10

ExecStartPre=/bin/rm -f $JENKINS_HOME_DIR/jenkins.pid
ExecStart=/usr/bin/java \$JAVA_OPTS -jar \$JENKINS_WAR \$JENKINS_OPTS

[Install]
WantedBy=multi-user.target
EOF

chmod 600 /etc/systemd/system/jenkins.service

# ログファイル用ディレクトリの確認と準備
log "ログディレクトリの準備"
mkdir -p $JENKINS_HOME_DIR/logs
chown jenkins:jenkins $JENKINS_HOME_DIR/logs
chmod 755 $JENKINS_HOME_DIR/logs

# プラグイン用ディレクトリの確認
log "プラグインディレクトリの確認"
mkdir -p $JENKINS_HOME_DIR/plugins
chown jenkins:jenkins $JENKINS_HOME_DIR/plugins

# 追加: WAR ファイルをコピーして権限確保（オプショナル）
log "Jenkins WAR ファイルの確認"
if [ -f "/usr/share/java/jenkins.war" ]; then
  log "Jenkins WAR ファイルの権限設定"
  chmod 644 /usr/share/java/jenkins.war
else
  log "警告: Jenkins WAR ファイルが見つかりません"
fi

# SSMエージェントのインストール確認
if ! systemctl is-active amazon-ssm-agent > /dev/null; then
  log "SSM Agent is not running. Starting it..."
  systemctl start amazon-ssm-agent
fi

log "Jenkins controller installation completed."
log "次のステップ: Jenkinsの設定とサービスの起動"
