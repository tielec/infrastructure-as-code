/**
 * pulumi/security/index.ts
 * 
 * Jenkinsインフラのセキュリティグループを構築するPulumiスクリプト
 * ALB、Jenkinsコントローラー、エージェント、EFSのセキュリティグループを作成
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// 環境名をスタック名から取得
const environment = pulumi.getStack();
const ssmPrefix = `/jenkins-infra/${environment}`;

// SSMパラメータから設定を取得
const projectNameParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/project-name`,
});
const vpcIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/vpc-id`,
});

// 設定値を変数に設定
const projectName = pulumi.output(projectNameParam).apply(p => p.value);
const vpcId = pulumi.output(vpcIdParam).apply(p => p.value);

// ALB用セキュリティグループ
const albSecurityGroup = new aws.ec2.SecurityGroup(`alb-sg`, {
    vpcId: vpcId,
    description: "Security group for Jenkins ALB",
    ingress: [
        // HTTP
        {
            protocol: "tcp",
            fromPort: 80,
            toPort: 80,
            cidrBlocks: ["0.0.0.0/0"],
            description: "HTTP access",
        },
        // HTTPS
        {
            protocol: "tcp",
            fromPort: 443,
            toPort: 443,
            cidrBlocks: ["0.0.0.0/0"],
            description: "HTTPS access",
        },
        // Jenkins HTTP
        {
            protocol: "tcp",
            fromPort: 8080,
            toPort: 8080,
            cidrBlocks: ["0.0.0.0/0"],
            description: "Jenkins HTTP access",
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
        Name: pulumi.interpolate`${projectName}-alb-sg-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// Jenkins マスター用セキュリティグループ
const jenkinsSecurityGroup = new aws.ec2.SecurityGroup(`jenkins-sg`, {
    vpcId: vpcId,
    description: "Security group for Jenkins master instances",
    ingress: [
        // Jenkins Web UI（ALBからのみ許可）
        {
            protocol: "tcp",
            fromPort: 8080,
            toPort: 8080,
            securityGroups: [albSecurityGroup.id],
            description: "Jenkins Web UI access from ALB",
        },
        // SSH アクセス
        {
            protocol: "tcp",
            fromPort: 22,
            toPort: 22,
            cidrBlocks: ["0.0.0.0/0"],  // 本番環境では制限すべき
            description: "SSH access",
        },
        // JNLP（Jenkinsエージェント接続用）
        {
            protocol: "tcp",
            fromPort: 50000,
            toPort: 50000,
            cidrBlocks: ["10.0.0.0/16"],
            description: "Jenkins agent JNLP connection",
        },
    ],
    // すべてのアウトバウンドトラフィックを許可
    egress: [{
        protocol: "-1",
        fromPort: 0,
        toPort: 0,
        cidrBlocks: ["0.0.0.0/0"],
        description: "Allow all outbound traffic",
    }],
    tags: {
        Name: pulumi.interpolate`${projectName}-jenkins-master-sg-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// Jenkinsエージェント用セキュリティグループ
const jenkinsAgentSecurityGroup = new aws.ec2.SecurityGroup(`jenkins-agent-sg`, {
    vpcId: vpcId,
    description: "Security group for Jenkins agent instances",
    ingress: [
        // SSHアクセス（Jenkinsマスターからのみ）
        {
            protocol: "tcp",
            fromPort: 22,
            toPort: 22,
            securityGroups: [jenkinsSecurityGroup.id],
            description: "SSH access from Jenkins master",
        },
        // Jenkins JNLPエージェント接続（Jenkinsマスターからのみ）
        {
            protocol: "tcp",
            fromPort: 0,
            toPort: 65535,
            securityGroups: [jenkinsSecurityGroup.id],
            description: "JNLP agent connection from Jenkins master",
        },
    ],
    // すべてのアウトバウンドトラフィックを許可
    egress: [{
        protocol: "-1",
        fromPort: 0,
        toPort: 0,
        cidrBlocks: ["0.0.0.0/0"],
        description: "Allow all outbound traffic",
    }],
    tags: {
        Name: pulumi.interpolate`${projectName}-jenkins-agent-sg-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// EFS用セキュリティグループ
const efsSecurityGroup = new aws.ec2.SecurityGroup(`efs-sg`, {
    vpcId: vpcId,
    description: "Security group for Jenkins EFS",
    ingress: [
        // NFS（2049ポート）を許可
        {
            protocol: "tcp",
            fromPort: 2049,
            toPort: 2049,
            securityGroups: [jenkinsSecurityGroup.id, jenkinsAgentSecurityGroup.id],
            description: "NFS access from Jenkins instances and agents",
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
        Name: pulumi.interpolate`${projectName}-efs-sg-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// NAT Instance用セキュリティグループ
const natInstanceSecurityGroup = new aws.ec2.SecurityGroup(`nat-instance-sg`, {
    vpcId: vpcId,
    description: "Security group for NAT instance",
    ingress: [
        // VPC内からの全トラフィックを許可
        {
            protocol: "-1",
            fromPort: 0,
            toPort: 0,
            cidrBlocks: ["10.0.0.0/16"],
            description: "Allow all traffic from VPC",
        },
        // 管理用SSH（必要に応じて制限）
        {
            protocol: "tcp",
            fromPort: 22,
            toPort: 22,
            cidrBlocks: ["0.0.0.0/0"], // 本番環境では管理者IPに制限
            description: "SSH access for management",
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
        Name: pulumi.interpolate`${projectName}-nat-instance-sg-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// SSMパラメータストアへの保存
// ALBセキュリティグループ
const albSecurityGroupIdParam = new aws.ssm.Parameter(`alb-sg-id`, {
    name: `${ssmPrefix}/security/alb-sg-id`,
    type: "String",
    value: albSecurityGroup.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "security",
    },
});

// Jenkinsマスターセキュリティグループ
const jenkinsSecurityGroupIdParam = new aws.ssm.Parameter(`jenkins-sg-id`, {
    name: `${ssmPrefix}/security/jenkins-sg-id`,
    type: "String",
    value: jenkinsSecurityGroup.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "security",
    },
});

// Jenkinsエージェントセキュリティグループ
const jenkinsAgentSecurityGroupIdParam = new aws.ssm.Parameter(`jenkins-agent-sg-id`, {
    name: `${ssmPrefix}/security/jenkins-agent-sg-id`,
    type: "String",
    value: jenkinsAgentSecurityGroup.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "security",
    },
});

// EFSセキュリティグループ
const efsSecurityGroupIdParam = new aws.ssm.Parameter(`efs-sg-id`, {
    name: `${ssmPrefix}/security/efs-sg-id`,
    type: "String",
    value: efsSecurityGroup.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "security",
    },
});

// NATインスタンスセキュリティグループ
const natInstanceSecurityGroupIdParam = new aws.ssm.Parameter(`nat-instance-sg-id`, {
    name: `${ssmPrefix}/security/nat-instance-sg-id`,
    type: "String",
    value: natInstanceSecurityGroup.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "security",
    },
});

// エクスポート（既存のスタック参照用に残す）
export const albSecurityGroupId = albSecurityGroup.id;
export const jenkinsSecurityGroupId = jenkinsSecurityGroup.id;
export const jenkinsAgentSecurityGroupId = jenkinsAgentSecurityGroup.id;
export const efsSecurityGroupId = efsSecurityGroup.id;
export const natInstanceSecurityGroupId = natInstanceSecurityGroup.id;
