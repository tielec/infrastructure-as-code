#!/bin/bash

# Pulumiの深いデバッグ

echo "=========================================="
echo "Deep Debug Pulumi Stack Issue"
echo "=========================================="

# 環境変数の設定
export AWS_REGION="ap-northeast-1"
export AWS_DEFAULT_REGION="ap-northeast-1"
export PULUMI_CONFIG_PASSPHRASE=$(aws ssm get-parameter --name "/bootstrap/pulumi/config-passphrase" --with-decryption --query 'Parameter.Value' --output text)

# S3バケット名を取得
S3_BUCKET=$(aws ssm get-parameter --name "/bootstrap/pulumi/s3bucket-name" --query 'Parameter.Value' --output text)

cd /home/ec2-user/infrastructure-as-code/pulumi/jenkins-agent

echo "1. Current Pulumi.yaml content:"
cat Pulumi.yaml
echo ""

echo "2. Check for any Pulumi.*.yaml files:"
ls -la Pulumi*.yaml 2>/dev/null || echo "Only Pulumi.yaml exists"
echo ""

echo "3. Check home directory for .pulumi:"
ls -la ~/.pulumi/ 2>/dev/null | head -20 || echo "No ~/.pulumi directory"
echo ""

echo "4. Environment variables:"
env | grep -i pulumi | grep -v PASSPHRASE
echo ""

echo "5. S3 backend login with verbose output:"
pulumi login s3://${S3_BUCKET} -v 9 2>&1 | grep -A5 -B5 "jenkins-agent" | head -20
echo ""

echo "6. Try to access stack with different methods:"
echo "   a. Using pulumi stack select:"
pulumi stack select dev 2>&1
echo ""

echo "   b. Using pulumi stack select with full path:"
pulumi stack select jenkins-agent/dev 2>&1
echo ""

echo "   c. Using just stack name:"
pulumi stack select --stack dev 2>&1
echo ""

echo "7. Check Pulumi CLI behavior:"
echo "   Running: pulumi about"
pulumi about 2>&1 | grep -A3 -B3 "Stack"
echo ""

echo "8. Try to export the stack:"
pulumi stack export 2>&1 | head -20
echo ""

echo "9. Check if there's a workspace file:"
find . -name "*.workspace.json" -o -name "*.workspace.yml" 2>/dev/null
echo ""

echo "10. Check S3 for any other jenkins-agent related files:"
aws s3 ls s3://${S3_BUCKET}/.pulumi/ --recursive | grep jenkins-agent
echo ""

echo "=========================================="
echo "Debug completed"
echo "=========================================="