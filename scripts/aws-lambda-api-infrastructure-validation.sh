#!/bin/bash
#
# Lambda API Infrastructure Phase 1 Validation Script
# 
# Usage: ./validate-lambda-api-infra.sh [environment]
# Example: ./validate-lambda-api-infra.sh dev
#
# This script validates all Phase 1 components of the Lambda API infrastructure

set -euo pipefail

# ========== Configuration ==========
ENV="${1:-dev}"
PROJECT_NAME="lambda-api"
REGION="${AWS_REGION:-ap-northeast-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# ========== Helper Functions ==========

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((PASSED_CHECKS++))
    ((TOTAL_CHECKS++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    ((FAILED_CHECKS++))
    ((TOTAL_CHECKS++))
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
    ((WARNINGS++))
}

section_header() {
    echo
    echo "=========================================="
    echo "$1"
    echo "=========================================="
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "Required command '$1' not found"
        exit 1
    fi
}

get_resource_tag() {
    local resource_id="$1"
    local resource_type="$2"
    local tag_key="$3"
    
    case "$resource_type" in
        "vpc"|"subnet"|"security-group"|"route-table"|"internet-gateway"|"nat-gateway")
            aws ec2 describe-tags \
                --filters "Name=resource-id,Values=$resource_id" "Name=key,Values=$tag_key" \
                --query "Tags[0].Value" \
                --output text 2>/dev/null || echo ""
            ;;
        *)
            echo ""
            ;;
    esac
}

# ========== Pre-flight Checks ==========

section_header "Pre-flight Checks"

log_info "Environment: $ENV"
log_info "Project: $PROJECT_NAME"
log_info "Region: $REGION"

# Check required commands
check_command "aws"
check_command "jq"

# Check AWS credentials
if aws sts get-caller-identity &>/dev/null; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    log_success "AWS credentials configured (Account: $ACCOUNT_ID)"
else
    log_error "AWS credentials not configured"
    exit 1
fi

# ========== 1. Network Resources ==========

section_header "1. Network Resources (lambda-network)"

# Check VPC
log_info "Checking VPC..."
VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=tag:Name,Values=${PROJECT_NAME}-vpc-${ENV}" \
    --query "Vpcs[0].VpcId" \
    --output text 2>/dev/null || echo "None")

if [[ "$VPC_ID" != "None" && "$VPC_ID" != "null" ]]; then
    log_success "VPC found: $VPC_ID"
    
    # Get VPC CIDR
    VPC_CIDR=$(aws ec2 describe-vpcs \
        --vpc-ids "$VPC_ID" \
        --query "Vpcs[0].CidrBlock" \
        --output text)
    log_info "  CIDR: $VPC_CIDR"
    
    if [[ "$VPC_CIDR" == "10.1.0.0/16" ]]; then
        log_success "VPC CIDR matches design: 10.1.0.0/16"
    else
        log_warning "VPC CIDR differs from design (expected: 10.1.0.0/16, actual: $VPC_CIDR)"
    fi
else
    log_error "VPC not found"
    VPC_ID=""
fi

# Check Internet Gateway
if [[ -n "$VPC_ID" ]]; then
    IGW_ID=$(aws ec2 describe-internet-gateways \
        --filters "Name=attachment.vpc-id,Values=$VPC_ID" \
        --query "InternetGateways[0].InternetGatewayId" \
        --output text 2>/dev/null || echo "None")
    
    if [[ "$IGW_ID" != "None" && "$IGW_ID" != "null" ]]; then
        log_success "Internet Gateway found: $IGW_ID"
    else
        log_error "Internet Gateway not found"
    fi
fi

