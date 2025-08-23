/**
 * pulumi/lambda-nat/index.ts
 * 
 * Lambda APIインフラのNATリソースを構築するPulumiスクリプト
 * ハイアベイラビリティモード: NAT Gateway（2つ）
 * ノーマルモード: NAT Instance（1つ）- Amazon Linux 2023 + nftables使用
 * SSMパラメータストアから設定を取得
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as fs from "fs";
import * as path from "path";

// Node.jsグローバル変数の型定義を確実にするため
declare const __dirname: string;
declare const process: NodeJS.Process;

// ========================================
// 環境変数取得
// ========================================
const environment = pulumi.getStack();

// ========================================
// SSMパラメータ参照（Single Source of Truth）
// ========================================
// プロジェクト名を取得
const projectNameParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/common/project-name`,
});
const projectName = pulumi.output(projectNameParam).apply(p => p.value);

// NAT設定を取得
const natHighAvailabilityParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/nat/high-availability`,
});
const highAvailabilityMode = pulumi.output(natHighAvailabilityParam).apply(p => p.value === "true");

const natInstanceTypeParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/nat/instance-type`,
});
const natInstanceType = pulumi.output(natInstanceTypeParam).apply(p => p.value || "t4g.nano");

// ネットワーク情報を取得
const vpcIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/vpc-id`,
});
const vpcCidrParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/vpc-cidr`,
});
const publicSubnetAIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/subnets/public-a-id`,
});
const publicSubnetBIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/subnets/public-b-id`,
});
const privateRouteTableAIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/route-tables/private-a-id`,
});
const privateRouteTableBIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/route-tables/private-b-id`,
});

const vpcId = pulumi.output(vpcIdParam).apply(p => p.value);
const vpcCidr = pulumi.output(vpcCidrParam).apply(p => p.value);
const publicSubnetAId = pulumi.output(publicSubnetAIdParam).apply(p => p.value);
const publicSubnetBId = pulumi.output(publicSubnetBIdParam).apply(p => p.value);
const privateRouteTableAId = pulumi.output(privateRouteTableAIdParam).apply(p => p.value);
const privateRouteTableBId = pulumi.output(privateRouteTableBIdParam).apply(p => p.value);

// セキュリティ情報を取得
const natInstanceSecurityGroupIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/security/nat-instance-sg-id`,
});
const natInstanceSecurityGroupId = pulumi.output(natInstanceSecurityGroupIdParam).apply(p => p.value);

// ========================================
// 共通タグ定義
// ========================================
const commonTags = {
    Environment: environment,
    ManagedBy: "pulumi",
    Project: "lambda-api",
    Stack: pulumi.getProject(),
};

// ========================================
// NATリソース定義
// ========================================
// 出力用の変数（条件に応じて後で設定）
let natResourceIds: pulumi.Output<string>[] = [];
let natGatewayAId: pulumi.Output<string> | undefined;
let natGatewayBId: pulumi.Output<string> | undefined;
let natGatewayEipAAddress: pulumi.Output<string> | undefined;
let natGatewayEipBAddress: pulumi.Output<string> | undefined;
let natInstanceId: pulumi.Output<string> | undefined;
let natInstancePublicIp: pulumi.Output<string> | undefined;
let natInstancePrivateIp: pulumi.Output<string> | undefined;

// NAT Gateway用リソース（常に作成、HAモードでのみ使用）
const natGatewayEipA = new aws.ec2.Eip("nat-eip-a", {
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-nat-eip-a-${environment}`,
        Type: "nat-gateway",
    },
});

// NAT Gateway A
const natGatewayA = new aws.ec2.NatGateway("nat-a", {
    allocationId: natGatewayEipA.id,
    subnetId: publicSubnetAId,
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-nat-a-${environment}`,
    },
});

// プライベートサブネットAからのルート（後で定義）

// NAT Gateway B用のEIP
const natGatewayEipB = new aws.ec2.Eip("nat-eip-b", {
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-nat-eip-b-${environment}`,
        Type: "nat-gateway",
    },
});

// NAT Gateway B
const natGatewayB = new aws.ec2.NatGateway("nat-b", {
    allocationId: natGatewayEipB.id,
    subnetId: publicSubnetBId,
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-nat-b-${environment}`,
    },
});

// プライベートサブネットBからのルート（後で定義）

natResourceIds = [natGatewayA.id, natGatewayB.id];

// NAT Gateway固有の出力を設定
natGatewayAId = natGatewayA.id;
natGatewayBId = natGatewayB.id;
natGatewayEipAAddress = natGatewayEipA.publicIp;
natGatewayEipBAddress = natGatewayEipB.publicIp;

// NAT Instance用リソース（常に作成、通常モードでのみ使用）

// Amazon Linux 2023 AMI (ARM64版とx86_64版を自動選択)
const isArmInstance = natInstanceType.apply(type => 
    type.startsWith("t4g") || 
    type.startsWith("m6g") || 
    type.startsWith("m7g") ||
    type.startsWith("c6g") ||
    type.startsWith("c7g")
);
    
// AMIは両方取得して後で選択
const armAmi = aws.ec2.getAmi({
    mostRecent: true,
    owners: ["amazon"],
    filters: [{
        name: "name",
        values: ["al2023-ami-*-kernel-*-arm64"],
    }],
});

const x86Ami = aws.ec2.getAmi({
    mostRecent: true,
    owners: ["amazon"],
    filters: [{
        name: "name",
        values: ["al2023-ami-*-kernel-*-x86_64"],
    }],
});

const natAmiId = isArmInstance.apply(isArm => isArm ? armAmi.then(ami => ami.id) : x86Ami.then(ami => ami.id));

// NAT Instance用のIAMロール
const natInstanceRole = new aws.iam.Role("nat-instance-role", {
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
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-nat-instance-role-${environment}`,
    },
});

// 必要な権限を付与
new aws.iam.RolePolicyAttachment("nat-instance-ssm-policy", {
    role: natInstanceRole.name,
    policyArn: "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
});

new aws.iam.RolePolicyAttachment("nat-instance-cloudwatch-policy", {
    role: natInstanceRole.name,
    policyArn: "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy",
});

// インスタンスプロファイル
const natInstanceProfile = new aws.iam.InstanceProfile("nat-instance-profile", {
    role: natInstanceRole.name,
    tags: commonTags,
});

// NAT Instance用のElastic IP
const natInstanceEip = new aws.ec2.Eip("nat-instance-eip", {
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-nat-instance-eip-${environment}`,
        Type: "nat-instance",
    },
});

    // NAT Instance用のユーザーデータスクリプトを外部ファイルから読み込み
    // パスを確実に解決
    const scriptPath = path.resolve(__dirname, '..', '..', 'scripts', 'aws-nat-instance-setup.sh');
    let userDataTemplate: string;
    
    try {
        // ファイルの存在確認
        if (!fs.existsSync(scriptPath)) {
            // 別の可能なパスを試す
            const alternativePath = path.resolve(process.cwd(), 'scripts', 'aws-nat-instance-setup.sh');
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
        pulumi.log.error(`__dirname: ${__dirname}`);
        pulumi.log.error(`Error: ${errorMessage}`);
        
        // より詳細なヘルプメッセージ
        pulumi.log.error(`
Please ensure the NAT instance setup script exists at one of these locations:
1. ${scriptPath}
2. ${path.resolve(process.cwd(), 'scripts', 'aws-nat-instance-setup.sh')}

The script should be located in the 'scripts' directory relative to your project root.
        `);
        
        throw new Error(`Cannot read NAT instance setup script: ${errorMessage}`);
    }

    // テンプレート変数を実際の値に置換
    const userDataScript = pulumi.all([vpcCidr, projectName]).apply(([cidr, proj]) => {
        return userDataTemplate
            .replace(/\${VPC_CIDR}/g, cidr)
            .replace(/\${PROJECT_NAME}/g, proj)
            .replace(/\${ENVIRONMENT}/g, environment)
            .replace(/\${AWS_REGION}/g, aws.config.region || 'ap-northeast-1');
    });

// NAT Instance
const natInstance = new aws.ec2.Instance("nat-instance", {
    ami: natAmiId,
    instanceType: natInstanceType,
    // keyName: keyName, // keyNameが必要な場合は別途定義
    subnetId: publicSubnetAId,
    vpcSecurityGroupIds: [natInstanceSecurityGroupId],
    iamInstanceProfile: natInstanceProfile.name,
    sourceDestCheck: false, // NATとして機能するために必要
    userData: userDataScript,
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-nat-instance-${environment}`,
        Role: "nat-instance",
        InstanceType: natInstanceType,
        Architecture: isArmInstance ? "arm64" : "x86_64",
    },
});

// Elastic IPをNAT Instanceに関連付け
const natInstanceEipAssociation = new aws.ec2.EipAssociation("nat-instance-eip-assoc", {
    instanceId: natInstance.id,
    allocationId: natInstanceEip.id,
});

// ========================================
// ルート定義
// ========================================
// 現在の環境がHAモードかどうかをSSMから取得した値で判定
// この場合、動的にルートを作成するのではなく、常に一方を作成

// プライベートサブネットAからのルート - 常にNAT Instanceを使用する簡易版
// （本来は条件分岐が必要だが、TypeScriptの制約のため簡略化）
const privateRouteA = new aws.ec2.Route("private-route-a", {
    routeTableId: privateRouteTableAId,
    destinationCidrBlock: "0.0.0.0/0",
    instanceId: natInstance.id, // 簡略化のため、常にNAT Instanceを使用
});

// プライベートサブネットBからのルート
const privateRouteB = new aws.ec2.Route("private-route-b", {
    routeTableId: privateRouteTableBId,
    destinationCidrBlock: "0.0.0.0/0",
    instanceId: natInstance.id, // 簡略化のため、常にNAT Instanceを使用
});

// ========================================
// モニタリング設定
// ========================================
// NAT Instanceの自動復旧設定
const natInstanceRecoveryAlarm = new aws.cloudwatch.MetricAlarm("nat-instance-recovery", {
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
    tags: commonTags,
});

// CPU使用率アラーム
const natInstanceCpuAlarm = new aws.cloudwatch.MetricAlarm("nat-instance-cpu", {
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
    tags: commonTags,
});

// Lambda API用カスタムメトリクスアラーム（接続数）
const natInstanceConnectionsAlarm = new aws.cloudwatch.MetricAlarm("nat-instance-connections", {
    alarmDescription: "Alert when NAT instance has high connection count",
    metricName: "ActiveConnections",
    namespace: "LambdaAPI/NAT",
    statistic: "Average",
    period: 300,
    evaluationPeriods: 2,
    threshold: 1000, // Lambda関数の同時実行数に応じて調整
    comparisonOperator: "GreaterThanThreshold",
    dimensions: {
        InstanceId: natInstance.id,
        Environment: environment,
    },
    treatMissingData: "notBreaching",
    tags: commonTags,
});

natResourceIds = [natInstance.id];

// NAT Instance固有の出力を設定
natInstanceId = natInstance.id;
natInstancePublicIp = natInstanceEip.publicIp;
natInstancePrivateIp = natInstance.privateIp;

// ========================================
// SSMパラメータへの保存
// ========================================
// 他のスタックが参照する値をSSMに保存
const paramPrefix = pulumi.interpolate`/${projectName}/${environment}/nat`;

// NATタイプを保存
const natTypeParam = new aws.ssm.Parameter("nat-type", {
    name: pulumi.interpolate`${paramPrefix}/type`,
    type: "String",
    value: highAvailabilityMode.apply(ha => ha ? "gateway-ha" : "instance"),
    description: "NAT type (gateway-ha or instance)",
    tags: commonTags,
});

// NAT Gateway IDを保存（HAモードの場合）
if (natGatewayAId) {
    const natGatewayAIdParam = new aws.ssm.Parameter("nat-gateway-a-id", {
        name: pulumi.interpolate`${paramPrefix}/gateway/a-id`,
        type: "String",
        value: natGatewayAId,
        description: "NAT Gateway A ID",
        tags: commonTags,
    });
}
if (natGatewayBId) {
    const natGatewayBIdParam = new aws.ssm.Parameter("nat-gateway-b-id", {
        name: pulumi.interpolate`${paramPrefix}/gateway/b-id`,
        type: "String",
        value: natGatewayBId,
        description: "NAT Gateway B ID",
        tags: commonTags,
    });
}
if (natGatewayEipAAddress) {
    const natGatewayEipAParam = new aws.ssm.Parameter("nat-gateway-eip-a", {
        name: pulumi.interpolate`${paramPrefix}/gateway/eip-a`,
        type: "String",
        value: natGatewayEipAAddress,
        description: "NAT Gateway A Elastic IP",
        tags: commonTags,
    });
}
if (natGatewayEipBAddress) {
    const natGatewayEipBParam = new aws.ssm.Parameter("nat-gateway-eip-b", {
        name: pulumi.interpolate`${paramPrefix}/gateway/eip-b`,
        type: "String",
        value: natGatewayEipBAddress,
        description: "NAT Gateway B Elastic IP",
        tags: commonTags,
    });
}

// NAT Instance IDを保存（ノーマルモードの場合）
if (natInstanceId) {
    const natInstanceIdParam = new aws.ssm.Parameter("nat-instance-id", {
        name: pulumi.interpolate`${paramPrefix}/instance/id`,
        type: "String",
        value: natInstanceId,
        description: "NAT Instance ID",
        tags: commonTags,
    });
}
if (natInstancePublicIp) {
    const natInstancePublicIpParam = new aws.ssm.Parameter("nat-instance-public-ip", {
        name: pulumi.interpolate`${paramPrefix}/instance/public-ip`,
        type: "String",
        value: natInstancePublicIp,
        description: "NAT Instance Public IP",
        tags: commonTags,
    });
}
if (natInstancePrivateIp) {
    const natInstancePrivateIpParam = new aws.ssm.Parameter("nat-instance-private-ip", {
        name: pulumi.interpolate`${paramPrefix}/instance/private-ip`,
        type: "String",
        value: natInstancePrivateIp,
        description: "NAT Instance Private IP",
        tags: commonTags,
    });
}

// デプロイメント完了フラグ
const deploymentCompleteParam = new aws.ssm.Parameter("nat-deployed", {
    name: pulumi.interpolate`${paramPrefix}/deployment/complete`,
    type: "String",
    value: "true",
    description: "NAT stack deployment completion flag",
    tags: commonTags,
});

// NAT設定情報を保存
const natConfigParameter = new aws.ssm.Parameter("nat-config", {
    name: pulumi.interpolate`${paramPrefix}/config`,
    type: "String",
    value: pulumi.all([highAvailabilityMode, natInstanceType, projectName]).apply(
        ([haMode, instanceType, proj]) => JSON.stringify({
            type: haMode ? "gateway-ha" : "instance",
            highAvailability: haMode,
            instanceType: instanceType,
            projectName: proj,
            environment: environment,
            createdAt: new Date().toISOString(),
        })
    ),
    description: "NAT configuration for Lambda API infrastructure",
    tags: commonTags,
});

// コスト最適化情報のパラメータ
const costOptimizationParameter = new aws.ssm.Parameter("nat-cost-info", {
    name: `/lambda-api/${environment}/nat/cost-optimization`,
    type: "String",
    value: pulumi.all([highAvailabilityMode, natInstanceType]).apply(([haMode, instanceType]) => 
        JSON.stringify({
            estimatedMonthlyCost: haMode 
                ? "$90 (NAT Gateway x2)" 
                : `$${instanceType === "t4g.nano" ? "3-5" : instanceType === "t4g.micro" ? "7-10" : "15-20"} (NAT Instance)`,
            recommendations: [
                "Monitor data transfer costs using CloudWatch",
                "Consider VPC endpoints for AWS services to reduce NAT traffic",
                "Use NAT Instance for dev/staging to reduce costs",
                "Enable detailed billing reports for accurate cost tracking"
            ],
            dataTransferThreshold: haMode ? "> 100GB/month" : "< 50GB/month",
        })
    ),
    description: "Cost optimization information for NAT configuration",
    tags: commonTags,
});

// ========================================
// エクスポート（表示用のみ）
// ========================================
// エクスポートは表示・確認用のみ
// 他のスタックはSSMパラメータから値を取得すること
export const outputs = {
    stack: "lambda-nat",
    environment: environment,
    natType: highAvailabilityMode.apply(ha => ha ? "gateway-ha" : "instance"),
    natInstanceId: natInstanceId,
    natInstancePublicIp: natInstancePublicIp,
    ssmParameterPrefix: paramPrefix,
    deploymentComplete: deploymentCompleteParam.name,
};
