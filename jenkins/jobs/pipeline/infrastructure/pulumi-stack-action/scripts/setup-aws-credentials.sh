#!/bin/bash
set -euo pipefail

# =====================================================
# AWS認証情報セットアップスクリプト
# =====================================================
# 説明: IAMロール使用時にIMDSv2から認証情報を取得して環境変数に設定
# 使用方法: source setup-aws-credentials.sh
# =====================================================

# 既存の認証情報をチェック
if [ -n "${AWS_ACCESS_KEY_ID:-}" ] && [ "${AWS_ACCESS_KEY_ID}" != "" ]; then
    echo "明示的に指定された認証情報を使用"
    exit 0
fi

echo "EC2インスタンスのIAMロールから認証情報を取得中..."

# 空の認証情報環境変数をクリア
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN 2>/dev/null || true

# IMDSv2のトークンを取得
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "警告: IMDSv2トークンの取得に失敗しました"
    exit 1
fi

echo "IMDSv2トークンを取得しました"

# IAMロール名を取得
ROLE_NAME=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
    http://169.254.169.254/latest/meta-data/iam/security-credentials/ 2>/dev/null)

if [ -z "$ROLE_NAME" ]; then
    echo "警告: IAMロールが見つかりません"
    exit 1
fi

echo "IAMロール: $ROLE_NAME"

# 認証情報を取得
CREDS=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
    http://169.254.169.254/latest/meta-data/iam/security-credentials/$ROLE_NAME 2>/dev/null)

if [ -z "$CREDS" ]; then
    echo "警告: 認証情報の取得に失敗しました"
    exit 1
fi

# 環境変数にエクスポート
export AWS_ACCESS_KEY_ID=$(echo $CREDS | jq -r '.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(echo $CREDS | jq -r '.SecretAccessKey')
export AWS_SESSION_TOKEN=$(echo $CREDS | jq -r '.Token')

echo "EC2インスタンスの認証情報を環境変数に設定しました"

# 認証確認
echo "=== AWS認証情報の確認 ==="
aws sts get-caller-identity || {
    echo "AWS CLI認証失敗"
    exit 1
}
echo "========================="