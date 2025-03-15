#!/bin/bash
# 最小限の初期設定スクリプト - SSMエージェントのセットアップと初期実行のみ
set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

# システムの更新とSSMエージェントのインストール
dnf update -y
dnf install -y amazon-ssm-agent aws-cli jq

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

# SSMコマンドを実行し、完了を待機する関数
execute_ssm_command_and_wait() {
  local document_name=$1
  local comment=$2
  local additional_params=$3

  echo "Running $document_name..."
  
  # SSMコマンドを実行
  local cmd_json=$(aws ssm send-command \
    --region "$REGION" \
    --document-name "$document_name" \
    --targets "Key=instanceids,Values=$INSTANCE_ID" \
    --parameters "ProjectName=${PROJECT_NAME},Environment=${ENVIRONMENT}$additional_params" \
    --comment "$comment" \
    --max-concurrency 1 \
    --max-errors 0 \
    --output json)
  
  # コマンドIDを抽出
  local cmd_id=$(echo "$cmd_json" | jq -r '.Command.CommandId')
  
  if [ -z "$cmd_id" ] || [ "$cmd_id" == "null" ]; then
    echo "ERROR: Failed to execute $document_name. Command ID not returned."
    return 1
  fi
  
  echo "Command ID: $cmd_id - Waiting for completion..."
  
  # コマンドの完了を待機
  local status="Pending"
  local max_wait=600  # 10分タイムアウト
  local wait_interval=10
  local elapsed=0
  
  while [ "$status" == "Pending" ] || [ "$status" == "InProgress" ]; do
    sleep $wait_interval
    elapsed=$((elapsed + wait_interval))
    
    # コマンドの状態を確認
    local cmd_status_json=$(aws ssm get-command-invocation \
      --region "$REGION" \
      --command-id "$cmd_id" \
      --instance-id "$INSTANCE_ID" \
      --output json 2>/dev/null || echo '{"Status":"Failed"}')
    
    status=$(echo "$cmd_status_json" | jq -r '.Status')
    
    echo "Status: $status - Elapsed time: $elapsed seconds"
    
    # タイムアウトチェック
    if [ $elapsed -ge $max_wait ]; then
      echo "ERROR: Timed out waiting for $document_name to complete"
      return 1
    fi
  done
  
  # 実行結果の確認
  if [ "$status" != "Success" ]; then
    echo "ERROR: $document_name failed with status: $status"
    # エラー出力を表示
    echo "Command output:"
    echo "$cmd_status_json" | jq -r '.StandardOutputContent'
    echo "Error output:"
    echo "$cmd_status_json" | jq -r '.StandardErrorContent'
    return 1
  fi
  
  echo "$document_name completed successfully"
  return 0
}

# SSMドキュメントを順番に実行
echo "Starting Jenkins installation via SSM Documents"

# 1. EFS Mount (最初に実行)
if [ -n "${EFS_ID}" ]; then
  execute_ssm_command_and_wait \
    "${PROJECT_NAME}-jenkins-mount-efs-${JENKINS_COLOR}-${ENVIRONMENT}" \
    "Mounting EFS" \
    ",EfsId=${EFS_ID},Region=$REGION"
  
  if [ $? -ne 0 ]; then
    echo "EFS mount failed, exiting"
    exit 1
  fi
else
  echo "No EFS specified, skipping EFS mount"
fi

# 2. Jenkins Install
execute_ssm_command_and_wait \
  "${PROJECT_NAME}-jenkins-install-${JENKINS_COLOR}-${ENVIRONMENT}" \
  "Installing Jenkins" \
  ",JenkinsVersion=${JENKINS_VERSION},JenkinsColor=${JENKINS_COLOR}"

if [ $? -ne 0 ]; then
  echo "Jenkins installation failed, exiting"
  exit 1
fi

# 3. Jenkins Configure
execute_ssm_command_and_wait \
  "${PROJECT_NAME}-jenkins-configure-${JENKINS_COLOR}-${ENVIRONMENT}" \
  "Configuring Jenkins" \
  ",JenkinsMode=${JENKINS_MODE},JenkinsColor=${JENKINS_COLOR}"

if [ $? -ne 0 ]; then
  echo "Jenkins configuration failed, exiting"
  exit 1
fi

# 4. Jenkins Startup
execute_ssm_command_and_wait \
  "${PROJECT_NAME}-jenkins-startup-${JENKINS_COLOR}-${ENVIRONMENT}" \
  "Starting Jenkins" \
  ",JenkinsColor=${JENKINS_COLOR}"

if [ $? -ne 0 ]; then
  echo "Jenkins startup failed, exiting"
  exit 1
fi

echo "Jenkins setup completed successfully through SSM"
