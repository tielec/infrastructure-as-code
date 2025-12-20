/**
 * pulumi/jenkins-ssm-init/index.ts
 * 
 * SSMパラメータストアの初期化設定を管理するPulumiスクリプト
 * すべてのJenkinsインフラ設定の基本パラメータを定義
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as random from "@pulumi/random";

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

// IPv6設定
const ipv6EnabledParam = new aws.ssm.Parameter("ipv6-enabled", {
    name: `${ssmPrefix}/config/ipv6-enabled`,
    type: "String",
    value: "true",
    overwrite: true,
    description: "Enable IPv6 dual-stack configuration",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

const useEgressOnlyGatewayParam = new aws.ssm.Parameter("use-egress-only-gateway", {
    name: `${ssmPrefix}/config/use-egress-only-gateway`,
    type: "String",
    value: "true",
    overwrite: true,
    description: "Use Egress-only Internet Gateway for IPv6 outbound traffic",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// NAT設定（IPv6とのハイブリッド構成）
const natHighAvailabilityParam = new aws.ssm.Parameter("nat-high-availability", {
    name: `${ssmPrefix}/config/nat-high-availability`,
    type: "String",
    value: "false",  // 通常モード（NATインスタンス1台）
    overwrite: true,
    description: "NAT high availability mode (false = single NAT instance)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

const natInstanceTypeParam = new aws.ssm.Parameter("nat-instance-type", {
    name: `${ssmPrefix}/config/nat-instance-type`,
    type: "String",
    value: "t4g.nano",  // ARM64ベースの最小インスタンス（コスト最適化）
    overwrite: true,
    description: "NAT instance type for IPv4 outbound traffic",
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
// 注: 実際のキーペア名を設定するか、SSHアクセスが不要な場合は"none"のままにしてください
const keyNameParam = new aws.ssm.Parameter("key-name", {
    name: `${ssmPrefix}/config/key-name`,
    type: "String",
    value: "none",  // EC2キーペア名（SSHアクセスが必要な場合は実際のキーペア名を設定）
    overwrite: true,
    description: "EC2 key pair name for SSH access (set to 'none' if SSH access not needed)",
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
    value: "t4g.medium",  // ARM64 instance type
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
    value: "t4g.medium",  // ARM64 instance type
    overwrite: true,
    description: "Jenkins agent EC2 instance type",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// 後方互換性のための既存パラメータ（medium用として継続使用）
const agentMinCapacityParam = new aws.ssm.Parameter("agent-min-capacity", {
    name: `${ssmPrefix}/config/agent-min-capacity`,
    type: "String",
    value: "0",
    overwrite: true,
    description: "Minimum number of Jenkins agents (legacy, same as medium)",
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
    description: "Maximum number of Jenkins agents (legacy, same as medium)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// Medium インスタンス用のキャパシティ設定（明示的）
const agentMediumMinCapacityParam = new aws.ssm.Parameter("agent-medium-min-capacity", {
    name: `${ssmPrefix}/config/agent-medium-min-capacity`,
    type: "String",
    value: "0",
    overwrite: true,
    description: "Minimum number of Jenkins agents (medium instances)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

const agentMediumMaxCapacityParam = new aws.ssm.Parameter("agent-medium-max-capacity", {
    name: `${ssmPrefix}/config/agent-medium-max-capacity`,
    type: "String",
    value: "10",
    overwrite: true,
    description: "Maximum number of Jenkins agents (medium instances)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// Small インスタンス用のキャパシティ設定
const agentSmallMinCapacityParam = new aws.ssm.Parameter("agent-small-min-capacity", {
    name: `${ssmPrefix}/config/agent-small-min-capacity`,
    type: "String",
    value: "0",
    overwrite: true,
    description: "Minimum number of Jenkins agents (small instances)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

const agentSmallMaxCapacityParam = new aws.ssm.Parameter("agent-small-max-capacity", {
    name: `${ssmPrefix}/config/agent-small-max-capacity`,
    type: "String",
    value: "10",
    overwrite: true,
    description: "Maximum number of Jenkins agents (small instances)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// Micro インスタンス用のキャパシティ設定
const agentMicroMinCapacityParam = new aws.ssm.Parameter("agent-micro-min-capacity", {
    name: `${ssmPrefix}/config/agent-micro-min-capacity`,
    type: "String",
    value: "0",
    overwrite: true,
    description: "Minimum number of Jenkins agents (micro instances)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

const agentMicroMaxCapacityParam = new aws.ssm.Parameter("agent-micro-max-capacity", {
    name: `${ssmPrefix}/config/agent-micro-max-capacity`,
    type: "String",
    value: "10",
    overwrite: true,
    description: "Maximum number of Jenkins agents (micro instances)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// 後方互換性のための既存パラメータ（medium用として継続使用）
const agentSpotPriceParam = new aws.ssm.Parameter("agent-spot-price", {
    name: `${ssmPrefix}/config/agent-spot-price`,
    type: "String",
    value: "0.027",  // 50% of t3.medium on-demand price (~$0.054)
    overwrite: true,
    description: "Maximum spot price for Jenkins agents (legacy, same as medium)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// Medium インスタンス用のスポット価格設定（明示的）
const agentSpotPriceMediumParam = new aws.ssm.Parameter("agent-spot-price-medium", {
    name: `${ssmPrefix}/config/agent-spot-price-medium`,
    type: "String",
    value: "0.027",  // 50% of t3.medium on-demand price (~$0.054)
    overwrite: true,
    description: "Maximum spot price for Jenkins agents (medium instances)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// Small インスタンス用のスポット価格設定
const agentSpotPriceSmallParam = new aws.ssm.Parameter("agent-spot-price-small", {
    name: `${ssmPrefix}/config/agent-spot-price-small`,
    type: "String",
    value: "0.014",  // 50% of t3.small on-demand price (~$0.027)
    overwrite: true,
    description: "Maximum spot price for Jenkins agents (small instances)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// Micro インスタンス用のスポット価格設定
const agentSpotPriceMicroParam = new aws.ssm.Parameter("agent-spot-price-micro", {
    name: `${ssmPrefix}/config/agent-spot-price-micro`,
    type: "String",
    value: "0.007",  // 50% of t3.micro on-demand price (~$0.014)
    overwrite: true,
    description: "Maximum spot price for Jenkins agents (micro instances)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// インスタンスサイズ別のIdle Minutes設定
// Medium インスタンス用のIdle Minutes（明示的）
const agentIdleMinutesMediumParam = new aws.ssm.Parameter("agent-idle-minutes-medium", {
    name: `${ssmPrefix}/config/agent-idle-minutes-medium`,
    type: "String",
    value: "15",
    overwrite: true,
    description: "Idle minutes before scaledown for Jenkins agent (medium instances)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// Small インスタンス用のIdle Minutes
const agentIdleMinutesSmallParam = new aws.ssm.Parameter("agent-idle-minutes-small", {
    name: `${ssmPrefix}/config/agent-idle-minutes-small`,
    type: "String",
    value: "10",
    overwrite: true,
    description: "Idle minutes before scaledown for Jenkins agent (small instances)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// Micro インスタンス用のIdle Minutes
const agentIdleMinutesMicroParam = new aws.ssm.Parameter("agent-idle-minutes-micro", {
    name: `${ssmPrefix}/config/agent-idle-minutes-micro`,
    type: "String",
    value: "5",
    overwrite: true,
    description: "Idle minutes before scaledown for Jenkins agent (micro instances)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// インスタンスサイズ別のExecutor数設定
// Medium インスタンス用のExecutor数（明示的）
const agentNumExecutorsMediumParam = new aws.ssm.Parameter("agent-num-executors-medium", {
    name: `${ssmPrefix}/config/agent-num-executors-medium`,
    type: "String",
    value: "3",
    overwrite: true,
    description: "Number of executors per Jenkins agent (medium instances)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// Small インスタンス用のExecutor数
const agentNumExecutorsSmallParam = new aws.ssm.Parameter("agent-num-executors-small", {
    name: `${ssmPrefix}/config/agent-num-executors-small`,
    type: "String",
    value: "2",
    overwrite: true,
    description: "Number of executors per Jenkins agent (small instances)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// Micro インスタンス用のExecutor数
const agentNumExecutorsMicroParam = new aws.ssm.Parameter("agent-num-executors-micro", {
    name: `${ssmPrefix}/config/agent-num-executors-micro`,
    type: "String",
    value: "1",
    overwrite: true,
    description: "Number of executors per Jenkins agent (micro instances)",
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
    value: "https://github.com/tielec/infrastructure-as-code",
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

// Jenkins Adminユーザーのパスワード生成
const adminPassword = new random.RandomPassword("jenkins-admin-password", {
    length: 16,
    special: true,
    overrideSpecial: "_%@[]()<>?",
});

// 生成したパスワードをSSMに保存
const adminPasswordParam = new aws.ssm.Parameter("jenkins-admin-password-param", {
    name: `${ssmPrefix}/jenkins/admin-password`,
    type: "SecureString",
    value: adminPassword.result,
    overwrite: true,
    description: "Password for the Jenkins admin user",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "jenkins-auth",
    },
});

// Jenkins CLIユーザーのパスワード生成
const cliPassword = new random.RandomPassword("jenkins-cli-password", {
    length: 20,
    special: true,
    overrideSpecial: "_%@[]()<>?",
});

// CLIユーザーのパスワードをSSMに保存
const cliPasswordParam = new aws.ssm.Parameter("jenkins-cli-password-param", {
    name: `${ssmPrefix}/jenkins/cli-password`,
    type: "SecureString",
    value: cliPassword.result,
    overwrite: true,
    description: "Password for the Jenkins CLI user",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "jenkins-auth",
    },
});

// エクスポート
export const ssmPrefixOutput = ssmPrefix;
export const projectNameOutput = projectName;
export const environmentOutput = environment;

// セキュアな値のパス情報のみエクスポート（実際の値はエクスポートしない）
export const adminPasswordPath = adminPasswordParam.name;
export const cliPasswordPath = cliPasswordParam.name;