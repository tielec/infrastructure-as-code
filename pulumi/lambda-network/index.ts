/**
 * pulumi/lambda-network/index.ts
 * 
 * Lambda APIインフラのネットワークリソースを構築するPulumiスクリプト
 * VPC、サブネット、ルートテーブルを作成
 * VPCエンドポイントは lambda-vpce スタックに移動
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

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "lambda-api";
const vpcCidrBlock = config.get("vpcCidr") || "10.1.0.0/16";
const environment = pulumi.getStack();

// Phase 1/2 の判定
const createIsolatedSubnets = config.getBoolean("createIsolatedSubnets") || false;
const enableFlowLogs = config.getBoolean("enableFlowLogs") || false;

// VPC作成
const vpc = new aws.ec2.Vpc(`${projectName}-vpc`, {
    cidrBlock: vpcCidrBlock,
    enableDnsHostnames: true,
    enableDnsSupport: true,
    tags: {
        Name: `${projectName}-vpc-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// インターネットゲートウェイ
const igw = new aws.ec2.InternetGateway(`${projectName}-igw`, {
    vpcId: vpc.id,
    tags: {
        Name: `${projectName}-igw-${environment}`,
        Environment: environment,
    },
});

// アベイラビリティゾーン情報の取得
const azs = pulumi.output(aws.getAvailabilityZones({}));

// ===== Public Subnets =====
// パブリックサブネットA (10.1.0.0/24)
const publicSubnetA = new aws.ec2.Subnet(`${projectName}-public-subnet-a`, {
    vpcId: vpc.id,
    cidrBlock: "10.1.0.0/24",
    availabilityZone: azs.names[0],
    mapPublicIpOnLaunch: true,
    tags: {
        Name: `${projectName}-public-subnet-a-${environment}`,
        Environment: environment,
        Type: "public",
    },
});

// パブリックサブネットB (10.1.2.0/24)
const publicSubnetB = new aws.ec2.Subnet(`${projectName}-public-subnet-b`, {
    vpcId: vpc.id,
    cidrBlock: "10.1.2.0/24",
    availabilityZone: azs.names[1],
    mapPublicIpOnLaunch: true,
    tags: {
        Name: `${projectName}-public-subnet-b-${environment}`,
        Environment: environment,
        Type: "public",
    },
});

// ===== Private Subnets =====
// プライベートサブネットA (10.1.1.0/24)
const privateSubnetA = new aws.ec2.Subnet(`${projectName}-private-subnet-a`, {
    vpcId: vpc.id,
    cidrBlock: "10.1.1.0/24",
    availabilityZone: azs.names[0],
    tags: {
        Name: `${projectName}-private-subnet-a-${environment}`,
        Environment: environment,
        Type: "private",
    },
});

// プライベートサブネットB (10.1.3.0/24)
const privateSubnetB = new aws.ec2.Subnet(`${projectName}-private-subnet-b`, {
    vpcId: vpc.id,
    cidrBlock: "10.1.3.0/24",
    availabilityZone: azs.names[1],
    tags: {
        Name: `${projectName}-private-subnet-b-${environment}`,
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
    isolatedSubnetA = new aws.ec2.Subnet(`${projectName}-isolated-subnet-a`, {
        vpcId: vpc.id,
        cidrBlock: "10.1.10.0/24",
        availabilityZone: azs.names[0],
        tags: {
            Name: `${projectName}-isolated-subnet-a-${environment}`,
            Environment: environment,
            Type: "isolated",
        },
    });

    // アイソレートサブネットB (10.1.11.0/24)
    isolatedSubnetB = new aws.ec2.Subnet(`${projectName}-isolated-subnet-b`, {
        vpcId: vpc.id,
        cidrBlock: "10.1.11.0/24",
        availabilityZone: azs.names[1],
        tags: {
            Name: `${projectName}-isolated-subnet-b-${environment}`,
            Environment: environment,
            Type: "isolated",
        },
    });

    // アイソレートルートテーブルA
    isolatedRouteTableA = new aws.ec2.RouteTable(`${projectName}-isolated-rt-a`, {
        vpcId: vpc.id,
        tags: {
            Name: `${projectName}-isolated-rt-a-${environment}`,
            Environment: environment,
        },
    });

    // アイソレートルートテーブルB  
    isolatedRouteTableB = new aws.ec2.RouteTable(`${projectName}-isolated-rt-b`, {
        vpcId: vpc.id,
        tags: {
            Name: `${projectName}-isolated-rt-b-${environment}`,
            Environment: environment,
        },
    });

    // アイソレートサブネットとルートテーブルの関連付け
    new aws.ec2.RouteTableAssociation(`${projectName}-isolated-rta-a`, {
        subnetId: isolatedSubnetA.id,
        routeTableId: isolatedRouteTableA.id,
    });

    new aws.ec2.RouteTableAssociation(`${projectName}-isolated-rta-b`, {
        subnetId: isolatedSubnetB.id,
        routeTableId: isolatedRouteTableB.id,
    });
}

// ===== Route Tables =====
// パブリックルートテーブル
const publicRouteTable = new aws.ec2.RouteTable(`${projectName}-public-rt`, {
    vpcId: vpc.id,
    tags: {
        Name: `${projectName}-public-rt-${environment}`,
        Environment: environment,
    },
});

// パブリックルート（インターネットゲートウェイ向け）
const publicRoute = new aws.ec2.Route(`${projectName}-public-route`, {
    routeTableId: publicRouteTable.id,
    destinationCidrBlock: "0.0.0.0/0",
    gatewayId: igw.id,
});

// パブリックサブネットとルートテーブルの関連付け
const publicRtAssociationA = new aws.ec2.RouteTableAssociation(`${projectName}-public-rta-a`, {
    subnetId: publicSubnetA.id,
    routeTableId: publicRouteTable.id,
});

const publicRtAssociationB = new aws.ec2.RouteTableAssociation(`${projectName}-public-rta-b`, {
    subnetId: publicSubnetB.id,
    routeTableId: publicRouteTable.id,
});

// プライベートルートテーブルA
const privateRouteTableA = new aws.ec2.RouteTable(`${projectName}-private-rt-a`, {
    vpcId: vpc.id,
    tags: {
        Name: `${projectName}-private-rt-a-${environment}`,
        Environment: environment,
    },
});

// プライベートルートテーブルB
const privateRouteTableB = new aws.ec2.RouteTable(`${projectName}-private-rt-b`, {
    vpcId: vpc.id,
    tags: {
        Name: `${projectName}-private-rt-b-${environment}`,
        Environment: environment,
    },
});

// プライベートサブネットとルートテーブルの関連付け
const privateRtAssociationA = new aws.ec2.RouteTableAssociation(`${projectName}-private-rta-a`, {
    subnetId: privateSubnetA.id,
    routeTableId: privateRouteTableA.id,
});

const privateRtAssociationB = new aws.ec2.RouteTableAssociation(`${projectName}-private-rta-b`, {
    subnetId: privateSubnetB.id,
    routeTableId: privateRouteTableB.id,
});

// ===== VPC Flow Logs (オプション) =====
let flowLogGroup: aws.cloudwatch.LogGroup | undefined;
let flowLog: aws.ec2.FlowLog | undefined;

if (enableFlowLogs) {
    // Flow Logs用のCloudWatch Logsグループ
    flowLogGroup = new aws.cloudwatch.LogGroup(`${projectName}-vpc-flow-logs`, {
        name: `/aws/vpc/${projectName}-${environment}`,
        retentionInDays: environment === "prod" ? 14 : 3,
        tags: {
            Environment: environment,
        },
    });

    // Flow Logs用のIAMロール
    const flowLogRole = new aws.iam.Role(`${projectName}-flow-log-role`, {
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
    const flowLogPolicy = new aws.iam.RolePolicy(`${projectName}-flow-log-policy`, {
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
    flowLog = new aws.ec2.FlowLog(`${projectName}-vpc-flow-log`, {
        iamRoleArn: flowLogRole.arn,
        logDestinationType: "cloud-watch-logs",
        logGroupName: flowLogGroup.name,
        trafficType: "ALL",
        vpcId: vpc.id,
        tags: {
            Name: `${projectName}-vpc-flow-log-${environment}`,
            Environment: environment,
        },
    }, {
        dependsOn: [flowLogPolicy],
    });
}

// エクスポート
export const vpcId = vpc.id;
export const vpcCidr = vpc.cidrBlock;
export const publicSubnetIds = [publicSubnetA.id, publicSubnetB.id];
export const privateSubnetIds = [privateSubnetA.id, privateSubnetB.id];
export const publicSubnetAId = publicSubnetA.id;
export const publicSubnetBId = publicSubnetB.id;
export const privateSubnetAId = privateSubnetA.id;
export const privateSubnetBId = privateSubnetB.id;
export const internetGatewayId = igw.id;
export const publicRouteTableId = publicRouteTable.id;
export const privateRouteTableAId = privateRouteTableA.id;
export const privateRouteTableBId = privateRouteTableB.id;
export const privateRouteTableIds = [privateRouteTableA.id, privateRouteTableB.id];

// Phase 2のエクスポート（条件付き）
export const isolatedSubnetIds = createIsolatedSubnets && isolatedSubnetA && isolatedSubnetB
    ? [isolatedSubnetA.id, isolatedSubnetB.id]
    : undefined;
export const isolatedSubnetAId = isolatedSubnetA?.id;
export const isolatedSubnetBId = isolatedSubnetB?.id;
export const isolatedRouteTableAId = isolatedRouteTableA?.id;
export const isolatedRouteTableBId = isolatedRouteTableB?.id;

// Flow LogsのエクスポートID
export const flowLogId = flowLog?.id;
export const flowLogGroupName = flowLogGroup?.name;

// 設定情報のエクスポート
export const networkConfig = {
    projectName: projectName,
    environment: environment,
    vpcCidr: vpcCidrBlock,
    phase2Enabled: createIsolatedSubnets,
    flowLogsEnabled: enableFlowLogs,
};

// SSMパラメータに設定を保存
const networkConfigParameter = new aws.ssm.Parameter(`${projectName}-network-config`, {
    name: `/${projectName}/${environment}/network/config`,
    type: "String",
    value: JSON.stringify({
        vpc: {
            id: vpc.id,
            cidr: vpcCidrBlock,
        },
        subnets: {
            public: {
                a: publicSubnetA.id,
                b: publicSubnetB.id,
            },
            private: {
                a: privateSubnetA.id,
                b: privateSubnetB.id,
            },
            isolated: createIsolatedSubnets ? {
                a: isolatedSubnetA?.id,
                b: isolatedSubnetB?.id,
            } : undefined,
        },
        routeTables: {
            public: publicRouteTable.id,
            private: {
                a: privateRouteTableA.id,
                b: privateRouteTableB.id,
            },
            isolated: createIsolatedSubnets ? {
                a: isolatedRouteTableA?.id,
                b: isolatedRouteTableB?.id,
            } : undefined,
        },
        internetGateway: igw.id,
        phase2Enabled: createIsolatedSubnets,
        flowLogsEnabled: enableFlowLogs,
        deployment: {
            environment: environment,
            lastUpdated: new Date().toISOString(),
        },
    }),
    description: "Network configuration for Lambda API infrastructure",
    tags: {
        Environment: environment,
    },
});

export const networkConfigParameterName = networkConfigParameter.name;
