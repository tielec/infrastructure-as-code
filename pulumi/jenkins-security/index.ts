/**
 * pulumi/security/index.ts
 * 
 * JenkinsインフラのセキュリティグループとNACLを構築するPulumiスクリプト
 * IPv6デュアルスタック対応のセキュリティルールを含む
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
const vpcCidrParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/vpc-cidr`,
});
const vpcIpv6CidrParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/vpc-ipv6-cidr`,
});
const privateSubnetAIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/private-subnet-a-id`,
});
const privateSubnetBIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/private-subnet-b-id`,
});

// 設定値を変数に設定
const projectName = pulumi.output(projectNameParam).apply(p => p.value);
const vpcId = pulumi.output(vpcIdParam).apply(p => p.value);
const vpcCidr = pulumi.output(vpcCidrParam).apply(p => p.value);
const vpcIpv6Cidr = pulumi.output(vpcIpv6CidrParam).apply(p => p.value);
const privateSubnetAId = pulumi.output(privateSubnetAIdParam).apply(p => p.value);
const privateSubnetBId = pulumi.output(privateSubnetBIdParam).apply(p => p.value);

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
        // HTTPS (IPv6)
        {
            protocol: "tcp",
            fromPort: 443,
            toPort: 443,
            ipv6CidrBlocks: ["::/0"],
            description: "HTTPS access (IPv6)",
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
    egress: [
        {
            protocol: "-1",
            fromPort: 0,
            toPort: 0,
            cidrBlocks: ["0.0.0.0/0"],
            description: "Allow all outbound traffic (IPv4)",
        },
        {
            protocol: "-1",
            fromPort: 0,
            toPort: 0,
            ipv6CidrBlocks: ["::/0"],
            description: "Allow all outbound traffic (IPv6)",
        },
    ],
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
    egress: [
        {
            protocol: "-1",
            fromPort: 0,
            toPort: 0,
            cidrBlocks: ["0.0.0.0/0"],
            description: "Allow all outbound traffic (IPv4)",
        },
        {
            protocol: "-1",
            fromPort: 0,
            toPort: 0,
            ipv6CidrBlocks: ["::/0"],
            description: "Allow all outbound traffic (IPv6)",
        },
    ],
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
    egress: [
        {
            protocol: "-1",
            fromPort: 0,
            toPort: 0,
            cidrBlocks: ["0.0.0.0/0"],
            description: "Allow all outbound traffic (IPv4)",
        },
        {
            protocol: "-1",
            fromPort: 0,
            toPort: 0,
            ipv6CidrBlocks: ["::/0"],
            description: "Allow all outbound traffic (IPv6)",
        },
    ],
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
    egress: [
        {
            protocol: "-1",
            fromPort: 0,
            toPort: 0,
            cidrBlocks: ["0.0.0.0/0"],
            description: "Allow all outbound traffic (IPv4)",
        },
        {
            protocol: "-1",
            fromPort: 0,
            toPort: 0,
            ipv6CidrBlocks: ["::/0"],
            description: "Allow all outbound traffic (IPv6)",
        },
    ],
    tags: {
        Name: pulumi.interpolate`${projectName}-efs-sg-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// NAT Instance用セキュリティグループ（IPv6環境では不要だが互換性のため残す）
const natInstanceSecurityGroup = new aws.ec2.SecurityGroup(`nat-instance-sg`, {
    vpcId: vpcId,
    description: "Security group for NAT instance (deprecated in IPv6 environment)",
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
    egress: [
        {
            protocol: "-1",
            fromPort: 0,
            toPort: 0,
            cidrBlocks: ["0.0.0.0/0"],
            description: "Allow all outbound traffic (IPv4)",
        },
        {
            protocol: "-1",
            fromPort: 0,
            toPort: 0,
            ipv6CidrBlocks: ["::/0"],
            description: "Allow all outbound traffic (IPv6)",
        },
    ],
    tags: {
        Name: pulumi.interpolate`${projectName}-nat-instance-sg-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// プライベートサブネット用NACL（制限的なアクセス制御）
const privateNacl = new aws.ec2.NetworkAcl(`private-nacl`, {
    vpcId: vpcId,
    tags: {
        Name: pulumi.interpolate`${projectName}-private-nacl-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// プライベートNACLインバウンドルール
// HTTPSレスポンス（エフェメラルポート）
new aws.ec2.NetworkAclRule(`private-nacl-inbound-https-response`, {
    networkAclId: privateNacl.id,
    ruleNumber: 100,
    protocol: "tcp",
    ruleAction: "allow",
    fromPort: 1024,
    toPort: 65535,
    cidrBlock: "0.0.0.0/0",
});

new aws.ec2.NetworkAclRule(`private-nacl-inbound-https-response-ipv6`, {
    networkAclId: privateNacl.id,
    ruleNumber: 101,
    protocol: "tcp",
    ruleAction: "allow",
    fromPort: 1024,
    toPort: 65535,
    ipv6CidrBlock: "::/0",
});

// VPC内からの通信を許可
new aws.ec2.NetworkAclRule(`private-nacl-inbound-vpc`, {
    networkAclId: privateNacl.id,
    ruleNumber: 200,
    protocol: "-1",
    ruleAction: "allow",
    fromPort: 0,
    toPort: 0,
    cidrBlock: vpcCidr,
});

new aws.ec2.NetworkAclRule(`private-nacl-inbound-vpc-ipv6`, {
    networkAclId: privateNacl.id,
    ruleNumber: 201,
    protocol: "-1",
    ruleAction: "allow",
    fromPort: 0,
    toPort: 0,
    ipv6CidrBlock: vpcIpv6Cidr,
});

// プライベートNACLアウトバウンドルール
// HTTPS（必要なアウトバウンド通信）
new aws.ec2.NetworkAclRule(`private-nacl-outbound-https`, {
    networkAclId: privateNacl.id,
    ruleNumber: 100,
    protocol: "tcp",
    ruleAction: "allow",
    fromPort: 443,
    toPort: 443,
    cidrBlock: "0.0.0.0/0",
    egress: true,
});

new aws.ec2.NetworkAclRule(`private-nacl-outbound-https-ipv6`, {
    networkAclId: privateNacl.id,
    ruleNumber: 101,
    protocol: "tcp",
    ruleAction: "allow",
    fromPort: 443,
    toPort: 443,
    ipv6CidrBlock: "::/0",
    egress: true,
});

// HTTP（パッケージリポジトリ等のため）
new aws.ec2.NetworkAclRule(`private-nacl-outbound-http`, {
    networkAclId: privateNacl.id,
    ruleNumber: 110,
    protocol: "tcp",
    ruleAction: "allow",
    fromPort: 80,
    toPort: 80,
    cidrBlock: "0.0.0.0/0",
    egress: true,
});

new aws.ec2.NetworkAclRule(`private-nacl-outbound-http-ipv6`, {
    networkAclId: privateNacl.id,
    ruleNumber: 111,
    protocol: "tcp",
    ruleAction: "allow",
    fromPort: 80,
    toPort: 80,
    ipv6CidrBlock: "::/0",
    egress: true,
});

// VPC内への通信を許可
new aws.ec2.NetworkAclRule(`private-nacl-outbound-vpc`, {
    networkAclId: privateNacl.id,
    ruleNumber: 200,
    protocol: "-1",
    ruleAction: "allow",
    fromPort: 0,
    toPort: 0,
    cidrBlock: vpcCidr,
    egress: true,
});

new aws.ec2.NetworkAclRule(`private-nacl-outbound-vpc-ipv6`, {
    networkAclId: privateNacl.id,
    ruleNumber: 201,
    protocol: "-1",
    ruleAction: "allow",
    fromPort: 0,
    toPort: 0,
    ipv6CidrBlock: vpcIpv6Cidr,
    egress: true,
});

// NACLをプライベートサブネットに関連付け
new aws.ec2.NetworkAclAssociation(`private-nacl-assoc-a`, {
    networkAclId: privateNacl.id,
    subnetId: privateSubnetAId,
});

new aws.ec2.NetworkAclAssociation(`private-nacl-assoc-b`, {
    networkAclId: privateNacl.id,
    subnetId: privateSubnetBId,
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

// プライベートNACL ID
const privateNaclIdParam = new aws.ssm.Parameter(`private-nacl-id`, {
    name: `${ssmPrefix}/security/private-nacl-id`,
    type: "String",
    value: privateNacl.id,
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
export const privateNaclId = privateNacl.id;
