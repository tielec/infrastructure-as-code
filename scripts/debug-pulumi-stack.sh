#!/bin/bash

# デバッグスクリプト: Pulumi S3バックエンドのスタック問題を診断

echo "=========================================="
echo "Pulumi Stack Debug Script"
echo "=========================================="

# 環境変数の設定
export AWS_REGION="ap-northeast-1"
export AWS_DEFAULT_REGION="ap-northeast-1"

# SSMからパスフレーズを取得
echo "1. Getting PULUMI_CONFIG_PASSPHRASE from SSM..."
export PULUMI_CONFIG_PASSPHRASE=$(aws ssm get-parameter --name "/bootstrap/pulumi/config-passphrase" --with-decryption --query 'Parameter.Value' --output text)
if [ $? -eq 0 ]; then
    echo "   ✓ Passphrase retrieved successfully"
else
    echo "   ✗ Failed to retrieve passphrase"
    exit 1
fi

# S3バケット名を取得
echo ""
echo "2. Getting S3 bucket name from SSM..."
S3_BUCKET=$(aws ssm get-parameter --name "/bootstrap/pulumi/s3bucket-name" --query 'Parameter.Value' --output text)
if [ $? -eq 0 ]; then
    echo "   ✓ S3 bucket: $S3_BUCKET"
else
    echo "   ✗ Failed to retrieve S3 bucket name"
    exit 1
fi

# jenkins-agentディレクトリに移動
echo ""
echo "3. Changing to jenkins-agent directory..."
cd /home/ec2-user/infrastructure-as-code/pulumi/jenkins-agent
if [ $? -eq 0 ]; then
    echo "   ✓ Current directory: $(pwd)"
else
    echo "   ✗ Failed to change directory"
    exit 1
fi

# Pulumi.yamlの内容を確認
echo ""
echo "4. Checking Pulumi.yaml content..."
echo "   Content:"
cat Pulumi.yaml | sed 's/^/   /'

# S3バックエンドにログイン
echo ""
echo "5. Logging in to S3 backend..."
pulumi login s3://${S3_BUCKET}
if [ $? -eq 0 ]; then
    echo "   ✓ Logged in to S3 backend"
else
    echo "   ✗ Failed to login to S3 backend"
    exit 1
fi

# 現在のバックエンドを確認
echo ""
echo "6. Checking current backend..."
pulumi whoami
echo ""

# スタック一覧を確認
echo "7. Listing all stacks..."
pulumi stack ls
echo ""

# S3バケット内のスタックファイルを直接確認
echo "8. Checking S3 bucket contents..."
echo "   Looking for jenkins-agent stacks in S3..."
aws s3 ls s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/ 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✓ Found jenkins-agent stacks in S3"
else
    echo "   ✗ No jenkins-agent stacks found in S3"
fi

# 現在選択されているスタックを確認
echo ""
echo "9. Checking currently selected stack..."
pulumi stack --show-name 2>/dev/null
if [ $? -ne 0 ]; then
    echo "   No stack currently selected"
    
    # スタックを選択してみる
    echo ""
    echo "10. Attempting to select 'dev' stack..."
    pulumi stack select dev
    if [ $? -eq 0 ]; then
        echo "   ✓ Successfully selected 'dev' stack"
    else
        echo "   ✗ Failed to select 'dev' stack"
        
        # スタックを作成してみる
        echo ""
        echo "11. Attempting to create 'dev' stack..."
        pulumi stack init dev --secrets-provider=passphrase
        if [ $? -eq 0 ]; then
            echo "   ✓ Successfully created 'dev' stack"
        else
            echo "   ✗ Failed to create 'dev' stack"
        fi
    fi
fi

# 最終的なスタック状態を確認
echo ""
echo "12. Final stack status:"
pulumi stack --show-name
echo ""
pulumi stack ls

echo ""
echo "=========================================="
echo "Debug script completed"
echo "=========================================="