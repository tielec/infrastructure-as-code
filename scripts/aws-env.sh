#!/bin/bash
# AWS認証情報を取得して環境変数として出力

# IAMロール名の取得 (EC2メタデータサービスから)
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
ROLE_NAME=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/)
echo "# Role name: $ROLE_NAME" >&2

if [ -n "$ROLE_NAME" ]; then
  # EC2インスタンスからIAMロール認証情報を取得
  CREDENTIALS=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/$ROLE_NAME)
  AWS_ACCESS_KEY_ID=$(echo $CREDENTIALS | jq -r '.AccessKeyId')
  AWS_SECRET_ACCESS_KEY=$(echo $CREDENTIALS | jq -r '.SecretAccessKey')
  AWS_SESSION_TOKEN=$(echo $CREDENTIALS | jq -r '.Token')
  AWS_REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)
  
  # 環境変数としてエクスポート
  echo "export AWS_ACCESS_KEY_ID=\"$AWS_ACCESS_KEY_ID\""
  echo "export AWS_SECRET_ACCESS_KEY=\"$AWS_SECRET_ACCESS_KEY\""
  echo "export AWS_SESSION_TOKEN=\"$AWS_SESSION_TOKEN\""
  echo "export AWS_REGION=\"$AWS_REGION\""
  echo "# AWS認証情報がメタデータサービスから正常に取得されました" >&2
else
  # ~/.aws/credentialsから認証情報を取得
  AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
  AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)
  AWS_SESSION_TOKEN=$(aws configure get aws_session_token 2>/dev/null || echo "")
  AWS_REGION=$(aws configure get region 2>/dev/null || echo "ap-northeast-1")
  
  echo "export AWS_ACCESS_KEY_ID=\"$AWS_ACCESS_KEY_ID\""
  echo "export AWS_SECRET_ACCESS_KEY=\"$AWS_SECRET_ACCESS_KEY\""
  [ -n "$AWS_SESSION_TOKEN" ] && echo "export AWS_SESSION_TOKEN=\"$AWS_SESSION_TOKEN\""
  echo "export AWS_REGION=\"$AWS_REGION\""
  echo "# AWS認証情報がAWS CLIの設定から取得されました" >&2
fi
