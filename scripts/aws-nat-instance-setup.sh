#!/bin/bash
#
# NAT Instance Setup Script for Amazon Linux 2023 with nftables
# Lambda API Infrastructure - Optimized for serverless workloads
#
# Variables replaced by Pulumi:
# - ${VPC_CIDR}: VPC CIDR block (e.g., 10.1.0.0/16)
# - ${PROJECT_NAME}: Project name (e.g., lambda-api)
# - ${ENVIRONMENT}: Environment (dev/staging/prod)
# - ${AWS_REGION}: AWS Region

# スクリプトの実行ログを記録
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
set -x  # デバッグ用

echo "============================================"
echo "Starting NAT instance configuration"
echo "Project: ${PROJECT_NAME}"
echo "Environment: ${ENVIRONMENT}"
echo "VPC CIDR: ${VPC_CIDR}"
echo "Region: ${AWS_REGION}"
echo "============================================"

# ネットワークが完全に初期化されるまで待機
echo "Waiting for network initialization..."
while ! curl -s http://169.254.169.254/latest/meta-data/instance-id; do
    echo "Waiting for metadata service..."
    sleep 2
done

# インスタンスメタデータの取得
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
echo "Instance ID: $INSTANCE_ID"

# ===== システム設定 =====
echo "=== Configuring system settings ==="

# IP forwardingの有効化（永続化）
echo "Enabling IP forwarding..."
echo "net.ipv4.ip_forward = 1" | sudo tee /etc/sysctl.d/99-ip-forward.conf
echo "net.ipv4.conf.all.rp_filter = 0" | sudo tee -a /etc/sysctl.d/99-ip-forward.conf
echo "net.ipv4.conf.default.rp_filter = 0" | sudo tee -a /etc/sysctl.d/99-ip-forward.conf
sudo sysctl -p /etc/sysctl.d/99-ip-forward.conf

# システムアップデート
echo "Updating system packages..."
sudo dnf update -y

# ===== nftables設定 =====
echo "=== Setting up nftables ==="

# nftablesのインストール
echo "Installing nftables..."
sudo dnf install -y nftables

# iptables-nftが既にインストールされているか確認
if ! rpm -q iptables-nft &>/dev/null; then
    echo "Installing iptables-nft..."
    sudo dnf install -y iptables-nft
fi

# iptables-nftへの切り替え（互換性のため）
if [ -f /usr/sbin/iptables-nft ]; then
    sudo alternatives --set iptables /usr/sbin/iptables-nft
fi

# nftablesサービスの有効化
echo "Enabling nftables service..."
sudo systemctl enable nftables

# 既存のルールをクリア
echo "Clearing existing nftables rules..."
sudo nft flush ruleset

# プライマリネットワークインターフェースの検出
MAIN_ENI=$(ip -o link show | awk -F': ' '{print $2}' | grep -E '^(eth|ens|enp)' | head -n1)
echo "Primary network interface: $MAIN_ENI"

# nftablesルールの設定
echo "Configuring nftables rules..."
sudo nft add table ip nat
sudo nft add chain ip nat prerouting { type nat hook prerouting priority -100 \; }
sudo nft add chain ip nat postrouting { type nat hook postrouting priority 100 \; }

# フィルターテーブルの追加（セキュリティ用）
sudo nft add table ip filter
sudo nft add chain ip filter forward { type filter hook forward priority 0 \; }

# MASQUERADEルールの追加（VPC CIDRからのトラフィック用）
echo "Adding MASQUERADE rule for VPC CIDR: ${VPC_CIDR}"
sudo nft add rule ip nat postrouting ip saddr ${VPC_CIDR} oifname "$MAIN_ENI" masquerade

# フォワーディングルールの追加
echo "Adding forwarding rules..."
sudo nft add rule ip filter forward ip saddr ${VPC_CIDR} accept
sudo nft add rule ip filter forward ip daddr ${VPC_CIDR} ct state related,established accept

# 設定ディレクトリの作成
sudo mkdir -p /etc/nftables

# デフォルトのiptables/nftablesルールを無効化
echo "Disabling default firewall rules..."
if systemctl is-enabled iptables.service &>/dev/null; then
    sudo systemctl disable --now iptables.service
fi
if systemctl is-enabled ip6tables.service &>/dev/null; then
    sudo systemctl disable --now ip6tables.service
fi

# 設定の保存
echo "Saving nftables configuration..."
sudo nft list ruleset | sudo tee /etc/nftables/nat.nft

# nftablesの設定ファイルを更新
cat <<EOF | sudo tee /etc/sysconfig/nftables.conf
# Load saved ruleset on service start
include "/etc/nftables/nat.nft"
EOF

# rejectルールの削除（存在する場合）
echo "Checking for reject rules..."
if sudo nft list ruleset | grep -q "reject with icmp type host-prohibited"; then
    echo "WARNING: Reject rules found, removing..."
    sudo cp /etc/nftables/nat.nft /etc/nftables/nat.nft.backup
    
    # rejectルールを含まないルールセットを再作成
    sudo nft flush ruleset
    sudo nft add table ip nat
    sudo nft add chain ip nat prerouting { type nat hook prerouting priority -100 \; }
    sudo nft add chain ip nat postrouting { type nat hook postrouting priority 100 \; }
    sudo nft add rule ip nat postrouting ip saddr ${VPC_CIDR} oifname "$MAIN_ENI" masquerade
    
    sudo nft add table ip filter
    sudo nft add chain ip filter forward { type filter hook forward priority 0 \; }
    sudo nft add rule ip filter forward ip saddr ${VPC_CIDR} accept
    sudo nft add rule ip filter forward ip daddr ${VPC_CIDR} ct state related,established accept
    
    # 再度保存
    sudo nft list ruleset | sudo tee /etc/nftables/nat.nft
