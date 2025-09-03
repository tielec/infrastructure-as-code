/**
 * pulumi/lambda-ssm-init/index.ts
 * 
 * Lambda APIインフラのSSMパラメータ初期化スタック
 * 全スタックで使用する共通パラメータを事前に設定
 * Jenkinsと同様の設計思想で、SSMパラメータストアをSingle Source of Truthとして使用
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import { SSMParameterHelper } from "@tielec/pulumi-components";

// ========================================
// 環境変数取得
// ========================================
const config = new pulumi.Config();
const environment = pulumi.getStack();
const githubToken = config.require("githubToken");
const lambdaRepoUrl = config.require("lambdaRepoUrl");
const lambdaRepoBranch = config.require("lambdaRepoBranch");
const lambdaVersionRetention = config.requireNumber("lambdaVersionRetention");

// ========================================
// 初期設定
// ========================================
// 注: これは初期化スタックのため、他のSSMパラメータはまだ存在しない
// プロジェクト名は固定値として定義
const projectName = "lambda-api";

// Pulumi設定から環境設定を取得
const lambdaMemory = config.requireNumber("lambdaMemory");
const lambdaTimeout = config.requireNumber("lambdaTimeout");
const logLevel = config.require("logLevel");
const logRetentionDays = config.requireNumber("logRetentionDays");
const vpcCidr = config.require("vpcCidr");
const enableFlowLogs = config.requireBoolean("enableFlowLogs");
const vpcEndpoints = JSON.parse(config.require("vpcEndpoints"));
const natHighAvailability = config.requireBoolean("natHighAvailability");
const natInstanceType = config.require("natInstanceType");
const apiRateLimit = config.requireNumber("apiRateLimit");
const apiBurstLimit = config.requireNumber("apiBurstLimit");
const enableWaf = config.requireBoolean("enableWaf");
const enableWebSocket = config.requireBoolean("enableWebSocket");
const enableDatabase = config.requireBoolean("enableDatabase");

// ========================================
// 共通タグ定義
// ========================================
const commonTags = {
    Environment: environment,
    ManagedBy: "pulumi",
    Project: projectName,
    Stack: pulumi.getProject(),
};

// ========================================
// パラメータ定義
// ========================================
const paramPrefix = `/${projectName}/${environment}`;

// ========================================
// SSMパラメータヘルパー初期化
// ========================================
const ssmHelper = new SSMParameterHelper(paramPrefix, commonTags);

// ========================================
// 管理パラメータ（Pulumiで常に管理）
// ========================================
// プロジェクト基本情報
ssmHelper.createParameter('/common/project-name', {
    paramType: 'managed',
    value: projectName,
    description: "Project name",
});

ssmHelper.createParameter('/common/environment', {
    paramType: 'managed',
    value: environment,
    description: "Environment",
});

ssmHelper.createParameter('/common/region', {
    paramType: 'managed',
    value: aws.config.region || "ap-northeast-1",
    description: "AWS region",
});

// ネットワーク設定
ssmHelper.createParameter('/network/vpc-cidr', {
    paramType: 'managed',
    value: vpcCidr,
    description: "VPC CIDR block",
});

ssmHelper.createParameter('/network/enable-flow-logs', {
    paramType: 'managed',
    value: String(enableFlowLogs),
    description: "Enable VPC flow logs",
});

ssmHelper.createParameter('/network/vpc-endpoints', {
    paramType: 'managed',
    value: JSON.stringify(vpcEndpoints),
    description: "VPC endpoints configuration",
});

// Lambda設定
ssmHelper.createParameter('/lambda/memory', {
    paramType: 'managed',
    value: String(lambdaMemory),
    description: "Lambda memory size",
});

ssmHelper.createParameter('/lambda/timeout', {
    paramType: 'managed',
    value: String(lambdaTimeout),
    description: "Lambda timeout",
});

ssmHelper.createParameter('/lambda/log-level', {
    paramType: 'managed',
    value: logLevel,
    description: "Lambda log level",
});

ssmHelper.createParameter('/lambda/log-retention-days', {
    paramType: 'managed',
    value: String(logRetentionDays),
    description: "CloudWatch logs retention days",
});

ssmHelper.createParameter('/lambda/memory-size', {
    paramType: 'managed',
    value: String(lambdaMemory),
    description: "Lambda memory size (duplicate for compatibility)",
});

// API Gateway設定
ssmHelper.createParameter('/api/rate-limit', {
    paramType: 'managed',
    value: String(apiRateLimit),
    description: "API rate limit",
});

ssmHelper.createParameter('/api/burst-limit', {
    paramType: 'managed',
    value: String(apiBurstLimit),
    description: "API burst limit",
});

ssmHelper.createParameter('/api/enable-waf', {
    paramType: 'managed',
    value: String(enableWaf),
    description: "Enable WAF",
});

ssmHelper.createParameter('/api/enable-websocket', {
    paramType: 'managed',
    value: String(enableWebSocket),
    description: "Enable WebSocket",
});

// NAT設定
ssmHelper.createParameter('/nat/high-availability', {
    paramType: 'managed',
    value: String(natHighAvailability),
    description: "NAT high availability",
});

ssmHelper.createParameter('/nat/instance-type', {
    paramType: 'managed',
    value: natInstanceType,
    description: "NAT instance type",
});

// データベース設定
ssmHelper.createParameter('/database/enabled', {
    paramType: 'managed',
    value: String(enableDatabase),
    description: "Database enabled",
});

// フェーズ設定
ssmHelper.createParameter('/phase/isolated-subnets-enabled', {
    paramType: 'managed',
    value: String(enableDatabase),
    description: "Isolated subnets enabled",
});

ssmHelper.createParameter('/phase/database-sg-enabled', {
    paramType: 'managed',
    value: String(enableDatabase),
    description: "Database security group enabled",
});

// VPCエンドポイント設定
ssmHelper.createParameter('/vpce/enable-s3', {
    paramType: 'managed',
    value: String(vpcEndpoints.includes("s3")),
    description: "Enable S3 VPC endpoint",
});

ssmHelper.createParameter('/vpce/enable-dynamodb', {
    paramType: 'managed',
    value: String(vpcEndpoints.includes("dynamodb")),
    description: "Enable DynamoDB VPC endpoint",
});

// デプロイメント情報
ssmHelper.createParameter('/deployment/stack-name', {
    paramType: 'managed',
    value: `lambda-ssm-init-${environment}`,
    description: "Stack name",
});

ssmHelper.createParameter('/deployment/last-updated', {
    paramType: 'managed',
    value: new Date().toISOString(),
    description: "Last updated timestamp",
});

// ========================================
// セキュアパラメータ（初期設定のみ）
// ========================================
// セキュリティ関連の暗号化パラメータ（SecureString）
// 注: 実際の値は環境変数またはCI/CDパイプラインから設定すること
ssmHelper.createParameter('/security/api-key', {
    paramType: 'init-only',  // 一度設定したら変更しない
    value: pulumi.secret("CHANGE-ME-IN-PRODUCTION"),
    type: "SecureString",
    description: "API key for Lambda API",
});

ssmHelper.createParameter('/security/jwt-secret', {
    paramType: 'init-only',  // 一度設定したら変更しない
    value: pulumi.secret("CHANGE-ME-IN-PRODUCTION"),
    type: "SecureString",
    description: "JWT secret for Lambda API",
});

// GitHub Personal Access Token 用のSSM Parameter（Pulumiコンフィグから取得）
const githubTokenParam = ssmHelper.createParameter('/security/github-token', {
    paramType: 'init-only',  // 一度設定したら変更しない
    value: githubToken,
    type: "SecureString",
    description: "GitHub Personal Access Token for repository access",
});

// Lambda関数ソースコードリポジトリURL用のSSM Parameter（Pulumiコンフィグから取得）
const lambdaRepoUrlParam = ssmHelper.createParameter('/lambda/source/repository-url', {
    paramType: 'init-only',  // 一度設定したら変更しない
    value: lambdaRepoUrl,
    type: "SecureString",
    description: "Lambda functions source code repository URL",
});

// Lambda関数ソースコードブランチ用のSSM Parameter
const lambdaRepoBranchParam = ssmHelper.createParameter('/lambda/source/repository-branch', {
    paramType: 'managed',
    value: lambdaRepoBranch,
    type: "String",
    description: "Lambda functions source code repository branch",
});

// Lambda関数バージョン保持数用のSSM Parameter
const lambdaVersionRetentionParam = ssmHelper.createParameter('/lambda/versioning/retain-versions', {
    paramType: 'managed',
    value: String(lambdaVersionRetention),
    type: "String",
    description: "Number of Lambda function versions to retain",
});

// 初期化完了フラグ
const initComplete = ssmHelper.createParameter('/common/init-complete', {
    paramType: 'managed',
    value: "true",
    type: "String",
    description: "SSM parameter initialization complete flag",
});

// ========================================
// エクスポート（表示用のみ）
// ========================================
// エクスポートは表示・確認用のみ
// 他のスタックはSSMパラメータから値を取得すること
export const outputs = {
    stack: "lambda-ssm-init",
    environment: environment,
    ssmParameterPrefix: paramPrefix,
    parametersCreated: ssmHelper.getParameterCount(),
    initCompleteFlag: initComplete.name,
    githubTokenParameterName: githubTokenParam.name,
    lambdaRepoUrlParameterName: lambdaRepoUrlParam.name,
    lambdaRepoBranchParameterName: lambdaRepoBranchParam.name,
    lambdaVersionRetentionParameterName: lambdaVersionRetentionParam.name,
};

// デプロイ完了の確認用
export const deploymentComplete = true;