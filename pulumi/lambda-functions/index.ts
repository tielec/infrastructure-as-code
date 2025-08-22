/**
 * pulumi/lambda-functions/index.ts
 * 
 * Lambda APIのLambda関数を構築するPulumiスクリプト
 * Phase 1: 最小構成 - 1つのメインLambda関数のみ
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

// Lambda関数の設定をSSMから取得
const memorySizeParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/lambda/memory-size`,
});
const timeoutParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/lambda/timeout`,
});
const logRetentionDaysParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/lambda/log-retention-days`,
});

const memorySize = pulumi.output(memorySizeParam).apply(p => parseInt(p.value) || 256);
const timeout = pulumi.output(timeoutParam).apply(p => parseInt(p.value) || 30);
const logRetentionDays = pulumi.output(logRetentionDaysParam).apply(p => parseInt(p.value) || (environment === "dev" ? 3 : environment === "staging" ? 7 : 14));

// スタック参照名は固定（コンベンションとして）
const networkStackName = "lambda-network";
const securityStackName = "lambda-security";

// 既存のスタックから値を取得
const networkStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${networkStackName}/${environment}`);
const securityStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${securityStackName}/${environment}`);

const privateSubnetIds = networkStack.getOutput("privateSubnetIds");
const lambdaSecurityGroupId = securityStack.getOutput("lambdaSecurityGroupId");

// ===== Dead Letter Queue (DLQ) - エラー処理用 =====
const dlq = new aws.sqs.Queue("lambda-api-dlq", {
    name: pulumi.interpolate`${projectName}-dlq-${environment}`,
    messageRetentionSeconds: 14 * 24 * 60 * 60, // 14日間保持
    visibilityTimeoutSeconds: timeout * 6, // Lambdaタイムアウトの6倍
    tags: {
        Name: pulumi.interpolate`${projectName}-dlq-${environment}`,
        Environment: environment,
    },
});

// ===== IAMロール - Lambda実行権限 =====
const lambdaRole = new aws.iam.Role("lambda-api-lambda-role", {
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
        Name: pulumi.interpolate`${projectName}-lambda-role-${environment}`,
        Environment: environment,
    },
});

// VPC内でLambdaを実行するための権限
new aws.iam.RolePolicyAttachment("lambda-api-vpc-access", {
    role: lambdaRole.name,
    policyArn: "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole",
});

// 基本的な権限（CloudWatch Logs、DLQ、Secrets Manager）
const lambdaPolicy = new aws.iam.RolePolicy("lambda-api-lambda-policy", {
    role: lambdaRole.id,
    policy: pulumi.all([dlq.arn]).apply(([dlqArn]) => JSON.stringify({
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
                Resource: pulumi.interpolate`arn:aws:secretsmanager:*:*:secret:${projectName}/*`,
            },
        ],
    })),
});

// ===== メインのLambda関数 =====
const mainFunction = new aws.lambda.Function("lambda-api-main", {
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
        Name: `${projectName}-main-${environment}`,
        Environment: environment,
    },
});

// ===== CloudWatch Logs グループ =====
const logGroup = new aws.cloudwatch.LogGroup(`${projectName}-logs`, {
    name: pulumi.interpolate`/aws/lambda/${mainFunction.name}`,
    retentionInDays: logRetentionDays,
    tags: {
        Environment: environment,
    },
});

// ===== 設定情報をSSMパラメータに保存 =====
const functionConfig = new aws.ssm.Parameter(`${projectName}-function-config`, {
    name: `/${projectName}/${environment}/lambda/config`,
    type: "String",
    value: pulumi.all([mainFunction.name, mainFunction.arn, dlq.url]).apply(
        ([name, arn, dlqUrl]) => JSON.stringify({
            function: {
                name: name,
                arn: arn,
                runtime: "nodejs18.x",
                architecture: "arm64",
                memorySize: memorySize,
                timeout: timeout,
            },
            dlq: {
                url: dlqUrl,
            },
            deployment: {
                environment: environment,
                lastUpdated: new Date().toISOString(),
            },
            // 将来の拡張ポイント
            future: {
                additionalFunctions: "Add more functions as needed",
                database: "Add RDS/DynamoDB configuration in Phase 2",
                layers: "Add shared libraries as Lambda Layers",
            },
        })
    ),
    description: "Lambda function configuration",
    tags: {
        Environment: environment,
    },
});

// エクスポート
export const functionName = mainFunction.name;
export const functionArn = mainFunction.arn;
export const functionUrl = mainFunction.invokeArn;
export const dlqUrl = dlq.url;
export const dlqArn = dlq.arn;
export const lambdaRoleArn = lambdaRole.arn;
export const logGroupName = logGroup.name;

// 簡潔な情報サマリー
export const summary = {
    runtime: "nodejs18.x",
    architecture: "arm64",
    memorySize: memorySize,
    timeout: timeout,
    environment: environment,
    vpcEnabled: true,
    dlqEnabled: true,
};
