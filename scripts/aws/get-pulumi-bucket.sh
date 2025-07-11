#!/bin/bash
# Script to retrieve Pulumi state bucket name from SSM Parameter Store

BUCKET_NAME=$(aws ssm get-parameter --name /bootstrap/pulumi/s3bucket-name --query 'Parameter.Value' --output text)

if [ $? -eq 0 ]; then
    echo "Pulumi state bucket: $BUCKET_NAME"
else
    echo "Error: Failed to retrieve Pulumi bucket name from SSM Parameter Store"
    exit 1
fi
