#!/bin/bash
# EFSマウント用スクリプト - 改善版

# エラーハンドリングを設定
set -e

# ログ記録用関数
log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a /var/log/efs-mount.log
}

log "EFSマウント処理を開始します"

# マウントポイントの作成
MOUNT_POINT="/var/lib/jenkins"
log "マウントポイントの作成: $MOUNT_POINT"
mkdir -p $MOUNT_POINT
chmod 755 $MOUNT_POINT

# AWS リージョンを取得
AWS_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)

log "EFS ID: $EFS_FILE_SYSTEM_ID, リージョン: $AWS_REGION"

# 既存のEFSエントリを/etc/fstabから削除
log "/etc/fstabから既存のEFSエントリを削除"
sed -i '/efs/d' /etc/fstab
sed -i '/fs-/d' /etc/fstab

# 接続テスト
log "EFSエンドポイントへの接続テスト"
EFS_DNS="$EFS_FILE_SYSTEM_ID.efs.$AWS_REGION.amazonaws.com"
if ping -c 2 $EFS_DNS > /dev/null 2>&1; then
  log "EFSエンドポイントに到達できます: $EFS_DNS"
else
  log "警告: EFSエンドポイントに到達できません: $EFS_DNS"
  # DNSルックアップで解決を試みる
  log "DNSルックアップ: $(nslookup $EFS_DNS 2>&1 || echo 'DNSルックアップに失敗')"
fi

# EFSマウントエントリを/etc/fstabに追加
# EFSアクセスポイントオプションの設定
ACCESS_POINT_OPTIONS=""
if [ -n "$EFS_ACCESS_POINT_ID" ]; then
  ACCESS_POINT_OPTIONS=",accesspoint=$EFS_ACCESS_POINT_ID"
fi

log "fstabにEFSマウントエントリを追加"
echo "$EFS_FILE_SYSTEM_ID:/ $MOUNT_POINT efs _netdev,tls,iam$ACCESS_POINT_OPTIONS 0 0" >> /etc/fstab

# fstabの内容を表示
log "/etc/fstabの内容:"
cat /etc/fstab | grep -v '#' | tee -a /var/log/efs-mount.log

# マウント処理と再試行ロジック
log "EFSファイルシステムのマウントを試みます"
MOUNT_ATTEMPTS=0
MAX_ATTEMPTS=5

until mount -a && df -h | grep -q "$MOUNT_POINT"; do
  MOUNT_ATTEMPTS=$((MOUNT_ATTEMPTS+1))
  log "マウント試行 $MOUNT_ATTEMPTS/$MAX_ATTEMPTS"
  
  if [ $MOUNT_ATTEMPTS -ge $MAX_ATTEMPTS ]; then
    log "エラー: $MAX_ATTEMPTS回の試行後もマウントに失敗しました"
    
    # 必要な情報を収集
    log "システム情報:"
    df -h | tee -a /var/log/efs-mount.log
    mount | tee -a /var/log/efs-mount.log
    
    # fstabのバックアップを作成
    cp /etc/fstab /etc/fstab.bak
    
    # 問題のあるマウントエントリを削除
    log "問題のあるマウントエントリを削除して再起動できるようにします"
    sed -i '/efs/d' /etc/fstab
    sed -i '/fs-/d' /etc/fstab
    
    log "緊急モードを避けるためにマウントエラーを無視します"
    exit 0
  fi
  
  sleep 10
done

log "EFSマウント成功"

# 所有者の設定
log "Jenkinsユーザーに所有権を設定"
chown -R jenkins:jenkins $MOUNT_POINT
chmod 755 $MOUNT_POINT

log "EFSマウント処理が完了しました"
