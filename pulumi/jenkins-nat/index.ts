/**
 * pulumi/jenkins-nat/index.ts
 * 
 * JenkinsインフラのNATリソースを構築するPulumiスクリプト
 * ハイアベイラビリティモード: NATゲートウェイ（2つ）
 * ノーマルモード: NATインスタンス（1つ）
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

// 出力用の変数
let natResourceIds: pulumi.Output<string>[] = [];
let natType: string;

if (highAvailabilityMode) {
    // ハイアベイラビリティモード: NATゲートウェイ x2
    pulumi.log.info("Deploying NAT Gateways in High Availability mode");
    natType = "gateway-ha";

    // NATゲートウェイA用のEIP
    const natGatewayEipA = new aws.ec2.Eip(`${projectName}-nat-eip-a`, {
        domain: "vpc",
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
        domain: "vpc",
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

    // NATゲートウェイ固有のエクスポート
    export const natGatewayAId = natGatewayA.id;
    export const natGatewayBId = natGatewayB.id;
    export const natGatewayEipA = natGatewayEipA.publicIp;
    export const natGatewayEipB = natGatewayEipB.publicIp;

} else {
    // ノーマルモード: NATインスタンス x1
    pulumi.log.info("Deploying NAT Instance in Normal mode");
    natType = "instance";

    // 最新のAmazon Linux 2023 AMIを取得
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
        domain: "vpc",
        tags: {
            Name: `${projectName}-nat-instance-eip-${environment}`,
            Environment: environment,
            Type: "nat-instance",
        },
    });

    // NATインスタンス
    const natInstance = new aws.ec2.Instance(`${projectName}-nat-instance`, {
        ami: natAmi.then(ami => ami.id),
        instanceType: natInstanceType,
        keyName: keyName,
        subnetId: publicSubnetAId,
        vpcSecurityGroupIds: [natInstanceSecurityGroupId],
        iamInstanceProfile: natInstanceProfile.name,
        sourceDestCheck: false, // NATとして機能するために必要
        userData: Buffer.from(`#!/bin/bash
# NAT Instance Setup Script
set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "Starting NAT instance configuration..."

# システムアップデート
dnf update -y

# IP転送を有効化
echo "Enabling IP forwarding..."
echo 1 > /proc/sys/net/ipv4/ip_forward
echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
sysctl -p

# iptables設定
echo "Installing and configuring iptables..."
dnf install -y iptables-services
systemctl enable iptables
systemctl start iptables

# NAT設定
echo "Configuring NAT rules..."
iptables -t nat -A POSTROUTING -o eth0 -s ${vpcCidr} -j MASQUERADE
iptables -A FORWARD -i eth0 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i eth0 -o eth0 -j ACCEPT

# 設定を保存
service iptables save

# SSMエージェントの確認と起動
echo "Starting SSM agent..."
dnf install -y amazon-ssm-agent
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

# CloudWatchエージェントインストール
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

echo "NAT instance configuration completed successfully!"
`).toString("base64"),
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

    // NATインスタンス固有のエクスポート
    export const natInstanceId = natInstance.id;
    export const natInstancePublicIp = natInstanceEip.publicIp;
    export const natInstancePrivateIp = natInstance.privateIp;
    export const natInstanceType = natInstanceType;
}

// 共通エクスポート
export const natType = natType;
export const natResourceIds = natResourceIds;
export const highAvailabilityEnabled = highAvailabilityMode;

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
