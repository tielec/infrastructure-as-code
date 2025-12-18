#!/bin/bash
# ============================================================================
# test-casc-internal-url-config.sh
#
# Issue #497: JENKINS_INTERNAL_URL設定のインテグレーションテスト
# application-configure-with-casc.shがJENKINS_INTERNAL_URLを正しく
# 取得・設定・エクスポートすることを確認
#
# Usage: ./test-casc-internal-url-config.sh
#
# Prerequisites:
#   - 対象ファイルが存在すること
#   - bashコマンドが利用可能であること
#
# Test Scenarios:
#   IT-04: Bashスクリプト設定テスト
#   IT-05: フォールバック動作テスト
# ============================================================================

set -euo pipefail

# パス設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
CONFIGURE_SCRIPT="${ROOT_DIR}/scripts/jenkins/shell/application-configure-with-casc.sh"
TEMPLATE_FILE="${ROOT_DIR}/scripts/jenkins/casc/jenkins.yaml.template"

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ログ関数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

# テスト結果カウンター
TESTS_PASSED=0
TESTS_FAILED=0

# テスト結果記録関数
test_pass() {
    log_success "$1"
    ((TESTS_PASSED++))
}

test_fail() {
    log_error "$1"
    ((TESTS_FAILED++))
}

# ヘッダー出力
echo "============================================================"
echo "  JENKINS_INTERNAL_URL Configuration Test"
echo "  Issue #497: VPC Internal URL Configuration"
echo "============================================================"
echo ""
echo "Date: $(date)"
echo ""

# Test 1: 設定スクリプトの存在確認
echo "------------------------------------------------------------"
echo "Test 1: Configuration script existence"
echo "------------------------------------------------------------"

if [ -f "${CONFIGURE_SCRIPT}" ]; then
    test_pass "Configuration script exists: ${CONFIGURE_SCRIPT}"
else
    test_fail "Configuration script not found: ${CONFIGURE_SCRIPT}"
    exit 1
fi

echo ""

# Test 2: JENKINS_INTERNAL_URL SSMパラメータ取得コードの存在確認
echo "------------------------------------------------------------"
echo "Test 2: SSM parameter retrieval code for jenkins-internal-url"
echo "------------------------------------------------------------"

if grep -q "jenkins-internal-url" "${CONFIGURE_SCRIPT}"; then
    test_pass "SSM parameter 'jenkins-internal-url' retrieval code found"

    # 詳細確認: SSMパラメータパスの確認
    if grep -q '/loadbalancer/jenkins-internal-url' "${CONFIGURE_SCRIPT}"; then
        log_info "  - Correct SSM path pattern found"
    else
        log_warn "  - SSM path pattern may not match expected format"
    fi
else
    test_fail "SSM parameter 'jenkins-internal-url' retrieval code NOT found"
fi

echo ""

# Test 3: setup_jenkins_internal_url関数の存在確認
echo "------------------------------------------------------------"
echo "Test 3: setup_jenkins_internal_url function existence"
echo "------------------------------------------------------------"

if grep -q "setup_jenkins_internal_url" "${CONFIGURE_SCRIPT}"; then
    test_pass "setup_jenkins_internal_url function found"

    # 詳細確認: フォールバックロジックの存在
    if grep -A 10 "setup_jenkins_internal_url" "${CONFIGURE_SCRIPT}" | grep -q "JENKINS_URL\|setup_jenkins_url"; then
        log_info "  - Fallback logic appears to be implemented"
    else
        log_warn "  - Fallback logic may not be implemented"
    fi
else
    test_fail "setup_jenkins_internal_url function NOT found"
fi

echo ""

# Test 4: JENKINS_INTERNAL_URL環境変数のエクスポート確認
echo "------------------------------------------------------------"
echo "Test 4: JENKINS_INTERNAL_URL export statement"
echo "------------------------------------------------------------"

if grep -q "export JENKINS_INTERNAL_URL" "${CONFIGURE_SCRIPT}"; then
    test_pass "JENKINS_INTERNAL_URL export statement found"
else
    test_fail "JENKINS_INTERNAL_URL export statement NOT found"
fi

echo ""

# Test 5: envsubst変数リストにJENKINS_INTERNAL_URLが含まれているか確認
echo "------------------------------------------------------------"
echo "Test 5: envsubst includes JENKINS_INTERNAL_URL"
echo "------------------------------------------------------------"

if grep -E "envsubst.*JENKINS_INTERNAL_URL" "${CONFIGURE_SCRIPT}"; then
    test_pass "JENKINS_INTERNAL_URL is included in envsubst command"
