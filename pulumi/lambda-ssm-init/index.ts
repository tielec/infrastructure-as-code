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

// 環境別設定
const environmentConfig = {
    dev: {
        vpcCidr: "10.1.0.0/16",
        lambdaMemory: 512,
        lambdaTimeout: 30,
        logLevel: "DEBUG",
        logRetentionDays: 3,
        apiRateLimit: 100,
        apiBurstLimit: 200,
        enableFlowLogs: false,
        enableWaf: false,
        enableWebSocket: false,
        enableDatabase: false,
        natHighAvailability: false,
        natInstanceType: "t4g.nano",
        vpcEndpoints: ["s3"],
    },
    prod: {
        vpcCidr: "10.3.0.0/16",
        lambdaMemory: 2048,
        lambdaTimeout: 60,
        logLevel: "INFO",
        logRetentionDays: 14,
        apiRateLimit: 1000,
        apiBurstLimit: 2000,
        enableFlowLogs: true,
        enableWaf: true,
        enableWebSocket: true,
        enableDatabase: true,
        natHighAvailability: true,
        natInstanceType: "t4g.medium",
        vpcEndpoints: ["s3", "dynamodb"],
    },
};

// 現在の環境の設定を取得
const envConfig = environmentConfig[environment as keyof typeof environmentConfig] || environmentConfig.dev;

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

// 共通設定パラメータ
const commonParams = {
    // プロジェクト基本情報
    [`${paramPrefix}/common/project-name`]: projectName,
    [`${paramPrefix}/common/environment`]: environment,
    [`${paramPrefix}/common/region`]: aws.config.region || "ap-northeast-1",
    
    // ネットワーク設定
    [`${paramPrefix}/network/vpc-cidr`]: envConfig.vpcCidr,
    [`${paramPrefix}/network/enable-flow-logs`]: String(envConfig.enableFlowLogs),
    [`${paramPrefix}/network/vpc-endpoints`]: JSON.stringify(envConfig.vpcEndpoints),
    
    // Lambda設定
    [`${paramPrefix}/lambda/memory`]: String(envConfig.lambdaMemory),
    [`${paramPrefix}/lambda/timeout`]: String(envConfig.lambdaTimeout),
    [`${paramPrefix}/lambda/log-level`]: envConfig.logLevel,
    [`${paramPrefix}/lambda/log-retention-days`]: String(envConfig.logRetentionDays),
    
    // API Gateway設定
    [`${paramPrefix}/api/rate-limit`]: String(envConfig.apiRateLimit),
    [`${paramPrefix}/api/burst-limit`]: String(envConfig.apiBurstLimit),
    [`${paramPrefix}/api/enable-waf`]: String(envConfig.enableWaf),
    [`${paramPrefix}/api/enable-websocket`]: String(envConfig.enableWebSocket),
    
    // NAT設定
    [`${paramPrefix}/nat/high-availability`]: String(envConfig.natHighAvailability),
    [`${paramPrefix}/nat/instance-type`]: envConfig.natInstanceType,
    
    // データベース設定
    [`${paramPrefix}/database/enabled`]: String(envConfig.enableDatabase),
    
    // 将来的な機能拡張用設定
    [`${paramPrefix}/phase/isolated-subnets-enabled`]: String(envConfig.enableDatabase),
    [`${paramPrefix}/phase/database-sg-enabled`]: String(envConfig.enableDatabase),
    
    // VPCエンドポイント個別設定（Gateway型のみ）
    [`${paramPrefix}/vpce/enable-s3`]: String(envConfig.vpcEndpoints.includes("s3")),
    [`${paramPrefix}/vpce/enable-dynamodb`]: String(envConfig.vpcEndpoints.includes("dynamodb")),
    
    // Lambda設定（追加）
    [`${paramPrefix}/lambda/memory-size`]: String(envConfig.lambdaMemory),
    
    // デプロイメント情報
    [`${paramPrefix}/deployment/stack-name`]: `lambda-ssm-init-${environment}`,
    [`${paramPrefix}/deployment/last-updated`]: new Date().toISOString(),
};

// ========================================
// SSMパラメータ作成
// ========================================
const parameters: aws.ssm.Parameter[] = [];

