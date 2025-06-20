/**
 * pulumi/jenkins-nat/index.ts
 * 
 * JenkinsインフラのNATリソースを構築するPulumiスクリプト
 * ハイアベイラビリティモード: NATゲートウェイ（2つ）
 * ノーマルモード: NATインスタンス（1つ）- Amazon Linux 2023使用
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
// NAT AMIの選択（デフォルトはAmazon Linux 2023）
const useAwsNatAmi = config.getBoolean("useAwsNatAmi") || false;

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
    // ノーマルモード: NATインスタンス x1
    pulumi.log.info(`Deploying NAT Instance in Normal mode (AMI: ${useAwsNatAmi ? 'AWS NAT AMI' : 'Amazon Linux 2023'})`);
    natType = "instance";

    // AMIの選択
    let natAmi;
    if (useAwsNatAmi) {
        // AWS公式のNATインスタンス用AMI（古いが動作確認済み）
        natAmi = aws.ec2.getAmi({
            mostRecent: true,
            owners: ["amazon"],
            filters: [
                {
                    name: "name",
                    values: ["amzn-ami-vpc-nat-*"],
                },
                {
                    name: "architecture",
                    values: ["x86_64"],
                },
                {
                    name: "virtualization-type",
                    values: ["hvm"],
                },
                {
                    name: "root-device-type",
                    values: ["ebs"],
                },
                {
                    name: "state",
                    values: ["available"],
                },
            ],
        });
    } else {
        // 最新のAmazon Linux 2023 AMI（推奨）
        natAmi = aws.ec2.getAmi({
            mostRecent: true,
            owners: ["amazon"],
            filters: [{
                name: "name",
                values: ["al2023-ami-*-kernel-*-x86_64"],
            }],
        });
    }

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

    // ユーザーデータの選択
    let userDataScript: string;
    if (useAwsNatAmi) {
        // AWS NAT AMI用の最小限の設定
        userDataScript = `#!/bin/bash
# AWS NAT AMI追加設定スクリプト
set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "Starting NAT instance additional configuration..."

# システムアップデート
yum update -y

# SSMエージェントのインストールと起動（必要な場合）
if ! systemctl is-active amazon-ssm-agent > /dev/null 2>&1; then
    echo "Installing SSM agent..."
    yum install -y amazon-ssm-agent
    systemctl enable amazon-ssm-agent
    systemctl start amazon-ssm-agent
fi

echo "NAT instance configuration completed!"`;
    } else {
        // Amazon Linux 2023用の完全なNAT設定
        userDataScript = `#!/bin/bash
# NAT Instance Setup Script for Amazon Linux 2023
set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "Starting NAT instance configuration for Amazon Linux 2023..."

# システムアップデート
dnf update -y

# 必要なパッケージのインストール
dnf install -y iptables-services amazon-ssm-agent

# IP転送を有効化
echo "Enabling IP forwarding..."
echo 1 > /proc/sys/net/ipv4/ip_forward
echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
sysctl -p

# iptablesサービスの有効化
systemctl enable iptables
systemctl start iptables

# iptablesルールの設定（AWS NAT AMIと同じ設定を適用）
echo "Configuring iptables rules..."

# 既存のルールをクリア
iptables -F
iptables -t nat -F
iptables -t mangle -F

# デフォルトポリシーの設定
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT
iptables -P OUTPUT ACCEPT

# NAT設定
VPC_CIDR="${vpcCidr}"
iptables -t nat -A POSTROUTING -o eth0 -s $VPC_CIDR -j MASQUERADE

# フォワーディングルール
# 確立された接続を許可
iptables -A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT
# VPC内からのすべてのトラフィックを許可
iptables -A FORWARD -s $VPC_CIDR -j ACCEPT
# インターネットから戻ってくるトラフィックを許可
iptables -A FORWARD -d $VPC_CIDR -m state --state RELATED,ESTABLISHED -j ACCEPT

# ルールを保存
service iptables save

# SSMエージェントの起動
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

# CloudWatchエージェントのインストール
echo "Installing CloudWatch agent..."
wget -q https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm

# CloudWatch設定
cat > /opt/aws/amazon-cloudwatch-agent/etc/config.json << 'EOF'
{
  "metrics": {
    "namespace": "JenkinsNAT",
    "metrics_collected": {
      "cpu": {
        "measurement": [
          "cpu_usage_active"
        ],
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": [
          "used_percent"
        ],
        "metrics_collection_interval": 60,
        "resources": [
          "/"
        ]
      },
      "mem": {
        "measurement": [
          "mem_used_percent"
        ],
        "metrics_collection_interval": 60
      },
      "netstat": {
        "measurement": [
          "tcp_established",
          "tcp_time_wait"
        ],
        "metrics_collection_interval": 60
      }
    }
  }
}
EOF

# CloudWatchエージェント起動
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json

# 動作確認
echo "Verifying NAT configuration..."
echo "IP Forwarding: $(cat /proc/sys/net/ipv4/ip_forward)"
echo "iptables NAT rules:"
iptables -t nat -L POSTROUTING -n -v
echo "iptables FORWARD rules:"
iptables -L FORWARD -n -v

echo "NAT instance configuration completed successfully!"`;
    }

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
            AMIType: useAwsNatAmi ? "aws-nat-ami" : "amazon-linux-2023",
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
export const natAmiType = useAwsNatAmi ? "aws-nat-ami" : "amazon-linux-2023";

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
        amiType: useAwsNatAmi ? "aws-nat-ami" : "amazon-linux-2023",
        createdAt: new Date().toISOString(),
    }),
    description: "NAT configuration for Jenkins infrastructure",
    tags: {
        Environment: environment,
    },
});
