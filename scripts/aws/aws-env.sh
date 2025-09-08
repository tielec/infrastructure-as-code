#!/bin/bash
# ==================================================================
# AWS認証情報設定スクリプト
# 
# 目的：
#   - AWS認証情報を環境変数として設定する
#   - Ansibleから呼び出されることを想定し、標準出力を抑制
#   - EC2インスタンスとローカル環境の両方に対応
#
# 使用方法：
#   - 通常実行: ./aws-env.sh
#   - デバッグ: AWS_ENV_DEBUG=true ./aws-env.sh
#
# 注意事項：
#   - このスクリプトは環境変数を設定するため、sourceコマンドで
#     実行するか、Ansibleのshellモジュールから呼び出す必要があります
#   - 標準出力は意図的に抑制されています（Ansible連携のため）
# ==================================================================

# デバッグモード（環境変数で制御）
# AWS_ENV_DEBUG=true を設定すると、標準エラー出力にログが出力される
DEBUG="${AWS_ENV_DEBUG:-false}"

# ログ関数
# デバッグモードが有効な場合のみ、標準エラー出力にメッセージを出力
# Ansibleの実行結果に影響を与えないよう、標準エラー出力を使用
log() {
    if [ "$DEBUG" = "true" ]; then
        echo "$@" >&2
    fi
}

# ==================================================================
# 既存の環境変数チェック
# すでにAWS認証情報が設定されている場合は何もせずに終了
# これにより、不要な処理をスキップし、既存の認証情報を保護
# ==================================================================
if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
    log "# AWS認証情報は既に環境変数に設定されています"
    exit 0
fi

# ==================================================================
# EC2インスタンスのメタデータサービスからの認証情報取得
# EC2インスタンス上で実行されている場合、IAMロールの一時認証情報を取得
# ==================================================================

# IMDSv2（Instance Metadata Service Version 2）のトークンを取得
# セキュリティ向上のため、IMDSv2を使用（トークンベースの認証）
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null)

# IAMロール名の取得
# EC2インスタンスに割り当てられているIAMロール名を取得
ROLE_NAME=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/ 2>/dev/null)

if [ -n "$ROLE_NAME" ]; then
    # EC2インスタンス上で実行されている場合
    log "# AWS認証情報をメタデータサービスから取得中..."
    
    # IAMロールの一時認証情報を取得
    # この認証情報は定期的に自動更新される
    CREDENTIALS=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/$ROLE_NAME)
    
    # JSON形式の認証情報から必要な値を抽出して環境変数に設定
    export AWS_ACCESS_KEY_ID=$(echo $CREDENTIALS | jq -r '.AccessKeyId')
    export AWS_SECRET_ACCESS_KEY=$(echo $CREDENTIALS | jq -r '.SecretAccessKey')
    export AWS_SESSION_TOKEN=$(echo $CREDENTIALS | jq -r '.Token')  # 一時認証情報のため、セッショントークンが必要
    
    # リージョン情報も取得
    export AWS_REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)
    
    log "# AWS認証情報がメタデータサービスから正常に取得されました"
else
    # ==================================================================
    # ローカル環境での認証情報取得
    # EC2インスタンスではない場合、AWS CLIの設定ファイルから認証情報を取得
    # 通常は ~/.aws/credentials と ~/.aws/config から読み込まれる
    # ==================================================================
    log "# AWS認証情報をAWS CLIの設定から取得中..."
    
    # AWS CLIの設定から認証情報を取得
    export AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
    export AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)
    
    # セッショントークンは存在しない場合があるため、エラーを抑制
    AWS_SESSION_TOKEN=$(aws configure get aws_session_token 2>/dev/null || echo "")
    [ -n "$AWS_SESSION_TOKEN" ] && export AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN"
    
    # リージョンの取得（デフォルト: us-west-2 = 米国西部リージョン）
    export AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-west-2")
    
    log "# AWS認証情報がAWS CLIの設定から取得されました"
fi

# ==================================================================
# 認証情報の検証
# 必須の認証情報が取得できたかを確認
# ==================================================================
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    # エラーメッセージは標準エラー出力に出力（Ansibleでもエラーとして認識される）
    echo "エラー: AWS認証情報を取得できませんでした" >&2
    exit 1
fi

log "# AWS認証情報の設定が完了しました"

# スクリプトの正常終了
# 環境変数は呼び出し元のシェルプロセスに引き継がれる
