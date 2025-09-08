/**
 * components/applicationParameters.ts
 * 
 * アプリケーション用SSMパラメータの定義
 * AI API設定、その他のアプリケーション固有の設定を管理
 * 
 * 注: タグはSSMParameterHelperによって自動的にすべてのパラメータに適用されます
 */
import * as pulumi from "@pulumi/pulumi";
import { SSMParameterHelper } from "@tielec/pulumi-components";

/**
 * AI API設定インターフェース
 */
interface AIApiConfig {
    claudeApiKey?: string;
    claudeSpeedModel?: string;
    claudeQualityModel?: string;
    openaiApiKey?: string;
    openaiSpeedModel?: string;
    openaiQualityModel?: string;
}

/**
 * アプリケーション設定インターフェース
 */
interface ApplicationConfig {
    aiApi: AIApiConfig;
    // 将来的に他のアプリケーション設定を追加可能
}

/**
 * アプリケーション用パラメータの作成
 */
export function createApplicationParameters(
    ssmHelper: SSMParameterHelper,
    config: ApplicationConfig
) {
    const parameters: Record<string, any> = {};

    // ========================================
    // AI API設定パラメータ
    // ========================================
    
    // Claude API設定
    if (config.aiApi.claudeApiKey !== undefined) {
        parameters.claudeApiKey = ssmHelper.createParameter('/settings/claude-api-key', {
            paramType: 'init-only',
            value: config.aiApi.claudeApiKey,
            type: "SecureString",
            description: "Anthropic Claude APIのAPIキー",
        });
    }

    if (config.aiApi.claudeSpeedModel !== undefined) {
        parameters.claudeSpeedModel = ssmHelper.createParameter('/settings/claude-speed-model', {
            paramType: 'managed',
            value: config.aiApi.claudeSpeedModel,
            type: "String",
            description: "高速処理用のClaudeモデル名",
        });
    }

    if (config.aiApi.claudeQualityModel !== undefined) {
        parameters.claudeQualityModel = ssmHelper.createParameter('/settings/claude-quality-model', {
            paramType: 'managed',
            value: config.aiApi.claudeQualityModel,
            type: "String",
            description: "高品質処理用のClaudeモデル名",
        });
    }

    // OpenAI API設定
    if (config.aiApi.openaiApiKey !== undefined) {
        parameters.openaiApiKey = ssmHelper.createParameter('/settings/openai-api-key', {
            paramType: 'init-only',
            value: config.aiApi.openaiApiKey,
            type: "SecureString",
            description: "OpenAI APIのAPIキー",
        });
    }

    if (config.aiApi.openaiSpeedModel !== undefined) {
        parameters.openaiSpeedModel = ssmHelper.createParameter('/settings/openai-speed-model', {
            paramType: 'managed',
            value: config.aiApi.openaiSpeedModel,
            type: "String",
            description: "高速処理用のOpenAIモデル名",
        });
    }

    if (config.aiApi.openaiQualityModel !== undefined) {
        parameters.openaiQualityModel = ssmHelper.createParameter('/settings/openai-quality-model', {
            paramType: 'managed',
            value: config.aiApi.openaiQualityModel,
            type: "String",
            description: "高品質処理用のOpenAIモデル名",
        });
    }

    // ========================================
    // 将来的なアプリケーション設定の追加箇所
    // ========================================
    // 例: 外部API連携、機能フラグ、アプリケーション固有の設定など

    return parameters;
}