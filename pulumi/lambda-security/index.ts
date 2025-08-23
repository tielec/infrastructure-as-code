/**
 * pulumi/lambda-security/index.ts
 * 
 * Lambda APIインフラのセキュリティグループを構築するPulumiスクリプト
 * Lambda、VPCエンドポイント、NAT Instance、DLQのセキュリティグループを作成
 * SSMパラメータストアから設定を取得
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

// VPC情報を取得
const vpcIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/vpc-id`,
});
const vpcId = pulumi.output(vpcIdParam).apply(p => p.value);

const vpcCidrParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/vpc-cidr`,
});
const vpcCidr = pulumi.output(vpcCidrParam).apply(p => p.value);

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
// セキュリティグループ定義
// ========================================
// Lambda関数用セキュリティグループ
const lambdaSecurityGroup = new aws.ec2.SecurityGroup("lambda-sg", {
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
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-lambda-sg-${environment}`,
        Purpose: "lambda-functions",
    },
});

// VPCエンドポイント用セキュリティグループ
const vpceSecurityGroup = new aws.ec2.SecurityGroup("vpce-sg", {
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
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-vpce-sg-${environment}`,
        Purpose: "vpc-endpoints",
    },
});

// NAT Instance用セキュリティグループ
const natInstanceSecurityGroup = new aws.ec2.SecurityGroup("nat-instance-sg", {
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
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-nat-instance-sg-${environment}`,
        Purpose: "nat-instance",
    },
});

// Dead Letter Queue (SQS)用セキュリティグループ
const dlqSecurityGroup = new aws.ec2.SecurityGroup("dlq-sg", {
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
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-dlq-sg-${environment}`,
        Purpose: "dead-letter-queue",
    },
});

// ========================================
// Phase 2: RDS/DynamoDB用セキュリティグループ（将来用）
// ========================================
// Phase 2で有効化する場合のみ作成
// SSMパラメータが存在しない場合はfalseとして扱う
const createDatabaseSecurityGroups = pulumi.output(
    aws.ssm.getParameter({
        name: `/lambda-api/${environment}/phase/database-sg-enabled`,
    }).catch(() => ({ value: "false" }))
).apply(p => p.value === "true");

let rdsSecurityGroup: aws.ec2.SecurityGroup | undefined;
let dynamodbVpceSecurityGroup: aws.ec2.SecurityGroup | undefined;

if (createDatabaseSecurityGroups) {
    // RDS用セキュリティグループ
    rdsSecurityGroup = new aws.ec2.SecurityGroup("rds-sg", {
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
            ...commonTags,
            Name: pulumi.interpolate`${projectName}-rds-sg-${environment}`,
            Purpose: "rds-database",
            Phase: "2",
        },
    });

    // DynamoDB VPCエンドポイント用セキュリティグループ
    dynamodbVpceSecurityGroup = new aws.ec2.SecurityGroup("dynamodb-vpce-sg", {
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
            ...commonTags,
            Name: pulumi.interpolate`${projectName}-dynamodb-vpce-sg-${environment}`,
            Purpose: "dynamodb-endpoint",
            Phase: "2",
        },
    });
}

// ========================================
// API Gateway用のセキュリティルール（参考情報）
// ========================================
// API Gatewayは管理型サービスのためセキュリティグループは不要
// WAFで以下を制御:
// - IPホワイトリスト（bubble.io環境のIP）
// - レート制限（5分間で2000リクエスト）
// - SQLインジェクション/XSS防御
// - ペイロードサイズ制限（10MB以下）

// ========================================
// SSMパラメータへの保存
// ========================================
// 他のスタックが参照する値をSSMに保存
const paramPrefix = pulumi.interpolate`/${projectName}/${environment}/security`;

// Lambda Security Group ID
const lambdaSgIdParam = new aws.ssm.Parameter("lambda-sg-id", {
    name: pulumi.interpolate`${paramPrefix}/lambda-sg-id`,
    type: "String",
    value: lambdaSecurityGroup.id,
    description: "Lambda functions security group ID",
    tags: commonTags,
});

// VPC Endpoint Security Group ID
const vpceSgIdParam = new aws.ssm.Parameter("vpce-sg-id", {
    name: pulumi.interpolate`${paramPrefix}/vpce-sg-id`,
    type: "String",
    value: vpceSecurityGroup.id,
    description: "VPC Endpoints security group ID",
    tags: commonTags,
});

// NAT Instance Security Group ID
const natSgIdParam = new aws.ssm.Parameter("nat-sg-id", {
    name: pulumi.interpolate`${paramPrefix}/nat-instance-sg-id`,
    type: "String",
    value: natInstanceSecurityGroup.id,
    description: "NAT Instance security group ID",
    tags: commonTags,
});

// DLQ Security Group ID
const dlqSgIdParam = new aws.ssm.Parameter("dlq-sg-id", {
    name: pulumi.interpolate`${paramPrefix}/dlq-sg-id`,
    type: "String",
    value: dlqSecurityGroup.id,
    description: "Dead Letter Queue security group ID",
    tags: commonTags,
});

// Phase 2: RDS/DynamoDB Security Groups (if enabled)
if (createDatabaseSecurityGroups && rdsSecurityGroup && dynamodbVpceSecurityGroup) {
    const rdsSgIdParam = new aws.ssm.Parameter("rds-sg-id", {
        name: pulumi.interpolate`${paramPrefix}/rds-sg-id`,
        type: "String",
        value: rdsSecurityGroup.id,
        description: "RDS security group ID",
        tags: commonTags,
    });

    const dynamodbSgIdParam = new aws.ssm.Parameter("dynamodb-sg-id", {
        name: pulumi.interpolate`${paramPrefix}/dynamodb-vpce-sg-id`,
        type: "String",
        value: dynamodbVpceSecurityGroup.id,
        description: "DynamoDB VPC Endpoint security group ID",
        tags: commonTags,
    });
} else {
    // Phase 1の場合は空文字列を設定
    new aws.ssm.Parameter("rds-sg-id-empty", {
        name: pulumi.interpolate`${paramPrefix}/rds-sg-id`,
        type: "String",
        value: "",
        description: "RDS security group ID (not created in Phase 1)",
        tags: commonTags,
    });

    new aws.ssm.Parameter("dynamodb-sg-id-empty", {
        name: pulumi.interpolate`${paramPrefix}/dynamodb-vpce-sg-id`,
        type: "String",
        value: "",
        description: "DynamoDB VPC Endpoint security group ID (not created in Phase 1)",
        tags: commonTags,
    });
}

// デプロイメント完了フラグ
const deploymentCompleteParam = new aws.ssm.Parameter("security-deployed", {
    name: pulumi.interpolate`${paramPrefix}/deployment/complete`,
    type: "String",
    value: "true",
    description: "Security stack deployment completion flag",
    tags: commonTags,
});

// ========================================
// セキュリティチェックリスト
// ========================================

const securityChecklistParameter = new aws.ssm.Parameter("security-checklist", {
    name: pulumi.interpolate`/${projectName}/${environment}/security/checklist`,
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
    tags: commonTags,
});

// ========================================
// エクスポート（表示用のみ）
// ========================================
// エクスポートは表示・確認用のみ
// 他のスタックはSSMパラメータから値を取得すること
export const outputs = {
    stack: "lambda-security",
    environment: environment,
    lambdaSecurityGroupId: lambdaSecurityGroup.id,
    vpceSecurityGroupId: vpceSecurityGroup.id,
    natSecurityGroupId: natInstanceSecurityGroup.id,
    dlqSecurityGroupId: dlqSecurityGroup.id,
    ssmParameterPrefix: paramPrefix,
    phase2Enabled: createDatabaseSecurityGroups,
    deploymentComplete: deploymentCompleteParam.name,
};
