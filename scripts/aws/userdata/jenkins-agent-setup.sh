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
mount -o remount,size=10G /tmp
echo "/tmpのサイズを10GBに設定しました"

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

# ===== ECR credential-helper のインストールと設定 =====
# docker-credential-ecr-login がない場合のみインストール（冪等性の確保）
if ! command -v docker-credential-ecr-login &>/dev/null; then
  echo "Installing ECR credential-helper..."
  dnf install -y amazon-ecr-credential-helper || echo "WARNING: amazon-ecr-credential-helper のインストールに失敗しました"
else
  echo "ECR credential-helper は既にインストール済みです（スキップ）"
fi

# IMDSv2トークンを使用してAWSアカウントIDを取得
echo "Retrieving AWS Account ID via IMDSv2..."
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" || echo "")
if [ -n "$TOKEN" ]; then
  ACCOUNT_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/dynamic/instance-identity/document | jq -r .accountId)
else
  ACCOUNT_ID=""
fi

if [ -z "$ACCOUNT_ID" ] || [ "$ACCOUNT_ID" = "null" ]; then
  echo "WARNING: ACCOUNT_IDの取得に失敗しました。ワイルドカード形式を使用します。"
  ECR_ENDPOINT="*.dkr.ecr.*.amazonaws.com"
else
  echo "AWS Account ID: $ACCOUNT_ID"
  ECR_ENDPOINT="${ACCOUNT_ID}.dkr.ecr.ap-northeast-1.amazonaws.com"
fi

# jenkinsユーザー用 Docker config.json
mkdir -p /home/jenkins/.docker
cat > /home/jenkins/.docker/config.json << EOF
{
  "credHelpers": {
    "${ECR_ENDPOINT}": "ecr-login"
  }
}
EOF
chown jenkins:jenkins /home/jenkins/.docker
chown jenkins:jenkins /home/jenkins/.docker/config.json

# rootユーザー用 Docker config.json
mkdir -p /root/.docker
cat > /root/.docker/config.json << EOF
{
  "credHelpers": {
    "${ECR_ENDPOINT}": "ecr-login"
  }
}
EOF
echo "ECR credential-helper の設定が完了しました"
# ===== ECR credential-helper 設定完了 =====

# 環境情報の保存
echo "PROJECT_NAME=${PROJECT_NAME}" > /etc/jenkins-agent-env
echo "ENVIRONMENT=${ENVIRONMENT}" >> /etc/jenkins-agent-env
echo "AGENT_ROOT=/home/jenkins/agent" >> /etc/jenkins-agent-env
${ARCHITECTURE_ENV}
chmod 644 /etc/jenkins-agent-env

# SSMエージェントの起動
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

# Javaのインストール（最後に実行）
echo "Installing Java..."
dnf install -y java-21-amazon-corretto

# 起動完了のマーク
echo "$(date) - Agent bootstrap completed" > /home/jenkins/agent/bootstrap-complete
chown jenkins:jenkins /home/jenkins/agent/bootstrap-complete
