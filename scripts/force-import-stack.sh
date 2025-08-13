#!/bin/bash

# 既存のスタックファイルを強制的に再インポート

set -e

echo "=========================================="
echo "Force Import Existing Stack"
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
echo "1. Exporting current state from S3..."
# 現在のS3にあるスタックファイルをエクスポート形式で保存
EXPORT_FILE="/tmp/jenkins-agent-export.json"
aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/dev.json $EXPORT_FILE

echo ""
echo "2. Backing up and removing old stack from S3..."
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
aws s3 mv s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/dev.json \
          s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/dev.json.old-${TIMESTAMP}

echo ""
echo "3. Clearing all local state..."
rm -rf .pulumi
rm -rf ~/.pulumi/workspaces/jenkins-agent*
rm -f Pulumi.*.yaml

echo ""
echo "4. Logging in to S3 backend..."
pulumi login s3://${S3_BUCKET}

echo ""
echo "5. Creating new stack with correct format..."
pulumi stack init dev --secrets-provider=passphrase

echo ""
echo "6. Importing the state..."
pulumi stack import --file $EXPORT_FILE

echo ""
echo "7. Setting configuration values..."
pulumi config set aws:region ${AWS_REGION}
pulumi config set jenkins-agent:projectName jenkins-infra
pulumi config set jenkins-agent:networkStackName jenkins-network
pulumi config set jenkins-agent:securityStackName jenkins-security
pulumi config set jenkins-agent:instanceType t4g.medium
pulumi config set jenkins-agent:minTargetCapacity 0
pulumi config set jenkins-agent:maxTargetCapacity 5
pulumi config set jenkins-agent:spotPrice 0.05

echo ""
echo "8. Verifying import..."
pulumi stack --show-name
pulumi stack ls

echo ""
echo "9. Building TypeScript..."
npm install
npm run build

echo ""
echo "10. Running preview to verify..."
pulumi preview --diff 2>&1 | head -50

echo ""
echo "=========================================="
echo "Import completed!"
echo "=========================================="
echo ""
echo "If the preview shows 'No changes', the import was successful."
echo "If there are changes, review them carefully before running 'pulumi up'."