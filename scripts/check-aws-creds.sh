#!/bin/bash
# AWS認証情報の確認と簡易的な設定スクリプト

# 認証情報の確認
echo "現在のAWS認証情報を確認します："
aws configure list

# sts get-caller-identityで検証
echo "AWS STS認証情報を検証します："
aws sts get-caller-identity

# 基本的な認証情報変数をエクスポート
echo "AWS認証情報を環境変数としてエクスポートします："
export AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
export AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)
export AWS_SESSION_TOKEN=$(aws configure get aws_session_token 2>/dev/null || echo "")

echo "環境変数の設定が完了しました"
echo "AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:0:5}... (最初の5文字のみ表示)"
echo "AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:0:5}... (最初の5文字のみ表示)"
if [ -n "$AWS_SESSION_TOKEN" ]; then
    echo "AWS_SESSION_TOKEN=設定済み"
else
    echo "AWS_SESSION_TOKEN=未設定"
fi