# Check Subnets
if [[ -n "$VPC_ID" ]]; then
    log_info "Checking Subnets..."
    
    # Expected subnets for Phase 1
    declare -A EXPECTED_SUBNETS=(
        ["public-a"]="10.1.0.0/24"
        ["public-b"]="10.1.2.0/24"
        ["private-a"]="10.1.1.0/24"
        ["private-b"]="10.1.3.0/24"
    )
    
    for subnet_type in "${!EXPECTED_SUBNETS[@]}"; do
        SUBNET_ID=$(aws ec2 describe-subnets \
            --filters "Name=vpc-id,Values=$VPC_ID" \
                     "Name=tag:Name,Values=${PROJECT_NAME}-${subnet_type}-subnet-${ENV}" \
            --query "Subnets[0].SubnetId" \
            --output text 2>/dev/null || echo "None")
        
        if [[ "$SUBNET_ID" != "None" && "$SUBNET_ID" != "null" ]]; then
            SUBNET_CIDR=$(aws ec2 describe-subnets \
                --subnet-ids "$SUBNET_ID" \
                --query "Subnets[0].CidrBlock" \
                --output text)
            
            if [[ "$SUBNET_CIDR" == "${EXPECTED_SUBNETS[$subnet_type]}" ]]; then
                log_success "Subnet $subnet_type: $SUBNET_ID (CIDR: $SUBNET_CIDR ✓)"
            else
                log_warning "Subnet $subnet_type: $SUBNET_ID (CIDR mismatch: expected ${EXPECTED_SUBNETS[$subnet_type]}, got $SUBNET_CIDR)"
            fi
        else
            log_error "Subnet $subnet_type not found"
        fi
    done
    
    # Check for isolated subnets (should not exist in Phase 1)
    ISOLATED_COUNT=$(aws ec2 describe-subnets \
        --filters "Name=vpc-id,Values=$VPC_ID" \
                 "Name=tag:Name,Values=${PROJECT_NAME}-isolated-*" \
        --query "length(Subnets)" \
        --output text 2>/dev/null || echo "0")
    
    if [[ "$ISOLATED_COUNT" == "0" ]]; then
        log_success "No isolated subnets (correct for Phase 1)"
    else
        log_warning "Found $ISOLATED_COUNT isolated subnets (should be Phase 2)"
    fi
fi

# Check Route Tables
if [[ -n "$VPC_ID" ]]; then
    log_info "Checking Route Tables..."
    
    # Public route table
    PUBLIC_RT=$(aws ec2 describe-route-tables \
        --filters "Name=vpc-id,Values=$VPC_ID" \
                 "Name=tag:Name,Values=${PROJECT_NAME}-public-rt-${ENV}" \
        --query "RouteTables[0].RouteTableId" \
        --output text 2>/dev/null || echo "None")
    
    if [[ "$PUBLIC_RT" != "None" && "$PUBLIC_RT" != "null" ]]; then
        log_success "Public route table found: $PUBLIC_RT"
        
        # Check for internet route
        IGW_ROUTE=$(aws ec2 describe-route-tables \
            --route-table-ids "$PUBLIC_RT" \
            --query "RouteTables[0].Routes[?DestinationCidrBlock=='0.0.0.0/0'].GatewayId" \
            --output text 2>/dev/null || echo "None")
        
        if [[ "$IGW_ROUTE" == igw-* ]]; then
            log_success "Internet route configured in public route table"
        else
            log_error "Internet route not found in public route table"
        fi
    else
        log_error "Public route table not found"
    fi
    
    # Private route tables
    for az in a b; do
        PRIVATE_RT=$(aws ec2 describe-route-tables \
            --filters "Name=vpc-id,Values=$VPC_ID" \
                     "Name=tag:Name,Values=${PROJECT_NAME}-private-rt-${az}-${ENV}" \
            --query "RouteTables[0].RouteTableId" \
            --output text 2>/dev/null || echo "None")
        
        if [[ "$PRIVATE_RT" != "None" && "$PRIVATE_RT" != "null" ]]; then
            log_success "Private route table $az found: $PRIVATE_RT"
        else
            log_error "Private route table $az not found"
        fi
    done
fi

# ========== 2. Security Groups ==========

section_header "2. Security Groups (lambda-security)"

if [[ -n "$VPC_ID" ]]; then
    # Expected security groups
    declare -a EXPECTED_SGS=(
        "lambda-sg"
        "vpce-sg"
        "nat-instance-sg"
        "dlq-sg"
    )
    
    for sg_name in "${EXPECTED_SGS[@]}"; do
        SG_ID=$(aws ec2 describe-security-groups \
            --filters "Name=vpc-id,Values=$VPC_ID" \
                     "Name=tag:Name,Values=${PROJECT_NAME}-${sg_name}-${ENV}" \
            --query "SecurityGroups[0].GroupId" \
            --output text 2>/dev/null || echo "None")
        
        if [[ "$SG_ID" != "None" && "$SG_ID" != "null" ]]; then
            log_success "Security group $sg_name found: $SG_ID"
            
            # Check specific rules for lambda-sg (outbound only)
            if [[ "$sg_name" == "lambda-sg" ]]; then
                INGRESS_COUNT=$(aws ec2 describe-security-groups \
                    --group-ids "$SG_ID" \
                    --query "length(SecurityGroups[0].IpPermissions)" \
                    --output text)
                
                if [[ "$INGRESS_COUNT" == "0" ]]; then
                    log_success "  Lambda SG has no ingress rules (correct)"
                else
                    log_warning "  Lambda SG has $INGRESS_COUNT ingress rules (should be 0)"
                fi
            fi
        else
            log_error "Security group $sg_name not found"
        fi
    done
