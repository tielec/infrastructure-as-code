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
const region = aws.config.region || "ap-northeast-1";

// ========================================
// SSMパラメータ参照（Single Source of Truth）
// ========================================
// プロジェクト名を取得
const projectNameParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/common/project-name`,
});
const projectName = pulumi.output(projectNameParam).apply(p => p.value);

// ========================================
// 共通設定
// ========================================
// 共通タグ定義
const commonTags = {
    Environment: environment,
    ManagedBy: "pulumi",
    Project: projectName,
    Stack: pulumi.getProject(),
    SharedResource: "true",
};

// ========================================
// S3バケット作成
// ========================================
const bucketName = `tielec-lambda-shipment-${environment}`;

const deploymentBucket = new LambdaDeploymentBucket("lambda-shipment", {
  useExisting: false,  // 新規作成を明示的に指定
  bucketName: bucketName,
  versioning: true,
  lifecycleDays: 7,
  tags: commonTags,
});

// ========================================
// SSMパラメータへの保存
// ========================================
// 他のスタックが参照する値をSSMに保存
const paramPrefix = pulumi.interpolate`/lambda-shipment/${environment}`;

// バケット名
const bucketNameParam = new aws.ssm.Parameter("bucket-name", {
    name: pulumi.interpolate`${paramPrefix}/bucket/name`,
    type: "String",
    value: deploymentBucket.bucketName,
    description: "Lambda Shipment S3 Bucket Name",
    tags: commonTags,
});

// バケットARN
const bucketArnParam = new aws.ssm.Parameter("bucket-arn", {
    name: pulumi.interpolate`${paramPrefix}/bucket/arn`,
    type: "String",
    value: deploymentBucket.bucketArn,
    description: "Lambda Shipment S3 Bucket ARN",
    tags: commonTags,
});

// リージョン
const regionParam = new aws.ssm.Parameter("region", {
    name: pulumi.interpolate`${paramPrefix}/region`,
    type: "String",
    value: region,
    description: "Lambda Shipment Deployment Region",
    tags: commonTags,
});

// ========================================
// エクスポート（表示用のみ）
// ========================================
// エクスポートは表示・確認用のみ
// 他のスタックはSSMパラメータから値を取得すること
export const outputs = {
    stack: "lambda-shipment-s3",
    environment: environment,
    bucketName: deploymentBucket.bucketName,
    bucketArn: deploymentBucket.bucketArn,
    region: region,
    ssmParameterPrefix: paramPrefix,
};