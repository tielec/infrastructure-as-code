#!/bin/bash
# Jenkins全体設定の統合検証
# SSM経由で実行されることを前提

# エラーハンドリング設定
set -e

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /var/log/jenkins-application-verify.log
}

# エラーハンドラー
error_exit() {
    log "ERROR: $1"
    exit 1
}

log "===== Verifying All Jenkins Configurations ====="

# 環境変数の設定
JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
PROJECT_NAME="${PROJECT_NAME:-jenkins-infra}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
SEED_JOB_NAME="${SEED_JOB_NAME:-seed-job}"

VERIFICATION_RESULTS=()
FAILED_CHECKS=0
TOTAL_CHECKS=0

# 検証関数
check_item() {
    local check_name="$1"
    local check_command="$2"
    local success_msg="$3"
    local failure_msg="$4"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    if eval "$check_command"; then
        log "✓ $check_name: $success_msg"
        VERIFICATION_RESULTS+=("✓ $check_name")
    else
        log "✗ $check_name: $failure_msg"
        VERIFICATION_RESULTS+=("✗ $check_name")
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
}

# 1. Jenkinsサービスの状態確認
log "1. Jenkins Service Status"
check_item "Jenkins Service" \
    "systemctl is-active jenkins >/dev/null 2>&1" \
    "Service is running" \
    "Service is not running"

# 2. Jenkins Webインターフェースの応答確認
log ""
log "2. Jenkins Web Interface"
check_item "Web Interface" \
    "curl -sf http://localhost:8080/login >/dev/null 2>&1" \
    "Responding on port 8080" \
    "Not responding on port 8080"

# 3. 必須プラグインの確認
log ""
log "3. Required Plugins"
REQUIRED_PLUGINS=("git" "workflow-aggregator" "job-dsl" "configuration-as-code" "ec2-fleet")
for plugin in "${REQUIRED_PLUGINS[@]}"; do
    check_item "Plugin: $plugin" \
        "[ -d '${JENKINS_HOME}/plugins/${plugin}' ]" \
        "Installed" \
        "Not installed"
done

# 4. セキュリティ設定の確認
log ""
log "4. Security Configuration"
check_item "CLI User" \
    "[ -d '${JENKINS_HOME}/users/cli-user_'* ]" \
    "Configured" \
    "Not configured"

check_item "Credentials Store" \
    "[ -f '${JENKINS_HOME}/credentials.xml' ]" \
    "Exists" \
    "Not found"

check_item "Security Realm" \
    "grep -q '<securityRealm' '${JENKINS_HOME}/config.xml' 2>/dev/null" \
    "Configured" \
    "Not configured"

# 5. JCasC設定の確認
log ""
log "5. Configuration as Code"
check_item "JCasC Config File" \
    "[ -f '${JENKINS_HOME}/jenkins.yaml' ]" \
    "Present" \
    "Not found"

check_item "JCasC Plugin" \
    "[ -d '${JENKINS_HOME}/plugins/configuration-as-code' ]" \
    "Installed" \
    "Not installed"

# 6. シードジョブの確認
log ""
log "6. Seed Job Configuration"
check_item "Seed Job" \
    "[ -d '${JENKINS_HOME}/jobs/${SEED_JOB_NAME}' ]" \
    "Created" \
    "Not created"

check_item "Seed Job Config" \
    "[ -f '${JENKINS_HOME}/jobs/${SEED_JOB_NAME}/config.xml' ]" \
    "Configured" \
    "Not configured"

# 7. EC2 Fleet設定の確認（JCasC経由）
log ""
log "7. EC2 Fleet Configuration"
if [ -f "${JENKINS_HOME}/jenkins.yaml" ]; then
    check_item "EC2 Fleet Config" \
        "grep -q 'ec2Fleet' '${JENKINS_HOME}/jenkins.yaml' 2>/dev/null" \
        "Found in JCasC" \
        "Not found in JCasC"
else
    log "⚠ EC2 Fleet Config: JCasC file not available for check"
fi

# 8. EFSマウントの確認
log ""
log "8. Storage Configuration"
check_item "EFS Mount" \
    "mount | grep -q '/mnt/efs'" \
    "Mounted" \
    "Not mounted"

check_item "Jenkins Home on EFS" \
    "[ -d '/mnt/efs/jenkins' ]" \
    "Exists" \
    "Not found"

# 9. ログファイルのエラー確認
log ""
log "9. Log File Analysis"
if [ -f "/var/log/jenkins/jenkins.log" ]; then
    ERROR_COUNT=$(grep -c "ERROR\|SEVERE" /var/log/jenkins/jenkins.log 2>/dev/null | tail -100 || echo "0")
    if [ "$ERROR_COUNT" -lt 10 ]; then
        log "✓ Log Errors: Acceptable ($ERROR_COUNT errors in recent logs)"
    else
        log "⚠ Log Errors: High error count ($ERROR_COUNT errors in recent logs)"
    fi
else
    log "⚠ Log File: Jenkins log not found"
fi

# 結果のサマリー
log ""
log "===== Verification Summary ====="
log "Total Checks: $TOTAL_CHECKS"
log "Passed: $((TOTAL_CHECKS - FAILED_CHECKS))"
log "Failed: $FAILED_CHECKS"
log ""

# 詳細結果の表示
log "Detailed Results:"
for result in "${VERIFICATION_RESULTS[@]}"; do
    log "  $result"
done

# SSMパラメータに結果を記録
INSTANCE_ID=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" | xargs -I {} curl -s -H "X-aws-ec2-metadata-token: {}" http://169.254.169.254/latest/meta-data/instance-id)
REGION=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" | xargs -I {} curl -s -H "X-aws-ec2-metadata-token: {}" http://169.254.169.254/latest/meta-data/placement/region)

if [ $FAILED_CHECKS -eq 0 ]; then
    STATUS="SUCCESS: All checks passed ($TOTAL_CHECKS/$TOTAL_CHECKS)"
    log ""
    log "✅ $STATUS"
    EXIT_CODE=0
else
    STATUS="WARNING: $FAILED_CHECKS checks failed ($((TOTAL_CHECKS - FAILED_CHECKS))/$TOTAL_CHECKS passed)"
    log ""
    log "⚠️  $STATUS"
    EXIT_CODE=1
fi

aws ssm put-parameter \
    --region $REGION \
    --name "/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/status/verification-complete" \
    --value "$STATUS - $(date '+%Y-%m-%d %H:%M:%S')" \
    --type String \
    --overwrite 2>/dev/null || true

log "===== All Verification Completed ====="

exit $EXIT_CODE