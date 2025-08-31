/**
 * pulumi/lambda-api-gateway/index.ts
 * 
 * Lambda API Gateway REST APIを構築するPulumiスクリプト
 * 基本的なREST API with APIキー認証
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// ========================================
// 環境変数取得
// ========================================
const environment = pulumi.getStack();

// ========================================
// SSMパラメータ参照（Single Source of Truth）
// ========================================
// プロジェクト名を取得
const projectNameParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/common/project-name`,
});
const projectName = pulumi.output(projectNameParam).apply(p => p.value);

// Lambda関数の設定を取得
const lambdaFunctionNameParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/lambda/main-function-name`,
});
const lambdaFunctionName = pulumi.output(lambdaFunctionNameParam).apply(p => p.value);

const lambdaFunctionArnParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/lambda/main-function-arn`,
});
const lambdaFunctionArn = pulumi.output(lambdaFunctionArnParam).apply(p => p.value);

// ========================================
// 共通タグ定義
// ========================================
const commonTags = {
    Environment: environment,
    ManagedBy: "pulumi",
    Project: "lambda-api",
    Stack: pulumi.getProject(),
};

// ========================================
// API Gateway定義
// ========================================
// REST API
const api = new aws.apigateway.RestApi("api", {
    name: pulumi.interpolate`${projectName}-api-${environment}`,
    description: `Lambda API Gateway for ${environment} environment`,
    endpointConfiguration: {
        types: "REGIONAL", // リージョナルエンドポイント（低レイテンシー）
    },
    // バイナリメディアタイプのサポート（将来の拡張用）
    binaryMediaTypes: ["application/octet-stream", "image/*"],
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-api-${environment}`,
    },
});

// ========================================
// リソースとメソッドの作成
// ========================================
// ヘルスチェックエンドポイント（/health）- APIキー不要
const healthResource = new aws.apigateway.Resource("health-resource", {
    restApi: api.id,
    parentId: api.rootResourceId,
    pathPart: "health",
});

const healthMethod = new aws.apigateway.Method("health-method", {
    restApi: api.id,
    resourceId: healthResource.id,
    httpMethod: "GET",
    authorization: "NONE", // ヘルスチェックは認証不要
});

// ヘルスチェックのモックレスポンス（Lambdaを呼ばない）
const healthIntegration = new aws.apigateway.Integration("health-integration", {
    restApi: api.id,
    resourceId: healthResource.id,
    httpMethod: healthMethod.httpMethod,
    type: "MOCK",
    requestTemplates: {
        "application/json": JSON.stringify({ statusCode: 200 }),
    },
});

const healthResponse = new aws.apigateway.IntegrationResponse("health-response", {
    restApi: api.id,
    resourceId: healthResource.id,
    httpMethod: healthMethod.httpMethod,
    statusCode: "200",
    responseTemplates: {
        "application/json": pulumi.interpolate`{"status":"healthy","environment":"${environment}","service":"${projectName}","timestamp":"$context.requestTime"}`,
    },
}, {
    dependsOn: [healthIntegration],
});

const healthMethodResponse = new aws.apigateway.MethodResponse("health-method-response", {
    restApi: api.id,
    resourceId: healthResource.id,
    httpMethod: healthMethod.httpMethod,
    statusCode: "200",
    responseModels: {
        "application/json": "Empty",
    },
}, {
    dependsOn: [healthMethod],
});

// メインAPIエンドポイント（/api）
const apiResource = new aws.apigateway.Resource("api-resource", {
    restApi: api.id,
    parentId: api.rootResourceId,
    pathPart: "api",
});

// プロキシリソース（/api/{proxy+}）- すべてのサブパスをキャッチ
const proxyResource = new aws.apigateway.Resource("proxy-resource", {
    restApi: api.id,
    parentId: apiResource.id,
    pathPart: "{proxy+}",
});

// Lambda実行権限
const lambdaPermission = new aws.lambda.Permission("lambda-permission", {
    action: "lambda:InvokeFunction",
    function: lambdaFunctionName,
    principal: "apigateway.amazonaws.com",
    sourceArn: pulumi.interpolate`${api.executionArn}/*/*`,
});

// ANY メソッド（すべてのHTTPメソッドを受け付ける）
const proxyMethod = new aws.apigateway.Method("proxy-method", {
    restApi: api.id,
    resourceId: proxyResource.id,
    httpMethod: "ANY",
    authorization: "NONE", // APIキーはリクエストバリデーターで検証
    apiKeyRequired: true, // APIキー必須
    requestParameters: {
        "method.request.header.x-api-key": true,
    },
});

// Lambda統合
const lambdaIntegration = new aws.apigateway.Integration("lambda-integration", {
    restApi: api.id,
    resourceId: proxyResource.id,
    httpMethod: proxyMethod.httpMethod,
    type: "AWS_PROXY", // Lambda Proxy統合
    integrationHttpMethod: "POST",
    uri: pulumi.interpolate`arn:aws:apigateway:${aws.config.region}:lambda:path/2015-03-31/functions/${lambdaFunctionArn}/invocations`,
}, {
    dependsOn: [lambdaPermission],
});

// /api 直下のメソッド（プロキシなし）
const apiMethod = new aws.apigateway.Method("api-method", {
    restApi: api.id,
    resourceId: apiResource.id,
    httpMethod: "ANY",
    authorization: "NONE",
    apiKeyRequired: true,
    requestParameters: {
        "method.request.header.x-api-key": true,
    },
});

const apiIntegration = new aws.apigateway.Integration("api-integration", {
    restApi: api.id,
    resourceId: apiResource.id,
    httpMethod: apiMethod.httpMethod,
    type: "AWS_PROXY",
    integrationHttpMethod: "POST",
    uri: pulumi.interpolate`arn:aws:apigateway:${aws.config.region}:lambda:path/2015-03-31/functions/${lambdaFunctionArn}/invocations`,
});

// ========================================
// API デプロイメント
// ========================================
const deployment = new aws.apigateway.Deployment("deployment", {
    restApi: api.id,
}, {
    // 依存関係を明示的に設定
    dependsOn: [
        healthMethod,
        healthIntegration,
        healthResponse,
        healthMethodResponse,
        proxyMethod,
        lambdaIntegration,
        apiMethod,
        apiIntegration,
    ],
});

// ===== ステージ =====
const stage = new aws.apigateway.Stage("lambda-api-stage", {
    deployment: deployment.id,
    restApi: api.id,
    stageName: environment,
    description: `${environment} stage`,
    // ログ設定
    accessLogSettings: {
        destinationArn: pulumi.interpolate`arn:aws:logs:${aws.config.region}:${aws.getCallerIdentity().then(i => i.accountId)}:log-group:/aws/apigateway/${projectName}-${environment}`,
        format: JSON.stringify({
            requestId: "$context.requestId",
            ip: "$context.identity.sourceIp",
            caller: "$context.identity.caller",
            user: "$context.identity.user",
            requestTime: "$context.requestTime",
            httpMethod: "$context.httpMethod",
            resourcePath: "$context.resourcePath",
            status: "$context.status",
            protocol: "$context.protocol",
            responseLength: "$context.responseLength",
            error: "$context.error.message",
            integrationLatency: "$context.integration.latency",
            integrationStatus: "$context.integration.status",
        }),
    },
    // メトリクス有効化
    xrayTracingEnabled: environment === "prod", // 本番環境のみX-Ray有効
    tags: commonTags,
});

// API Gateway用のCloudWatch Logsグループ
const apiLogGroup = new aws.cloudwatch.LogGroup("lambda-api-api-logs", {
    name: pulumi.interpolate`/aws/apigateway/${projectName}-${environment}`,
    retentionInDays: environment === "dev" ? 3 : environment === "staging" ? 7 : 14,
    tags: {
        Environment: environment,
    },
});

// ===== 使用プラン =====
const usagePlan = new aws.apigateway.UsagePlan("lambda-api-usage-plan", {
    name: pulumi.interpolate`${projectName}-usage-plan-${environment}`,
    description: `Usage plan for ${environment} environment`,
    apiStages: [{
        apiId: api.id,
        stage: stage.stageName,
    }],
    // レート制限設定（環境別）
    throttleSettings: {
        rateLimit: environment === "prod" ? 1000 : 100, // リクエスト/秒
        burstLimit: environment === "prod" ? 2000 : 200, // バースト容量
    },
    // クォータ設定（日次）
    quotaSettings: {
        limit: environment === "prod" ? 1000000 : 10000, // リクエスト/日
        period: "DAY",
    },
});

// ===== APIキー =====
// bubble.io用APIキー
const bubbleApiKey = new aws.apigateway.ApiKey("lambda-api-bubble-key", {
    name: pulumi.interpolate`${projectName}-bubble-key-${environment}`,
    description: "API key for bubble.io integration",
    enabled: true,
    tags: {
        Environment: environment,
        Client: "bubble",
    },
});

// 外部システム用APIキー（将来の拡張用）
const externalApiKey = new aws.apigateway.ApiKey("lambda-api-external-key", {
    name: pulumi.interpolate`${projectName}-external-key-${environment}`,
    description: "API key for external system integration",
    enabled: true,
    tags: {
        Environment: environment,
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
// CORS設定
// ========================================
// bubble.ioからのアクセスを許可
const corsSettings = {
    allowOrigins: environment === "prod" 
        ? ["https://your-app.bubbleapps.io"] // 本番環境では特定のドメインのみ
        : ["*"], // 開発環境では全て許可
    allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allowHeaders: ["Content-Type", "X-Api-Key", "Authorization"],
    maxAge: 86400, // 24時間
};

// ========================================
// SSMパラメータへの保存
// ========================================
// APIキー情報を別のパラメータに保存（セキュリティのため）
const apiKeyInfoParam = new aws.ssm.Parameter("api-keys", {
    name: pulumi.interpolate`/${projectName}/${environment}/api-gateway/keys`,
    type: "SecureString", // 暗号化
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
            note: "Use x-api-key header for authentication",
        })
    ),
    description: "API keys for authentication",
    tags: {
        ...commonTags,
        Sensitive: "true",
    },
});

// API GatewayエンドポイントをSSMパラメータに保存
const apiEndpointParam = new aws.ssm.Parameter("api-endpoint", {
    name: pulumi.interpolate`/${projectName}/${environment}/api-gateway/endpoint`,
    type: "String",
    value: stage.invokeUrl,
    description: "API Gateway endpoint URL",
    tags: commonTags,
    overwrite: true,
});

const apiIdParam = new aws.ssm.Parameter("api-id", {
    name: pulumi.interpolate`/${projectName}/${environment}/api-gateway/api-id`,
    type: "String",
    value: api.id,
    description: "API Gateway REST API ID",
    tags: commonTags,
    overwrite: true,
});

// ========================================
// エクスポート（表示用のみ）
// ========================================
// エクスポートは表示・確認用のみ
// 他のスタックはSSMパラメータから値を取得すること
export const outputs = {
    apiId: api.id,
    apiUrl: stage.invokeUrl,
    apiStage: stage.stageName,
    apiEndpoints: {
        health: pulumi.interpolate`${stage.invokeUrl}health`,
        api: pulumi.interpolate`${stage.invokeUrl}api`,
    },
    apiKeyIds: {
        bubbleKeyId: bubbleApiKey.id,
        externalKeyId: externalApiKey.id,
    },
    retrieveKeysCommand: pulumi.interpolate`aws ssm get-parameter --name /${projectName}/${environment}/api-gateway/keys --with-decryption --query 'Parameter.Value' --output text | jq .`,
};

// 使用例
export const usageExample = {
    curlHealth: pulumi.interpolate`curl ${stage.invokeUrl}health`,
    curlApi: pulumi.interpolate`curl -H "x-api-key: YOUR_API_KEY" ${stage.invokeUrl}api`,
};

// サマリー
export const summary = {
    environment: environment,
    rateLimit: `${environment === "prod" ? 1000 : 100} req/sec`,
    dailyQuota: `${environment === "prod" ? "1M" : "10K"} requests`,
    authentication: "API Key (x-api-key header)",
    endpoints: 2, // health, api/*
};
