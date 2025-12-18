#!/bin/bash
# ============================================================================
# test-dns-resolution.sh
#
# Issue #497: VPC内部DNS解決のインテグレーションテスト
# Route 53プライベートホストゾーンでjenkins.internalが正しく解決されることを確認
#
# Usage: ./test-dns-resolution.sh
#
# Prerequisites:
#   - VPC内部のインスタンスから実行すること
#   - dig, nslookupコマンドが利用可能であること
# ============================================================================

set -euo pipefail

# 設定
INTERNAL_HOSTNAME="jenkins.internal"
PRIVATE_IP_REGEX="^(10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|192\.168\.)"

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
echo "  DNS Resolution Integration Test"
echo "  Issue #497: VPC Internal DNS Resolution"
echo "============================================================"
echo ""
echo "Hostname: ${INTERNAL_HOSTNAME}"
echo "Date: $(date)"
echo ""

# Test 1: nslookup テスト
echo "------------------------------------------------------------"
echo "Test 1: nslookup resolution"
echo "------------------------------------------------------------"

if command -v nslookup &> /dev/null; then
    if nslookup "${INTERNAL_HOSTNAME}" &> /dev/null; then
        test_pass "nslookup ${INTERNAL_HOSTNAME} succeeded"
        echo ""
        nslookup "${INTERNAL_HOSTNAME}"
    else
        test_fail "nslookup ${INTERNAL_HOSTNAME} failed"
    fi
else
    log_warn "nslookup command not found, skipping"
fi

echo ""

# Test 2: dig テスト
echo "------------------------------------------------------------"
echo "Test 2: dig resolution"
echo "------------------------------------------------------------"

if command -v dig &> /dev/null; then
    RESOLVED_IPS=$(dig +short "${INTERNAL_HOSTNAME}" 2>/dev/null || echo "")

    if [ -n "${RESOLVED_IPS}" ]; then
        test_pass "dig +short ${INTERNAL_HOSTNAME} succeeded"
        echo "Resolved IPs:"
        echo "${RESOLVED_IPS}"
    else
        test_fail "dig +short ${INTERNAL_HOSTNAME} returned no results"
    fi
else
    log_warn "dig command not found, skipping"
fi

echo ""

# Test 3: プライベートIP確認
echo "------------------------------------------------------------"
echo "Test 3: Private IP verification"
echo "------------------------------------------------------------"

if [ -n "${RESOLVED_IPS:-}" ]; then
    ALL_PRIVATE=true

    while IFS= read -r ip; do
        if [ -z "${ip}" ]; then
            continue
        fi

        if [[ "${ip}" =~ ${PRIVATE_IP_REGEX} ]]; then
            log_info "IP ${ip} is a private IP address"
        else
            log_warn "IP ${ip} may NOT be a private IP address"
            ALL_PRIVATE=false
        fi
    done <<< "${RESOLVED_IPS}"

    if [ "${ALL_PRIVATE}" = true ]; then
        test_pass "All resolved IPs are private addresses"
    else
        test_fail "Some resolved IPs may not be private addresses"
    fi
else
    test_fail "No IPs to verify"
fi

echo ""

# Test 4: ALB ENI確認（複数IP）
echo "------------------------------------------------------------"
echo "Test 4: ALB ENI verification (multiple IPs expected)"
echo "------------------------------------------------------------"

if [ -n "${RESOLVED_IPS:-}" ]; then
    IP_COUNT=$(echo "${RESOLVED_IPS}" | grep -c . || echo "0")

    if [ "${IP_COUNT}" -ge 1 ]; then
        log_info "Resolved ${IP_COUNT} IP address(es)"
        if [ "${IP_COUNT}" -ge 2 ]; then
            test_pass "Multiple IPs returned (ALB with multiple ENIs)"
        else
            log_info "Single IP returned (ALB may have single ENI in single AZ)"
            test_pass "At least one IP returned"
        fi
    else
        test_fail "No IP addresses resolved"
    fi
fi

echo ""

# Test 5: 外部からの解決不可確認（情報のみ）
echo "------------------------------------------------------------"
echo "Test 5: External resolution check (informational)"
echo "------------------------------------------------------------"

log_info "Private hosted zones are only resolvable within the associated VPC"
log_info "This test should be run from within the VPC"
log_info "External resolution of ${INTERNAL_HOSTNAME} should fail from outside the VPC"

echo ""

# サマリー出力
echo "============================================================"
echo "  Test Summary"
echo "============================================================"
echo ""
echo "Tests Passed: ${TESTS_PASSED}"
echo "Tests Failed: ${TESTS_FAILED}"
echo ""

if [ "${TESTS_FAILED}" -eq 0 ]; then
    log_success "All tests passed!"
    exit 0
else
    log_error "${TESTS_FAILED} test(s) failed"
    exit 1
fi
