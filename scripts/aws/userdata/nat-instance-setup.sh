#!/bin/bash
#
# NAT Instance Setup Script for Amazon Linux 2023 with nftables
# Generic NAT instance for AWS VPC environments
#
# Variables (to be replaced by infrastructure provisioning tool):
# - ${VPC_CIDR}: VPC CIDR block (e.g., 10.0.0.0/16)
# - ${PROJECT_NAME}: Project name (optional, for tagging/monitoring)
# - ${ENVIRONMENT}: Environment (optional, e.g., dev/staging/prod)
# - ${AWS_REGION}: AWS Region (optional, for monitoring)
# - ${ENABLE_MONITORING}: Enable CloudWatch monitoring (true/false, default: false)
# - ${ENABLE_SSM}: Enable SSM agent (true/false, default: true)
#
# Usage:
#   Can be used as EC2 User Data or executed manually on Amazon Linux 2023
#

# スクリプトの実行ログを記録
exec > >(tee /var/log/nat-instance-setup.log|logger -t nat-instance-setup -s 2>/dev/console) 2>&1
set -x  # デバッグ用

echo "============================================"
echo "Starting NAT instance configuration"
echo "Date: $(date)"
if [ -n "${PROJECT_NAME:-}" ]; then
    echo "Project: ${PROJECT_NAME}"
fi
if [ -n "${ENVIRONMENT:-}" ]; then
    echo "Environment: ${ENVIRONMENT}"
fi
echo "VPC CIDR: ${VPC_CIDR}"
if [ -n "${AWS_REGION:-}" ]; then
    echo "Region: ${AWS_REGION}"
fi
echo "============================================"

# デフォルト値の設定
ENABLE_MONITORING="${ENABLE_MONITORING:-false}"
ENABLE_SSM="${ENABLE_SSM:-true}"

# ネットワークが完全に初期化されるまで待機
echo "Waiting for network initialization..."
MAX_RETRIES=30
RETRY_COUNT=0
while ! curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/instance-id > /dev/null 2>&1; do
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "ERROR: Failed to connect to metadata service after $MAX_RETRIES attempts"
        exit 1
    fi
    echo "Waiting for metadata service... (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)"
    sleep 2
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

# インスタンスメタデータの取得
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
echo "Instance ID: $INSTANCE_ID"

# ===== システム設定 =====
echo "=== Configuring system settings ==="

# IP forwardingの有効化（永続化）
echo "Enabling IP forwarding..."
cat <<EOF | sudo tee /etc/sysctl.d/99-nat-instance.conf
# NAT Instance Configuration
net.ipv4.ip_forward = 1
net.ipv4.conf.all.rp_filter = 0
net.ipv4.conf.default.rp_filter = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
EOF
sudo sysctl -p /etc/sysctl.d/99-nat-instance.conf

# システムアップデート（オプション）
echo "Updating system packages..."
sudo dnf update -y --security

# ===== nftables設定 =====
echo "=== Setting up nftables ==="

# nftablesのインストール
echo "Installing nftables..."
sudo dnf install -y nftables

# iptables-nftが既にインストールされているか確認
if ! rpm -q iptables-nft &>/dev/null; then
    echo "Installing iptables-nft for compatibility..."
    sudo dnf install -y iptables-nft
fi

# iptables-nftへの切り替え（互換性のため）
if [ -f /usr/sbin/iptables-nft ]; then
    sudo alternatives --set iptables /usr/sbin/iptables-nft || true
fi

# nftablesサービスの有効化
echo "Enabling nftables service..."
sudo systemctl enable nftables

# 既存のルールをクリア
echo "Clearing existing nftables rules..."
sudo nft flush ruleset

# プライマリネットワークインターフェースの検出
MAIN_ENI=$(ip -o link show | awk -F': ' '{print $2}' | grep -E '^(eth|ens|enp)' | head -n1)
if [ -z "$MAIN_ENI" ]; then
    echo "ERROR: Could not detect primary network interface"
    exit 1
fi
echo "Primary network interface: $MAIN_ENI"

# nftablesルールの設定
echo "Configuring nftables rules..."

