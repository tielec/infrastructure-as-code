#!/bin/bash
# Lambda SSMパラメータクリーンアップスクリプト
# 
# 使用方法:
#   ./cleanup-ssm-params.sh dev
#   ./cleanup-ssm-params.sh staging
#   ./cleanup-ssm-params.sh prod

set -euo pipefail

# 環境名を取得
ENV_NAME="${1:-dev}"

echo "=========================================="
echo "Lambda SSM Parameter Cleanup"
echo "=========================================="
echo "Environment: ${ENV_NAME}"
echo ""

# SSMパラメータをリスト表示
echo "Listing SSM parameters for /lambda-api/${ENV_NAME}/..."
PARAMS=$(aws ssm describe-parameters \
  --parameter-filters "Key=Name,Option=BeginsWith,Values=/lambda-api/${ENV_NAME}/" \
  --query "Parameters[].Name" \
  --output text)

if [ -z "$PARAMS" ]; then
  echo "No SSM parameters found."
  exit 0
fi

# パラメータ数をカウント
PARAM_COUNT=$(echo "$PARAMS" | wc -w)
echo "Found ${PARAM_COUNT} parameter(s) to delete:"
echo "$PARAMS" | tr ' ' '\n'
echo ""

# 確認プロンプト
read -p "Are you sure you want to delete these parameters? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Deletion cancelled."
  exit 0
fi

# パラメータを削除
echo ""
echo "Deleting parameters..."
for PARAM in $PARAMS; do
  echo "Deleting: $PARAM"
  aws ssm delete-parameter --name "$PARAM" || echo "Failed to delete: $PARAM"
done

echo ""
echo "=========================================="
echo "Cleanup Complete"
echo "=========================================="

# 残存パラメータの確認
echo "Verifying deletion..."
REMAINING=$(aws ssm describe-parameters \
  --parameter-filters "Key=Name,Option=BeginsWith,Values=/lambda-api/${ENV_NAME}/" \
  --query "Parameters[].Name" \
  --output text)

if [ -z "$REMAINING" ]; then
  echo "✅ All SSM parameters have been successfully deleted."
else
  echo "⚠️  Some parameters still remain:"
  echo "$REMAINING" | tr ' ' '\n'
fi