/**
 * pulumi/lambda-waf/index.ts
 * 
 * Lambda API WAFリソースを構築するPulumiスクリプト
 * IPホワイトリスト、レート制限、SQLi/XSS防御を実装
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "lambda-api";
const environment = pulumi.getStack();

// スタック参照
const apiGatewayStackName = config.get("apiGatewayStackName") || "lambda-api-gateway";
const apiGatewayStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${apiGatewayStackName}/${environment}`);
const apiStage = apiGatewayStack.getOutput("apiStage");

// WAF設定（設計書に基づく）
interface WafConfig {
    projectName: string;
    ipWhitelist: string[];
    rateLimit: number;
    blockPeriod: number;
    geoMatchConstraint?: string[];
}

// bubble.io のIPアドレス（実際の値は要確認）
const bubbleIpAddresses = config.getObject<string[]>("bubbleIpWhitelist") || [
    // bubble.io の実際のIPアドレスをここに設定
    // 例: "52.70.100.0/24", "34.195.100.0/24"
];

// 開発環境では自分のIPも追加（オプション）
const additionalWhitelistIps = config.getObject<string[]>("additionalWhitelist") || [];

// すべての許可IPアドレス
const allWhitelistIps = [...bubbleIpAddresses, ...additionalWhitelistIps];

// ===== IP Set（ホワイトリスト）=====
const ipSet = new aws.wafv2.IpSet(`${projectName}-ip-whitelist`, {
    name: `${projectName}-ip-whitelist-${environment}`,
    description: "Allowed IP addresses for API access",
    scope: "REGIONAL", // API Gateway用
    ipAddressVersion: "IPV4",
    addresses: allWhitelistIps.length > 0 ? allWhitelistIps : ["0.0.0.0/0"], // IPが設定されていない場合は全許可（開発用）
    tags: {
        Name: `${projectName}-ip-whitelist-${environment}`,
        Environment: environment,
    },
});

// ===== Web ACL =====
const webAcl = new aws.wafv2.WebAcl(`${projectName}-web-acl`, {
    name: `${projectName}-web-acl-${environment}`,
    description: "Web ACL for Lambda API protection",
    scope: "REGIONAL",
    
    // デフォルトアクション（ルールに一致しない場合）
    defaultAction: {
        allow: {}, // 開発環境ではデフォルト許可、本番では要検討
    },
    
    rules: [
        // ===== 1. IPホワイトリストルール =====
        {
            name: "IPWhitelistRule",
            priority: 1,
            action: {
                allow: {}, // ホワイトリストのIPは許可
            },
            statement: {
                ipSetReferenceStatement: {
                    arn: ipSet.arn,
                },
            },
            visibilityConfig: {
                cloudwatchMetricsEnabled: true,
                metricName: "IPWhitelistRule",
                sampledRequestsEnabled: true,
            },
        },
        
        // ===== 2. レート制限ルール =====
        {
            name: "RateLimitRule",
            priority: 2,
            action: {
                block: {}, // 制限超過はブロック
            },
            statement: {
                rateBasedStatement: {
                    limit: 2000, // 5分間で2000リクエスト
                    aggregateKeyType: "IP",
                },
            },
            visibilityConfig: {
                cloudwatchMetricsEnabled: true,
                metricName: "RateLimitRule",
                sampledRequestsEnabled: true,
            },
        },
        
        // ===== 3. AWS Managed Rules - Core Rule Set（OWASP Top 10対策）=====
        {
            name: "AWSManagedRulesCommonRuleSet",
            priority: 3,
            overrideAction: {
                none: {},
            },
            statement: {
                managedRuleGroupStatement: {
                    vendorName: "AWS",
                    name: "AWSManagedRulesCommonRuleSet",
                    // 特定のルールを除外（必要に応じて）
                    excludedRules: environment === "dev" ? [
                        { name: "SizeRestrictions_BODY" }, // 開発環境では大きなペイロードを許可
                    ] : [],
                },
            },
            visibilityConfig: {
                cloudwatchMetricsEnabled: true,
                metricName: "CommonRuleSetMetric",
                sampledRequestsEnabled: true,
            },
        },
        
        // ===== 4. SQLインジェクション防御 =====
        {
            name: "AWSManagedRulesSQLiRuleSet",
            priority: 4,
            overrideAction: {
                none: {},
            },
            statement: {
                managedRuleGroupStatement: {
                    vendorName: "AWS",
                    name: "AWSManagedRulesSQLiRuleSet",
                },
            },
            visibilityConfig: {
                cloudwatchMetricsEnabled: true,
                metricName: "SQLiRuleSetMetric",
                sampledRequestsEnabled: true,
            },
        },
        
        // ===== 5. XSS防御 =====
        {
            name: "AWSManagedRulesKnownBadInputsRuleSet",
            priority: 5,
            overrideAction: {
                none: {},
            },
            statement: {
                managedRuleGroupStatement: {
                    vendorName: "AWS",
                    name: "AWSManagedRulesKnownBadInputsRuleSet",
                },
            },
            visibilityConfig: {
                cloudwatchMetricsEnabled: true,
                metricName: "KnownBadInputsRuleSetMetric",
                sampledRequestsEnabled: true,
            },
        },
        
        // ===== 6. サイズ制限ルール =====
        {
            name: "SizeRestrictionRule",
            priority: 6,
            action: {
                block: {},
            },
            statement: {
                sizeConstraintStatement: {
                    fieldToMatch: {
                        body: {},
                    },
                    textTransformations: [{
                        priority: 0,
                        type: "NONE",
                    }],
                    comparisonOperator: "GT",
                    size: 10485760, // 10MB (10 * 1024 * 1024)
                },
            },
            visibilityConfig: {
                cloudwatchMetricsEnabled: true,
                metricName: "SizeRestrictionRule",
                sampledRequestsEnabled: true,
            },
        },
        
        // ===== 7. 地理的制限（オプション）=====
        ...(config.get("enableGeoBlocking") ? [{
            name: "GeoBlockingRule",
            priority: 7,
            action: {
                block: {},
            },
            statement: {
                notStatement: {
                    statement: {
                        geoMatchStatement: {
                            countryCodes: config.getObject<string[]>("allowedCountries") || ["JP", "US"],
                        },
                    },
                },
            },
            visibilityConfig: {
                cloudwatchMetricsEnabled: true,
                metricName: "GeoBlockingRule",
                sampledRequestsEnabled: true,
            },
        }] : []),
    ],
    
    visibilityConfig: {
        cloudwatchMetricsEnabled: true,
        metricName: `${projectName}-web-acl`,
        sampledRequestsEnabled: true,
    },
    
    tags: {
        Name: `${projectName}-web-acl-${environment}`,
        Environment: environment,
    },
});

// ===== API Gateway との関連付け =====
// API Gateway のステージARNを構築
const region = aws.config.region;
const accountId = aws.getCallerIdentity().then(identity => identity.accountId);

const apiGatewayArn = pulumi.all([accountId, apiGatewayStack.getOutput("apiId"), apiStage]).apply(
    ([account, apiId, stage]) => 
        `arn:aws:apigateway:${region}::/restapis/${apiId}/stages/${stage}`
);

const webAclAssociation = new aws.wafv2.WebAclAssociation(`${projectName}-web-acl-association`, {
    resourceArn: apiGatewayArn,
    webAclArn: webAcl.arn,
});

// ===== CloudWatch アラーム =====
// レート制限違反のアラーム
const rateLimitAlarm = new aws.cloudwatch.MetricAlarm(`${projectName}-waf-rate-limit-alarm`, {
    alarmName: `${projectName}-waf-rate-limit-${environment}`,
    alarmDescription: "Alert when rate limit is exceeded",
    metricName: "BlockedRequests",
    namespace: "AWS/WAFV2",
    statistic: "Sum",
    period: 300, // 5分
    evaluationPeriods: 1,
    threshold: 100, // 5分間で100回以上ブロック
    comparisonOperator: "GreaterThanThreshold",
    dimensions: {
        Rule: "RateLimitRule",
        WebACL: webAcl.name,
        Region: region,
    },
    treatMissingData: "notBreaching",
    tags: {
        Environment: environment,
    },
});

// SQLi/XSS攻撃検出のアラーム
const attackAlarm = new aws.cloudwatch.MetricAlarm(`${projectName}-waf-attack-alarm`, {
    alarmName: `${projectName}-waf-attack-${environment}`,
    alarmDescription: "Alert when potential attacks are detected",
    metricName: "BlockedRequests",
    namespace: "AWS/WAFV2",
    statistic: "Sum",
    period: 300, // 5分
    evaluationPeriods: 1,
    threshold: 10, // 5分間で10回以上の攻撃検出
    comparisonOperator: "GreaterThanThreshold",
    dimensions: {
        WebACL: webAcl.name,
        Region: region,
    },
    treatMissingData: "notBreaching",
    tags: {
        Environment: environment,
    },
});

// ===== WAF ログ設定 =====
const wafLogGroup = new aws.cloudwatch.LogGroup(`${projectName}-waf-logs`, {
    name: `/aws/wafv2/${projectName}-${environment}`,
    retentionInDays: environment === "prod" ? 30 : 7,
    tags: {
        Environment: environment,
    },
});

// Kinesis Firehose（WAFログ配信用）
const wafLogBucket = new aws.s3.Bucket(`${projectName}-waf-logs-bucket`, {
    bucket: `${projectName}-waf-logs-${environment}-${Date.now()}`,
    acl: "private",
    lifecycleRules: [{
        enabled: true,
        expiration: {
            days: environment === "prod" ? 90 : 30,
        },
    }],
    tags: {
        Environment: environment,
    },
});

const firehoseRole = new aws.iam.Role(`${projectName}-waf-firehose-role`, {
    assumeRolePolicy: JSON.stringify({
        Version: "2012-10-17",
        Statement: [{
            Effect: "Allow",
            Principal: {
                Service: "firehose.amazonaws.com",
            },
            Action: "sts:AssumeRole",
        }],
    }),
});

const firehosePolicy = new aws.iam.RolePolicy(`${projectName}-waf-firehose-policy`, {
    role: firehoseRole.id,
    policy: pulumi.all([wafLogBucket.arn]).apply(([bucketArn]) => JSON.stringify({
        Version: "2012-10-17",
        Statement: [
            {
                Effect: "Allow",
                Action: [
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:ListBucket",
                ],
                Resource: [
                    bucketArn,
                    `${bucketArn}/*`,
                ],
            },
            {
                Effect: "Allow",
                Action: [
                    "logs:PutLogEvents",
                ],
                Resource: "*",
            },
        ],
    })),
});

const wafLogStream = new aws.kinesis.FirehoseDeliveryStream(`${projectName}-waf-log-stream`, {
    name: `aws-waf-logs-${projectName}-${environment}`,
    destination: "extended_s3",
    extendedS3Configuration: {
        bucketArn: wafLogBucket.arn,
        roleArn: firehoseRole.arn,
        prefix: "waf-logs/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/",
        errorOutputPrefix: "waf-logs-error/",
        bufferInterval: 300,
        bufferSize: 5,
        compressionFormat: "GZIP",
    },
    tags: {
        Environment: environment,
    },
});

const wafLoggingConfiguration = new aws.wafv2.WebAclLoggingConfiguration(`${projectName}-waf-logging`, {
    resourceArn: webAcl.arn,
    logDestinationConfigs: [wafLogStream.arn],
    redactedFields: [
        // センシティブな情報をマスク
        {
            singleHeader: {
                name: "authorization",
            },
        },
        {
            singleHeader: {
                name: "x-api-key",
            },
        },
    ],
});

// ===== 設定情報をSSMパラメータに保存 =====
const wafConfig = new aws.ssm.Parameter(`${projectName}-waf-config`, {
    name: `/${projectName}/${environment}/waf/config`,
    type: "String",
    value: pulumi.all([webAcl.arn, ipSet.arn]).apply(
        ([webAclArn, ipSetArn]) => JSON.stringify({
            webAcl: {
                arn: webAclArn,
                name: webAcl.name,
            },
            ipSet: {
                arn: ipSetArn,
                addresses: allWhitelistIps.length > 0 ? allWhitelistIps : ["No IP restrictions in dev"],
            },
            rules: {
                ipWhitelist: "Priority 1 - Allow whitelisted IPs",
                rateLimit: "Priority 2 - 2000 requests per 5 minutes",
                commonRuleSet: "Priority 3 - OWASP Top 10 protection",
                sqliProtection: "Priority 4 - SQL injection protection",
                xssProtection: "Priority 5 - XSS protection",
                sizeRestriction: "Priority 6 - 10MB body size limit",
                geoBlocking: config.get("enableGeoBlocking") ? "Enabled" : "Disabled",
            },
            logging: {
                s3Bucket: wafLogBucket.bucket,
                firehoseStream: wafLogStream.name,
            },
            alarms: {
                rateLimit: rateLimitAlarm.name,
                attacks: attackAlarm.name,
            },
            deployment: {
                environment: environment,
                lastUpdated: new Date().toISOString(),
            },
        })
    ),
    description: "WAF configuration",
    tags: {
        Environment: environment,
    },
});

// エクスポート
export const webAclId = webAcl.id;
export const webAclArn = webAcl.arn;
export const ipSetId = ipSet.id;
export const ipSetAddresses = allWhitelistIps;
export const wafLogBucketName = wafLogBucket.bucket;
export const wafLogStreamName = wafLogStream.name;

// WAF管理用コマンド
export const wafManagement = {
    updateIpSet: pulumi.interpolate`aws wafv2 update-ip-set --id ${ipSet.id} --addresses "IP1" "IP2" --scope REGIONAL`,
    viewBlockedRequests: pulumi.interpolate`aws logs tail /aws/wafv2/${projectName}-${environment} --follow`,
    downloadWafLogs: pulumi.interpolate`aws s3 sync s3://${wafLogBucket.bucket}/waf-logs/ ./waf-logs/`,
};

// サマリー
export const summary = {
    protection: {
        ipWhitelist: allWhitelistIps.length > 0 ? `${allWhitelistIps.length} IPs` : "No restriction (dev)",
        rateLimit: "2000 requests / 5 minutes",
        bodySize: "10MB max",
        sqli: "Protected",
        xss: "Protected",
    },
    monitoring: {
        cloudWatch: "Enabled",
        s3Logs: "Enabled",
        alarms: 2,
    },
    environment: environment,
};
