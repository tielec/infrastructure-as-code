#!/bin/bash
# テスト名: Dockerイメージ存在確認スクリプト
# 目的: AMI起動後に期待されるDockerイメージがすべて存在することを確認
# 使用方法: ./test_docker_images.sh <instance-id>

set -euo pipefail

# カラー出力用の定数
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# 引数チェック
if [ $# -ne 1 ]; then
  echo "Usage: $0 <instance-id>"
  echo "Example: $0 i-0123456789abcdef0"
  exit 1
fi

INSTANCE_ID=$1

# 期待されるDockerイメージリスト（要件定義書セクション2に基づく）
EXPECTED_IMAGES=(
  "python:3.11-slim"
  "node:18-slim"
  "rust:1.76-slim"
  "rust:slim"
  "amazon/aws-cli:latest"
  "pulumi/pulumi:latest"
  "ubuntu:22.04"
  "nikolaik/python-nodejs:python3.11-nodejs20"
)

readonly TOTAL_EXPECTED=${#EXPECTED_IMAGES[@]}

# 結果格納用変数
declare -a images_found=()
declare -a missing_images=()

echo "===== Docker Images Verification Test ====="
echo "Instance ID: ${INSTANCE_ID}"
echo "Expected images: ${TOTAL_EXPECTED}"
echo ""

# SSM Session Managerでdocker imagesコマンドを実行
echo "Fetching Docker images from instance via SSM..."
DOCKER_IMAGES_OUTPUT=$(aws ssm send-command \
  --instance-ids "${INSTANCE_ID}" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["docker images --format \"{{.Repository}}:{{.Tag}}\""]' \
  --output text \
  --query 'Command.CommandId')

# コマンド実行完了を待機
echo "Waiting for SSM command to complete..."
sleep 5

# コマンド出力を取得
COMMAND_OUTPUT=$(aws ssm get-command-invocation \
  --command-id "${DOCKER_IMAGES_OUTPUT}" \
  --instance-id "${INSTANCE_ID}" \
  --output text \
  --query 'StandardOutputContent')

if [ -z "$COMMAND_OUTPUT" ]; then
  echo -e "${RED}ERROR: Failed to retrieve Docker images from instance${NC}"
  exit 1
fi

echo ""
echo "Docker images on instance:"
echo "----------------------------"
echo "$COMMAND_OUTPUT"
echo "----------------------------"
echo ""

# 各イメージの存在確認
echo "Verifying expected images..."
for expected_image in "${EXPECTED_IMAGES[@]}"; do
  if echo "$COMMAND_OUTPUT" | grep -q "^${expected_image}$"; then
    images_found+=("$expected_image")
    echo -e "${GREEN}✓${NC} Found: $expected_image"
  else
    missing_images+=("$expected_image")
    echo -e "${RED}✗${NC} Missing: $expected_image"
  fi
done

echo ""

# アーキテクチャ情報を取得（オプション）
ARCH_OUTPUT=$(aws ssm send-command \
  --instance-ids "${INSTANCE_ID}" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["uname -m"]' \
  --output text \
  --query 'Command.CommandId')

sleep 3

ARCHITECTURE=$(aws ssm get-command-invocation \
  --command-id "${ARCH_OUTPUT}" \
  --instance-id "${INSTANCE_ID}" \
  --output text \
  --query 'StandardOutputContent' | tr -d '\n')

# JSON形式で結果を出力
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
SUCCESS="false"
if [ ${#missing_images[@]} -eq 0 ]; then
  SUCCESS="true"
fi

# JSON出力生成
cat <<EOF
{
  "total_expected": ${TOTAL_EXPECTED},
  "total_found": ${#images_found[@]},
  "missing_images": [
EOF

# missing_imagesの配列を出力
if [ ${#missing_images[@]} -gt 0 ]; then
  for i in "${!missing_images[@]}"; do
    printf '    "%s"' "${missing_images[$i]}"
    if [ $i -lt $((${#missing_images[@]} - 1)) ]; then
      echo ","
    else
      echo ""
    fi
  done
else
  # 空配列の場合
  :
fi

cat <<EOF
  ],
  "success": ${SUCCESS},
  "timestamp": "${TIMESTAMP}",
  "architecture": "${ARCHITECTURE}",
  "instance_id": "${INSTANCE_ID}",
  "images_found": [
EOF

# images_foundの配列を出力
for i in "${!images_found[@]}"; do
  printf '    "%s"' "${images_found[$i]}"
  if [ $i -lt $((${#images_found[@]} - 1)) ]; then
    echo ","
  else
    echo ""
  fi
done

cat <<EOF
  ]
}
EOF

# 終了コード
if [ "$SUCCESS" = "true" ]; then
  echo ""
  echo -e "${GREEN}===== Test PASSED: All expected images found =====${NC}"
  exit 0
else
  echo ""
  echo -e "${RED}===== Test FAILED: ${#missing_images[@]} image(s) missing =====${NC}"
  exit 1
fi
