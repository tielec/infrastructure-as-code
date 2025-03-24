/**
 * pulumi/agent/index.ts
 * 
 * Jenkinsインフラのエージェントリソースを構築するPulumiスクリプト
 * Spot Fleetリクエスト、EC2起動テンプレート、IAMロールなどを作成
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "jenkins-infra";
const environment = pulumi.getStack();

// スタック参照名を設定から取得
const networkStackName = config.get("networkStackName") || "jenkins-network";
const securityStackName = config.get("securityStackName") || "jenkins-security";

// エージェント固有の設定を取得
const maxTargetCapacity = config.getNumber("maxTargetCapacity") || 10;
const minTargetCapacity = config.getNumber("minTargetCapacity") || 0;
const spotPrice = config.get("spotPrice") || "0.10";
const instanceType = config.get("instanceType") || "t3.medium";
const keyName = config.get("keyName");

// 既存のスタックから値を取得
const networkStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${networkStackName}/${environment}`);
const securityStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${securityStackName}/${environment}`);

// 必要なリソースIDを取得
const vpcId = networkStack.getOutput("vpcId");
const privateSubnetIds = networkStack.getOutput("privateSubnetIds");
const jenkinsAgentSecurityGroupId = securityStack.getOutput("jenkinsAgentSecurityGroupId");

// 最新のAmazon Linux 2023 AMIを取得
const ami = aws.ec2.getAmi({
    mostRecent: true,
    owners: ["amazon"],
    filters: [{
        name: "name",
        values: ["al2023-ami-*-kernel-*-x86_64"],
    }],
});

// IAMロール作成（Jenkinsエージェント用）
const jenkinsAgentRole = new aws.iam.Role(`${projectName}-agent-role`, {
    assumeRolePolicy: JSON.stringify({
        Version: "2012-10-17",
        Statement: [{
            Action: "sts:AssumeRole",
            Effect: "Allow",
            Principal: {
                Service: "ec2.amazonaws.com",
            },
        }],
    }),
    tags: {
        Name: `${projectName}-agent-role-${environment}`,
        Environment: environment,
    },
});

// マネージドポリシーのアタッチ
const ssmPolicy = new aws.iam.RolePolicyAttachment(`${projectName}-agent-ssm-policy`, {
    role: jenkinsAgentRole.name,
    policyArn: "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
});

const efsPolicy = new aws.iam.RolePolicyAttachment(`${projectName}-agent-efs-policy`, {
    role: jenkinsAgentRole.name,
    policyArn: "arn:aws:iam::aws:policy/AmazonElasticFileSystemClientReadWriteAccess",
});

// ECRとS3アクセス権限（ビルドアーティファクト用）
const buildResourcesPolicy = new aws.iam.Policy(`${projectName}-agent-build-policy`, {
    description: "Policy for Jenkins agent to access build resources",
    policy: JSON.stringify({
        Version: "2012-10-17",
        Statement: [
            {
                Effect: "Allow",
                Action: [
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:InitiateLayerUpload",
                    "ecr:UploadLayerPart",
                    "ecr:CompleteLayerUpload",
                    "ecr:PutImage"
                ],
                Resource: "*"
            },
            {
                Effect: "Allow",
                Action: [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket"
                ],
                Resource: [
                    `arn:aws:s3:::${projectName}-artifacts-${environment}*`,
                    `arn:aws:s3:::${projectName}-artifacts-${environment}*/*`
                ]
            }
        ]
    }),
});

const buildResourcesPolicyAttachment = new aws.iam.RolePolicyAttachment(
    `${projectName}-agent-build-policy-attachment`, 
    {
        role: jenkinsAgentRole.name,
        policyArn: buildResourcesPolicy.arn,
    }
);

// Jenkins用インスタンスプロファイル
const jenkinsAgentProfile = new aws.iam.InstanceProfile(
    `${projectName}-agent-profile`, 
    {
        role: jenkinsAgentRole.name,
        tags: {
            Environment: environment,
        },
    }
);

// SpotFleet用IAMロール
const spotFleetRole = new aws.iam.Role(`${projectName}-spotfleet-role`, {
    name: `${projectName}-spotfleet-role-${environment}`,
    assumeRolePolicy: JSON.stringify({
        Version: "2012-10-17",
        Statement: [{
            Effect: "Allow",
            Principal: {
                Service: "spotfleet.amazonaws.com",
            },
            Action: "sts:AssumeRole",
        }],
    }),
    managedPolicyArns: [
        "arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetTaggingRole",
    ],
    tags: {
        Name: `${projectName}-spotfleet-role-${environment}`,
        Environment: environment,
    },
});

// エージェント起動テンプレート
const agentLaunchTemplate = new aws.ec2.LaunchTemplate(`${projectName}-agent-lt`, {
    namePrefix: `${projectName}-agent-lt-`,
    imageId: ami.then(ami => ami.id),
    instanceType: instanceType,
    keyName: keyName,
    vpcSecurityGroupIds: [jenkinsAgentSecurityGroupId],
    iamInstanceProfile: {
        name: jenkinsAgentProfile.name,
    },
    blockDeviceMappings: [{
        deviceName: "/dev/xvda",
        ebs: {
            volumeSize: 30,
            volumeType: "gp3",
            deleteOnTermination: true,
            encrypted: true,
        },
    }],
    metadataOptions: {
        httpEndpoint: "enabled",
        httpTokens: "required",
        httpPutResponseHopLimit: 2,
    },
    tagSpecifications: [{
        resourceType: "instance",
        tags: {
            Name: `${projectName}-agent-${environment}`,
            Environment: environment,
            Role: "jenkins-agent",
        },
    }],
    // ユーザーデータをBase64エンコード
    userData: pulumi.output(`#!/bin/bash
