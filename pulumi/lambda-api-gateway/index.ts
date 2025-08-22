/**
 * pulumi/lambda-api-gateway/index.ts
 * 
 * Lambda API Gateway REST APIを構築するPulumiスクリプト
 * Phase 1: 基本的なREST API with APIキー認証
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// 環境変数を取得
const environment = pulumi.getStack();

// SSMパラメータストアから設定を取得（Single Source of Truth）
const projectNameParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/common/project-name`,
});
const projectName = pulumi.output(projectNameParam).apply(p => p.value);

// スタック参照名は固定（コンベンションとして）
const functionsStackName = "lambda-functions";

// 既存のスタックから値を取得
const functionsStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${functionsStackName}/${environment}`);
const lambdaFunctionName = functionsStack.getOutput("functionName");
const lambdaFunctionArn = functionsStack.getOutput("functionArn");

// ===== REST API =====
const api = new aws.apigateway.RestApi("lambda-api-api", {
    name: pulumi.interpolate`${projectName}-api-${environment}`,
    description: `Lambda API Gateway for ${environment} environment`,
    endpointConfiguration: {
        types: "REGIONAL", // リージョナルエンドポイント（低レイテンシー）
    },
    // バイナリメディアタイプのサポート（将来の拡張用）
    binaryMediaTypes: ["application/octet-stream", "image/*"],
    tags: {
        Name: pulumi.interpolate`${projectName}-api-${environment}`,
        Environment: environment,
    },
});

// ===== リソースとメソッドの作成 =====
// ヘルスチェックエンドポイント（/health）- APIキー不要
const healthResource = new aws.apigateway.Resource("lambda-api-health-resource", {
    restApi: api.id,
    parentId: api.rootResourceId,
    pathPart: "health",
});

const healthMethod = new aws.apigateway.Method("lambda-api-health-method", {
    restApi: api.id,
    resourceId: healthResource.id,
    httpMethod: "GET",
    authorization: "NONE", // ヘルスチェックは認証不要
});

// ヘルスチェックのモックレスポンス（Lambdaを呼ばない）
const healthIntegration = new aws.apigateway.Integration("lambda-api-health-integration", {
    restApi: api.id,
    resourceId: healthResource.id,
    httpMethod: healthMethod.httpMethod,
    type: "MOCK",
    requestTemplates: {
        "application/json": JSON.stringify({ statusCode: 200 }),
    },
});

const healthResponse = new aws.apigateway.IntegrationResponse("lambda-api-health-response", {
    restApi: api.id,
    resourceId: healthResource.id,
    httpMethod: healthMethod.httpMethod,
    statusCode: "200",
    responseTemplates: {
        "application/json": JSON.stringify({
            status: "healthy",
            environment: environment,
            service: projectName,
            timestamp: "$context.requestTime",
        }),
    },
}, {
    dependsOn: [healthIntegration],
});

const healthMethodResponse = new aws.apigateway.MethodResponse("lambda-api-health-method-response", {
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

// ===== メインAPIエンドポイント（/api）=====
const apiResource = new aws.apigateway.Resource("lambda-api-api-resource", {
    restApi: api.id,
    parentId: api.rootResourceId,
    pathPart: "api",
});

// プロキシリソース（/api/{proxy+}）- すべてのサブパスをキャッチ
const proxyResource = new aws.apigateway.Resource("lambda-api-proxy-resource", {
    restApi: api.id,
    parentId: apiResource.id,
    pathPart: "{proxy+}",
});

// Lambda実行権限
const lambdaPermission = new aws.lambda.Permission(`${projectName}-api-lambda-permission`, {
    action: "lambda:InvokeFunction",
    function: lambdaFunctionName,
    principal: "apigateway.amazonaws.com",
    sourceArn: pulumi.interpolate`${api.executionArn}/*/*`,
});

// ANY メソッド（すべてのHTTPメソッドを受け付ける）
const proxyMethod = new aws.apigateway.Method(`${projectName}-proxy-method`, {
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
const lambdaIntegration = new aws.apigateway.Integration(`${projectName}-lambda-integration`, {
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
const apiMethod = new aws.apigateway.Method(`${projectName}-api-method`, {
    restApi: api.id,
    resourceId: apiResource.id,
    httpMethod: "ANY",
    authorization: "NONE",
    apiKeyRequired: true,
    requestParameters: {
        "method.request.header.x-api-key": true,
    },
});

const apiIntegration = new aws.apigateway.Integration(`${projectName}-api-integration`, {
    restApi: api.id,
    resourceId: apiResource.id,
    httpMethod: apiMethod.httpMethod,
    type: "AWS_PROXY",
    integrationHttpMethod: "POST",
    uri: pulumi.interpolate`arn:aws:apigateway:${aws.config.region}:lambda:path/2015-03-31/functions/${lambdaFunctionArn}/invocations`,
});

// ===== API デプロイメント =====
const deployment = new aws.apigateway.Deployment(`${projectName}-deployment`, {
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
const stage = new aws.apigateway.Stage(`${projectName}-stage`, {
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
    tags: {
        Environment: environment,
    },
});

// API Gateway用のCloudWatch Logsグループ
const apiLogGroup = new aws.cloudwatch.LogGroup(`${projectName}-api-logs`, {
    name: `/aws/apigateway/${projectName}-${environment}`,
    retentionInDays: environment === "dev" ? 3 : environment === "staging" ? 7 : 14,
    tags: {
        Environment: environment,
    },
});

// ===== 使用プラン =====
const usagePlan = new aws.apigateway.UsagePlan(`${projectName}-usage-plan`, {
    name: `${projectName}-usage-plan-${environment}`,
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
const bubbleApiKey = new aws.apigateway.ApiKey(`${projectName}-bubble-key`, {
    name: `${projectName}-bubble-key-${environment}`,
    description: "API key for bubble.io integration",
    enabled: true,
    tags: {
        Environment: environment,
        Client: "bubble",
    },
});

// 外部システム用APIキー（将来の拡張用）
const externalApiKey = new aws.apigateway.ApiKey(`${projectName}-external-key`, {
    name: `${projectName}-external-key-${environment}`,
    description: "API key for external system integration",
    enabled: true,
    tags: {
        Environment: environment,
        Client: "external",
    },
});

// APIキーと使用プランの関連付け
const bubbleUsagePlanKey = new aws.apigateway.UsagePlanKey(`${projectName}-bubble-usage-key`, {
    keyId: bubbleApiKey.id,
    keyType: "API_KEY",
    usagePlanId: usagePlan.id,
});

const externalUsagePlanKey = new aws.apigateway.UsagePlanKey(`${projectName}-external-usage-key`, {
    keyId: externalApiKey.id,
    keyType: "API_KEY",
    usagePlanId: usagePlan.id,
});

// ===== CORS設定（必要に応じて）=====
// bubble.ioからのアクセスを許可
const corsSettings = {
    allowOrigins: environment === "prod" 
        ? ["https://your-app.bubbleapps.io"] // 本番環境では特定のドメインのみ
        : ["*"], // 開発環境では全て許可
    allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allowHeaders: ["Content-Type", "X-Api-Key", "Authorization"],
    maxAge: 86400, // 24時間
};

// ===== 設定情報をSSMパラメータに保存 =====
const apiConfig = new aws.ssm.Parameter(`${projectName}-api-config`, {
    name: `/${projectName}/${environment}/api-gateway/config`,
    type: "String",
    value: pulumi.all([api.id, stage.invokeUrl, bubbleApiKey.id]).apply(
        ([apiId, invokeUrl, keyId]) => JSON.stringify({
            api: {
                id: apiId,
                url: invokeUrl,
                stage: environment,
            },
            endpoints: {
                health: `${invokeUrl}health`,
                api: `${invokeUrl}api`,
            },
            rateLimit: {
                rateLimit: environment === "prod" ? 1000 : 100,
                burstLimit: environment === "prod" ? 2000 : 200,
                dailyQuota: environment === "prod" ? 1000000 : 10000,
            },
            cors: corsSettings,
            deployment: {
                environment: environment,
                lastUpdated: new Date().toISOString(),
            },
        })
    ),
    description: "API Gateway configuration",
    tags: {
        Environment: environment,
    },
});

// APIキー情報を別のパラメータに保存（セキュリティのため）
const apiKeyInfoParam = new aws.ssm.Parameter(`${projectName}-api-keys`, {
    name: `/${projectName}/${environment}/api-gateway/keys`,
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
        Environment: environment,
        Sensitive: "true",
    },
});

// エクスポート
export const apiId = api.id;
export const apiUrl = stage.invokeUrl;
export const apiStage = stage.stageName;
export const apiEndpoints = {
    health: pulumi.interpolate`${stage.invokeUrl}health`,
    api: pulumi.interpolate`${stage.invokeUrl}api`,
};

// APIキー情報（値は出力しない）- 名前を変更
export const apiKeyInfo = {
    bubbleKeyId: bubbleApiKey.id,
    externalKeyId: externalApiKey.id,
    retrieveCommand: pulumi.interpolate`aws ssm get-parameter --name /${projectName}/${environment}/api-gateway/keys --with-decryption --query 'Parameter.Value' --output text | jq .`,
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
