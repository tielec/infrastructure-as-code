#!/bin/bash
# Lambda環境の簡易チェックスクリプト

set -euo pipefail

ENV_NAME="${1:-dev}"
REGION="${AWS_REGION:-ap-northeast-1}"

echo "========================================"
echo "Lambda Environment Check"
echo "========================================"
echo "Environment: ${ENV_NAME}"
echo "Region: ${REGION}"
echo "========================================"

# VPCチェック
echo -e "\n[VPC & Network]"
VPC_ID=$(aws ssm get-parameter --name "/lambda-api/${ENV_NAME}/network/vpc-id" --query "Parameter.Value" --output text 2>/dev/null || echo "")
if [ -n "$VPC_ID" ]; then
    echo "✅ VPC: ${VPC_ID}"
else
    echo "❌ VPC not found"
fi

# Lambda関数チェック
echo -e "\n[Lambda Functions]"
FUNCTIONS=$(aws lambda list-functions --query "Functions[?starts_with(FunctionName, 'lambda-api-${ENV_NAME}')].FunctionName" --output text 2>/dev/null || echo "")
if [ -n "$FUNCTIONS" ]; then
    COUNT=$(echo "$FUNCTIONS" | wc -w)
    echo "✅ Found ${COUNT} Lambda functions"
    echo "$FUNCTIONS" | tr '\t' '\n' | while read -r func; do
        echo "  - ${func}"
    done
else
    echo "❌ No Lambda functions found"
fi

# API Gatewayチェック
echo -e "\n[API Gateway]"
API_CONFIG=$(aws ssm get-parameter --name "/lambda-api/${ENV_NAME}/api-gateway/config" --query "Parameter.Value" --output text 2>/dev/null || echo "")
if [ -n "$API_CONFIG" ]; then
    API_ID=$(echo "$API_CONFIG" | python3 -c "import sys, json; print(json.load(sys.stdin)['apiId'])" 2>/dev/null || echo "")
    API_ENDPOINT=$(echo "$API_CONFIG" | python3 -c "import sys, json; print(json.load(sys.stdin)['apiEndpoint'])" 2>/dev/null || echo "")
    if [ -n "$API_ID" ]; then
        echo "✅ API ID: ${API_ID}"
        echo "✅ Endpoint: ${API_ENDPOINT}"
    fi
else
    echo "❌ API Gateway not configured"
fi

echo -e "\n========================================"
echo "Check completed"
echo "========================================"