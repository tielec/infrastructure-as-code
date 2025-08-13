#!/bin/bash

# jenkins-agentスタックのテスト

echo "=========================================="
echo "Testing jenkins-agent Stack"
echo "=========================================="

# 環境変数の設定
export AWS_REGION="ap-northeast-1"
export AWS_DEFAULT_REGION="ap-northeast-1"
export PULUMI_CONFIG_PASSPHRASE=$(aws ssm get-parameter --name "/bootstrap/pulumi/config-passphrase" --with-decryption --query 'Parameter.Value' --output text)

# S3バケット名を取得
S3_BUCKET=$(aws ssm get-parameter --name "/bootstrap/pulumi/s3bucket-name" --query 'Parameter.Value' --output text)

# jenkins-agentディレクトリに移動
cd /home/ec2-user/infrastructure-as-code/pulumi/jenkins-agent

# ローカルキャッシュをクリア
echo "1. Clearing local cache..."
rm -rf .pulumi
rm -rf ~/.pulumi/workspaces/jenkins-agent-*

# S3バックエンドにログイン
echo ""
echo "2. Logging in to S3 backend..."
pulumi login s3://${S3_BUCKET}

# スタックを選択
echo ""
echo "3. Selecting dev stack..."
pulumi stack select dev

# 現在のスタックを確認
echo ""
echo "4. Current stack:"
pulumi stack --show-name

# スタック一覧
echo ""
echo "5. Stack list:"
pulumi stack ls

# スタックの詳細情報
echo ""
echo "6. Stack info:"
pulumi stack -v 3 2>&1 | head -10

# プレビューをテスト
echo ""
echo "7. Testing preview..."
pulumi preview 2>&1 | head -30

echo ""
echo "=========================================="
echo "Test completed"
echo "=========================================="