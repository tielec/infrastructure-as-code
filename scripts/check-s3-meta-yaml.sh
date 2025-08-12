#!/bin/bash

# S3バックエンドのmeta.yamlを確認

echo "Checking S3 backend meta.yaml..."

S3_BUCKET=$(aws ssm get-parameter --name "/bootstrap/pulumi/s3bucket-name" --query 'Parameter.Value' --output text)

echo "1. Content of .pulumi/meta.yaml:"
aws s3 cp s3://${S3_BUCKET}/.pulumi/meta.yaml - 2>/dev/null

echo ""
echo "2. Checking if there's a project-specific meta.yaml:"
aws s3 ls s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/.pulumi/ 2>/dev/null || echo "   No project-specific .pulumi directory"

echo ""
echo "3. All files in .pulumi/stacks/jenkins-agent/:"
aws s3 ls s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/ --recursive

echo ""
echo "4. Checking if legacy format exists:"
aws s3 ls s3://${S3_BUCKET}/.pulumi/stacks/organization/ 2>/dev/null || echo "   No organization directory found"
aws s3 ls s3://${S3_BUCKET}/.pulumi/stacks/tielec/ 2>/dev/null || echo "   No tielec directory found"