fi

# ========== 3. VPC Endpoints ==========

section_header "3. VPC Endpoints (lambda-vpce)"

if [[ -n "$VPC_ID" ]]; then
    # Check S3 endpoint (required for Phase 1)
    S3_ENDPOINT=$(aws ec2 describe-vpc-endpoints \
        --filters "Name=vpc-id,Values=$VPC_ID" \
                 "Name=service-name,Values=com.amazonaws.${REGION}.s3" \
        --query "VpcEndpoints[0].VpcEndpointId" \
        --output text 2>/dev/null || echo "None")
    
    if [[ "$S3_ENDPOINT" != "None" && "$S3_ENDPOINT" != "null" ]]; then
        log_success "S3 VPC endpoint found: $S3_ENDPOINT"
    else
        log_error "S3 VPC endpoint not found (required for Phase 1)"
    fi
    
    # Check optional endpoints
    for service in secretsmanager kms dynamodb; do
        ENDPOINT=$(aws ec2 describe-vpc-endpoints \
            --filters "Name=vpc-id,Values=$VPC_ID" \
                     "Name=service-name,Values=com.amazonaws.${REGION}.${service}" \
            --query "VpcEndpoints[0].VpcEndpointId" \
            --output text 2>/dev/null || echo "None")
        
        if [[ "$ENDPOINT" != "None" && "$ENDPOINT" != "null" ]]; then
            log_info "Optional $service endpoint found: $ENDPOINT"
        fi
    done
fi

# ========== 4. NAT Configuration ==========

section_header "4. NAT Configuration (lambda-nat)"

if [[ -n "$VPC_ID" ]]; then
    # Check for NAT Gateways
    NAT_GW_COUNT=$(aws ec2 describe-nat-gateways \
        --filter "Name=vpc-id,Values=$VPC_ID" "Name=state,Values=available" \
        --query "length(NatGateways)" \
        --output text 2>/dev/null || echo "0")
    
    if [[ "$NAT_GW_COUNT" -gt 0 ]]; then
        log_success "Found $NAT_GW_COUNT NAT Gateway(s)"
        
        if [[ "$ENV" == "prod" && "$NAT_GW_COUNT" -lt 2 ]]; then
            log_warning "Production should have 2 NAT Gateways for HA (found: $NAT_GW_COUNT)"
        fi
    else
        # Check for NAT Instance
        NAT_INSTANCE=$(aws ec2 describe-instances \
            --filters "Name=vpc-id,Values=$VPC_ID" \
                     "Name=tag:Name,Values=${PROJECT_NAME}-nat-instance-${ENV}" \
                     "Name=instance-state-name,Values=running" \
            --query "Reservations[0].Instances[0].InstanceId" \
            --output text 2>/dev/null || echo "None")
        
        if [[ "$NAT_INSTANCE" != "None" && "$NAT_INSTANCE" != "null" ]]; then
            log_success "NAT Instance found: $NAT_INSTANCE"
            
            # Check instance type
            INSTANCE_TYPE=$(aws ec2 describe-instances \
                --instance-ids "$NAT_INSTANCE" \
                --query "Reservations[0].Instances[0].InstanceType" \
                --output text)
            
            log_info "  Instance type: $INSTANCE_TYPE"
            
            # Check source/dest check is disabled
            SRC_DEST_CHECK=$(aws ec2 describe-instances \
                --instance-ids "$NAT_INSTANCE" \
                --query "Reservations[0].Instances[0].SourceDestCheck" \
                --output text)
            
            if [[ "$SRC_DEST_CHECK" == "False" ]]; then
                log_success "  Source/Dest check disabled (correct)"
            else
                log_error "  Source/Dest check enabled (should be disabled)"
            fi
        else
            log_error "No NAT Gateway or NAT Instance found"
        fi
    fi
