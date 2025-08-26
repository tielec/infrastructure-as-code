/**
 * pulumi/lambda-websocket/index.ts
 * 
 * Lambda API WebSocket APIを構築するPulumiスクリプト
 * 基本的なWebSocket接続管理
 */

// TODO: config はSSMパラメータから取得するように変更予定

import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "lambda-api";
const environment = pulumi.getStack();

// スタック参照
const functionsStackName = config.get("functionsStackName") || "lambda-functions";
const functionsStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${functionsStackName}/${environment}`);
const lambdaFunctionArn = functionsStack.getOutput("functionArn");
const lambdaFunctionName = functionsStack.getOutput("functionName");

// WebSocket設定（設計書に基づく）
interface WebSocketConfig {
    projectName: string;
    routeSelectionExpression: string;
    maxConnections: number;
    idleTimeout: number;
}

const wsConfig: WebSocketConfig = {
    projectName: projectName,
    routeSelectionExpression: config.get("routeSelectionExpression") || "$request.body.action",
    maxConnections: config.getNumber("maxConnections") || 10000,
    idleTimeout: config.getNumber("idleTimeout") || 600, // 10分
};

// ===== WebSocket API =====
const websocketApi = new aws.apigatewayv2.Api(`${projectName}-websocket-api`, {
    name: `${projectName}-websocket-api-${environment}`,
    protocolType: "WEBSOCKET",
    routeSelectionExpression: wsConfig.routeSelectionExpression,
    description: `WebSocket API for ${projectName} - ${environment}`,
    tags: {
        Name: `${projectName}-websocket-api-${environment}`,
        Environment: environment,
    },
});

// ===== WebSocket用Lambda関数 =====
// 既存のLambda関数を使用し、将来的に専用関数に分離可能

// Lambda実行権限（WebSocket用）
const websocketLambdaPermission = new aws.lambda.Permission(`${projectName}-websocket-lambda-permission`, {
    action: "lambda:InvokeFunction",
    function: lambdaFunctionName,
    principal: "apigateway.amazonaws.com",
    sourceArn: pulumi.interpolate`${websocketApi.executionArn}/*/*`,
});

// ===== Lambda統合 =====
const lambdaIntegration = new aws.apigatewayv2.Integration(`${projectName}-websocket-integration`, {
    apiId: websocketApi.id,
    integrationType: "AWS_PROXY",
    integrationUri: pulumi.interpolate`arn:aws:apigateway:${aws.config.region}:lambda:path/2015-03-31/functions/${lambdaFunctionArn}/invocations`,
    integrationMethod: "POST",
    payloadFormatVersion: "1.0",
});

// ===== ルート設定 =====
// $connect ルート（接続時）
const connectRoute = new aws.apigatewayv2.Route(`${projectName}-connect-route`, {
    apiId: websocketApi.id,
    routeKey: "$connect",
    target: pulumi.interpolate`integrations/${lambdaIntegration.id}`,
    // 接続時の認証（オプション）
    authorizationType: "NONE", // 現在は認証なし、将来的にカスタムオーソライザー追加可能
});

// $disconnect ルート（切断時）
const disconnectRoute = new aws.apigatewayv2.Route(`${projectName}-disconnect-route`, {
    apiId: websocketApi.id,
    routeKey: "$disconnect",
    target: pulumi.interpolate`integrations/${lambdaIntegration.id}`,
});

// $default ルート（メッセージ受信時）
const defaultRoute = new aws.apigatewayv2.Route(`${projectName}-default-route`, {
    apiId: websocketApi.id,
    routeKey: "$default",
    target: pulumi.interpolate`integrations/${lambdaIntegration.id}`,
});

// カスタムルート例（action ベースのルーティング）
const messageRoute = new aws.apigatewayv2.Route(`${projectName}-message-route`, {
    apiId: websocketApi.id,
    routeKey: "message", // { "action": "message", ... } に対応
    target: pulumi.interpolate`integrations/${lambdaIntegration.id}`,
});

const broadcastRoute = new aws.apigatewayv2.Route(`${projectName}-broadcast-route`, {
    apiId: websocketApi.id,
    routeKey: "broadcast", // { "action": "broadcast", ... } に対応
    target: pulumi.interpolate`integrations/${lambdaIntegration.id}`,
});

// ===== ステージとデプロイメント =====
const deployment = new aws.apigatewayv2.Deployment(`${projectName}-websocket-deployment`, {
    apiId: websocketApi.id,
    description: `Deployment for ${environment}`,
    // 明示的な依存関係
    dependsOn: [
        connectRoute,
        disconnectRoute,
        defaultRoute,
        messageRoute,
        broadcastRoute,
    ],
});

const stage = new aws.apigatewayv2.Stage(`${projectName}-websocket-stage`, {
    apiId: websocketApi.id,
    name: environment,
    deploymentId: deployment.id,
    description: `WebSocket stage for ${environment}`,
    
    // ログ設定
    accessLogSettings: {
        destinationArn: pulumi.interpolate`arn:aws:logs:${aws.config.region}:${aws.getCallerIdentity().then(i => i.accountId)}:log-group:/aws/apigateway/${projectName}-websocket`,
        format: JSON.stringify({
            requestId: "$context.requestId",
            ip: "$context.identity.sourceIp",
            requestTime: "$context.requestTime",
            routeKey: "$context.routeKey",
            status: "$context.status",
            error: "$context.error.message",
            connectionId: "$context.connectionId",
            eventType: "$context.eventType",
        }),
    },
    
    // スロットリング設定
    defaultRouteSettings: {
        throttlingRateLimit: environment === "prod" ? 1000 : 100,
        throttlingBurstLimit: environment === "prod" ? 2000 : 200,
    },
    
    tags: {
        Environment: environment,
    },
});

// CloudWatch Logsグループ
const websocketLogGroup = new aws.cloudwatch.LogGroup(`${projectName}-websocket-logs`, {
    name: `/aws/apigateway/${projectName}-websocket`,
    retentionInDays: environment === "dev" ? 3 : 7,
    tags: {
        Environment: environment,
    },
});

// ===== 接続管理用のリソース（簡易版）=====
// 接続情報をLambda関数内のメモリで管理
// 将来的にDynamoDBに移行可能

// WebSocket Management API用のIAMポリシー
// Lambda関数がWebSocket接続にメッセージを送信するために必要
const websocketManagementPolicy = new aws.iam.Policy(`${projectName}-websocket-management-policy`, {
    description: "Policy for Lambda to manage WebSocket connections",
    policy: pulumi.all([websocketApi.id, stage.name]).apply(([apiId, stageName]) => JSON.stringify({
        Version: "2012-10-17",
        Statement: [{
            Effect: "Allow",
            Action: [
                "execute-api:ManageConnections",
                "execute-api:Invoke",
            ],
            Resource: [
                `arn:aws:execute-api:${aws.config.region}:*:${apiId}/${stageName}/POST/@connections/*`,
                `arn:aws:execute-api:${aws.config.region}:*:${apiId}/${stageName}/DELETE/@connections/*`,
                `arn:aws:execute-api:${aws.config.region}:*:${apiId}/${stageName}/GET/@connections/*`,
            ],
        }],
    })),
});

// 既存のLambdaロールにWebSocket管理ポリシーをアタッチ
const lambdaRoleArn = functionsStack.getOutput("lambdaRoleArn");
const lambdaRoleName = lambdaRoleArn.apply(arn => arn.split("/").pop()!);

const websocketPolicyAttachment = new aws.iam.RolePolicyAttachment(`${projectName}-websocket-policy-attachment`, {
    role: lambdaRoleName,
    policyArn: websocketManagementPolicy.arn,
});

// ===== メトリクスとアラーム =====
// 同時接続数のアラーム
const connectionCountAlarm = new aws.cloudwatch.MetricAlarm(`${projectName}-websocket-connections-alarm`, {
    alarmName: `${projectName}-websocket-connections-${environment}`,
    alarmDescription: "Alert when WebSocket connections are high",
    metricName: "Count",
    namespace: "AWS/ApiGateway",
    statistic: "Maximum",
    period: 300,
    evaluationPeriods: 2,
    threshold: environment === "prod" ? 8000 : 800, // 最大接続数の80%
    comparisonOperator: "GreaterThanThreshold",
    dimensions: {
        ApiName: websocketApi.name,
        Stage: stage.name,
    },
    treatMissingData: "notBreaching",
    tags: {
        Environment: environment,
    },
});

// エラー率のアラーム
const errorRateAlarm = new aws.cloudwatch.MetricAlarm(`${projectName}-websocket-errors-alarm`, {
    alarmName: `${projectName}-websocket-errors-${environment}`,
    alarmDescription: "Alert when WebSocket error rate is high",
    metricName: "4xx",
    namespace: "AWS/ApiGateway",
    statistic: "Sum",
    period: 300,
    evaluationPeriods: 2,
    threshold: 100,
    comparisonOperator: "GreaterThanThreshold",
    dimensions: {
        ApiName: websocketApi.name,
        Stage: stage.name,
    },
    treatMissingData: "notBreaching",
    tags: {
        Environment: environment,
    },
});

// ===== 設定情報をSSMパラメータに保存 =====
const websocketConfig = new aws.ssm.Parameter(`${projectName}-websocket-config`, {
    name: `/${projectName}/${environment}/websocket/config`,
    type: "String",
    value: pulumi.all([websocketApi.id, stage.invokeUrl]).apply(
        ([apiId, wsUrl]) => JSON.stringify({
            api: {
                id: apiId,
                url: wsUrl,
                stage: environment,
            },
            routes: {
                connect: "$connect",
                disconnect: "$disconnect",
                default: "$default",
                custom: ["message", "broadcast"],
            },
            limits: {
                maxConnections: wsConfig.maxConnections,
                idleTimeout: `${wsConfig.idleTimeout} seconds`,
                rateLimit: environment === "prod" ? "1000 req/s" : "100 req/s",
            },
            management: {
                sendMessage: `POST ${wsUrl}/@connections/{connectionId}`,
                disconnect: `DELETE ${wsUrl}/@connections/{connectionId}`,
                getConnection: `GET ${wsUrl}/@connections/{connectionId}`,
            },
            deployment: {
                environment: environment,
                lastUpdated: new Date().toISOString(),
            },
        })
    ),
    description: "WebSocket API configuration",
    tags: {
        Environment: environment,
    },
});

// ===== クライアント接続例 =====
const clientExampleParam = new aws.ssm.Parameter(`${projectName}-websocket-example`, {
    name: `/${projectName}/${environment}/websocket/example`,
    type: "String",
    value: pulumi.all([stage.invokeUrl]).apply(([wsUrl]) => JSON.stringify({
        javascript: `
// WebSocket接続例
const ws = new WebSocket('${wsUrl}');

ws.onopen = () => {
    console.log('Connected to WebSocket');
    
    // メッセージ送信
    ws.send(JSON.stringify({
        action: 'message',
        data: 'Hello from client'
    }));
};

ws.onmessage = (event) => {
    console.log('Received:', event.data);
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

ws.onclose = () => {
    console.log('Disconnected from WebSocket');
};
`,
        curl: `
# WebSocket接続テスト（wscat使用）
npm install -g wscat
wscat -c ${wsUrl}

# 接続後、以下のようなメッセージを送信
{"action": "message", "data": "Hello from wscat"}
`,
    })),
    description: "WebSocket client connection examples",
    tags: {
        Environment: environment,
    },
});

// エクスポート
export const websocketApiId = websocketApi.id;
export const websocketApiUrl = stage.invokeUrl;
export const websocketApiEndpoint = websocketApi.apiEndpoint;
export const stageName = stage.name;

// 管理用エンドポイント
export const managementEndpoints = {
    sendMessage: pulumi.interpolate`POST ${stage.invokeUrl}/@connections/{connectionId}`,
    disconnect: pulumi.interpolate`DELETE ${stage.invokeUrl}/@connections/{connectionId}`,
    getConnection: pulumi.interpolate`GET ${stage.invokeUrl}/@connections/{connectionId}`,
};

// 接続情報
export const connectionInfo = {
    maxConnections: wsConfig.maxConnections,
    idleTimeout: `${wsConfig.idleTimeout} seconds`,
    routeSelectionExpression: wsConfig.routeSelectionExpression,
};

// サマリー
export const summary = {
    protocol: "WebSocket",
    authentication: "None",
    routes: 5,
    maxConnections: wsConfig.maxConnections,
    idleTimeout: wsConfig.idleTimeout,
    rateLimit: environment === "prod" ? "1000 req/s" : "100 req/s",
    monitoring: {
        logs: "CloudWatch Logs",
        alarms: 2,
    },
    environment: environment,
};
