#!/bin/bash

# Pulumiのワークスペース設定を確認

echo "=========================================="
echo "Checking Pulumi Workspace Configuration"
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

# .pulumiディレクトリの存在確認
echo ""
echo "1. Checking local .pulumi directory..."
if [ -d ".pulumi" ]; then
    echo "   Found .pulumi directory"
    echo "   Contents:"
    ls -la .pulumi/
    
    # ワークスペース設定ファイルを確認
    if [ -f ".pulumi/workspaces/jenkins-agent-dev-workspace.json" ]; then
        echo ""
        echo "   Workspace file content:"
        cat .pulumi/workspaces/jenkins-agent-dev-workspace.json | python -m json.tool
    fi
else
    echo "   No .pulumi directory found"
fi

# Pulumi.yamlの内容を再確認
echo ""
echo "2. Pulumi.yaml content:"
cat Pulumi.yaml

# 現在のPulumiのバージョン
echo ""
echo "3. Pulumi version:"
pulumi version

# S3バックエンドにログイン
echo ""
echo "4. Logging in to S3 backend..."
pulumi login s3://${S3_BUCKET}

# 現在のスタック設定を詳細に確認
echo ""
echo "5. Current stack configuration:"
pulumi stack select dev 2>&1

echo ""
echo "6. Stack export (first 20 lines):"
pulumi stack export 2>&1 | head -20

# Pulumiの内部状態を確認
echo ""
echo "7. Pulumi workspace info:"
pulumi about

# 環境変数を確認
echo ""
echo "8. Relevant environment variables:"
env | grep -E "PULUMI|AWS" | grep -v PASSPHRASE | sort

echo ""
echo "=========================================="
echo "Workspace check completed"
echo "=========================================="