/**
 * Jenkinsコントローラー用のAWSリソース（EC2インスタンス、EFS、SSMリソースなど）を
 * 作成するためのモジュール。Blue/Greenデプロイメント戦略をサポートしています。
 */

import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as fs from "fs";
import * as path from "path";
import { dependsOn } from "../../common/dependency-utils";

interface JenkinsInstanceInput {
    projectName: string;
    environment: string;
    vpcId: pulumi.Input<string>;
    subnetId: pulumi.Input<string>;
    securityGroupId: pulumi.Input<string>;
    targetGroupArn: pulumi.Input<string>;
    efsFileSystemId?: pulumi.Input<string>;
    efsAccessPointId?: pulumi.Input<string>;
    instanceType?: string;
    keyName?: string;
    color: "blue" | "green";
    jenkinsVersion?: string;
    recoveryMode?: boolean;
}

// スクリプトファイルの読み込み関数
function loadScript(scriptPath: string): string {
    try {
        return fs.readFileSync(path.resolve(__dirname, scriptPath), 'utf8');
    } catch (error) {
        console.error(`Error loading script from ${scriptPath}:`, error);
        throw error;
    }
}

// ユーザーデータテンプレートを準備して変数を置換する関数
// 引数の型を修正して pulumi.Input や pulumi.Output も受け入れるようにする
function prepareUserData(templatePath: string, variables: Record<string, pulumi.Input<string> | string>): pulumi.Output<string> {
    const template = loadScript(templatePath);
    
    // 全ての変数をOutputにまとめる
    return pulumi.all(Object.entries(variables).map(([key, value]) => {
        return pulumi.output(value).apply(resolvedValue => ({ key, value: resolvedValue || '' }));
    })).apply(resolvedVars => {
        // 変数の置換処理
        let result = template;
        for (const { key, value } of resolvedVars) {
            const regex = new RegExp(`\\$\\{${key}\\}`, 'g');
            result = result.replace(regex, value);
        }
        return result;
    });
}

// SSMパラメータを作成する関数 - Advanced ティア対応
function createSSMParameter(
    name: string,
    value: string,
    projectName: string,
    environment: string,
    secure: boolean = false,
    dependencies?: pulumi.Resource[]
): aws.ssm.Parameter {
    const paramType = secure ? "SecureString" : "String";
    
    // 値のサイズが4000バイトを超える場合はAdvancedティアを使用
    // 余裕を持って4000バイトで判定（4096ギリギリだとリスクがある）
    const tier = value.length > 4000 ? "Advanced" : "Standard";
    
    console.log(`Creating Parameter /${projectName}/${environment}/jenkins/${name} with tier: ${tier}`);
    
    const param = new aws.ssm.Parameter(`${projectName}-${name}`, {
        name: `/${projectName}/${environment}/jenkins/${name}`,
        type: paramType,
        value: value,
        tier: tier,  // サイズに基づいて自動的にティアを決定
        overwrite: true,
        tags: {
            Environment: environment,
            ManagedBy: "pulumi",
        },
    });

    if (dependencies && dependencies.length > 0) {
        return dependsOn(param, dependencies);
    }
    return param;
}

