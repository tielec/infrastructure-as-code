/**
 * pulumi/lambda-shipment-s3/index.ts
 * 
 * Lambda関数デプロイメント用S3バケットを構築するPulumiスクリプト
 * Lambdaパッケージの保存・バージョニング管理用バケットを作成
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import { LambdaDeploymentBucket } from "@tielec/pulumi-components";

// ========================================
// 環境変数取得
// ========================================
const environment = pulumi.getStack();
const region = aws.config.region || "us-west-2";

// ========================================
// SSMパラメータ参照（Single Source of Truth）
// ========================================
// プロジェクト名を取得
const projectNameParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/common/project-name`,
});

// ========================================
// S3バケット作成
// ========================================
const bucketName = `tielec-lambda-shipment-${environment}`;

// プロジェクト名を解決してからバケットを作成
const deploymentBucket = pulumi.output(projectNameParam).apply(param => {
    const commonTags = {
        Environment: environment,
        ManagedBy: "pulumi",
        Project: param.value,
        Stack: pulumi.getProject(),
        SharedResource: "true",
    };

    return new LambdaDeploymentBucket("lambda-shipment", {
        useExisting: false,  // 新規作成を明示的に指定
        bucketName: bucketName,
        versioning: true,
        lifecycleDays: 7,
        tags: commonTags,
    });
});

// ========================================
// SSMパラメータへの保存
// ========================================
// 他のスタックが参照する値をSSMに保存
const paramPrefix = `/lambda-shipment/${environment}`;

// SSMパラメータ用のタグを作成（プロジェクト名を解決後）
const ssmTags = pulumi.output(projectNameParam).apply(param => ({
    Environment: environment,
    ManagedBy: "pulumi",
    Project: param.value,
    Stack: pulumi.getProject(),
    SharedResource: "true",
}));

// バケット名
const bucketNameParam = new aws.ssm.Parameter("bucket-name", {
    name: `${paramPrefix}/bucket/name`,
    type: "String",
    value: deploymentBucket.apply(bucket => bucket.bucketName),
    description: "Lambda Shipment S3 Bucket Name",
    tags: ssmTags,
});

// バケットARN
const bucketArnParam = new aws.ssm.Parameter("bucket-arn", {
    name: `${paramPrefix}/bucket/arn`,
    type: "String",
    value: deploymentBucket.apply(bucket => bucket.bucketArn),
    description: "Lambda Shipment S3 Bucket ARN",
    tags: ssmTags,
});

// リージョン
const regionParam = new aws.ssm.Parameter("region", {
    name: `${paramPrefix}/region`,
    type: "String",
    value: region,
    description: "Lambda Shipment Deployment Region",
    tags: ssmTags,
});

// ========================================
// エクスポート（表示用のみ）
// ========================================
// エクスポートは表示・確認用のみ
// 他のスタックはSSMパラメータから値を取得すること
export const outputs = {
    stack: "lambda-shipment-s3",
    environment: environment,
    bucketName: deploymentBucket.apply(bucket => bucket.bucketName),
    bucketArn: deploymentBucket.apply(bucket => bucket.bucketArn),
    region: region,
    ssmParameterPrefix: paramPrefix,
};