#!/bin/bash
# 最小限の初期設定スクリプト - SSMエージェントのセットアップと初期実行のみ
set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

# システムの更新とSSMエージェントのインストール
dnf update -y
dnf install -y amazon-ssm-agent aws-cli

# SSMエージェントの起動
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

# IMDSv2対応 - トークンを取得してからメタデータにアクセス
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)

# 環境変数のロギング（デバッグ用）
echo "DEBUG: INSTANCE_ID=$INSTANCE_ID"
echo "DEBUG: REGION=$REGION"
echo "DEBUG: PROJECT_NAME=${PROJECT_NAME}"
echo "DEBUG: ENVIRONMENT=${ENVIRONMENT}"
echo "DEBUG: JENKINS_COLOR=${JENKINS_COLOR}"
echo "DEBUG: JENKINS_VERSION=${JENKINS_VERSION}"
echo "DEBUG: JENKINS_MODE=${JENKINS_MODE}"
echo "DEBUG: EFS_ID=${EFS_ID}"

if [ -z "$INSTANCE_ID" ]; then
  echo "ERROR: Failed to detect instance ID from metadata service"
  echo "Cannot proceed with SSM commands without instance ID"
  exit 1
fi

# SSMドキュメントを実行
echo "Running Jenkins installation via SSM Documents"

# 1. Jenkins Install
echo "Running Jenkins install document"
aws ssm send-command \
  --region "$REGION" \
  --document-name "${PROJECT_NAME}-jenkins-install-${JENKINS_COLOR}-${ENVIRONMENT}" \
  --targets "Key=instanceids,Values=$INSTANCE_ID" \
  --parameters "ProjectName=${PROJECT_NAME},Environment=${ENVIRONMENT},JenkinsVersion=${JENKINS_VERSION},JenkinsColor=${JENKINS_COLOR}" \
  --comment "Installing Jenkins" \
  --max-concurrency 1 \
  --max-errors 0 || echo "Warning: Failed to run install document"

# 実行結果を確認（5秒待機）
sleep 5

# 2. EFS Mount (if EFS ID is provided)
if [ -n "${EFS_ID}" ]; then
  echo "Running EFS mount document"
  aws ssm send-command \
    --region "$REGION" \
    --document-name "${PROJECT_NAME}-jenkins-mount-efs-${JENKINS_COLOR}-${ENVIRONMENT}" \
    --targets "Key=instanceids,Values=$INSTANCE_ID" \
    --parameters "ProjectName=${PROJECT_NAME},Environment=${ENVIRONMENT},EfsId=${EFS_ID},Region=$REGION" \
    --comment "Mounting EFS" \
    --max-concurrency 1 \
    --max-errors 0 || echo "Warning: Failed to run EFS mount document"
  
  # 実行結果を確認（5秒待機）
  sleep 5
else
  echo "No EFS specified, skipping EFS mount"
fi

# 3. Jenkins Configure
echo "Running Jenkins configure document"
aws ssm send-command \
  --region "$REGION" \
  --document-name "${PROJECT_NAME}-jenkins-configure-${JENKINS_COLOR}-${ENVIRONMENT}" \
  --targets "Key=instanceids,Values=$INSTANCE_ID" \
  --parameters "ProjectName=${PROJECT_NAME},Environment=${ENVIRONMENT},JenkinsMode=${JENKINS_MODE},JenkinsColor=${JENKINS_COLOR}" \
  --comment "Configuring Jenkins" \
  --max-concurrency 1 \
  --max-errors 0 || echo "Warning: Failed to run configure document"

# 実行結果を確認（5秒待機）
sleep 5

# 4. Jenkins Startup
echo "Running Jenkins startup document"
aws ssm send-command \
  --region "$REGION" \
  --document-name "${PROJECT_NAME}-jenkins-startup-${JENKINS_COLOR}-${ENVIRONMENT}" \
  --targets "Key=instanceids,Values=$INSTANCE_ID" \
  --parameters "ProjectName=${PROJECT_NAME},Environment=${ENVIRONMENT},JenkinsColor=${JENKINS_COLOR}" \
  --comment "Starting Jenkins" \
  --max-concurrency 1 \
  --max-errors 0 || echo "Warning: Failed to run startup document"

echo "Jenkins setup initiated through SSM"

# 失敗した場合にエラーログを残す
if [ $? -ne 0 ]; then
  echo "ERROR: One or more SSM commands failed. Check the AWS SSM console for details."
  # SSMエージェントのステータスを確認
  systemctl status amazon-ssm-agent || true
fi
