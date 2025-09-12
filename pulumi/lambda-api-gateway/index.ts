/**
 * pulumi/lambda-api-gateway/index.ts
 * 
 * API Gatewayを構築するPulumiスクリプト
 * わかりやすさを重視したシンプルな実装
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// ========================================
// 1. 基本設定
// ========================================
const environment = pulumi.getStack();
const commonTags = {
    Environment: environment,
    ManagedBy: "pulumi",
    Project: "lambda-api",
};

// ========================================
// 2. SSMパラメータから設定値を取得
// ========================================
// プロジェクト名
const projectNameParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/common/project-name`,
});
const projectName = pulumi.output(projectNameParam).apply(p => p.value);

// Lambda関数の情報（main関数）
const lambdaFunctionNameParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/lambda/main-function-name`,
});
const lambdaFunctionName = pulumi.output(lambdaFunctionNameParam).apply(p => p.value);

const lambdaFunctionArnParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/lambda/main-function-arn`,
});
const lambdaFunctionArn = pulumi.output(lambdaFunctionArnParam).apply(p => p.value);

// ========================================
// 3. REST APIを作成
// ========================================
const api = new aws.apigateway.RestApi("api", {
    name: pulumi.interpolate`${projectName}-api-${environment}`,
    description: `Lambda API Gateway for ${environment} environment`,
    endpointConfiguration: {
        types: "REGIONAL",  // リージョナルエンドポイント
    },
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-api-${environment}`,
    },
});

// ========================================
// 4. ヘルスチェックエンドポイント（/health）
// ========================================
// リソース作成
const healthResource = new aws.apigateway.Resource("health-resource", {
    restApi: api.id,
    parentId: api.rootResourceId,
    pathPart: "health",
});

// メソッド作成
const healthMethod = new aws.apigateway.Method("health-method", {
    restApi: api.id,
    resourceId: healthResource.id,
    httpMethod: "GET",
    authorization: "NONE",  // 認証不要
});

// Lambda統合（ヘルスチェックもLambda関数で処理）
const healthIntegration = new aws.apigateway.Integration("health-integration", {
    restApi: api.id,
    resourceId: healthResource.id,
    httpMethod: healthMethod.httpMethod,
    type: "AWS_PROXY",
    integrationHttpMethod: "POST",
    uri: pulumi.interpolate`arn:aws:apigateway:${aws.config.region}:lambda:path/2015-03-31/functions/${lambdaFunctionArn}/invocations`,
}, {
    dependsOn: [lambdaPermission],
});

// ========================================
// 5. メインAPIエンドポイント（/api）
// ========================================
// /apiリソース
const apiResource = new aws.apigateway.Resource("api-resource", {
    restApi: api.id,
    parentId: api.rootResourceId,
    pathPart: "api",
});

// Lambda実行権限
const lambdaPermission = new aws.lambda.Permission("lambda-permission", {
    action: "lambda:InvokeFunction",
    function: lambdaFunctionName,
    principal: "apigateway.amazonaws.com",
    sourceArn: pulumi.interpolate`${api.executionArn}/*/*`,
});

// /api直下のメソッド
const apiMethod = new aws.apigateway.Method("api-method", {
    restApi: api.id,
    resourceId: apiResource.id,
    httpMethod: "ANY",
    authorization: "NONE",
    apiKeyRequired: true,  // APIキー必須
});

// Lambda統合
const apiIntegration = new aws.apigateway.Integration("api-integration", {
    restApi: api.id,
    resourceId: apiResource.id,
    httpMethod: apiMethod.httpMethod,
    type: "AWS_PROXY",
    integrationHttpMethod: "POST",
    uri: pulumi.interpolate`arn:aws:apigateway:${aws.config.region}:lambda:path/2015-03-31/functions/${lambdaFunctionArn}/invocations`,
}, {
    dependsOn: [lambdaPermission],
});

// ========================================
// 6. プロキシエンドポイント（/api/{proxy+}）
// ========================================
// すべてのサブパスをキャッチ
const proxyResource = new aws.apigateway.Resource("proxy-resource", {
    restApi: api.id,
    parentId: apiResource.id,
    pathPart: "{proxy+}",
});

// プロキシメソッド
const proxyMethod = new aws.apigateway.Method("proxy-method", {
    restApi: api.id,
    resourceId: proxyResource.id,
    httpMethod: "ANY",
    authorization: "NONE",
    apiKeyRequired: true,
});

// Lambda統合
const proxyIntegration = new aws.apigateway.Integration("proxy-integration", {
    restApi: api.id,
    resourceId: proxyResource.id,
    httpMethod: proxyMethod.httpMethod,
    type: "AWS_PROXY",
    integrationHttpMethod: "POST",
    uri: pulumi.interpolate`arn:aws:apigateway:${aws.config.region}:lambda:path/2015-03-31/functions/${lambdaFunctionArn}/invocations`,
}, {
    dependsOn: [lambdaPermission],
});

// ========================================
// 7. デプロイメントとステージ
// ========================================
// デプロイメント
const deployment = new aws.apigateway.Deployment("deployment", {
    restApi: api.id,
}, {
    dependsOn: [
        healthMethod, healthIntegration,
        apiMethod, apiIntegration,
        proxyMethod, proxyIntegration,
    ],
});

// CloudWatch Logsグループ
const logGroup = new aws.cloudwatch.LogGroup("api-logs", {
    name: pulumi.interpolate`/aws/apigateway/${projectName}-${environment}`,
    retentionInDays: environment === "dev" ? 3 : environment === "staging" ? 7 : 14,
    tags: commonTags,
});

// ステージ
const stage = new aws.apigateway.Stage("stage", {
    deployment: deployment.id,
    restApi: api.id,
    stageName: environment,
    description: `${environment} stage`,
    accessLogSettings: {
        destinationArn: pulumi.interpolate`arn:aws:logs:${aws.config.region}:${aws.getCallerIdentity().then(i => i.accountId)}:log-group:${logGroup.name}`,
        format: JSON.stringify({
            requestId: "$context.requestId",
            ip: "$context.identity.sourceIp",
            requestTime: "$context.requestTime",
            httpMethod: "$context.httpMethod",
            resourcePath: "$context.resourcePath",
            status: "$context.status",
        }),
    },
    xrayTracingEnabled: environment === "prod",
    tags: commonTags,
});

// ========================================
// 8. 使用プランとAPIキー
// ========================================
// 使用プラン
const usagePlan = new aws.apigateway.UsagePlan("usage-plan", {
    name: pulumi.interpolate`${projectName}-usage-plan-${environment}`,
    description: `Usage plan for ${environment}`,
    apiStages: [{
        apiId: api.id,
        stage: stage.stageName,
    }],
    // レート制限（環境別）
    throttleSettings: {
        rateLimit: environment === "prod" ? 1000 : 100,
        burstLimit: environment === "prod" ? 2000 : 200,
    },
    // 日次クォータ
    quotaSettings: {
        limit: environment === "prod" ? 1000000 : 10000,
        period: "DAY",
    },
});

// bubble.io用APIキー
const bubbleApiKey = new aws.apigateway.ApiKey("bubble-api-key", {
    name: pulumi.interpolate`${projectName}-bubble-key-${environment}`,
    description: "API key for bubble.io integration",
    enabled: true,
    tags: {
        ...commonTags,
        Client: "bubble",
    },
});

// 外部システム用APIキー
const externalApiKey = new aws.apigateway.ApiKey("external-api-key", {
    name: pulumi.interpolate`${projectName}-external-key-${environment}`,
    description: "API key for external system",
    enabled: true,
    tags: {
        ...commonTags,
        Client: "external",
    },
});

// APIキーと使用プランの関連付け
const bubbleUsagePlanKey = new aws.apigateway.UsagePlanKey("bubble-usage-key", {
    keyId: bubbleApiKey.id,
    keyType: "API_KEY",
    usagePlanId: usagePlan.id,
});

const externalUsagePlanKey = new aws.apigateway.UsagePlanKey("external-usage-key", {
    keyId: externalApiKey.id,
    keyType: "API_KEY",
    usagePlanId: usagePlan.id,
});

// ========================================
// 9. SSMパラメータに保存（他スタックから参照用）
// ========================================
// APIエンドポイント
const apiEndpointParam = new aws.ssm.Parameter("api-endpoint-param", {
    name: pulumi.interpolate`/${projectName}/${environment}/api-gateway/endpoint`,
    type: "String",
    value: stage.invokeUrl,
    description: "API Gateway endpoint URL",
    tags: commonTags,
});

// API ID
const apiIdParam = new aws.ssm.Parameter("api-id-param", {
    name: pulumi.interpolate`/${projectName}/${environment}/api-gateway/api-id`,
    type: "String",
    value: api.id,
    description: "API Gateway REST API ID",
    tags: commonTags,
});

// APIキー（暗号化して保存）
const apiKeysParam = new aws.ssm.Parameter("api-keys-param", {
    name: pulumi.interpolate`/${projectName}/${environment}/api-gateway/keys`,
    type: "SecureString",
    value: pulumi.all([bubbleApiKey.value, externalApiKey.value]).apply(
        ([bubbleKey, externalKey]) => JSON.stringify({
            bubble: {
                key: bubbleKey,
                usage: "bubble.io integration",
            },
            external: {
                key: externalKey,
                usage: "External system integration",
            },
        })
    ),
    description: "API keys for authentication",
    tags: {
        ...commonTags,
        Sensitive: "true",
    },
});

// ========================================
// 10. エクスポート（確認用）
// ========================================
export const outputs = {
    // API情報
    apiId: api.id,
    apiUrl: stage.invokeUrl,
    stage: environment,
    
    // エンドポイント
    endpoints: {
        health: pulumi.interpolate`${stage.invokeUrl}health`,
        api: pulumi.interpolate`${stage.invokeUrl}api`,
    },
    
    // APIキーID
    apiKeyIds: {
        bubble: bubbleApiKey.id,
        external: externalApiKey.id,
    },
    
    // APIキー取得コマンド
    getApiKeysCommand: pulumi.interpolate`aws ssm get-parameter --name /${projectName}/${environment}/api-gateway/keys --with-decryption --query 'Parameter.Value' --output text | jq .`,
};

// 使用例
export const usageExamples = {
    healthCheck: pulumi.interpolate`curl ${stage.invokeUrl}health`,
    apiCall: pulumi.interpolate`curl -H "x-api-key: YOUR_API_KEY" ${stage.invokeUrl}api`,
};

// サマリー
export const summary = {
    environment: environment,
    rateLimit: `${environment === "prod" ? 1000 : 100} req/sec`,
    dailyQuota: `${environment === "prod" ? "1M" : "10K"} requests`,
    authentication: "API Key (x-api-key header)",
    endpoints: ["health", "api", "api/{proxy+}"],
};