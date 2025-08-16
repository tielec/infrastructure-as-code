/**
 * pulumi/jenkins-controller/index.ts
 * 
 * Jenkinsインフラのコントローラーリソースを構築するPulumiスクリプト
 * EC2インスタンスとIAMロールに集中し、設定部分は別スタックで管理
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
const jenkinsVersionParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/jenkins-version`,
});
const jenkinsColorParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/jenkins-color`,
});
const recoveryModeParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/jenkins-recovery-mode`,
});
const instanceTypeParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/controller-instance-type`,
});
const keyNameParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/key-name`,
});
const gitRepoParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/git-repo`,
});
const gitBranchParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/git-branch`,
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
const jenkinsSecurityGroupIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/security/jenkins-sg-id`,
});
const efsSecurityGroupIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/security/efs-sg-id`,
});

// ストレージリソースのSSMパラメータを取得
const efsFileSystemIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/storage/efs-file-system-id`,
});
const jenkinsAccessPointIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/storage/jenkins-access-point-id`,
});

// ロードバランサーリソースのSSMパラメータを取得
const blueTargetGroupArnParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/loadbalancer/blue-target-group-arn`,
});
const greenTargetGroupArnParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/loadbalancer/green-target-group-arn`,
});

// 設定値を変数に設定
const projectName = pulumi.output(projectNameParam).apply(p => p.value);
const jenkinsVersion = pulumi.output(jenkinsVersionParam).apply(p => p.value);
const jenkinsColor = pulumi.output(jenkinsColorParam).apply(p => p.value);
const recoveryMode = pulumi.output(recoveryModeParam).apply(p => p.value === "true");
const instanceType = pulumi.output(instanceTypeParam).apply(p => p.value);
const keyName = pulumi.output(keyNameParam).apply(p => p.value);
const gitRepo = pulumi.output(gitRepoParam).apply(p => p.value);
const gitBranch = pulumi.output(gitBranchParam).apply(p => p.value);

// ネットワークリソースIDを取得
const vpcId = pulumi.output(vpcIdParam).apply(p => p.value);
const privateSubnetAId = pulumi.output(privateSubnetAIdParam).apply(p => p.value);
const privateSubnetBId = pulumi.output(privateSubnetBIdParam).apply(p => p.value);
const privateSubnetIds = [privateSubnetAId, privateSubnetBId];

// セキュリティグループIDを取得
const jenkinsSecurityGroupId = pulumi.output(jenkinsSecurityGroupIdParam).apply(p => p.value);
const efsSecurityGroupId = pulumi.output(efsSecurityGroupIdParam).apply(p => p.value);

// ストレージリソースIDを取得
const efsFileSystemId = pulumi.output(efsFileSystemIdParam).apply(p => p.value);
const jenkinsAccessPointId = pulumi.output(jenkinsAccessPointIdParam).apply(p => p.value);

// ロードバランサーリソースARNを取得
const blueTargetGroupArn = pulumi.output(blueTargetGroupArnParam).apply(p => p.value);
const greenTargetGroupArn = pulumi.output(greenTargetGroupArnParam).apply(p => p.value);

// 環境に基づいてターゲットグループを選択
const targetGroupArn = jenkinsColor.apply(color => color === "blue" ? blueTargetGroupArn : greenTargetGroupArn);

// 最新のAmazon Linux 2023 AMI (ARM64版)を取得
const ami = aws.ec2.getAmi({
    mostRecent: true,
    owners: ["amazon"],
    filters: [
        {
            name: "name",
            values: ["al2023-ami-*-kernel-*-arm64"],  // ARM64アーキテクチャ用に変更
        },
        {
            name: "architecture",
            values: ["arm64"],  // 明示的にARM64アーキテクチャを指定
        },
        {
            name: "virtualization-type",
            values: ["hvm"],
        },
    ],
});

// IAMロール作成（Jenkins用）
const jenkinsRole = new aws.iam.Role(`jenkins-role`, {
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
        Name: pulumi.interpolate`${projectName}-jenkins-role-${jenkinsColor}-${environment}`,
        Environment: environment,
        Color: pulumi.interpolate`${jenkinsColor}`,
    },
});

// マネージドポリシーのアタッチ
const ssmPolicy = new aws.iam.RolePolicyAttachment(`jenkins-ssm-policy`, {
    role: jenkinsRole.name,
    policyArn: "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
});

const efsPolicy = new aws.iam.RolePolicyAttachment(`jenkins-efs-policy`, {
    role: jenkinsRole.name,
    policyArn: "arn:aws:iam::aws:policy/AmazonElasticFileSystemClientReadWriteAccess",
});

// SSM関連ポリシー（SSMコマンド実行のためのシンプルな権限）
const ssmCustomPolicy = new aws.iam.Policy(`jenkins-ssm-custom-policy`, {
    description: "Custom policy for Jenkins instance to use SSM",
    policy: JSON.stringify({
        Version: "2012-10-17",
        Statement: [
            {
                Effect: "Allow",
                Action: [
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                    "ssm:GetParametersByPath",
                    "ssm:SendCommand",
                    "ssm:ListCommands",
                    "ssm:ListCommandInvocations",
                    "ssm:GetCommandInvocation",
                    "ssm:DescribeInstanceInformation"
                ],
                Resource: "*"
            },
            {
                Effect: "Allow",
                Action: [
                    "ssm:PutParameter"
                ],
                Resource: [
                    pulumi.interpolate`arn:aws:ssm:*:*:parameter/jenkins-infra/${environment}/jenkins/status/*`
                ]
            }
        ]
    }),
});

const ssmCustomPolicyAttachment = new aws.iam.RolePolicyAttachment(
    `jenkins-ssm-custom-policy-attachment`, 
    {
        role: jenkinsRole.name,
        policyArn: ssmCustomPolicy.arn,
    }
);

// EC2およびSpot Fleet管理用の包括的なポリシー
const ec2SpotFleetPolicy = new aws.iam.Policy(`jenkins-ec2-spotfleet-policy`, {
    description: "Comprehensive policy for Jenkins controller to manage EC2 instances and Spot Fleet",
    policy: JSON.stringify({
        Version: "2012-10-17",
        Statement: [
            {
                // EC2インスタンスの管理権限
                Effect: "Allow",
                Action: [
                    "ec2:DescribeInstances",
                    "ec2:DescribeInstanceStatus",
                    "ec2:DescribeInstanceTypes",
                    "ec2:DescribeAvailabilityZones",
                    "ec2:DescribeSubnets",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeKeyPairs",
                    "ec2:DescribeImages",
                    "ec2:DescribeLaunchTemplates",
                    "ec2:DescribeLaunchTemplateVersions",
                    "ec2:RunInstances",
                    "ec2:TerminateInstances",
                    "ec2:StopInstances",
                    "ec2:StartInstances",
                    "ec2:CreateTags",
                    "ec2:DeleteTags"
                ],
                Resource: "*"
            },
            {
                // Spot Fleet の包括的な管理権限
                Effect: "Allow",
                Action: [
                    "ec2:DescribeSpotFleetRequests",
                    "ec2:DescribeSpotFleetInstances",
                    "ec2:DescribeSpotInstanceRequests",
                    "ec2:DescribeSpotPriceHistory",
                    "ec2:RequestSpotFleet",
                    "ec2:ModifySpotFleetRequest",
                    "ec2:CancelSpotFleetRequests",
                    "ec2:RequestSpotInstances",
                    "ec2:CancelSpotInstanceRequests"
                ],
                Resource: "*"
            },
            {
                // EC2 Fleet の管理権限
                Effect: "Allow",
                Action: [
                    "ec2:CreateFleet",
                    "ec2:DeleteFleet",
                    "ec2:DescribeFleets",
                    "ec2:ModifyFleet"
                ],
                Resource: "*"
            },
            {
                // Auto Scaling関連の権限
                Effect: "Allow",
                Action: [
                    "autoscaling:DescribeAutoScalingGroups",
                    "autoscaling:DescribeAutoScalingInstances",
                    "autoscaling:SetDesiredCapacity",
                    "autoscaling:UpdateAutoScalingGroup",
                    "autoscaling:DescribeScalingActivities"
                ],
                Resource: "*"
            },
            {
                // CloudWatch メトリクスの読み取り（スケーリング判断用）
                Effect: "Allow",
                Action: [
                    "cloudwatch:GetMetricStatistics",
                    "cloudwatch:ListMetrics",
                    "cloudwatch:PutMetricData",
                    "cloudwatch:DescribeAlarms"
                ],
                Resource: "*"
            },
            {
                // IAM PassRole権限（EC2インスタンスにロールを付与するため）
                Effect: "Allow",
                Action: [
                    "iam:PassRole"
                ],
                Resource: [
                    pulumi.interpolate`arn:aws:iam::*:role/${projectName}-agent-role-${environment}`,
                    pulumi.interpolate`arn:aws:iam::*:role/${projectName}-spotfleet-role-${environment}`,
                    pulumi.interpolate`arn:aws:iam::*:instance-profile/${projectName}-agent-profile-${environment}`
                ]
            },
            {
                // IAM リストアクセス（ロールの確認用）
                Effect: "Allow",
                Action: [
                    "iam:GetRole",
                    "iam:GetInstanceProfile",
                    "iam:ListInstanceProfiles",
                    "iam:ListRoles"
                ],
                Resource: "*"
            },
            {
                // SSM Parameter Store（エージェント設定の読み書き用）
                Effect: "Allow",
                Action: [
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                    "ssm:PutParameter",
                    "ssm:DeleteParameter"
                ],
                Resource: [
                    pulumi.interpolate`arn:aws:ssm:*:*:parameter/jenkins-infra/${environment}/jenkins/agent/*`
                ]
            }
        ]
    }),
});

// EC2 Spot Fleet ポリシーのアタッチ
const ec2SpotFleetPolicyAttachment = new aws.iam.RolePolicyAttachment(
    `jenkins-ec2-spotfleet-policy-attachment`, 
    {
        role: jenkinsRole.name,
        policyArn: ec2SpotFleetPolicy.arn,
    }
);

// Jenkins Plugins用の追加権限（EC2 Plugin, Fleet Plugin等）
const jenkinsPluginPolicy = new aws.iam.Policy(`jenkins-plugin-policy`, {
    description: "Additional permissions for Jenkins EC2 and Fleet plugins",
    policy: JSON.stringify({
        Version: "2012-10-17",
        Statement: [
            {
                // EC2 Plugin固有の権限
                Effect: "Allow",
                Action: [
                    "ec2:DescribeRegions",
                    "ec2:DescribeZones",
                    "ec2:DescribeVpcs",
                    "ec2:DescribeInstanceAttribute",
                    "ec2:ModifyInstanceAttribute",
                    "ec2:GetConsoleOutput",
                    "ec2:GetPasswordData"
                ],
                Resource: "*"
            },
            {
                // ネットワークインターフェース関連（プライベートIPの管理）
                Effect: "Allow",
                Action: [
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:CreateNetworkInterface",
                    "ec2:DeleteNetworkInterface",
                    "ec2:AttachNetworkInterface",
                    "ec2:DetachNetworkInterface"
                ],
                Resource: "*"
            },
            {
                // EBS ボリューム関連（必要に応じて）
                Effect: "Allow",
                Action: [
                    "ec2:DescribeVolumes",
                    "ec2:DescribeSnapshots",
                    "ec2:CreateSnapshot",
                    "ec2:DeleteSnapshot"
                ],
                Resource: "*"
            },
            {
                // EC2 インスタンス接続関連
                Effect: "Allow",
                Action: [
                    "ec2-instance-connect:SendSSHPublicKey"
                ],
                Resource: "*"
            }
        ]
    }),
});

const jenkinsPluginPolicyAttachment = new aws.iam.RolePolicyAttachment(
    `jenkins-plugin-policy-attachment`, 
    {
        role: jenkinsRole.name,
        policyArn: jenkinsPluginPolicy.arn,
    }
);

// Jenkins用インスタンスプロファイル
const jenkinsInstanceProfile = new aws.iam.InstanceProfile(
    `jenkins-profile`, 
    {
        role: jenkinsRole.name,
        tags: {
            Environment: environment,
            Color: pulumi.interpolate`${jenkinsColor}`,
        },
    }
);

// ユーザーデータスクリプト（SSMエージェント起動のみ）
// ARM64アーキテクチャ対応の注意点を追加
const userDataScript = pulumi.interpolate`#!/bin/bash
# Jenkins Controller User Data Script - SSM Setup Only
# ARM64 (t4g) instance compatible
set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

# システムの更新とSSMエージェントのインストール
dnf update -y
dnf install -y amazon-ssm-agent aws-cli jq git

# SSMエージェントの起動
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

# インスタンスIDの取得 (IMDSv2対応)
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
echo "Instance ID: $INSTANCE_ID - SSM Agent started successfully"

# アーキテクチャ情報の取得と記録
ARCH=$(uname -m)
echo "Architecture: $ARCH"

# 基本的な環境変数を設定（設定スクリプトから使用される場合のため）
cat > /etc/jenkins-env << EOF
PROJECT_NAME=${projectName}
ENVIRONMENT=${environment}
JENKINS_COLOR=${jenkinsColor}
JENKINS_VERSION=${jenkinsVersion}
JENKINS_MODE=${recoveryMode ? "recovery" : "normal"}
EFS_ID=${efsFileSystemId}
ACCESS_POINT_ID=${jenkinsAccessPointId}
GIT_REPO=${gitRepo}
GIT_BRANCH=${gitBranch}
ARCHITECTURE=$ARCH
EOF
chmod 644 /etc/jenkins-env

# 初期Gitリポジトリのクローン（SSMコマンドが使用する前準備として）
cd /root
git clone ${gitRepo} infrastructure-as-code || echo "Repository already exists"
cd infrastructure-as-code
git checkout ${gitBranch}

# ARM64用のJava設定メモ（Jenkinsインストール時に参照）
echo "Note: When installing Jenkins, ensure to use ARM64-compatible Java runtime" >> /var/log/user-data.log
`;

// Jenkinsコントローラーインスタンス
const jenkinsInstance = new aws.ec2.Instance(`jenkins-controller`, {
    ami: ami.then(ami => ami.id),
    instanceType: instanceType,
    subnetId: privateSubnetAId,
    vpcSecurityGroupIds: pulumi.all([jenkinsSecurityGroupId, efsSecurityGroupId]).apply(
        ([jenkinsSgId, efsSgId]) => [jenkinsSgId, efsSgId]
    ),
    keyName: keyName.apply(k => k === "none" ? "" : k),
    iamInstanceProfile: jenkinsInstanceProfile.name,
    userData: userDataScript.apply(script => Buffer.from(script).toString("base64")),
    rootBlockDevice: {
        volumeSize: 50,
        volumeType: "gp3",
        deleteOnTermination: true,
        encrypted: true,
    },
    tags: {
        Name: pulumi.interpolate`${projectName}-jenkins-${jenkinsColor}-${environment}`,
        Environment: environment,
        Color: pulumi.interpolate`${jenkinsColor}`,
        Role: "jenkins-master",
        Architecture: "arm64",  // アーキテクチャタグを追加
    },
});

// ターゲットグループへの登録
const targetGroupAttachment = new aws.lb.TargetGroupAttachment(
    `jenkins-tg-attachment`, 
    {
        targetGroupArn: targetGroupArn,
        targetId: jenkinsInstance.id,
        port: 8080,
    }
);

// インスタンスIDをSSM Parameter Storeに保存
const instanceIdParameter = new aws.ssm.Parameter(`jenkins-instance-id`, {
    name: `${ssmPrefix}/controller/instance-id`,
    type: "String",
    value: jenkinsInstance.id,
    description: pulumi.interpolate`Jenkins Controller Instance ID for ${environment} environment (${jenkinsColor})`,
    tags: {
        Name: pulumi.interpolate`${projectName}-jenkins-instance-id-${environment}`,
        Environment: environment,
        Color: pulumi.interpolate`${jenkinsColor}`,
        Component: "controller",
    },
    overwrite: true,  // 既存のパラメータを上書き可能にする
});

// プライベートIPをSSMパラメータに保存
const privateIpParameter = new aws.ssm.Parameter(`jenkins-private-ip`, {
    name: `${ssmPrefix}/controller/private-ip`,
    type: "String",
    value: jenkinsInstance.privateIp,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "controller",
    },
});

// インスタンスプロファイル名をSSMパラメータに保存
const instanceProfileParameter = new aws.ssm.Parameter(`jenkins-instance-profile`, {
    name: `${ssmPrefix}/controller/instance-profile-name`,
    type: "String",
    value: jenkinsInstanceProfile.name,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "controller",
    },
});

// Jenkins RoleのARNをSSMパラメータに保存
const roleArnParameter = new aws.ssm.Parameter(`jenkins-role-arn`, {
    name: `${ssmPrefix}/controller/role-arn`,
    type: "String",
    value: jenkinsRole.arn,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "controller",
    },
});

// デプロイされたJenkinsカラーをSSMパラメータに保存
const deployedColorParameter = new aws.ssm.Parameter(`jenkins-deployed-color`, {
    name: `${ssmPrefix}/controller/deployed-color`,
    type: "String",
    value: jenkinsColor,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "controller",
    },
});

// エクスポート
export const jenkinsInstanceId = jenkinsInstance.id;
export const jenkinsPrivateIp = jenkinsInstance.privateIp;
export const instanceProfileName = jenkinsInstanceProfile.name;
export const jenkinsRoleArn = jenkinsRole.arn;
export const deployedJenkinsColor = jenkinsColor;
export const recoveryModeEnabled = recoveryMode;
export const deployedGitRepo = gitRepo;
export const deployedGitBranch = gitBranch;
export const instanceArchitecture = "arm64";  // アーキテクチャ情報をエクスポート