else
    test_fail "JENKINS_INTERNAL_URL is NOT included in envsubst command"
fi

echo ""

# Test 6: JCasCテンプレートの確認
echo "------------------------------------------------------------"
echo "Test 6: JCasC template configuration"
echo "------------------------------------------------------------"

if [ -f "${TEMPLATE_FILE}" ]; then
    log_info "Template file found: ${TEMPLATE_FILE}"

    # ECS設定でJENKINS_INTERNAL_URLを使用しているか確認
    if grep -A 5 "ecs:" "${TEMPLATE_FILE}" | grep -q 'jenkinsUrl.*JENKINS_INTERNAL_URL'; then
        test_pass "ECS cloud jenkinsUrl uses JENKINS_INTERNAL_URL"
    elif grep -q 'jenkinsUrl.*JENKINS_INTERNAL_URL' "${TEMPLATE_FILE}"; then
        test_pass "jenkinsUrl uses JENKINS_INTERNAL_URL (found in template)"
    else
        test_fail "ECS cloud jenkinsUrl does NOT use JENKINS_INTERNAL_URL"
        log_info "  Checking current jenkinsUrl configuration..."
        grep "jenkinsUrl" "${TEMPLATE_FILE}" || log_warn "  No jenkinsUrl found in template"
    fi
else
    test_fail "Template file not found: ${TEMPLATE_FILE}"
fi

echo ""

# Test 7: フォールバック動作のテスト（静的解析）
echo "------------------------------------------------------------"
echo "Test 7: Fallback logic static analysis"
echo "------------------------------------------------------------"

# フォールバックパターンの確認
FALLBACK_PATTERNS=(
    'ALB_INTERNAL_DNS.*None'
    'setup_jenkins_url'
    'JENKINS_URL'
)

FALLBACK_FOUND=0
for pattern in "${FALLBACK_PATTERNS[@]}"; do
    if grep -q "${pattern}" "${CONFIGURE_SCRIPT}"; then
        log_info "  - Pattern '${pattern}' found (potential fallback logic)"
        ((FALLBACK_FOUND++))
    fi
done

if [ "${FALLBACK_FOUND}" -ge 2 ]; then
    test_pass "Fallback logic patterns detected (${FALLBACK_FOUND} patterns)"
else
    test_fail "Insufficient fallback logic patterns found (${FALLBACK_FOUND} patterns)"
fi

echo ""

# Test 8: スクリプト構文チェック
echo "------------------------------------------------------------"
echo "Test 8: Script syntax validation"
echo "------------------------------------------------------------"

if bash -n "${CONFIGURE_SCRIPT}" 2>/dev/null; then
    test_pass "Script syntax is valid"
else
    test_fail "Script has syntax errors"
fi

echo ""

# Test 9: テンプレート変数の整合性チェック
echo "------------------------------------------------------------"
echo "Test 9: Template variable consistency"
echo "------------------------------------------------------------"

if [ -f "${TEMPLATE_FILE}" ]; then
    # JENKINS_INTERNAL_URL変数がテンプレートに存在するか
    if grep -q '\${JENKINS_INTERNAL_URL}' "${TEMPLATE_FILE}"; then
        test_pass "JENKINS_INTERNAL_URL variable found in template"
    else
        test_fail "JENKINS_INTERNAL_URL variable NOT found in template"
    fi

    # JENKINS_URL変数も維持されているか（外部アクセス用）
    if grep -q '\${JENKINS_URL}' "${TEMPLATE_FILE}"; then
        log_info "  - JENKINS_URL variable also exists (for external access)"
    fi
else
    log_warn "Cannot check template - file not found"
fi

echo ""

# Test 10: JCasCテンプレートのレンダリングテスト
echo "------------------------------------------------------------"
echo "Test 10: JCasC template rendering test"
echo "------------------------------------------------------------"

