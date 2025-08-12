#!/bin/bash

# Pulumiのワークスペースをリセット

echo "=========================================="
echo "Reset Pulumi Workspace"
echo "=========================================="

# 環境変数の設定
export AWS_REGION="ap-northeast-1"
export AWS_DEFAULT_REGION="ap-northeast-1"
export PULUMI_CONFIG_PASSPHRASE=$(aws ssm get-parameter --name "/bootstrap/pulumi/config-passphrase" --with-decryption --query 'Parameter.Value' --output text)

# S3バケット名を取得
S3_BUCKET=$(aws ssm get-parameter --name "/bootstrap/pulumi/s3bucket-name" --query 'Parameter.Value' --output text)
echo "S3 bucket: $S3_BUCKET"

# jenkins-agentディレクトリに移動
cd /home/ec2-user/infrastructure-as-code/pulumi/jenkins-agent
echo "Current directory: $(pwd)"

# ローカルの.pulumiディレクトリを削除
echo ""
echo "1. Removing local .pulumi directory if exists..."
if [ -d ".pulumi" ]; then
    rm -rf .pulumi
    echo "   ✓ Removed .pulumi directory"
else
    echo "   No .pulumi directory to remove"
fi

# グローバルのPulumiキャッシュをクリア
echo ""
echo "2. Clearing global Pulumi cache..."
if [ -d "$HOME/.pulumi" ]; then
    echo "   Found global .pulumi directory"
    # workspacesディレクトリのみクリア（credentialsは保持）
    if [ -d "$HOME/.pulumi/workspaces" ]; then
        rm -rf $HOME/.pulumi/workspaces
        echo "   ✓ Cleared workspaces cache"
    fi
fi

# S3バックエンドにログイン
echo ""
echo "3. Logging in to S3 backend..."
pulumi login s3://${S3_BUCKET}

# スタックをリストアップ
echo ""
echo "4. Available stacks:"
pulumi stack ls

# devスタックを明示的に選択
echo ""
echo "5. Selecting dev stack..."
pulumi stack select dev

# 現在のスタックを確認
echo ""
echo "6. Current stack:"
pulumi stack --show-name

# スタックの設定を確認
echo ""
echo "7. Stack configuration:"
pulumi config

# テストプレビュー
echo ""
echo "8. Testing preview..."
pulumi preview --non-interactive 2>&1 | head -20

echo ""
echo "=========================================="
echo "Workspace reset completed"
echo "=========================================="