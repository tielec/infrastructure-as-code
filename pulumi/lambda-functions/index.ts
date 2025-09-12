/**
 * pulumi/lambda-functions/index.ts
 * 
 * Lambda関数を構築するPulumiスクリプト
 * わかりやすさを重視したシンプルな実装
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import { 
    GitHubRepoCheckout, 
    LambdaPackage, 
    LambdaDeploymentBucket 
} from "@tielec/pulumi-components";
import { createLambdaFunction } from "./components/lambda-factory";

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

// GitHub設定
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

// Lambda設定
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
const logRetentionDays = pulumi.output(logRetentionDaysParam).apply(p => parseInt(p.value) || 7);


// デプロイメントバケット
const deploymentBucketNameParam = aws.ssm.getParameter({
    name: `/lambda-shipment/${environment}/bucket/name`,
});
const deploymentBucketName = pulumi.output(deploymentBucketNameParam).apply(p => p.value);

// ========================================
// 3. GitHubからソースコードを取得してパッケージ化
// ========================================
// Pulumi Outputを解決してから処理
const githubRepoAndPackage = pulumi.all([repoUrl, repoBranch, githubToken, deploymentBucketName, projectName]).apply(
    ([url, branch, token, bucketName, projName]) => {
        // GitHubからソースコードを取得
        const githubRepo = new GitHubRepoCheckout("lambda-source", {
            repositoryUrl: url,
            branch: branch,
            githubToken: token,
            useParameterStore: false,
        });
        
        // Lambdaパッケージを作成
        const lambdaPackage = new LambdaPackage("lambda-package", {
            sourcePath: githubRepo.outputPath,
            runtime: "nodejs20.x",
        });
        
        // S3バケットにアップロード
        const deploymentBucket = new LambdaDeploymentBucket("deployment-bucket", {
            bucketName: bucketName,
            useExisting: true,
        });
        
        const lambdaCodeObject = deploymentBucket.uploadLambdaPackage(
            projName,
            lambdaPackage.zipPath,
            lambdaPackage.zipHash,
            {
                environment: environment,
                project: projName,
                commithash: githubRepo.commitHash,
                branch: branch,
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

// 各リソースを抽出
const deploymentBucket = githubRepoAndPackage.apply(r => r.deploymentBucket);
const lambdaCodeObject = githubRepoAndPackage.apply(r => r.lambdaCodeObject);
const githubRepo = githubRepoAndPackage.apply(r => r.githubRepo);

// ========================================
// 4. DLQ（Dead Letter Queue）を作成
// ========================================
const dlq = new aws.sqs.Queue("dlq", {
    name: pulumi.interpolate`${projectName}-dlq-${environment}`,
    messageRetentionSeconds: 14 * 24 * 60 * 60, // 14日間保持
    tags: commonTags,
});

// ========================================
// 5. IAMロールを作成
// ========================================
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
    tags: commonTags,
});

// その他の権限
new aws.iam.RolePolicy("lambda-policy", {
    role: lambdaRole.id,
    policy: pulumi.all([dlq.arn, projectName]).apply(([dlqArn, proj]) => JSON.stringify({
        Version: "2012-10-17",
        Statement: [
            {
                Effect: "Allow",
                Action: [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                Resource: "*",
            },
            {
                Effect: "Allow",
                Action: ["sqs:SendMessage"],
                Resource: dlqArn,
            },
            {
                Effect: "Allow",
                Action: ["secretsmanager:GetSecretValue"],
                Resource: `arn:aws:secretsmanager:*:*:secret:${proj}/*`,
            },
            {
                Effect: "Allow",
                Action: [
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                    "ssm:GetParametersByPath",
                ],
                Resource: `arn:aws:ssm:*:*:parameter/lambda-api/${environment}/*`,
            },
        ],
    })),
});

// ========================================
// 6. Lambda関数を作成（シンプルなヘルパー関数を使用）
// ========================================
const mainLambda = createLambdaFunction(
    "main",
    projectName,
    environment,
    {
        // 必須パラメータ
        role: lambdaRole,
        s3Bucket: deploymentBucket.apply(b => b.bucketName),
        s3Key: lambdaCodeObject.apply(o => o.key),
        dlqArn: dlq.arn,
        
        // オプションパラメータ
        description: "Main API handler for bubble.io integration",
        handler: "dist/index.handler",
        runtime: "nodejs20.x",
        memorySize: memorySize,
        timeout: timeout,
        environmentVariables: {
            NODE_ENV: environment,
            LOG_LEVEL: environment === "prod" ? "ERROR" : "INFO",
            DEPLOYMENT_VERSION: githubRepo.apply(r => r.commitHash),
        },
        logRetentionDays: logRetentionDays,
        tags: commonTags,
    }
);

// ========================================
// 7. エクスポート（確認用）
// ========================================
export const outputs = {
    // Lambda関数情報
    functionName: mainLambda.function.name,
    functionArn: mainLambda.function.arn,
    functionVersion: mainLambda.function.version,
    aliasArn: mainLambda.alias.arn,
    
    // DLQ情報
    dlqUrl: dlq.url,
    dlqArn: dlq.arn,
    
    // ロール情報
    lambdaRoleArn: lambdaRole.arn,
    
    // ログ情報
    logGroupName: mainLambda.logGroup.name,
    
    // デプロイメント情報
    deploymentBucket: deploymentBucket.apply(b => b.bucketName),
    codeObjectKey: lambdaCodeObject.apply(o => o.key),
    commitHash: githubRepo.apply(r => r.commitHash),
};

