/**
 * pulumi/lambda-nat/index.ts
 * 
 * Lambda APIインフラのNATリソースを構築するPulumiスクリプト
 * ハイアベイラビリティモード: NAT Gateway（2つ）
 * ノーマルモード: NAT Instance（1つ）- Amazon Linux 2023 + nftables使用
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as fs from "fs";
import * as path from "path";

// Node.jsグローバル変数の型定義を確実にするため
declare const __dirname: string;
declare const process: NodeJS.Process;

// 設計書に基づいたNatConfig interface
interface NatConfig {
    projectName: string;
    highAvailabilityMode: boolean;
    natInstanceType?: string;
    keyName?: string;
    networkStackName: string;
    securityStackName: string;
}

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "lambda-api";
const environment = pulumi.getStack();

// NATモード設定（本番環境はデフォルトでHA）
const highAvailabilityMode = config.getBoolean("highAvailabilityMode") || (environment === "prod");

// NAT Instance設定（設計書のデフォルト値に基づく）
const natInstanceType = config.get("natInstanceType") || (
    environment === "dev" ? "t4g.nano" :
    environment === "staging" ? "t4g.micro" :
    "t4g.small" // 本番でNAT Instanceを使う場合
);
const keyName = config.get("keyName");

// スタック参照名を設定から取得
const networkStackName = config.get("networkStackName") || "lambda-network";
const securityStackName = config.get("securityStackName") || "lambda-security";

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
    // ===== ハイアベイラビリティモード: NAT Gateway x2 =====
    pulumi.log.info("Deploying NAT Gateways in High Availability mode");
    natType = "gateway-ha";

    // NAT Gateway A用のEIP
    const natGatewayEipA = new aws.ec2.Eip(`${projectName}-nat-eip-a`, {
        tags: {
            Name: `${projectName}-nat-eip-a-${environment}`,
            Environment: environment,
            Type: "nat-gateway",
        },
    });

    // NAT Gateway A
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

    // NAT Gateway B用のEIP
    const natGatewayEipB = new aws.ec2.Eip(`${projectName}-nat-eip-b`, {
        tags: {
            Name: `${projectName}-nat-eip-b-${environment}`,
            Environment: environment,
            Type: "nat-gateway",
        },
    });

    // NAT Gateway B
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
    
    // NAT Gateway固有の出力を設定
    natGatewayAId = natGatewayA.id;
    natGatewayBId = natGatewayB.id;
    natGatewayEipAAddress = natGatewayEipA.publicIp;
    natGatewayEipBAddress = natGatewayEipB.publicIp;

} else {
    // ===== ノーマルモード: NAT Instance x1 (Amazon Linux 2023) =====
    pulumi.log.info("Deploying NAT Instance in Normal mode (Amazon Linux 2023 with nftables)");
    natType = "instance";

    // Amazon Linux 2023 AMI (ARM64版とx86_64版を自動選択)
    const isArmInstance = natInstanceType.startsWith("t4g") || 
                         natInstanceType.startsWith("m6g") || 
                         natInstanceType.startsWith("m7g") ||
                         natInstanceType.startsWith("c6g") ||
                         natInstanceType.startsWith("c7g");
    
    const natAmi = aws.ec2.getAmi({
        mostRecent: true,
        owners: ["amazon"],
        filters: [{
            name: "name",
            values: ["al2023-ami-*-kernel-*-" + (isArmInstance ? "arm64" : "x86_64")],
        }],
    });

    // NAT Instance用のIAMロール
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

    // NAT Instance用のElastic IP
    const natInstanceEip = new aws.ec2.Eip(`${projectName}-nat-instance-eip`, {
        tags: {
            Name: `${projectName}-nat-instance-eip-${environment}`,
            Environment: environment,
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
    const userDataScript = pulumi.all([vpcCidr]).apply(([cidr]) => {
        return userDataTemplate
            .replace(/\${VPC_CIDR}/g, cidr)
            .replace(/\${PROJECT_NAME}/g, projectName)
            .replace(/\${ENVIRONMENT}/g, environment)
            .replace(/\${AWS_REGION}/g, aws.config.region || 'ap-northeast-1');
    });

    // NAT Instance
    const natInstance = new aws.ec2.Instance(`${projectName}-nat-instance`, {
        ami: natAmi.then((ami: any) => ami.id),
        instanceType: natInstanceType,
        keyName: keyName,
        subnetId: publicSubnetAId,
        vpcSecurityGroupIds: [natInstanceSecurityGroupId],
        iamInstanceProfile: natInstanceProfile.name,
        sourceDestCheck: false, // NATとして機能するために必要
        userData: userDataScript,
        tags: {
            Name: `${projectName}-nat-instance-${environment}`,
            Environment: environment,
            Role: "nat-instance",
            InstanceType: natInstanceType,
            Architecture: isArmInstance ? "arm64" : "x86_64",
        },
    });

    // Elastic IPをNAT Instanceに関連付け
    const natInstanceEipAssociation = new aws.ec2.EipAssociation(`${projectName}-nat-instance-eip-assoc`, {
        instanceId: natInstance.id,
        allocationId: natInstanceEip.id,
    });

    // 両方のプライベートサブネットからのルート（単一NAT Instance経由）
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

    // NAT Instanceの自動復旧設定
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

    // Lambda API用カスタムメトリクスアラーム（接続数）
    const natInstanceConnectionsAlarm = new aws.cloudwatch.MetricAlarm(`${projectName}-nat-instance-connections`, {
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
        tags: {
            Environment: environment,
        },
    });

    natResourceIds = [natInstance.id];
    
    // NAT Instance固有の出力を設定
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
        projectName: projectName,
        environment: environment,
        createdAt: new Date().toISOString(),
    }),
    description: "NAT configuration for Lambda API infrastructure",
    tags: {
        Environment: environment,
    },
});

// コスト最適化情報のパラメータ
const costOptimizationParameter = new aws.ssm.Parameter(`${projectName}-nat-cost-info`, {
    name: `/${projectName}/${environment}/nat/cost-optimization`,
    type: "String",
    value: JSON.stringify({
        estimatedMonthlyCost: highAvailabilityMode 
            ? "$90 (NAT Gateway x2)" 
            : `$${natInstanceType === "t4g.nano" ? "3-5" : natInstanceType === "t4g.micro" ? "7-10" : "15-20"} (NAT Instance)`,
        recommendations: [
            "Monitor data transfer costs using CloudWatch",
            "Consider VPC endpoints for AWS services to reduce NAT traffic",
            "Use NAT Instance for dev/staging to reduce costs",
            "Enable detailed billing reports for accurate cost tracking"
        ],
        dataTransferThreshold: highAvailabilityMode ? "> 100GB/month" : "< 50GB/month",
    }),
    description: "Cost optimization information for NAT configuration",
    tags: {
        Environment: environment,
    },
});

export const natConfigParameterName = natConfigParameter.name;
export const costInfoParameterName = costOptimizationParameter.name;
