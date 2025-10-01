/**
 * components/config.ts
 * 
 * Pulumi設定の取得と管理
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

/**
 * 設定を取得してインフラとアプリケーション設定に分離
 */
export function loadConfig() {
    const config = new pulumi.Config();
    const environment = pulumi.getStack();
    const projectName = "lambda-api";
    
    // インフラ管理用設定
    const infrastructure = {
        environment,
        projectName,
        region: aws.config.region || "ap-northeast-1",
        vpcCidr: config.require("vpcCidr"),
        enableFlowLogs: config.requireBoolean("enableFlowLogs"),
        vpcEndpoints: JSON.parse(config.require("vpcEndpoints")),
        lambdaMemory: config.requireNumber("lambdaMemory"),
        lambdaTimeout: config.requireNumber("lambdaTimeout"),
        logLevel: config.require("logLevel"),
        logRetentionDays: config.requireNumber("logRetentionDays"),
        apiRateLimit: config.requireNumber("apiRateLimit"),
        apiBurstLimit: config.requireNumber("apiBurstLimit"),
        enableWaf: config.requireBoolean("enableWaf"),
        enableWebSocket: config.requireBoolean("enableWebSocket"),
        enableDatabase: config.requireBoolean("enableDatabase"),
        natHighAvailability: config.requireBoolean("natHighAvailability"),
        natInstanceType: config.require("natInstanceType"),
        githubToken: config.require("githubToken"),
        lambdaRepoUrl: config.require("lambdaRepoUrl"),
        lambdaRepoBranch: config.require("lambdaRepoBranch"),
        lambdaVersionRetention: config.requireNumber("lambdaVersionRetention"),
    };
    
    // アプリケーション用設定（AI API）
    const application = {
        aiApi: {
            claudeApiKey: config.get("claudeApiKey") || "PLACEHOLDER_PLEASE_UPDATE_WITH_ACTUAL_API_KEY",
            claudeSpeedModel: config.get("claudeSpeedModel") || "claude-3-haiku-20240307",
            claudeQualityModel: config.get("claudeQualityModel") || "claude-3-5-sonnet-20240620",
            openaiApiKey: config.get("openaiApiKey") || "PLACEHOLDER_PLEASE_UPDATE_WITH_ACTUAL_API_KEY",
            openaiSpeedModel: config.get("openaiSpeedModel") || "gpt-4.1-mini",
            openaiQualityModel: config.get("openaiQualityModel") || "gpt-4.1",
        }
    };
    
    // 共通タグ
    const commonTags = {
        Environment: environment,
        ManagedBy: "pulumi",
        Project: projectName,
        Stack: pulumi.getProject(),
    };
    
    return {
        projectName,
        environment,
        paramPrefix: `/${projectName}/${environment}`,
        commonTags,
        infrastructure,
        application,
    };
}