#!/bin/bash

# S3バックエンドのスタックメタデータを修正するスクリプト

set -e

echo "=========================================="
echo "Fix S3 Stack Metadata Script"
echo "=========================================="

# 環境変数の設定
export AWS_REGION="ap-northeast-1"
export AWS_DEFAULT_REGION="ap-northeast-1"

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

# 各プロジェクトのスタックファイルを修正
for PROJECT in "${PROJECTS[@]}"; do
    echo ""
    echo "Processing project: $PROJECT"
    
    # devスタックファイルが存在するか確認
    if aws s3 ls s3://${S3_BUCKET}/.pulumi/stacks/${PROJECT}/dev.json > /dev/null 2>&1; then
        echo "  Found dev.json for $PROJECT"
        
        # ファイルをダウンロード
        TEMP_FILE="/tmp/${PROJECT}-dev.json"
        aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/${PROJECT}/dev.json $TEMP_FILE
        
        # バックアップを作成
        aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/${PROJECT}/dev.json \
                  s3://${S3_BUCKET}/.pulumi/stacks/${PROJECT}/dev.json.bak-$(date +%Y%m%d-%H%M%S)
        
        # organizationを含む形式を修正
        # "organization/PROJECT/dev" -> "dev"
        # "tielec/PROJECT/dev" -> "dev"
        sed -i 's/"Stack": *"[^\/]*\/[^\/]*\/\([^"]*\)"/"Stack": "\1"/g' $TEMP_FILE
        
        # 修正内容を確認
        echo "  Modified Stack references:"
        grep '"Stack"' $TEMP_FILE | head -3
        
        # 修正したファイルをS3にアップロード
        aws s3 cp $TEMP_FILE s3://${S3_BUCKET}/.pulumi/stacks/${PROJECT}/dev.json
        
        # 一時ファイルを削除
        rm -f $TEMP_FILE
        
        echo "  ✓ Fixed $PROJECT/dev.json"
    else
        echo "  No dev.json found for $PROJECT (skipping)"
    fi
done

echo ""
echo "=========================================="
echo "Stack metadata fix completed"
echo "=========================================="
echo ""
echo "Now testing jenkins-agent..."

# jenkins-agentで動作確認
cd /home/ec2-user/infrastructure-as-code/pulumi/jenkins-agent

# パスフレーズを設定
export PULUMI_CONFIG_PASSPHRASE=$(aws ssm get-parameter --name "/bootstrap/pulumi/config-passphrase" --with-decryption --query 'Parameter.Value' --output text)

# S3バックエンドにログイン
pulumi login s3://${S3_BUCKET}

# スタックを選択
pulumi stack select dev

# 現在のスタックを確認
echo "Current stack:"
pulumi stack --show-name

# スタック一覧
echo ""
echo "Stack list:"
pulumi stack ls

echo ""
echo "Fix completed successfully!"