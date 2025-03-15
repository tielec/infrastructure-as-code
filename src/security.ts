import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import { dependsOn } from "./dependency-utils";

export function createSecurityGroups(
    projectName: string, 
    environment: string, 
    vpcId: pulumi.Input<string>,
    dependencies?: pulumi.Resource[]
) {
    // ALB用セキュリティグループ
    let albSecurityGroup = new aws.ec2.SecurityGroup(`${projectName}-alb-sg`, {
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
                cidrBlocks: ["0.0.0.0/0"], // または適切に制限
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
            Name: `${projectName}-alb-sg-${environment}`,
            Environment: environment,
        },
    });

    // 依存関係がある場合は別途設定
    if (dependencies && dependencies.length > 0) {
        albSecurityGroup = dependsOn(albSecurityGroup, dependencies);
    }

    // Jenkins マスター用セキュリティグループ
    let jenkinsSecurityGroup = new aws.ec2.SecurityGroup(`${projectName}-jenkins-sg`, {
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
            Name: `${projectName}-jenkins-master-sg-${environment}`,
            Environment: environment,
        },
    });

    // 依存関係を設定
    jenkinsSecurityGroup = dependsOn(jenkinsSecurityGroup, [albSecurityGroup, ...(dependencies || [])]);

    // Jenkinsエージェント用セキュリティグループ
    let jenkinsAgentSecurityGroup = new aws.ec2.SecurityGroup(`${projectName}-jenkins-agent-sg`, {
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
            Name: `${projectName}-jenkins-agent-sg-${environment}`,
            Environment: environment,
        },
    });

    // 依存関係を設定
    jenkinsAgentSecurityGroup = dependsOn(jenkinsAgentSecurityGroup, [jenkinsSecurityGroup, ...(dependencies || [])]);

    // EFS用セキュリティグループ
    let efsSecurityGroup = new aws.ec2.SecurityGroup(`${projectName}-efs-sg`, {
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
            Name: `${projectName}-efs-sg-${environment}`,
            Environment: environment,
        },
    });

    // 依存関係を設定
    efsSecurityGroup = dependsOn(efsSecurityGroup, [jenkinsSecurityGroup, jenkinsAgentSecurityGroup, ...(dependencies || [])]);

    return {
        albSecurityGroup,
        jenkinsSecurityGroup,
        jenkinsAgentSecurityGroup,
        efsSecurityGroup,
    };
}
