#!/bin/bash

# すべてのPulumi問題を修正

set -e

echo "=========================================="
echo "Fix All Pulumi Issues"
echo "=========================================="

# 環境変数の設定
export AWS_REGION="ap-northeast-1"
export AWS_DEFAULT_REGION="ap-northeast-1"
export PULUMI_CONFIG_PASSPHRASE=$(aws ssm get-parameter --name "/bootstrap/pulumi/config-passphrase" --with-decryption --query 'Parameter.Value' --output text)

# S3バケット名を取得
S3_BUCKET=$(aws ssm get-parameter --name "/bootstrap/pulumi/s3bucket-name" --query 'Parameter.Value' --output text)
echo "S3 bucket: $S3_BUCKET"

cd /home/ec2-user/infrastructure-as-code/pulumi/jenkins-agent

echo ""
echo "1. Removing Pulumi.dev.yaml file..."
if [ -f "Pulumi.dev.yaml" ]; then
    sudo rm -f Pulumi.dev.yaml
    echo "   ✓ Removed Pulumi.dev.yaml"
else
    echo "   No Pulumi.dev.yaml to remove"
fi

echo ""
echo "2. Clearing all local caches..."
rm -rf .pulumi
rm -rf ~/.pulumi/workspaces/jenkins-agent-*
echo "   ✓ Cleared local caches"

echo ""
echo "3. Downloading current stack file from S3..."
TEMP_FILE="/tmp/jenkins-agent-dev.json"
aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/dev.json $TEMP_FILE

echo ""
echo "4. Completely fixing the stack file..."
python3 << 'EOF'
import json

# ファイルを読み込み
with open("/tmp/jenkins-agent-dev.json", "r") as f:
    data = json.load(f)

print("Current secrets_providers:", data.get('deployment', {}).get('secrets_providers', {}))

# deploymentセクションを確認・作成
if "deployment" not in data:
    data["deployment"] = {}

# secrets_providersを完全に置き換え
data["deployment"]["secrets_providers"] = {
    "type": "passphrase"
}
print("Fixed secrets_providers:", data["deployment"]["secrets_providers"])

# checkpointセクションを確認・修正
if "checkpoint" not in data:
    data["checkpoint"] = {}

# Stackフィールドを単純な名前に修正
data["checkpoint"]["Stack"] = "dev"
print("Fixed checkpoint.Stack:", data["checkpoint"]["Stack"])

# バージョン情報を確認
if "version" not in data:
    data["version"] = 3

# ファイルを保存
with open("/tmp/jenkins-agent-dev.json", "w") as f:
    json.dump(data, f, indent=4)

print("\n✓ File has been completely fixed!")
EOF

echo ""
echo "5. Creating backup and uploading fixed file..."
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/dev.json \
          s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/dev.json.complete-fix-backup-${TIMESTAMP}
aws s3 cp $TEMP_FILE s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/dev.json
echo "   ✓ Uploaded fixed file"

echo ""
echo "6. Verifying the fix..."
aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/dev.json - 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
sp = data.get('deployment', {}).get('secrets_providers', {})
cs = data.get('checkpoint', {}).get('Stack', 'not found')
print(f'   - secrets_providers.type: {sp.get(\"type\", \"not found\")}')
print(f'   - checkpoint.Stack: {cs}')
if sp.get('type') == 'passphrase' and cs == 'dev':
    print('   ✓ Verification passed!')
else:
    print('   ✗ Verification failed!')
"

echo ""
echo "7. Testing with Pulumi..."
pulumi login s3://${S3_BUCKET}
pulumi stack select dev
echo "   Current stack: $(pulumi stack --show-name)"

echo ""
echo "8. Final test - running preview..."
pulumi preview 2>&1 | head -30

echo ""
echo "=========================================="
echo "Fix completed!"
echo "=========================================="

# クリーンアップ
rm -f $TEMP_FILE