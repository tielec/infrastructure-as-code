import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import { createNetworkInfrastructure } from "./network";
import { createSecurityGroups } from "./security";
import { createLoadBalancer } from "./load-balancer";
import { createJenkinsInstance, createJenkinsEfs } from "./jenkins-controller";
import { createJenkinsAgentFleet, ensureAgentScriptFile } from "./jenkins-agent";
import { dependsOn } from "./dependency-utils";

// 共通設定
const config = new pulumi.Config();
const projectName = config.get("projectName") || "jenkins-infra";
const environment = pulumi.getStack();
const jenkinsVersion = config.get("jenkinsVersion") || "latest";  // デフォルトは最新バージョン
const recoveryMode = config.getBoolean("recoveryMode") || false;   // デフォルトは通常モード

// セットアップスクリプトが存在することを確認
ensureAgentScriptFile();

// ネットワークインフラ構築
const network = createNetworkInfrastructure(projectName, environment);

// 依存関係のあるネットワークリソースを整理
const networkDependencies = [
    network.vpc,
    ...network.publicSubnets,
    ...network.privateSubnets,
    network.igw,
    ...network.routeTables,
    ...network.natGateways,
];

// セキュリティグループ（ネットワークリソースの作成完了後に作成する）
const securityGroups = createSecurityGroups(
    projectName, 
    environment, 
    network.vpc.id, 
    networkDependencies
);

// ロードバランサー設定（VPCとセキュリティグループが作成された後に作成）
const loadBalancer = createLoadBalancer(
    projectName, 
    environment, 
    network.vpc.id, 
    network.publicSubnets.map(subnet => subnet.id), 
    securityGroups.albSecurityGroup.id,
    [...networkDependencies, securityGroups.albSecurityGroup]
);

// EFSファイルシステム作成（VPCとセキュリティグループが作成された後に作成）
const jenkinsEfs = createJenkinsEfs(
    projectName,
    environment,
    network.vpc.id,
    securityGroups.efsSecurityGroup.id,  // Jenkinsではなく、EFS用のセキュリティグループを使用
    [network.privateSubnetA.id, network.privateSubnetB.id],
    [...networkDependencies, securityGroups.jenkinsSecurityGroup, securityGroups.efsSecurityGroup]
);

// EFSマウントターゲットを配列で取得
const efsMountTargets = jenkinsEfs.mountTargets;

// Blueインスタンス（アクティブ環境）- 依存リソースがすべて作成された後に作成
const blueJenkinsInstance = createJenkinsInstance({
    projectName: projectName,
    environment: environment,
    vpcId: network.vpc.id,
    subnetId: network.privateSubnetA.id,
    securityGroupId: securityGroups.jenkinsSecurityGroup.id,
    targetGroupArn: loadBalancer.blueTargetGroup.arn,
    efsFileSystemId: jenkinsEfs.efsFileSystem.id,
    efsAccessPointId: jenkinsEfs.jenkinsAccessPoint.id,
    jenkinsVersion: jenkinsVersion,
    recoveryMode: recoveryMode,
    color: "blue"
});

// 明示的に依存関係を設定（各リソースに対して）
dependsOn(blueJenkinsInstance.jenkinsInstance, [
    ...efsMountTargets,
    securityGroups.jenkinsSecurityGroup,
    loadBalancer.blueTargetGroup,
    jenkinsEfs.jenkinsAccessPoint
]);

// 必要に応じてGreenインスタンス（スタンバイ環境）も作成可能
// コメントアウトを解除して使用
/*
const greenJenkinsInstance = createJenkinsInstance({
    projectName: projectName,
    environment: environment,
    vpcId: network.vpc.id,
    subnetId: network.privateSubnetB.id,
    securityGroupId: securityGroups.jenkinsSecurityGroup.id,
    targetGroupArn: loadBalancer.greenTargetGroup.arn,
    efsFileSystemId: jenkinsEfs.efsFileSystem.id,
    efsAccessPointId: jenkinsEfs.jenkinsAccessPoint.id,
    jenkinsVersion: jenkinsVersion,
    recoveryMode: true,  // 必要に応じてリカバリーモードを有効化
    color: "green"
});

// 明示的に依存関係を設定（各リソースに対して）
dependsOn(greenJenkinsInstance.jenkinsInstance, [
    ...efsMountTargets,
    securityGroups.jenkinsSecurityGroup,
    loadBalancer.greenTargetGroup,
    jenkinsEfs.jenkinsAccessPoint
]);
*/

// Jenkinsエージェント用のスポットフリート設定 - すべての依存リソースが作成された後に作成
const jenkinsAgents = createJenkinsAgentFleet({
    projectName: projectName,
    environment: environment,
    vpcId: network.vpc.id,
    subnetIds: [network.privateSubnetA.id, network.privateSubnetB.id],
    securityGroupId: securityGroups.jenkinsAgentSecurityGroup.id,
    keyName: config.get("keyName"),
    maxTargetCapacity: config.getNumber("maxTargetCapacity") || 10,
    spotPrice: config.get("spotPrice") || "0.10"
});

// 明示的に依存関係を設定
if (jenkinsAgents.agentRole) {
    dependsOn(jenkinsAgents.agentRole, [
        ...networkDependencies,
        securityGroups.jenkinsAgentSecurityGroup
    ]);
}

if (jenkinsAgents.spotFleetRequest) {
    dependsOn(jenkinsAgents.spotFleetRequest, [
        jenkinsAgents.launchTemplate,
        jenkinsAgents.spotFleetRole
    ]);
}

// エクスポート
export const vpcId = network.vpc.id;
export const publicSubnetIds = network.publicSubnets.map(subnet => subnet.id);
export const privateSubnetIds = network.privateSubnets.map(subnet => subnet.id);
export const jenkinsSecurityGroupId = securityGroups.jenkinsSecurityGroup.id;
export const jenkinsAgentSecurityGroupId = securityGroups.jenkinsAgentSecurityGroup.id;
export const albDnsName = loadBalancer.albDnsName;
export const jenkinsEfsId = jenkinsEfs.efsFileSystem.id;
export const jenkinsInstanceId = blueJenkinsInstance.jenkinsInstance.id;
export const activeEnvironment = loadBalancer.activeEnvironmentParam.value;
export const agentRoleArn = jenkinsAgents.agentRole?.arn;
export const agentProfileArn = jenkinsAgents.agentProfile?.arn;
export const spotFleetRequestId = jenkinsAgents.spotFleetRequest?.id;
export const agentLaunchTemplateId = jenkinsAgents.launchTemplate.id;
