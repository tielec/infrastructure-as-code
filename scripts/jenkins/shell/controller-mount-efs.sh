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
JENKINS_HOME_DIR="/mnt/efs/jenkins" # Jenkinsのホームディレクトリを明示的に定義

# リージョンが空の場合はメタデータから取得
if [ -z "$AWS_REGION" ]; then
  AWS_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
  if [ -z "$AWS_REGION" ]; then
    # もし通常の方法で取得できない場合はAZから推測
    AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
    if [ -n "$AZ" ]; then
      AWS_REGION=${AZ%?}
      echo "リージョンをAZから抽出: $AWS_REGION"
    else
      # 最終手段としてデフォルト値を設定
      AWS_REGION="us-east-1"
      echo "デフォルトリージョンを使用: $AWS_REGION"
    fi
  fi
fi

echo "EFS ID: $EFS_ID, リージョン: $AWS_REGION"

# EFS IDが指定されているか確認
if [ -z "$EFS_ID" ]; then
  echo "エラー: EFS_ID が指定されていません。マウントできません。"
  exit 1
fi

# 必要なパッケージがインストールされているか確認
echo "amazon-efs-utilsの確認とインストール"
if ! rpm -q amazon-efs-utils &>/dev/null; then
  dnf install -y amazon-efs-utils
fi

# 追加: NFS関連パッケージをインストール（EFSマウントに必要な場合がある）
echo "NFS関連パッケージのインストール"
dnf install -y nfs-utils

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

# 改善: DNSルックアップおよびNWの疎通確認テスト
echo "DNSルックアップ試行中..."
if host $EFS_DNS &>/dev/null; then
  echo "DNSルックアップ成功: $EFS_DNS"
else
  echo "警告: DNSルックアップ失敗 - $EFS_DNS"
  echo "手動でDNSを確認: $(nslookup $EFS_DNS 2>&1 || echo 'DNSルックアップに失敗')"
fi

echo "EFSエンドポイントへのping試行中..."
if ping -c 2 $EFS_DNS > /dev/null 2>&1; then
  echo "EFSエンドポイントに到達できます: $EFS_DNS"
else
  echo "警告: EFSエンドポイントに到達できません: $EFS_DNS"
  # ネットワーク診断情報を追加
  echo "ネットワーク診断情報:"
  ip addr show
  echo "ルート情報:"
  ip route
  echo "DNS情報:"
  cat /etc/resolv.conf
fi

# EFSマウントエントリを/etc/fstabに追加
# 改善: awsefsメソッドを使用 (より安全で信頼性が高い)
echo "fstabにEFSマウントエントリを追加"
echo "$EFS_ID:/ $MOUNT_POINT efs _netdev,tls,iam 0 0" >> /etc/fstab

# fstabの内容を表示
echo "/etc/fstabの内容:"
cat /etc/fstab | grep -v '#'

# マウント処理と再試行ロジック
echo "EFSファイルシステムのマウントを試みます"
MOUNT_ATTEMPTS=0
MAX_ATTEMPTS=5

until mount -a -t efs && df -h | grep -q "$MOUNT_POINT"; do
  MOUNT_ATTEMPTS=$((MOUNT_ATTEMPTS+1))
  echo "マウント試行 $MOUNT_ATTEMPTS/$MAX_ATTEMPTS"
  
  if [ $MOUNT_ATTEMPTS -ge $MAX_ATTEMPTS ]; then
    echo "エラー: $MAX_ATTEMPTS回の試行後もマウントに失敗しました"
    
    # 必要な情報を収集
    echo "システム情報:"
    df -h
    mount
    dmesg | tail -50
    
    # fstabのバックアップを作成
    cp /etc/fstab /etc/fstab.bak
    
    # 問題のあるマウントエントリを削除
    echo "問題のあるマウントエントリを削除して再起動できるようにします"
    sed -i '/efs/d' /etc/fstab
    sed -i '/fs-/d' /etc/fstab
    
    echo "緊急モードを避けるためにマウントエラーを無視します"
    exit 0
  fi
  
  echo "マウント情報:"
  systemctl status --no-pager amazon-efs-mount-watchdog.service 2>/dev/null || true
  
  sleep 10
done

echo "EFSマウント成功"

# Jenkinsディレクトリ構造の作成
echo "Jenkinsデータディレクトリを作成: $JENKINS_HOME_DIR"
mkdir -p $JENKINS_HOME_DIR/{plugins,jobs,secrets,nodes,logs,init.groovy.d}

# UID/GIDを正しく取得する（通常は994:994がJenkins）
JENKINS_UID=$(id -u jenkins 2>/dev/null || echo 994)
JENKINS_GID=$(getent group jenkins 2>/dev/null || echo 994)

# Jenkinsユーザーが存在しない場合は作成
if ! id jenkins &>/dev/null; then
  echo "Jenkinsユーザーを作成します"
  groupadd -g $JENKINS_GID jenkins 2>/dev/null || true
  useradd -u $JENKINS_UID -g jenkins -d $JENKINS_HOME_DIR -m jenkins 2>/dev/null || true
fi

# 所有権とパーミッションを適切に設定
echo "Jenkinsディレクトリの所有権とパーミッションを設定"
chown -R $JENKINS_UID:$JENKINS_GID $JENKINS_HOME_DIR
find $JENKINS_HOME_DIR -type d -exec chmod 755 {} \;
find $JENKINS_HOME_DIR -type f -exec chmod 644 {} \; 2>/dev/null || true

# ディレクトリの読み書き権限をテスト
echo "Jenkinsディレクトリのアクセス権をテスト"
if su - jenkins -c "touch $JENKINS_HOME_DIR/write_test && rm $JENKINS_HOME_DIR/write_test"; then
  echo "Jenkinsユーザーはホームディレクトリに書き込み可能です"
else
  echo "警告: Jenkinsユーザーはホームディレクトリに書き込みできません"
  ls -la $JENKINS_HOME_DIR
fi

# Jenkinsホームディレクトリへのシンボリックリンク
SYSTEM_JENKINS_HOME="/var/lib/jenkins"
echo "Jenkinsホームディレクトリへのシンボリックリンクを設定: $SYSTEM_JENKINS_HOME -> $JENKINS_HOME_DIR"

# 既存のディレクトリ/リンクを処理
if [ -L "$SYSTEM_JENKINS_HOME" ]; then
  echo "既存のシンボリックリンクを削除"
  rm -f "$SYSTEM_JENKINS_HOME"
elif [ -d "$SYSTEM_JENKINS_HOME" ]; then
  BACKUP_DIR="${SYSTEM_JENKINS_HOME}.bak.$(date +%Y%m%d%H%M%S)"
  echo "既存のディレクトリをバックアップ: $SYSTEM_JENKINS_HOME -> $BACKUP_DIR"
  mv "$SYSTEM_JENKINS_HOME" "$BACKUP_DIR"
fi

# シンボリックリンクを作成
ln -sf "$JENKINS_HOME_DIR" "$SYSTEM_JENKINS_HOME"
echo "シンボリックリンクの作成完了: $(ls -la $SYSTEM_JENKINS_HOME)"

echo "EFSマウント処理が完了しました - マウント状況:"
df -h | grep efs