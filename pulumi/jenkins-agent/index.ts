/**
 * pulumi/agent/index.ts
 * 
 * Jenkinsインフラのエージェントリソースを構築するPulumiスクリプト
 * Spot Fleetリクエスト、EC2起動テンプレート、IAMロールなどを作成
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as tls from "@pulumi/tls";

// 環境名をスタック名から取得
const environment = pulumi.getStack();
const ssmPrefix = `/jenkins-infra/${environment}`;

// SSMパラメータから設定を取得
const projectNameParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/project-name`,
});
const maxTargetCapacityParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/agent-max-capacity`,
});
const minTargetCapacityParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/agent-min-capacity`,
});
const spotPriceParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/agent-spot-price`,
});
const instanceTypeParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/agent-instance-type`,
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
const jenkinsAgentSecurityGroupIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/security/jenkins-agent-sg-id`,
});

// 設定値を変数に設定
const projectName = pulumi.output(projectNameParam).apply(p => p.value);
const maxTargetCapacity = pulumi.output(maxTargetCapacityParam).apply(p => parseInt(p.value));
const minTargetCapacity = pulumi.output(minTargetCapacityParam).apply(p => parseInt(p.value));
const spotPrice = pulumi.output(spotPriceParam).apply(p => p.value);
const instanceType = pulumi.output(instanceTypeParam).apply(p => p.value);

// ネットワークリソースIDを取得
const vpcId = pulumi.output(vpcIdParam).apply(p => p.value);
const privateSubnetAId = pulumi.output(privateSubnetAIdParam).apply(p => p.value);
const privateSubnetBId = pulumi.output(privateSubnetBIdParam).apply(p => p.value);
const privateSubnetIds = [privateSubnetAId, privateSubnetBId];

// セキュリティグループIDを取得
const jenkinsAgentSecurityGroupId = pulumi.output(jenkinsAgentSecurityGroupIdParam).apply(p => p.value);

// Jenkins Agent用のSSHキーペアを作成
const agentPrivateKey = new tls.PrivateKey(`agent-private-key`, {
    algorithm: "RSA",
    rsaBits: 4096,
});

// AWS Key Pairリソースを作成
const agentKeyPair = new aws.ec2.KeyPair(`agent-keypair`, {
    keyName: pulumi.interpolate`${projectName}-agent-${environment}`,
    publicKey: agentPrivateKey.publicKeyOpenssh,
    tags: {
        Name: pulumi.interpolate`${projectName}-agent-keypair-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// 秘密鍵をSSM Parameter Storeに保存（セキュアな管理のため）
const agentPrivateKeyParameter = new aws.ssm.Parameter(`agent-private-key-param`, {
    name: `${ssmPrefix}/agent/private-key`,
    type: "SecureString",
    value: agentPrivateKey.privateKeyPem,
    description: "Private key for Jenkins agent SSH access",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// 最新のAmazon Linux 2023 AMIを取得
const defaultAmiX86 = aws.ec2.getAmi({
    mostRecent: true,
    owners: ["amazon"],
    filters: [{
        name: "name",
        values: ["al2023-ami-*-kernel-*-x86_64"],
    }],
});

const defaultAmiArm = aws.ec2.getAmi({
    mostRecent: true,
    owners: ["amazon"],
    filters: [{
        name: "name",
        values: ["al2023-ami-*-kernel-*-arm64"],
    }],
});

// カスタムAMI IDをSSMパラメータから取得（存在しない場合はデフォルトAMIを使用）
const customAmiX86Promise = aws.ssm.getParameter({
    name: `${ssmPrefix}/agent-ami/custom-ami-x86`,
}).then(param => param.value).catch(() => null);

const customAmiArmPromise = aws.ssm.getParameter({
    name: `${ssmPrefix}/agent-ami/custom-ami-arm`,
}).then(param => param.value).catch(() => null);

// 使用するAMI IDを決定（カスタムAMIがあればそれを使用、なければデフォルト）
const amiX86Id = pulumi.output(Promise.all([customAmiX86Promise, defaultAmiX86])).apply(([customId, defaultAmi]) => {
    console.log(`[DEBUG] x86 Custom AMI ID from SSM: ${customId}`);
    console.log(`[DEBUG] x86 Default AMI ID: ${defaultAmi.id}`);
    if (customId && customId !== "ami-placeholder-x86" && customId !== "ami-placeholder") {
        console.log(`[DEBUG] Using x86 custom AMI: ${customId}`);
        return customId;
    }
    console.log(`[DEBUG] Using x86 default AMI: ${defaultAmi.id}`);
    return defaultAmi.id;
});

const amiArmId = pulumi.output(Promise.all([customAmiArmPromise, defaultAmiArm])).apply(([customId, defaultAmi]) => {
    console.log(`[DEBUG] ARM Custom AMI ID from SSM: ${customId}`);
    console.log(`[DEBUG] ARM Default AMI ID: ${defaultAmi.id}`);
    if (customId && customId !== "ami-placeholder-arm" && customId !== "ami-placeholder") {
        console.log(`[DEBUG] Using ARM custom AMI: ${customId}`);
        return customId;
    }
    console.log(`[DEBUG] Using ARM default AMI: ${defaultAmi.id}`);
    return defaultAmi.id;
});

// IAMロール作成（Jenkinsエージェント用）
const jenkinsAgentRole = new aws.iam.Role(`agent-role`, {
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
        Name: pulumi.interpolate`${projectName}-agent-role-${environment}`,
        Environment: environment,
    },
});

// マネージドポリシーのアタッチ
const ssmPolicy = new aws.iam.RolePolicyAttachment(`agent-ssm-policy`, {
    role: jenkinsAgentRole.name,
    policyArn: "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
});

const efsPolicy = new aws.iam.RolePolicyAttachment(`agent-efs-policy`, {
    role: jenkinsAgentRole.name,
    policyArn: "arn:aws:iam::aws:policy/AmazonElasticFileSystemClientReadWriteAccess",
});

// ECRとS3アクセス権限（ビルドアーティファクト用）
const buildResourcesPolicy = new aws.iam.Policy(`agent-build-policy`, {
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
                    `arn:aws:s3:::jenkins-infra-artifacts-${environment}*`,
                    `arn:aws:s3:::jenkins-infra-artifacts-${environment}*/*`
                ]
            }
        ]
    }),
});

const buildResourcesPolicyAttachment = new aws.iam.RolePolicyAttachment(
    `agent-build-policy-attachment`, 
    {
        role: jenkinsAgentRole.name,
        policyArn: buildResourcesPolicy.arn,
    }
);

// Jenkins用インスタンスプロファイル
const jenkinsAgentProfile = new aws.iam.InstanceProfile(
    `agent-profile`, 
    {
        role: jenkinsAgentRole.name,
        tags: {
            Environment: environment,
        },
    }
);

// SpotFleet用IAMロール
const spotFleetRole = new aws.iam.Role(`spotfleet-role`, {
    name: pulumi.interpolate`${projectName}-spotfleet-role-${environment}`,
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
        Name: pulumi.interpolate`${projectName}-spotfleet-role-${environment}`,
        Environment: environment,
    },
});

// エージェント起動テンプレート（x86_64用）
const agentLaunchTemplate = new aws.ec2.LaunchTemplate(`agent-lt`, {
    namePrefix: `jenkins-infra-agent-lt-`,
    imageId: amiX86Id,
    instanceType: "t3.small", // デフォルトをt3.smallに変更
    keyName: agentKeyPair.keyName,  // 作成したキーペアを使用
    vpcSecurityGroupIds: [jenkinsAgentSecurityGroupId],
    iamInstanceProfile: {
        name: jenkinsAgentProfile.name,
    },
    blockDeviceMappings: [{
        deviceName: "/dev/xvda",
        ebs: {
            volumeSize: 30, // expect size>= 30GB
            volumeType: "gp3",
            deleteOnTermination: "true", // 文字列に変更
            encrypted: "true", // 文字列に変更
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
            Name: `jenkins-infra-agent-${environment}`,
            Environment: environment,
            Role: "jenkins-agent",
        },
    }],
    // ユーザーデータをBase64エンコード（カスタムAMI使用時は最小限の設定）
    userData: pulumi.all([amiX86Id, customAmiX86Promise]).apply(([id, customId]) => {
        const isCustomAmi = customId && !customId.startsWith("ami-placeholder");
        const userData = isCustomAmi ? 
            // カスタムAMI用の最小限のユーザーデータ
            `#!/bin/bash
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
set -x

