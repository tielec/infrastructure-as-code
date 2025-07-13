#!/bin/bash
# verify-installation.sh - ブートストラップ環境のインストール状況確認スクリプト

# カラー定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# チェックマーク
CHECK_MARK="✓"
CROSS_MARK="✗"

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}    Bootstrap Environment Verification       ${NC}"
echo -e "${BLUE}=============================================${NC}"
echo

# 環境変数を読み込み
if [ -f /etc/profile.d/bootstrap-env.sh ]; then
    source /etc/profile.d/bootstrap-env.sh
fi
source ~/.bashrc 2>/dev/null || true

# システム情報
echo -e "${YELLOW}=== System Information ===${NC}"
echo "Architecture: $(uname -m)"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '"')"
echo "Kernel: $(uname -r)"
echo

# PATH環境変数
echo -e "${YELLOW}=== PATH Environment ===${NC}"
echo "PATH: $PATH"
echo

# Python環境
echo -e "${YELLOW}=== Python Environment ===${NC}"
if command -v python3 &> /dev/null; then
    echo -e "${GREEN}${CHECK_MARK}${NC} Python3: $(python3 --version 2>&1)"
    echo "  Location: $(which python3)"
else
    echo -e "${RED}${CROSS_MARK}${NC} Python3: Not installed"
fi

if command -v pip3 &> /dev/null; then
    echo -e "${GREEN}${CHECK_MARK}${NC} Pip3: $(pip3 --version 2>&1)"
else
    echo -e "${RED}${CROSS_MARK}${NC} Pip3: Not installed"
fi

# User pip
if python3 -m pip --version &> /dev/null; then
    echo -e "${GREEN}${CHECK_MARK}${NC} User pip: $(python3 -m pip --version 2>&1)"
else
    echo -e "${YELLOW}!${NC} User pip: Not available"
fi
echo

# インストールされたツール
echo -e "${YELLOW}=== Installed Tools ===${NC}"

# Node.js
if command -v node &> /dev/null; then
    echo -e "${GREEN}${CHECK_MARK}${NC} Node.js: $(node --version)"
    echo "  npm: $(npm --version 2>/dev/null || echo 'Not installed')"
else
    echo -e "${RED}${CROSS_MARK}${NC} Node.js: Not installed"
fi

# AWS CLI
if command -v aws &> /dev/null; then
    echo -e "${GREEN}${CHECK_MARK}${NC} AWS CLI: $(aws --version)"
else
    echo -e "${RED}${CROSS_MARK}${NC} AWS CLI: Not installed"
fi

# Ansible
if command -v ansible &> /dev/null; then
    echo -e "${GREEN}${CHECK_MARK}${NC} Ansible: $(ansible --version 2>&1 | head -n 1)"
    echo "  Location: $(which ansible)"
    
    # ansible-core version
    if python3 -m pip show ansible-core &> /dev/null; then
        core_version=$(python3 -m pip show ansible-core | grep Version | awk '{print $2}')
        echo "  ansible-core: $core_version"
    fi
else
    echo -e "${RED}${CROSS_MARK}${NC} Ansible: Not installed"
fi

# Pulumi
if command -v pulumi &> /dev/null; then
    echo -e "${GREEN}${CHECK_MARK}${NC} Pulumi: $(pulumi version 2>&1)"
else
    echo -e "${RED}${CROSS_MARK}${NC} Pulumi: Not installed"
fi

# Git
if command -v git &> /dev/null; then
    echo -e "${GREEN}${CHECK_MARK}${NC} Git: $(git --version)"
else
    echo -e "${RED}${CROSS_MARK}${NC} Git: Not installed"
fi

# Java
if command -v java &> /dev/null; then
    echo -e "${GREEN}${CHECK_MARK}${NC} Java: $(java -version 2>&1 | head -n 1)"
    echo "  JAVA_HOME: ${JAVA_HOME:-Not set}"
else
    echo -e "${RED}${CROSS_MARK}${NC} Java: Not installed"
fi

# Docker
if command -v docker &> /dev/null; then
    echo -e "${GREEN}${CHECK_MARK}${NC} Docker: $(docker --version 2>&1)"
    
    # Docker daemon status
    if docker ps &> /dev/null; then
        echo -e "  ${GREEN}${CHECK_MARK}${NC} Docker daemon is running"
    else
        echo -e "  ${YELLOW}!${NC} Docker daemon is not running or no permission"
    fi
