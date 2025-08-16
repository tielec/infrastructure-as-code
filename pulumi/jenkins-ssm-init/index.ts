/**
 * pulumi/jenkins-ssm-init/index.ts
 * 
 * SSMパラメータストアの初期化設定を管理するPulumiスクリプト
 * すべてのJenkinsインフラ設定の基本パラメータを定義
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// 環境名をスタック名から取得
const environment = pulumi.getStack();

// 基本設定値の定義
const projectName = "jenkins-infra";
const ssmPrefix = `/${projectName}/${environment}`;

// 基本設定パラメータをSSMに保存
const projectNameParam = new aws.ssm.Parameter("project-name", {
    name: `${ssmPrefix}/config/project-name`,
    type: "String",
    value: projectName,
    overwrite: true,
    description: "Project name for Jenkins infrastructure",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

const environmentParam = new aws.ssm.Parameter("environment", {
    name: `${ssmPrefix}/config/environment`,
    type: "String",
    value: environment,
    overwrite: true,
    description: "Environment name",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// ネットワーク設定
const vpcCidrParam = new aws.ssm.Parameter("vpc-cidr", {
    name: `${ssmPrefix}/config/vpc-cidr`,
    type: "String",
    value: "10.0.0.0/16",
    overwrite: true,
    description: "VPC CIDR block",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// NAT設定
const natHighAvailabilityParam = new aws.ssm.Parameter("nat-high-availability", {
    name: `${ssmPrefix}/config/nat-high-availability`,
    type: "String",
    value: "false",  // dev環境ではfalse、prodではtrueに設定
    overwrite: true,
    description: "Use NAT Gateway (true) or NAT Instance (false)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

const natInstanceTypeParam = new aws.ssm.Parameter("nat-instance-type", {
    name: `${ssmPrefix}/config/nat-instance-type`,
    type: "String",
    value: "t4g.nano",
    overwrite: true,
    description: "NAT instance type (when not using NAT Gateway)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// Jenkins設定
const jenkinsVersionParam = new aws.ssm.Parameter("jenkins-version", {
    name: `${ssmPrefix}/config/jenkins-version`,
    type: "String",
    value: "latest",
    overwrite: true,
    description: "Jenkins version to install",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

const jenkinsColorParam = new aws.ssm.Parameter("jenkins-color", {
    name: `${ssmPrefix}/config/jenkins-color`,
    type: "String",
    value: "blue",
    overwrite: true,
    description: "Jenkins deployment color (blue/green)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

const jenkinsRecoveryModeParam = new aws.ssm.Parameter("jenkins-recovery-mode", {
    name: `${ssmPrefix}/config/jenkins-recovery-mode`,
    type: "String",
    value: "false",
    overwrite: true,
    description: "Enable Jenkins recovery mode",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// EC2設定
const keyNameParam = new aws.ssm.Parameter("key-name", {
    name: `${ssmPrefix}/config/key-name`,
    type: "String",
    value: "",  // 必要に応じて設定
    overwrite: true,
    description: "EC2 key pair name for SSH access",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// Jenkins Controller設定
const controllerInstanceTypeParam = new aws.ssm.Parameter("controller-instance-type", {
    name: `${ssmPrefix}/config/controller-instance-type`,
    type: "String",
    value: "t3.medium",
    overwrite: true,
    description: "Jenkins controller EC2 instance type",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// Jenkins Agent設定
const agentInstanceTypeParam = new aws.ssm.Parameter("agent-instance-type", {
    name: `${ssmPrefix}/config/agent-instance-type`,
    type: "String",
    value: "t3.medium",
    overwrite: true,
    description: "Jenkins agent EC2 instance type",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

const agentMinCapacityParam = new aws.ssm.Parameter("agent-min-capacity", {
    name: `${ssmPrefix}/config/agent-min-capacity`,
    type: "String",
    value: "0",
    overwrite: true,
    description: "Minimum number of Jenkins agents",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

const agentMaxCapacityParam = new aws.ssm.Parameter("agent-max-capacity", {
    name: `${ssmPrefix}/config/agent-max-capacity`,
    type: "String",
    value: "10",
    overwrite: true,
    description: "Maximum number of Jenkins agents",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

const agentSpotPriceParam = new aws.ssm.Parameter("agent-spot-price", {
    name: `${ssmPrefix}/config/agent-spot-price`,
    type: "String",
    value: "0.10",
    overwrite: true,
    description: "Maximum spot price for Jenkins agents",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// Git設定
const gitRepoParam = new aws.ssm.Parameter("git-repo", {
    name: `${ssmPrefix}/config/git-repo`,
    type: "String",
    value: "",  // 必要に応じて設定
    overwrite: true,
    description: "Git repository URL for Jenkins configuration",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

const gitBranchParam = new aws.ssm.Parameter("git-branch", {
    name: `${ssmPrefix}/config/git-branch`,
    type: "String",
    value: "main",
    overwrite: true,
    description: "Git branch for Jenkins configuration",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// ALB設定
const albIdleTimeoutParam = new aws.ssm.Parameter("alb-idle-timeout", {
    name: `${ssmPrefix}/config/alb-idle-timeout`,
    type: "String",
    value: "300",
    overwrite: true,
    description: "ALB idle timeout in seconds",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// EFS設定
const efsPerformanceModeParam = new aws.ssm.Parameter("efs-performance-mode", {
    name: `${ssmPrefix}/config/efs-performance-mode`,
    type: "String",
    value: "generalPurpose",
    overwrite: true,
    description: "EFS performance mode (generalPurpose or maxIO)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

const efsThroughputModeParam = new aws.ssm.Parameter("efs-throughput-mode", {
    name: `${ssmPrefix}/config/efs-throughput-mode`,
    type: "String",
    value: "bursting",
    overwrite: true,
    description: "EFS throughput mode (bursting or provisioned)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// エクスポート
export const ssmPrefixOutput = ssmPrefix;
export const projectNameOutput = projectName;
export const environmentOutput = environment;