# スワップの有効化（既に作成済み）
swapon /swapfile || true

# Dockerの起動と権限設定
systemctl start docker
chmod 666 /var/run/docker.sock || true
usermod -aG docker jenkins || true

# 環境情報の保存
echo "PROJECT_NAME=jenkins-infra" > /etc/jenkins-agent-env
echo "ENVIRONMENT=${environment}" >> /etc/jenkins-agent-env
echo "AGENT_ROOT=/home/jenkins/agent" >> /etc/jenkins-agent-env
chmod 644 /etc/jenkins-agent-env

# SSMエージェントの起動
systemctl start amazon-ssm-agent

# 起動完了のマーク
echo "$(date) - Agent bootstrap completed (custom AMI)" > /home/jenkins/agent/bootstrap-complete
chown jenkins:jenkins /home/jenkins/agent/bootstrap-complete
` :
            // デフォルトAMI用のフルユーザーデータ
            `#!/bin/bash
# Jenkins Agent Bootstrap Script
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
set -x

# スワップファイルの作成（2GB）
dd if=/dev/zero of=/swapfile bs=1M count=2048
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# /tmpの容量を確保（tmpfsのサイズを調整）
mount -o remount,size=2G /tmp

# システムのアップデートと必要なパッケージのインストール（Javaを除く）
dnf update -y
dnf install -y docker git jq amazon-ssm-agent