# Jenkins Agent Bootstrap Script
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
set -x

# システムのアップデートと必要なパッケージのインストール（Javaを除く）
dnf update -y
dnf install -y docker git jq amazon-ssm-agent

# Dockerの設定と起動
systemctl enable docker
systemctl start docker

# Jenkinsユーザーの作成
useradd -m -d /home/jenkins -s /bin/bash jenkins
usermod -aG docker jenkins

# エージェント作業ディレクトリの設定
mkdir -p /home/jenkins/agent
chown -R jenkins:jenkins /home/jenkins

# 環境情報の保存
echo "PROJECT_NAME=${projectName}" > /etc/jenkins-agent-env
echo "ENVIRONMENT=${environment}" >> /etc/jenkins-agent-env
echo "AGENT_ROOT=/home/jenkins/agent" >> /etc/jenkins-agent-env
chmod 644 /etc/jenkins-agent-env

# SSMエージェントの起動
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

# Javaのインストール（最後に実行）
echo "Installing Java..."
dnf install -y java-17-amazon-corretto

# 起動完了のマーク
echo "$(date) - Agent bootstrap completed" > /home/jenkins/agent/bootstrap-complete
chown jenkins:jenkins /home/jenkins/agent/bootstrap-complete
`).apply(userData => Buffer.from(userData).toString("base64")),
    tags: {
        Name: `${projectName}-agent-lt-${environment}`,
        Environment: environment,
    },
});

// SpotFleetリクエスト設定
const spotFleetRequest = new aws.ec2.SpotFleetRequest(`${projectName}-agent-spot-fleet`, {
    iamFleetRole: spotFleetRole.arn,
    spotPrice: spotPrice,
    targetCapacity: minTargetCapacity,
    terminateInstancesWithExpiration: true,
    instanceInterruptionBehavior: "terminate",
    launchTemplateConfigs: pulumi.all([privateSubnetIds]).apply(([subnetIds]) => 
        subnetIds.map((subnetId: string) => ({
            launchTemplateSpecification: {
                id: agentLaunchTemplate.id,
                version: agentLaunchTemplate.latestVersion,
            },
            overrides: [
                {
                    subnetId: subnetId,
                    instanceType: "t3.medium",
                    spotPrice: spotPrice,
                },
                {
                    subnetId: subnetId,
                    instanceType: "t3.large",
                    spotPrice: spotPrice,
                },
                {
                    subnetId: subnetId,
                    instanceType: "m5.large",
                    spotPrice: spotPrice,
                }
            ],
        }))
    ),
    tags: {
        Name: `${projectName}-agent-fleet-${environment}`,
        Environment: environment,
    },
});

// エージェントのステータスモニタリング用SNSトピック
const spotFleetNotificationTopic = new aws.sns.Topic(`${projectName}-agent-fleet-notifications`, {
    name: `${projectName}-agent-fleet-notifications-${environment}`,
    tags: {
        Name: `${projectName}-agent-fleet-notifications-${environment}`,
        Environment: environment,
    },
});

// 基本的なSSMパラメータ（エージェント設定情報保存用）
const agentInfoParameter = new aws.ssm.Parameter(`${projectName}-agent-fleet-info`, {
    name: `/${projectName}/${environment}/jenkins/agent/fleet-info`,
    type: "String",
    value: JSON.stringify({
        projectName: projectName,
        environment: environment,
        instanceType: instanceType,
        minCapacity: minTargetCapacity,
        maxCapacity: maxTargetCapacity,
        spotPrice: spotPrice,
        createdAt: new Date().toISOString(),
    }),
    description: "Jenkins agent fleet configuration information",
    tags: {
        Environment: environment,
    },
});

// SSMパラメータにスポットフリートIDを保存
const spotFleetIdParameter = new aws.ssm.Parameter(`${projectName}-agent-spotfleet-id`, {
    name: `/${projectName}/${environment}/jenkins/agent/spotFleetRequestId`,
    type: "String",
    value: spotFleetRequest.id,
    description: "Jenkins agent spot fleet request ID",
    tags: {
        Environment: environment,
    },
});

// エクスポート
export const agentRoleArn = jenkinsAgentRole.arn;
export const agentProfileArn = jenkinsAgentProfile.arn;
export const spotFleetRequestId = spotFleetRequest.id;
export const launchTemplateId = agentLaunchTemplate.id;
export const launchTemplateLatestVersion = agentLaunchTemplate.latestVersion;
export const spotFleetRoleArn = spotFleetRole.arn;
export const notificationTopicArn = spotFleetNotificationTopic.arn;
export const minCapacity = minTargetCapacity;
export const maxCapacity = maxTargetCapacity;