fi

# ========== 5. Lambda Functions ==========

section_header "5. Lambda Functions (lambda-functions)"

# Main Lambda function
LAMBDA_FUNCTION="${PROJECT_NAME}-main-${ENV}"
LAMBDA_EXISTS=$(aws lambda get-function \
    --function-name "$LAMBDA_FUNCTION" \
    --query "Configuration.FunctionName" \
    --output text 2>/dev/null || echo "None")

if [[ "$LAMBDA_EXISTS" != "None" && "$LAMBDA_EXISTS" != "null" ]]; then
    log_success "Lambda function found: $LAMBDA_FUNCTION"
    
    # Check configuration
    LAMBDA_CONFIG=$(aws lambda get-function-configuration \
        --function-name "$LAMBDA_FUNCTION" \
        --output json 2>/dev/null)
    
    if [[ -n "$LAMBDA_CONFIG" ]]; then
        MEMORY=$(echo "$LAMBDA_CONFIG" | jq -r '.MemorySize')
        TIMEOUT=$(echo "$LAMBDA_CONFIG" | jq -r '.Timeout')
        RUNTIME=$(echo "$LAMBDA_CONFIG" | jq -r '.Runtime')
        VPC_CONFIG=$(echo "$LAMBDA_CONFIG" | jq -r '.VpcConfig')
        
        log_info "  Memory: ${MEMORY}MB"
        log_info "  Timeout: ${TIMEOUT}s"
        log_info "  Runtime: $RUNTIME"
        
        if [[ "$VPC_CONFIG" != "null" ]]; then
            log_success "  VPC configuration present"
        else
            log_error "  No VPC configuration"
        fi
        
        # Check DLQ
        DLQ_ARN=$(echo "$LAMBDA_CONFIG" | jq -r '.DeadLetterConfig.TargetArn // empty')
        if [[ -n "$DLQ_ARN" ]]; then
            log_success "  DLQ configured: ${DLQ_ARN##*/}"
        else
            log_error "  No DLQ configured"
        fi
    fi
else
    log_error "Lambda function not found: $LAMBDA_FUNCTION"
fi

# Check SQS DLQ
DLQ_NAME="${PROJECT_NAME}-dlq-${ENV}"
DLQ_URL=$(aws sqs get-queue-url \
    --queue-name "$DLQ_NAME" \
    --query "QueueUrl" \
    --output text 2>/dev/null || echo "None")

if [[ "$DLQ_URL" != "None" && "$DLQ_URL" != "null" ]]; then
    log_success "SQS DLQ found: $DLQ_NAME"
    
    # Check message count
    MSG_COUNT=$(aws sqs get-queue-attributes \
        --queue-url "$DLQ_URL" \
        --attribute-names ApproximateNumberOfMessages \
        --query "Attributes.ApproximateNumberOfMessages" \
        --output text 2>/dev/null || echo "0")
    
    log_info "  Messages in DLQ: $MSG_COUNT"
else
    log_error "SQS DLQ not found: $DLQ_NAME"
fi

# ========== 6. API Gateway ==========

section_header "6. API Gateway (lambda-api-gateway)"

# Find API Gateway
API_NAME="${PROJECT_NAME}-api-${ENV}"
API_ID=$(aws apigateway get-rest-apis \
    --query "items[?name=='$API_NAME'].id" \
    --output text 2>/dev/null || echo "None")

