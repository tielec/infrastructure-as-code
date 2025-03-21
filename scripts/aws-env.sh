#!/bin/bash
# aws-env.sh - AWS環境変数の設定（セキュリティ強化版）

# 認証情報取得
ACCESS_KEY=$(aws configure get aws_access_key_id 2>/dev/null)
SECRET_KEY=$(aws configure get aws_secret_access_key 2>/dev/null)
SESSION_TOKEN=$(aws configure get aws_session_token 2>/dev/null)

# 環境変数をエクスポート（トークンがあれば設定）
if [ -n "$ACCESS_KEY" ]; then
  export AWS_ACCESS_KEY_ID="$ACCESS_KEY"
else
  echo "Warning: AWS_ACCESS_KEY_ID not found" >&2
fi

if [ -n "$SECRET_KEY" ]; then
  export AWS_SECRET_ACCESS_KEY="$SECRET_KEY"
else
  echo "Warning: AWS_SECRET_ACCESS_KEY not found" >&2
fi

if [ -n "$SESSION_TOKEN" ]; then
  export AWS_SESSION_TOKEN="$SESSION_TOKEN"
fi

export AWS_REGION="ap-northeast-1"

# 安全な確認メッセージ
echo "AWS環境変数が設定されました。" >&2
echo "AWS_REGION=$AWS_REGION" >&2
echo "AWS認証情報: $([ -n "$ACCESS_KEY" ] && echo "設定済み" || echo "未設定")" >&2

# シェル用のコマンドを出力（ただし認証情報は表示しない）
echo "export AWS_REGION=\"$AWS_REGION\";"
[ -n "$ACCESS_KEY" ] && echo "export AWS_ACCESS_KEY_ID=\$AWS_ACCESS_KEY_ID;"
[ -n "$SECRET_KEY" ] && echo "export AWS_SECRET_ACCESS_KEY=\$AWS_SECRET_ACCESS_KEY;"
[ -n "$SESSION_TOKEN" ] && echo "export AWS_SESSION_TOKEN=\$AWS_SESSION_TOKEN;"