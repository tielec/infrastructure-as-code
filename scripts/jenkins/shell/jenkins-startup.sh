# ファイル権限の設定
chmod 644 /mnt/efs/jenkins/init.groovy.d/*.groovy
chown jenkins:jenkins /mnt/efs/jenkins/init.groovy.d/*.groovy

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

echo "Jenkins setup completed successfully"
