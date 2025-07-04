#!/bin/bash
#
# IP Whitelist初期設定スクリプト
# 各環境のSecrets Managerに初期設定を作成します

set -e

PROJECT_NAME="lambda-api"
ENVIRONMENTS=("dev" "staging" "prod")

# 初期設定のJSON
create_initial_config() {
    local env=$1
    local config='{
  "version": "1.0",
  "lastUpdated": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
  "clients": [],
  "globalRules": {
    "allowedEnvironments": ["dev", "staging", "prod"],
    "maxIpsPerClient": 10,
    "ipFormat": "CIDR"
  }
}'

    # 開発環境用のデフォルトクライアント
    if [ "$env" = "dev" ]; then
        config=$(echo $config | jq '.clients += [{
            "id": "dev-team",
            "name": "Development Team",
            "description": "Development team access",
            "enabled": true,
            "ipAddresses": ["0.0.0.0/0"],
            "tags": {
                "type": "internal",
                "priority": "low",
                "environment": "dev-only"
            }
        }]')
    fi

    echo "$config"
}

# 各環境でSecretを作成
for ENV in "${ENVIRONMENTS[@]}"; do
    SECRET_NAME="${PROJECT_NAME}/ip-whitelist/${ENV}"
    
    echo "Checking if secret exists: $SECRET_NAME"
    
    # Secretが存在するかチェック
    if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" 2>/dev/null; then
        echo "Secret already exists: $SECRET_NAME"
        read -p "Do you want to update it? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # 既存のSecretを更新
            INITIAL_CONFIG=$(create_initial_config "$ENV")
            aws secretsmanager put-secret-value \
                --secret-id "$SECRET_NAME" \
                --secret-string "$INITIAL_CONFIG"
            echo "Updated: $SECRET_NAME"
        else
            echo "Skipped: $SECRET_NAME"
        fi
    else
        # 新規作成
        echo "Creating new secret: $SECRET_NAME"
        INITIAL_CONFIG=$(create_initial_config "$ENV")
        aws secretsmanager create-secret \
            --name "$SECRET_NAME" \
            --description "IP whitelist configuration for ${PROJECT_NAME} WAF - ${ENV}" \
            --secret-string "$INITIAL_CONFIG" \
            --tags Key=Environment,Value="${ENV}" Key=ManagedBy,Value=pulumi Key=Project,Value="${PROJECT_NAME}"
        echo "Created: $SECRET_NAME"
    fi
    
    echo "---"
done

echo "IP Whitelist initialization completed!"
echo ""
echo "Next steps:"
echo "1. Add your IP addresses to the whitelist:"
echo "   aws secretsmanager get-secret-value --secret-id ${PROJECT_NAME}/ip-whitelist/dev --query SecretString --output text | jq ."
echo ""
echo "2. Deploy the WAF stack:"
echo "   cd pulumi/lambda-waf && pulumi up"
