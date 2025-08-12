#!/bin/bash

# S3バックエンドのスタックファイルのsecrets_providerを修正

set -e

echo "=========================================="
echo "Fix Stack Secrets Provider"
echo "=========================================="

# 環境変数の設定
export AWS_REGION="ap-northeast-1"
export AWS_DEFAULT_REGION="ap-northeast-1"
export PULUMI_CONFIG_PASSPHRASE=$(aws ssm get-parameter --name "/bootstrap/pulumi/config-passphrase" --with-decryption --query 'Parameter.Value' --output text)

# S3バケット名を取得
S3_BUCKET=$(aws ssm get-parameter --name "/bootstrap/pulumi/s3bucket-name" --query 'Parameter.Value' --output text)
echo "S3 bucket: $S3_BUCKET"

# 修正するプロジェクトのリスト
PROJECTS=(
    "jenkins-agent"
    "jenkins-network"
    "jenkins-security"
    "jenkins-nat"
    "jenkins-storage"
    "jenkins-loadbalancer"
    "jenkins-controller"
    "jenkins-config"
    "jenkins-application"
    "lambda-network"
    "lambda-security"
    "lambda-vpce"
    "lambda-nat"
    "lambda-functions"
    "lambda-api-gateway"
    "lambda-waf"
    "lambda-websocket"
    "lambda-account-setup"
)

echo ""
echo "Fixing secrets_providers in all stack files..."

for PROJECT in "${PROJECTS[@]}"; do
    echo ""
    echo "Processing: $PROJECT"
    
    # devスタックファイルが存在するか確認
    if aws s3 ls s3://${S3_BUCKET}/.pulumi/stacks/${PROJECT}/dev.json > /dev/null 2>&1; then
        # ファイルをダウンロード
        TEMP_FILE="/tmp/${PROJECT}-dev.json"
        aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/${PROJECT}/dev.json $TEMP_FILE --quiet
        
        # secrets_providersセクションを修正
        # Pythonを使用してJSONを適切に処理
        python3 << EOF
import json
import sys

with open("$TEMP_FILE", "r") as f:
    data = json.load(f)

# checkpoint内のStackを修正（もし存在すれば）
if "checkpoint" in data and "Stack" in data["checkpoint"]:
    # organization/project/stack -> project/stack -> stack
    stack_parts = data["checkpoint"]["Stack"].split("/")
    if len(stack_parts) >= 2:
        data["checkpoint"]["Stack"] = stack_parts[-1]  # 最後の部分（スタック名）のみ使用

# deployment.secrets_providersを修正
if "deployment" in data and "secrets_providers" in data["deployment"]:
    data["deployment"]["secrets_providers"] = {
        "type": "passphrase"
    }

# ファイルを保存
with open("$TEMP_FILE", "w") as f:
    json.dump(data, f, indent=4)

print("  ✓ Fixed secrets_providers and stack name")
EOF
        
        # 修正したファイルをS3にアップロード
        aws s3 cp $TEMP_FILE s3://${S3_BUCKET}/.pulumi/stacks/${PROJECT}/dev.json --quiet
        
        # 一時ファイルを削除
        rm -f $TEMP_FILE
        
        echo "  ✓ Updated $PROJECT/dev.json"
    else
        echo "  - No dev.json found for $PROJECT (skipping)"
    fi
done

echo ""
echo "=========================================="
echo "Testing jenkins-agent..."
echo "=========================================="

# jenkins-agentディレクトリに移動
cd /home/ec2-user/infrastructure-as-code/pulumi/jenkins-agent

# ローカルキャッシュをクリア
rm -rf .pulumi

# S3バックエンドにログイン
echo "Logging in to S3 backend..."
pulumi login s3://${S3_BUCKET}

# スタックを選択
echo ""
echo "Selecting dev stack..."
pulumi stack select dev

# 現在のスタックを確認
echo ""
echo "Current stack:"
pulumi stack --show-name

# スタック一覧
echo ""
echo "Stack list:"
pulumi stack ls

# プレビューをテスト
echo ""
echo "Testing preview..."
pulumi preview --non-interactive 2>&1 | head -20

echo ""
echo "=========================================="
echo "Fix completed!"
echo "=========================================="