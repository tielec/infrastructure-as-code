/**
 * pulumi/lambda-ssm-init/index.ts
 * 
 * Lambda APIインフラのSSMパラメータ初期化スタック
 * SSMパラメータストアをSingle Source of Truthとして使用
 */
import { SSMParameterHelper } from "@tielec/pulumi-components";
import { 
    loadConfig,
    createInfrastructureParameters, 
    createApplicationParameters
} from "./components";

// ========================================
// 設定の読み込みとSSMヘルパー初期化
// ========================================
const config = loadConfig();
const ssmHelper = new SSMParameterHelper(config.paramPrefix, config.commonTags);

// ========================================
// パラメータの作成
// ========================================
const infrastructureParams = createInfrastructureParameters(ssmHelper, config.infrastructure);
const applicationParams = createApplicationParameters(ssmHelper, config.application);

// ========================================
// エクスポート
// ========================================
export const outputs = {
    stack: "lambda-ssm-init",
    environment: config.environment,
    ssmParameterPrefix: config.paramPrefix,
    parametersCreated: ssmHelper.getParameterCount(),
    
    // インフラ管理用パラメータ名
    infrastructure: {
        initCompleteFlag: infrastructureParams.initComplete?.name,
        githubTokenParameterName: infrastructureParams.githubToken?.name,
        lambdaRepoUrlParameterName: infrastructureParams.lambdaRepoUrl?.name,
        lambdaRepoBranchParameterName: infrastructureParams.lambdaRepoBranch?.name,
        lambdaVersionRetentionParameterName: infrastructureParams.lambdaVersionRetention?.name,
    },
    
    // アプリケーション用パラメータ名（AI API）
    application: {
        aiApi: {
            claudeApiKeyParameterName: applicationParams.claudeApiKey?.name,
            claudeSpeedModelParameterName: applicationParams.claudeSpeedModel?.name,
            claudeQualityModelParameterName: applicationParams.claudeQualityModel?.name,
            openaiApiKeyParameterName: applicationParams.openaiApiKey?.name,
            openaiSpeedModelParameterName: applicationParams.openaiSpeedModel?.name,
            openaiQualityModelParameterName: applicationParams.openaiQualityModel?.name,
        }
    }
};

// デプロイ完了の確認用
export const deploymentComplete = true;