#!/bin/bash
# Script to test S3 access permissions for Pulumi state bucket

echo "Testing S3 access for Pulumi state bucket..."

# Get bucket name from SSM Parameter Store
BUCKET=$(aws ssm get-parameter --name /bootstrap/pulumi/s3bucket-name --query 'Parameter.Value' --output text)

if [ $? -ne 0 ]; then
    echo "Error: Failed to retrieve bucket name from SSM Parameter Store"
    exit 1
fi

echo "Testing bucket: $BUCKET"

# Create a test file
TEST_FILE="/tmp/test-$(date +%s).txt"
echo "Test data - $(date)" > $TEST_FILE

# Test upload
echo "Testing upload to S3..."
if aws s3 cp $TEST_FILE s3://$BUCKET/test.txt; then
    echo "✓ Upload successful"
else
    echo "✗ Upload failed"
    rm -f $TEST_FILE
    exit 1
fi

# Test list
echo "Testing list S3 objects..."
if aws s3 ls s3://$BUCKET/; then
    echo "✓ List successful"
else
    echo "✗ List failed"
fi

# Test download
echo "Testing download from S3..."
if aws s3 cp s3://$BUCKET/test.txt /tmp/download-test.txt; then
    echo "✓ Download successful"
    rm -f /tmp/download-test.txt
else
    echo "✗ Download failed"
fi

# Test delete
echo "Testing delete from S3..."
if aws s3 rm s3://$BUCKET/test.txt; then
    echo "✓ Delete successful"
else
    echo "✗ Delete failed"
fi

# Cleanup
rm -f $TEST_FILE

echo ""
echo "S3 access test completed!"