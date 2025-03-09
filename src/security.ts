import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

export function createSecurityGroups(projectName: string, environment: string, vpcId: pulumi.Input<string>) {
    // Jenkins マスター用セキュリティグループ
    const jenkinsSecurityGroup = new aws.ec2.SecurityGroup(`${projectName}-jenkins-sg`, {
        vpcId: vpcId,
        description: "Security group for Jenkins master instances",
        ingress: [
            // Jenkins Web UI
            {
                protocol: "tcp",
                fromPort: 8080,
                toPort: 8080,
                cidrBlocks: ["0.0.0.0/0"],
                description: "Jenkins Web UI access",
            },
            // SSH アクセス
            {
                protocol: "tcp",
                fromPort: 22,
                toPort: 22,
                cidrBlocks: ["0.0.0.0/0"],
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
            Name: `${projectName}-jenkins-master-sg-${environment}`,
            Environment: environment,
        },
    });

    // Jenkinsエージェント用セキュリティグループ
    const jenkinsAgentSecurityGroup = new aws.ec2.SecurityGroup(`${projectName}-jenkins-agent-sg`, {
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
            Name: `${projectName}-jenkins-agent-sg-${environment}`,
            Environment: environment,
        },
    });

    return {
        jenkinsSecurityGroup,
        jenkinsAgentSecurityGroup,
    };
}