/**
 * pulumi/lambda-waf/index.ts
 * 
 * Lambda API WAFリソースを構築するPulumiスクリプト
 * IP Whitelistは独立したスタックから参照
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// Node.jsグローバル変数の型定義を確実にするため（VSCode対応）
declare const process: NodeJS.Process;

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "lambda-api";
const environment = pulumi.getStack();

// スタック参照
const apiGatewayStackName = config.get("apiGatewayStackName") || "lambda-api-gateway";
const ipWhitelistStackName = config.get("ipWhitelistStackName") || "lambda-ip-whitelist";

// 既存スタックから値を取得
const apiGatewayStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${apiGatewayStackName}/${environment}`);
const ipWhitelistStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${ipWhitelistStackName}/${environment}`);

const apiStage = apiGatewayStack.getOutput("apiStage");
const ipWhitelistSecretArn = ipWhitelistStack.getOutput("secretArn");
const ipWhitelistSecretName = ipWhitelistStack.getOutput("secretName");

// WAF設定（設計書に基づく）
interface WafConfig {
    projectName: string;
    ipWhitelist: string[];
    rateLimit: number;
    blockPeriod: number;
    geoMatchConstraint?: string[];
}

// クライアント情報の型定義（IP Whitelistスタックと共通）
interface ClientInfo {
    id: string;
    name: string;
    description: string;
    enabled: boolean;
    ipAddresses: string[];
    tags: {
        type: string;
        priority: string;
        environment?: string;
    };
}

interface IpWhitelistConfig {
    version: string;
    lastUpdated: string;
    clients: ClientInfo[];
    globalRules: {
        allowedEnvironments: string[];
        maxIpsPerClient: number;
        ipFormat: string;
    };
}

// ===== IP Whitelist の取得（独立スタックから）=====
async function getIpWhitelist(): Promise<string[]> {
    try {
        // Secrets Manager SDKクライアントの作成
        const secretsManager = new aws.sdk.SecretsManager();
        
        // Secrets Managerから取得（スタック参照経由）
        const secretName = await ipWhitelistSecretName.promise();
        
        try {
            // Secretの値を取得
            const result = await secretsManager.getSecretValue({ SecretId: secretName }).promise();
            
            if (result.SecretString) {
                const whitelistConfig: IpWhitelistConfig = JSON.parse(result.SecretString);
                const allowedIps: string[] = [];
                
                // 有効なクライアントのIPアドレスを収集
                whitelistConfig.clients.forEach(client => {
                    if (!client.enabled) {
                        pulumi.log.info(`Skipping disabled client: ${client.name}`);
                        return;
                    }
                    
                    if (client.tags.environment && client.tags.environment !== `${environment}-only`) {
                        pulumi.log.info(`Skipping client ${client.name} - not for ${environment} environment`);
                        return;
                    }
                    
                    pulumi.log.info(`Adding IPs for client: ${client.name} (${client.ipAddresses.length} addresses)`);
                    allowedIps.push(...client.ipAddresses);
                });
                
                pulumi.log.info(`Total allowed IPs from Secrets Manager: ${allowedIps.length}`);
                return allowedIps.length > 0 ? allowedIps : getDefaultIps();
            }
        } catch (secretError: any) {
            // Secretが見つからない、またはアクセスできない場合
            if (secretError.code === 'ResourceNotFoundException') {
                pulumi.log.warn(`Secret not found: ${secretName}. Using default configuration.`);
            } else if (secretError.code === 'AccessDeniedException') {
                pulumi.log.warn(`Access denied to secret: ${secretName}. Check IAM permissions.`);
            } else {
                pulumi.log.warn(`Error retrieving secret: ${secretError.message}`);
            }
        }
        
        // Secretが取得できない場合はデフォルト値を返す
        return getDefaultIps();
        
    } catch (error) {
        pulumi.log.error(`Unexpected error in getIpWhitelist: ${error}`);
        return getDefaultIps();
    }
}

// デフォルトIPの取得
function getDefaultIps(): string[] {
    // 環境別のデフォルト値
    if (environment === "dev") {
        pulumi.log.warn("Using default IP whitelist for development (0.0.0.0/0 - ALL IPs allowed)");
        pulumi.log.warn("SECURITY WARNING: Please configure actual IP whitelist via lambda-ip-whitelist stack");
        return ["0.0.0.0/0"];
    }
    
    // Pulumi設定からフォールバックIPを取得
    const fallbackIps = config.getObject<string[]>("fallbackIpWhitelist");
    if (fallbackIps && fallbackIps.length > 0) {
        pulumi.log.info(`Using fallback IP whitelist from Pulumi config: ${fallbackIps.length} IPs`);
        return fallbackIps;
    }
    
    // ステージング/本番で設定がない場合はエラー
    throw new Error(`No IP whitelist configured for ${environment} environment. Please deploy lambda-ip-whitelist stack first.`);
}

// IP Whitelistの取得（非同期処理をPromiseとして扱う）
const ipWhitelistPromise = getIpWhitelist();

// ===== IP Set（ホワイトリスト）=====
const ipSet = new aws.wafv2.IpSet(`${projectName}-ip-whitelist`, {
    name: `${projectName}-ip-whitelist-${environment}`,
    description: "Allowed IP addresses for API access (managed by lambda-ip-whitelist stack)",
    scope: "REGIONAL", // API Gateway用
    ipAddressVersion: "IPV4",
    addresses: pulumi.output(ipWhitelistPromise),
    tags: {
        Name: `${projectName}-ip-whitelist-${environment}`,
        Environment: environment,
        ManagedBy: "lambda-ip-whitelist-stack",
    },
});

// ===== Web ACL =====
const webAcl = new aws.wafv2.WebAcl(`${projectName}-web-acl`, {
    name: `${projectName}-web-acl-${environment}`,
    description: "Web ACL for Lambda API protection",
    scope: "REGIONAL",
    
    // デフォルトアクション（ルールに一致しない場合）
    defaultAction: {
        // 本番環境ではデフォルトブロック、開発環境ではデフォルト許可
        ...(environment === "prod" ? { block: {} } : { allow: {} }),
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
                geoMatchStatement: {
                    countryCodes: config.getObject<string[]>("blockedCountries") || ["CN", "RU"],
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
const region = aws.config.region || "ap-northeast-1";
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
    name: `${projectName}-waf-rate-limit-${environment}`,
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
        Region: region || "ap-northeast-1",
    },
    treatMissingData: "notBreaching",
    tags: {
        Environment: environment,
    },
});

// SQLi/XSS攻撃検出のアラーム
const attackAlarm = new aws.cloudwatch.MetricAlarm(`${projectName}-waf-attack-alarm`, {
    name: `${projectName}-waf-attack-${environment}`,
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
        Region: region || "ap-northeast-1",
    },
    treatMissingData: "notBreaching",
    tags: {
        Environment: environment,
    },
});

// ===== 管理用Lambda関数（IP Whitelist更新用）=====
const updateIpWhitelistRole = new aws.iam.Role(`${projectName}-update-ip-whitelist-role`, {
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
});

new aws.iam.RolePolicyAttachment(`${projectName}-update-ip-whitelist-basic`, {
    role: updateIpWhitelistRole.name,
    policyArn: "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
});

const updateIpWhitelistPolicy = new aws.iam.RolePolicy(`${projectName}-update-ip-whitelist-policy`, {
    role: updateIpWhitelistRole.id,
    policy: pulumi.all([ipSet.arn, ipWhitelistSecretArn]).apply(([ipSetArn, secretArn]) => JSON.stringify({
        Version: "2012-10-17",
        Statement: [
            {
                Effect: "Allow",
                Action: [
                    "wafv2:UpdateIPSet",
                    "wafv2:GetIPSet",
                ],
                Resource: ipSetArn,
            },
            {
                Effect: "Allow",
                Action: [
                    "secretsmanager:GetSecretValue",
                ],
                Resource: secretArn,
            },
        ],
    })),
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
    value: pulumi.all([webAcl.arn, ipSet.arn, ipWhitelistSecretArn, ipWhitelistSecretName]).apply(
        ([webAclArn, ipSetArn, secretArn, secretName]) => JSON.stringify({
            webAcl: {
                arn: webAclArn,
                name: webAcl.name,
            },
            ipSet: {
                arn: ipSetArn,
                managedBy: "lambda-ip-whitelist stack",
                secretArn: secretArn,
                secretName: secretName,
                updateInstructions: "Update via lambda-ip-whitelist stack or Secrets Manager",
            },
            rules: {
                ipWhitelist: "Priority 1 - Allow whitelisted IPs from lambda-ip-whitelist stack",
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

// IP管理ガイドのパラメータ
const ipManagementGuide = new aws.ssm.Parameter(`${projectName}-ip-management-guide`, {
    name: `/${projectName}/${environment}/waf/ip-management-guide`,
    type: "String",
    value: pulumi.all([ipWhitelistSecretName]).apply(([secretName]) => JSON.stringify({
        overview: "IP whitelist is managed via lambda-ip-whitelist stack",
        secretName: secretName,
        managementMethod: "Pulumi stack (lambda-ip-whitelist)",
        updateProcess: [
            "Option 1: Update via lambda-ip-whitelist stack",
            "Option 2: Direct Secrets Manager update",
            `aws secretsmanager get-secret-value --secret-id ${secretName} --query SecretString --output text > whitelist.json`,
            "Edit whitelist.json",
            `aws secretsmanager put-secret-value --secret-id ${secretName} --secret-string file://whitelist.json`,
            "Changes are applied automatically within 5 minutes"
        ],
        clientStructure: {
            id: "Unique identifier for the client",
            name: "Human-readable name",
            description: "Purpose of this client",
            enabled: "true/false to enable/disable without removing",
            ipAddresses: ["Array of CIDR blocks"],
            tags: {
                type: "platform|api-service|internal|monitoring|other",
                priority: "high|medium|low",
                environment: "Optional: dev-only|staging-only|prod-only"
            }
        },
        examples: {
            addNewClient: {
                id: "client-004",
                name: "Mobile App Backend",
                description: "Mobile application API gateway",
                enabled: true,
                ipAddresses: ["192.0.2.0/24"],
                tags: {
                    type: "api-service",
                    priority: "high"
                }
            },
            disableClient: "Set 'enabled': false for the client",
            removeClient: "Delete the entire client object from the array"
        },
        securityNotes: {
            dev: environment === "dev" ? "WARNING: May be using 0.0.0.0/0 (all IPs). Check lambda-ip-whitelist stack." : null,
            production: "Always use specific IP ranges in production environments",
            monitoring: "Check WAF logs regularly for blocked legitimate requests",
            stackManagement: "IP whitelist is managed by lambda-ip-whitelist stack"
        }
    })),
    description: "IP whitelist management guide",
    tags: {
        Environment: environment,
    },
});

// エクスポート
export const webAclId = webAcl.id;
export const webAclArn = webAcl.arn;
export const ipSetId = ipSet.id;
export const ipWhitelistSource = "lambda-ip-whitelist stack";
export const wafLogBucketName = wafLogBucket.bucket;
export const wafLogStreamName = wafLogStream.name;

// WAF管理用コマンド
export const wafManagement = {
    getIpWhitelist: pulumi.interpolate`aws secretsmanager get-secret-value --secret-id ${ipWhitelistSecretName} --query SecretString --output text | jq .`,
    updateIpWhitelist: pulumi.interpolate`Use lambda-ip-whitelist stack or: aws secretsmanager put-secret-value --secret-id ${ipWhitelistSecretName} --secret-string 'YOUR_JSON_HERE'`,
    viewBlockedRequests: pulumi.interpolate`aws logs tail /aws/wafv2/${projectName}-${environment} --follow`,
    downloadWafLogs: pulumi.interpolate`aws s3 sync s3://${wafLogBucket.bucket}/waf-logs/ ./waf-logs/`,
};

// IP管理情報
export const ipManagement = {
    source: "Managed by lambda-ip-whitelist stack",
    secretName: ipWhitelistSecretName,
    updateCommand: pulumi.interpolate`cd ../lambda-ip-whitelist && pulumi stack output managementCommands`,
};

// サマリー
export const summary = {
    protection: {
        ipWhitelist: "Managed via lambda-ip-whitelist stack",
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
    ipManagement: {
        method: "lambda-ip-whitelist Pulumi stack",
        secretName: ipWhitelistSecretName,
        updateFrequency: "Real-time",
        stackReference: `${pulumi.getOrganization()}/${ipWhitelistStackName}/${environment}`,
    },
    environment: environment,
    setupStatus: pulumi.output(ipWhitelistPromise).apply(ips => 
        ips.includes("0.0.0.0/0") ? "Using default configuration - UPDATE REQUIRED" : "Configured"
    ),
};
