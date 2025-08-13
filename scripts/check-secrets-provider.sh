#!/bin/bash

# secrets_providersの詳細を確認

echo "Checking secrets_providers configuration..."

S3_BUCKET=$(aws ssm get-parameter --name "/bootstrap/pulumi/s3bucket-name" --query 'Parameter.Value' --output text)

echo "Full secrets_providers section from dev.json:"
aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/dev.json - 2>/dev/null | python3 -c "
import json
import sys
data = json.load(sys.stdin)
if 'deployment' in data and 'secrets_providers' in data['deployment']:
    print(json.dumps(data['deployment']['secrets_providers'], indent=2))
else:
    print('No secrets_providers found')
"

echo ""
echo "Checking if the file still has references to Pulumi Cloud..."
aws s3 cp s3://${S3_BUCKET}/.pulumi/stacks/jenkins-agent/dev.json - 2>/dev/null | grep -E "(api\.pulumi\.com|yuto-takashi|organization)" || echo "No Pulumi Cloud references found"