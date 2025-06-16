#!/bin/bash
# Jenkinsバージョン更新スクリプト
# SSM経由で実行されることを前提

# エラーハンドリング設定
set -e

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /var/log/jenkins-update-version.log
}

# エラーハンドラー
error_exit() {
    log "ERROR: $1"
    exit 1
}

# 環境変数
JENKINS_VERSION="${JENKINS_VERSION:-latest}"
JENKINS_HOME_DIR="/mnt/efs/jenkins"

log "===== Starting Jenkins Version Update ====="
log "Target version: $JENKINS_VERSION"

# 現在のバージョンを確認
CURRENT_VERSION=$(rpm -q jenkins --queryformat '%{VERSION}' 2>/dev/null || echo 'not installed')
log "Current version: $CURRENT_VERSION"

# Jenkinsがインストールされていない場合はエラー
if [ "$CURRENT_VERSION" = "not installed" ]; then
    error_exit "Jenkins is not installed. Cannot update."
fi

# 同じバージョンの場合はスキップ
if [ "$JENKINS_VERSION" != "latest" ] && [ "$CURRENT_VERSION" = "$JENKINS_VERSION" ]; then
    log "Already running version $JENKINS_VERSION. No update needed."
    exit 0
fi

# Jenkinsサービスを停止
log "Stopping Jenkins service..."
systemctl stop jenkins

# 停止確認
TIMEOUT=60
ELAPSED=0
while systemctl is-active jenkins >/dev/null 2>&1; do
    if [ $ELAPSED -ge $TIMEOUT ]; then
        error_exit "Failed to stop Jenkins service within timeout"
    fi
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    log "Waiting for Jenkins to stop... ($ELAPSED seconds)"
done
log "Jenkins service stopped"

# バックアップ作成（オプショナル）
if [ -d "$JENKINS_HOME_DIR" ]; then
    BACKUP_FILE="/mnt/efs/jenkins-backup-$(date +%Y%m%d%H%M%S).tar.gz"
    log "Creating configuration backup: $BACKUP_FILE"
    tar -czf "$BACKUP_FILE" \
        -C /mnt/efs \
        jenkins/jobs \
        jenkins/config.xml \
        jenkins/plugins \
        jenkins/secrets \
        jenkins/users \
        2>/dev/null || log "WARNING: Some files could not be backed up"
    
    # 古いバックアップを削除（7日以上前のもの）
    find /mnt/efs -name "jenkins-backup-*.tar.gz" -mtime +7 -delete || true
fi

# Jenkinsリポジトリの更新
log "Updating Jenkins repository..."
wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io-2023.key

# Jenkinsを更新
if [ "$JENKINS_VERSION" != "latest" ]; then
    log "Installing specific version: jenkins-$JENKINS_VERSION"
    dnf install -y jenkins-$JENKINS_VERSION
else
    log "Updating to latest version"
    dnf update -y jenkins
fi

# 更新されたバージョンを確認
NEW_VERSION=$(rpm -q jenkins --queryformat '%{VERSION}')
log "Updated to version: $NEW_VERSION"

# WAR ファイルの権限確認
if [ -f "/usr/share/java/jenkins.war" ]; then
    chmod 644 /usr/share/java/jenkins.war
    log "Jenkins WAR file permissions set"
fi

# Jenkinsサービスを開始
log "Starting Jenkins service..."
systemctl start jenkins

# 起動確認
log "Waiting for Jenkins to start..."
TIMEOUT=300
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if systemctl is-active jenkins >/dev/null && curl -s -f http://localhost:8080/login >/dev/null 2>&1; then
        log "Jenkins started successfully (elapsed: $ELAPSED seconds)"
        break
    fi
    
    if ! systemctl is-active jenkins >/dev/null; then
        log "WARNING: Jenkins service is not active. Checking logs..."
        journalctl -u jenkins --no-pager -n 50
        
        log "Attempting to restart Jenkins..."
        systemctl restart jenkins
    fi
    
    sleep 10
    ELAPSED=$((ELAPSED + 10))
    log "Still waiting... (elapsed: $ELAPSED seconds)"
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    error_exit "Jenkins failed to start within timeout"
fi

# 更新完了情報を記録
UPDATE_INFO="Updated from $CURRENT_VERSION to $NEW_VERSION at $(date)"
echo "$UPDATE_INFO" >> "$JENKINS_HOME_DIR/.update-history"
chown jenkins:jenkins "$JENKINS_HOME_DIR/.update-history"

# インスタンスメタデータ取得（IMDSv2対応）
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)

# SSMパラメータに状態を報告
log "Reporting update status to SSM parameter"
STATUS_MESSAGE="$(date '+%Y-%m-%d %H:%M:%S') - Jenkins updated to $NEW_VERSION (Instance: $INSTANCE_ID)"

aws ssm put-parameter \
    --region $REGION \
    --name "/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/status/last-update" \
    --value "$STATUS_MESSAGE" \
    --type String \
    --overwrite || log "WARNING: Failed to update SSM parameter"

log "Jenkins version update completed successfully"
log "Previous version: $CURRENT_VERSION"
log "New version: $NEW_VERSION"
