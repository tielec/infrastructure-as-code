#!/bin/bash

# S3のスタックファイルの内容を確認

echo "Verifying stack file in S3..."

S3_BUCKET=$(aws ssm get-parameter --name "/bootstrap/pulumi/s3bucket-name" --query 'Parameter.Value' --output text)

echo "Checking jenkins-agent/dev.json:"
echo ""
echo "1. checkpoint.Stack value:"
aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/dev.json - 2>/dev/null | \
    python3 -c "import json, sys; data = json.load(sys.stdin); print(data.get('checkpoint', {}).get('Stack', 'not found'))"

echo ""
echo "2. secrets_providers configuration:"
aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/dev.json - 2>/dev/null | \
    python3 -c "import json, sys; data = json.load(sys.stdin); print(json.dumps(data.get('deployment', {}).get('secrets_providers', {}), indent=2))"

echo ""
echo "3. First resource URN (to check format):"
aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/dev.json - 2>/dev/null | \
    python3 -c "import json, sys; data = json.load(sys.stdin); resources = data.get('deployment', {}).get('resources', []); print(resources[0].get('urn', 'no resources') if resources else 'no resources')"