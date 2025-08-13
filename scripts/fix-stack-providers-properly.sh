#!/bin/bash

# S3バックエンドのスタックファイルを正しく修正

set -e

echo "=========================================="
echo "Fix Stack Providers Properly"
echo "=========================================="

# 環境変数の設定
export AWS_REGION="ap-northeast-1"
export AWS_DEFAULT_REGION="ap-northeast-1"

# S3バケット名を取得
S3_BUCKET=$(aws ssm get-parameter --name "/bootstrap/pulumi/s3bucket-name" --query 'Parameter.Value' --output text)
echo "S3 bucket: $S3_BUCKET"

# スタックファイルをダウンロード
echo "Downloading current stack file..."
TEMP_FILE="/tmp/jenkins-agent-dev-current.json"
aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/dev.json $TEMP_FILE

# 現在のファイル構造を確認
echo ""
echo "Current file structure:"
python3 << EOF
import json
with open("$TEMP_FILE", "r") as f:
    data = json.load(f)
    print(f"  - Has checkpoint: {'checkpoint' in data}")
    print(f"  - Has deployment: {'deployment' in data}")
    if 'deployment' in data:
        print(f"  - Has secrets_providers: {'secrets_providers' in data['deployment']}")
        print(f"  - Has resources: {'resources' in data['deployment']}")
        if 'resources' in data['deployment']:
            print(f"  - Number of resources: {len(data['deployment']['resources'])}")
EOF

# バックアップファイルから元のリソース情報を復元する必要があるか確認
echo ""
echo "Checking for backup files with resources..."
LATEST_BACKUP=$(aws s3 ls s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/ | grep "dev.json.bak" | sort | tail -1 | awk '{print $4}')

if [ -n "$LATEST_BACKUP" ]; then
    echo "Found backup file: $LATEST_BACKUP"
    BACKUP_FILE="/tmp/jenkins-agent-backup.json"
    aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/$LATEST_BACKUP $BACKUP_FILE
    
    # バックアップファイルの構造を確認
    echo "Backup file structure:"
    python3 << EOF
import json
with open("$BACKUP_FILE", "r") as f:
    data = json.load(f)
    if 'deployment' in data:
        if 'resources' in data['deployment']:
            print(f"  - Number of resources in backup: {len(data['deployment']['resources'])}")
EOF
else
    echo "No backup file found"
    BACKUP_FILE=""
fi

# Pythonスクリプトで修正
echo ""
echo "Fixing stack file..."
python3 << EOF
import json
import sys

# 現在のファイルを読み込み
with open("$TEMP_FILE", "r") as f:
    data = json.load(f)

# バックアップファイルがあれば読み込み
backup_data = None
if "$BACKUP_FILE":
    with open("$BACKUP_FILE", "r") as f:
        backup_data = json.load(f)

# deploymentセクションが存在しない場合は作成
if "deployment" not in data:
    print("Creating deployment section...")
    data["deployment"] = {}

# resourcesがない場合、バックアップから復元
if "resources" not in data["deployment"] or len(data["deployment"]["resources"]) == 0:
    if backup_data and "deployment" in backup_data and "resources" in backup_data["deployment"]:
        print(f"Restoring {len(backup_data['deployment']['resources'])} resources from backup...")
        data["deployment"]["resources"] = backup_data["deployment"]["resources"]
    else:
        print("No resources to restore, keeping empty resources array")
        data["deployment"]["resources"] = []

# secrets_providersを正しく設定
print("Setting secrets_providers to passphrase type...")
data["deployment"]["secrets_providers"] = {
    "type": "passphrase"
}

# manifestも確認・設定
if "manifest" not in data["deployment"]:
    data["deployment"]["manifest"] = {
        "time": "2025-08-09T13:28:15.182433999Z",
        "magic": "6dfe99f30e904acf4c9f8dfdbc83d19cafc6867fd0bb464d943c0787f94d2658",
        "version": "v3.184.0"
    }

# checkpointセクションを確認
if "checkpoint" not in data:
    data["checkpoint"] = {}

# checkpoint.Stackを修正（単純なスタック名のみ）
data["checkpoint"]["Stack"] = "dev"
print(f"Set checkpoint.Stack to: {data['checkpoint']['Stack']}")

# ファイルを保存
with open("$TEMP_FILE", "w") as f:
    json.dump(data, f, indent=4)

print("\nFile has been fixed!")
print(f"  - Resources: {len(data['deployment'].get('resources', []))} items")
print(f"  - Secrets provider: {data['deployment']['secrets_providers']['type']}")
print(f"  - Checkpoint stack: {data['checkpoint']['Stack']}")
EOF

# 修正したファイルをS3にアップロード
echo ""
echo "Uploading fixed file to S3..."
aws s3 cp $TEMP_FILE s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/dev.json

# 一時ファイルを削除
rm -f $TEMP_FILE
[ -n "$BACKUP_FILE" ] && rm -f $BACKUP_FILE

echo ""
echo "=========================================="
echo "Verification"
echo "=========================================="

echo "Checking fixed file in S3:"
aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/dev.json - 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"  - checkpoint.Stack: {data.get('checkpoint', {}).get('Stack', 'not found')}\")
print(f\"  - secrets_providers.type: {data.get('deployment', {}).get('secrets_providers', {}).get('type', 'not found')}\")
print(f\"  - Number of resources: {len(data.get('deployment', {}).get('resources', []))}\")
"

echo ""
echo "Fix completed!"