#!/bin/bash
# Jenkinsコントローラーインストールスクリプト
# SSM用に最適化されたバージョン（EFSマウント後の実行を前提）

# エラーハンドリングとログ設定
set -e
exec > >(tee /var/log/jenkins-install.log|logger -t jenkins-install -s 2>/dev/console) 2>&1
set -x

# 環境変数
JENKINS_COLOR="${JENKINS_COLOR:-blue}"
JENKINS_VERSION="${JENKINS_VERSION:-latest}"
JENKINS_HOME_DIR="/mnt/efs/jenkins" # EFSマウント済みであることを前提

echo "Starting Jenkins installation script for ${JENKINS_COLOR} environment"

# EFSマウント確認
if ! df -h | grep -q "/mnt/efs"; then
  echo "エラー: EFSがマウントされていません。インストールを中止します。"
  echo "先にEFSマウントスクリプトを実行してください。"
  exit 1
fi

# システムのアップデートと必要なパッケージのインストール
echo "システムの更新と必要なパッケージのインストール"
dnf update -y
dnf install -y java-17-amazon-corretto docker git jq wget amazon-ssm-agent aws-cfn-bootstrap

# サービスの有効化
echo "システムサービスの有効化"
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent
systemctl enable docker
systemctl start docker

# Jenkinsユーザーの設定（EFSマウント済みを前提）
echo "Jenkinsユーザーとグループの設定"
groupadd -f jenkins
# EFSマウント済みのディレクトリをホームに指定
useradd -m -d $JENKINS_HOME_DIR -g jenkins jenkins 2>/dev/null || true
usermod -aG docker jenkins

# UID/GIDを取得
JENKINS_UID=$(id -u jenkins)
JENKINS_GID=$(getent group jenkins | cut -d: -f3)
echo "Jenkins UID:GID = $JENKINS_UID:$JENKINS_GID"

# Jenkinsディレクトリ所有権確認
echo "Jenkinsディレクトリの所有権を確認"
chown -R jenkins:jenkins $JENKINS_HOME_DIR

# Jenkinsのインストール
echo "Jenkinsパッケージリポジトリの設定"
wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io-2023.key

# バージョン指定がある場合
if [ "${JENKINS_VERSION}" != "latest" ]; then
  echo "指定されたバージョンのJenkinsをインストール: ${JENKINS_VERSION}"
  dnf install -y jenkins-${JENKINS_VERSION}
else
  echo "最新バージョンのJenkinsをインストール"
  dnf install -y jenkins
fi

# インストールされたバージョンを確認
INSTALLED_VERSION=$(rpm -q jenkins --queryformat '%{VERSION}')
echo "インストールされたJenkinsバージョン: $INSTALLED_VERSION"

# Jenkinsサービス定義を上書き（EFSをJENKINS_HOMEとして使用）
echo "Jenkinsサービス定義の作成"
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
Environment="JAVA_OPTS=-Djava.awt.headless=true -Djenkins.install.runSetupWizard=false -Dhudson.model.DownloadService.noSignatureCheck=true -Djenkins.security.canSetSecurityRealm=true"
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
echo "ログディレクトリの準備"
mkdir -p $JENKINS_HOME_DIR/logs
chown jenkins:jenkins $JENKINS_HOME_DIR/logs
chmod 755 $JENKINS_HOME_DIR/logs

# プラグイン用ディレクトリの確認
echo "プラグインディレクトリの確認"
mkdir -p $JENKINS_HOME_DIR/plugins
chown jenkins:jenkins $JENKINS_HOME_DIR/plugins

# 追加: WAR ファイルをコピーして権限確保（オプショナル）
echo "Jenkins WAR ファイルの確認"
if [ -f "/usr/share/java/jenkins.war" ]; then
  echo "Jenkins WAR ファイルの権限設定"
  chmod 644 /usr/share/java/jenkins.war
else
  echo "警告: Jenkins WAR ファイルが見つかりません"
fi

# SSMエージェントのインストール確認
if ! systemctl is-active amazon-ssm-agent > /dev/null; then
  echo "SSM Agent is not running. Starting it..."
  systemctl start amazon-ssm-agent
fi

echo "Jenkins controller installation completed."
echo "次のステップ: Jenkinsの設定とサービスの起動"