fi

# nftablesサービスの再起動
echo "Restarting nftables service..."
sudo systemctl restart nftables

# ===== モニタリング設定 =====
echo "=== Setting up monitoring ==="

# SSMエージェントの確認と起動
echo "Checking SSM agent..."
if systemctl is-enabled amazon-ssm-agent &>/dev/null; then
    sudo systemctl start amazon-ssm-agent
    echo "SSM agent started"
else
    echo "SSM agent not found, skipping..."
fi

# CloudWatchエージェントのインストール（オプション）
echo "Installing CloudWatch agent..."
if ! rpm -q amazon-cloudwatch-agent &>/dev/null; then
    ARCH=$(uname -m)
    if [ "$ARCH" = "aarch64" ]; then
        CW_ARCH="arm64"
    else
        CW_ARCH="amd64"
    fi
    wget -q https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/${CW_ARCH}/latest/amazon-cloudwatch-agent.rpm
    sudo rpm -U ./amazon-cloudwatch-agent.rpm || echo "CloudWatch agent installation skipped"
    rm -f ./amazon-cloudwatch-agent.rpm
fi

# ===== カスタムスクリプト設定 =====
echo "=== Setting up custom scripts ==="

# NAT メトリクス送信スクリプト
cat > /usr/local/bin/send-nat-metrics.sh << 'METRICS_EOF'
#!/bin/bash
# Send custom metrics for Lambda API NAT monitoring
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)

# 接続数メトリクス
CONNECTIONS=$(ss -nat | grep ESTABLISHED | wc -l)
aws cloudwatch put-metric-data \
    --namespace "LambdaAPI/NAT" \
    --metric-name ActiveConnections \
    --value $CONNECTIONS \
    --dimensions InstanceId=$INSTANCE_ID,Environment=${ENVIRONMENT}

# CPU使用率
CPU=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
aws cloudwatch put-metric-data \
    --namespace "LambdaAPI/NAT" \
    --metric-name CPUUtilization \
    --value $CPU \
    --dimensions InstanceId=$INSTANCE_ID,Environment=${ENVIRONMENT}
METRICS_EOF
sudo chmod +x /usr/local/bin/send-nat-metrics.sh

# NAT診断スクリプト
cat > /usr/local/bin/test-nat.sh << 'TEST_EOF'
#!/bin/bash
echo "=== Lambda API NAT Instance Diagnostics ==="
echo "Date: $(date)"
echo "Project: ${PROJECT_NAME}"
echo "Environment: ${ENVIRONMENT}"
echo ""
echo "=== System Settings ==="
echo "IP Forwarding: $(cat /proc/sys/net/ipv4/ip_forward)"
echo "RP Filter (all): $(cat /proc/sys/net/ipv4/conf/all/rp_filter)"
echo "RP Filter (default): $(cat /proc/sys/net/ipv4/conf/default/rp_filter)"
echo ""
echo "=== Network Configuration ==="
echo "Primary Interface: $(ip -o link show | awk -F': ' '{print $2}' | grep -E '^(eth|ens|enp)' | head -n1)"
ip addr show
echo ""
echo "=== Active Connections ==="
ss -nat | head -20
echo ""
echo "=== nftables Status ==="
sudo systemctl status nftables --no-pager
echo ""
echo "=== Current nftables Rules ==="
sudo nft list ruleset
echo ""
echo "=== Packet Counts ==="
sudo nft list ruleset -a
echo ""
echo "=== Testing External Connectivity ==="
curl -s -m 5 http://ifconfig.me && echo " - External IP" || echo "Failed to get external IP"
echo ""
echo "=== Lambda Connectivity Test ==="
echo "Testing connection to AWS Lambda endpoint..."
curl -s -m 5 https://lambda.${AWS_REGION}.amazonaws.com && echo "SUCCESS" || echo "FAILED"
TEST_EOF
sudo chmod +x /usr/local/bin/test-nat.sh

# Cronジョブの設定（5分ごとにメトリクス送信）
echo "Setting up cron jobs..."
echo "*/5 * * * * /usr/local/bin/send-nat-metrics.sh" | sudo crontab -

# ===== 最終確認 =====
echo ""
echo "============================================"
echo "Lambda API NAT instance configuration completed!"
echo "Instance Type: $(curl -s http://169.254.169.254/latest/meta-data/instance-type)"
echo "Architecture: $(uname -m)"
echo "VPC CIDR: ${VPC_CIDR}"
echo "Test with: /usr/local/bin/test-nat.sh"
echo "Check logs: /var/log/user-data.log"
echo "============================================"

# 初回テスト実行
/usr/local/bin/test-nat.sh > /var/log/nat-test-initial.log 2>&1
