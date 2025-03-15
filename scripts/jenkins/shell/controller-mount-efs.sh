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

# リージョンが空の場合はメタデータから取得
if [ -z "$AWS_REGION" ]; then
  AWS_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
fi

echo "EFS ID: $EFS_ID, リージョン: $AWS_REGION"

# マウントポイントの作成
MOUNT_POINT="/mnt/efs"
echo "マウントポイントの作成: $MOUNT_POINT"
mkdir -p $MOUNT_POINT
chmod 755 $MOUNT_POINT

# 既存のEFSエントリを/etc/fstabから削除
echo "/etc/fstabから既存のEFSエントリを削除"
sed -i '/efs/d' /etc/fstab
sed -i '/fs-/d' /etc/fstab

# 接続テスト
echo "EFSエンドポイントへの接続テスト"
EFS_DNS="$EFS_ID.efs.$AWS_REGION.amazonaws.com"
if ping -c 2 $EFS_DNS > /dev/null 2>&1; then
  echo "EFSエンドポイントに到達できます: $EFS_DNS"
else
  echo "警告: EFSエンドポイントに到達できません: $EFS_DNS"
  # DNSルックアップで解決を試みる
  echo "DNSルックアップ: $(nslookup $EFS_DNS 2>&1 || echo 'DNSルックアップに失敗')"
fi

# EFSマウントエントリを/etc/fstabに追加
echo "fstabにNFSマウントエントリを追加"
echo "$EFS_DNS:/ $MOUNT_POINT nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0" >> /etc/fstab

# fstabの内容を表示
echo "/etc/fstabの内容:"
cat /etc/fstab | grep -v '#'

# マウント処理と再試行ロジック
echo "EFSファイルシステムのマウントを試みます"
MOUNT_ATTEMPTS=0
MAX_ATTEMPTS=5

until mount -a && df -h | grep -q "$MOUNT_POINT"; do
  MOUNT_ATTEMPTS=$((MOUNT_ATTEMPTS+1))
  echo "マウント試行 $MOUNT_ATTEMPTS/$MAX_ATTEMPTS"
  
  if [ $MOUNT_ATTEMPTS -ge $MAX_ATTEMPTS ]; then
    echo "エラー: $MAX_ATTEMPTS回の試行後もマウントに失敗しました"
    
    # 必要な情報を収集
    echo "システム情報:"
    df -h
    mount
    
    # fstabのバックアップを作成
    cp /etc/fstab /etc/fstab.bak
    
    # 問題のあるマウントエントリを削除
    echo "問題のあるマウントエントリを削除して再起動できるようにします"
    sed -i '/efs/d' /etc/fstab
    sed -i '/fs-/d' /etc/fstab
    
    echo "緊急モードを避けるためにマウントエラーを無視します"
    exit 0
  fi
  
  sleep 10
done

echo "EFSマウント成功"

# Jenkinsのホームディレクトリを作成
JENKINS_DATA_DIR="$MOUNT_POINT/jenkins-home"
echo "Jenkinsデータディレクトリを作成: $JENKINS_DATA_DIR"
mkdir -p $JENKINS_DATA_DIR

# UID/GIDを正しく取得する（通常は994:994がJenkins）
JENKINS_UID=$(id -u jenkins 2>/dev/null || echo 994)
JENKINS_GID=$(getent group jenkins 2>/dev/null | cut -d: -f3 || echo 994)

# 所有権とパーミッションを適切に設定
chown -R $JENKINS_UID:$JENKINS_GID $JENKINS_DATA_DIR
chmod -R 755 $JENKINS_DATA_DIR

# Jenkinsホームディレクトリへのシンボリックリンク
JENKINS_HOME="/var/lib/jenkins"
echo "Jenkinsホームディレクトリへのシンボリックリンクを設定: $JENKINS_HOME -> $JENKINS_DATA_DIR"

# 既存のディレクトリ/リンクを処理
if [ -L "$JENKINS_HOME" ]; then
  echo "既存のシンボリックリンクを削除"
  rm -f "$JENKINS_HOME"
elif [ -d "$JENKINS_HOME" ]; then
  BACKUP_DIR="${JENKINS_HOME}.bak.$(date +%Y%m%d%H%M%S)"
  echo "既存のディレクトリをバックアップ: $JENKINS_HOME -> $BACKUP_DIR"
  mv "$JENKINS_HOME" "$BACKUP_DIR"
fi

# シンボリックリンクを作成
ln -sf "$JENKINS_DATA_DIR" "$JENKINS_HOME"
echo "シンボリックリンクの作成完了"

echo "EFSマウント処理が完了しました"
