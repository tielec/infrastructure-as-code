#!/bin/bash

# S3バックエンドのスタックファイルを完全に修正

set -e

echo "=========================================="
echo "Complete Stack Fix for S3 Backend"
echo "=========================================="

# 環境変数の設定
export AWS_REGION="ap-northeast-1"
export AWS_DEFAULT_REGION="ap-northeast-1"

# S3バケット名を取得
S3_BUCKET=$(aws ssm get-parameter --name "/bootstrap/pulumi/s3bucket-name" --query 'Parameter.Value' --output text)
echo "S3 bucket: $S3_BUCKET"

# 修正対象のプロジェクト
PROJECT="jenkins-agent"
STACK="dev"

echo ""
echo "Fixing $PROJECT/$STACK stack file..."

# 現在のスタックファイルをダウンロード
TEMP_FILE="/tmp/${PROJECT}-${STACK}.json"
aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/${PROJECT}/${STACK}.json $TEMP_FILE

# バックアップを作成
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/${PROJECT}/${STACK}.json \
          s3://${S3_BUCKET}/.pulumi/stacks/${PROJECT}/${STACK}.json.fix-backup-${TIMESTAMP}

# Pythonスクリプトで修正
python3 << 'EOF'
import json
import sys

# ファイルを読み込み
with open("/tmp/jenkins-agent-dev.json", "r") as f:
    data = json.load(f)

# checkpoint.Stackを修正
# S3バックエンドでは、単純にスタック名のみにする必要がある
if "checkpoint" in data:
    if "Stack" in data["checkpoint"]:
        print(f"Original checkpoint.Stack: {data['checkpoint']['Stack']}")
        # "organization/project/stack" または "project/stack" から "stack" のみに修正
        stack_parts = data["checkpoint"]["Stack"].split("/")
        data["checkpoint"]["Stack"] = stack_parts[-1]  # 最後の部分（スタック名）のみ
        print(f"Fixed checkpoint.Stack: {data['checkpoint']['Stack']}")

# deployment.secrets_providersを修正
if "deployment" in data:
    if "secrets_providers" in data["deployment"]:
        print(f"Original secrets_providers: {data['deployment']['secrets_providers']}")
        # passphraseタイプに変更
        data["deployment"]["secrets_providers"] = {
            "type": "passphrase"
        }
        print(f"Fixed secrets_providers: {data['deployment']['secrets_providers']}")
    
    # もしresourcesがある場合、URNも修正
    if "resources" in data["deployment"]:
        for resource in data["deployment"]["resources"]:
            if "urn" in resource:
                original_urn = resource["urn"]
                # URN形式: urn:pulumi:stack::project::type::name
                # organizationが含まれている場合は削除
                if "::jenkins-agent::" in original_urn:
                    # すでに正しい形式
                    pass
                else:
                    # URNを解析して修正
                    urn_parts = original_urn.split("::")
                    if len(urn_parts) >= 2:
                        # スタック部分を修正
                        stack_part = urn_parts[0].split(":")
                        if len(stack_part) >= 3:
                            # urn:pulumi:dev に修正
                            stack_part = ["urn", "pulumi", "dev"]
                            urn_parts[0] = ":".join(stack_part)
                            resource["urn"] = "::".join(urn_parts)

# ファイルを保存
with open("/tmp/jenkins-agent-dev.json", "w") as f:
    json.dump(data, f, indent=4)

print("\nFile has been fixed successfully!")
EOF

# 修正したファイルをS3にアップロード
echo ""
echo "Uploading fixed file to S3..."
aws s3 cp $TEMP_FILE s3://${S3_BUCKET}/.pulumi/stacks/${PROJECT}/${STACK}.json

# 一時ファイルを削除
rm -f $TEMP_FILE

echo ""
echo "=========================================="
echo "Testing the fix..."
echo "=========================================="

# jenkins-agentディレクトリに移動
cd /home/ec2-user/infrastructure-as-code/pulumi/jenkins-agent

# ローカルキャッシュをクリア
rm -rf .pulumi
rm -rf ~/.pulumi/workspaces/jenkins-agent-*

# パスフレーズを設定
export PULUMI_CONFIG_PASSPHRASE=$(aws ssm get-parameter --name "/bootstrap/pulumi/config-passphrase" --with-decryption --query 'Parameter.Value' --output text)

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
echo "Testing preview (first 30 lines)..."
pulumi preview --non-interactive 2>&1 | head -30

echo ""
echo "=========================================="
echo "Fix completed!"
echo "=========================================="