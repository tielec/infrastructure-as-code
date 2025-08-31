#!/bin/bash
# Jenkins Agent Bootstrap Script
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
set -x

# スワップファイルの作成（2GB）
dd if=/dev/zero of=/swapfile bs=1M count=2048
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# /tmpの容量を確保（tmpfsのサイズを調整）
# 注意: EC2 Fleetプラグインが一時的に/tmpを使用する可能性があるため、十分な容量を確保
# デフォルトでメモリの50%まで使用可能にする（最小3GB、最大10GB）
TOTAL_MEM=$(free -g | awk '/^Mem:/ {print $2}')
TMP_SIZE=$((TOTAL_MEM / 2))
if [ $TMP_SIZE -lt 3 ]; then
    TMP_SIZE=3
elif [ $TMP_SIZE -gt 10 ]; then
    TMP_SIZE=10
fi
mount -o remount,size=${TMP_SIZE}G /tmp
echo "/tmpのサイズを${TMP_SIZE}GBに設定しました"

# システムのアップデートと必要なパッケージのインストール（Javaを除く）
dnf update -y
dnf install -y docker git jq amazon-ssm-agent

# 不要なパッケージキャッシュをクリーンアップ
dnf clean all

# Dockerの設定と起動
systemctl enable docker
systemctl start docker

# Dockerソケットの権限設定
chmod 666 /var/run/docker.sock || true

# Jenkinsユーザーの作成
useradd -m -d /home/jenkins -s /bin/bash jenkins
usermod -aG docker jenkins

# エージェント作業ディレクトリの設定
mkdir -p /home/jenkins/agent
chown -R jenkins:jenkins /home/jenkins

# 環境情報の保存
echo "PROJECT_NAME=${PROJECT_NAME}" > /etc/jenkins-agent-env
echo "ENVIRONMENT=${ENVIRONMENT}" >> /etc/jenkins-agent-env
echo "AGENT_ROOT=/home/jenkins/agent" >> /etc/jenkins-agent-env
${ARCHITECTURE_ENV}chmod 644 /etc/jenkins-agent-env

# SSMエージェントの起動
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

# Javaのインストール（最後に実行）
echo "Installing Java..."
dnf install -y java-21-amazon-corretto

# 起動完了のマーク
echo "$(date) - Agent bootstrap completed" > /home/jenkins/agent/bootstrap-complete
chown jenkins:jenkins /home/jenkins/agent/bootstrap-complete