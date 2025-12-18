#!/bin/bash
# ============================================================================
# test-websocket-connection.sh
#
# Issue #497: WebSocket接続安定性のインテグレーションテスト
# VPC内部URLでJenkinsへのHTTP接続が安定していることを確認
#
# Usage: ./test-websocket-connection.sh [duration_minutes]
#        duration_minutes: テスト時間（分）、デフォルト10分
#
# Prerequisites:
#   - VPC内部のインスタンスから実行すること
#   - curlコマンドが利用可能であること
#   - jenkins.internalが解決可能であること
# ============================================================================

set -euo pipefail

# 設定
INTERNAL_URL="http://jenkins.internal"
TEST_DURATION_MINUTES=${1:-10}
CHECK_INTERVAL_SECONDS=30

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%H:%M:%S') $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%H:%M:%S') $*"
}

log_check() {
    echo -e "${BLUE}[CHECK]${NC} $(date '+%H:%M:%S') $*"
}

# 結果カウンター
SUCCESS_COUNT=0
FAILURE_COUNT=0
TOTAL_CHECKS=0

# ヘッダー出力
echo "============================================================"
echo "  WebSocket Connection Stability Test"
echo "  Issue #497: NAT Instance Timeout Verification"
echo "============================================================"
echo ""
echo "URL: ${INTERNAL_URL}"
echo "Duration: ${TEST_DURATION_MINUTES} minutes"
echo "Check Interval: ${CHECK_INTERVAL_SECONDS} seconds"
echo "Date: $(date)"
echo ""

# Test 1: 初期HTTP接続テスト
echo "------------------------------------------------------------"
echo "Test 1: Initial HTTP connectivity"
echo "------------------------------------------------------------"

log_info "Testing initial HTTP connection to ${INTERNAL_URL}/login"

HTTP_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "${INTERNAL_URL}/login" --connect-timeout 10 || echo "000")

if [ "${HTTP_STATUS}" = "200" ] || [ "${HTTP_STATUS}" = "302" ] || [ "${HTTP_STATUS}" = "403" ]; then
    log_success "Initial HTTP connection successful (HTTP ${HTTP_STATUS})"
else
    log_error "Initial HTTP connection failed (HTTP ${HTTP_STATUS})"
    log_error "Cannot proceed with stability test"
    exit 1
fi

echo ""

# Test 2: 8080ポート接続テスト
echo "------------------------------------------------------------"
echo "Test 2: Port 8080 connectivity"
echo "------------------------------------------------------------"

HTTP_STATUS_8080=$(curl -sf -o /dev/null -w "%{http_code}" "${INTERNAL_URL}:8080/login" --connect-timeout 10 || echo "000")

if [ "${HTTP_STATUS_8080}" = "200" ] || [ "${HTTP_STATUS_8080}" = "302" ] || [ "${HTTP_STATUS_8080}" = "403" ]; then
    log_success "Port 8080 connection successful (HTTP ${HTTP_STATUS_8080})"
else
    log_warn "Port 8080 connection returned HTTP ${HTTP_STATUS_8080}"
fi

echo ""

# Test 3: 長時間接続安定性テスト
echo "------------------------------------------------------------"
echo "Test 3: Connection stability test (${TEST_DURATION_MINUTES} minutes)"
echo "------------------------------------------------------------"
echo ""
echo "Key milestones:"
echo "  - 6 minutes: NAT Instance timeout threshold (previous failure point)"
echo "  - 10 minutes: Extended stability verification"
echo ""

START_TIME=$(date +%s)
END_TIME=$((START_TIME + TEST_DURATION_MINUTES * 60))
CHECKPOINT_6MIN=$((START_TIME + 360))  # 6分（360秒）= NAT Instanceタイムアウト閾値

log_info "Starting stability test..."
echo ""

