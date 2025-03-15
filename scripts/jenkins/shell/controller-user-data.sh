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

# インスタンスIDとリージョンの取得
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)

# SSMドキュメントを実行
echo "Running Jenkins installation via SSM Documents"

# 1. Jenkins Install
aws ssm send-command \
  --region $REGION \
  --document-name "${PROJECT_NAME}-jenkins-install-${JENKINS_COLOR}-${ENVIRONMENT}" \
  --targets "Key=instanceids,Values=$INSTANCE_ID" \
  --parameters "ProjectName=${PROJECT_NAME},Environment=${ENVIRONMENT},JenkinsVersion=${JENKINS_VERSION},JenkinsColor=${JENKINS_COLOR}" \
  --comment "Installing Jenkins" \
  --max-concurrency 1 \
  --max-errors 0

# 2. EFS Mount (if EFS ID is provided)
if [ -n "${EFS_ID}" ]; then
  aws ssm send-command \
    --region $REGION \
    --document-name "${PROJECT_NAME}-jenkins-mount-efs-${JENKINS_COLOR}-${ENVIRONMENT}" \
    --targets "Key=instanceids,Values=$INSTANCE_ID" \
    --parameters "ProjectName=${PROJECT_NAME},Environment=${ENVIRONMENT},EfsId=${EFS_ID},Region=$REGION" \
    --comment "Mounting EFS" \
    --max-concurrency 1 \
    --max-errors 0
else
  echo "No EFS specified, skipping EFS mount"
fi

# 3. Jenkins Configure
aws ssm send-command \
  --region $REGION \
  --document-name "${PROJECT_NAME}-jenkins-configure-${JENKINS_COLOR}-${ENVIRONMENT}" \
  --targets "Key=instanceids,Values=$INSTANCE_ID" \
  --parameters "ProjectName=${PROJECT_NAME},Environment=${ENVIRONMENT},JenkinsMode=${JENKINS_MODE},JenkinsColor=${JENKINS_COLOR}" \
  --comment "Configuring Jenkins" \
  --max-concurrency 1 \
  --max-errors 0

# 4. Jenkins Startup
aws ssm send-command \
  --region $REGION \
  --document-name "${PROJECT_NAME}-jenkins-startup-${JENKINS_COLOR}-${ENVIRONMENT}" \
  --targets "Key=instanceids,Values=$INSTANCE_ID" \
  --parameters "ProjectName=${PROJECT_NAME},Environment=${ENVIRONMENT},JenkinsColor=${JENKINS_COLOR}" \
  --comment "Starting Jenkins" \
  --max-concurrency 1 \
  --max-errors 0

echo "Jenkins setup initiated through SSM"