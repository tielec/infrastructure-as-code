#!/bin/bash
# AWS認証情報の設定を確認し、必要に応じて環境変数を設定
# eval用にexportコマンドのみを出力

# デバッグモード（環境変数で制御）
DEBUG="${AWS_ENV_DEBUG:-false}"

# ログ関数（必ずstderrに出力）
log() {
    if [ "$DEBUG" = "true" ]; then
        echo "$@" >&2
    fi
}

# エラー関数（必ずstderrに出力）
error() {
    echo "$@" >&2
}

# すでに環境変数が設定されているかチェック
if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
    log "AWS認証情報は既に環境変数に設定されています"
    # evalで実行される際に何も出力しない
    exit 0
fi

# IAMロール名の取得 (EC2メタデータサービスから)
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null)
ROLE_NAME=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/ 2>/dev/null)

if [ -n "$ROLE_NAME" ]; then
    # EC2インスタンスからIAMロール認証情報を取得
    log "AWS認証情報をメタデータサービスから取得中..."
    CREDENTIALS=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/$ROLE_NAME 2>/dev/null)
    
    ACCESS_KEY=$(echo $CREDENTIALS | jq -r '.AccessKeyId' 2>/dev/null)
    SECRET_KEY=$(echo $CREDENTIALS | jq -r '.SecretAccessKey' 2>/dev/null)
    SESSION_TOKEN=$(echo $CREDENTIALS | jq -r '.Token' 2>/dev/null)
    REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null)
    
    if [ -n "$ACCESS_KEY" ] && [ "$ACCESS_KEY" != "null" ]; then
        echo "export AWS_ACCESS_KEY_ID='$ACCESS_KEY'"
        echo "export AWS_SECRET_ACCESS_KEY='$SECRET_KEY'"
        echo "export AWS_SESSION_TOKEN='$SESSION_TOKEN'"
        echo "export AWS_REGION='$REGION'"
        echo "export AWS_DEFAULT_REGION='$REGION'"
        log "AWS認証情報がメタデータサービスから正常に取得されました"
    else
        error "エラー: メタデータサービスから認証情報を取得できませんでした"
        exit 1
    fi
else
    # ~/.aws/credentialsから認証情報を取得
    log "AWS認証情報をAWS CLIの設定から取得中..."
    
    ACCESS_KEY=$(aws configure get aws_access_key_id 2>/dev/null)
    SECRET_KEY=$(aws configure get aws_secret_access_key 2>/dev/null)
    SESSION_TOKEN=$(aws configure get aws_session_token 2>/dev/null || echo "")
    REGION=$(aws configure get region 2>/dev/null || echo "ap-northeast-1")
    
    if [ -n "$ACCESS_KEY" ] && [ -n "$SECRET_KEY" ]; then
        echo "export AWS_ACCESS_KEY_ID='$ACCESS_KEY'"
        echo "export AWS_SECRET_ACCESS_KEY='$SECRET_KEY'"
        [ -n "$SESSION_TOKEN" ] && echo "export AWS_SESSION_TOKEN='$SESSION_TOKEN'"
        echo "export AWS_REGION='$REGION'"
        echo "export AWS_DEFAULT_REGION='$REGION'"
        log "AWS認証情報がAWS CLIの設定から取得されました"
    else
        error "エラー: AWS認証情報を取得できませんでした"
        exit 1
    fi
fi

# 最後に改行や余計な出力がないことを確実にする
exit 0