if [ -f "${TEMPLATE_FILE}" ]; then
    TEMP_RENDER="$(mktemp)"

    # テスト用の環境変数を設定
    export JENKINS_URL="http://jenkins.example.com/"
    export JENKINS_INTERNAL_URL="http://jenkins.internal/"
    export EC2_FLEET_ID="fleet-test"
    export WORKTERMINAL_HOST="192.168.1.1"
    export AWS_REGION="ap-northeast-1"
    export AWS_PROD_ACCOUNT_IDS="123456789012"
    export AWS_DEV_ACCOUNT_IDS="210987654321"
    export SHARED_LIBRARY_REPO="https://example.com/repo.git"
    export SHARED_LIBRARY_BRANCH="main"
    export SHARED_LIBRARY_PATH="jenkins/jobs/shared/"
    export EC2_IDLE_MINUTES="10"
    export EC2_MIN_SIZE="0"
    export EC2_MAX_SIZE="5"
    export EC2_NUM_EXECUTORS="2"
    export ECS_CLUSTER_ARN="arn:aws:ecs:ap-northeast-1:123456789012:cluster/test"
    export ECS_TASK_DEFINITION_ARN="arn:aws:ecs:ap-northeast-1:123456789012:task-definition/test:1"
    export ECS_EXECUTION_ROLE_ARN="arn:aws:iam::123456789012:role/execution-role"
    export ECS_TASK_ROLE_ARN="arn:aws:iam::123456789012:role/task-role"
    export JENKINS_AGENT_SG_ID="sg-0123456789abcdef0"
    export PRIVATE_SUBNET_A_ID="subnet-aaaaaaaa"
    export PRIVATE_SUBNET_B_ID="subnet-bbbbbbbb"

    # テンプレートをレンダリング
    # shellcheck disable=SC2016
    envsubst '$JENKINS_URL $JENKINS_INTERNAL_URL $EC2_FLEET_ID $WORKTERMINAL_HOST $AWS_REGION $AWS_PROD_ACCOUNT_IDS $AWS_DEV_ACCOUNT_IDS $SHARED_LIBRARY_REPO $SHARED_LIBRARY_BRANCH $SHARED_LIBRARY_PATH $EC2_IDLE_MINUTES $EC2_MIN_SIZE $EC2_MAX_SIZE $EC2_NUM_EXECUTORS $ECS_CLUSTER_ARN $ECS_TASK_DEFINITION_ARN $ECS_EXECUTION_ROLE_ARN $ECS_TASK_ROLE_ARN $JENKINS_AGENT_SG_ID $PRIVATE_SUBNET_A_ID $PRIVATE_SUBNET_B_ID' \
        < "${TEMPLATE_FILE}" > "${TEMP_RENDER}"

    # ECS設定のjenkinsUrlがJENKINS_INTERNAL_URLで置換されているか確認
    if grep -q "http://jenkins.internal/" "${TEMP_RENDER}"; then
        test_pass "Template rendered with JENKINS_INTERNAL_URL value"

        # ECSクラウド設定内に内部URLがあるか詳細確認
        if grep -B 5 "http://jenkins.internal/" "${TEMP_RENDER}" | grep -q "ecs"; then
            log_info "  - Internal URL is in ECS cloud configuration section"
        fi
    else
        test_fail "Template did NOT render with JENKINS_INTERNAL_URL value"
        log_warn "  Checking rendered template..."
        grep "jenkinsUrl" "${TEMP_RENDER}" || log_warn "  No jenkinsUrl found in rendered template"
    fi

    # 外部URL（JENKINS_URL）も維持されているか確認
    if grep -q "http://jenkins.example.com/" "${TEMP_RENDER}"; then
        log_info "  - External URL (JENKINS_URL) is preserved in template"
    fi

    rm -f "${TEMP_RENDER}"
else
    log_warn "Cannot perform rendering test - template file not found"
fi

echo ""

# サマリー出力
echo "============================================================"
echo "  Test Summary"
echo "============================================================"
echo ""
echo "Tests Passed: ${TESTS_PASSED}"
echo "Tests Failed: ${TESTS_FAILED}"
echo ""

# テストシナリオとの対応
echo "Test Scenario Coverage:"
echo "  IT-04 (Bashスクリプト設定テスト): Tests 1-5, 8"
echo "  IT-05 (フォールバック動作テスト): Tests 7"
echo "  Template Configuration: Tests 6, 9, 10"
echo ""

if [ "${TESTS_FAILED}" -eq 0 ]; then
    log_success "All tests passed!"
    echo ""
    echo "Note: This test validates static configuration."
    echo "For runtime verification, deploy the changes and run:"
    echo "  1. test-dns-resolution.sh (DNS resolution test)"
    echo "  2. test-websocket-connection.sh (connectivity test)"
    echo "  3. Actual Jenkins build with ECS Fargate agent"
    exit 0
else
    log_error "${TESTS_FAILED} test(s) failed"
    echo ""
    echo "Please check the implementation in:"
    echo "  - ${CONFIGURE_SCRIPT}"
    echo "  - ${TEMPLATE_FILE}"
    exit 1
fi
