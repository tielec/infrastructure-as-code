#!/bin/bash
# EC2インスタンスのEBSボリューム自動拡張スクリプト
# 
# このスクリプトは以下の処理を行います：
# - ルートデバイスのパーティションを拡張
# - ファイルシステムを拡張（XFS/ext4対応）
# - 拡張前後のディスク容量を表示

set -e

echo "========================================="
echo "Starting EBS Volume Expansion"
echo "========================================="

# ディスク容量の確認（拡張前）
echo "Current disk usage:"
df -h /

# ルートデバイスの情報を取得
ROOT_DEVICE=$(df / | tail -1 | awk '{print $1}')
echo "Root device: $ROOT_DEVICE"

# デバイス名からパーティション番号を取得
if [[ "$ROOT_DEVICE" =~ nvme ]]; then
    # NVMe デバイスの場合 (例: /dev/nvme0n1p1)
    DEVICE_NAME=$(echo "$ROOT_DEVICE" | sed 's/p[0-9]*$//')
    PARTITION_NUM=$(echo "$ROOT_DEVICE" | grep -o '[0-9]*$')
else
    # 通常のデバイスの場合 (例: /dev/xvda1)
    DEVICE_NAME=$(echo "$ROOT_DEVICE" | sed 's/[0-9]*$//')
    PARTITION_NUM=$(echo "$ROOT_DEVICE" | grep -o '[0-9]*$')
fi

echo "Device name: $DEVICE_NAME"
echo "Partition number: $PARTITION_NUM"

# cloud-utils-growpartのインストール（必要な場合）
if ! command -v growpart &> /dev/null; then
    echo "Installing cloud-utils-growpart..."
    dnf install -y cloud-utils-growpart || yum install -y cloud-utils-growpart
fi

# パーティションの拡張
echo "Expanding partition..."
growpart "$DEVICE_NAME" "$PARTITION_NUM" || {
    echo "Note: growpart returned non-zero (partition might already be expanded)"
}

# ファイルシステムの種類を確認
FS_TYPE=$(file -s "$ROOT_DEVICE" | grep -oE 'ext[234]|XFS' | head -1)
if [ -z "$FS_TYPE" ]; then
    # blkidコマンドで再確認
    FS_TYPE=$(blkid -o value -s TYPE "$ROOT_DEVICE")
fi

echo "Filesystem type: $FS_TYPE"

# ファイルシステムの拡張
if [[ "$FS_TYPE" =~ ext[234] ]]; then
    echo "Expanding ext filesystem..."
    resize2fs "$ROOT_DEVICE"
elif [[ "$FS_TYPE" == "xfs" || "$FS_TYPE" == "XFS" ]]; then
    echo "Expanding XFS filesystem..."
    xfs_growfs -d /
else
    echo "WARNING: Unknown filesystem type: $FS_TYPE"
    echo "Manual intervention may be required"
fi

# ディスク容量の確認（拡張後）
echo ""
echo "Disk usage after expansion:"
df -h /

# 詳細な情報表示
echo ""
echo "Detailed block device information:"
lsblk

echo ""
echo "========================================="
echo "EBS Volume Expansion Completed"
echo "========================================="