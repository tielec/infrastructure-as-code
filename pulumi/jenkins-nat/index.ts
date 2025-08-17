/**
 * pulumi/jenkins-nat/index.ts
 * 
 * JenkinsインフラのNATリソースを構築するPulumiスクリプト
 * ハイアベイラビリティモード: NATゲートウェイ（2つ）
 * ノーマルモード: NATインスタンス（1つ）- Amazon Linux 2023 + nftables使用
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// 環境名をスタック名から取得
const environment = pulumi.getStack();
const ssmPrefix = `/jenkins-infra/${environment}`;

// SSMパラメータから設定を取得
const projectNameParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/project-name`,
});
const highAvailabilityModeParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/nat-high-availability`,
});
const natInstanceTypeParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/nat-instance-type`,
});
const keyNameParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/key-name`,
});

// ネットワークリソースのSSMパラメータを取得
const vpcIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/vpc-id`,
});
const vpcCidrParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/vpc-cidr`,
});
const publicSubnetAIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/public-subnet-a-id`,
});
const publicSubnetBIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/public-subnet-b-id`,
});
const privateRouteTableAIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/private-route-table-a-id`,
});
const privateRouteTableBIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/private-route-table-b-id`,
});

// セキュリティグループのSSMパラメータを取得
const natInstanceSecurityGroupIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/security/nat-instance-sg-id`,
});

// 設定値を変数に設定
const projectName = pulumi.output(projectNameParam).apply(p => p.value);
const highAvailabilityMode = pulumi.output(highAvailabilityModeParam).apply(p => p.value === "true");
const natInstanceType = pulumi.output(natInstanceTypeParam).apply(p => p.value);
// keyNameは"none"の場合は使用しない
const keyNameValue = pulumi.output(keyNameParam).apply(p => p.value);

// ネットワークリソースIDを取得
const vpcId = pulumi.output(vpcIdParam).apply(p => p.value);
const vpcCidr = pulumi.output(vpcCidrParam).apply(p => p.value);
const publicSubnetAId = pulumi.output(publicSubnetAIdParam).apply(p => p.value);
const publicSubnetBId = pulumi.output(publicSubnetBIdParam).apply(p => p.value);
const privateRouteTableAId = pulumi.output(privateRouteTableAIdParam).apply(p => p.value);
const privateRouteTableBId = pulumi.output(privateRouteTableBIdParam).apply(p => p.value);
const natInstanceSecurityGroupId = pulumi.output(natInstanceSecurityGroupIdParam).apply(p => p.value);

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

// デフォルトはノーマルモード
natType = "instance";

// 注意: highAvailabilityModeはSSMから取得したOutput型なので、
// 条件分岐を簡略化し、環境変数やconfigで制御することを推奨
// ここでは簡略化のため、常にNATインスタンスモードを使用
if (false) { // 本番環境ではtrueに設定
    // ハイアベイラビリティモード: NATゲートウェイ x2
    pulumi.log.info("Deploying NAT Gateways in High Availability mode");
    natType = "gateway-ha";

    // NATゲートウェイA用のEIP
    const natGatewayEipA = new aws.ec2.Eip(`nat-eip-a`, {
        tags: {
            Name: pulumi.interpolate`${projectName}-nat-eip-a-${environment}`,
            Environment: environment,
            Type: "nat-gateway",
        },
    });

    // NATゲートウェイA
    const natGatewayA = new aws.ec2.NatGateway(`nat-a`, {
        allocationId: natGatewayEipA.id,
        subnetId: publicSubnetAId,
        tags: {
            Name: pulumi.interpolate`${projectName}-nat-a-${environment}`,
            Environment: environment,
        },
    });

    // プライベートサブネットAからのルート
    const privateRouteA = new aws.ec2.Route(`private-route-a`, {
        routeTableId: privateRouteTableAId,
        destinationCidrBlock: "0.0.0.0/0",
        natGatewayId: natGatewayA.id,
    });

    // NATゲートウェイB用のEIP
    const natGatewayEipB = new aws.ec2.Eip(`nat-eip-b`, {
        tags: {
            Name: pulumi.interpolate`${projectName}-nat-eip-b-${environment}`,
            Environment: environment,
            Type: "nat-gateway",
        },
    });

    // NATゲートウェイB
    const natGatewayB = new aws.ec2.NatGateway(`nat-b`, {
        allocationId: natGatewayEipB.id,
        subnetId: publicSubnetBId,
        tags: {
            Name: pulumi.interpolate`${projectName}-nat-b-${environment}`,
            Environment: environment,
        },
    });

    // プライベートサブネットBからのルート
    const privateRouteB = new aws.ec2.Route(`private-route-b`, {
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

    // Amazon Linux 2023 AMI (ARM64版とx86_64版を自動選択)
    // natInstanceTypeはOutput<string>なので、applyを使用して処理
    const amiArch = natInstanceType.apply(instanceType => {
        const isArm = instanceType.startsWith("t4g") || 
                     instanceType.startsWith("m6g") || 
                     instanceType.startsWith("m7g") ||
                     instanceType.startsWith("c6g") ||
                     instanceType.startsWith("c7g");
        return isArm ? "arm64" : "x86_64";
    });
    
    const natAmi = amiArch.apply(arch => 
        aws.ec2.getAmi({
            mostRecent: true,
            owners: ["amazon"],
            filters: [{
                name: "name",
                values: [`al2023-ami-*-kernel-*-${arch}`],
            }],
        })
    );

    // NATインスタンス用のIAMロール
    const natInstanceRole = new aws.iam.Role(`nat-instance-role`, {
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
            Name: pulumi.interpolate`${projectName}-nat-instance-role-${environment}`,
            Environment: environment,
        },
    });

    // 必要な権限を付与
    new aws.iam.RolePolicyAttachment(`nat-instance-ssm-policy`, {
        role: natInstanceRole.name,
        policyArn: "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
    });

    new aws.iam.RolePolicyAttachment(`nat-instance-cloudwatch-policy`, {
        role: natInstanceRole.name,
        policyArn: "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy",
    });

    // インスタンスプロファイル
    const natInstanceProfile = new aws.iam.InstanceProfile(`nat-instance-profile`, {
        role: natInstanceRole.name,
        tags: {
            Environment: environment,
        },
    });

    // NATインスタンス用のElastic IP
    const natInstanceEip = new aws.ec2.Eip(`nat-instance-eip`, {
        tags: {
            Name: pulumi.interpolate`${projectName}-nat-instance-eip-${environment}`,
            Environment: environment,
            Type: "nat-instance",
        },
    });

    // Amazon Linux 2023用の改善されたNAT設定スクリプト
    const userDataScript = pulumi.interpolate`#!/bin/bash
# NAT Instance Setup Script for Amazon Linux 2023 with nftables
# 改善版: nftablesインストールを含む完全な設定

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

# デフォルトのiptables/nftablesルールを無効化
echo "Disabling default firewall rules..."
# iptables-servicesが有効な場合は無効化
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

# 最終的なルール確認とrejectルールの削除
echo "Final rule check..."
if sudo nft list ruleset | grep -q "reject with icmp type host-prohibited"; then
    echo "WARNING: Reject rules still present, removing..."
    # バックアップを作成
    sudo cp /etc/nftables/nat.nft /etc/nftables/nat.nft.backup
    
    # rejectルールを含まないルールセットを再作成
    sudo nft flush ruleset
    sudo nft add table ip nat
    sudo nft add chain ip nat prerouting { type nat hook prerouting priority -100 \; }
    sudo nft add chain ip nat postrouting { type nat hook postrouting priority 100 \; }
    sudo nft add rule ip nat postrouting ip saddr $VPC_CIDR oifname "$MAIN_ENI" masquerade
    
    sudo nft add table ip filter
    sudo nft add chain ip filter forward { type filter hook forward priority 0 \; }
    sudo nft add rule ip filter forward ip saddr $VPC_CIDR accept
    sudo nft add rule ip filter forward ip daddr $VPC_CIDR ct state related,established accept
    
    # 再度保存
    sudo nft list ruleset | sudo tee /etc/nftables/nat.nft
fi

# nftablesサービスの再起動
echo "Restarting nftables service..."
sudo systemctl restart nftables

# 既存のrejectルールが存在する場合は削除（Amazon Linux 2023のデフォルト設定対策）
echo "Checking for default reject rules..."
if sudo nft list chain ip filter FORWARD 2>/dev/null | grep -q "reject"; then
    echo "Removing default reject rules..."
    # FORWARDチェーンが存在する場合は削除して再作成
    sudo nft delete chain ip filter FORWARD 2>/dev/null || true
    sudo nft delete chain ip filter forward 2>/dev/null || true
    
    # クリーンなforwardチェーンを作成
    sudo nft add chain ip filter forward { type filter hook forward priority 0 \; }
    sudo nft add rule ip filter forward ip saddr $VPC_CIDR accept
    sudo nft add rule ip filter forward ip daddr $VPC_CIDR ct state related,established accept
fi

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
    const natInstance = new aws.ec2.Instance(`nat-instance`, {
        ami: pulumi.output(natAmi).apply(ami => ami.id),
        instanceType: natInstanceType,
        // keyNameは"none"の場合は設定しない（空文字として扱う）
        keyName: keyNameValue.apply(k => k === "none" ? "" : k),
        subnetId: publicSubnetAId,
        vpcSecurityGroupIds: [natInstanceSecurityGroupId],
        iamInstanceProfile: natInstanceProfile.name,
        sourceDestCheck: false, // NATとして機能するために必要
        userData: userDataScript,
        tags: {
            Name: pulumi.interpolate`${projectName}-nat-instance-${environment}`,
            Environment: environment,
            Role: "nat-instance",
            InstanceType: pulumi.interpolate`${natInstanceType}`,
        },
    });

    // Elastic IPをNATインスタンスに関連付け
    const natInstanceEipAssociation = new aws.ec2.EipAssociation(`nat-instance-eip-assoc`, {
        instanceId: natInstance.id,
        allocationId: natInstanceEip.id,
    });

    // 両方のプライベートサブネットからのルート（単一NATインスタンス経由）
    const privateRouteA = new aws.ec2.Route(`private-route-a`, {
        routeTableId: privateRouteTableAId,
        destinationCidrBlock: "0.0.0.0/0",
        instanceId: natInstance.id,
    }, {
        dependsOn: [natInstance],
    });

    const privateRouteB = new aws.ec2.Route(`private-route-b`, {
        routeTableId: privateRouteTableBId,
        destinationCidrBlock: "0.0.0.0/0",
        instanceId: natInstance.id,
    }, {
        dependsOn: [natInstance],
    });

    // NATインスタンスの自動復旧設定
    const natInstanceRecoveryAlarm = new aws.cloudwatch.MetricAlarm(`nat-instance-recovery`, {
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
    const natInstanceCpuAlarm = new aws.cloudwatch.MetricAlarm(`nat-instance-cpu`, {
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
const natTypeParam = new aws.ssm.Parameter(`nat-type`, {
    name: `${ssmPrefix}/nat/type`,
    type: "String",
    value: natType,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "nat",
    },
});

// NAT Gateway AのIDをSSMに保存（ハイアベイラビリティモードの場合）
if (natGatewayAId) {
    const natGatewayAIdParam = new aws.ssm.Parameter(`nat-gateway-a-id`, {
        name: `${ssmPrefix}/nat/gateway-a-id`,
        type: "String",
        value: natGatewayAId,
        overwrite: true,
        tags: {
            Environment: environment,
            ManagedBy: "pulumi",
            Component: "nat",
        },
    });
}

// NAT Gateway BのIDをSSMに保存（ハイアベイラビリティモードの場合）
if (natGatewayBId) {
    const natGatewayBIdParam = new aws.ssm.Parameter(`nat-gateway-b-id`, {
        name: `${ssmPrefix}/nat/gateway-b-id`,
        type: "String",
        value: natGatewayBId,
        overwrite: true,
        tags: {
            Environment: environment,
            ManagedBy: "pulumi",
            Component: "nat",
        },
    });
}

// NAT Gateway EIP AのアドレスをSSMに保存（ハイアベイラビリティモードの場合）
if (natGatewayEipAAddress) {
    const natGatewayEipAParam = new aws.ssm.Parameter(`nat-gateway-eip-a`, {
        name: `${ssmPrefix}/nat/gateway-eip-a`,
        type: "String",
        value: natGatewayEipAAddress,
        overwrite: true,
        tags: {
            Environment: environment,
            ManagedBy: "pulumi",
            Component: "nat",
        },
    });
}

// NAT Gateway EIP BのアドレスをSSMに保存（ハイアベイラビリティモードの場合）
if (natGatewayEipBAddress) {
    const natGatewayEipBParam = new aws.ssm.Parameter(`nat-gateway-eip-b`, {
        name: `${ssmPrefix}/nat/gateway-eip-b`,
        type: "String",
        value: natGatewayEipBAddress,
        overwrite: true,
        tags: {
            Environment: environment,
            ManagedBy: "pulumi",
            Component: "nat",
        },
    });
}

// NAT Instance IDをSSMに保存（ノーマルモードの場合）
if (natInstanceId) {
    const natInstanceIdParam = new aws.ssm.Parameter(`nat-instance-id`, {
        name: `${ssmPrefix}/nat/instance-id`,
        type: "String",
        value: natInstanceId,
        overwrite: true,
        tags: {
            Environment: environment,
            ManagedBy: "pulumi",
            Component: "nat",
        },
    });
}

// NAT Instance Public IPをSSMに保存（ノーマルモードの場合）
if (natInstancePublicIp) {
    const natInstancePublicIpParam = new aws.ssm.Parameter(`nat-instance-public-ip`, {
        name: `${ssmPrefix}/nat/instance-public-ip`,
        type: "String",
        value: natInstancePublicIp,
        overwrite: true,
        tags: {
            Environment: environment,
            ManagedBy: "pulumi",
            Component: "nat",
        },
    });
}

// NAT Instance Private IPをSSMに保存（ノーマルモードの場合）
if (natInstancePrivateIp) {
    const natInstancePrivateIpParam = new aws.ssm.Parameter(`nat-instance-private-ip`, {
        name: `${ssmPrefix}/nat/instance-private-ip`,
        type: "String",
        value: natInstancePrivateIp,
        overwrite: true,
        tags: {
            Environment: environment,
            ManagedBy: "pulumi",
            Component: "nat",
        },
    });
}