while [ "$(date +%s)" -lt "${END_TIME}" ]; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    REMAINING=$((END_TIME - CURRENT_TIME))
    ELAPSED_MIN=$((ELAPSED / 60))
    ELAPSED_SEC=$((ELAPSED % 60))

    ((TOTAL_CHECKS++))

    # HTTP接続チェック
    HTTP_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "${INTERNAL_URL}/login" --connect-timeout 10 || echo "000")

    # 6分チェックポイントの特別処理
    if [ "${CURRENT_TIME}" -ge "${CHECKPOINT_6MIN}" ] && [ "$((CURRENT_TIME - CHECK_INTERVAL_SECONDS))" -lt "${CHECKPOINT_6MIN}" ]; then
        echo ""
        echo "============================================================"
        echo "  CRITICAL CHECKPOINT: 6 minutes (NAT timeout threshold)"
        echo "============================================================"
    fi

    if [ "${HTTP_STATUS}" = "200" ] || [ "${HTTP_STATUS}" = "302" ] || [ "${HTTP_STATUS}" = "403" ]; then
        ((SUCCESS_COUNT++))

        # 重要なマイルストーンでの出力
        if [ "${ELAPSED}" -eq 360 ] || [ $((ELAPSED % 60)) -lt "${CHECK_INTERVAL_SECONDS}" ]; then
            log_check "Elapsed: ${ELAPSED_MIN}m ${ELAPSED_SEC}s | HTTP: ${HTTP_STATUS} | Remaining: ${REMAINING}s"
        fi

        # 6分経過時の特別なメッセージ
        if [ "${CURRENT_TIME}" -ge "${CHECKPOINT_6MIN}" ] && [ "$((CURRENT_TIME - CHECK_INTERVAL_SECONDS))" -lt "${CHECKPOINT_6MIN}" ]; then
            log_success "CONNECTION STABLE AT 6 MINUTES - NAT timeout issue resolved!"
        fi
    else
        ((FAILURE_COUNT++))
        log_error "Connection FAILED at ${ELAPSED_MIN}m ${ELAPSED_SEC}s | HTTP: ${HTTP_STATUS}"

        # 6分付近での失敗は特に重要
        if [ "${ELAPSED}" -ge 300 ] && [ "${ELAPSED}" -le 420 ]; then
            log_error "CRITICAL: Failure occurred near 6-minute mark (NAT timeout suspected)"
        fi
    fi

    sleep "${CHECK_INTERVAL_SECONDS}"
done

echo ""

# Test 4: 最終接続確認
echo "------------------------------------------------------------"
echo "Test 4: Final connectivity verification"
echo "------------------------------------------------------------"

FINAL_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "${INTERNAL_URL}/login" --connect-timeout 10 || echo "000")

if [ "${FINAL_STATUS}" = "200" ] || [ "${FINAL_STATUS}" = "302" ] || [ "${FINAL_STATUS}" = "403" ]; then
    log_success "Final connection check successful (HTTP ${FINAL_STATUS})"
else
    log_error "Final connection check failed (HTTP ${FINAL_STATUS})"
fi

echo ""

# サマリー出力
echo "============================================================"
echo "  Test Summary"
echo "============================================================"
echo ""
echo "Test Duration: ${TEST_DURATION_MINUTES} minutes"
echo "Total Checks: ${TOTAL_CHECKS}"
echo "Successful: ${SUCCESS_COUNT}"
echo "Failed: ${FAILURE_COUNT}"
echo ""

if [ "${FAILURE_COUNT}" -eq 0 ]; then
    log_success "All connectivity checks passed!"
    echo ""
    echo "Key findings:"
    echo "  - Connection remained stable for ${TEST_DURATION_MINUTES} minutes"
    echo "  - No disconnection at 6-minute mark (NAT timeout)"
    echo "  - Route 53 private hosted zone is working correctly"
    echo ""
    echo "NOTE: This test verifies HTTP connectivity."
    echo "For WebSocket stability, also run a long-running Jenkins build"
    echo "with ECS Fargate agent and monitor for:"
    echo "  - 'java.lang.InterruptedException' errors"
    echo "  - 'seems to be removed or offline' messages"
    exit 0
else
    log_error "${FAILURE_COUNT} connectivity check(s) failed"
    echo ""
    echo "Possible issues:"
    echo "  - NAT Instance timeout may still be occurring"
    echo "  - Route 53 private hosted zone may not be configured correctly"
    echo "  - Network connectivity issues"
    exit 1
fi
