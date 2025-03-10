#!/bin/bash
# EFSマウントスクリプト - 改善版

# エラーハンドリングを設定
set -e

# ログ記録用関数
log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a /var/log/efs-mount.log
}

log "EFSマウント処理を開始します"

# マウントポイントの作成
MOUNT_POINT="/mnt/efs"
log "マウントポイントの作成: $MOUNT_POINT"
mkdir -p $MOUNT_POINT
chmod 755 $MOUNT_POINT

# EFSファイルシステムIDとリージョンを設定
EFS_ID="${efsFileSystemId}"
AWS_REGION="${AWS_REGION}"

# リージョンが空の場合はメタデータから取得
if [ -z "$AWS_REGION" ]; then
  AWS_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
fi

log "EFS ID: $EFS_ID, リージョン: $AWS_REGION"

# 既存のEFSエントリを/etc/fstabから削除
log "/etc/fstabから既存のEFSエントリを削除"
sed -i '/efs/d' /etc/fstab
sed -i '/fs-/d' /etc/fstab

# 接続テスト
log "EFSエンドポイントへの接続テスト"
EFS_DNS="$EFS_ID.efs.$AWS_REGION.amazonaws.com"
if ping -c 2 $EFS_DNS > /dev/null 2>&1; then
  log "EFSエンドポイントに到達できます: $EFS_DNS"
else
  log "警告: EFSエンドポイントに到達できません: $EFS_DNS"
  # DNSルックアップで解決を試みる
  log "DNSルックアップ: $(nslookup $EFS_DNS 2>&1 || echo 'DNSルックアップに失敗')"
fi

# EFSマウントエントリを/etc/fstabに追加
log "fstabにNFSマウントエントリを追加"
echo "$EFS_DNS:/ $MOUNT_POINT nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0" >> /etc/fstab

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

# Jenkinsのホームディレクトリを作成
JENKINS_DATA_DIR="$MOUNT_POINT/jenkins-home"
log "Jenkinsデータディレクトリを作成: $JENKINS_DATA_DIR"
mkdir -p $JENKINS_DATA_DIR
chown -R 994:994 $JENKINS_DATA_DIR
chmod 755 $JENKINS_DATA_DIR

# Jenkinsホームディレクトリへのシンボリックリンク
JENKINS_HOME="/var/lib/jenkins"
log "Jenkinsホームディレクトリへのシンボリックリンクを設定: $JENKINS_HOME -> $JENKINS_DATA_DIR"

# 既存のディレクトリ/リンクを処理
if [ -L "$JENKINS_HOME" ]; then
  log "既存のシンボリックリンクを削除"
  rm -f "$JENKINS_HOME"
elif [ -d "$JENKINS_HOME" ]; then
  BACKUP_DIR="${JENKINS_HOME}.bak.$(date +%Y%m%d%H%M%S)"
  log "既存のディレクトリをバックアップ: $JENKINS_HOME -> $BACKUP_DIR"
  mv "$JENKINS_HOME" "$BACKUP_DIR"
fi

# シンボリックリンクを作成
ln -sf "$JENKINS_DATA_DIR" "$JENKINS_HOME"
log "シンボリックリンクの作成完了"

log "EFSマウント処理が完了しました"