// Jenkinsコントローラー設定に必要なSSMパラメータとドキュメントを作成
function createJenkinsControllerSSMResources(
    projectName: string, 
    environment: string,
    jenkinsVersion: string,
    color: string,
    recoveryMode: boolean,
    dependencies?: pulumi.Resource[]
): {
    parameters: Record<string, aws.ssm.Parameter>,
    documents: Record<string, aws.ssm.Document>
} {
    // Groovyスクリプトの読み込み
    const disableCliGroovy = loadScript('../../../../scripts/jenkins/groovy/disable-cli.groovy');
    const basicSettingsGroovy = loadScript('../../../../scripts/jenkins/groovy/basic-settings.groovy');
    const recoveryModeGroovy = loadScript('../../../../scripts/jenkins/groovy/recovery-mode.groovy');
    
    // シェルスクリプトの読み込み
    const installScript = loadScript('../../../../scripts/jenkins/shell/controller-install.sh');
    const efsMountScript = loadScript('../../../../scripts/jenkins/shell/controller-mount-efs.sh');
    const configureScript = loadScript('../../../../scripts/jenkins/shell/controller-configure.sh');
    const startupScript = loadScript('../../../../scripts/jenkins/shell/controller-startup.sh');
    const updateScript = loadScript('../../../../scripts/jenkins/shell/controller-update.sh');
    //const installPluginsScript = loadScript('../../../../scripts/jenkins/shell/controller-install-plugins.sh');


    // パラメータの作成
    const parameters: Record<string, aws.ssm.Parameter> = {
        version: createSSMParameter("version", jenkinsVersion, projectName, environment, false, dependencies),
        color: createSSMParameter("color", color, projectName, environment, false, dependencies),
        mode: createSSMParameter("mode", recoveryMode ? "recovery" : "normal", projectName, environment, false, dependencies),
        activeEnv: createSSMParameter("active-environment", color, projectName, environment, false, dependencies),
        disableCliGroovy: createSSMParameter("groovy/disable-cli", disableCliGroovy, projectName, environment, false, dependencies),
        basicSettingsGroovy: createSSMParameter("groovy/basic-settings", basicSettingsGroovy, projectName, environment, false, dependencies),
        recoveryModeGroovy: createSSMParameter("groovy/recovery-mode", recoveryModeGroovy, projectName, environment, false, dependencies),
        //installPluginsScript: createSSMParameter("scripts/install-plugins", installPluginsScript, projectName, environment, false, dependencies)
    };

    // SSMドキュメントの作成
    const installDocument = new aws.ssm.Document(`${projectName}-jenkins-install-${color}`, {
        name: `${projectName}-jenkins-install-${color}-${environment}`,
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
                    default: color,
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
                            installScript
                        ]
                    }
                }
            ]
        }),
        tags: {
            Environment: environment,
            Color: color,
        },
    });

    const mountEfsDocument = new aws.ssm.Document(`${projectName}-jenkins-mount-efs-${color}`, {
        name: `${projectName}-jenkins-mount-efs-${color}-${environment}`,
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
                            efsMountScript
                        ]
                    }
                }
            ]
        }),
        tags: {
            Environment: environment,
            Color: color,
        },
    });

    const configureDocument = new aws.ssm.Document(`${projectName}-jenkins-configure-${color}`, {
        name: `${projectName}-jenkins-configure-${color}-${environment}`,
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
                    default: color,
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
                            configureScript
                        ]
                    }
                }
            ]
        }),
        tags: {
            Environment: environment,
            Color: color,
        },
    });

    const startupDocument = new aws.ssm.Document(`${projectName}-jenkins-startup-${color}`, {
        name: `${projectName}-jenkins-startup-${color}-${environment}`,
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
                    default: color,
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
                            startupScript
                        ]
                    }
                }
            ]
        }),
        tags: {
            Environment: environment,
            Color: color,
        },
    });

    const updateDocument = new aws.ssm.Document(`${projectName}-jenkins-update-${color}`, {
        name: `${projectName}-jenkins-update-${color}-${environment}`,
        documentType: "Command",
        content: JSON.stringify({
            schemaVersion: "2.2",
            description: "Update Jenkins controller",
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
                    default: "latest",
                    description: "Jenkins version to update to"
                },
                RestartJenkins: {
                    type: "String",
                    default: "false",
                    allowedValues: ["true", "false"],
                    description: "Whether to restart Jenkins after update"
                }
            },
            mainSteps: [
                {
                    action: "aws:runShellScript",
                    name: "updateJenkins",
                    inputs: {
                        runCommand: [
                            "#!/bin/bash",
                            "export PROJECT_NAME={{ProjectName}}",
                            "export ENVIRONMENT={{Environment}}",
                            "export JENKINS_VERSION={{JenkinsVersion}}",
                            "export RESTART_JENKINS={{RestartJenkins}}",
                            updateScript
                        ]
                    }
                }
            ]
        }),
        tags: {
            Environment: environment,
            Color: color,
        },
    });

    // 依存関係の設定
    const docs: Record<string, aws.ssm.Document> = {
        install: installDocument,
        mountEfs: mountEfsDocument,
        configure: configureDocument,
        startup: startupDocument,
        update: updateDocument
    };

    // 依存関係を設定
    if (dependencies && dependencies.length > 0) {
        Object.keys(docs).forEach(key => {
            docs[key] = dependsOn(docs[key], dependencies);
        });
    }

    // パラメータ間の依存関係を設定
    Object.keys(docs).forEach(key => {
        docs[key] = dependsOn(docs[key], Object.values(parameters));
    });

    return {
        parameters,
        documents: docs
    };
}

