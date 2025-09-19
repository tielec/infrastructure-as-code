/**
 * pulumi/lambda-network/index.ts
 * 
 * Lambda APIインフラのネットワークリソースを構築するPulumiスクリプト
 * VPC、サブネット、ルートテーブルを作成
 * すべての出力をSSMパラメータストアに保存
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

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

// VPC CIDRを取得
const vpcCidrParamResult = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/vpc-cidr`,
});
const vpcCidrBlock = pulumi.output(vpcCidrParamResult).apply(p => p.value);

// VPC CIDRからサブネットのベースオクテットを計算
// dev: 10.1.0.0/16, staging: 10.2.0.0/16, prod: 10.3.0.0/16
const baseOctet = vpcCidrBlock.apply(cidr => {
    const match = cidr.match(/^(\d+)\.(\d+)\.(\d+)\.(\d+)\//);
    if (!match) throw new Error(`Invalid VPC CIDR: ${cidr}`);
    return `${match[1]}.${match[2]}`;
});

// Flow Logs設定を取得
const enableFlowLogsParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/enable-flow-logs`,
});
const enableFlowLogs = pulumi.output(enableFlowLogsParam).apply(p => p.value === "true");

// Isolated Subnets設定を取得（将来用）
const createIsolatedSubnetsParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/phase/isolated-subnets-enabled`,
});
const createIsolatedSubnets = pulumi.output(createIsolatedSubnetsParam).apply(p => p.value === "true");

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
// リソース定義
// ========================================
// VPC作成
const vpc = new aws.ec2.Vpc("vpc", {
    cidrBlock: vpcCidrBlock,
    enableDnsHostnames: true,
    enableDnsSupport: true,
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-vpc-${environment}`,
    },
});

// インターネットゲートウェイ
const igw = new aws.ec2.InternetGateway("igw", {
    vpcId: vpc.id,
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-igw-${environment}`,
    },
});

// アベイラビリティゾーン情報の取得
const azs = pulumi.output(aws.getAvailabilityZones({}));

// ========================================
// サブネット定義
// ========================================
// パブリックサブネットA
const publicSubnetA = new aws.ec2.Subnet("public-subnet-a", {
    vpcId: vpc.id,
    cidrBlock: pulumi.interpolate`${baseOctet}.0.0/24`,
    availabilityZone: azs.names[0],
    mapPublicIpOnLaunch: true,
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-public-subnet-a-${environment}`,
        Type: "public",
    },
});

// パブリックサブネットB
const publicSubnetB = new aws.ec2.Subnet("public-subnet-b", {
    vpcId: vpc.id,
    cidrBlock: pulumi.interpolate`${baseOctet}.2.0/24`,
    availabilityZone: azs.names[1],
    mapPublicIpOnLaunch: true,
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-public-subnet-b-${environment}`,
        Type: "public",
    },
});

// プライベートサブネットA
const privateSubnetA = new aws.ec2.Subnet("private-subnet-a", {
    vpcId: vpc.id,
    cidrBlock: pulumi.interpolate`${baseOctet}.1.0/24`,
    availabilityZone: azs.names[0],
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-private-subnet-a-${environment}`,
        Type: "private",
    },
});

// プライベートサブネットB
const privateSubnetB = new aws.ec2.Subnet("private-subnet-b", {
    vpcId: vpc.id,
    cidrBlock: pulumi.interpolate`${baseOctet}.3.0/24`,
    availabilityZone: azs.names[1],
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-private-subnet-b-${environment}`,
        Type: "private",
    },
});

// ========================================
// Isolated Subnets (将来用)
// ========================================
let isolatedSubnetA: aws.ec2.Subnet | undefined;
let isolatedSubnetB: aws.ec2.Subnet | undefined;
let isolatedRouteTableA: aws.ec2.RouteTable | undefined;
let isolatedRouteTableB: aws.ec2.RouteTable | undefined;

if (createIsolatedSubnets) {
    // アイソレートサブネットA
    isolatedSubnetA = new aws.ec2.Subnet("isolated-subnet-a", {
        vpcId: vpc.id,
        cidrBlock: pulumi.interpolate`${baseOctet}.10.0/24`,
        availabilityZone: azs.names[0],
        tags: {
            ...commonTags,
            Name: pulumi.interpolate`${projectName}-isolated-subnet-a-${environment}`,
            Type: "isolated",
        },
    });

    // アイソレートサブネットB
    isolatedSubnetB = new aws.ec2.Subnet("isolated-subnet-b", {
        vpcId: vpc.id,
        cidrBlock: pulumi.interpolate`${baseOctet}.11.0/24`,
        availabilityZone: azs.names[1],
        tags: {
            ...commonTags,
            Name: pulumi.interpolate`${projectName}-isolated-subnet-b-${environment}`,
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
        tags: commonTags,
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
// SSMパラメータへの保存
// ========================================
// 他のスタックが参照する値をSSMに保存
const paramPrefix = pulumi.interpolate`/${projectName}/${environment}/network`;

// VPC情報
const vpcIdParam = new aws.ssm.Parameter("vpc-id", {
    name: pulumi.interpolate`${paramPrefix}/vpc-id`,
    type: "String",
    value: vpc.id,
    description: "VPC ID for Lambda API infrastructure",
    tags: commonTags,
});

// VPC CIDRはSSMから取得した値なので、再度保存は不要

// Internet Gateway
const igwIdParam = new aws.ssm.Parameter("igw-id", {
    name: pulumi.interpolate`${paramPrefix}/igw-id`,
    type: "String",
    value: igw.id,
    description: "Internet Gateway ID",
    tags: commonTags,
});

// Public Subnets
const publicSubnetAIdParam = new aws.ssm.Parameter("public-subnet-a-id", {
    name: pulumi.interpolate`${paramPrefix}/subnets/public-a-id`,
    type: "String",
    value: publicSubnetA.id,
    description: "Public Subnet A ID",
    tags: commonTags,
});

const publicSubnetBIdParam = new aws.ssm.Parameter("public-subnet-b-id", {
    name: pulumi.interpolate`${paramPrefix}/subnets/public-b-id`,
    type: "String",
    value: publicSubnetB.id,
    description: "Public Subnet B ID",
    tags: commonTags,
});

const publicSubnetIdsParam = new aws.ssm.Parameter("public-subnet-ids", {
    name: pulumi.interpolate`${paramPrefix}/subnets/public-ids`,
    type: "StringList",
    value: pulumi.interpolate`${publicSubnetA.id},${publicSubnetB.id}`,
    description: "Public Subnet IDs (comma-separated)",
    tags: commonTags,
});

// Private Subnets
const privateSubnetAIdParam = new aws.ssm.Parameter("private-subnet-a-id", {
    name: pulumi.interpolate`${paramPrefix}/subnets/private-a-id`,
    type: "String",
    value: privateSubnetA.id,
    description: "Private Subnet A ID",
    tags: commonTags,
});

const privateSubnetBIdParam = new aws.ssm.Parameter("private-subnet-b-id", {
    name: pulumi.interpolate`${paramPrefix}/subnets/private-b-id`,
    type: "String",
    value: privateSubnetB.id,
    description: "Private Subnet B ID",
    tags: commonTags,
});

const privateSubnetIdsParam = new aws.ssm.Parameter("private-subnet-ids", {
    name: pulumi.interpolate`${paramPrefix}/subnets/private-ids`,
    type: "StringList",
    value: pulumi.interpolate`${privateSubnetA.id},${privateSubnetB.id}`,
    description: "Private Subnet IDs (comma-separated)",
    tags: commonTags,
});

// Route Tables
const publicRouteTableIdParam = new aws.ssm.Parameter("public-rt-id", {
    name: pulumi.interpolate`${paramPrefix}/route-tables/public-id`,
    type: "String",
    value: publicRouteTable.id,
    description: "Public Route Table ID",
    tags: commonTags,
});

const privateRouteTableAIdParam = new aws.ssm.Parameter("private-rt-a-id", {
    name: pulumi.interpolate`${paramPrefix}/route-tables/private-a-id`,
    type: "String",
    value: privateRouteTableA.id,
    description: "Private Route Table A ID",
    tags: commonTags,
});

const privateRouteTableBIdParam = new aws.ssm.Parameter("private-rt-b-id", {
    name: pulumi.interpolate`${paramPrefix}/route-tables/private-b-id`,
    type: "String",
    value: privateRouteTableB.id,
    description: "Private Route Table B ID",
    tags: commonTags,
});

const privateRouteTableIdsParam = new aws.ssm.Parameter("private-rt-ids", {
    name: pulumi.interpolate`${paramPrefix}/route-tables/private-ids`,
    type: "StringList",
    value: pulumi.interpolate`${privateRouteTableA.id},${privateRouteTableB.id}`,
    description: "Private Route Table IDs (comma-separated)",
    tags: commonTags,
});

// Isolated Subnets (将来用) - 空文字列をデフォルトとして保存
if (createIsolatedSubnets && isolatedSubnetA && isolatedSubnetB && isolatedRouteTableA && isolatedRouteTableB) {
    const isolatedSubnetAIdParam = new aws.ssm.Parameter("isolated-subnet-a-id", {
        name: pulumi.interpolate`${paramPrefix}/subnets/isolated-a-id`,
        type: "String",
        value: isolatedSubnetA.id,
        description: "Isolated Subnet A ID",
        tags: commonTags,
});

    const isolatedSubnetBIdParam = new aws.ssm.Parameter("isolated-subnet-b-id", {
        name: pulumi.interpolate`${paramPrefix}/subnets/isolated-b-id`,
        type: "String",
        value: isolatedSubnetB.id,
        description: "Isolated Subnet B ID",
        tags: commonTags,
});

    const isolatedSubnetIdsParam = new aws.ssm.Parameter("isolated-subnet-ids", {
        name: pulumi.interpolate`${paramPrefix}/subnets/isolated-ids`,
        type: "StringList",
        value: pulumi.interpolate`${isolatedSubnetA.id},${isolatedSubnetB.id}`,
        description: "Isolated Subnet IDs (comma-separated)",
        tags: commonTags,
});

    const isolatedRouteTableAIdParam = new aws.ssm.Parameter("isolated-rt-a-id", {
        name: pulumi.interpolate`${paramPrefix}/route-tables/isolated-a-id`,
        type: "String",
        value: isolatedRouteTableA.id,
        description: "Isolated Route Table A ID",
        tags: commonTags,
});

    const isolatedRouteTableBIdParam = new aws.ssm.Parameter("isolated-rt-b-id", {
        name: pulumi.interpolate`${paramPrefix}/route-tables/isolated-b-id`,
        type: "String",
        value: isolatedRouteTableB.id,
        description: "Isolated Route Table B ID",
        tags: commonTags,
});
}
// Isolated Subnetが作成されていない場合、空のSSMパラメータは作成しない

// Flow Logs
if (enableFlowLogs && flowLog && flowLogGroup) {
    const flowLogIdParam = new aws.ssm.Parameter("flow-log-id", {
        name: pulumi.interpolate`${paramPrefix}/flow-logs/id`,
        type: "String",
        value: flowLog.id,
        description: "VPC Flow Log ID",
        tags: commonTags,
});

    const flowLogGroupNameParam = new aws.ssm.Parameter("flow-log-group", {
        name: pulumi.interpolate`${paramPrefix}/flow-logs/log-group-name`,
        type: "String",
        value: flowLogGroup.name,
        description: "VPC Flow Log CloudWatch Log Group Name",
        tags: commonTags,
});
}
// Flow Logsが無効の場合、空のSSMパラメータは作成しない


// ========================================
// エクスポート（表示用のみ）
// ========================================
// エクスポートは表示・確認用のみ
// 他のスタックはSSMパラメータから値を取得すること
export const outputs = {
    stack: "lambda-network",
    environment: environment,
    vpcId: vpc.id,
    vpcCidr: vpc.cidrBlock,
    ssmParameterPrefix: paramPrefix,
};
