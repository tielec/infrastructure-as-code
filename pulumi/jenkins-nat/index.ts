/**
 * pulumi/jenkins-nat/index.ts
 * 
 * JenkinsインフラのNATリソースを構築するPulumiスクリプト
 * ハイアベイラビリティモード: NATゲートウェイ（2つ）
 * ノーマルモード: NATインスタンス（1つ）- Amazon Linux 2023 + nftables使用
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "jenkins-infra";
const environment = pulumi.getStack();

// NATモード設定
const highAvailabilityMode = config.getBoolean("highAvailabilityMode") || false;
const natInstanceType = config.get("natInstanceType") || "t3.nano";
const keyName = config.get("keyName");

// スタック参照名を設定から取得
const networkStackName = config.get("networkStackName") || "jenkins-network";
const securityStackName = config.get("securityStackName") || "jenkins-security";

// 既存のスタックから値を取得
const networkStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${networkStackName}/${environment}`);
const securityStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${securityStackName}/${environment}`);

// 必要なリソースIDを取得
const vpcId = networkStack.getOutput("vpcId");
const vpcCidr = networkStack.getOutput("vpcCidr");
const publicSubnetAId = networkStack.getOutput("publicSubnetAId");
const publicSubnetBId = networkStack.getOutput("publicSubnetBId");
const privateRouteTableAId = networkStack.getOutput("privateRouteTableAId");
const privateRouteTableBId = networkStack.getOutput("privateRouteTableBId");
const natInstanceSecurityGroupId = securityStack.getOutput("natInstanceSecurityGroupId");

// 出力用の変数（条件に応じて後で設定）
let natResourceIds: pulumi.Output<string>[] = [];
let natType: string;
let natGatewayAId: pulumi.Output<string> | undefined;
let natGatewayBId: pulumi.Output<string> | undefined;
let natGatewayEipAAddress: pulumi.Output<string> | undefined;
let natGatewayEipBAddress: pulumi.Output<string> | undefined;
let natInstanceId: pulumi.Output<string> | undefined;
let natInstancePublicIp: pulumi.Output<string> | undefined;
let natInstancePrivateIp: pulumi.Output<string> | undefined;

if (highAvailabilityMode) {
    // ハイアベイラビリティモード: NATゲートウェイ x2
    pulumi.log.info("Deploying NAT Gateways in High Availability mode");
    natType = "gateway-ha";

    // NATゲートウェイA用のEIP
    const natGatewayEipA = new aws.ec2.Eip(`${projectName}-nat-eip-a`, {
        tags: {
            Name: `${projectName}-nat-eip-a-${environment}`,
            Environment: environment,
            Type: "nat-gateway",
        },
    });

    // NATゲートウェイA
    const natGatewayA = new aws.ec2.NatGateway(`${projectName}-nat-a`, {
        allocationId: natGatewayEipA.id,
        subnetId: publicSubnetAId,
        tags: {
            Name: `${projectName}-nat-a-${environment}`,
            Environment: environment,
        },
    });

    // プライベートサブネットAからのルート
    const privateRouteA = new aws.ec2.Route(`${projectName}-private-route-a`, {
        routeTableId: privateRouteTableAId,
        destinationCidrBlock: "0.0.0.0/0",
        natGatewayId: natGatewayA.id,
    });

    // NATゲートウェイB用のEIP
    const natGatewayEipB = new aws.ec2.Eip(`${projectName}-nat-eip-b`, {
        tags: {
            Name: `${projectName}-nat-eip-b-${environment}`,
            Environment: environment,
            Type: "nat-gateway",
        },
    });

    // NATゲートウェイB
    const natGatewayB = new aws.ec2.NatGateway(`${projectName}-nat-b`, {
        allocationId: natGatewayEipB.id,
        subnetId: publicSubnetBId,
        tags: {
            Name: `${projectName}-nat-b-${environment}`,
            Environment: environment,
        },
    });

    // プライベートサブネットBからのルート
    const privateRouteB = new aws.ec2.Route(`${projectName}-private-route-b`, {
        routeTableId: privateRouteTableBId,
        destinationCidrBlock: "0.0.0.0/0",
        natGatewayId: natGatewayB.id,
    });

    natResourceIds = [natGatewayA.id, natGatewayB.id];
    
    // NATゲートウェイ固有の出力を設定
    natGatewayAId = natGatewayA.id;
    natGatewayBId = natGatewayB.id;
    natGatewayEipAAddress = natGatewayEipA.publicIp;
    natGatewayEipBAddress = natGatewayEipB.publicIp;

} else {
    // ノーマルモード: NATインスタンス x1 (Amazon Linux 2023)
    pulumi.log.info("Deploying NAT Instance in Normal mode (Amazon Linux 2023 with nftables)");
    natType = "instance";

    // Amazon Linux 2023 AMI
    const natAmi = aws.ec2.getAmi({
        mostRecent: true,
        owners: ["amazon"],
        filters: [{
            name: "name",
            values: ["al2023-ami-*-kernel-*-x86_64"],
        }],
    });

    // NATインスタンス用のIAMロール
    const natInstanceRole = new aws.iam.Role(`${projectName}-nat-instance-role`, {
        assumeRolePolicy: JSON.stringify({
            Version: "2012-10-17",
            Statement: [{
                Action: "sts:AssumeRole",
                Effect: "Allow",
                Principal: {
                    Service: "ec2.amazonaws.com",
                },
            }],
        }),
        tags: {
            Name: `${projectName}-nat-instance-role-${environment}`,
            Environment: environment,
        },
    });

    // 必要な権限を付与
    new aws.iam.RolePolicyAttachment(`${projectName}-nat-instance-ssm-policy`, {
        role: natInstanceRole.name,
        policyArn: "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
    });

    new aws.iam.RolePolicyAttachment(`${projectName}-nat-instance-cloudwatch-policy`, {
        role: natInstanceRole.name,
        policyArn: "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy",
    });

    // インスタンスプロファイル
    const natInstanceProfile = new aws.iam.InstanceProfile(`${projectName}-nat-instance-profile`, {
        role: natInstanceRole.name,
        tags: {
            Environment: environment,
        },
    });

    // NATインスタンス用のElastic IP
    const natInstanceEip = new aws.ec2.Eip(`${projectName}-nat-instance-eip`, {
        tags: {
            Name: `${projectName}-nat-instance-eip-${environment}`,
            Environment: environment,
            Type: "nat-instance",
        },
    });

    // Amazon Linux 2023用の改善されたNAT設定スクリプト
    const userDataScript = `#!/bin/bash
# NAT Instance Setup Script for Amazon Linux 2023 with nftables

# スクリプトの実行ログを記録
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
set -x  # デバッグ用

echo "Starting NAT instance configuration for Amazon Linux 2023..."

# ネットワークが完全に初期化されるまで待機
echo "Waiting for network initialization..."
while ! curl -s http://169.254.169.254/latest/meta-data/instance-id; do
    echo "Waiting for metadata service..."
    sleep 2
done

# インスタンスメタデータの取得
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
echo "Instance ID: $INSTANCE_ID"

# IP forwardingの有効化（永続化）
echo "Enabling IP forwarding..."
echo "net.ipv4.ip_forward = 1" | sudo tee /etc/sysctl.d/99-ip-forward.conf
sudo sysctl -p /etc/sysctl.d/99-ip-forward.conf

# RPフィルターの調整（重要: これがないと動作しない場合がある）
echo "Adjusting RP filter settings..."
echo "net.ipv4.conf.all.rp_filter = 0" | sudo tee -a /etc/sysctl.d/99-ip-forward.conf
echo "net.ipv4.conf.default.rp_filter = 0" | sudo tee -a /etc/sysctl.d/99-ip-forward.conf
sudo sysctl -p /etc/sysctl.d/99-ip-forward.conf

# システムアップデート
echo "Updating system packages..."
sudo dnf update -y

# nftablesのインストール（デフォルトでは含まれていない）
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

# 基本的なnftablesルールの設定
echo "Setting up nftables rules..."
sudo nft add table ip nat
sudo nft add chain ip nat prerouting { type nat hook prerouting priority -100 \\; }
sudo nft add chain ip nat postrouting { type nat hook postrouting priority 100 \\; }

# フィルターテーブルの追加（セキュリティ用）
sudo nft add table ip filter
sudo nft add chain ip filter forward { type filter hook forward priority 0 \\; }

# VPC CIDRの取得
VPC_CIDR="${vpcCidr}"
echo "VPC CIDR: $VPC_CIDR"

# プライマリネットワークインターフェースの検出
MAIN_ENI=$(ip -o link show | awk -F': ' '{print $2}' | grep -E '^(eth|ens|enp)' | head -n1)
echo "Primary network interface: $MAIN_ENI"

# MASQUERADEルールの追加（VPC CIDRからのトラフィック用）
echo "Adding MASQUERADE rule..."
sudo nft add rule ip nat postrouting ip saddr $VPC_CIDR oifname "$MAIN_ENI" masquerade

# フォワーディングルールの追加
echo "Adding forwarding rules..."
sudo nft add rule ip filter forward ip saddr $VPC_CIDR accept
sudo nft add rule ip filter forward ip daddr $VPC_CIDR ct state related,established accept

# 設定ディレクトリの作成
sudo mkdir -p /etc/nftables

# 設定の保存
echo "Saving nftables configuration..."
sudo nft list ruleset | sudo tee /etc/nftables/nat.nft

# nftablesの設定ファイルを更新
cat <<EOF | sudo tee /etc/sysconfig/nftables.conf
# Load saved ruleset on service start
include "/etc/nftables/nat.nft"
EOF

# nftablesサービスの再起動
echo "Restarting nftables service..."
sudo systemctl restart nftables

# 設定の確認
echo "=== Current System Configuration ==="
echo "IP Forwarding: $(cat /proc/sys/net/ipv4/ip_forward)"
echo "RP Filter (all): $(cat /proc/sys/net/ipv4/conf/all/rp_filter)"
echo "RP Filter (default): $(cat /proc/sys/net/ipv4/conf/default/rp_filter)"
echo ""
echo "=== Installed Packages ==="
rpm -qa | grep -E "(iptables|nftables)"
echo ""
echo "=== Network Interfaces ==="
ip addr show
echo ""
echo "=== Routing Table ==="
ip route show
echo ""
echo "=== nftables Service Status ==="
sudo systemctl status nftables --no-pager
echo ""
echo "=== nftables Rules ==="
sudo nft list ruleset
echo ""

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
    wget -q https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
    sudo rpm -U ./amazon-cloudwatch-agent.rpm || echo "CloudWatch agent installation skipped"
    rm -f ./amazon-cloudwatch-agent.rpm
fi

# テストスクリプトの作成
cat > /usr/local/bin/test-nat.sh << 'SCRIPT_EOF'
#!/bin/bash
echo "=== NAT Instance Diagnostics ==="
echo "Date: $(date)"
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
SCRIPT_EOF
sudo chmod +x /usr/local/bin/test-nat.sh

# 最終確認
echo ""
echo "============================================"
echo "NAT instance configuration completed!"
echo "Test with: /usr/local/bin/test-nat.sh"
echo "Check logs: /var/log/user-data.log"
echo "============================================"`;

    // NATインスタンス
    const natInstance = new aws.ec2.Instance(`${projectName}-nat-instance`, {
        ami: natAmi.then(ami => ami.id),
        instanceType: natInstanceType,
        keyName: keyName,
        subnetId: publicSubnetAId,
        vpcSecurityGroupIds: [natInstanceSecurityGroupId],
        iamInstanceProfile: natInstanceProfile.name,
        sourceDestCheck: false, // NATとして機能するために必要
        userData: Buffer.from(userDataScript).toString("base64"),
        tags: {
            Name: `${projectName}-nat-instance-${environment}`,
            Environment: environment,
            Role: "nat-instance",
            InstanceType: natInstanceType,
        },
    });

    // Elastic IPをNATインスタンスに関連付け
    const natInstanceEipAssociation = new aws.ec2.EipAssociation(`${projectName}-nat-instance-eip-assoc`, {
        instanceId: natInstance.id,
        allocationId: natInstanceEip.id,
    });

    // 両方のプライベートサブネットからのルート（単一NATインスタンス経由）
    const privateRouteA = new aws.ec2.Route(`${projectName}-private-route-a`, {
        routeTableId: privateRouteTableAId,
        destinationCidrBlock: "0.0.0.0/0",
        instanceId: natInstance.id,
    }, {
        dependsOn: [natInstance],
    });

    const privateRouteB = new aws.ec2.Route(`${projectName}-private-route-b`, {
        routeTableId: privateRouteTableBId,
        destinationCidrBlock: "0.0.0.0/0",
        instanceId: natInstance.id,
    }, {
        dependsOn: [natInstance],
    });

    // NATインスタンスの自動復旧設定
    const natInstanceRecoveryAlarm = new aws.cloudwatch.MetricAlarm(`${projectName}-nat-instance-recovery`, {
        alarmDescription: "Recover NAT instance when it fails",
        metricName: "StatusCheckFailed_System",
        namespace: "AWS/EC2",
        statistic: "Maximum",
        period: 60,
        evaluationPeriods: 2,
        threshold: 1,
        comparisonOperator: "GreaterThanThreshold",
        dimensions: {
            InstanceId: natInstance.id,
        },
        alarmActions: [
            pulumi.interpolate`arn:aws:automate:${aws.config.region}:ec2:recover`,
        ],
        tags: {
            Environment: environment,
        },
    });

    // CPU使用率アラーム
    const natInstanceCpuAlarm = new aws.cloudwatch.MetricAlarm(`${projectName}-nat-instance-cpu`, {
        alarmDescription: "Alert when NAT instance CPU is high",
        metricName: "CPUUtilization",
        namespace: "AWS/EC2",
        statistic: "Average",
        period: 300,
        evaluationPeriods: 2,
        threshold: 80,
        comparisonOperator: "GreaterThanThreshold",
        dimensions: {
            InstanceId: natInstance.id,
        },
        tags: {
            Environment: environment,
        },
    });

    natResourceIds = [natInstance.id];
    
    // NATインスタンス固有の出力を設定
    natInstanceId = natInstance.id;
    natInstancePublicIp = natInstanceEip.publicIp;
    natInstancePrivateIp = natInstance.privateIp;
}

// 共通エクスポート
export const natTypeExport = natType;
export const natResourceIdsExport = natResourceIds;
export const highAvailabilityEnabled = highAvailabilityMode;

// 条件付きエクスポート（NAT Gateway用）
export const natGatewayAIdExport = natGatewayAId;
export const natGatewayBIdExport = natGatewayBId;
export const natGatewayEipA = natGatewayEipAAddress;
export const natGatewayEipB = natGatewayEipBAddress;

// 条件付きエクスポート（NAT Instance用）
export const natInstanceIdExport = natInstanceId;
export const natInstancePublicIpExport = natInstancePublicIp;
export const natInstancePrivateIpExport = natInstancePrivateIp;
export const natInstanceTypeExport = natInstanceType;

// SSMパラメータにNAT設定を保存
const natConfigParameter = new aws.ssm.Parameter(`${projectName}-nat-config`, {
    name: `/${projectName}/${environment}/nat/config`,
    type: "String",
    value: JSON.stringify({
        type: natType,
        highAvailability: highAvailabilityMode,
        instanceType: natInstanceType,
        createdAt: new Date().toISOString(),
    }),
    description: "NAT configuration for Jenkins infrastructure",
    tags: {
        Environment: environment,
    },
});
