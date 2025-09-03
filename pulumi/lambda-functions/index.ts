/**
 * pulumi/lambda-functions/index.ts
 * 
 * Lambda APIのLambda関数を構築するPulumiスクリプト
 * プライベートリポジトリからソースコードを取得してデプロイ
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import { 
    GitHubRepoCheckout, 
    LambdaPackage, 
    LambdaDeploymentBucket 
} from "@tielec/pulumi-components";

// ========================================
// 環境変数取得
// ========================================
const environment = pulumi.getStack();
const config = new pulumi.Config();

// ========================================
// SSMパラメータ参照（Single Source of Truth）
// ========================================
// プロジェクト名を取得
const projectNameParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/common/project-name`,
});
const projectName = pulumi.output(projectNameParam).apply(p => p.value);

// GitHub認証情報とリポジトリ情報を取得
const githubTokenParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/security/github-token`,
    withDecryption: true,
});
const githubToken = pulumi.output(githubTokenParam).apply(p => p.value);

const repoUrlParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/lambda/source/repository-url`,
    withDecryption: true,
});
const repoUrl = pulumi.output(repoUrlParam).apply(p => p.value);

const repoBranchParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/lambda/source/repository-branch`,
});
const repoBranch = pulumi.output(repoBranchParam).apply(p => p.value);

const versionRetentionParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/lambda/versioning/retain-versions`,
});
const versionRetention = pulumi.output(versionRetentionParam).apply(p => parseInt(p.value) || 3);

// S3デプロイメントバケット情報を取得
const deploymentBucketNameParam = aws.ssm.getParameter({
    name: `/lambda-shipment/${environment}/bucket/name`,
});
const deploymentBucketName = pulumi.output(deploymentBucketNameParam).apply(p => p.value);

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
// GitHubからソースコードをチェックアウトしてパッケージ化
// ========================================
// pulumi.Output型をapplyで解決してリソースを作成
const githubRepoAndPackage = pulumi.all([repoUrl, repoBranch, githubToken, deploymentBucketName, projectName]).apply(
    ([url, branch, token, bucketName, projName]) => {
        // GitHubからLambdaコードを取得
        const githubRepo = new GitHubRepoCheckout("lambda-source", {
            repositoryUrl: url,  // SSMから取得したリポジトリURL
            branch: branch,
            githubToken: token,  // SSMから取得したトークン
            useParameterStore: false,  // 既にSSMから取得しているのでfalse
        });

        // Lambdaパッケージを作成
        const lambdaPackage = new LambdaPackage("lambda-package", {
            sourcePath: githubRepo.outputPath,
            runtime: "nodejs20.x",  // Node.js 20を使用
        });

        // S3デプロイメントバケットを参照
        const deploymentBucket = new LambdaDeploymentBucket("deployment-bucket", {
            bucketName: bucketName,
            useExisting: true,
        });

        // S3にLambdaパッケージをアップロード
        const lambdaCodeObject = deploymentBucket.uploadLambdaPackage(
            projName,
            lambdaPackage.zipPath,
            lambdaPackage.zipHash,
            {
                Environment: environment,
                Project: projName,
                CommitHash: githubRepo.commitHash,
                Branch: branch,
            }
        );

        return {
            githubRepo,
            lambdaPackage,
            deploymentBucket,
            lambdaCodeObject,
        };
    }
);

// 各コンポーネントを抽出
const deploymentBucket = githubRepoAndPackage.apply(r => r.deploymentBucket);
const lambdaCodeObject = githubRepoAndPackage.apply(r => r.lambdaCodeObject);
const githubRepo = githubRepoAndPackage.apply(r => r.githubRepo);

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
    runtime: "nodejs20.x",  // Node.js 20にアップグレード
    architectures: ["arm64"], // AWS Graviton2でコスト削減
    handler: "index.handler",
    role: lambdaRole.arn,
    memorySize: memorySize,
    timeout: timeout,
    
    // S3からコードを取得
    s3Bucket: deploymentBucket.apply(b => b.bucketName),
    s3Key: lambdaCodeObject.apply(o => o.key),
    
    // バージョン管理を有効化
    publish: true,
    
    // 環境変数
    environment: {
        variables: {
            NODE_ENV: environment,
            LOG_LEVEL: environment === "prod" ? "ERROR" : "INFO",
            DEPLOYMENT_VERSION: githubRepo.apply(r => r.commitHash),
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
    
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-main-${environment}`,
        Version: githubRepo.apply(r => r.commitHash),
    },
});

// ========================================
// Lambda バージョン管理とエイリアス
// ========================================
// 環境別のエイリアスを作成
const functionAlias = new aws.lambda.Alias("function-alias", {
    name: environment,  // dev, staging, prod
    functionName: mainFunction.name,
    functionVersion: mainFunction.version,  // 最新の発行済みバージョン
    description: pulumi.interpolate`Alias for ${environment} environment`,
});

// カナリアデプロイメント用のエイリアス（prodのみ）
const canaryAlias = environment === "prod" ? new aws.lambda.Alias("canary-alias", {
    name: "canary",
    functionName: mainFunction.name,
    functionVersion: mainFunction.version,
    description: "Canary deployment alias",
    routingConfig: {
        additionalVersionWeights: {
            // 新バージョンに10%のトラフィックを送る設定例
            // 実際の運用では、段階的に割合を増やす
        },
    },
}) : undefined;

// 古いバージョンのクリーンアップ（保持数を超えたバージョンを削除）
// 注: Pulumiでは直接削除はできないため、別途Lambda関数やスクリプトで実装が必要

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

const functionVersionParam = new aws.ssm.Parameter("function-version", {
    name: pulumi.interpolate`/${projectName}/${environment}/lambda/main-function-version`,
    type: "String",
    value: mainFunction.version,
    description: "Main Lambda function version",
    tags: commonTags,
});

const functionAliasArnParam = new aws.ssm.Parameter("function-alias-arn", {
    name: pulumi.interpolate`/${projectName}/${environment}/lambda/main-function-alias-arn`,
    type: "String",
    value: functionAlias.arn,
    description: "Main Lambda function alias ARN",
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
    functionVersion: mainFunction.version,
    functionAliasArn: functionAlias.arn,
    functionUrl: mainFunction.invokeArn,
    dlqUrl: dlq.url,
    dlqArn: dlq.arn,
    lambdaRoleArn: lambdaRole.arn,
    logGroupName: logGroup.name,
    deploymentInfo: pulumi.all([deploymentBucket, lambdaCodeObject, githubRepo, repoBranch]).apply(
        ([bucket, obj, repo, branch]) => ({
            bucketName: bucket.bucketName,
            objectKey: obj.key,
            commitHash: repo.commitHash,
            branch: branch,
        })
    ),
};

// 簡潔な情報サマリー
export const summary = pulumi.all([memorySize, timeout, versionRetention]).apply(([mem, time, retention]) => ({
    runtime: "nodejs20.x",
    architecture: "arm64",
    memorySize: mem,
    timeout: time,
    environment: environment,
    vpcEnabled: true,
    dlqEnabled: true,
    versioningEnabled: true,
    versionRetention: retention,
    aliasName: environment,
}));
