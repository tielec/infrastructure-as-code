#!/bin/bash
# AWS認証情報の設定を確認し、必要に応じて環境変数を設定
# 標準出力には何も出力しない

# デバッグモード（環境変数で制御）
DEBUG="${AWS_ENV_DEBUG:-false}"

# ログ関数
log() {
    if [ "$DEBUG" = "true" ]; then
        echo "$@" >&2
    fi
}

# すでに環境変数が設定されているかチェック
if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
    log "# AWS認証情報は既に環境変数に設定されています"
    exit 0
fi

# IAMロール名の取得 (EC2メタデータサービスから)
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null)
ROLE_NAME=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/ 2>/dev/null)

if [ -n "$ROLE_NAME" ]; then
    # EC2インスタンスからIAMロール認証情報を取得
    log "# AWS認証情報をメタデータサービスから取得中..."
    CREDENTIALS=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/$ROLE_NAME)
    export AWS_ACCESS_KEY_ID=$(echo $CREDENTIALS | jq -r '.AccessKeyId')
    export AWS_SECRET_ACCESS_KEY=$(echo $CREDENTIALS | jq -r '.SecretAccessKey')
    export AWS_SESSION_TOKEN=$(echo $CREDENTIALS | jq -r '.Token')
    export AWS_REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)
    
    log "# AWS認証情報がメタデータサービスから正常に取得されました"
else
    # ~/.aws/credentialsから認証情報を取得
    log "# AWS認証情報をAWS CLIの設定から取得中..."
    export AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
    export AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)
    AWS_SESSION_TOKEN=$(aws configure get aws_session_token 2>/dev/null || echo "")
    [ -n "$AWS_SESSION_TOKEN" ] && export AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN"
    export AWS_REGION=$(aws configure get region 2>/dev/null || echo "ap-northeast-1")
    
    log "# AWS認証情報がAWS CLIの設定から取得されました"
fi

# 認証情報が正しく設定されたか確認
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "エラー: AWS認証情報を取得できませんでした" >&2
    exit 1
fi

log "# AWS認証情報の設定が完了しました"
