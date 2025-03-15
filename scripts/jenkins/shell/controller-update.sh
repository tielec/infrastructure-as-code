#!/bin/bash
# Jenkinsコントローラー更新スクリプト
# システムマネージャーから実行するための更新用スクリプト

# エラーハンドリングとログ設定
set -e
exec > >(tee /var/log/jenkins-update.log|logger -t jenkins-update -s 2>/dev/console) 2>&1
set -x

# 環境変数
JENKINS_VERSION="${JENKINS_VERSION:-latest}"
RESTART_JENKINS="${RESTART_JENKINS:-false}"

echo "Updating Jenkins controller to version ${JENKINS_VERSION}"

# Jenkinsの更新
if [ "${JENKINS_VERSION}" != "latest" ]; then
  echo "Installing specific Jenkins version: ${JENKINS_VERSION}"
  dnf install -y jenkins-${JENKINS_VERSION}
else
  echo "Updating to latest Jenkins version"
  dnf update -y jenkins
fi

# 設定ファイルの更新（SSMパラメータから）
PARAMETER_PATH="/${PROJECT_NAME}/${ENVIRONMENT}/jenkins"

# 設定ファイル更新関数
update_groovy_script() {
  local script_name=$1
  local parameter_path="${PARAMETER_PATH}/groovy/${script_name}"
  local script_path="/mnt/efs/jenkins/init.groovy.d/${script_name}.groovy"
  
  echo "Checking for updated ${script_name} script"
  local script_content=$(aws ssm get-parameter --name "${parameter_path}" --with-decryption --query "Parameter.Value" --output text 2>/dev/null || echo "")
  
  if [ -n "$script_content" ]; then
    echo "Updating ${script_name} script"
    echo "$script_content" > $script_path
    chmod 644 $script_path
    chown jenkins:jenkins $script_path
    return 0
  fi
  
  return 1
}

# 主要なGroovyスクリプトを更新
SCRIPTS_UPDATED=0
update_groovy_script "disable-cli" && SCRIPTS_UPDATED=1
update_groovy_script "basic-settings" && SCRIPTS_UPDATED=1
update_groovy_script "recovery-mode" && SCRIPTS_UPDATED=1

# Jenkinsの再起動（必要な場合）
if [ "$RESTART_JENKINS" = "true" ] || [ $SCRIPTS_UPDATED -eq 1 ]; then
  echo "Restarting Jenkins service"
  systemctl restart jenkins
  
  # 起動確認
  TIMEOUT=180
  INTERVAL=5
  ELAPSED=0
  echo "Waiting for Jenkins to restart..."
  
  while [ $ELAPSED -lt $TIMEOUT ]; do
    if curl -s -f http://localhost:8080/login > /dev/null; then
      echo "Jenkins restarted successfully"
      break
    fi
    
    echo "Still waiting... ($ELAPSED seconds elapsed)"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
  done
  
  if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "Jenkins failed to restart within timeout"
    exit 1
  fi
else
  echo "Jenkins restart not required"
fi

echo "Jenkins update completed successfully"
