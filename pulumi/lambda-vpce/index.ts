/**
 * pulumi/lambda-vpce/index.ts
 * 
 * Lambda APIインフラのVPCエンドポイントを構築するPulumiスクリプト
 * Gateway型とInterface型のVPCエンドポイントを作成
 * SSMパラメータストアから設定を取得
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "lambda-api";
const environment = pulumi.getStack();

// SSMパラメータストアからネットワーク情報を取得
const vpcIdParam = aws.ssm.getParameter({
    name: `/${projectName}/${environment}/network/vpc-id`,
});
const privateSubnetAIdParam = aws.ssm.getParameter({
    name: `/${projectName}/${environment}/network/subnets/private-a-id`,
});
const privateSubnetBIdParam = aws.ssm.getParameter({
    name: `/${projectName}/${environment}/network/subnets/private-b-id`,
});
const privateRouteTableAIdParam = aws.ssm.getParameter({
    name: `/${projectName}/${environment}/network/route-tables/private-a-id`,
});
const privateRouteTableBIdParam = aws.ssm.getParameter({
    name: `/${projectName}/${environment}/network/route-tables/private-b-id`,
});
const isolatedRouteTableAIdParam = aws.ssm.getParameter({
    name: `/${projectName}/${environment}/network/route-tables/isolated-a-id`,
});
const isolatedRouteTableBIdParam = aws.ssm.getParameter({
    name: `/${projectName}/${environment}/network/route-tables/isolated-b-id`,
});

// SSMパラメータストアからセキュリティ情報を取得
const vpceSecurityGroupIdParam = aws.ssm.getParameter({
    name: `/${projectName}/${environment}/security/sg/vpce-id`,
});

// SSMパラメータストアからVPCエンドポイント設定を取得
const vpcEndpointsParam = aws.ssm.getParameter({
    name: `/${projectName}/${environment}/network/vpc-endpoints`,
});

// 値の取得
const vpcId = vpcIdParam.then(p => p.value);
const privateSubnetIds = Promise.all([
    privateSubnetAIdParam.then(p => p.value),
    privateSubnetBIdParam.then(p => p.value),
]);
const privateRouteTableIds = Promise.all([
    privateRouteTableAIdParam.then(p => p.value),
    privateRouteTableBIdParam.then(p => p.value),
]);
const isolatedRouteTableAId = isolatedRouteTableAIdParam.then(p => p.value || "");
const isolatedRouteTableBId = isolatedRouteTableBIdParam.then(p => p.value || "");
const vpceSecurityGroupId = vpceSecurityGroupIdParam.then(p => p.value);
const vpcEndpoints = vpcEndpointsParam.then(p => JSON.parse(p.value || "[]"));

// VPCエンドポイント設定
const enableS3Endpoint = config.getBoolean("enableS3Endpoint") !== false; // デフォルトtrue
const enableDynamoDBEndpoint = config.getBoolean("enableDynamoDBEndpoint") || false;
const enableSecretsManagerEndpoint = config.getBoolean("enableSecretsManagerEndpoint") || false;
const enableKMSEndpoint = config.getBoolean("enableKMSEndpoint") || false;

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
        ]).apply(([privateRtIds, isoRtA, isoRtB]) => {
            const rtIds = [...privateRtIds];
            if (isoRtA && isoRtA !== "") rtIds.push(isoRtA);
            if (isoRtB && isoRtB !== "") rtIds.push(isoRtB);
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
        ]).apply(([privateRtIds, isoRtA, isoRtB]) => {
            const rtIds = [...privateRtIds];
            if (isoRtA && isoRtA !== "") rtIds.push(isoRtA);
            if (isoRtB && isoRtB !== "") rtIds.push(isoRtB);
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

// ===== SSMパラメータストアに個別の出力を保存 =====
const paramPrefix = `/${projectName}/${environment}/vpce`;

// S3エンドポイントID
if (s3Endpoint) {
    const s3EndpointIdParam = new aws.ssm.Parameter(`${projectName}-vpce-s3-id`, {
        name: `${paramPrefix}/endpoints/s3-id`,
        type: "String",
        value: s3Endpoint.id,
        description: "S3 VPC Endpoint ID",
        tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-vpce" },
    });
} else {
    const s3EndpointIdParam = new aws.ssm.Parameter(`${projectName}-vpce-s3-id`, {
        name: `${paramPrefix}/endpoints/s3-id`,
        type: "String",
        value: "",
        description: "S3 VPC Endpoint ID (not created)",
        tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-vpce" },
    });
}

// DynamoDBエンドポイントID
if (dynamodbEndpoint) {
    const dynamodbEndpointIdParam = new aws.ssm.Parameter(`${projectName}-vpce-dynamodb-id`, {
        name: `${paramPrefix}/endpoints/dynamodb-id`,
        type: "String",
        value: dynamodbEndpoint.id,
        description: "DynamoDB VPC Endpoint ID",
        tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-vpce" },
    });
} else {
    const dynamodbEndpointIdParam = new aws.ssm.Parameter(`${projectName}-vpce-dynamodb-id`, {
        name: `${paramPrefix}/endpoints/dynamodb-id`,
        type: "String",
        value: "",
        description: "DynamoDB VPC Endpoint ID (not created)",
        tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-vpce" },
    });
}

// Secrets ManagerエンドポイントID
if (secretsManagerEndpoint) {
    const smEndpointIdParam = new aws.ssm.Parameter(`${projectName}-vpce-sm-id`, {
        name: `${paramPrefix}/endpoints/secretsmanager-id`,
        type: "String",
        value: secretsManagerEndpoint.id,
        description: "Secrets Manager VPC Endpoint ID",
        tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-vpce" },
    });
} else {
    const smEndpointIdParam = new aws.ssm.Parameter(`${projectName}-vpce-sm-id`, {
        name: `${paramPrefix}/endpoints/secretsmanager-id`,
        type: "String",
        value: "",
        description: "Secrets Manager VPC Endpoint ID (not created)",
        tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-vpce" },
    });
}

// KMSエンドポイントID
if (kmsEndpoint) {
    const kmsEndpointIdParam = new aws.ssm.Parameter(`${projectName}-vpce-kms-id`, {
        name: `${paramPrefix}/endpoints/kms-id`,
        type: "String",
        value: kmsEndpoint.id,
        description: "KMS VPC Endpoint ID",
        tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-vpce" },
    });
} else {
    const kmsEndpointIdParam = new aws.ssm.Parameter(`${projectName}-vpce-kms-id`, {
        name: `${paramPrefix}/endpoints/kms-id`,
        type: "String",
        value: "",
        description: "KMS VPC Endpoint ID (not created)",
        tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-vpce" },
    });
}

// デプロイメント完了フラグ
const deploymentCompleteParam = new aws.ssm.Parameter(`${projectName}-vpce-deployed`, {
    name: `${paramPrefix}/deployment/complete`,
    type: "String",
    value: "true",
    description: "VPC Endpoints stack deployment completion flag",
    tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-vpce" },
});

// 設定情報をSSMパラメータに保存
const vpceConfig = new aws.ssm.Parameter(`${projectName}-vpce-config`, {
    name: `${paramPrefix}/config`,
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

// ========================================
// エクスポート（最小限に限定）
// ========================================
// すべての値はSSMパラメータストアに保存されているため、
// stack outputは必要最小限のみエクスポート

// デプロイメント確認用の基本情報のみ
export const deploymentInfo = {
    stack: "lambda-vpce",
    environment: environment,
    timestamp: new Date().toISOString(),
    ssmParameterPrefix: paramPrefix,
    endpointsCreated: [
        enableS3Endpoint,
        enableDynamoDBEndpoint,
        enableSecretsManagerEndpoint,
        enableKMSEndpoint,
    ].filter(Boolean).length,
};

// デプロイ完了の確認用
export const deploymentComplete = true;
