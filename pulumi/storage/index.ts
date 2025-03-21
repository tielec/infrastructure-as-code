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

// EFSマウントターゲットの作成 (プライベートサブネットに1つずつ)
const mountTargets = pulumi.all([privateSubnetAId, privateSubnetBId, efsSecurityGroupId])
    .apply(([subnetA, subnetB, securityGroupId]) => {
        const targets = [];
        
        // サブネットAのマウントターゲット
        targets.push(new aws.efs.MountTarget(`${projectName}-efs-mt-a`, {
            fileSystemId: efsFileSystem.id,
            subnetId: subnetA,
            securityGroups: [securityGroupId],
        }));
        
        // サブネットBのマウントターゲット
        targets.push(new aws.efs.MountTarget(`${projectName}-efs-mt-b`, {
            fileSystemId: efsFileSystem.id,
            subnetId: subnetB,
            securityGroups: [securityGroupId],
        }));
        
        return targets;
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
});

// エクスポート
export const efsFileSystemId = efsFileSystem.id;
export const efsFileSystemArn = efsFileSystem.arn;
export const efsFileSystemDnsName = pulumi.interpolate`${efsFileSystem.id}.efs.${aws.config.region}.amazonaws.com`;
export const jenkinsAccessPointId = jenkinsAccessPoint.id;
export const jenkinsAccessPointArn = jenkinsAccessPoint.arn;

// マウントターゲットIDのエクスポート - 型定義を追加
export const mountTargetA = mountTargets.apply((targets: aws.efs.MountTarget[]) => targets[0].id);
export const mountTargetB = mountTargets.apply((targets: aws.efs.MountTarget[]) => targets[1].id);
