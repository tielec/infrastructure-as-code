/**
 * pulumi/lambda-security/index.ts
 * 
 * Lambda APIインフラのセキュリティグループを構築するPulumiスクリプト
 * Lambda、VPCエンドポイント、NAT Instance、DLQのセキュリティグループを作成
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "lambda-api";
const environment = pulumi.getStack();

// ネットワークスタック名を設定から取得
const networkStackName = config.get("networkStackName") || "lambda-network";

// 既存のネットワークスタックから値を取得
const networkStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${networkStackName}/${environment}`);
const vpcId = networkStack.getOutput("vpcId");
const vpcCidr = networkStack.getOutput("vpcCidr");

// ===== Lambda関数用セキュリティグループ =====
const lambdaSecurityGroup = new aws.ec2.SecurityGroup(`${projectName}-lambda-sg`, {
    vpcId: vpcId,
    description: "Security group for Lambda functions in VPC",
    // Lambda関数はアウトバウンドのみ必要（インバウンドは不要）
    ingress: [], // インバウンドルールなし
    egress: [{
        protocol: "-1", // すべてのプロトコル
        fromPort: 0,
        toPort: 0,
        cidrBlocks: ["0.0.0.0/0"],
        description: "Allow all outbound traffic for Lambda functions",
    }],
    tags: {
        Name: `${projectName}-lambda-sg-${environment}`,
        Environment: environment,
        Purpose: "lambda-functions",
    },
});

// ===== VPCエンドポイント用セキュリティグループ =====
const vpceSecurityGroup = new aws.ec2.SecurityGroup(`${projectName}-vpce-sg`, {
    vpcId: vpcId,
    description: "Security group for VPC Endpoints",
    ingress: [
        {
            protocol: "tcp",
            fromPort: 443,
            toPort: 443,
            securityGroups: [lambdaSecurityGroup.id],
            description: "HTTPS access from Lambda functions",
        },
        {
            protocol: "tcp",
            fromPort: 443,
            toPort: 443,
            cidrBlocks: [vpcCidr],
            description: "HTTPS access from VPC CIDR",
        },
    ],
    egress: [{
        protocol: "-1",
        fromPort: 0,
        toPort: 0,
        cidrBlocks: ["0.0.0.0/0"],
        description: "Allow all outbound traffic",
    }],
    tags: {
        Name: `${projectName}-vpce-sg-${environment}`,
        Environment: environment,
        Purpose: "vpc-endpoints",
    },
});

// ===== NAT Instance用セキュリティグループ =====
const natInstanceSecurityGroup = new aws.ec2.SecurityGroup(`${projectName}-nat-instance-sg`, {
    vpcId: vpcId,
    description: "Security group for NAT instance",
    ingress: [
        // VPC内からの全トラフィックを許可
        {
            protocol: "-1",
            fromPort: 0,
            toPort: 0,
            cidrBlocks: [vpcCidr],
            description: "Allow all traffic from VPC",
        },
        // 管理用SSH（必要に応じて制限）
        {
            protocol: "tcp",
            fromPort: 22,
            toPort: 22,
            cidrBlocks: ["0.0.0.0/0"], // 本番環境では管理者IPに制限すべき
            description: "SSH access for management (RESTRICT IN PRODUCTION)",
        },
    ],
    egress: [{
        protocol: "-1",
        fromPort: 0,
        toPort: 0,
        cidrBlocks: ["0.0.0.0/0"],
        description: "Allow all outbound traffic for NAT functionality",
    }],
    tags: {
        Name: `${projectName}-nat-instance-sg-${environment}`,
        Environment: environment,
        Purpose: "nat-instance",
    },
});

// ===== Dead Letter Queue (SQS)用セキュリティグループ =====
const dlqSecurityGroup = new aws.ec2.SecurityGroup(`${projectName}-dlq-sg`, {
    vpcId: vpcId,
    description: "Security group for Dead Letter Queue (SQS VPC Endpoint)",
    ingress: [
        {
            protocol: "tcp",
            fromPort: 443,
            toPort: 443,
            securityGroups: [lambdaSecurityGroup.id],
            description: "HTTPS access from Lambda functions to SQS",
        },
    ],
    egress: [{
        protocol: "-1",
        fromPort: 0,
        toPort: 0,
        cidrBlocks: ["0.0.0.0/0"],
        description: "Allow all outbound traffic",
    }],
    tags: {
        Name: `${projectName}-dlq-sg-${environment}`,
        Environment: environment,
        Purpose: "dead-letter-queue",
    },
});

// ===== Phase 2: RDS/DynamoDB用セキュリティグループ（将来用） =====
// Phase 2で有効化する場合のみ作成
const createDatabaseSecurityGroups = config.getBoolean("createDatabaseSecurityGroups") || false;

let rdsSecurityGroup: aws.ec2.SecurityGroup | undefined;
let dynamodbVpceSecurityGroup: aws.ec2.SecurityGroup | undefined;

if (createDatabaseSecurityGroups) {
    // RDS用セキュリティグループ
    rdsSecurityGroup = new aws.ec2.SecurityGroup(`${projectName}-rds-sg`, {
        vpcId: vpcId,
        description: "Security group for RDS instances (Phase 2)",
        ingress: [
            {
                protocol: "tcp",
                fromPort: 3306, // MySQL/Aurora
                toPort: 3306,
                securityGroups: [lambdaSecurityGroup.id],
                description: "MySQL access from Lambda functions",
            },
            {
                protocol: "tcp",
                fromPort: 5432, // PostgreSQL
                toPort: 5432,
                securityGroups: [lambdaSecurityGroup.id],
                description: "PostgreSQL access from Lambda functions",
            },
        ],
        egress: [{
            protocol: "-1",
            fromPort: 0,
            toPort: 0,
            cidrBlocks: ["0.0.0.0/0"],
            description: "Allow all outbound traffic",
        }],
        tags: {
            Name: `${projectName}-rds-sg-${environment}`,
            Environment: environment,
            Purpose: "rds-database",
            Phase: "2",
        },
    });

    // DynamoDB VPCエンドポイント用セキュリティグループ
    dynamodbVpceSecurityGroup = new aws.ec2.SecurityGroup(`${projectName}-dynamodb-vpce-sg`, {
        vpcId: vpcId,
        description: "Security group for DynamoDB VPC Endpoint (Phase 2)",
        ingress: [
            {
                protocol: "tcp",
                fromPort: 443,
                toPort: 443,
                securityGroups: [lambdaSecurityGroup.id],
                description: "HTTPS access from Lambda functions to DynamoDB",
            },
        ],
        egress: [{
            protocol: "-1",
            fromPort: 0,
            toPort: 0,
            cidrBlocks: ["0.0.0.0/0"],
            description: "Allow all outbound traffic",
        }],
        tags: {
            Name: `${projectName}-dynamodb-vpce-sg-${environment}`,
            Environment: environment,
            Purpose: "dynamodb-endpoint",
            Phase: "2",
        },
    });
}

// ===== API Gateway用のセキュリティルール（参考情報） =====
// API Gatewayは管理型サービスのためセキュリティグループは不要
// WAFで以下を制御:
// - IPホワイトリスト（bubble.io環境のIP）
// - レート制限（5分間で2000リクエスト）
// - SQLインジェクション/XSS防御
// - ペイロードサイズ制限（10MB以下）

// SSMパラメータにセキュリティ設定を保存
const securityConfigParameter = new aws.ssm.Parameter(`${projectName}-security-config`, {
    name: `/${projectName}/${environment}/security/config`,
    type: "String",
    value: JSON.stringify({
        lambdaSecurityGroupId: lambdaSecurityGroup.id,
        vpceSecurityGroupId: vpceSecurityGroup.id,
        natInstanceSecurityGroupId: natInstanceSecurityGroup.id,
        dlqSecurityGroupId: dlqSecurityGroup.id,
        vpcCidr: vpcCidr,
        phase2Enabled: createDatabaseSecurityGroups,
        securityNotes: {
            lambda: "Outbound only - connects to external APIs and AWS services",
            vpce: "Inbound 443 from Lambda - for S3, Secrets Manager, KMS access",
            nat: "All traffic from VPC - enables internet access for Lambda",
            dlq: "Inbound 443 from Lambda - for SQS DLQ operations",
        },
        createdAt: new Date().toISOString(),
    }),
    description: "Security configuration for Lambda API infrastructure",
    tags: {
        Environment: environment,
    },
});

// エクスポート
export const lambdaSecurityGroupId = lambdaSecurityGroup.id;
export const vpceSecurityGroupId = vpceSecurityGroup.id;
export const natInstanceSecurityGroupId = natInstanceSecurityGroup.id;
export const dlqSecurityGroupId = dlqSecurityGroup.id;

// Phase 2のエクスポート（条件付き）
export const rdsSecurityGroupId = rdsSecurityGroup?.id;
export const dynamodbVpceSecurityGroupId = dynamodbVpceSecurityGroup?.id;

// セキュリティグループの詳細情報
export const securityGroupInfo = {
    lambda: {
        id: lambdaSecurityGroup.id,
        name: lambdaSecurityGroup.name,
        description: "Lambda functions security group - outbound only",
    },
    vpce: {
        id: vpceSecurityGroup.id,
        name: vpceSecurityGroup.name,
        description: "VPC Endpoints security group - HTTPS from Lambda",
    },
    nat: {
        id: natInstanceSecurityGroup.id,
        name: natInstanceSecurityGroup.name,
        description: "NAT Instance security group - all VPC traffic",
    },
    dlq: {
        id: dlqSecurityGroup.id,
        name: dlqSecurityGroup.name,
        description: "Dead Letter Queue security group - HTTPS from Lambda",
    },
    phase2: createDatabaseSecurityGroups ? {
        rds: {
            id: rdsSecurityGroup?.id,
            name: rdsSecurityGroup?.name,
            description: "RDS security group - MySQL/PostgreSQL from Lambda",
        },
        dynamodb: {
            id: dynamodbVpceSecurityGroup?.id,
            name: dynamodbVpceSecurityGroup?.name,
            description: "DynamoDB VPC Endpoint security group - HTTPS from Lambda",
        },
    } : undefined,
};

// セキュリティベストプラクティスのチェックリスト
const securityChecklistParameter = new aws.ssm.Parameter(`${projectName}-security-checklist`, {
    name: `/${projectName}/${environment}/security/checklist`,
    type: "String",
    value: JSON.stringify({
        completed: [
            "VPC isolation for Lambda functions",
            "Least privilege security groups",
            "No unnecessary inbound rules for Lambda",
            "VPC endpoints for AWS services (reduces exposure)",
            "NAT for controlled internet access",
        ],
        recommended: [
            "Enable VPC Flow Logs for network monitoring",
            "Restrict NAT Instance SSH to specific IPs in production",
            "Enable AWS GuardDuty for threat detection",
            "Regular security group audits",
            "Use AWS Config rules for compliance checking",
        ],
        phase2: [
            "Encrypt RDS at rest and in transit",
            "Enable DynamoDB encryption",
            "Database security group restrictions",
            "Secrets Manager for database credentials",
            "Enable database audit logging",
        ],
    }),
    description: "Security best practices checklist for Lambda API",
    tags: {
        Environment: environment,
    },
});

export const securityConfigParameterName = securityConfigParameter.name;
export const securityChecklistParameterName = securityChecklistParameter.name;
