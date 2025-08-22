/**
 * pulumi/lambda-network/index.ts
 * 
 * Lambda APIインフラのネットワークリソースを構築するPulumiスクリプト
 * VPC、サブネット、ルートテーブルを作成
 * すべての出力をSSMパラメータストアに保存
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// 設計書に基づいたNetworkConfig interface
interface NetworkConfig {
    projectName: string;
    vpcCidr: string;
    enableFlowLogs?: boolean;
    createIsolatedSubnets?: boolean;  // Phase 2で true
}

// 環境変数とスタック名を取得
const environment = pulumi.getStack();

// SSMパラメータストアから設定を取得（Single Source of Truth）
const projectNameParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/common/project-name`,
});

const vpcCidrParamResult = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/vpc-cidr`,
});

const enableFlowLogsParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/enable-flow-logs`,
});

const createIsolatedSubnetsParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/phase/isolated-subnets-enabled`,
});

// SSMから取得した値を使用
const projectName = pulumi.output(projectNameParam).apply(p => p.value);
const vpcCidrBlock = pulumi.output(vpcCidrParamResult).apply(p => p.value);
const enableFlowLogs = pulumi.output(enableFlowLogsParam).apply(p => p.value === "true");
const createIsolatedSubnets = pulumi.output(createIsolatedSubnetsParam).apply(p => p.value === "true");

// VPC作成
const vpc = new aws.ec2.Vpc("lambda-api-vpc", {
    cidrBlock: vpcCidrBlock,
    enableDnsHostnames: true,
    enableDnsSupport: true,
    tags: {
        Name: pulumi.interpolate`${projectName}-vpc-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// インターネットゲートウェイ
const igw = new aws.ec2.InternetGateway("lambda-api-igw", {
    vpcId: vpc.id,
    tags: {
        Name: pulumi.interpolate`${projectName}-igw-${environment}`,
        Environment: environment,
    },
});

// アベイラビリティゾーン情報の取得
const azs = pulumi.output(aws.getAvailabilityZones({}));

// ===== Public Subnets =====
// パブリックサブネットA (10.1.0.0/24)
const publicSubnetA = new aws.ec2.Subnet("lambda-api-public-subnet-a", {
    vpcId: vpc.id,
    cidrBlock: "10.1.0.0/24",
    availabilityZone: azs.names[0],
    mapPublicIpOnLaunch: true,
    tags: {
        Name: pulumi.interpolate`${projectName}-public-subnet-a-${environment}`,
        Environment: environment,
        Type: "public",
    },
});

// パブリックサブネットB (10.1.2.0/24)
const publicSubnetB = new aws.ec2.Subnet("lambda-api-public-subnet-b", {
    vpcId: vpc.id,
    cidrBlock: "10.1.2.0/24",
    availabilityZone: azs.names[1],
    mapPublicIpOnLaunch: true,
    tags: {
        Name: pulumi.interpolate`${projectName}-public-subnet-b-${environment}`,
        Environment: environment,
        Type: "public",
    },
});

// ===== Private Subnets =====
// プライベートサブネットA (10.1.1.0/24)
const privateSubnetA = new aws.ec2.Subnet("lambda-api-private-subnet-a", {
    vpcId: vpc.id,
    cidrBlock: "10.1.1.0/24",
    availabilityZone: azs.names[0],
    tags: {
        Name: pulumi.interpolate`${projectName}-private-subnet-a-${environment}`,
        Environment: environment,
        Type: "private",
    },
});

// プライベートサブネットB (10.1.3.0/24)
const privateSubnetB = new aws.ec2.Subnet("lambda-api-private-subnet-b", {
    vpcId: vpc.id,
    cidrBlock: "10.1.3.0/24",
    availabilityZone: azs.names[1],
    tags: {
        Name: pulumi.interpolate`${projectName}-private-subnet-b-${environment}`,
        Environment: environment,
        Type: "private",
    },
});

// ===== Isolated Subnets (Phase 2) =====
let isolatedSubnetA: aws.ec2.Subnet | undefined;
let isolatedSubnetB: aws.ec2.Subnet | undefined;
let isolatedRouteTableA: aws.ec2.RouteTable | undefined;
let isolatedRouteTableB: aws.ec2.RouteTable | undefined;

if (createIsolatedSubnets) {
    // アイソレートサブネットA (10.1.10.0/24)
    isolatedSubnetA = new aws.ec2.Subnet("lambda-api-isolated-subnet-a", {
        vpcId: vpc.id,
        cidrBlock: "10.1.10.0/24",
        availabilityZone: azs.names[0],
        tags: {
            Name: pulumi.interpolate`${projectName}-isolated-subnet-a-${environment}`,
            Environment: environment,
            Type: "isolated",
        },
    });

    // アイソレートサブネットB (10.1.11.0/24)
    isolatedSubnetB = new aws.ec2.Subnet("lambda-api-isolated-subnet-b", {
        vpcId: vpc.id,
        cidrBlock: "10.1.11.0/24",
        availabilityZone: azs.names[1],
        tags: {
            Name: pulumi.interpolate`${projectName}-isolated-subnet-b-${environment}`,
            Environment: environment,
            Type: "isolated",
        },
    });

    // アイソレートルートテーブルA
    isolatedRouteTableA = new aws.ec2.RouteTable("lambda-api-isolated-rt-a", {
        vpcId: vpc.id,
        tags: {
            Name: pulumi.interpolate`${projectName}-isolated-rt-a-${environment}`,
            Environment: environment,
        },
    });

    // アイソレートルートテーブルB  
    isolatedRouteTableB = new aws.ec2.RouteTable("lambda-api-isolated-rt-b", {
        vpcId: vpc.id,
        tags: {
            Name: pulumi.interpolate`${projectName}-isolated-rt-b-${environment}`,
            Environment: environment,
        },
    });

    // アイソレートサブネットとルートテーブルの関連付け
    new aws.ec2.RouteTableAssociation("lambda-api-isolated-rta-a", {
        subnetId: isolatedSubnetA.id,
        routeTableId: isolatedRouteTableA.id,
    });

    new aws.ec2.RouteTableAssociation("lambda-api-isolated-rta-b", {
        subnetId: isolatedSubnetB.id,
        routeTableId: isolatedRouteTableB.id,
    });
}

// ===== Route Tables =====
// パブリックルートテーブル
const publicRouteTable = new aws.ec2.RouteTable("lambda-api-public-rt", {
    vpcId: vpc.id,
    tags: {
        Name: pulumi.interpolate`${projectName}-public-rt-${environment}`,
        Environment: environment,
    },
});

// パブリックルート（インターネットゲートウェイ向け）
const publicRoute = new aws.ec2.Route("lambda-api-public-route", {
    routeTableId: publicRouteTable.id,
    destinationCidrBlock: "0.0.0.0/0",
    gatewayId: igw.id,
});

// パブリックサブネットとルートテーブルの関連付け
const publicRtAssociationA = new aws.ec2.RouteTableAssociation("lambda-api-public-rta-a", {
    subnetId: publicSubnetA.id,
    routeTableId: publicRouteTable.id,
});

const publicRtAssociationB = new aws.ec2.RouteTableAssociation("lambda-api-public-rta-b", {
    subnetId: publicSubnetB.id,
    routeTableId: publicRouteTable.id,
});

// プライベートルートテーブルA
const privateRouteTableA = new aws.ec2.RouteTable("lambda-api-private-rt-a", {
    vpcId: vpc.id,
    tags: {
        Name: pulumi.interpolate`${projectName}-private-rt-a-${environment}`,
        Environment: environment,
    },
});

// プライベートルートテーブルB
const privateRouteTableB = new aws.ec2.RouteTable("lambda-api-private-rt-b", {
    vpcId: vpc.id,
    tags: {
        Name: pulumi.interpolate`${projectName}-private-rt-b-${environment}`,
        Environment: environment,
    },
});

// プライベートサブネットとルートテーブルの関連付け
const privateRtAssociationA = new aws.ec2.RouteTableAssociation("lambda-api-private-rta-a", {
    subnetId: privateSubnetA.id,
    routeTableId: privateRouteTableA.id,
});

const privateRtAssociationB = new aws.ec2.RouteTableAssociation("lambda-api-private-rta-b", {
    subnetId: privateSubnetB.id,
    routeTableId: privateRouteTableB.id,
});

// ===== VPC Flow Logs (オプション) =====
let flowLogGroup: aws.cloudwatch.LogGroup | undefined;
let flowLog: aws.ec2.FlowLog | undefined;

if (enableFlowLogs) {
    // Flow Logs用のCloudWatch Logsグループ
    flowLogGroup = new aws.cloudwatch.LogGroup("lambda-api-vpc-flow-logs", {
        name: pulumi.interpolate`/aws/vpc/${projectName}-${environment}`,
        retentionInDays: environment === "prod" ? 14 : 3,
        tags: {
            Environment: environment,
        },
    });

    // Flow Logs用のIAMロール
    const flowLogRole = new aws.iam.Role("lambda-api-flow-log-role", {
        assumeRolePolicy: JSON.stringify({
            Version: "2012-10-17",
            Statement: [{
                Effect: "Allow",
                Principal: {
                    Service: "vpc-flow-logs.amazonaws.com",
                },
                Action: "sts:AssumeRole",
            }],
        }),
        tags: {
            Environment: environment,
        },
    });

    // Flow Logs用のIAMポリシー
    const flowLogPolicy = new aws.iam.RolePolicy("lambda-api-flow-log-policy", {
        role: flowLogRole.id,
        policy: JSON.stringify({
            Version: "2012-10-17",
            Statement: [{
                Effect: "Allow",
                Action: [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogGroups",
                    "logs:DescribeLogStreams",
                ],
                Resource: "*",
            }],
        }),
    });

    // VPC Flow Logs
    flowLog = new aws.ec2.FlowLog("lambda-api-vpc-flow-log", {
        iamRoleArn: flowLogRole.arn,
        logDestinationType: "cloud-watch-logs",
        logGroupName: flowLogGroup.name,
        trafficType: "ALL",
        vpcId: vpc.id,
        tags: {
            Name: pulumi.interpolate`${projectName}-vpc-flow-log-${environment}`,
            Environment: environment,
        },
    }, {
        dependsOn: [flowLogPolicy],
    });
}

// ========================================
// エクスポート（最小限に限定）
// ========================================
// すべての値はSSMパラメータストアに保存されているため、
// stack outputは必要最小限のみエクスポート

// デプロイメント確認用の基本情報のみ
export const deploymentInfo = {
    stack: "lambda-network",
    environment: environment,
    timestamp: new Date().toISOString(),
    ssmParameterPrefix: pulumi.interpolate`/${projectName}/${environment}/network`,
};

// SSMパラメータストアに個別の出力を保存
const paramPrefix = pulumi.interpolate`/${projectName}/${environment}/network`;

// VPC情報
const vpcIdParam = new aws.ssm.Parameter("lambda-api-vpc-id", {
    name: pulumi.interpolate`${paramPrefix}/vpc-id`,
    type: "String",
    value: vpc.id,
    description: "VPC ID for Lambda API infrastructure",
            tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
});

const vpcCidrSsmParam = new aws.ssm.Parameter("lambda-api-vpc-cidr", {
    name: pulumi.interpolate`${paramPrefix}/vpc-cidr`,
    type: "String",
    value: vpc.cidrBlock,
    description: "VPC CIDR block",
            tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
});

// Internet Gateway
const igwIdParam = new aws.ssm.Parameter("lambda-api-igw-id", {
    name: pulumi.interpolate`${paramPrefix}/igw-id`,
    type: "String",
    value: igw.id,
    description: "Internet Gateway ID",
            tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
});

// Public Subnets
const publicSubnetAIdParam = new aws.ssm.Parameter("lambda-api-public-subnet-a-id", {
    name: pulumi.interpolate`${paramPrefix}/subnets/public-a-id`,
    type: "String",
    value: publicSubnetA.id,
    description: "Public Subnet A ID",
            tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
});

const publicSubnetBIdParam = new aws.ssm.Parameter("lambda-api-public-subnet-b-id", {
    name: pulumi.interpolate`${paramPrefix}/subnets/public-b-id`,
    type: "String",
    value: publicSubnetB.id,
    description: "Public Subnet B ID",
            tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
});

const publicSubnetIdsParam = new aws.ssm.Parameter("lambda-api-public-subnet-ids", {
    name: pulumi.interpolate`${paramPrefix}/subnets/public-ids`,
    type: "StringList",
    value: pulumi.interpolate`${publicSubnetA.id},${publicSubnetB.id}`,
    description: "Public Subnet IDs (comma-separated)",
            tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
});

// Private Subnets
const privateSubnetAIdParam = new aws.ssm.Parameter("lambda-api-private-subnet-a-id", {
    name: pulumi.interpolate`${paramPrefix}/subnets/private-a-id`,
    type: "String",
    value: privateSubnetA.id,
    description: "Private Subnet A ID",
            tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
});

const privateSubnetBIdParam = new aws.ssm.Parameter("lambda-api-private-subnet-b-id", {
    name: pulumi.interpolate`${paramPrefix}/subnets/private-b-id`,
    type: "String",
    value: privateSubnetB.id,
    description: "Private Subnet B ID",
            tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
});

const privateSubnetIdsParam = new aws.ssm.Parameter("lambda-api-private-subnet-ids", {
    name: pulumi.interpolate`${paramPrefix}/subnets/private-ids`,
    type: "StringList",
    value: pulumi.interpolate`${privateSubnetA.id},${privateSubnetB.id}`,
    description: "Private Subnet IDs (comma-separated)",
            tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
});

// Route Tables
const publicRouteTableIdParam = new aws.ssm.Parameter("lambda-api-public-rt-id", {
    name: pulumi.interpolate`${paramPrefix}/route-tables/public-id`,
    type: "String",
    value: publicRouteTable.id,
    description: "Public Route Table ID",
            tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
});

const privateRouteTableAIdParam = new aws.ssm.Parameter("lambda-api-private-rt-a-id", {
    name: pulumi.interpolate`${paramPrefix}/route-tables/private-a-id`,
    type: "String",
    value: privateRouteTableA.id,
    description: "Private Route Table A ID",
            tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
});

const privateRouteTableBIdParam = new aws.ssm.Parameter("lambda-api-private-rt-b-id", {
    name: pulumi.interpolate`${paramPrefix}/route-tables/private-b-id`,
    type: "String",
    value: privateRouteTableB.id,
    description: "Private Route Table B ID",
            tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
});

const privateRouteTableIdsParam = new aws.ssm.Parameter("lambda-api-private-rt-ids", {
    name: pulumi.interpolate`${paramPrefix}/route-tables/private-ids`,
    type: "StringList",
    value: pulumi.interpolate`${privateRouteTableA.id},${privateRouteTableB.id}`,
    description: "Private Route Table IDs (comma-separated)",
            tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
});

// Isolated Subnets (Phase 2) - 空文字列をデフォルトとして保存
if (createIsolatedSubnets && isolatedSubnetA && isolatedSubnetB && isolatedRouteTableA && isolatedRouteTableB) {
    const isolatedSubnetAIdParam = new aws.ssm.Parameter("lambda-api-isolated-subnet-a-id", {
        name: pulumi.interpolate`${paramPrefix}/subnets/isolated-a-id`,
        type: "String",
        value: isolatedSubnetA.id,
        description: "Isolated Subnet A ID",
                tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
    });

    const isolatedSubnetBIdParam = new aws.ssm.Parameter("lambda-api-isolated-subnet-b-id", {
        name: pulumi.interpolate`${paramPrefix}/subnets/isolated-b-id`,
        type: "String",
        value: isolatedSubnetB.id,
        description: "Isolated Subnet B ID",
                tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
    });

    const isolatedSubnetIdsParam = new aws.ssm.Parameter("lambda-api-isolated-subnet-ids", {
        name: pulumi.interpolate`${paramPrefix}/subnets/isolated-ids`,
        type: "StringList",
        value: pulumi.interpolate`${isolatedSubnetA.id},${isolatedSubnetB.id}`,
        description: "Isolated Subnet IDs (comma-separated)",
                tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
    });

    const isolatedRouteTableAIdParam = new aws.ssm.Parameter("lambda-api-isolated-rt-a-id", {
        name: pulumi.interpolate`${paramPrefix}/route-tables/isolated-a-id`,
        type: "String",
        value: isolatedRouteTableA.id,
        description: "Isolated Route Table A ID",
                tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
    });

    const isolatedRouteTableBIdParam = new aws.ssm.Parameter("lambda-api-isolated-rt-b-id", {
        name: pulumi.interpolate`${paramPrefix}/route-tables/isolated-b-id`,
        type: "String",
        value: isolatedRouteTableB.id,
        description: "Isolated Route Table B ID",
                tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
    });
} else {
    // Phase 1の場合は空文字列を設定
    const isolatedSubnetAIdParam = new aws.ssm.Parameter("lambda-api-isolated-subnet-a-id", {
        name: pulumi.interpolate`${paramPrefix}/subnets/isolated-a-id`,
        type: "String",
        value: "",
        description: "Isolated Subnet A ID (not created in Phase 1)",
                tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
    });

    const isolatedSubnetBIdParam = new aws.ssm.Parameter("lambda-api-isolated-subnet-b-id", {
        name: pulumi.interpolate`${paramPrefix}/subnets/isolated-b-id`,
        type: "String",
        value: "",
        description: "Isolated Subnet B ID (not created in Phase 1)",
                tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
    });

    const isolatedSubnetIdsParam = new aws.ssm.Parameter("lambda-api-isolated-subnet-ids", {
        name: pulumi.interpolate`${paramPrefix}/subnets/isolated-ids`,
        type: "String",
        value: "",
        description: "Isolated Subnet IDs (not created in Phase 1)",
                tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
    });

    const isolatedRouteTableAIdParam = new aws.ssm.Parameter("lambda-api-isolated-rt-a-id", {
        name: pulumi.interpolate`${paramPrefix}/route-tables/isolated-a-id`,
        type: "String",
        value: "",
        description: "Isolated Route Table A ID (not created in Phase 1)",
                tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
    });

    const isolatedRouteTableBIdParam = new aws.ssm.Parameter("lambda-api-isolated-rt-b-id", {
        name: pulumi.interpolate`${paramPrefix}/route-tables/isolated-b-id`,
        type: "String",
        value: "",
        description: "Isolated Route Table B ID (not created in Phase 1)",
                tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
    });
}

// Flow Logs
if (enableFlowLogs && flowLog && flowLogGroup) {
    const flowLogIdParam = new aws.ssm.Parameter("lambda-api-flow-log-id", {
        name: pulumi.interpolate`${paramPrefix}/flow-logs/id`,
        type: "String",
        value: flowLog.id,
        description: "VPC Flow Log ID",
                tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
    });

    const flowLogGroupNameParam = new aws.ssm.Parameter("lambda-api-flow-log-group", {
        name: pulumi.interpolate`${paramPrefix}/flow-logs/log-group-name`,
        type: "String",
        value: flowLogGroup.name,
        description: "VPC Flow Log CloudWatch Log Group Name",
                tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
    });
} else {
    const flowLogIdParam = new aws.ssm.Parameter("lambda-api-flow-log-id", {
        name: pulumi.interpolate`${paramPrefix}/flow-logs/id`,
        type: "String",
        value: "",
        description: "VPC Flow Log ID (not enabled)",
                tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
    });

    const flowLogGroupNameParam = new aws.ssm.Parameter("lambda-api-flow-log-group", {
        name: pulumi.interpolate`${paramPrefix}/flow-logs/log-group-name`,
        type: "String",
        value: "",
        description: "VPC Flow Log CloudWatch Log Group Name (not enabled)",
                tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
    });
}

// デプロイメント完了フラグ
const deploymentCompleteParam = new aws.ssm.Parameter("lambda-api-network-deployed", {
    name: pulumi.interpolate`${paramPrefix}/deployment/complete`,
    type: "String",
    value: "true",
    description: "Network stack deployment completion flag",
            tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-network" },
    overwrite: true,
});
});

// デプロイ完了の確認用（最小限のエクスポート）
export const deploymentComplete = true;
