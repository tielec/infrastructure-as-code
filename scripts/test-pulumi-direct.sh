#!/bin/bash

# Ansibleと同じ環境変数とコマンドを再現してテスト

echo "Testing Pulumi commands directly..."

# 環境変数の設定（Ansibleと同じ）
export PULUMI_CONFIG_PASSPHRASE=$(aws ssm get-parameter --name "/bootstrap/pulumi/config-passphrase" --with-decryption --query 'Parameter.Value' --output text)
export AWS_REGION="ap-northeast-1"
export AWS_DEFAULT_REGION="ap-northeast-1"

# jenkins-agentディレクトリに移動
cd /home/ec2-user/infrastructure-as-code/pulumi/jenkins-agent

# AWS環境スクリプトをソース
source /home/ec2-user/infrastructure-as-code/scripts/aws/aws-env.sh > /dev/null
eval $(/home/ec2-user/infrastructure-as-code/scripts/aws/aws-env.sh) > /dev/null

# S3バックエンドにログイン
S3_BUCKET=$(aws ssm get-parameter --name "/bootstrap/pulumi/s3bucket-name" --query 'Parameter.Value' --output text)
echo "Logging in to S3 backend: s3://${S3_BUCKET}"
/usr/local/bin/pulumi login s3://${S3_BUCKET}

# スタックを選択
echo ""
echo "Selecting stack 'dev'..."
/usr/local/bin/pulumi stack select dev

# 現在のスタックを確認
echo ""
echo "Current stack:"
/usr/local/bin/pulumi stack --show-name

# プレビューを実行（Ansibleと同じコマンド）
echo ""
echo "Running preview..."
/usr/local/bin/pulumi preview

echo ""
echo "Test completed."