#!/bin/bash
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
set -x

${IPV6_CONFIG}# スワップの有効化（既に作成済み）
swapon /swapfile || true

# /tmpの容量を確保（tmpfsのサイズを調整）
# 注意: EC2 Fleetプラグインが一時的に/tmpを使用する可能性があるため、十分な容量を確保
# デフォルトでメモリの50%まで使用可能にする（最小3GB、最大10GB）
TOTAL_MEM=$(free -g | awk '/^Mem:/ {print $2}')
TMP_SIZE=$((TOTAL_MEM / 2))
if [ $TMP_SIZE -lt 3 ]; then
    TMP_SIZE=3
elif [ $TMP_SIZE -gt 10 ]; then
    TMP_SIZE=10
fi
mount -o remount,size=${TMP_SIZE}G /tmp
echo "/tmpのサイズを${TMP_SIZE}GBに設定しました"

# Dockerの起動と権限設定
systemctl start docker
chmod 666 /var/run/docker.sock || true
usermod -aG docker jenkins || true

# 環境情報の保存
echo "PROJECT_NAME=${PROJECT_NAME}" > /etc/jenkins-agent-env
echo "ENVIRONMENT=${ENVIRONMENT}" >> /etc/jenkins-agent-env
echo "AGENT_ROOT=/home/jenkins/agent" >> /etc/jenkins-agent-env
${ARCHITECTURE_ENV}${IPV6_ENV}chmod 644 /etc/jenkins-agent-env

# SSMエージェントの起動
systemctl start amazon-ssm-agent

# 起動完了のマーク
echo "$(date) - Agent bootstrap completed (custom AMI)" > /home/jenkins/agent/bootstrap-complete
chown jenkins:jenkins /home/jenkins/agent/bootstrap-complete