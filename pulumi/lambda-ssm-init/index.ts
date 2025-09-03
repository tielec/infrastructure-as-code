/**
 * pulumi/lambda-ssm-init/index.ts
 * 
 * Lambda APIインフラのSSMパラメータ初期化スタック
 * 全スタックで使用する共通パラメータを事前に設定
 * Jenkinsと同様の設計思想で、SSMパラメータストアをSingle Source of Truthとして使用
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

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
// SSMパラメータヘルパー関数
// ========================================
// パラメータタイプの定義
type ParameterType = 'init-only' | 'managed';

// 拡張されたParameterArgs
interface ExtendedSSMParameterArgs extends Omit<aws.ssm.ParameterArgs, 'name' | 'value' | 'tags'> {
    paramType: ParameterType;
    value: pulumi.Input<string>;
    description?: string;
    type?: 'String' | 'SecureString' | 'StringList';
}

// ヘルパー関数
function createSSMParameter(
    name: string,
    args: ExtendedSSMParameterArgs
): aws.ssm.Parameter {
    const resourceName = name.replace(/\//g, "-").replace(/^-/, "");
    const fullName = `${paramPrefix}${name}`;
    
    // パラメータタイプに応じた設定
    let resourceOptions: pulumi.ResourceOptions = {};
    
    switch (args.paramType) {
        case 'init-only':
            // 初期設定のみ - 値の変更を完全に無視
            resourceOptions = {
                ignoreChanges: ["value"],
                protect: true,  // 削除保護
            };
            break;
            
        case 'managed':
            // Pulumiで管理 - 常に上書き
            resourceOptions = {};
            break;
    }
    
    // paramTypeを除いたargs
    const { paramType, ...ssmArgs } = args;
    
    const param = new aws.ssm.Parameter(resourceName, {
        name: fullName,
        tags: commonTags,
        ...ssmArgs,
    }, resourceOptions);
    
    parameters.push(param);
    return param;
}

// ========================================
// パラメータ定義
// ========================================
const paramPrefix = `/${projectName}/${environment}`;

// ========================================
// 管理パラメータ（Pulumiで常に管理）
// ========================================
// プロジェクト基本情報
createSSMParameter('/common/project-name', {
    paramType: 'managed',
    value: projectName,
    description: "Project name",
});

createSSMParameter('/common/environment', {
    paramType: 'managed',
    value: environment,
    description: "Environment",
});

createSSMParameter('/common/region', {
    paramType: 'managed',
    value: aws.config.region || "ap-northeast-1",
    description: "AWS region",
});

// ネットワーク設定
createSSMParameter('/network/vpc-cidr', {
    paramType: 'managed',
    value: vpcCidr,
    description: "VPC CIDR block",
});

createSSMParameter('/network/enable-flow-logs', {
    paramType: 'managed',
    value: String(enableFlowLogs),
    description: "Enable VPC flow logs",
});

createSSMParameter('/network/vpc-endpoints', {
    paramType: 'managed',
    value: JSON.stringify(vpcEndpoints),
    description: "VPC endpoints configuration",
});

// Lambda設定
createSSMParameter('/lambda/memory', {
    paramType: 'managed',
    value: String(lambdaMemory),
    description: "Lambda memory size",
});

createSSMParameter('/lambda/timeout', {
    paramType: 'managed',
    value: String(lambdaTimeout),
    description: "Lambda timeout",
});

createSSMParameter('/lambda/log-level', {
    paramType: 'managed',
    value: logLevel,
    description: "Lambda log level",
});

createSSMParameter('/lambda/log-retention-days', {
    paramType: 'managed',
    value: String(logRetentionDays),
    description: "CloudWatch logs retention days",
});

createSSMParameter('/lambda/memory-size', {
    paramType: 'managed',
    value: String(lambdaMemory),
    description: "Lambda memory size (duplicate for compatibility)",
});

// API Gateway設定
createSSMParameter('/api/rate-limit', {
    paramType: 'managed',
    value: String(apiRateLimit),
    description: "API rate limit",
});

createSSMParameter('/api/burst-limit', {
    paramType: 'managed',
    value: String(apiBurstLimit),
    description: "API burst limit",
});

createSSMParameter('/api/enable-waf', {
    paramType: 'managed',
    value: String(enableWaf),
    description: "Enable WAF",
});

createSSMParameter('/api/enable-websocket', {
    paramType: 'managed',
    value: String(enableWebSocket),
    description: "Enable WebSocket",
});

// NAT設定
createSSMParameter('/nat/high-availability', {
    paramType: 'managed',
    value: String(natHighAvailability),
    description: "NAT high availability",
});

createSSMParameter('/nat/instance-type', {
    paramType: 'managed',
    value: natInstanceType,
    description: "NAT instance type",
});

// データベース設定
createSSMParameter('/database/enabled', {
    paramType: 'managed',
    value: String(enableDatabase),
    description: "Database enabled",
});

// フェーズ設定
createSSMParameter('/phase/isolated-subnets-enabled', {
    paramType: 'managed',
    value: String(enableDatabase),
    description: "Isolated subnets enabled",
});

createSSMParameter('/phase/database-sg-enabled', {
    paramType: 'managed',
    value: String(enableDatabase),
    description: "Database security group enabled",
});

// VPCエンドポイント設定
createSSMParameter('/vpce/enable-s3', {
    paramType: 'managed',
    value: String(vpcEndpoints.includes("s3")),
    description: "Enable S3 VPC endpoint",
});

createSSMParameter('/vpce/enable-dynamodb', {
    paramType: 'managed',
    value: String(vpcEndpoints.includes("dynamodb")),
    description: "Enable DynamoDB VPC endpoint",
});

// デプロイメント情報
createSSMParameter('/deployment/stack-name', {
    paramType: 'managed',
    value: `lambda-ssm-init-${environment}`,
    description: "Stack name",
});

createSSMParameter('/deployment/last-updated', {
    paramType: 'managed',
    value: new Date().toISOString(),
    description: "Last updated timestamp",
});

// ========================================
// SSMパラメータ作成
// ========================================
const parameters: aws.ssm.Parameter[] = [];

// ========================================
// セキュアパラメータ（初期設定のみ）
// ========================================
// セキュリティ関連の暗号化パラメータ（SecureString）
// 注: 実際の値は環境変数またはCI/CDパイプラインから設定すること
createSSMParameter('/security/api-key', {
    paramType: 'init-only',  // 一度設定したら変更しない
    value: pulumi.secret("CHANGE-ME-IN-PRODUCTION"),
    type: "SecureString",
    description: "API key for Lambda API",
});

createSSMParameter('/security/jwt-secret', {
    paramType: 'init-only',  // 一度設定したら変更しない
    value: pulumi.secret("CHANGE-ME-IN-PRODUCTION"),
    type: "SecureString",
    description: "JWT secret for Lambda API",
});

// GitHub Personal Access Token 用のSSM Parameter（Pulumiコンフィグから取得）
const githubTokenParam = createSSMParameter('/security/github-token', {
    paramType: 'init-only',  // 一度設定したら変更しない
    value: githubToken,
    type: "SecureString",
    description: "GitHub Personal Access Token for repository access",
});

// Lambda関数ソースコードリポジトリURL用のSSM Parameter（Pulumiコンフィグから取得）
const lambdaRepoUrlParam = createSSMParameter('/lambda/source/repository-url', {
    paramType: 'init-only',  // 一度設定したら変更しない
    value: lambdaRepoUrl,
    type: "SecureString",
    description: "Lambda functions source code repository URL",
});

// Lambda関数ソースコードブランチ用のSSM Parameter
const lambdaRepoBranchParam = createSSMParameter('/lambda/source/repository-branch', {
    paramType: 'managed',
    value: lambdaRepoBranch,
    type: "String",
    description: "Lambda functions source code repository branch",
});

// Lambda関数バージョン保持数用のSSM Parameter
const lambdaVersionRetentionParam = createSSMParameter('/lambda/versioning/retain-versions', {
    paramType: 'managed',
    value: String(lambdaVersionRetention),
    type: "String",
    description: "Number of Lambda function versions to retain",
});

// ========================================
// スタック依存関係定義
// ========================================
const stackDependencies = createSSMParameter('/common/stack-dependencies', {
    paramType: 'managed',
    value: JSON.stringify({
        stacks: [
            { name: "lambda-ssm-init", order: 1, required: true },
            { name: "lambda-shipment-s3", order: 2, required: true },
            { name: "lambda-network", order: 3, required: true },
            { name: "lambda-security", order: 4, required: true },
            { name: "lambda-vpce", order: 5, required: true },
            { name: "lambda-nat", order: 6, required: true },
            { name: "lambda-functions", order: 7, required: true },
            { name: "lambda-api-gateway", order: 8, required: true },
            { name: "lambda-waf", order: 9, required: enableWaf },
            { name: "lambda-websocket", order: 10, required: enableWebSocket },
            { name: "lambda-database", order: 11, required: enableDatabase },
        ],
        deployment: {
            environment: environment,
            timestamp: new Date().toISOString(),
        },
    }),
    type: "String",
    description: "Stack deployment dependencies and order",
});

// 初期化完了フラグ
const initComplete = createSSMParameter('/common/init-complete', {
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
    parametersCreated: parameters.length,
    initCompleteFlag: initComplete.name,
    githubTokenParameterName: githubTokenParam.name,
    lambdaRepoUrlParameterName: lambdaRepoUrlParam.name,
    lambdaRepoBranchParameterName: lambdaRepoBranchParam.name,
    lambdaVersionRetentionParameterName: lambdaVersionRetentionParam.name,
};

// デプロイ完了の確認用
export const deploymentComplete = true;