else
    echo -e "${YELLOW}!${NC} Docker: Not installed (optional)"
fi
echo

# Python AWS Libraries
echo -e "${YELLOW}=== Python AWS Libraries ===${NC}"
for lib in boto3 botocore jmespath; do
    if python3 -m pip show $lib &> /dev/null; then
        version=$(python3 -m pip show $lib | grep Version | awk '{print $2}')
        echo -e "${GREEN}${CHECK_MARK}${NC} $lib: $version"
    else
        echo -e "${RED}${CROSS_MARK}${NC} $lib: Not installed"
    fi
done
echo

# Ansible Collections
echo -e "${YELLOW}=== Ansible Collections ===${NC}"
if command -v ansible-galaxy &> /dev/null; then
    collections=$(ansible-galaxy collection list 2>/dev/null | grep -E "(amazon\.aws|community\.aws|community\.general|ansible\.posix|community\.docker)" || true)
    
    if [ -n "$collections" ]; then
        echo "$collections" | while read line; do
            echo -e "${GREEN}${CHECK_MARK}${NC} $line"
        done
    else
        echo -e "${YELLOW}!${NC} No AWS/required collections found"
        echo -e "${YELLOW}  Run: ansible-galaxy collection install amazon.aws community.aws community.general ansible.posix${NC}"
    fi
else
    echo -e "${RED}${CROSS_MARK}${NC} ansible-galaxy command not found"
fi
echo

# AWS Credentials
echo -e "${YELLOW}=== AWS Credentials ===${NC}"
if aws sts get-caller-identity &> /dev/null; then
    echo -e "${GREEN}${CHECK_MARK}${NC} AWS credentials are configured"
    aws sts get-caller-identity --output table
else
    echo -e "${YELLOW}!${NC} AWS credentials not configured"
    echo "  This is normal if using IAM instance role"
fi
echo

# Pulumi Backend
echo -e "${YELLOW}=== Pulumi Backend ===${NC}"
if [ -n "$PULUMI_ACCESS_TOKEN" ]; then
    echo -e "${GREEN}${CHECK_MARK}${NC} PULUMI_ACCESS_TOKEN is set"
else
    echo -e "${YELLOW}!${NC} PULUMI_ACCESS_TOKEN is not set"
fi

# Check for S3 backend parameter
if aws ssm get-parameter --name /bootstrap/pulumi/s3bucket-name &> /dev/null; then
    bucket_name=$(aws ssm get-parameter --name /bootstrap/pulumi/s3bucket-name --query 'Parameter.Value' --output text)
    echo -e "${GREEN}${CHECK_MARK}${NC} Pulumi S3 backend: s3://$bucket_name"
else
    echo -e "${YELLOW}!${NC} Pulumi S3 backend parameter not found in SSM"
fi
echo

# Summary
echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}                 Summary                     ${NC}"
echo -e "${BLUE}=============================================${NC}"

# Count installed tools
total_tools=9
installed_tools=0
critical_missing=""

for tool in python3 aws ansible pulumi git java node; do
    if command -v $tool &> /dev/null; then
        installed_tools=$((installed_tools + 1))
    else
        critical_missing="$critical_missing $tool"
    fi
done

# Docker is optional
if command -v docker &> /dev/null; then
    installed_tools=$((installed_tools + 1))
fi

# Check for ansible-galaxy separately
if command -v ansible-galaxy &> /dev/null; then
    installed_tools=$((installed_tools + 1))
fi

echo -e "Installed tools: ${installed_tools}/${total_tools}"

if [ -n "$critical_missing" ]; then
    echo -e "${RED}Missing critical tools:${critical_missing}${NC}"
fi

# Check for Ansible collections
if command -v ansible-galaxy &> /dev/null; then
    collection_count=$(ansible-galaxy collection list 2>/dev/null | grep -cE "(amazon\.aws|community\.aws)" || echo "0")
    if [ "$collection_count" -eq "0" ]; then
        echo -e "${YELLOW}Warning: AWS Ansible collections not installed${NC}"
        echo -e "Run: ${GREEN}ansible-galaxy collection install amazon.aws community.aws${NC}"
    fi
fi

echo
echo -e "${BLUE}=============================================${NC}"