if [[ "$API_ID" != "None" && "$API_ID" != "null" && -n "$API_ID" ]]; then
    log_success "API Gateway found: $API_ID"
    
    # Check deployment stage
    STAGE_EXISTS=$(aws apigateway get-stage \
        --rest-api-id "$API_ID" \
        --stage-name "$ENV" \
        --query "stageName" \
        --output text 2>/dev/null || echo "None")
    
    if [[ "$STAGE_EXISTS" == "$ENV" ]]; then
        log_success "Stage '$ENV' deployed"
        
        # Get API endpoint
        API_ENDPOINT="https://${API_ID}.execute-api.${REGION}.amazonaws.com/${ENV}"
        log_info "  Endpoint: $API_ENDPOINT"
    else
        log_error "Stage '$ENV' not found"
    fi
    
    # Check usage plan
    USAGE_PLAN=$(aws apigateway get-usage-plans \
        --query "items[?name=='${PROJECT_NAME}-usage-plan-${ENV}'].id" \
        --output text 2>/dev/null || echo "None")
    
    if [[ "$USAGE_PLAN" != "None" && "$USAGE_PLAN" != "null" && -n "$USAGE_PLAN" ]]; then
        log_success "Usage plan found: $USAGE_PLAN"
        
        # Get usage plan details
        PLAN_DETAILS=$(aws apigateway get-usage-plan \
            --usage-plan-id "$USAGE_PLAN" \
            --output json 2>/dev/null)
        
        if [[ -n "$PLAN_DETAILS" ]]; then
            RATE_LIMIT=$(echo "$PLAN_DETAILS" | jq -r '.throttle.rateLimit // "N/A"')
            BURST_LIMIT=$(echo "$PLAN_DETAILS" | jq -r '.throttle.burstLimit // "N/A"')
            QUOTA_LIMIT=$(echo "$PLAN_DETAILS" | jq -r '.quota.limit // "N/A"')
            
            log_info "  Rate limit: $RATE_LIMIT req/s"
            log_info "  Burst limit: $BURST_LIMIT"
            log_info "  Daily quota: $QUOTA_LIMIT"
        fi
    else
        log_error "Usage plan not found"
    fi
    
    # Check API keys
    API_KEY_COUNT=$(aws apigateway get-api-keys \
        --include-values \
        --query "length(items[?name | contains('${PROJECT_NAME}') && name | contains('${ENV}')])" \
        --output text 2>/dev/null || echo "0")
    
    if [[ "$API_KEY_COUNT" -gt 0 ]]; then
        log_success "Found $API_KEY_COUNT API key(s)"
    else
        log_error "No API keys found"
    fi
else
    log_error "API Gateway not found: $API_NAME"
fi

# ========== 7. WAF Configuration ==========

section_header "7. WAF Configuration (lambda-waf)"

# Check Web ACL
WEB_ACL_NAME="${PROJECT_NAME}-web-acl-${ENV}"
WEB_ACL=$(aws wafv2 list-web-acls \
    --scope REGIONAL \
    --query "WebACLs[?Name=='$WEB_ACL_NAME'].ARN" \
    --output text 2>/dev/null || echo "None")

if [[ "$WEB_ACL" != "None" && "$WEB_ACL" != "null" && -n "$WEB_ACL" ]]; then
    log_success "WAF Web ACL found"
    
    # Check association with API Gateway
    if [[ -n "$API_ID" ]]; then
        ASSOCIATED_RESOURCE=$(aws wafv2 get-web-acl-for-resource \
            --resource-arn "arn:aws:apigateway:${REGION}::/restapis/${API_ID}/stages/${ENV}" \
            --query "WebACL.Name" \
            --output text 2>/dev/null || echo "None")
        
        if [[ "$ASSOCIATED_RESOURCE" == "$WEB_ACL_NAME" ]]; then
            log_success "WAF associated with API Gateway"
        else
            log_error "WAF not associated with API Gateway"
        fi
    fi
    
    # Check IP Set
    IP_SET_NAME="${PROJECT_NAME}-ip-whitelist-${ENV}"
    IP_SET=$(aws wafv2 list-ip-sets \
        --scope REGIONAL \
        --query "IPSets[?Name=='$IP_SET_NAME'].ARN" \
        --output text 2>/dev/null || echo "None")
    
    if [[ "$IP_SET" != "None" && "$IP_SET" != "null" && -n "$IP_SET" ]]; then
        log_success "IP Set found"
        
        # Get IP count
        IP_COUNT=$(aws wafv2 get-ip-set \
            --name "$IP_SET_NAME" \
            --scope REGIONAL \
            --id "${IP_SET##*/}" \
            --query "length(IPSet.Addresses)" \
            --output text 2>/dev/null || echo "0")
        
        log_info "  IP addresses configured: $IP_COUNT"
    else
        log_error "IP Set not found"
    fi
else
    log_error "WAF Web ACL not found: $WEB_ACL_NAME"
fi

# ========== 8. Secrets Manager ==========

section_header "8. Secrets Manager (IP Whitelist)"

