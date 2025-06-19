#!/bin/bash
# エラーハンドリングを設定
set -e

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /var/log/efs-mount.log
}

# エラーハンドラー
error_exit() {
    log "ERROR: $1"
    exit 1
}

# 環境変数はSSMドキュメントで既に設定されている
# EFS_ID と AWS_REGION が渡される
JENKINS_HOME_DIR="/mnt/efs/jenkins"
MOUNT_POINT="/mnt/efs"

log "Starting EFS mount script"
log "EFS ID: $EFS_ID, Region: $AWS_REGION"

# EFS IDが指定されているか確認
if [ -z "$EFS_ID" ]; then
  error_exit "EFS_ID が指定されていません。マウントできません。"
fi

# リージョンが空の場合はメタデータから取得
if [ -z "$AWS_REGION" ]; then
  # IMDSv2対応
  TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
  AWS_REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)
  if [ -z "$AWS_REGION" ]; then
    AWS_REGION="ap-northeast-1"
  fi
  log "使用するリージョン: $AWS_REGION"
fi

# 冪等性対応: 正しくマウントされているか確認
if df -h | grep -q "$MOUNT_POINT"; then
  log "EFSは既にマウントされています"
  exit 0
fi

# 必要なパッケージがインストールされているか確認
log "必要なパッケージの確認"
if ! rpm -q amazon-efs-utils &>/dev/null; then
  log "amazon-efs-utilsをインストールします"
  dnf install -y amazon-efs-utils || yum install -y amazon-efs-utils
fi

if ! rpm -q nfs-utils &>/dev/null; then
  log "nfs-utilsをインストールします"
  dnf install -y nfs-utils || yum install -y nfs-utils
fi

# マウントポイントの作成
mkdir -p $MOUNT_POINT
chmod 755 $MOUNT_POINT

# 既存のEFSエントリを/etc/fstabから削除
sed -i '/efs/d' /etc/fstab
sed -i '/fs-/d' /etc/fstab

# DNS解決のテスト（オプショナル）
log "EFSエンドポイントへの接続テスト（DNS解決をスキップ）"
EFS_DNS="$EFS_ID.efs.$AWS_REGION.amazonaws.com"

# DNS解決の問題を回避するため、mount.efsに任せる
log "EFSファイルシステムをマウントします（mount.efsがDNS解決を処理）"

# 方法1: mount.efsを直接使用（推奨）
if ! mount -t efs -o tls,iam $EFS_ID:/ $MOUNT_POINT; then
  log "警告: IAMオプション付きのマウントに失敗しました。tlsのみで再試行します"
  
  # 方法2: IAMなしで再試行
  if ! mount -t efs -o tls $EFS_ID:/ $MOUNT_POINT; then
    log "エラー: tlsオプションでのマウントに失敗しました"
    
    # 診断情報を収集
    log "診断情報:"
    log "VPC DNS設定の確認が必要かもしれません"
    
    # EFSヘルパーのログを確認
    if [ -f /var/log/amazon/efs/mount.log ]; then
      log "EFSマウントヘルパーのログ:"
      tail -20 /var/log/amazon/efs/mount.log | tee -a /var/log/efs-mount.log
    fi
    
    error_exit "EFSマウントに失敗しました"
  fi
fi

# マウント確認
if ! df -h | grep -q "$MOUNT_POINT"; then
  error_exit "マウントコマンドは成功しましたが、マウントが存在しません"
fi

log "EFSマウント成功"

# Jenkinsディレクトリ構造の作成
mkdir -p $JENKINS_HOME_DIR/{plugins,jobs,secrets,nodes,logs,init.groovy.d}

# Jenkinsユーザーの確認
if ! getent group jenkins > /dev/null; then
  groupadd jenkins
fi

if ! id jenkins &>/dev/null; then
  useradd -m -d $JENKINS_HOME_DIR -g jenkins jenkins
fi

# 所有権とパーミッションを設定
chown -R jenkins:jenkins $JENKINS_HOME_DIR
find $JENKINS_HOME_DIR -type d -exec chmod 755 {} \;
find $JENKINS_HOME_DIR -type f -exec chmod 644 {} \; 2>/dev/null || true

# シンボリックリンクの設定
SYSTEM_JENKINS_HOME="/var/lib/jenkins"
if [ -L "$SYSTEM_JENKINS_HOME" ]; then
  rm -f "$SYSTEM_JENKINS_HOME"
elif [ -d "$SYSTEM_JENKINS_HOME" ]; then
  BACKUP_DIR="${SYSTEM_JENKINS_HOME}.bak.$(date +%Y%m%d%H%M%S)"
  mv "$SYSTEM_JENKINS_HOME" "$BACKUP_DIR"
fi

ln -sf "$JENKINS_HOME_DIR" "$SYSTEM_JENKINS_HOME"
log "シンボリックリンクを作成: $SYSTEM_JENKINS_HOME -> $JENKINS_HOME_DIR"

# fstabにエントリを追加（永続化）
echo "$EFS_ID:/ $MOUNT_POINT efs _netdev,tls,iam 0 0" >> /etc/fstab
log "fstabエントリを追加しました"

log "EFSマウント処理が完了しました"
exit 0
