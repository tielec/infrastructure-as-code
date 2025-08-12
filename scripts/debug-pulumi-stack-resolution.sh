#!/bin/bash

# Pulumiのスタック解決をデバッグ

echo "=========================================="
echo "Debug Pulumi Stack Resolution"
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

# S3バックエンドにログイン
echo ""
echo "1. Logging in to S3 backend..."
pulumi login s3://${S3_BUCKET}

# デバッグ情報を有効にしてスタック操作を実行
echo ""
echo "2. Running pulumi stack select with debug output..."
PULUMI_DEBUG_COMMANDS=1 pulumi stack select dev 2>&1

echo ""
echo "3. Checking what Pulumi thinks the current stack is..."
pulumi stack --show-name

echo ""
echo "4. Checking stack with verbose output..."
pulumi stack -v 9 2>&1 | head -30

echo ""
echo "5. Trying to list stacks with JSON output..."
pulumi stack ls --json 2>&1

echo ""
echo "6. Checking S3 backend state files directly..."
echo "   Files in .pulumi/stacks/jenkins-agent/:"
aws s3 ls s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/

echo ""
echo "7. Checking the content of dev.json (Stack field)..."
aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/dev.json - 2>/dev/null | python3 -c "
import json
import sys
data = json.load(sys.stdin)
if 'checkpoint' in data and 'Stack' in data['checkpoint']:
    print(f\"   checkpoint.Stack: {data['checkpoint']['Stack']}\")
if 'deployment' in data:
    if 'secrets_providers' in data['deployment']:
        print(f\"   secrets_providers.type: {data['deployment']['secrets_providers'].get('type', 'not set')}\")
        if 'state' in data['deployment']['secrets_providers']:
            state = data['deployment']['secrets_providers']['state']
            print(f\"   secrets_providers.state: {state}\")
"

echo ""
echo "8. Trying preview with explicit stack specification..."
pulumi preview -s dev 2>&1 | head -20

echo ""
echo "=========================================="
echo "Debug completed"
echo "=========================================="