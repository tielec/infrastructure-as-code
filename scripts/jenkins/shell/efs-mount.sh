# EFSマウント設定
echo "${efsFileSystemId}:/ /mnt/efs efs _netdev,tls,iam 0 0" >> /etc/fstab

# マウント処理と再試行ロジック
MOUNT_ATTEMPTS=0
MAX_ATTEMPTS=10
until mount -a && df -h | grep -q "/mnt/efs"; do
  echo "Attempt $((MOUNT_ATTEMPTS+1)) of $MAX_ATTEMPTS to mount EFS"
  sleep 30
  MOUNT_ATTEMPTS=$((MOUNT_ATTEMPTS+1))
  if [ $MOUNT_ATTEMPTS -eq $MAX_ATTEMPTS ]; then
    echo "Failed to mount EFS after $MAX_ATTEMPTS attempts"
    exit 1
  fi
done
