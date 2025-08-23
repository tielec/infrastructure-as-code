/**
 * pulumi/lambda-vpce/index.ts
 * 
 * Lambda APIインフラのVPCエンドポイントを構築するPulumiスクリプト
 * Gateway型とInterface型のVPCエンドポイントを作成
 * SSMパラメータストアから設定を取得
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

// ネットワーク情報を取得
const vpcIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/vpc-id`,
});
const vpcId = pulumi.output(vpcIdParam).apply(p => p.value);

const privateSubnetAIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/subnets/private-a-id`,
});
const privateSubnetBIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/subnets/private-b-id`,
});
const privateSubnetIds = pulumi.all([
    pulumi.output(privateSubnetAIdParam).apply(p => p.value),
    pulumi.output(privateSubnetBIdParam).apply(p => p.value),
]);

const privateRouteTableAIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/route-tables/private-a-id`,
});
const privateRouteTableBIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/route-tables/private-b-id`,
});
const privateRouteTableIds = pulumi.all([
    pulumi.output(privateRouteTableAIdParam).apply(p => p.value),
    pulumi.output(privateRouteTableBIdParam).apply(p => p.value),
]);

const isolatedRouteTableAIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/route-tables/isolated-a-id`,
});
const isolatedRouteTableAId = pulumi.output(isolatedRouteTableAIdParam).apply(p => p.value || "");

const isolatedRouteTableBIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/route-tables/isolated-b-id`,
});
const isolatedRouteTableBId = pulumi.output(isolatedRouteTableBIdParam).apply(p => p.value || "");

// セキュリティ情報を取得
const vpceSecurityGroupIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/security/vpce-sg-id`,
});
const vpceSecurityGroupId = pulumi.output(vpceSecurityGroupIdParam).apply(p => p.value);

// VPCエンドポイント設定を取得
const enableS3EndpointParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/vpce/enable-s3`,
});
const enableS3Endpoint = pulumi.output(enableS3EndpointParam).apply(p => p.value !== "false");

const enableDynamoDBEndpointParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/vpce/enable-dynamodb`,
});
const enableDynamoDBEndpoint = pulumi.output(enableDynamoDBEndpointParam).apply(p => p.value === "true");

const enableSecretsManagerEndpointParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/vpce/enable-secrets-manager`,
});
const enableSecretsManagerEndpoint = pulumi.output(enableSecretsManagerEndpointParam).apply(p => p.value === "true");

const enableKMSEndpointParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/vpce/enable-kms`,
});
const enableKMSEndpoint = pulumi.output(enableKMSEndpointParam).apply(p => p.value === "true");

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
// VPCエンドポイント定義
// ========================================
// Gateway型 VPC Endpoints
// S3エンドポイント（Phase 1で必須）
const s3Endpoint = new aws.ec2.VpcEndpoint("vpce-s3", {
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
            ...commonTags,
            Name: pulumi.interpolate`${projectName}-vpce-s3-${environment}`,
            Type: "gateway",
        },
    });

// DynamoDBエンドポイント（Phase 2）
const dynamodbEndpoint = new aws.ec2.VpcEndpoint("vpce-dynamodb", {
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
            ...commonTags,
            Name: pulumi.interpolate`${projectName}-vpce-dynamodb-${environment}`,
            Type: "gateway",
        },
    });

// Interface型 VPC Endpoints
// Secrets Managerエンドポイント（本番環境推奨）
const secretsManagerEndpoint = new aws.ec2.VpcEndpoint("vpce-secretsmanager", {
        vpcId: vpcId,
        serviceName: pulumi.interpolate`com.amazonaws.${aws.config.region}.secretsmanager`,
        vpcEndpointType: "Interface",
        subnetIds: privateSubnetIds,
        securityGroupIds: [vpceSecurityGroupId],
        privateDnsEnabled: true,
        tags: {
            ...commonTags,
            Name: pulumi.interpolate`${projectName}-vpce-secretsmanager-${environment}`,
            Type: "interface",
        },
    });

// KMSエンドポイント（本番環境推奨）
const kmsEndpoint = new aws.ec2.VpcEndpoint("vpce-kms", {
        vpcId: vpcId,
        serviceName: pulumi.interpolate`com.amazonaws.${aws.config.region}.kms`,
        vpcEndpointType: "Interface",
        subnetIds: privateSubnetIds,
        securityGroupIds: [vpceSecurityGroupId],
        privateDnsEnabled: true,
        tags: {
            ...commonTags,
            Name: pulumi.interpolate`${projectName}-vpce-kms-${environment}`,
            Type: "interface",
        },
    });

// ========================================
// 将来の拡張用エンドポイント（Phase 2以降）
// ========================================
// 必要に応じて以下のエンドポイントを追加可能：
// - SQS（DLQ用）
// - SNS（通知用）
// - SSM（パラメータストア用）
// - Lambda（VPC内からのLambda呼び出し用）
// - CloudWatch Logs（ログ送信用）

// ========================================
// SSMパラメータへの保存
// ========================================
// 他のスタックが参照する値をSSMに保存
const paramPrefix = pulumi.interpolate`/${projectName}/${environment}/vpce`;

// S3エンドポイントID
const s3EndpointIdParam = new aws.ssm.Parameter("vpce-s3-id", {
    name: pulumi.interpolate`${paramPrefix}/endpoints/s3-id`,
    type: "String",
    value: s3Endpoint.id,
    description: "S3 VPC Endpoint ID",
    tags: commonTags,
});

// DynamoDBエンドポイントID
const dynamodbEndpointIdParam = new aws.ssm.Parameter("vpce-dynamodb-id", {
    name: pulumi.interpolate`${paramPrefix}/endpoints/dynamodb-id`,
    type: "String",
    value: dynamodbEndpoint.id,
    description: "DynamoDB VPC Endpoint ID",
    tags: commonTags,
});

// Secrets ManagerエンドポイントID
const smEndpointIdParam = new aws.ssm.Parameter("vpce-sm-id", {
    name: pulumi.interpolate`${paramPrefix}/endpoints/secretsmanager-id`,
    type: "String",
    value: secretsManagerEndpoint.id,
    description: "Secrets Manager VPC Endpoint ID",
    tags: commonTags,
});

// KMSエンドポイントID
const kmsEndpointIdParam = new aws.ssm.Parameter("vpce-kms-id", {
    name: pulumi.interpolate`${paramPrefix}/endpoints/kms-id`,
    type: "String",
    value: kmsEndpoint.id,
    description: "KMS VPC Endpoint ID",
    tags: commonTags,
});

// デプロイメント完了フラグ
const deploymentCompleteParam = new aws.ssm.Parameter("vpce-deployed", {
    name: pulumi.interpolate`${paramPrefix}/deployment/complete`,
    type: "String",
    value: "true",
    description: "VPC Endpoints stack deployment completion flag",
    tags: commonTags,
});

// 設定情報をSSMパラメータに保存
const vpceConfig = new aws.ssm.Parameter("vpce-config", {
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
    tags: commonTags,
});

// エンドポイント使用ガイド
const usageGuide = new aws.ssm.Parameter("vpce-usage-guide", {
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
    tags: commonTags,
});

// ========================================
// エクスポート（表示用のみ）
// ========================================
// エクスポートは表示・確認用のみ
// 他のスタックはSSMパラメータから値を取得すること
export const outputs = {
    stack: "lambda-vpce",
    environment: environment,
    s3EndpointId: s3Endpoint.id,
    dynamodbEndpointId: dynamodbEndpoint.id,
    secretsManagerEndpointId: secretsManagerEndpoint.id,
    kmsEndpointId: kmsEndpoint.id,
    ssmParameterPrefix: paramPrefix,
    deploymentComplete: deploymentCompleteParam.name,
};
