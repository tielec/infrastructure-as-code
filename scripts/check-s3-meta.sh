#!/bin/bash

# S3バックエンドのメタデータを確認

echo "Checking S3 backend metadata..."

# S3バケット名を取得
S3_BUCKET=$(aws ssm get-parameter --name "/bootstrap/pulumi/s3bucket-name" --query 'Parameter.Value' --output text)
echo "S3 bucket: $S3_BUCKET"

# .pulumi/meta.yaml の内容を確認
echo ""
echo "Checking .pulumi/meta.yaml in S3..."
aws s3 cp s3://${S3_BUCKET}/.pulumi/meta.yaml - 2>/dev/null

# jenkins-agentプロジェクトのメタデータを確認
echo ""
echo "Checking jenkins-agent project metadata..."
aws s3 ls s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/

# devスタックの内容を確認（最初の数行だけ）
echo ""
echo "Checking dev.json content (first 10 lines)..."
aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/dev.json - 2>/dev/null | head -10