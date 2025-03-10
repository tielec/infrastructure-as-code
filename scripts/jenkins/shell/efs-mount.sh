#!/bin/bash
# 必要なディレクトリを作成
mkdir -p /mnt/efs

# EFSのリージョンを取得（EC2メタデータから）
AWS_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
echo "Current AWS region: $AWS_REGION"

# 既存のEFSエントリを削除（重複を避けるため）
sed -i '/efs/d' /etc/fstab

# EFSマウント設定（nfs4タイプを使用）
echo "${efsFileSystemId}.efs.$AWS_REGION.amazonaws.com:/ /mnt/efs nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0" >> /etc/fstab

# マウント処理と再試行ロジック
MOUNT_ATTEMPTS=0
MAX_ATTEMPTS=10

echo "Attempting to mount EFS file system ${efsFileSystemId}"
echo "Mount configuration in /etc/fstab:"
cat /etc/fstab | grep efs

until mount -a && df -h | grep -q "/mnt/efs"; do
  MOUNT_ATTEMPTS=$((MOUNT_ATTEMPTS+1))
  echo "Attempt $MOUNT_ATTEMPTS of $MAX_ATTEMPTS to mount EFS"
  
  # 追加デバッグ情報
  if [ $MOUNT_ATTEMPTS -eq 3 ]; then
    echo "Debug: Testing connectivity to EFS endpoint"
    ping -c 2 ${efsFileSystemId}.efs.$AWS_REGION.amazonaws.com || echo "Ping failed - connectivity issues"
  fi
  
  sleep 30
  if [ $MOUNT_ATTEMPTS -eq $MAX_ATTEMPTS ]; then
    echo "Failed to mount EFS after $MAX_ATTEMPTS attempts"
    echo "Final attempt debug info:"
    dmesg | tail -30
    exit 1
  fi
done

echo "EFS mounted successfully"

# Jenkinsホームディレクトリの準備
mkdir -p /mnt/efs/jenkins-home
chown -R 994:994 /mnt/efs/jenkins-home
chmod 755 /mnt/efs/jenkins-home

# 既存のJenkinsディレクトリがあれば、シンボリックリンクで置き換え
JENKINS_HOME="/var/lib/jenkins"
if [ -L "$JENKINS_HOME" ]; then
  rm -f "$JENKINS_HOME"
elif [ -d "$JENKINS_HOME" ]; then
  mv "$JENKINS_HOME" "${JENKINS_HOME}.bak.$(date +%Y%m%d%H%M%S)"
fi

# EFSのJenkinsディレクトリへのシンボリックリンクを作成
ln -sf /mnt/efs/jenkins-home "$JENKINS_HOME"
