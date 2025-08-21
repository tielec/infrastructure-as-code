/**
 * pulumi/lambda-ssm-init/index.ts
 * 
 * Lambda APIインフラのSSMパラメータ初期化スタック
 * 全スタックで使用する共通パラメータを事前に設定
 * Jenkinsと同様の設計思想で、SSMパラメータストアをSingle Source of Truthとして使用
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "lambda-api";
const environment = pulumi.getStack();

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
        natInstanceType: "t3.nano",
        vpcEndpoints: ["s3", "ssm", "secretsmanager"],
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
        natInstanceType: "t3.medium",
        vpcEndpoints: ["s3", "ssm", "secretsmanager", "dynamodb", "rds"],
    },
};

// 現在の環境の設定を取得
const envConfig = environmentConfig[environment as keyof typeof environmentConfig] || environmentConfig.dev;

// パラメータのプレフィックス
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
    
    // Phase設定（Phase 2の機能）
    [`${paramPrefix}/phase/isolated-subnets-enabled`]: String(envConfig.enableDatabase),
    
    // デプロイメント情報
    [`${paramPrefix}/deployment/stack-name`]: `lambda-ssm-init-${environment}`,
    [`${paramPrefix}/deployment/last-updated`]: new Date().toISOString(),
};

// SSMパラメータを作成
const parameters: aws.ssm.Parameter[] = [];

for (const [name, value] of Object.entries(commonParams)) {
    const param = new aws.ssm.Parameter(
        `param-${name.replace(/\//g, "-").replace(/^-/, "")}`,
        {
            name: name,
            type: "String",
            value: value,
            description: `Lambda API ${name.split("/").pop()} configuration`,
            tags: {
                Environment: environment,
                ManagedBy: "pulumi",
                Stack: "lambda-ssm-init",
            },
        }
    );
    parameters.push(param);
}

// セキュリティ関連の暗号化パラメータ（SecureString）
const secureParams = {
    [`${paramPrefix}/security/api-key`]: config.getSecret("apiKey") || pulumi.secret("CHANGE-ME-IN-PRODUCTION"),
    [`${paramPrefix}/security/jwt-secret`]: config.getSecret("jwtSecret") || pulumi.secret("CHANGE-ME-IN-PRODUCTION"),
};

for (const [name, value] of Object.entries(secureParams)) {
    const param = new aws.ssm.Parameter(
        `secure-param-${name.replace(/\//g, "-").replace(/^-/, "")}`,
        {
            name: name,
            type: "SecureString",
            value: value,
            description: `Lambda API secure ${name.split("/").pop()} configuration`,
            tags: {
                Environment: environment,
                ManagedBy: "pulumi",
                Stack: "lambda-ssm-init",
            },
        }
    );
    parameters.push(param);
}

// スタック間の依存関係を定義
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
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Stack: "lambda-ssm-init",
    },
});

// 初期化完了フラグ
const initComplete = new aws.ssm.Parameter("init-complete", {
    name: `${paramPrefix}/common/init-complete`,
    type: "String",
    value: "true",
    description: "SSM parameter initialization complete flag",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Stack: "lambda-ssm-init",
    },
});

// ========================================
// エクスポート（最小限に限定）
// ========================================
// すべての値はSSMパラメータストアに保存されているため、
// stack outputは必要最小限のみエクスポート

// デプロイメント確認用の基本情報のみ
export const deploymentInfo = {
    stack: "lambda-ssm-init",
    environment: environment,
    timestamp: new Date().toISOString(),
    ssmParameterPrefix: paramPrefix,
    parametersCreated: parameters.length,
};

// デプロイ完了の確認用
export const deploymentComplete = true;