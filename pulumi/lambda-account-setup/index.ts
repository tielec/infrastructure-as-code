/**
 * pulumi/lambda-account-setup/index.ts
 * 
 * アカウントレベルの設定を行うPulumiスクリプト
 * - API Gateway CloudWatch Logsロール
 * - その他のアカウントレベル設定
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "lambda-api";

// アカウントID取得
const callerIdentity = aws.getCallerIdentity();

// ===== API Gateway CloudWatch Logs Role =====
const apiGatewayCloudWatchRole = new aws.iam.Role("api-gateway-cloudwatch-role", {
    name: "ApiGatewayCloudWatchLogsRole",
    description: "Allows API Gateway to push logs to CloudWatch Logs",
    assumeRolePolicy: JSON.stringify({
        Version: "2012-10-17",
        Statement: [{
            Effect: "Allow",
            Principal: {
                Service: "apigateway.amazonaws.com"
            },
            Action: "sts:AssumeRole"
        }]
    }),
    tags: {
        ManagedBy: "pulumi",
        Project: projectName,
    },
});

// CloudWatch Logs権限をアタッチ
new aws.iam.RolePolicyAttachment("api-gateway-cloudwatch-policy", {
    role: apiGatewayCloudWatchRole.name,
    policyArn: "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs",
});

// API Gatewayアカウント設定
const apiGatewayAccount = new aws.apigateway.Account("api-gateway-account", {
    cloudwatchRoleArn: apiGatewayCloudWatchRole.arn,
});

// ===== Cost and Usage Report (オプション) =====
// コスト監視用のS3バケット
const costReportBucket = new aws.s3.Bucket(`${projectName}-cost-reports`, {
    bucket: pulumi.interpolate`${projectName}-cost-reports-${callerIdentity.accountId}`,
    acl: "private",
    lifecycleRules: [{
        enabled: true,
        expiration: {
            days: 90, // 90日後に削除
        },
    }],
    tags: {
        Purpose: "cost-monitoring",
        Project: projectName,
    },
});

// バケットポリシー（AWS Cost and Usage Report用）
const costReportBucketPolicy = new aws.s3.BucketPolicy("cost-report-bucket-policy", {
    bucket: costReportBucket.id,
    policy: pulumi.all([costReportBucket.arn, callerIdentity.accountId]).apply(([bucketArn, accountId]) => JSON.stringify({
        Version: "2012-10-17",
        Statement: [
            {
                Effect: "Allow",
                Principal: {
                    Service: "billingreports.amazonaws.com"
                },
                Action: [
                    "s3:GetBucketAcl",
                    "s3:GetBucketPolicy"
                ],
                Resource: bucketArn,
                Condition: {
                    StringEquals: {
                        "aws:SourceAccount": accountId
                    }
                }
            },
            {
                Effect: "Allow",
                Principal: {
                    Service: "billingreports.amazonaws.com"
                },
                Action: "s3:PutObject",
                Resource: `${bucketArn}/*`,
                Condition: {
                    StringEquals: {
                        "aws:SourceAccount": accountId
                    }
                }
            }
        ]
    })),
});

// ===== Budget Alerts =====
const devBudget = new aws.budgets.Budget(`${projectName}-dev-budget`, {
    budgetType: "COST",
    limitAmount: "25",
    limitUnit: "USD",
    timeUnit: "MONTHLY",
    name: `${projectName}-dev-monthly`,
    notifications: [{
        comparisonOperator: "GREATER_THAN",
        threshold: 80,
        thresholdType: "PERCENTAGE",
        notificationType: "ACTUAL",
        subscriberEmailAddresses: [config.get("alertEmail") || "dev-team@example.com"],
    }],
});

const stagingBudget = new aws.budgets.Budget(`${projectName}-staging-budget`, {
    budgetType: "COST",
    limitAmount: "55",
    limitUnit: "USD",
    timeUnit: "MONTHLY",
    name: `${projectName}-staging-monthly`,
    notifications: [{
        comparisonOperator: "GREATER_THAN",
        threshold: 80,
        thresholdType: "PERCENTAGE",
        notificationType: "ACTUAL",
        subscriberEmailAddresses: [config.get("alertEmail") || "dev-team@example.com"],
    }],
});

const prodBudget = new aws.budgets.Budget(`${projectName}-prod-budget`, {
    budgetType: "COST",
    limitAmount: "160",
    limitUnit: "USD",
    timeUnit: "MONTHLY",
    name: `${projectName}-prod-monthly`,
    notifications: [
        {
            comparisonOperator: "GREATER_THAN",
            threshold: 80,
            thresholdType: "PERCENTAGE",
            notificationType: "ACTUAL",
            subscriberEmailAddresses: [config.get("alertEmail") || "ops-team@example.com"],
        },
        {
            comparisonOperator: "GREATER_THAN",
            threshold: 100,
            thresholdType: "PERCENTAGE",
            notificationType: "ACTUAL",
            subscriberEmailAddresses: [config.get("criticalAlertEmail") || "cto@example.com"],
        },
    ],
});

// ===== Parameter Store に設定を保存 =====
const accountConfig = new aws.ssm.Parameter(`${projectName}-account-config`, {
    name: `/${projectName}/account/config`,
    type: "String",
    value: pulumi.all([apiGatewayCloudWatchRole.arn, costReportBucket.bucket]).apply(
        ([roleArn, bucketName]) => JSON.stringify({
            apiGateway: {
                cloudWatchLogsRoleArn: roleArn,
                configured: true,
            },
            costMonitoring: {
                reportsBucket: bucketName,
                budgets: {
                    dev: "25 USD",
                    staging: "55 USD",
                    prod: "160 USD",
                },
            },
            setupDate: new Date().toISOString(),
        })
    ),
    description: "Account-level configuration for Lambda API",
    tags: {
        Project: projectName,
    },
});

// エクスポート
export const apiGatewayCloudWatchRoleArn = apiGatewayCloudWatchRole.arn;
export const costReportsBucket = costReportBucket.bucket;
export const accountConfigParameter = accountConfig.name;

export const summary = {
    apiGatewayLogging: "Configured",
    costMonitoring: "Enabled",
    budgetAlerts: 3,
};