# 不要なパッケージキャッシュをクリーンアップ
dnf clean all

# Dockerの設定と起動
systemctl enable docker
systemctl start docker

# Dockerソケットの権限設定
chmod 666 /var/run/docker.sock || true

# Jenkinsユーザーの作成
useradd -m -d /home/jenkins -s /bin/bash jenkins
usermod -aG docker jenkins

# エージェント作業ディレクトリの設定
mkdir -p /home/jenkins/agent
chown -R jenkins:jenkins /home/jenkins

# 環境情報の保存
echo "PROJECT_NAME=jenkins-infra" > /etc/jenkins-agent-env
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
`;
        return Buffer.from(userData).toString("base64");
    }),
    tags: {
        Name: `${projectName}-agent-lt-${environment}`,
        Environment: environment,
    },
});

// ARM64用の起動テンプレート
const agentLaunchTemplateArm = new aws.ec2.LaunchTemplate(`agent-lt-arm`, {
    namePrefix: `jenkins-infra-agent-lt-arm-`,
    imageId: amiArmId,
    instanceType: "t4g.small",
    keyName: agentKeyPair.keyName,
    vpcSecurityGroupIds: [jenkinsAgentSecurityGroupId],
    iamInstanceProfile: {
        name: jenkinsAgentProfile.name,
    },
    blockDeviceMappings: [{
        deviceName: "/dev/xvda",
        ebs: {
            volumeSize: 30,　// expect size>= 30GB
            volumeType: "gp3",
            deleteOnTermination: "true",
            encrypted: "true",
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
            Name: `jenkins-infra-agent-${environment}`,
            Environment: environment,
            Role: "jenkins-agent",
            Architecture: "arm64",
        },
    }],
    // ユーザーデータをBase64エンコード（カスタムAMI使用時は最小限の設定）
    userData: pulumi.all([amiArmId, customAmiArmPromise]).apply(([id, customId]) => {
        const isCustomAmi = customId && !customId.startsWith("ami-placeholder");
        const userData = isCustomAmi ? 
            // カスタムAMI用の最小限のユーザーデータ
            `#!/bin/bash
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
set -x

# スワップの有効化（既に作成済み）
swapon /swapfile || true

# Dockerの起動と権限設定
systemctl start docker
chmod 666 /var/run/docker.sock || true
usermod -aG docker jenkins || true

# 環境情報の保存
echo "PROJECT_NAME=jenkins-infra" > /etc/jenkins-agent-env
echo "ENVIRONMENT=${environment}" >> /etc/jenkins-agent-env
echo "AGENT_ROOT=/home/jenkins/agent" >> /etc/jenkins-agent-env
echo "ARCHITECTURE=arm64" >> /etc/jenkins-agent-env
chmod 644 /etc/jenkins-agent-env

# SSMエージェントの起動
systemctl start amazon-ssm-agent

