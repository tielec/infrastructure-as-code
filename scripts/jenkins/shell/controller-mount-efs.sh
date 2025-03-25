#!/bin/bash
# Jenkins用EFSマウントスクリプト
# SSM用に最適化されたバージョン

# エラーハンドリングを設定
set -e
exec > >(tee /var/log/efs-mount.log|logger -t efs-mount -s 2>/dev/console) 2>&1
set -x

# 引数またはSSMパラメータからの取得
EFS_ID="${EFS_ID}"
AWS_REGION="${AWS_REGION}"
JENKINS_HOME_DIR="/mnt/efs/jenkins"
MOUNT_POINT="/mnt/efs"

echo "EFS ID: $EFS_ID, リージョン: $AWS_REGION"

# EFS IDが指定されているか確認
if [ -z "$EFS_ID" ]; then
  echo "エラー: EFS_ID が指定されていません。マウントできません。"
  exit 1
fi

# リージョンが空の場合はメタデータから取得
if [ -z "$AWS_REGION" ]; then
  AWS_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
  if [ -z "$AWS_REGION" ]; then
    AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
    if [ -n "$AZ" ]; then
      AWS_REGION=${AZ%?}
    else
      AWS_REGION="us-east-1"
    fi
  fi
  echo "使用するリージョン: $AWS_REGION"
fi

# 冪等性対応: 正しくマウントされているか確認
if df -h | grep -q "$MOUNT_POINT"; then
  echo "EFSは既にマウントされています"
  
  # マウントされているのが正しいEFSか確認
  MOUNTED_FS_ID=$(mount | grep $MOUNT_POINT | grep -o 'fs-[a-z0-9]*' || echo "")
  if [ -n "$MOUNTED_FS_ID" ] && [ "$MOUNTED_FS_ID" != "$EFS_ID" ]; then
    echo "警告: マウントされているファイルシステムID($MOUNTED_FS_ID)が指定されたID($EFS_ID)と異なります"
    echo "既存のマウントをアンマウントします"
    umount $MOUNT_POINT
    # 続行してマウントし直す
  else
    # 同じEFSがマウントされている場合は、Jenkinsディレクトリ確認だけ行う
    if [ ! -d "$JENKINS_HOME_DIR" ]; then
      mkdir -p $JENKINS_HOME_DIR/{plugins,jobs,secrets,nodes,logs,init.groovy.d}
      echo "Jenkinsディレクトリを作成しました: $JENKINS_HOME_DIR"
    fi
    echo "正しいEFSがマウントされていることを確認しました"
    exit 0
  fi
fi

# 必要なパッケージがインストールされているか確認
echo "必要なパッケージの確認"
if ! rpm -q amazon-efs-utils &>/dev/null; then
  echo "amazon-efs-utilsをインストールします"
  dnf install -y amazon-efs-utils
fi

if ! rpm -q nfs-utils &>/dev/null; then
  echo "nfs-utilsをインストールします"
  dnf install -y nfs-utils
fi

# マウントポイントの作成
mkdir -p $MOUNT_POINT
chmod 755 $MOUNT_POINT

# 既存のEFSエントリを/etc/fstabから削除
sed -i '/efs/d' /etc/fstab
sed -i '/fs-/d' /etc/fstab

# 接続テスト
echo "EFSエンドポイントへの接続テスト"
EFS_DNS="$EFS_ID.efs.$AWS_REGION.amazonaws.com"

if ! host $EFS_DNS &>/dev/null; then
  echo "エラー: DNSルックアップ失敗 - $EFS_DNS"
  echo "DNSレコードが存在しないか、DNSサーバーに到達できません"
  exit 1
fi

# EFSマウントエントリを/etc/fstabに追加
echo "$EFS_ID:/ $MOUNT_POINT efs _netdev,tls,iam 0 0" >> /etc/fstab
echo "fstabエントリを追加しました"

# マウント実行
echo "EFSファイルシステムをマウントします"
if ! mount -a -t efs; then
  echo "エラー: EFSのマウントに失敗しました"
  # 診断情報を収集
  echo "診断情報:"
  mount
  df -h
  # マウントエントリを削除して再起動の問題を防止
  sed -i '/efs/d' /etc/fstab
  sed -i '/fs-/d' /etc/fstab
  exit 1
fi

# マウント確認
if ! df -h | grep -q "$MOUNT_POINT"; then
  echo "エラー: マウントコマンドは成功しましたが、マウントが存在しません"
  exit 1
fi

echo "EFSマウント成功"

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
echo "シンボリックリンクを作成: $SYSTEM_JENKINS_HOME -> $JENKINS_HOME_DIR"

echo "EFSマウント処理が完了しました"
exit 0
