#!/bin/bash
# Jenkinsコントローラー起動スクリプト
# SSM用に最適化されたバージョン

# エラーハンドリングとログ設定
set -e
exec > >(tee /var/log/jenkins-startup.log|logger -t jenkins-startup -s 2>/dev/console) 2>&1
set -x

echo "Starting Jenkins service"

# Jenkinsの起動と起動確認
systemctl daemon-reload
systemctl enable jenkins
systemctl start jenkins

# 起動確認
TIMEOUT=900
INTERVAL=10
ELAPSED=0
echo "Waiting for Jenkins to start..."

while [ $ELAPSED -lt $TIMEOUT ]; do
  if curl -s -f http://localhost:8080/login > /dev/null; then
    echo "Jenkins started successfully"
    break
  fi
  
  if ! systemctl is-active jenkins > /dev/null; then
    echo "Jenkins service is not running. Checking logs..."
    journalctl -u jenkins --no-pager -n 100
    cat /mnt/efs/jenkins/logs/jenkins.log || true
  fi
  
  echo "Still waiting... ($ELAPSED seconds elapsed)"
  sleep $INTERVAL
  ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
  echo "Jenkins failed to start within timeout"
  exit 1
fi

# ステータス報告
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)

# SSMパラメータに状態を報告（オプション）
aws ssm put-parameter \
  --region $REGION \
  --name "/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/status/${JENKINS_COLOR}" \
  --value "$(date '+%Y-%m-%d %H:%M:%S') - Started on $INSTANCE_ID" \
  --type String \
  --overwrite || true

echo "Jenkins startup completed successfully"