# 起動完了のマーク
echo "$(date) - Agent bootstrap completed (custom AMI)" > /home/jenkins/agent/bootstrap-complete
chown jenkins:jenkins /home/jenkins/agent/bootstrap-complete
` :
            // デフォルトAMI用のフルユーザーデータ
            `#!/bin/bash
# Jenkins Agent Bootstrap Script
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
set -x

# スワップファイルの作成（2GB）
dd if=/dev/zero of=/swapfile bs=1M count=2048
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# /tmpの容量を確保（tmpfsのサイズを調整）
mount -o remount,size=2G /tmp

# システムのアップデートと必要なパッケージのインストール（Javaを除く）
dnf update -y
dnf install -y docker git jq amazon-ssm-agent

# 不要なパッケージキャッシュをクリーンアップ
dnf clean all

# Dockerの設定と起動
systemctl enable docker
systemctl start docker

# Dockerソケットの権限設定
chmod 666 /var/run/docker.sock || true

# Jenkinsユーザーの作成
useradd -m -d /home/jenkins -s /bin/bash jenkins
usermod -aG docker jenkins

# エージェント作業ディレクトリの設定
mkdir -p /home/jenkins/agent
chown -R jenkins:jenkins /home/jenkins

# 環境情報の保存
echo "PROJECT_NAME=jenkins-infra" > /etc/jenkins-agent-env
echo "ENVIRONMENT=${environment}" >> /etc/jenkins-agent-env
echo "AGENT_ROOT=/home/jenkins/agent" >> /etc/jenkins-agent-env
echo "ARCHITECTURE=arm64" >> /etc/jenkins-agent-env
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
`;
        return Buffer.from(userData).toString("base64");
    }),
    tags: {
        Name: pulumi.interpolate`${projectName}-agent-lt-arm-${environment}`,
        Environment: environment,
    },
});

// SpotFleetリクエスト設定（複数の起動テンプレートを使用）
const spotFleetRequest = new aws.ec2.SpotFleetRequest(`agent-spot-fleet`, {
    iamFleetRole: spotFleetRole.arn,
    spotPrice: spotPrice,
    targetCapacity: minTargetCapacity,
    terminateInstancesWithExpiration: true,
    instanceInterruptionBehaviour: "terminate",
    allocationStrategy: "lowestPrice", // 最も安価なインスタンスを優先
    replaceUnhealthyInstances: true,
    launchTemplateConfigs: pulumi.all([privateSubnetIds]).apply(([subnetIds]) => {
        const configs: any[] = [];
        
        // ARM64インスタンス用の設定（t4g.small）- 全AZで利用可能
        subnetIds.forEach((subnetId: string) => {
            configs.push({
                launchTemplateSpecification: {
                    id: agentLaunchTemplateArm.id,
                    version: agentLaunchTemplateArm.latestVersion.apply(v => v.toString()),
                },
                overrides: [{
                    subnetId: subnetId,
                    instanceType: "t4g.small",
                    spotPrice: spotPrice,
                    priority: 1, // 最優先
                }],
            });
        });
        
        // x86_64インスタンス用の設定 - t3.smallとt2.smallのみ（全AZで利用可能）
        subnetIds.forEach((subnetId: string) => {
            configs.push({
                launchTemplateSpecification: {
                    id: agentLaunchTemplate.id,
                    version: agentLaunchTemplate.latestVersion.apply(v => v.toString()),
                },
                overrides: [
                    {
                        subnetId: subnetId,
                        instanceType: "t3.small",
                        spotPrice: spotPrice,
                        priority: 2,
                    },
                    {
                        subnetId: subnetId,
                        instanceType: "t2.small",
                        spotPrice: spotPrice,
                        priority: 3,
                    }
                ],
            });
        });
        
        return configs;
    }),
    tags: {
        Name: pulumi.interpolate`${projectName}-agent-fleet-${environment}`,
        Environment: environment,
    },
});

// エージェントのステータスモニタリング用SNSトピック
const spotFleetNotificationTopic = new aws.sns.Topic(`agent-fleet-notifications`, {
    name: `jenkins-infra-agent-fleet-notifications-${environment}`,
    tags: {
        Name: pulumi.interpolate`${projectName}-agent-fleet-notifications-${environment}`,
        Environment: environment,
    },
});

// 基本的なSSMパラメータ（エージェント設定情報保存用）
const agentInfoParameter = new aws.ssm.Parameter(`agent-fleet-info`, {
    name: `${ssmPrefix}/agent/fleet-info`,
    type: "String",
    value: pulumi.all([projectName, instanceType, minTargetCapacity, maxTargetCapacity, spotPrice, agentKeyPair.keyName]).apply(
        ([proj, inst, min, max, price, keyName]) => JSON.stringify({
            projectName: proj,
            environment: environment,
            instanceType: inst,
            minCapacity: min,
            maxCapacity: max,
            spotPrice: price,
            keyPairName: keyName,
            createdAt: new Date().toISOString(),
        })
    ),
    description: "Jenkins agent fleet configuration information",
    tags: {
        Environment: environment,
    },
});

// SSMパラメータにスポットフリートIDを保存
const spotFleetIdParameter = new aws.ssm.Parameter(`agent-spotfleet-id`, {
    name: `${ssmPrefix}/agent/spotFleetRequestId`,
    type: "String",
    value: spotFleetRequest.id,
    description: "Jenkins agent spot fleet request ID",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "agent",
    },
    overwrite: true,
});

// エージェントロールARNをSSMパラメータに保存
const agentRoleArnParameter = new aws.ssm.Parameter(`agent-role-arn`, {
    name: `${ssmPrefix}/agent/role-arn`,
    type: "String",
    value: jenkinsAgentRole.arn,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "agent",
    },
});

// エージェントインスタンスプロファイルARNをSSMパラメータに保存
const agentProfileArnParameter = new aws.ssm.Parameter(`agent-profile-arn`, {
    name: `${ssmPrefix}/agent/profile-arn`,
    type: "String",
    value: jenkinsAgentProfile.arn,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "agent",
    },
});

// 起動テンプレートIDをSSMパラメータに保存
const launchTemplateIdParameter = new aws.ssm.Parameter(`launch-template-id`, {
    name: `${ssmPrefix}/agent/launch-template-id`,
    type: "String",
    value: agentLaunchTemplate.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "agent",
    },
});

// ARM起動テンプレートIDをSSMパラメータに保存
const launchTemplateArmIdParameter = new aws.ssm.Parameter(`launch-template-arm-id`, {
    name: `${ssmPrefix}/agent/launch-template-arm-id`,
    type: "String",
    value: agentLaunchTemplateArm.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "agent",
    },
});

// SpotFleetロールARNをSSMパラメータに保存
const spotFleetRoleArnParameter = new aws.ssm.Parameter(`spotfleet-role-arn`, {
    name: `${ssmPrefix}/agent/spotfleet-role-arn`,
    type: "String",
    value: spotFleetRole.arn,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "agent",
    },
});

// 通知トピックARNをSSMパラメータに保存
const notificationTopicArnParameter = new aws.ssm.Parameter(`notification-topic-arn`, {
    name: `${ssmPrefix}/agent/notification-topic-arn`,
    type: "String",
    value: spotFleetNotificationTopic.arn,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "agent",
    },
});

// キーペア名をSSMパラメータに保存
const keyPairNameParameter = new aws.ssm.Parameter(`agent-keypair-name`, {
    name: `${ssmPrefix}/agent/keypair-name`,
    type: "String",
    value: agentKeyPair.keyName,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "agent",
    },
});

// エクスポート
export const agentRoleArn = jenkinsAgentRole.arn;
export const agentProfileArn = jenkinsAgentProfile.arn;
export const spotFleetRequestId = spotFleetRequest.id;
export const launchTemplateId = agentLaunchTemplate.id;
export const launchTemplateArmId = agentLaunchTemplateArm.id;
export const launchTemplateLatestVersion = agentLaunchTemplate.latestVersion;
export const launchTemplateArmLatestVersion = agentLaunchTemplateArm.latestVersion;
export const spotFleetRoleArn = spotFleetRole.arn;
export const notificationTopicArn = spotFleetNotificationTopic.arn;
export const minCapacity = minTargetCapacity;
export const maxCapacity = maxTargetCapacity;
export const agentKeyPairName = agentKeyPair.keyName;
export const privateKeyParameterName = agentPrivateKeyParameter.name;
