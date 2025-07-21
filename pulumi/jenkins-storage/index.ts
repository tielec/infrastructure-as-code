/**
 * pulumi/storage/index.ts
 * 
 * Jenkinsインフラのストレージリソース（EFSファイルシステム、マウントターゲット等）を
 * 構築するPulumiスクリプト
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "jenkins-infra";
const environment = pulumi.getStack();

// ネットワークスタック名とセキュリティスタック名を設定から取得
const networkStackName = config.get("networkStackName") || "jenkins-network";
const securityStackName = config.get("securityStackName") || "jenkins-security";

// 既存のネットワークスタックとセキュリティスタックから値を取得
const networkStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${networkStackName}/${environment}`);
const securityStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${securityStackName}/${environment}`);

// VPC IDとプライベートサブネットIDを取得
const vpcId = networkStack.getOutput("vpcId");
const privateSubnetIds = networkStack.getOutput("privateSubnetIds");
const privateSubnetAId = networkStack.getOutput("privateSubnetAId");
const privateSubnetBId = networkStack.getOutput("privateSubnetBId");

// EFSセキュリティグループIDを取得
const efsSecurityGroupId = securityStack.getOutput("efsSecurityGroupId");

// EFSファイルシステムの作成
const efsFileSystem = new aws.efs.FileSystem(`${projectName}-efs`, {
    encrypted: true,
    performanceMode: "generalPurpose",
    throughputMode: "bursting",
    tags: {
        Name: `${projectName}-jenkins-efs-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
    lifecyclePolicies: [{
        transitionToIa: "AFTER_30_DAYS",
    }],
});

// マウントターゲットを個別に作成（削除順序を制御するため）
const mountTargetA = new aws.efs.MountTarget(`${projectName}-efs-mt-a`, {
    fileSystemId: efsFileSystem.id,
    subnetId: privateSubnetAId,
    securityGroups: [efsSecurityGroupId],
}, {
    // 明示的な依存関係と削除順序の設定
    dependsOn: [efsFileSystem],
    // 削除前にEFSファイルシステムが削除されないようにする
    deleteBeforeReplace: true,
});

const mountTargetB = new aws.efs.MountTarget(`${projectName}-efs-mt-b`, {
    fileSystemId: efsFileSystem.id,
    subnetId: privateSubnetBId,
    securityGroups: [efsSecurityGroupId],
}, {
    // 明示的な依存関係と削除順序の設定
    dependsOn: [efsFileSystem],
    // 削除前にEFSファイルシステムが削除されないようにする
    deleteBeforeReplace: true,
});

// EFSアクセスポイント (Jenkinsホームディレクトリ用)
const jenkinsAccessPoint = new aws.efs.AccessPoint(`${projectName}-jenkins-ap`, {
    fileSystemId: efsFileSystem.id,
    posixUser: {
        gid: 994,  // Jenkinsのgid
        uid: 994,  // Jenkinsのuid
    },
    rootDirectory: {
        path: "/jenkins-home",
        creationInfo: {
            ownerGid: 994,
            ownerUid: 994,
            permissions: "755",
        },
    },
    tags: {
        Name: `${projectName}-jenkins-ap-${environment}`,
        Environment: environment,
    },
}, {
    // アクセスポイントも明示的に依存関係を設定
    dependsOn: [efsFileSystem, mountTargetA, mountTargetB],
});

// EFSファイルシステムIDをSSM Parameter Storeに保存
const efsFileSystemIdParameter = new aws.ssm.Parameter(`${projectName}-efs-id-param`, {
    name: `/${projectName}/${environment}/storage/efsFileSystemId`,
    type: "String",
    value: efsFileSystem.id,
    description: `EFS File System ID for Jenkins ${environment}`,
    tags: {
        Name: `${projectName}-efs-id-param-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// EFS DNS名をSSM Parameter Storeに保存
const efsFileSystemDnsParameter = new aws.ssm.Parameter(`${projectName}-efs-dns-param`, {
    name: `/${projectName}/${environment}/storage/efsFileSystemDns`,
    type: "String",
    value: pulumi.interpolate`${efsFileSystem.id}.efs.${aws.config.region}.amazonaws.com`,
    description: `EFS DNS name for Jenkins ${environment}`,
    tags: {
        Name: `${projectName}-efs-dns-param-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// Jenkinsアクセスポイント情報もSSM Parameter Storeに保存
const jenkinsAccessPointIdParameter = new aws.ssm.Parameter(`${projectName}-jenkins-ap-id-param`, {
    name: `/${projectName}/${environment}/storage/jenkinsAccessPointId`,
    type: "String",
    value: jenkinsAccessPoint.id,
    description: `Jenkins EFS Access Point ID for ${environment}`,
    tags: {
        Name: `${projectName}-jenkins-ap-id-param-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// エクスポート
export const efsFileSystemId = efsFileSystem.id;
export const efsFileSystemArn = efsFileSystem.arn;
export const efsFileSystemDnsName = pulumi.interpolate`${efsFileSystem.id}.efs.${aws.config.region}.amazonaws.com`;
export const jenkinsAccessPointId = jenkinsAccessPoint.id;
export const jenkinsAccessPointArn = jenkinsAccessPoint.arn;
export const mountTargetAId = mountTargetA.id;
export const mountTargetBId = mountTargetB.id;

// SSM Parameterのエクスポート（確認用）
export const ssmParameters = {
    efsFileSystemId: efsFileSystemIdParameter.name,
    efsFileSystemDns: efsFileSystemDnsParameter.name,
    jenkinsAccessPointId: jenkinsAccessPointIdParameter.name,
};