# NAT テーブルの作成
sudo nft add table ip nat
sudo nft add chain ip nat prerouting { type nat hook prerouting priority -100 \; }
sudo nft add chain ip nat postrouting { type nat hook postrouting priority 100 \; }

# フィルターテーブルの作成（セキュリティ用）
sudo nft add table ip filter
sudo nft add chain ip filter input { type filter hook input priority 0 \; policy accept \; }
sudo nft add chain ip filter forward { type filter hook forward priority 0 \; policy accept \; }
sudo nft add chain ip filter output { type filter hook output priority 0 \; policy accept \; }

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
echo "Disabling conflicting firewall services..."
for service in iptables ip6tables firewalld; do
    if systemctl is-enabled $service &>/dev/null; then
        echo "Disabling $service..."
        sudo systemctl disable --now $service || true
    fi
done

# 設定の保存
echo "Saving nftables configuration..."
sudo nft list ruleset | sudo tee /etc/nftables/nat-instance.nft

# nftablesの設定ファイルを更新
cat <<EOF | sudo tee /etc/sysconfig/nftables.conf
# NAT Instance nftables configuration
include "/etc/nftables/nat-instance.nft"
EOF

# nftablesサービスの再起動
echo "Restarting nftables service..."
sudo systemctl restart nftables

# ===== SSMエージェント設定 =====
if [ "$ENABLE_SSM" = "true" ]; then
    echo "=== Setting up SSM agent ==="
    
    # SSMエージェントの確認と起動
    echo "Checking SSM agent..."
    if systemctl is-enabled amazon-ssm-agent &>/dev/null; then
        sudo systemctl start amazon-ssm-agent
        echo "SSM agent started"
    else
        echo "SSM agent not found, attempting to install..."
        # SSM エージェントのインストール（Amazon Linux 2023には通常プリインストール済み）
        sudo dnf install -y amazon-ssm-agent || echo "SSM agent installation failed or already installed"
        sudo systemctl enable --now amazon-ssm-agent || echo "Failed to start SSM agent"
    fi
fi

# ===== モニタリング設定（オプション） =====
if [ "$ENABLE_MONITORING" = "true" ] && [ -n "${AWS_REGION:-}" ]; then
    echo "=== Setting up monitoring ==="
    
    # CloudWatchエージェントのインストール
    echo "Installing CloudWatch agent..."
    if ! rpm -q amazon-cloudwatch-agent &>/dev/null; then
        ARCH=$(uname -m)
        if [ "$ARCH" = "aarch64" ]; then
            CW_ARCH="arm64"
        else
            CW_ARCH="amd64"
        fi
        wget -q https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/${CW_ARCH}/latest/amazon-cloudwatch-agent.rpm
        sudo rpm -U ./amazon-cloudwatch-agent.rpm || echo "CloudWatch agent installation failed"
        rm -f ./amazon-cloudwatch-agent.rpm
    fi
    
    # メトリクス送信スクリプトの作成
    cat > /usr/local/bin/send-nat-metrics.sh << 'METRICS_EOF'
#!/bin/bash
# Send custom metrics for NAT instance monitoring

