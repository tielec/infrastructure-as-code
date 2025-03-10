#!/bin/bash
# エラーハンドリングとログ設定
set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
set -x
echo "Starting Jenkins installation script for ${color} environment"

# システムのアップデートと必要なパッケージのインストール
dnf update -y
dnf install -y java-17-amazon-corretto docker git jq amazon-efs-utils wget amazon-ssm-agent aws-cfn-bootstrap

# サービスの有効化
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent
systemctl enable docker
systemctl start docker

# EFSマウントポイントの作成
mkdir -p /mnt/efs

# Jenkinsディレクトリの準備
mkdir -p /mnt/efs/jenkins/{logs,plugins,jobs,secrets,nodes,init.groovy.d}

# Jenkinsユーザーの設定
groupadd -f jenkins
useradd -m -d /mnt/efs/jenkins -g jenkins jenkins || true
usermod -aG docker jenkins
chown -R jenkins:jenkins /mnt/efs/jenkins

# Jenkinsのインストール
wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io-2023.key
dnf install -y jenkins

# Jenkinsサービス定義
cat > /etc/systemd/system/jenkins.service << 'EOF'
[Unit]
Description=Jenkins Automation Server
After=network.target

[Service]
Type=simple
User=jenkins
Group=jenkins
Environment="JENKINS_HOME=/mnt/efs/jenkins"
Environment="JENKINS_WAR=/usr/share/java/jenkins.war"
Environment="JENKINS_LOG=/mnt/efs/jenkins/logs/jenkins.log"
Environment="JAVA_OPTS=-Djava.awt.headless=true -Djenkins.install.runSetupWizard=false -Dhudson.model.DownloadService.noSignatureCheck=true -Djenkins.security.canSetSecurityRealm=true"
Environment="JENKINS_OPTS=--httpPort=8080"
WorkingDirectory=/mnt/efs/jenkins
StandardOutput=append:/mnt/efs/jenkins/logs/jenkins.log
StandardError=append:/mnt/efs/jenkins/logs/jenkins.log
LimitNOFILE=8192
TimeoutStartSec=900
Restart=on-failure
RestartSec=10

ExecStartPre=/bin/rm -f /mnt/efs/jenkins/jenkins.pid
ExecStart=/usr/bin/java $JAVA_OPTS -jar $JENKINS_WAR $JENKINS_OPTS

[Install]
WantedBy=multi-user.target
EOF

chmod 600 /etc/systemd/system/jenkins.service
