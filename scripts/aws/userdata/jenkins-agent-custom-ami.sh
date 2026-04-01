#!/bin/bash
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
set -x

${IPV6_CONFIG}# スワップの有効化（既に作成済み）
swapon /swapfile || true

# /tmpの容量を確保（tmpfsのサイズを調整）
# 注意: EC2 Fleetプラグインが一時的に/tmpを使用する可能性があるため、十分な容量を確保
mount -o remount,size=10G /tmp
echo "/tmpのサイズを10GBに設定しました"

# Dockerの起動と権限設定
systemctl start docker
chmod 666 /var/run/docker.sock || true
usermod -aG docker jenkins || true

# ===== ECR credential-helper のフォールバック設定 =====
# docker-credential-ecr-login がない場合はインストール（古いAMIからの起動時の保護）
if ! command -v docker-credential-ecr-login &>/dev/null; then
  echo "docker-credential-ecr-login が未インストールです。インストールします..."
  dnf install -y amazon-ecr-credential-helper || echo "WARNING: amazon-ecr-credential-helper のインストールに失敗しました"
fi

# カスタムAMIにconfig.jsonが含まれている場合はスキップ（冪等性の確保）
# jenkins, root, ec2-user の3ユーザーすべてにconfig.jsonが存在するか確認
if [ -f /home/jenkins/.docker/config.json ] && jq -e '.credHelpers' /home/jenkins/.docker/config.json >/dev/null 2>&1 \
   && [ -f /home/ec2-user/.docker/config.json ] && jq -e '.credHelpers' /home/ec2-user/.docker/config.json >/dev/null 2>&1; then
  echo "ECR credential-helper config.json は既に設定済みです（スキップ）"
else
  echo "ECR credential-helper config.json が未設定です。動的生成を実行します..."
  # IMDSv2トークンを使用してAWSアカウントIDを取得
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

  mkdir -p /home/jenkins/.docker
  cat > /home/jenkins/.docker/config.json << EOF
{
  "credHelpers": {
    "${ECR_ENDPOINT}": "ecr-login"
  }
}
EOF
  chown jenkins:jenkins /home/jenkins/.docker/config.json

  mkdir -p /root/.docker
  cat > /root/.docker/config.json << EOF
{
  "credHelpers": {
    "${ECR_ENDPOINT}": "ecr-login"
  }
}
EOF

  # ec2-userユーザー用 config.json（Jenkins SSH接続ユーザー）
  mkdir -p /home/ec2-user/.docker
  cat > /home/ec2-user/.docker/config.json << EOF
{
  "credHelpers": {
    "${ECR_ENDPOINT}": "ecr-login"
  }
}
EOF
  chown ec2-user:ec2-user /home/ec2-user/.docker /home/ec2-user/.docker/config.json

  echo "ECR credential-helper config.json を動的生成しました"
fi
# ===== ECR credential-helper フォールバック設定完了 =====

# 環境情報の保存
echo "PROJECT_NAME=${PROJECT_NAME}" > /etc/jenkins-agent-env
echo "ENVIRONMENT=${ENVIRONMENT}" >> /etc/jenkins-agent-env
echo "AGENT_ROOT=/home/jenkins/agent" >> /etc/jenkins-agent-env
${ARCHITECTURE_ENV}
${IPV6_ENV}
chmod 644 /etc/jenkins-agent-env

# SSMエージェントの起動
systemctl start amazon-ssm-agent

# 起動完了のマーク
echo "$(date) - Agent bootstrap completed (custom AMI)" > /home/jenkins/agent/bootstrap-complete
chown jenkins:jenkins /home/jenkins/agent/bootstrap-complete
