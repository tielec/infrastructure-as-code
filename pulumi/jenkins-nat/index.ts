/**
 * pulumi/jenkins-nat/index.ts
 * 
 * JenkinsインフラのNATリソースを構築するPulumiスクリプト
 * ハイアベイラビリティモード: NATゲートウェイ（2つ）
 * ノーマルモード: NATインスタンス（1つ）- Amazon Linux 2023 + nftables使用
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as fs from "fs";
import * as path from "path";

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

    // NAT Instance用のユーザーデータスクリプトを外部ファイルから読み込み
    const scriptPath = path.resolve(__dirname, '..', '..', 'scripts', 'aws', 'userdata', 'nat-instance-setup.sh');
    let userDataTemplate: string;
    
    try {
        // ファイルの存在確認
        if (!fs.existsSync(scriptPath)) {
            // 別の可能なパスを試す
            const alternativePath = path.resolve(process.cwd(), 'scripts', 'aws', 'userdata', 'nat-instance-setup.sh');
            if (fs.existsSync(alternativePath)) {
                userDataTemplate = fs.readFileSync(alternativePath, 'utf8');
                pulumi.log.info(`Successfully loaded NAT instance setup script from alternative path: ${alternativePath}`);
            } else {
                throw new Error(`Script not found at ${scriptPath} or ${alternativePath}`);
            }
        } else {
            userDataTemplate = fs.readFileSync(scriptPath, 'utf8');
            pulumi.log.info(`Successfully loaded NAT instance setup script from: ${scriptPath}`);
        }
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        pulumi.log.error(`Failed to read NAT instance setup script`);
        pulumi.log.error(`Attempted path: ${scriptPath}`);
        pulumi.log.error(`Current directory: ${process.cwd()}`);
        pulumi.log.error(`Error: ${errorMessage}`);
        
        throw new Error(`Cannot read NAT instance setup script: ${errorMessage}`);
    }

    // テンプレート変数を実際の値に置換
    const userDataScript = pulumi.all([vpcCidr, projectName]).apply(([cidr, proj]) => {
        return userDataTemplate
            .replace(/\$\{VPC_CIDR\}/g, cidr)
            .replace(/\$\{PROJECT_NAME\}/g, proj)
            .replace(/\$\{ENVIRONMENT\}/g, environment)
            .replace(/\$\{AWS_REGION\}/g, aws.config.region || 'ap-northeast-1')
            .replace(/\$\{ENABLE_MONITORING\}/g, 'false')  // Jenkins環境ではモニタリングを無効化
            .replace(/\$\{ENABLE_SSM\}/g, 'true');  // SSMエージェントは有効化
    });
;

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
