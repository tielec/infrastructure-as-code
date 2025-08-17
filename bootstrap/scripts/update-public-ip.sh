#!/bin/bash

# Update SSM Parameter with current public IP
# This script runs on every EC2 instance start/restart

set -e

# Get the AWS region from instance metadata
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)

# Get the current public IP
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

# Check if public IP was retrieved
if [ -z "$PUBLIC_IP" ] || [ "$PUBLIC_IP" == "None" ]; then
    echo "Error: Could not retrieve public IP address"
    exit 1
fi

echo "Current public IP: $PUBLIC_IP"

# Update SSM Parameter Store
if aws ssm put-parameter \
    --name /bootstrap/workterminal/public-ip \
    --value "$PUBLIC_IP" \
    --type String \
    --overwrite \
    --region "$REGION" 2>&1; then
    echo "Successfully updated SSM parameter /bootstrap/workterminal/public-ip with IP: $PUBLIC_IP"
else
    echo "Failed to update SSM parameter"
    exit 1
fi

# Log the update
echo "$(date '+%Y-%m-%d %H:%M:%S') - Updated public IP to $PUBLIC_IP" >> /var/log/update-public-ip.log