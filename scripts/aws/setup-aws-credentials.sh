#!/bin/bash
# 共通AWS認証情報セットアップスクリプト

# ---------- 認証情報設定 ----------
DEBUG="${AWS_ENV_DEBUG:-false}"

log() {
    if [ "$DEBUG" = "true" ]; then
        echo "$@" >&2
    fi
}

log "# AWS認証情報の環境変数を確認します"
if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
    log "# 既に環境変数にAWS認証情報が設定されています"
else
    # EC2メタデータサービスから取得を試みる
    TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null)
    ROLE_NAME=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/ 2>/dev/null)

    if [ -n "$ROLE_NAME" ]; then
        log "# EC2インスタンスから認証情報を取得中..."
        CREDENTIALS=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/$ROLE_NAME)
        export AWS_ACCESS_KEY_ID=$(echo $CREDENTIALS | jq -r '.AccessKeyId')
        export AWS_SECRET_ACCESS_KEY=$(echo $CREDENTIALS | jq -r '.SecretAccessKey')
        export AWS_SESSION_TOKEN=$(echo $CREDENTIALS | jq -r '.Token')
        export AWS_REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)
    else
        log "# ~/.aws/credentials から認証情報を取得中..."
        export AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
        export AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)
        AWS_SESSION_TOKEN=$(aws configure get aws_session_token 2>/dev/null || echo "")
        [ -n "$AWS_SESSION_TOKEN" ] && export AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN"
        export AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-west-2")
    fi
fi

# 認証情報が正しく設定されたか確認
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "エラー: AWS認証情報を取得できませんでした" >&2
    exit 1
fi

log "# AWS認証情報の設定が完了しました"

# ---------- 拡張チェック ----------
echo "===== AWS 認証情報の確認 ====="
echo "Access Key: ${AWS_ACCESS_KEY_ID:0:4}********"
echo "Secret Key: ${AWS_SECRET_ACCESS_KEY:0:4}********"
[ -n "$AWS_SESSION_TOKEN" ] && echo "Session Token: 設定済み" || echo "Session Token: 未設定"
echo "Region: ${AWS_REGION:-未設定}"
echo

echo "===== STS GetCallerIdentity ====="
aws sts get-caller-identity

echo "===== 使用中のプロファイル ====="
echo "AWS_PROFILE: ${AWS_PROFILE:-default}"
echo

echo "===== IAM Role（EC2のみ） ====="
if curl -s --connect-timeout 1 http://169.254.169.254/latest/meta-data/iam/security-credentials/ > /dev/null; then
    ROLE_NAME=$(curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/)
    echo "IAM Role Name: $ROLE_NAME"
else
    echo "IAM Role: 不明（ローカル環境など）"
fi