# Check IP whitelist secret
SECRET_NAME="${PROJECT_NAME}/ip-whitelist/${ENV}"
SECRET_EXISTS=$(aws secretsmanager describe-secret \
    --secret-id "$SECRET_NAME" \
    --query "Name" \
    --output text 2>/dev/null || echo "None")

if [[ "$SECRET_EXISTS" == "$SECRET_NAME" ]]; then
    log_success "IP whitelist secret found: $SECRET_NAME"
    
    # Get secret value structure (without displaying IPs)
    SECRET_VALUE=$(aws secretsmanager get-secret-value \
        --secret-id "$SECRET_NAME" \
        --query "SecretString" \
        --output text 2>/dev/null || echo "{}")
    
    if [[ -n "$SECRET_VALUE" ]] && [[ "$SECRET_VALUE" != "{}" ]]; then
        CLIENT_COUNT=$(echo "$SECRET_VALUE" | jq -r '.clients | length' 2>/dev/null || echo "0")
        VERSION=$(echo "$SECRET_VALUE" | jq -r '.version' 2>/dev/null || echo "Unknown")
        
        log_info "  Version: $VERSION"
        log_info "  Configured clients: $CLIENT_COUNT"
    fi
else
    log_error "IP whitelist secret not found: $SECRET_NAME"
fi

# ========== 9. Connectivity Tests ==========

section_header "9. Connectivity Tests"

# Test API health endpoint (if API exists)
if [[ -n "$API_ENDPOINT" ]] && [[ "$API_ENDPOINT" != "None" ]]; then
    log_info "Testing API health endpoint..."
    
    HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        "${API_ENDPOINT}/health" 2>/dev/null || echo "000")
    
    if [[ "$HEALTH_RESPONSE" == "200" ]]; then
        log_success "Health endpoint accessible (HTTP 200)"
    else
        log_warning "Health endpoint returned HTTP $HEALTH_RESPONSE"
    fi
    
    # Test API with key (if we have example)
    log_info "API endpoint ready for testing with API key:"
    log_info "  curl -H 'x-api-key: YOUR_KEY' ${API_ENDPOINT}/api"
fi

# Test Lambda connectivity (via invoke)
if [[ "$LAMBDA_EXISTS" != "None" ]]; then
    log_info "Testing Lambda invocation..."
    
    INVOKE_RESULT=$(aws lambda invoke \
        --function-name "$LAMBDA_FUNCTION" \
        --payload '{"test": true}' \
        /tmp/lambda-response.json 2>&1)
    
    if [[ $? -eq 0 ]]; then
        log_success "Lambda invocation successful"
        rm -f /tmp/lambda-response.json
    else
        log_error "Lambda invocation failed"
    fi
fi

# ========== 10. Cost Monitoring ==========

section_header "10. Cost Monitoring"

# Check budget alerts
BUDGET_NAME="${PROJECT_NAME}-${ENV}-monthly"
BUDGET_EXISTS=$(aws budgets describe-budget \
    --account-id "$ACCOUNT_ID" \
    --budget-name "$BUDGET_NAME" \
    --query "Budget.BudgetName" \
    --output text 2>/dev/null || echo "None")

if [[ "$BUDGET_EXISTS" == "$BUDGET_NAME" ]]; then
    BUDGET_LIMIT=$(aws budgets describe-budget \
        --account-id "$ACCOUNT_ID" \
        --budget-name "$BUDGET_NAME" \
        --query "Budget.BudgetLimit.Amount" \
        --output text 2>/dev/null || echo "0")
    
    log_success "Budget alert configured: \$$BUDGET_LIMIT USD/month"
else
    log_warning "Budget alert not found: $BUDGET_NAME"
fi

# ========== Summary ==========

section_header "Validation Summary"

echo
echo "Environment: $ENV"
echo "Total checks: $TOTAL_CHECKS"
echo -e "Passed: ${GREEN}$PASSED_CHECKS${NC}"
echo -e "Failed: ${RED}$FAILED_CHECKS${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo

if [[ $FAILED_CHECKS -eq 0 ]]; then
    echo -e "${GREEN}✓ All critical checks passed!${NC}"
    echo "The Lambda API infrastructure Phase 1 is properly deployed."
    exit 0
else
    echo -e "${RED}✗ Some checks failed.${NC}"
    echo "Please review the errors above and ensure all components are deployed."
    exit 1
fi
