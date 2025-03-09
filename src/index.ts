import * as pulumi from "@pulumi/pulumi";
import { createNetworkInfrastructure } from "./network";
import { createSecurityGroups } from "./security";

// 共通設定
const config = new pulumi.Config();
const projectName = config.get("projectName") || "jenkins-infra";
const environment = pulumi.getStack();

// ネットワークインフラ構築
const network = createNetworkInfrastructure(projectName, environment);

// セキュリティグループ
const securityGroups = createSecurityGroups(projectName, environment, network.vpc.id);

// エクスポート
export const vpcId = network.vpc.id;
export const publicSubnetId = network.publicSubnet.id;
export const privateSubnetId = network.privateSubnet.id;
export const jenkinsSecurityGroupId = securityGroups.jenkinsSecurityGroup.id;