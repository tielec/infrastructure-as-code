#!/bin/bash

# IAMロール名の取得
ROLE_NAME=$(curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/)
echo "Role name: $ROLE_NAME"

# 認証情報の取得
CREDENTIALS=$(curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/$ROLE_NAME)
export AWS_ACCESS_KEY_ID=$(echo $CREDENTIALS | jq -r .AccessKeyId)
export AWS_SECRET_ACCESS_KEY=$(echo $CREDENTIALS | jq -r .SecretAccessKey)
export AWS_SESSION_TOKEN=$(echo $CREDENTIALS | jq -r .Token)

# 認証情報の確認
aws sts get-caller-identity

echo "AWS認証情報が環境変数に設定されました。以下のコマンドでPulumiを実行できます："
echo "pulumi preview"
echo "pulumi up"
