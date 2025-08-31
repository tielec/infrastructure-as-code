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
// S3エンドポイント
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

// DynamoDBエンドポイント
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

// Interface型エンドポイントは作成しないため、SSMパラメータも作成しない
// Secrets ManagerとKMSへのアクセスはNAT経由で行う



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
    ssmParameterPrefix: paramPrefix,
};