for (const [name, value] of Object.entries(commonParams)) {
    // リソース名は固定文字列を使用（Output<T>エラー回避）
    const resourceName = name.replace(/\//g, "-").replace(/^-/, "");
    const param = new aws.ssm.Parameter(
        resourceName,
        {
            name: name,
            type: "String",
            value: value,
            description: `Lambda API ${name.split("/").pop()} configuration`,
            tags: commonTags,
        }
    );
    parameters.push(param);
}

// ========================================
// セキュアパラメータ作成
// ========================================
// セキュリティ関連の暗号化パラメータ（SecureString）
// 注: 実際の値は環境変数またはCI/CDパイプラインから設定すること
const secureParams = {
    [`${paramPrefix}/security/api-key`]: pulumi.secret("CHANGE-ME-IN-PRODUCTION"),
    [`${paramPrefix}/security/jwt-secret`]: pulumi.secret("CHANGE-ME-IN-PRODUCTION"),
};

for (const [name, value] of Object.entries(secureParams)) {
    const resourceName = `secure-${name.replace(/\//g, "-").replace(/^-/, "")}`;
    const param = new aws.ssm.Parameter(
        resourceName,
        {
            name: name,
            type: "SecureString",
            value: value,
            description: `Lambda API secure ${name.split("/").pop()} configuration`,
            tags: commonTags,
        }
    );
    parameters.push(param);
}

// GitHub Personal Access Token 用のSSM Parameter（Pulumiコンフィグから取得）
const githubTokenParam = new aws.ssm.Parameter("github-token", {
    name: `${paramPrefix}/security/github-token`,
    description: "GitHub Personal Access Token for repository access",
    type: "SecureString",
    value: githubToken,
    tags: commonTags,
});
parameters.push(githubTokenParam);

// Lambda関数ソースコードリポジトリURL用のSSM Parameter（Pulumiコンフィグから取得）
const lambdaRepoUrlParam = new aws.ssm.Parameter("lambda-repo-url", {
    name: `${paramPrefix}/lambda/source/repository-url`,
    description: "Lambda functions source code repository URL",
    type: "SecureString",  // プライベートリポジトリURLなのでSecureString
    value: lambdaRepoUrl,
    tags: commonTags,
});
parameters.push(lambdaRepoUrlParam);

// Lambda関数ソースコードブランチ用のSSM Parameter（Pulumiコンフィグから取得、デフォルト値あり）
const lambdaRepoBranchParam = new aws.ssm.Parameter("lambda-repo-branch", {
    name: `${paramPrefix}/lambda/source/repository-branch`,
    description: "Lambda functions source code repository branch",
    type: "String",
    value: lambdaRepoBranch,
    tags: commonTags,
});
parameters.push(lambdaRepoBranchParam);

// Lambda関数バージョン保持数用のSSM Parameter（Pulumiコンフィグから取得、デフォルト値あり）
const lambdaVersionRetentionParam = new aws.ssm.Parameter("lambda-version-retention", {
    name: `${paramPrefix}/lambda/versioning/retain-versions`,
    description: "Number of Lambda function versions to retain",
    type: "String",
    value: String(lambdaVersionRetention),
    tags: commonTags,
});
parameters.push(lambdaVersionRetentionParam);

// ========================================
// スタック依存関係定義
// ========================================
const stackDependencies = new aws.ssm.Parameter("stack-dependencies", {
    name: `${paramPrefix}/common/stack-dependencies`,
    type: "String",
    value: JSON.stringify({
        stacks: [
            { name: "lambda-ssm-init", order: 1, required: true },
            { name: "lambda-network", order: 2, required: true },
            { name: "lambda-security", order: 3, required: true },
            { name: "lambda-vpce", order: 4, required: true },
            { name: "lambda-nat", order: 5, required: true },
            { name: "lambda-functions", order: 6, required: true },
            { name: "lambda-api-gateway", order: 7, required: true },
            { name: "lambda-waf", order: 8, required: envConfig.enableWaf },
            { name: "lambda-websocket", order: 9, required: envConfig.enableWebSocket },
            { name: "lambda-database", order: 10, required: envConfig.enableDatabase },
        ],
        deployment: {
            environment: environment,
            timestamp: new Date().toISOString(),
        },
    }),
    description: "Stack deployment dependencies and order",
    tags: commonTags,
});

// 初期化完了フラグ
const initComplete = new aws.ssm.Parameter("init-complete", {
    name: `${paramPrefix}/common/init-complete`,
    type: "String",
    value: "true",
    description: "SSM parameter initialization complete flag",
    tags: commonTags,
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