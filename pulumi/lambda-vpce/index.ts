/**
 * pulumi/lambda-vpce/index.ts
 * 
 * Lambda APIインフラのVPCエンドポイントを構築するPulumiスクリプト
 * Gateway型とInterface型のVPCエンドポイントを作成
 * Phase 1: S3（Gateway型）、Secrets Manager/KMS（Interface型）
 * Phase 2: DynamoDB（Gateway型）、その他のAWSサービス
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// 設計書に基づいたVpceConfig interface
interface VpceConfig {
    projectName: string;
    networkStackName: string;
    securityStackName: string;
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
const environment = pulumi.getStack();

// スタック参照名を設定から取得
const networkStackName = config.get("networkStackName") || "lambda-network";
const securityStackName = config.get("securityStackName") || "lambda-security";

// VPCエンドポイント設定
const enableS3Endpoint = config.getBoolean("enableS3Endpoint") !== false; // デフォルトtrue
const enableDynamoDBEndpoint = config.getBoolean("enableDynamoDBEndpoint") || false;
const enableSecretsManagerEndpoint = config.getBoolean("enableSecretsManagerEndpoint") || false;
const enableKMSEndpoint = config.getBoolean("enableKMSEndpoint") || false;

// 既存のスタックから値を取得
const networkStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${networkStackName}/${environment}`);
const securityStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${securityStackName}/${environment}`);

// ネットワークリソースの取得
const vpcId = networkStack.getOutput("vpcId");
const privateSubnetIds = networkStack.getOutput("privateSubnetIds");
const privateRouteTableIds = networkStack.getOutput("privateRouteTableIds");
const isolatedRouteTableAId = networkStack.getOutput("isolatedRouteTableAId");
const isolatedRouteTableBId = networkStack.getOutput("isolatedRouteTableBId");

// セキュリティグループの取得
const vpceSecurityGroupId = securityStack.getOutput("vpceSecurityGroupId");

// ===== Gateway型 VPC Endpoints =====

// S3エンドポイント（Phase 1で必須）
let s3Endpoint: aws.ec2.VpcEndpoint | undefined;
if (enableS3Endpoint) {
    s3Endpoint = new aws.ec2.VpcEndpoint(`${projectName}-vpce-s3`, {
        vpcId: vpcId,
        serviceName: pulumi.interpolate`com.amazonaws.${aws.config.region}.s3`,
        vpcEndpointType: "Gateway",
        routeTableIds: pulumi.all([
            privateRouteTableIds,
            isolatedRouteTableAId,
            isolatedRouteTableBId
        ]).apply(([privateRtIds, isoRtA, isoRtB]: [string[], string | undefined, string | undefined]) => {
            const rtIds = [...privateRtIds];
            if (isoRtA) rtIds.push(isoRtA);
            if (isoRtB) rtIds.push(isoRtB);
            return rtIds;
        }),
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
            Type: "gateway",
        },
    });
}

// DynamoDBエンドポイント（Phase 2）
let dynamodbEndpoint: aws.ec2.VpcEndpoint | undefined;
if (enableDynamoDBEndpoint) {
    dynamodbEndpoint = new aws.ec2.VpcEndpoint(`${projectName}-vpce-dynamodb`, {
        vpcId: vpcId,
        serviceName: pulumi.interpolate`com.amazonaws.${aws.config.region}.dynamodb`,
        vpcEndpointType: "Gateway",
        routeTableIds: pulumi.all([
            privateRouteTableIds,
            isolatedRouteTableAId,
            isolatedRouteTableBId
        ]).apply(([privateRtIds, isoRtA, isoRtB]: [string[], string | undefined, string | undefined]) => {
            const rtIds = [...privateRtIds];
            if (isoRtA) rtIds.push(isoRtA);
            if (isoRtB) rtIds.push(isoRtB);
            return rtIds;
        }),
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
            Name: `${projectName}-vpce-dynamodb-${environment}`,
            Environment: environment,
            Type: "gateway",
        },
    });
}

// ===== Interface型 VPC Endpoints =====

// Secrets Managerエンドポイント（本番環境推奨）
let secretsManagerEndpoint: aws.ec2.VpcEndpoint | undefined;
if (enableSecretsManagerEndpoint) {
    secretsManagerEndpoint = new aws.ec2.VpcEndpoint(`${projectName}-vpce-secretsmanager`, {
        vpcId: vpcId,
        serviceName: pulumi.interpolate`com.amazonaws.${aws.config.region}.secretsmanager`,
        vpcEndpointType: "Interface",
        subnetIds: privateSubnetIds,
        securityGroupIds: [vpceSecurityGroupId],
        privateDnsEnabled: true,
        tags: {
            Name: `${projectName}-vpce-secretsmanager-${environment}`,
            Environment: environment,
            Type: "interface",
        },
    });
}

// KMSエンドポイント（本番環境推奨）
let kmsEndpoint: aws.ec2.VpcEndpoint | undefined;
if (enableKMSEndpoint) {
    kmsEndpoint = new aws.ec2.VpcEndpoint(`${projectName}-vpce-kms`, {
        vpcId: vpcId,
        serviceName: pulumi.interpolate`com.amazonaws.${aws.config.region}.kms`,
        vpcEndpointType: "Interface",
        subnetIds: privateSubnetIds,
        securityGroupIds: [vpceSecurityGroupId],
        privateDnsEnabled: true,
        tags: {
            Name: `${projectName}-vpce-kms-${environment}`,
            Environment: environment,
            Type: "interface",
        },
    });
}

// ===== 将来の拡張用エンドポイント（Phase 2以降）=====
// 必要に応じて以下のエンドポイントを追加可能：
// - SQS（DLQ用）
// - SNS（通知用）
// - SSM（パラメータストア用）
// - Lambda（VPC内からのLambda呼び出し用）
// - CloudWatch Logs（ログ送信用）

// ===== コスト情報の計算 =====
const calculateMonthlyCost = () => {
    let cost = 0;
    const hoursPerMonth = 730; // 約30日
    
    // Gateway型エンドポイントは無料
    
    // Interface型エンドポイントのコスト（$0.01/時間 × AZ数）
    const interfaceEndpointCostPerHour = 0.01;
    const azCount = 2; // マルチAZ
    
    if (enableSecretsManagerEndpoint) {
        cost += interfaceEndpointCostPerHour * azCount * hoursPerMonth;
    }
    if (enableKMSEndpoint) {
        cost += interfaceEndpointCostPerHour * azCount * hoursPerMonth;
    }
    
    return cost.toFixed(2);
};

// ===== 設定情報をSSMパラメータに保存 =====
const vpceConfig = new aws.ssm.Parameter(`${projectName}-vpce-config`, {
    name: `/${projectName}/${environment}/vpce/config`,
    type: "String",
    value: pulumi.all([
        s3Endpoint?.id,
        dynamodbEndpoint?.id,
        secretsManagerEndpoint?.id,
        kmsEndpoint?.id,
    ]).apply(([s3Id, dynamodbId, smId, kmsId]: [string | undefined, string | undefined, string | undefined, string | undefined]) => JSON.stringify({
        endpoints: {
            gateway: {
                s3: s3Id ? { id: s3Id, enabled: true } : { enabled: false },
                dynamodb: dynamodbId ? { id: dynamodbId, enabled: true } : { enabled: false },
            },
            interface: {
                secretsManager: smId ? { id: smId, enabled: true } : { enabled: false },
                kms: kmsId ? { id: kmsId, enabled: true } : { enabled: false },
            },
        },
        cost: {
            monthlyEstimate: `$${calculateMonthlyCost()}`,
            breakdown: {
                gateway: "$0 (Free)",
                interface: {
                    secretsManager: enableSecretsManagerEndpoint ? "$14.60/month" : "$0",
                    kms: enableKMSEndpoint ? "$14.60/month" : "$0",
                },
            },
        },
        benefits: [
            "Reduced data transfer costs",
            "Lower latency for AWS service calls",
            "Enhanced security (traffic stays within AWS network)",
            "No NAT Gateway charges for AWS service access",
        ],
        deployment: {
            environment: environment,
            lastUpdated: new Date().toISOString(),
        },
    })),
    description: "VPC Endpoints configuration",
    tags: {
        Environment: environment,
    },
});

// ===== エンドポイント使用ガイド =====
const usageGuide = new aws.ssm.Parameter(`${projectName}-vpce-usage-guide`, {
    name: `/${projectName}/${environment}/vpce/usage-guide`,
    type: "String",
    value: JSON.stringify({
        s3: {
            enabled: enableS3Endpoint,
            usage: "Automatic - S3 API calls from Lambda will use VPC endpoint",
            example: "aws s3 cp file.txt s3://bucket/key",
        },
        dynamodb: {
            enabled: enableDynamoDBEndpoint,
            usage: "Automatic - DynamoDB API calls will use VPC endpoint",
            example: "dynamodb.getItem({ TableName: 'table', Key: {...} })",
        },
        secretsManager: {
            enabled: enableSecretsManagerEndpoint,
            usage: "Automatic with private DNS - Uses VPC endpoint",
            example: "secretsmanager.getSecretValue({ SecretId: 'secret-name' })",
        },
        kms: {
            enabled: enableKMSEndpoint,
            usage: "Automatic with private DNS - Uses VPC endpoint",
            example: "kms.decrypt({ CiphertextBlob: encrypted })",
        },
        troubleshooting: [
            "Check security group allows HTTPS (443) from Lambda",
            "Verify private DNS is enabled for interface endpoints",
            "Test with AWS CLI: aws s3 ls --debug",
            "Check VPC endpoint policy allows required actions",
        ],
    }),
    description: "VPC Endpoints usage guide",
    tags: {
        Environment: environment,
    },
});

// エクスポート
export const s3EndpointId = s3Endpoint?.id;
export const dynamodbEndpointId = dynamodbEndpoint?.id;
export const secretsManagerEndpointId = secretsManagerEndpoint?.id;
export const kmsEndpointId = kmsEndpoint?.id;

// 設定情報のエクスポート
export const vpceConfiguration = {
    gateway: {
        s3: enableS3Endpoint,
        dynamodb: enableDynamoDBEndpoint,
    },
    interface: {
        secretsManager: enableSecretsManagerEndpoint,
        kms: enableKMSEndpoint,
    },
    estimatedMonthlyCost: calculateMonthlyCost(),
};

// サマリー
export const summary = {
    totalEndpoints: [
        enableS3Endpoint,
        enableDynamoDBEndpoint,
        enableSecretsManagerEndpoint,
        enableKMSEndpoint,
    ].filter(Boolean).length,
    types: {
        gateway: [enableS3Endpoint, enableDynamoDBEndpoint].filter(Boolean).length,
        interface: [enableSecretsManagerEndpoint, enableKMSEndpoint].filter(Boolean).length,
    },
    monthlyCost: `${calculateMonthlyCost()}`,
    environment: environment,
};

// デバッグ情報
export const debugInfo = {
    networkStack: networkStackName,
    securityStack: securityStackName,
    vpcId: vpcId,
    privateSubnetIds: privateSubnetIds,
    vpceSecurityGroupId: vpceSecurityGroupId,
};
