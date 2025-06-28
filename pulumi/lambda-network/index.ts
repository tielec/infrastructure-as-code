/**
 * pulumi/lambda-network/index.ts
 * 
 * Lambda APIインフラのネットワークリソースを構築するPulumiスクリプト
 * VPC、サブネット、ルートテーブル、VPCエンドポイントを作成
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// 設計書に基づいたNetworkConfig interface
interface NetworkConfig {
    projectName: string;
    vpcCidr: string;
    enableFlowLogs?: boolean;
    createIsolatedSubnets?: boolean;  // Phase 2で true
    vpcEndpoints: {
        s3: boolean;
        dynamodb?: boolean;
        secretsManager?: boolean;
        kms?: boolean;
    };
}

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "lambda-api";
const vpcCidrBlock = config.get("vpcCidr") || "10.1.0.0/16";
const environment = pulumi.getStack();

// Phase 1/2 の判定
const createIsolatedSubnets = config.getBoolean("createIsolatedSubnets") || false;
const enableFlowLogs = config.getBoolean("enableFlowLogs") || false;

// VPCエンドポイント設定
const enableS3Endpoint = config.getBoolean("enableS3Endpoint") !== false; // デフォルトtrue
const enableDynamoDBEndpoint = config.getBoolean("enableDynamoDBEndpoint") || false;
const enableSecretsManagerEndpoint = config.getBoolean("enableSecretsManagerEndpoint") || false;
const enableKMSEndpoint = config.getBoolean("enableKMSEndpoint") || false;

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

// ===== VPC Endpoints =====
// S3エンドポイント（Phase 1で必須）
let s3Endpoint: aws.ec2.VpcEndpoint | undefined;
if (enableS3Endpoint) {
    s3Endpoint = new aws.ec2.VpcEndpoint(`${projectName}-vpce-s3`, {
        vpcId: vpc.id,
        serviceName: pulumi.interpolate`com.amazonaws.${aws.config.region}.s3`,
        routeTableIds: [
            privateRouteTableA.id,
            privateRouteTableB.id,
            ...(isolatedRouteTableA ? [isolatedRouteTableA.id] : []),
            ...(isolatedRouteTableB ? [isolatedRouteTableB.id] : []),
        ],
        policy: JSON.stringify({
            Version: "2012-10-17",
            Statement: [{
                Effect: "Allow",
                Principal: "*",
                Action: "*",
                Resource: "*",
            }],
        }),
        tags: {
            Name: `${projectName}-vpce-s3-${environment}`,
            Environment: environment,
        },
    });
}

// DynamoDBエンドポイント（Phase 2）
let dynamodbEndpoint: aws.ec2.VpcEndpoint | undefined;
if (enableDynamoDBEndpoint) {
    dynamodbEndpoint = new aws.ec2.VpcEndpoint(`${projectName}-vpce-dynamodb`, {
        vpcId: vpc.id,
        serviceName: pulumi.interpolate`com.amazonaws.${aws.config.region}.dynamodb`,
        routeTableIds: [
            privateRouteTableA.id,
            privateRouteTableB.id,
            ...(isolatedRouteTableA ? [isolatedRouteTableA.id] : []),
            ...(isolatedRouteTableB ? [isolatedRouteTableB.id] : []),
        ],
        tags: {
            Name: `${projectName}-vpce-dynamodb-${environment}`,
            Environment: environment,
        },
    });
}

// Secrets Managerエンドポイント（本番環境推奨）
let secretsManagerEndpoint: aws.ec2.VpcEndpoint | undefined;
if (enableSecretsManagerEndpoint) {
    secretsManagerEndpoint = new aws.ec2.VpcEndpoint(`${projectName}-vpce-secretsmanager`, {
        vpcId: vpc.id,
        serviceName: pulumi.interpolate`com.amazonaws.${aws.config.region}.secretsmanager`,
        vpcEndpointType: "Interface",
        subnetIds: [privateSubnetA.id, privateSubnetB.id],
        privateDnsEnabled: true,
        tags: {
            Name: `${projectName}-vpce-secretsmanager-${environment}`,
            Environment: environment,
        },
    });
}

// KMSエンドポイント（本番環境推奨）
let kmsEndpoint: aws.ec2.VpcEndpoint | undefined;
if (enableKMSEndpoint) {
    kmsEndpoint = new aws.ec2.VpcEndpoint(`${projectName}-vpce-kms`, {
        vpcId: vpc.id,
        serviceName: pulumi.interpolate`com.amazonaws.${aws.config.region}.kms`,
        vpcEndpointType: "Interface",
        subnetIds: [privateSubnetA.id, privateSubnetB.id],
        privateDnsEnabled: true,
        tags: {
            Name: `${projectName}-vpce-kms-${environment}`,
            Environment: environment,
        },
    });
}

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

// VPCエンドポイントのエクスポート
export const s3EndpointId = s3Endpoint?.id;
export const dynamodbEndpointId = dynamodbEndpoint?.id;
export const secretsManagerEndpointId = secretsManagerEndpoint?.id;
export const kmsEndpointId = kmsEndpoint?.id;

// Flow LogsのエクスポートID
export const flowLogId = flowLog?.id;
export const flowLogGroupName = flowLogGroup?.name;

// 設定情報のエクスポート
export const networkConfig = {
    projectName: projectName,
    environment: environment,
    vpcCidr: vpcCidrBlock,
    phase2Enabled: createIsolatedSubnets,
    vpcEndpoints: {
        s3: enableS3Endpoint,
        dynamodb: enableDynamoDBEndpoint,
        secretsManager: enableSecretsManagerEndpoint,
        kms: enableKMSEndpoint,
    },
    flowLogsEnabled: enableFlowLogs,
};
