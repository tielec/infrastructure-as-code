/**
 * pulumi/jenkins-controller/index.ts
 * 
 * Jenkinsインフラのコントローラーリソースを構築するPulumiスクリプト
 * EC2インスタンスとIAMロールに集中し、設定部分は別スタックで管理
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
const storageStackName = config.get("storageStackName") || "jenkins-storage";
const loadbalancerStackName = config.get("loadbalancerStackName") || "jenkins-loadbalancer";

// Jenkins設定を取得
const jenkinsVersion = config.get("jenkinsVersion") || "latest";
const jenkinsColor = config.get("jenkinsColor") || "blue";
const recoveryMode = config.getBoolean("recoveryMode") || false;
const instanceType = config.get("instanceType") || "t3.medium";
const keyName = config.get("keyName");
const gitRepo = config.get("gitRepo") || "https://github.com/tielec/infrastructure-as-code.git";
const gitBranch = config.get("gitBranch") || "main";

// 既存のスタックから値を取得
const networkStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${networkStackName}/${environment}`);
const securityStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${securityStackName}/${environment}`);
const storageStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${storageStackName}/${environment}`);
const loadbalancerStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${loadbalancerStackName}/${environment}`);

// 必要なリソースIDを取得
const vpcId = networkStack.getOutput("vpcId");
const privateSubnetIds = networkStack.getOutput("privateSubnetIds");
const jenkinsSecurityGroupId = securityStack.getOutput("jenkinsSecurityGroupId");
const efsSecurityGroupId = securityStack.getOutput("efsSecurityGroupId"); // EFSセキュリティグループも取得
const efsFileSystemId = storageStack.getOutput("efsFileSystemId");
const jenkinsAccessPointId = storageStack.getOutput("jenkinsAccessPointId");
const blueTargetGroupArn = loadbalancerStack.getOutput("blueTargetGroupArn");
const greenTargetGroupArn = loadbalancerStack.getOutput("greenTargetGroupArn");

// 環境に基づいてターゲットグループを選択
const targetGroupArn = jenkinsColor === "blue" ? blueTargetGroupArn : greenTargetGroupArn;

// 最新のAmazon Linux 2023 AMIを取得
const ami = aws.ec2.getAmi({
    mostRecent: true,
    owners: ["amazon"],
    filters: [{
        name: "name",
        values: ["al2023-ami-*-kernel-*-x86_64"],
    }],
});

// IAMロール作成（Jenkins用）
const jenkinsRole = new aws.iam.Role(`${projectName}-jenkins-role-${jenkinsColor}`, {
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
        Name: `${projectName}-jenkins-role-${jenkinsColor}-${environment}`,
        Environment: environment,
        Color: jenkinsColor,
    },
});

// マネージドポリシーのアタッチ
const ssmPolicy = new aws.iam.RolePolicyAttachment(`${projectName}-jenkins-ssm-policy-${jenkinsColor}`, {
    role: jenkinsRole.name,
    policyArn: "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
});

const efsPolicy = new aws.iam.RolePolicyAttachment(`${projectName}-jenkins-efs-policy-${jenkinsColor}`, {
    role: jenkinsRole.name,
    policyArn: "arn:aws:iam::aws:policy/AmazonElasticFileSystemClientReadWriteAccess",
});

// SSM関連ポリシー（SSMコマンド実行のためのシンプルな権限）
const ssmCustomPolicy = new aws.iam.Policy(`${projectName}-jenkins-ssm-custom-policy-${jenkinsColor}`, {
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
                    `arn:aws:ssm:*:*:parameter/${projectName}/${environment}/jenkins/status/*`
                ]
            }
        ]
    }),
});

const ssmCustomPolicyAttachment = new aws.iam.RolePolicyAttachment(
    `${projectName}-jenkins-ssm-custom-policy-attachment-${jenkinsColor}`, 
    {
        role: jenkinsRole.name,
        policyArn: ssmCustomPolicy.arn,
    }
);

// EC2およびSpot Fleet管理用のカスタムポリシー
const ec2SpotFleetPolicy = new aws.iam.Policy(`${projectName}-jenkins-ec2-spotfleet-policy-${jenkinsColor}`, {
    description: "Policy for Jenkins controller to manage EC2 instances and Spot Fleet",
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
                // Spot Fleet の管理権限
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
                // Auto Scaling関連の権限（将来的な拡張用）
                Effect: "Allow",
                Action: [
                    "autoscaling:DescribeAutoScalingGroups",
                    "autoscaling:DescribeAutoScalingInstances",
                    "autoscaling:SetDesiredCapacity",
                    "autoscaling:UpdateAutoScalingGroup"
                ],
                Resource: "*"
            },
            {
                // CloudWatch メトリクスの読み取り（スケーリング判断用）
                Effect: "Allow",
                Action: [
                    "cloudwatch:GetMetricStatistics",
                    "cloudwatch:ListMetrics",
                    "cloudwatch:PutMetricData"
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
                    `arn:aws:iam::*:role/${projectName}-agent-role-${environment}`,
                    `arn:aws:iam::*:role/${projectName}-spotfleet-role-${environment}`
                ]
            },
            {
                // SSM Parameter Store（エージェント設定の読み取り用）
                Effect: "Allow",
                Action: [
                    "ssm:GetParameter",
                    "ssm:GetParameters"
                ],
                Resource: [
                    `arn:aws:ssm:*:*:parameter/${projectName}/${environment}/jenkins/agent/*`
                ]
            }
        ]
    }),
});

// EC2 Spot Fleet ポリシーのアタッチ
const ec2SpotFleetPolicyAttachment = new aws.iam.RolePolicyAttachment(
    `${projectName}-jenkins-ec2-spotfleet-policy-attachment-${jenkinsColor}`, 
    {
        role: jenkinsRole.name,
        policyArn: ec2SpotFleetPolicy.arn,
    }
);

// Jenkins Plugins用の追加権限（EC2 Plugin, Fleet Plugin等）
const jenkinsPluginPolicy = new aws.iam.Policy(`${projectName}-jenkins-plugin-policy-${jenkinsColor}`, {
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
            }
        ]
    }),
});

const jenkinsPluginPolicyAttachment = new aws.iam.RolePolicyAttachment(
    `${projectName}-jenkins-plugin-policy-attachment-${jenkinsColor}`, 
    {
        role: jenkinsRole.name,
        policyArn: jenkinsPluginPolicy.arn,
    }
);

// Jenkins用インスタンスプロファイル
const jenkinsInstanceProfile = new aws.iam.InstanceProfile(
    `${projectName}-jenkins-profile-${jenkinsColor}`, 
    {
        role: jenkinsRole.name,
        tags: {
            Environment: environment,
            Color: jenkinsColor,
        },
    }
);

// ユーザーデータスクリプト（SSMエージェント起動のみ）
const userDataScript = pulumi.interpolate`#!/bin/bash
# Jenkins Controller User Data Script - SSM Setup Only
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
EOF
chmod 644 /etc/jenkins-env

# 初期Gitリポジトリのクローン（SSMコマンドが使用する前準備として）
cd /root
git clone ${gitRepo} infrastructure-as-code || echo "Repository already exists"
cd infrastructure-as-code
git checkout ${gitBranch}
`;

// Jenkinsコントローラーインスタンス
const jenkinsInstance = new aws.ec2.Instance(`${projectName}-jenkins-${jenkinsColor}`, {
    ami: ami.then(ami => ami.id),
    instanceType: instanceType,
    subnetId: privateSubnetIds.apply(subnets => subnets[0]),
    vpcSecurityGroupIds: pulumi.all([jenkinsSecurityGroupId, efsSecurityGroupId]).apply(
        ([jenkinsSgId, efsSgId]) => [jenkinsSgId, efsSgId]
    ),
    keyName: keyName,
    iamInstanceProfile: jenkinsInstanceProfile.name,
    userData: userDataScript.apply(script => Buffer.from(script).toString("base64")),
    rootBlockDevice: {
        volumeSize: 50,
        volumeType: "gp3",
        deleteOnTermination: true,
        encrypted: true,
    },
    tags: {
        Name: `${projectName}-jenkins-${jenkinsColor}-${environment}`,
        Environment: environment,
        Color: jenkinsColor,
        Role: "jenkins-master",
    },
});

// ターゲットグループへの登録
const targetGroupAttachment = new aws.lb.TargetGroupAttachment(
    `${projectName}-jenkins-tg-attachment-${jenkinsColor}`, 
    {
        targetGroupArn: targetGroupArn,
        targetId: jenkinsInstance.id,
        port: 8080,
    }
);

// エクスポート
export const jenkinsInstanceId = jenkinsInstance.id;
export const jenkinsPrivateIp = jenkinsInstance.privateIp;
export const instanceProfileName = jenkinsInstanceProfile.name;
export const jenkinsRoleArn = jenkinsRole.arn;
export const deployedJenkinsColor = jenkinsColor;
export const recoveryModeEnabled = recoveryMode;
export const deployedGitRepo = gitRepo;
export const deployedGitBranch = gitBranch;