# メタデータの取得
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
INSTANCE_TYPE=$(curl -s http://169.254.169.254/latest/meta-data/instance-type)

# 名前空間の設定
NAMESPACE="${PROJECT_NAME:-NAT}/Instance"
if [ -n "${ENVIRONMENT:-}" ]; then
    DIMENSIONS="InstanceId=$INSTANCE_ID,Environment=${ENVIRONMENT}"
else
    DIMENSIONS="InstanceId=$INSTANCE_ID"
fi

# 接続数メトリクス
CONNECTIONS=$(ss -nat | grep ESTABLISHED | wc -l)
aws cloudwatch put-metric-data \
    --region $REGION \
    --namespace "$NAMESPACE" \
    --metric-name ActiveConnections \
    --value $CONNECTIONS \
    --dimensions $DIMENSIONS 2>/dev/null || true

# CPU使用率（CloudWatchが自動収集しない場合のバックアップ）
CPU=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
if [ -n "$CPU" ]; then
    aws cloudwatch put-metric-data \
        --region $REGION \
        --namespace "$NAMESPACE" \
        --metric-name CPUUtilization \
        --value $CPU \
        --dimensions $DIMENSIONS 2>/dev/null || true
fi

# ネットワークスループット
if [ -f /proc/net/dev ]; then
    # 前回の値を保存
    STATS_FILE="/var/tmp/nat-network-stats"
    if [ -f "$STATS_FILE" ]; then
        source "$STATS_FILE"
        OLD_RX=$LAST_RX
        OLD_TX=$LAST_TX
        OLD_TIME=$LAST_TIME
    fi
    
    # 現在の値を取得
    CURRENT_TIME=$(date +%s)
    CURRENT_RX=$(cat /proc/net/dev | grep "$MAIN_ENI" | awk '{print $2}')
    CURRENT_TX=$(cat /proc/net/dev | grep "$MAIN_ENI" | awk '{print $10}')
    
    # 差分を計算して送信
    if [ -n "$OLD_RX" ] && [ -n "$OLD_TX" ] && [ -n "$OLD_TIME" ]; then
        TIME_DIFF=$((CURRENT_TIME - OLD_TIME))
        if [ $TIME_DIFF -gt 0 ]; then
            RX_BYTES_PER_SEC=$(( (CURRENT_RX - OLD_RX) / TIME_DIFF ))
            TX_BYTES_PER_SEC=$(( (CURRENT_TX - OLD_TX) / TIME_DIFF ))
            
            aws cloudwatch put-metric-data \
                --region $REGION \
                --namespace "$NAMESPACE" \
                --metric-name NetworkIn \
                --value $RX_BYTES_PER_SEC \
                --unit "Bytes/Second" \
                --dimensions $DIMENSIONS 2>/dev/null || true
                
            aws cloudwatch put-metric-data \
                --region $REGION \
                --namespace "$NAMESPACE" \
                --metric-name NetworkOut \
                --value $TX_BYTES_PER_SEC \
                --unit "Bytes/Second" \
                --dimensions $DIMENSIONS 2>/dev/null || true
        fi
    fi
    
    # 現在の値を保存
    echo "LAST_RX=$CURRENT_RX" > "$STATS_FILE"
    echo "LAST_TX=$CURRENT_TX" >> "$STATS_FILE"
    echo "LAST_TIME=$CURRENT_TIME" >> "$STATS_FILE"
fi
METRICS_EOF
    sudo chmod +x /usr/local/bin/send-nat-metrics.sh
    
    # Cronジョブの設定（5分ごとにメトリクス送信）
    echo "Setting up cron job for metrics..."
    (crontab -l 2>/dev/null || true; echo "*/5 * * * * /usr/local/bin/send-nat-metrics.sh") | crontab -
fi

# ===== 診断スクリプトの作成 =====
echo "=== Creating diagnostic scripts ==="

cat > /usr/local/bin/test-nat.sh << 'TEST_EOF'
#!/bin/bash
# NAT Instance Diagnostic Script

echo "=========================================="
echo "NAT Instance Diagnostics"
echo "Date: $(date)"
echo "Instance ID: $(curl -s http://169.254.169.254/latest/meta-data/instance-id)"
echo "Instance Type: $(curl -s http://169.254.169.254/latest/meta-data/instance-type)"
echo "=========================================="
echo ""

echo "=== System Settings ==="
echo "IP Forwarding: $(cat /proc/sys/net/ipv4/ip_forward)"
echo "RP Filter (all): $(cat /proc/sys/net/ipv4/conf/all/rp_filter)"
echo "RP Filter (default): $(cat /proc/sys/net/ipv4/conf/default/rp_filter)"
echo "Send Redirects (all): $(cat /proc/sys/net/ipv4/conf/all/send_redirects)"
echo ""

echo "=== Network Configuration ==="
MAIN_ENI=$(ip -o link show | awk -F': ' '{print $2}' | grep -E '^(eth|ens|enp)' | head -n1)
echo "Primary Interface: $MAIN_ENI"
echo ""
echo "Interface Details:"
ip addr show $MAIN_ENI
echo ""

echo "=== Routing Table ==="
ip route show
echo ""

echo "=== Active Connections ==="
echo "Total established connections: $(ss -nat | grep ESTABLISHED | wc -l)"
echo "Sample connections (first 10):"
ss -nat | grep ESTABLISHED | head -10
echo ""

echo "=== nftables Status ==="
sudo systemctl status nftables --no-pager | head -10
echo ""

echo "=== Current nftables Rules ==="
sudo nft list ruleset
echo ""

echo "=== Packet Statistics ==="
sudo nft list ruleset -a | grep -E "packets|bytes" | head -20
echo ""

echo "=== System Resources ==="
echo "CPU Usage:"
top -bn1 | head -5
echo ""
echo "Memory Usage:"
free -h
echo ""
echo "Disk Usage:"
df -h /
echo ""

echo "=== Testing External Connectivity ==="
echo -n "External IP: "
curl -s -m 5 http://ifconfig.me || echo "Failed to get external IP"
echo ""
echo ""

echo "=== DNS Resolution Test ==="
echo -n "Resolving example.com: "
nslookup example.com 2>/dev/null | grep -A1 "Name:" || echo "DNS resolution failed"
echo ""

echo "=== Service Status ==="
for service in nftables amazon-ssm-agent amazon-cloudwatch-agent; do
    if systemctl is-enabled $service &>/dev/null; then
        echo "$service: $(systemctl is-active $service)"
    fi
done
echo ""

echo "=========================================="
echo "Diagnostic completed at $(date)"
echo "=========================================="
TEST_EOF
sudo chmod +x /usr/local/bin/test-nat.sh

# 簡易ヘルスチェックスクリプトの作成
cat > /usr/local/bin/check-nat-health.sh << 'HEALTH_EOF'
#!/bin/bash
# Quick health check for NAT instance

ERRORS=0

# IP forwarding確認
if [ "$(cat /proc/sys/net/ipv4/ip_forward)" != "1" ]; then
    echo "ERROR: IP forwarding is disabled"
    ERRORS=$((ERRORS + 1))
fi

# nftablesサービス確認
if ! systemctl is-active nftables >/dev/null 2>&1; then
    echo "ERROR: nftables service is not running"
    ERRORS=$((ERRORS + 1))
fi

# MASQUERADEルール確認
if ! sudo nft list ruleset | grep -q "masquerade"; then
    echo "ERROR: MASQUERADE rule not found"
    ERRORS=$((ERRORS + 1))
fi

# 外部接続確認
if ! curl -s -m 5 http://ifconfig.me >/dev/null 2>&1; then
    echo "WARNING: Cannot reach external network"
    ERRORS=$((ERRORS + 1))
fi

if [ $ERRORS -eq 0 ]; then
    echo "OK: NAT instance is healthy"
    exit 0
else
    echo "CRITICAL: NAT instance has $ERRORS issue(s)"
    exit 1
fi
HEALTH_EOF
sudo chmod +x /usr/local/bin/check-nat-health.sh

# ===== 最終確認 =====
echo ""
echo "============================================"
echo "NAT instance configuration completed!"
echo "Instance ID: $INSTANCE_ID"
echo "Instance Type: $(curl -s http://169.254.169.254/latest/meta-data/instance-type)"
echo "Architecture: $(uname -m)"
echo "VPC CIDR: ${VPC_CIDR}"
echo "Primary Interface: $MAIN_ENI"
echo "Monitoring: $ENABLE_MONITORING"
echo "SSM Agent: $ENABLE_SSM"
echo ""
echo "Diagnostic tools:"
echo "  - Full test: /usr/local/bin/test-nat.sh"
echo "  - Health check: /usr/local/bin/check-nat-health.sh"
if [ "$ENABLE_MONITORING" = "true" ]; then
    echo "  - Metrics script: /usr/local/bin/send-nat-metrics.sh"
fi
echo ""
echo "Logs:"
echo "  - Setup log: /var/log/nat-instance-setup.log"
echo "  - System log: journalctl -u nftables"
echo "============================================"

# 初回診断の実行
echo "Running initial diagnostics..."
/usr/local/bin/check-nat-health.sh

# ヘルスチェックの結果をログに記録
if [ $? -eq 0 ]; then
    echo "SUCCESS: NAT instance is configured and healthy"
else
    echo "WARNING: NAT instance configuration completed but health check reported issues"
    echo "Please run /usr/local/bin/test-nat.sh for detailed diagnostics"
fi

echo "Setup completed at $(date)"