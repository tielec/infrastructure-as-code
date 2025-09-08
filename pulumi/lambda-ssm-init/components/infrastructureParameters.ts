/**
 * components/infrastructureParameters.ts
 * 
 * インフラ管理用SSMパラメータの定義
 * VPC、ネットワーク、Lambda基本設定、セキュリティ関連の設定を管理
 * 
 * 注: タグはSSMParameterHelperによって自動的にすべてのパラメータに適用されます
 */
import * as pulumi from "@pulumi/pulumi";
import { SSMParameterHelper } from "@tielec/pulumi-components";

/**
 * インフラ管理用パラメータの設定インターフェース
 */
interface InfrastructureConfig {
    environment: string;
    projectName: string;
    region: string;
    vpcCidr: string;
    enableFlowLogs: boolean;
    vpcEndpoints: string[];
    lambdaMemory: number;
    lambdaTimeout: number;
    logLevel: string;
    logRetentionDays: number;
    apiRateLimit: number;
    apiBurstLimit: number;
    enableWaf: boolean;
    enableWebSocket: boolean;
    enableDatabase: boolean;
    natHighAvailability: boolean;
    natInstanceType: string;
    githubToken: string;
    lambdaRepoUrl: string;
    lambdaRepoBranch: string;
    lambdaVersionRetention: number;
}

/**
 * インフラ管理用パラメータの作成
 */