// 依存関係を考慮してJenkinsインスタンスを作成する
export function createJenkinsInstance(input: JenkinsInstanceInput, dependencies?: pulumi.Resource[]) {
    const config = new pulumi.Config();
    const instanceType = input.instanceType || config.get("instanceType") || "t3.medium";
    const keyName = input.keyName || config.get("keyName");
    const jenkinsVersion = input.jenkinsVersion || config.get("jenkinsVersion") || "latest";
    const recoveryMode = input.recoveryMode !== undefined ? input.recoveryMode : false;
    
    // SSMリソースを作成
    const ssmResources = createJenkinsControllerSSMResources(
        input.projectName,
        input.environment,
        jenkinsVersion,
        input.color,
        recoveryMode,
        dependencies
    );

    // ユーザーデータの変数を設定
    const userDataVariables = {
        PROJECT_NAME: input.projectName,
        ENVIRONMENT: input.environment,
        JENKINS_VERSION: jenkinsVersion,
        JENKINS_COLOR: input.color,
        JENKINS_MODE: recoveryMode ? "recovery" : "normal",
        EFS_ID: input.efsFileSystemId || '',
    };

    // 別ファイルからユーザーデータスクリプトを読み込み、変数を置換
    const userDataContent = prepareUserData('../../../../scripts/jenkins/shell/controller-user-data.sh', userDataVariables);

    // 最新のAmazon Linux 2023 AMIを取得
    const ami = pulumi.output(aws.ec2.getAmi({
        mostRecent: true,
        owners: ["amazon"],
        filters: [{
            name: "name",
            values: ["al2023-ami-*-kernel-*-x86_64"],
        }],
    }));

    // IAMロール作成（Jenkins用）- SSM権限を追加
    let jenkinsRole = new aws.iam.Role(`${input.projectName}-jenkins-role-${input.color}`, {
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
            Name: `${input.projectName}-jenkins-role-${input.color}-${input.environment}`,
            Environment: input.environment,
            Color: input.color,
        },
    });

    // 依存関係を設定
    if (dependencies && dependencies.length > 0) {
        jenkinsRole = dependsOn(jenkinsRole, dependencies);
    }

    // マネージドポリシーのアタッチ
    const ssmPolicy = new aws.iam.RolePolicyAttachment(`${input.projectName}-jenkins-ssm-policy-${input.color}`, {
        role: jenkinsRole.name,
        policyArn: "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
    });
    
    const efsPolicy = new aws.iam.RolePolicyAttachment(`${input.projectName}-jenkins-efs-policy-${input.color}`, {
        role: jenkinsRole.name,
        policyArn: "arn:aws:iam::aws:policy/AmazonElasticFileSystemClientReadWriteAccess",
    });

    // SSM関連ポリシー（ドキュメント実行とパラメータ読み取り用）
    const ssmCustomPolicy = new aws.iam.Policy(`${input.projectName}-jenkins-ssm-custom-policy-${input.color}`, {
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
                        `arn:aws:ssm:*:*:parameter/${input.projectName}/${input.environment}/jenkins/status/*`
                    ]
                }
            ]
        }),
    });

    const ssmCustomPolicyAttachment = new aws.iam.RolePolicyAttachment(`${input.projectName}-jenkins-ssm-custom-policy-attachment-${input.color}`, {
        role: jenkinsRole.name,
        policyArn: ssmCustomPolicy.arn,
    });

    // 依存関係を設定
    const rolePolicyAttachments = [
        dependsOn(ssmPolicy, [jenkinsRole]),
        dependsOn(efsPolicy, [jenkinsRole]),
        dependsOn(ssmCustomPolicyAttachment, [jenkinsRole, ssmCustomPolicy])
    ];

    // Jenkins用インスタンスプロファイル
    let jenkinsInstanceProfile = new aws.iam.InstanceProfile(`${input.projectName}-jenkins-profile-${input.color}`, {
        role: jenkinsRole.name,
        tags: {
            Environment: input.environment,
            Color: input.color,
        },
    });

    // 依存関係を設定
    jenkinsInstanceProfile = dependsOn(jenkinsInstanceProfile, [jenkinsRole, ...rolePolicyAttachments]);

    // ユーザーデータをBase64エンコード
    const userData = userDataContent.apply(script => 
        Buffer.from(script).toString("base64")
    );

    // EC2インスタンスの作成
    let jenkinsInstance = new aws.ec2.Instance(`${input.projectName}-jenkins-${input.color}`, {
        ami: ami.id,
        instanceType: instanceType,
        subnetId: input.subnetId,
        vpcSecurityGroupIds: [input.securityGroupId],
        keyName: keyName,
        iamInstanceProfile: jenkinsInstanceProfile.name,
        userData: userData,
        rootBlockDevice: {
            volumeSize: 50,
            volumeType: "gp3",
            deleteOnTermination: true,
            encrypted: true,
        },
        tags: {
            Name: `${input.projectName}-jenkins-${input.color}-${input.environment}`,
            Environment: input.environment,
            Color: input.color,
            Role: "jenkins-master",
        },
    });

    // 依存関係を設定（SSMリソースへの依存を追加）
    const allDependencies = [
        ...(dependencies || []), 
        jenkinsInstanceProfile,
        ...Object.values(ssmResources.parameters),
        ...Object.values(ssmResources.documents)
    ];
    
    jenkinsInstance = dependsOn(jenkinsInstance, allDependencies);

    // ターゲットグループへの登録
    const targetGroupAttachment = new aws.lb.TargetGroupAttachment(`${input.projectName}-jenkins-tg-attachment-${input.color}`, {
        targetGroupArn: input.targetGroupArn,
        targetId: jenkinsInstance.id,
        port: 8080,
    });

    return {
        jenkinsInstance,
        jenkinsRole,
        instanceProfile: jenkinsInstanceProfile,
        targetGroupAttachment,
        ssmParameters: ssmResources.parameters,
        ssmDocuments: ssmResources.documents,
    };
}

