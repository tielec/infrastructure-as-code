import * as pulumi from "@pulumi/pulumi";
import { createNetworkInfrastructure } from "./network";
import { createSecurityGroups } from "./security";
import { createLoadBalancer } from "./load-balancer";
import { createJenkinsInstance, createJenkinsEfs } from "./jenkins-controller";
import { createJenkinsAgentFleet, ensureAgentScriptFile } from "./jenkins-agent";

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

// セキュリティグループ
const securityGroups = createSecurityGroups(projectName, environment, network.vpc.id);

// ロードバランサー設定
const loadBalancer = createLoadBalancer(
    projectName, 
    environment, 
    network.vpc.id, 
    network.publicSubnets.map(subnet => subnet.id), 
    securityGroups.albSecurityGroup.id
);

// EFSファイルシステム作成
const jenkinsEfs = createJenkinsEfs(
    projectName,
    environment,
    network.vpc.id,
    securityGroups.jenkinsSecurityGroup.id,
    [network.privateSubnetA.id, network.privateSubnetB.id]
);

// Blueインスタンス（アクティブ環境）
const blueJenkins = createJenkinsInstance({
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

// 必要に応じてGreenインスタンス（スタンバイ環境）も作成可能
// コメントアウトを解除して使用
/*
const greenJenkins = createJenkinsInstance({
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
*/

// Jenkinsエージェント用のスポットフリート設定
const jenkinsAgents = createJenkinsAgentFleet({
    projectName: projectName,
    environment: environment,
    vpcId: network.vpc.id,
    subnetIds: [network.privateSubnetA.id, network.privateSubnetB.id],
    securityGroupId: securityGroups.jenkinsAgentSecurityGroup.id,
    instanceProfileArn: pulumi.interpolate`arn:aws:iam::${aws.getCallerIdentity().then(id => id.accountId)}:instance-profile/${projectName}-agent-profile-${environment}`,
    keyName: config.get("keyName"),
    maxTargetCapacity: config.getNumber("maxTargetCapacity") || 10,
    spotPrice: config.get("spotPrice") || "0.10"
});

// エクスポート
export const vpcId = network.vpc.id;
export const publicSubnetIds = network.publicSubnets.map(subnet => subnet.id);
export const privateSubnetIds = network.privateSubnets.map(subnet => subnet.id);
export const jenkinsSecurityGroupId = securityGroups.jenkinsSecurityGroup.id;
export const jenkinsAgentSecurityGroupId = securityGroups.jenkinsAgentSecurityGroup.id;
export const albDnsName = loadBalancer.albDnsName;
export const jenkinsEfsId = jenkinsEfs.efsFileSystem.id;
export const jenkinsInstanceId = blueJenkins.jenkinsInstance.id;
export const activeEnvironment = loadBalancer.activeEnvironmentParam.value;
export const spotFleetRequestId = jenkinsAgents.spotFleetRequest.id;
export const agentLaunchTemplateId = jenkinsAgents.launchTemplate.id;
