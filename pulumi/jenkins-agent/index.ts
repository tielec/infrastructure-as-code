/**
 * pulumi/agent/index.ts
 * 
 * Jenkinsインフラのエージェントリソースを構築するPulumiスクリプト
 * Spot Fleetリクエスト、EC2起動テンプレート、IAMロールなどを作成
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as tls from "@pulumi/tls";
import * as fs from "fs";
import * as path from "path";

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
        Name: `jenkins-infra-agent-keypair-${environment}`,
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
        Name: `jenkins-infra-agent-role-${environment}`,
        Environment: environment,
    },
});

// Pulumiを使用したインフラストラクチャ管理のため、AdministratorAccessポリシーをアタッチ
// 注意: Pulumiで様々なAWSリソースを管理するため、広範な権限が必要
const adminPolicy = new aws.iam.RolePolicyAttachment(`agent-admin-policy`, {
    role: jenkinsAgentRole.name,
    policyArn: "arn:aws:iam::aws:policy/AdministratorAccess",
});

// SSMパラメータストア追加権限（ダッシュボード用）
// AdministratorAccessに含まれているが、明示的に記載
const ssmParameterReadPolicy = new aws.iam.Policy(`agent-ssm-parameter-policy`, {
    description: "Additional SSM permissions for parameter dashboard (redundant with AdministratorAccess)",
    policy: JSON.stringify({
        Version: "2012-10-17",
        Statement: [
            {
                Sid: "SSMParameterList",
                Effect: "Allow",
                Action: [
                    "ssm:DescribeParameters"  // パラメータ一覧取得
                ],
                Resource: "*"
            }
        ]
    }),
});

const ssmParameterReadPolicyAttachment = new aws.iam.RolePolicyAttachment(
    `agent-ssm-parameter-policy-attachment`, 
    {
        role: jenkinsAgentRole.name,
        policyArn: ssmParameterReadPolicy.arn,
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
        Name: `jenkins-infra-spotfleet-role-${environment}`,
        Environment: environment,
    },
});

// エージェント起動テンプレート（x86_64用、IPv6対応）
const agentLaunchTemplate = new aws.ec2.LaunchTemplate(`agent-lt`, {
    namePrefix: `jenkins-infra-agent-lt-`,
    imageId: amiX86Id,
    instanceType: "t3a.medium", // デフォルトをt3a.mediumに変更（AMDプロセッサで10%安価）
    keyName: agentKeyPair.keyName,  // 作成したキーペアを使用
    // vpcSecurityGroupIds は networkInterfaces と競合するため削除
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
    networkInterfaces: [{
        associatePublicIpAddress: "false",
        deleteOnTermination: "true",
        deviceIndex: 0,
        ipv6AddressCount: 1,  // IPv6アドレスを1つ割り当て
        securityGroups: [jenkinsAgentSecurityGroupId],
    }],
    tagSpecifications: [{
        resourceType: "instance",
        tags: {
            Name: `jenkins-infra-agent-${environment}`,
            Environment: environment,
            Role: "jenkins-agent",
            IPv6Enabled: "true",  // IPv6有効化タグを追加
        },
    }],
    // ユーザーデータをBase64エンコード（カスタムAMI使用時は最小限の設定）
    userData: pulumi.all([amiX86Id, customAmiX86Promise]).apply(([id, customId]) => {
        const isCustomAmi = customId && !customId.startsWith("ami-placeholder");
        
        // 外部スクリプトファイルのパスを決定
        const scriptName = isCustomAmi ? 'jenkins-agent-custom-ami.sh' : 'jenkins-agent-setup.sh';
        const scriptPath = path.resolve(__dirname, '..', '..', 'scripts', 'aws', 'userdata', scriptName);
        
        let userDataTemplate: string;
        
        try {
            if (!fs.existsSync(scriptPath)) {
                // フォールバックパス（Pulumi実行時のカレントディレクトリから）
                const alternativePath = path.resolve(process.cwd(), 'scripts', 'aws', 'userdata', scriptName);
                if (fs.existsSync(alternativePath)) {
                    userDataTemplate = fs.readFileSync(alternativePath, 'utf8');
                } else {
                    throw new Error(`Userdata script not found at ${scriptPath} or ${alternativePath}`);
                }
            } else {
                userDataTemplate = fs.readFileSync(scriptPath, 'utf8');
            }
        } catch (error) {
            pulumi.log.error(`Failed to read userdata script: ${error}`);
            throw error;
        }
        
        // テンプレート変数の置換
        const ipv6Config = isCustomAmi ? `# IPv6設定の有効化
echo "Configuring IPv6..."
cat >> /etc/sysconfig/network << EOF
NETWORKING_IPV6=yes
IPV6_DEFAULTDEV=eth0
EOF

# IPv6 の確認と記録
IPV6_ADDR=$(ip -6 addr show eth0 | grep "inet6" | grep -v "fe80" | awk '{print $2}' | cut -d'/' -f1 | head -n1)
if [ -n "$IPV6_ADDR" ]; then
    echo "IPv6 Address: $IPV6_ADDR"
    echo "$IPV6_ADDR" > /home/jenkins/ipv6_address
fi

` : '';
        
        const userData = userDataTemplate
            .replace(/\${PROJECT_NAME}/g, 'jenkins-infra')
            .replace(/\${ENVIRONMENT}/g, environment)
            .replace(/\${IPV6_CONFIG}/g, ipv6Config)
            .replace(/\${IPV6_ENV}/g, isCustomAmi ? 'echo "IPV6_ENABLED=true" >> /etc/jenkins-agent-env\n' : '')
            .replace(/\${ARCHITECTURE_ENV}/g, '');
        
        return Buffer.from(userData).toString("base64");
    }),
    tags: {
        Name: `jenkins-infra-agent-lt-${environment}`,
        Environment: environment,
    },
});

// ARM64用の起動テンプレート（IPv6対応）
const agentLaunchTemplateArm = new aws.ec2.LaunchTemplate(`agent-lt-arm`, {
    namePrefix: `jenkins-infra-agent-lt-arm-`,
    imageId: amiArmId,
    instanceType: "t4g.medium",
    keyName: agentKeyPair.keyName,
    // vpcSecurityGroupIds は networkInterfaces と競合するため削除
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
    networkInterfaces: [{
        associatePublicIpAddress: "false",
        deleteOnTermination: "true",
        deviceIndex: 0,
        ipv6AddressCount: 1,  // IPv6アドレスを1つ割り当て
        securityGroups: [jenkinsAgentSecurityGroupId],
    }],
    tagSpecifications: [{
        resourceType: "instance",
        tags: {
            Name: `jenkins-infra-agent-${environment}`,
            Environment: environment,
            Role: "jenkins-agent",
            Architecture: "arm64",
            IPv6Enabled: "true",  // IPv6有効化タグを追加
        },
    }],
    // ユーザーデータをBase64エンコード（カスタムAMI使用時は最小限の設定）
    userData: pulumi.all([amiArmId, customAmiArmPromise]).apply(([id, customId]) => {
        const isCustomAmi = customId && !customId.startsWith("ami-placeholder");
        
        // 外部スクリプトファイルのパスを決定
        const scriptName = isCustomAmi ? 'jenkins-agent-custom-ami.sh' : 'jenkins-agent-setup.sh';
        const scriptPath = path.resolve(__dirname, '..', '..', 'scripts', 'aws', 'userdata', scriptName);
        
        let userDataTemplate: string;
        
        try {
            if (!fs.existsSync(scriptPath)) {
                // フォールバックパス（Pulumi実行時のカレントディレクトリから）
                const alternativePath = path.resolve(process.cwd(), 'scripts', 'aws', 'userdata', scriptName);
                if (fs.existsSync(alternativePath)) {
                    userDataTemplate = fs.readFileSync(alternativePath, 'utf8');
                } else {
                    throw new Error(`Userdata script not found at ${scriptPath} or ${alternativePath}`);
                }
            } else {
                userDataTemplate = fs.readFileSync(scriptPath, 'utf8');
            }
        } catch (error) {
            pulumi.log.error(`Failed to read userdata script: ${error}`);
            throw error;
        }
        
        // テンプレート変数の置換
        const userData = userDataTemplate
            .replace(/\${PROJECT_NAME}/g, 'jenkins-infra')
            .replace(/\${ENVIRONMENT}/g, environment)
            .replace(/\${IPV6_CONFIG}/g, '')
            .replace(/\${IPV6_ENV}/g, '')
            .replace(/\${ARCHITECTURE_ENV}/g, 'echo "ARCHITECTURE=arm64" >> /etc/jenkins-agent-env\n');
        
        return Buffer.from(userData).toString("base64");
    }),
    tags: {
        Name: `jenkins-infra-agent-lt-arm-${environment}`,
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
                    instanceType: "t4g.medium",
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
                        instanceType: "t3a.medium",
                        spotPrice: spotPrice,
                        priority: 2,
                    },
                    {
                        subnetId: subnetId,
                        instanceType: "t3.medium",
                        spotPrice: spotPrice,
                        priority: 3,
                    }
                ],
            });
        });
        
        return configs;
    }),
    tags: {
        Name: `jenkins-infra-agent-fleet-${environment}`,
        Environment: environment,
    },
});

// エージェントのステータスモニタリング用SNSトピック
const spotFleetNotificationTopic = new aws.sns.Topic(`agent-fleet-notifications`, {
    name: `jenkins-infra-agent-fleet-notifications-${environment}`,
    tags: {
        Name: `jenkins-infra-agent-fleet-notifications-${environment}`,
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