// EFSファイルシステムを作成する関数
export function createJenkinsEfs(
    projectName: string, 
    environment: string, 
    vpcId: pulumi.Input<string>, 
    securityGroupId: pulumi.Input<string>, 
    subnetIds: pulumi.Input<string>[],
    dependencies?: pulumi.Resource[]
) {
    // EFSセキュリティグループ - 既に定義済みのため、ここでは使用するだけ
    const efsSecurityGroupId = securityGroupId;

    // EFSファイルシステム
    let efsFileSystem = new aws.efs.FileSystem(`${projectName}-efs`, {
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

    // 依存関係を設定
    if (dependencies && dependencies.length > 0) {
        efsFileSystem = dependsOn(efsFileSystem, dependencies);
    }

    // サブネットごとにマウントターゲットを作成
    const mountTargets = subnetIds.map((subnetId, index) => {
        const mountTarget = new aws.efs.MountTarget(`${projectName}-efs-mt-${index}`, {
            fileSystemId: efsFileSystem.id,
            subnetId: subnetId,
            securityGroups: [efsSecurityGroupId],
        });
        
        // 依存関係を設定
        if (dependencies && dependencies.length > 0) {
            return dependsOn(mountTarget, [efsFileSystem, ...dependencies]);
        }
        return dependsOn(mountTarget, [efsFileSystem]);
    });

    // EFSアクセスポイント
    let jenkinsAccessPoint = new aws.efs.AccessPoint(`${projectName}-jenkins-ap`, {
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
    
    // 依存関係を設定
    jenkinsAccessPoint = dependsOn(jenkinsAccessPoint, [efsFileSystem]);

    return {
        efsFileSystem,
        mountTargets,
        jenkinsAccessPoint,
    };
}