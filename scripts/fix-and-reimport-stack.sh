#!/bin/bash

# スタックファイルを修正してから再インポート

set -e

echo "=========================================="
echo "Fix and Reimport Stack"
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
echo "1. Getting the backup file..."
# 先ほどバックアップしたファイルを取得
LATEST_BACKUP=$(aws s3 ls s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/ | grep "dev.json.old" | sort | tail -1 | awk '{print $4}')
echo "   Using backup: $LATEST_BACKUP"

EXPORT_FILE="/tmp/jenkins-agent-export-fixed.json"
aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/$LATEST_BACKUP $EXPORT_FILE

echo ""
echo "2. Fixing the export file for proper import format..."
python3 << 'EOF'
import json

# ファイルを読み込み
with open("/tmp/jenkins-agent-export-fixed.json", "r") as f:
    data = json.load(f)

# Pulumi importが期待する形式に変換
# deploymentセクションのみを残す（checkpointは不要）
if "deployment" in data:
    # secrets_providersを削除（importコマンドが自動的に設定する）
    if "secrets_providers" in data["deployment"]:
        del data["deployment"]["secrets_providers"]
    
    # 新しい形式のエクスポートファイルを作成
    export_data = {
        "version": data.get("version", 3),
        "deployment": data["deployment"]
    }
else:
    # もし既にdeploymentがトップレベルの場合
    export_data = data

# ファイルを保存
with open("/tmp/jenkins-agent-export-fixed.json", "w") as f:
    json.dump(export_data, f, indent=4)

print("✓ Export file has been fixed for import")
EOF

echo ""
echo "3. Clearing the failed stack..."
# 失敗したスタックを削除
pulumi stack rm dev --yes 2>/dev/null || true

echo ""
echo "4. Creating a fresh stack..."
pulumi stack init dev --secrets-provider=passphrase

echo ""
echo "5. Setting basic configuration first..."
pulumi config set aws:region ${AWS_REGION}

echo ""
echo "6. Importing the fixed state..."
pulumi stack import --file $EXPORT_FILE --force

echo ""
echo "7. Setting remaining configuration..."
pulumi config set jenkins-agent:projectName jenkins-infra
pulumi config set jenkins-agent:networkStackName jenkins-network
pulumi config set jenkins-agent:securityStackName jenkins-security
pulumi config set jenkins-agent:instanceType t4g.medium
pulumi config set jenkins-agent:minTargetCapacity 0
pulumi config set jenkins-agent:maxTargetCapacity 5
pulumi config set jenkins-agent:spotPrice 0.05

echo ""
echo "8. Verifying the import..."
echo "   Current stack: $(pulumi stack --show-name)"
pulumi stack ls

echo ""
echo "9. Building TypeScript..."
npm install
npm run build

echo ""
echo "10. Running refresh to sync state..."
pulumi refresh --yes

echo ""
echo "11. Running preview..."
pulumi preview --diff 2>&1 | head -50

echo ""
echo "=========================================="
echo "Import process completed!"
echo "=========================================="