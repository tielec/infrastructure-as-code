/**
 * pulumi/controller/index.ts
 * 
 * Jenkinsインフラのコントローラーリソースを構築するPulumiスクリプト
 * Blue/Green環境で動作するJenkinsコントローラーインスタンスを作成
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

// 既存のスタックから値を取得
const networkStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${networkStackName}/${environment}`);
const securityStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${securityStackName}/${environment}`);
const storageStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${storageStackName}/${environment}`);
const loadbalancerStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${loadbalancerStackName}/${environment}`);

// 必要なリソースIDを取得
const vpcId = networkStack.getOutput("vpcId");
const privateSubnetIds = networkStack.getOutput("privateSubnetIds");
const jenkinsSecurityGroupId = securityStack.getOutput("jenkinsSecurityGroupId");
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

// SSM関連ポリシー（ドキュメント実行とパラメータ読み取り用）
const ssmCustomPolicy = new aws.iam.Policy(`${projectName}-jenkins-ssm-custom-policy-${jenkinsColor}`, {
    description: "Custom policy for Jenkins instance to use SSM documents and parameters",
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

// Jenkins設定用SSMパラメータ
const jenkinsVersionParam = new aws.ssm.Parameter(`${projectName}-jenkins-version-${jenkinsColor}`, {
    name: `/${projectName}/${environment}/jenkins/version`,
    type: "String",
    value: jenkinsVersion,
    tags: {
        Environment: environment,
        Color: jenkinsColor,
    },
});

const jenkinsColorParam = new aws.ssm.Parameter(`${projectName}-jenkins-color-${jenkinsColor}`, {
    name: `/${projectName}/${environment}/jenkins/color`,
    type: "String",
    value: jenkinsColor,
    tags: {
        Environment: environment,
        Color: jenkinsColor,
    },
});

const jenkinsModeParam = new aws.ssm.Parameter(`${projectName}-jenkins-mode-${jenkinsColor}`, {
    name: `/${projectName}/${environment}/jenkins/mode`,
    type: "String",
    value: recoveryMode ? "recovery" : "normal",
    tags: {
        Environment: environment,
        Color: jenkinsColor,
    },
});

// SSMドキュメント（インストール用）
const jenkinsInstallDocument = new aws.ssm.Document(`${projectName}-jenkins-install-${jenkinsColor}`, {
    name: `${projectName}-jenkins-install-${jenkinsColor}-${environment}`,
    documentType: "Command",
    content: JSON.stringify({
        schemaVersion: "2.2",
        description: "Jenkins Controller installation",
        parameters: {
            ProjectName: {
                type: "String",
                default: projectName,
                description: "Project name"
            },
            Environment: {
                type: "String",
                default: environment,
                description: "Environment name"
            },
            JenkinsVersion: {
                type: "String",
                default: jenkinsVersion,
                description: "Jenkins version to install"
            },
            JenkinsColor: {
                type: "String",
                default: jenkinsColor,
                description: "Jenkins environment color (blue/green)"
            }
        },
        mainSteps: [
            {
                action: "aws:runShellScript",
                name: "installJenkins",
                inputs: {
                    runCommand: [
                        "#!/bin/bash",
                        "export PROJECT_NAME={{ProjectName}}",
                        "export ENVIRONMENT={{Environment}}",
                        "export JENKINS_VERSION={{JenkinsVersion}}",
                        "export JENKINS_COLOR={{JenkinsColor}}",
                        `source /root/infrastructure-as-code/scripts/jenkins/shell/controller-install.sh`
                    ]
                }
            }
        ]
    }),
    tags: {
        Environment: environment,
        Color: jenkinsColor,
    },
});

// SSMドキュメント（EFSマウント用）
const jenkinsMountEfsDocument = new aws.ssm.Document(`${projectName}-jenkins-mount-efs-${jenkinsColor}`, {
    name: `${projectName}-jenkins-mount-efs-${jenkinsColor}-${environment}`,
    documentType: "Command",
    content: JSON.stringify({
        schemaVersion: "2.2",
        description: "Mount EFS for Jenkins",
        parameters: {
            ProjectName: {
                type: "String",
                default: projectName,
                description: "Project name"
            },
            Environment: {
                type: "String",
                default: environment,
                description: "Environment name"
            },
            EfsId: {
                type: "String",
                description: "EFS File System ID"
            },
            Region: {
                type: "String",
                default: "{{global:REGION}}",
                description: "AWS Region"
            }
        },
        mainSteps: [
            {
                action: "aws:runShellScript",
                name: "mountEfs",
                inputs: {
                    runCommand: [
                        "#!/bin/bash",
                        "export PROJECT_NAME={{ProjectName}}",
                        "export ENVIRONMENT={{Environment}}",
                        "export EFS_ID={{EfsId}}",
                        "export AWS_REGION={{Region}}",
                        `source /root/infrastructure-as-code/scripts/jenkins/shell/controller-mount-efs.sh`
                    ]
                }
            }
        ]
    }),
    tags: {
        Environment: environment,
        Color: jenkinsColor,
    },
});

// SSMドキュメント（設定用）
const jenkinsConfigureDocument = new aws.ssm.Document(`${projectName}-jenkins-configure-${jenkinsColor}`, {
    name: `${projectName}-jenkins-configure-${jenkinsColor}-${environment}`,
    documentType: "Command",
    content: JSON.stringify({
        schemaVersion: "2.2",
        description: "Configure Jenkins controller",
        parameters: {
            ProjectName: {
                type: "String",
                default: projectName,
                description: "Project name"
            },
            Environment: {
                type: "String",
                default: environment,
                description: "Environment name"
            },
            JenkinsMode: {
                type: "String",
                default: recoveryMode ? "recovery" : "normal",
                description: "Jenkins mode (normal/recovery)"
            },
            JenkinsColor: {
                type: "String",
                default: jenkinsColor,
                description: "Jenkins environment color (blue/green)"
            }
        },
        mainSteps: [
            {
                action: "aws:runShellScript",
                name: "configureJenkins",
                inputs: {
                    runCommand: [
                        "#!/bin/bash",
                        "export PROJECT_NAME={{ProjectName}}",
                        "export ENVIRONMENT={{Environment}}",
                        "export JENKINS_MODE={{JenkinsMode}}",
                        "export JENKINS_COLOR={{JenkinsColor}}",
                        `source /root/infrastructure-as-code/scripts/jenkins/shell/controller-configure.sh`
                    ]
                }
            }
        ]
    }),
    tags: {
        Environment: environment,
        Color: jenkinsColor,
    },
});

// SSMドキュメント（起動用）
const jenkinsStartupDocument = new aws.ssm.Document(`${projectName}-jenkins-startup-${jenkinsColor}`, {
    name: `${projectName}-jenkins-startup-${jenkinsColor}-${environment}`,
    documentType: "Command",
    content: JSON.stringify({
        schemaVersion: "2.2",
        description: "Start Jenkins controller service",
        parameters: {
            ProjectName: {
                type: "String",
                default: projectName,
                description: "Project name"
            },
            Environment: {
                type: "String",
                default: environment,
                description: "Environment name"
            },
            JenkinsColor: {
                type: "String",
                default: jenkinsColor,
                description: "Jenkins environment color (blue/green)"
            }
        },
        mainSteps: [
            {
                action: "aws:runShellScript",
                name: "startJenkins",
                inputs: {
                    runCommand: [
                        "#!/bin/bash",
                        "export PROJECT_NAME={{ProjectName}}",
                        "export ENVIRONMENT={{Environment}}",
                        "export JENKINS_COLOR={{JenkinsColor}}",
                        `source /root/infrastructure-as-code/scripts/jenkins/shell/controller-startup.sh`
                    ]
                }
            }
        ]
    }),
    tags: {
        Environment: environment,
        Color: jenkinsColor,
    },
});

// ユーザーデータスクリプト（SSMエージェント起動のみ）
const userDataScript = pulumi.interpolate`#!/bin/bash
# Jenkins Controller User Data Script - SSM Setup Only
set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

# システムの更新とSSMエージェントのインストール
dnf update -y
dnf install -y amazon-ssm-agent aws-cli jq

# SSMエージェントの起動
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

# インスタンスIDの取得 (IMDSv2対応)
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
echo "Instance ID: $INSTANCE_ID - SSM Agent started successfully"

# GitリポジトリのクローンとSSMドキュメントの順次実行
cd /root
git clone https://github.com/tielec/infrastructure-as-code.git

# 基本的な環境変数を設定（Ansibleから使用される場合のため）
echo "PROJECT_NAME=${projectName}" > /etc/environment
echo "ENVIRONMENT=${environment}" >> /etc/environment
echo "JENKINS_COLOR=${jenkinsColor}" >> /etc/environment
echo "JENKINS_VERSION=${jenkinsVersion}" >> /etc/environment
echo "JENKINS_MODE=${recoveryMode ? "recovery" : "normal"}" >> /etc/environment
echo "EFS_ID=${efsFileSystemId}" >> /etc/environment
`;

// Jenkinsコントローラーインスタンス
const jenkinsInstance = new aws.ec2.Instance(`${projectName}-jenkins-${jenkinsColor}`, {
    ami: ami.then(ami => ami.id),
    instanceType: instanceType,
    subnetId: privateSubnetIds.apply(subnets => subnets[0]),
    vpcSecurityGroupIds: [jenkinsSecurityGroupId],
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

// エクスポート箇所を以下のように修正
export const jenkinsInstanceId = jenkinsInstance.id;
export const jenkinsPrivateIp = jenkinsInstance.privateIp;
// 変数名を変更
export const instanceProfileName = jenkinsInstanceProfile.name;
export const jenkinsRoleArn = jenkinsRole.arn;
// 変数名を変更
export const deployedJenkinsColor = jenkinsColor;
export const recoveryModeEnabled = recoveryMode;

// SSM Documents ARN
export const ssmDocumentsArn = {
    install: jenkinsInstallDocument.arn,
    mountEfs: jenkinsMountEfsDocument.arn,
    configure: jenkinsConfigureDocument.arn,
    startup: jenkinsStartupDocument.arn,
};