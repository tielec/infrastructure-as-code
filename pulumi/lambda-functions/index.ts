/**
 * pulumi/lambda-functions/index.ts
 * 
 * Lambda APIのLambda関数を構築するPulumiスクリプト
 * 最小構成 - 1つのメインLambda関数のみ
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
const memorySizeParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/lambda/memory-size`,
});
const memorySize = pulumi.output(memorySizeParam).apply(p => parseInt(p.value) || 256);

const timeoutParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/lambda/timeout`,
});
const timeout = pulumi.output(timeoutParam).apply(p => parseInt(p.value) || 30);

const logRetentionDaysParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/lambda/log-retention-days`,
});
const logRetentionDays = pulumi.output(logRetentionDaysParam).apply(p => {
    const days = parseInt(p.value);
    if (!isNaN(days)) return days;
    // デフォルト値：dev=3日、staging=7日、prod=14日
    return environment === "dev" ? 3 : environment === "staging" ? 7 : 14;
});

// ネットワーク情報を取得
const privateSubnetAIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/subnets/private-a-id`,
});
const privateSubnetAId = pulumi.output(privateSubnetAIdParam).apply(p => p.value);

const privateSubnetBIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/subnets/private-b-id`,
});
const privateSubnetBId = pulumi.output(privateSubnetBIdParam).apply(p => p.value);

const lambdaSecurityGroupIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/security/lambda-sg-id`,
});
const lambdaSecurityGroupId = pulumi.output(lambdaSecurityGroupIdParam).apply(p => p.value);

// サブネットIDの配列
const privateSubnetIds = pulumi.all([privateSubnetAId, privateSubnetBId]);

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
// リソース定義
// ========================================
// Dead Letter Queue (DLQ) - エラー処理用
const dlq = new aws.sqs.Queue("dlq", {
    name: pulumi.interpolate`${projectName}-dlq-${environment}`,
    messageRetentionSeconds: 14 * 24 * 60 * 60, // 14日間保持
    visibilityTimeoutSeconds: timeout.apply(t => t * 6), // Lambdaタイムアウトの6倍
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-dlq-${environment}`,
    },
});

// IAMロール - Lambda実行権限
const lambdaRole = new aws.iam.Role("lambda-role", {
    assumeRolePolicy: JSON.stringify({
        Version: "2012-10-17",
        Statement: [{
            Action: "sts:AssumeRole",
            Effect: "Allow",
            Principal: {
                Service: "lambda.amazonaws.com",
            },
        }],
    }),
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-lambda-role-${environment}`,
    },
});

// VPC内でLambdaを実行するための権限
new aws.iam.RolePolicyAttachment("vpc-access-policy", {
    role: lambdaRole.name,
    policyArn: "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole",
});

// 基本的な権限（CloudWatch Logs、DLQ、Secrets Manager）
const lambdaPolicy = new aws.iam.RolePolicy("lambda-policy", {
    role: lambdaRole.id,
    policy: pulumi.all([dlq.arn, projectName]).apply(([dlqArn, proj]) => JSON.stringify({
        Version: "2012-10-17",
        Statement: [
            {
                // CloudWatch Logsへの書き込み
                Effect: "Allow",
                Action: [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                Resource: "*",
            },
            {
                // DLQへのメッセージ送信
                Effect: "Allow",
                Action: ["sqs:SendMessage"],
                Resource: dlqArn,
            },
            {
                // Secrets Manager（APIキーなどの機密情報用）
                Effect: "Allow",
                Action: ["secretsmanager:GetSecretValue"],
                Resource: `arn:aws:secretsmanager:*:*:secret:${proj}/*`,
            },
        ],
    })),
});

// ========================================
// Lambda関数定義
// ========================================
// メインのLambda関数
const mainFunction = new aws.lambda.Function("main-function", {
    name: pulumi.interpolate`${projectName}-main-${environment}`,
    description: "Main API handler for bubble.io integration",
    runtime: "nodejs18.x",
    architectures: ["arm64"], // AWS Graviton2でコスト削減
    handler: "index.handler",
    role: lambdaRole.arn,
    memorySize: memorySize,
    timeout: timeout,
    
    // 環境変数
    environment: {
        variables: {
            NODE_ENV: environment,
            LOG_LEVEL: environment === "prod" ? "ERROR" : "INFO",
            // 将来の拡張用: DB接続情報、外部APIエンドポイントなど
        },
    },
    
    // VPC設定（プライベートサブネットで実行）
    vpcConfig: {
        subnetIds: privateSubnetIds,
        securityGroupIds: [lambdaSecurityGroupId],
    },
    
    // エラー時はDLQに送信
    deadLetterConfig: {
        targetArn: dlq.arn,
    },
    
    // プレースホルダーコード（実際のコードは別途デプロイ）
    code: new pulumi.asset.AssetArchive({
        "index.js": new pulumi.asset.StringAsset(`
// Lambda関数のプレースホルダー
exports.handler = async (event, context) => {
    console.log('Event:', JSON.stringify(event));
    
    try {
        // ここに実際のビジネスロジックを実装
        // 例: bubble.ioからのWebhook処理、外部API呼び出しなど
        
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: 'Lambda API is running',
                environment: process.env.NODE_ENV,
                timestamp: new Date().toISOString(),
            }),
        };
    } catch (error) {
        console.error('Error:', error);
        
        // エラーはDLQに自動的に送信される
        throw error;
    }
};
        `),
    }),
    
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-main-${environment}`,
    },
});

// ========================================
// CloudWatch Logs設定
// ========================================
const logGroup = new aws.cloudwatch.LogGroup("log-group", {
    name: pulumi.interpolate`/aws/lambda/${mainFunction.name}`,
    retentionInDays: logRetentionDays,
    tags: commonTags,
});

// ========================================
// SSMパラメータへの保存
// ========================================
// 他のスタックが参照する値をSSMに保存
const functionArnParam = new aws.ssm.Parameter("function-arn", {
    name: pulumi.interpolate`/${projectName}/${environment}/lambda/main-function-arn`,
    type: "String",
    value: mainFunction.arn,
    description: "Main Lambda function ARN",
    tags: commonTags,
});

const functionNameParam = new aws.ssm.Parameter("function-name", {
    name: pulumi.interpolate`/${projectName}/${environment}/lambda/main-function-name`,
    type: "String",
    value: mainFunction.name,
    description: "Main Lambda function name",
    tags: commonTags,
});

const dlqArnParam = new aws.ssm.Parameter("dlq-arn", {
    name: pulumi.interpolate`/${projectName}/${environment}/lambda/dlq-arn`,
    type: "String",
    value: dlq.arn,
    description: "Dead Letter Queue ARN",
    tags: commonTags,
});

// ========================================
// エクスポート（表示用のみ）
// ========================================
// エクスポートは表示・確認用のみ
// 他のスタックはSSMパラメータから値を取得すること
export const outputs = {
    functionName: mainFunction.name,
    functionArn: mainFunction.arn,
    functionUrl: mainFunction.invokeArn,
    dlqUrl: dlq.url,
    dlqArn: dlq.arn,
    lambdaRoleArn: lambdaRole.arn,
    logGroupName: logGroup.name,
};

// 簡潔な情報サマリー
export const summary = pulumi.all([memorySize, timeout]).apply(([mem, time]) => ({
    runtime: "nodejs18.x",
    architecture: "arm64",
    memorySize: mem,
    timeout: time,
    environment: environment,
    vpcEnabled: true,
    dlqEnabled: true,
}));
