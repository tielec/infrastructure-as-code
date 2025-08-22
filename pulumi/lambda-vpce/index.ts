/**
 * pulumi/lambda-vpce/index.ts
 * 
 * Lambda APIインフラのVPCエンドポイントを構築するPulumiスクリプト
 * Gateway型とInterface型のVPCエンドポイントを作成
 * SSMパラメータストアから設定を取得
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// 環境変数を取得
const environment = pulumi.getStack();

// SSMパラメータストアから設定を取得（Single Source of Truth）
const projectNameParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/common/project-name`,
});
const projectName = pulumi.output(projectNameParam).apply(p => p.value);

// SSMパラメータストアからネットワーク情報を取得
const vpcIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/vpc-id`,
});
const privateSubnetAIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/subnets/private-a-id`,
});
const privateSubnetBIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/subnets/private-b-id`,
});
const privateRouteTableAIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/route-tables/private-a-id`,
});
const privateRouteTableBIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/route-tables/private-b-id`,
});
const isolatedRouteTableAIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/route-tables/isolated-a-id`,
});
const isolatedRouteTableBIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/route-tables/isolated-b-id`,
});

// SSMパラメータストアからセキュリティ情報を取得
const vpceSecurityGroupIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/security/vpce-sg-id`,
});

// SSMパラメータストアからVPCエンドポイント設定を取得
const vpcEndpointsParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/vpc-endpoints`,
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

// VPCエンドポイント設定をSSMから取得
const enableS3EndpointParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/vpce/enable-s3`,
});
const enableDynamoDBEndpointParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/vpce/enable-dynamodb`,
});
const enableSecretsManagerEndpointParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/vpce/enable-secrets-manager`,
});
const enableKMSEndpointParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/vpce/enable-kms`,
});

const enableS3Endpoint = pulumi.output(enableS3EndpointParam).apply(p => p.value !== "false"); // デフォルトtrue
const enableDynamoDBEndpoint = pulumi.output(enableDynamoDBEndpointParam).apply(p => p.value === "true");
const enableSecretsManagerEndpoint = pulumi.output(enableSecretsManagerEndpointParam).apply(p => p.value === "true");
const enableKMSEndpoint = pulumi.output(enableKMSEndpointParam).apply(p => p.value === "true");

// ===== Gateway型 VPC Endpoints =====

// S3エンドポイント（Phase 1で必須）
const s3Endpoint = new aws.ec2.VpcEndpoint("lambda-api-vpce-s3", {
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
            Name: pulumi.interpolate`${projectName}-vpce-s3-${environment}`,
            Environment: environment,
            Type: "gateway",
        },
    });

// DynamoDBエンドポイント（Phase 2）
const dynamodbEndpoint = new aws.ec2.VpcEndpoint("lambda-api-vpce-dynamodb", {
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
            Name: pulumi.interpolate`${projectName}-vpce-dynamodb-${environment}`,
            Environment: environment,
            Type: "gateway",
        },
    });

// ===== Interface型 VPC Endpoints =====

// Secrets Managerエンドポイント（本番環境推奨）
const secretsManagerEndpoint = new aws.ec2.VpcEndpoint("lambda-api-vpce-secretsmanager", {
        vpcId: vpcId,
        serviceName: pulumi.interpolate`com.amazonaws.${aws.config.region}.secretsmanager`,
        vpcEndpointType: "Interface",
        subnetIds: privateSubnetIds,
        securityGroupIds: [vpceSecurityGroupId],
        privateDnsEnabled: true,
        tags: {
            Name: pulumi.interpolate`${projectName}-vpce-secretsmanager-${environment}`,
            Environment: environment,
            Type: "interface",
        },
    });

// KMSエンドポイント（本番環境推奨）
const kmsEndpoint = new aws.ec2.VpcEndpoint("lambda-api-vpce-kms", {
        vpcId: vpcId,
        serviceName: pulumi.interpolate`com.amazonaws.${aws.config.region}.kms`,
        vpcEndpointType: "Interface",
        subnetIds: privateSubnetIds,
        securityGroupIds: [vpceSecurityGroupId],
        privateDnsEnabled: true,
        tags: {
            Name: pulumi.interpolate`${projectName}-vpce-kms-${environment}`,
            Environment: environment,
            Type: "interface",
        },
    });

// ===== 将来の拡張用エンドポイント（Phase 2以降）=====
// 必要に応じて以下のエンドポイントを追加可能：
// - SQS（DLQ用）
// - SNS（通知用）
// - SSM（パラメータストア用）
// - Lambda（VPC内からのLambda呼び出し用）
// - CloudWatch Logs（ログ送信用）

// ===== コスト情報の計算 =====
// Interface型エンドポイントのコスト（$0.01/時間 × AZ数）
const interfaceEndpointCostPerHour = 0.01;
const azCount = 2; // マルチAZ
const hoursPerMonth = 730; // 約30日
const interfaceCostPerMonth = interfaceEndpointCostPerHour * azCount * hoursPerMonth;

// ===== SSMパラメータストアに個別の出力を保存 =====
const paramPrefix = pulumi.interpolate`/${projectName}/${environment}/vpce`;

// S3エンドポイントID
const s3EndpointIdParam = new aws.ssm.Parameter("lambda-api-vpce-s3-id", {
        name: pulumi.interpolate`${paramPrefix}/endpoints/s3-id`,
        type: "String",
        value: s3Endpoint.id,
        description: "S3 VPC Endpoint ID",
        tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-vpce" },
    });

// DynamoDBエンドポイントID
const dynamodbEndpointIdParam = new aws.ssm.Parameter("lambda-api-vpce-dynamodb-id", {
        name: pulumi.interpolate`${paramPrefix}/endpoints/dynamodb-id`,
        type: "String",
        value: dynamodbEndpoint.id,
        description: "DynamoDB VPC Endpoint ID",
        tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-vpce" },
    });

// Secrets ManagerエンドポイントID
const smEndpointIdParam = new aws.ssm.Parameter("lambda-api-vpce-sm-id", {
        name: pulumi.interpolate`${paramPrefix}/endpoints/secretsmanager-id`,
        type: "String",
        value: secretsManagerEndpoint.id,
        description: "Secrets Manager VPC Endpoint ID",
        tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-vpce" },
    });

// KMSエンドポイントID
const kmsEndpointIdParam = new aws.ssm.Parameter("lambda-api-vpce-kms-id", {
        name: pulumi.interpolate`${paramPrefix}/endpoints/kms-id`,
        type: "String",
        value: kmsEndpoint.id,
        description: "KMS VPC Endpoint ID",
        tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-vpce" },
    });

// デプロイメント完了フラグ
const deploymentCompleteParam = new aws.ssm.Parameter("lambda-api-vpce-deployed", {
    name: pulumi.interpolate`${paramPrefix}/deployment/complete`,
    type: "String",
    value: "true",
    description: "VPC Endpoints stack deployment completion flag",
    tags: { Environment: environment, ManagedBy: "pulumi", Stack: "lambda-vpce" },
});

// 設定情報をSSMパラメータに保存
const vpceConfig = new aws.ssm.Parameter("lambda-api-vpce-config", {
    name: pulumi.interpolate`${paramPrefix}/config`,
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
            monthlyEstimate: "See breakdown below",
            breakdown: {
                gateway: "$0 (Free)",
                interface: {
                    perEndpoint: "$14.60/month",
                    note: "Cost applies if Interface endpoints are enabled",
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
const usageGuide = new aws.ssm.Parameter("lambda-api-vpce-usage-guide", {
    name: pulumi.interpolate`/${projectName}/${environment}/vpce/usage-guide`,
    type: "String",
    value: JSON.stringify({
        s3: {
            usage: "Automatic - S3 API calls from Lambda will use VPC endpoint",
            example: "aws s3 cp file.txt s3://bucket/key",
        },
        dynamodb: {
            usage: "Automatic - DynamoDB API calls will use VPC endpoint",
            example: "dynamodb.getItem({ TableName: 'table', Key: {...} })",
        },
        secretsManager: {
            usage: "Automatic with private DNS - Uses VPC endpoint",
            example: "secretsmanager.getSecretValue({ SecretId: 'secret-name' })",
        },
        kms: {
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
