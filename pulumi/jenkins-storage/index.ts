/**
 * pulumi/storage/index.ts
 * 
 * Jenkinsインフラのストレージリソース（EFSファイルシステム、マウントターゲット等）を
 * 構築するPulumiスクリプト
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
const efsPerformanceModeParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/efs-performance-mode`,
});
const efsThroughputModeParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/efs-throughput-mode`,
});

// ネットワークリソースのSSMパラメータを取得
const vpcIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/vpc-id`,
});
const privateSubnetAIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/private-subnet-a-id`,
});
const privateSubnetBIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/private-subnet-b-id`,
});

// セキュリティグループのSSMパラメータを取得
const efsSecurityGroupIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/security/efs-sg-id`,
});

// 設定値を変数に設定
const projectName = pulumi.output(projectNameParam).apply(p => p.value);
const efsPerformanceMode = pulumi.output(efsPerformanceModeParam).apply(p => p.value as "generalPurpose" | "maxIO");
const efsThroughputMode = pulumi.output(efsThroughputModeParam).apply(p => p.value as "bursting" | "provisioned");

// ネットワークリソースIDを取得
const vpcId = pulumi.output(vpcIdParam).apply(p => p.value);
const privateSubnetAId = pulumi.output(privateSubnetAIdParam).apply(p => p.value);
const privateSubnetBId = pulumi.output(privateSubnetBIdParam).apply(p => p.value);
const efsSecurityGroupId = pulumi.output(efsSecurityGroupIdParam).apply(p => p.value);

// EFSファイルシステムの作成
const efsFileSystem = new aws.efs.FileSystem(`efs`, {
    encrypted: true,
    performanceMode: efsPerformanceMode,
    throughputMode: efsThroughputMode,
    tags: {
        Name: pulumi.interpolate`${projectName}-jenkins-efs-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
    lifecyclePolicies: [{
        transitionToIa: "AFTER_30_DAYS",
    }],
});

// マウントターゲットを個別に作成（削除順序を制御するため）
const mountTargetA = new aws.efs.MountTarget(`efs-mt-a`, {
    fileSystemId: efsFileSystem.id,
    subnetId: privateSubnetAId,
    securityGroups: [efsSecurityGroupId],
}, {
    // 明示的な依存関係と削除順序の設定
    dependsOn: [efsFileSystem],
    // 削除前にEFSファイルシステムが削除されないようにする
    deleteBeforeReplace: true,
});

const mountTargetB = new aws.efs.MountTarget(`efs-mt-b`, {
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
const jenkinsAccessPoint = new aws.efs.AccessPoint(`jenkins-ap`, {
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
        Name: pulumi.interpolate`${projectName}-jenkins-ap-${environment}`,
        Environment: environment,
    },
}, {
    // アクセスポイントも明示的に依存関係を設定
    dependsOn: [efsFileSystem, mountTargetA, mountTargetB],
});

// EFSファイルシステムIDをSSM Parameter Storeに保存
const efsFileSystemIdParameter = new aws.ssm.Parameter(`efs-id-param`, {
    name: `${ssmPrefix}/storage/efs-file-system-id`,
    type: "String",
    value: efsFileSystem.id,
    overwrite: true,
    description: `EFS File System ID for Jenkins ${environment}`,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "storage",
    },
});

// EFS DNS名をSSM Parameter Storeに保存
const efsFileSystemDnsParameter = new aws.ssm.Parameter(`efs-dns-param`, {
    name: `${ssmPrefix}/storage/efs-dns-name`,
    type: "String",
    value: pulumi.interpolate`${efsFileSystem.id}.efs.${aws.config.region}.amazonaws.com`,
    overwrite: true,
    description: `EFS DNS name for Jenkins ${environment}`,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "storage",
    },
});

// Jenkinsアクセスポイント情報もSSM Parameter Storeに保存
const jenkinsAccessPointIdParameter = new aws.ssm.Parameter(`jenkins-ap-id-param`, {
    name: `${ssmPrefix}/storage/jenkins-access-point-id`,
    type: "String",
    value: jenkinsAccessPoint.id,
    overwrite: true,
    description: `Jenkins EFS Access Point ID for ${environment}`,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "storage",
    },
});

// マウントターゲットIDをSSMに保存
const mountTargetAIdParam = new aws.ssm.Parameter(`mount-target-a-id`, {
    name: `${ssmPrefix}/storage/mount-target-a-id`,
    type: "String",
    value: mountTargetA.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "storage",
    },
});

const mountTargetBIdParam = new aws.ssm.Parameter(`mount-target-b-id`, {
    name: `${ssmPrefix}/storage/mount-target-b-id`,
    type: "String",
    value: mountTargetB.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "storage",
    },
});

// EFS ARNをSSMに保存
const efsFileSystemArnParam = new aws.ssm.Parameter(`efs-arn-param`, {
    name: `${ssmPrefix}/storage/efs-arn`,
    type: "String",
    value: efsFileSystem.arn,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "storage",
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