export function createInfrastructureParameters(
    ssmHelper: SSMParameterHelper,
    config: InfrastructureConfig
) {
    const parameters: Record<string, any> = {};

    // ========================================
    // プロジェクト基本情報
    // ========================================
    parameters.projectName = ssmHelper.createParameter('/common/project-name', {
        paramType: 'managed',
        value: config.projectName,
        description: "Project name",
    });

    parameters.environment = ssmHelper.createParameter('/common/environment', {
        paramType: 'managed',
        value: config.environment,
        description: "Environment",
    });

    parameters.region = ssmHelper.createParameter('/common/region', {
        paramType: 'managed',
        value: config.region,
        description: "AWS region",
    });

    // ========================================
    // ネットワーク設定
    // ========================================
    parameters.vpcCidr = ssmHelper.createParameter('/network/vpc-cidr', {
        paramType: 'managed',
        value: config.vpcCidr,
        description: "VPC CIDR block",
    });

    parameters.enableFlowLogs = ssmHelper.createParameter('/network/enable-flow-logs', {
        paramType: 'managed',
        value: String(config.enableFlowLogs),
        description: "Enable VPC flow logs",
    });

    parameters.vpcEndpoints = ssmHelper.createParameter('/network/vpc-endpoints', {
        paramType: 'managed',
        value: JSON.stringify(config.vpcEndpoints),
        description: "VPC endpoints configuration",
    });

    // ========================================
    // Lambda設定
    // ========================================
    parameters.lambdaMemory = ssmHelper.createParameter('/lambda/memory', {
        paramType: 'managed',
        value: String(config.lambdaMemory),
        description: "Lambda memory size",
    });

    parameters.lambdaTimeout = ssmHelper.createParameter('/lambda/timeout', {
        paramType: 'managed',
        value: String(config.lambdaTimeout),
        description: "Lambda timeout",
    });

    parameters.lambdaLogLevel = ssmHelper.createParameter('/lambda/log-level', {
        paramType: 'managed',
        value: config.logLevel,
        description: "Lambda log level",
    });

    parameters.lambdaLogRetentionDays = ssmHelper.createParameter('/lambda/log-retention-days', {
        paramType: 'managed',
        value: String(config.logRetentionDays),
        description: "CloudWatch logs retention days",
    });

    parameters.lambdaMemorySize = ssmHelper.createParameter('/lambda/memory-size', {
        paramType: 'managed',
        value: String(config.lambdaMemory),
        description: "Lambda memory size (duplicate for compatibility)",
    });

    // ========================================
    // API Gateway設定
    // ========================================
    parameters.apiRateLimit = ssmHelper.createParameter('/api/rate-limit', {
        paramType: 'managed',
        value: String(config.apiRateLimit),
        description: "API rate limit",
    });

    parameters.apiBurstLimit = ssmHelper.createParameter('/api/burst-limit', {
        paramType: 'managed',
        value: String(config.apiBurstLimit),
        description: "API burst limit",
    });

    parameters.enableWaf = ssmHelper.createParameter('/api/enable-waf', {
        paramType: 'managed',
        value: String(config.enableWaf),
        description: "Enable WAF",
    });

    parameters.enableWebSocket = ssmHelper.createParameter('/api/enable-websocket', {
        paramType: 'managed',
        value: String(config.enableWebSocket),
        description: "Enable WebSocket",
    });

    // ========================================
    // NAT設定
    // ========================================
    parameters.natHighAvailability = ssmHelper.createParameter('/nat/high-availability', {
        paramType: 'managed',
        value: String(config.natHighAvailability),
        description: "NAT high availability",
    });

    parameters.natInstanceType = ssmHelper.createParameter('/nat/instance-type', {
        paramType: 'managed',
        value: config.natInstanceType,
        description: "NAT instance type",
    });

    // ========================================
    // データベース設定
    // ========================================
    parameters.databaseEnabled = ssmHelper.createParameter('/database/enabled', {
        paramType: 'managed',
        value: String(config.enableDatabase),
        description: "Database enabled",
    });

    // ========================================
    // フェーズ設定
    // ========================================
    parameters.isolatedSubnetsEnabled = ssmHelper.createParameter('/phase/isolated-subnets-enabled', {
        paramType: 'managed',
        value: String(config.enableDatabase),
        description: "Isolated subnets enabled",
    });

    parameters.databaseSgEnabled = ssmHelper.createParameter('/phase/database-sg-enabled', {
        paramType: 'managed',
        value: String(config.enableDatabase),
        description: "Database security group enabled",
    });

    // ========================================
    // VPCエンドポイント設定
    // ========================================
    parameters.vpceEnableS3 = ssmHelper.createParameter('/vpce/enable-s3', {
        paramType: 'managed',
        value: String(config.vpcEndpoints.includes("s3")),
        description: "Enable S3 VPC endpoint",
    });

    parameters.vpceEnableDynamodb = ssmHelper.createParameter('/vpce/enable-dynamodb', {
        paramType: 'managed',
        value: String(config.vpcEndpoints.includes("dynamodb")),
        description: "Enable DynamoDB VPC endpoint",
    });

    // ========================================
    // デプロイメント情報
    // ========================================
    parameters.stackName = ssmHelper.createParameter('/deployment/stack-name', {
        paramType: 'managed',
        value: `lambda-ssm-init-${config.environment}`,
        description: "Stack name",
    });

    parameters.lastUpdated = ssmHelper.createParameter('/deployment/last-updated', {
        paramType: 'managed',
        value: new Date().toISOString(),
        description: "Last updated timestamp",
    });

    // ========================================
    // セキュリティ関連の暗号化パラメータ
    // ========================================
    parameters.githubToken = ssmHelper.createParameter('/security/github-token', {
        paramType: 'init-only',
        value: config.githubToken,
        type: "SecureString",
        description: "GitHub Personal Access Token for repository access",
    });

    parameters.lambdaRepoUrl = ssmHelper.createParameter('/lambda/source/repository-url', {
        paramType: 'init-only',
        value: config.lambdaRepoUrl,
        type: "SecureString",
        description: "Lambda functions source code repository URL",
    });

    parameters.lambdaRepoBranch = ssmHelper.createParameter('/lambda/source/repository-branch', {
        paramType: 'managed',
        value: config.lambdaRepoBranch,
        type: "String",
        description: "Lambda functions source code repository branch",
    });

    parameters.lambdaVersionRetention = ssmHelper.createParameter('/lambda/versioning/retain-versions', {
        paramType: 'managed',
        value: String(config.lambdaVersionRetention),
        type: "String",
        description: "Number of Lambda function versions to retain",
    });

    // ========================================
    // 初期化完了フラグ
    // ========================================
    parameters.initComplete = ssmHelper.createParameter('/common/init-complete', {
        paramType: 'managed',
        value: "true",
        type: "String",
        description: "SSM parameter initialization complete flag",
    });

    return parameters;
}