/**
 * pulumi/jenkins-config/index.ts
 * 
 * Jenkinsの設定関連リソースを構築するPulumiスクリプト
 * SSMドキュメント、パラメータストア、共有設定などに特化
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as fs from "fs";
import * as path from "path";

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "jenkins-infra";
const environment = pulumi.getStack();

// スクリプトファイルの読み込み関数
function loadScript(scriptPath: string): string {
    try {
        return fs.readFileSync(path.resolve(__dirname, scriptPath), 'utf8');
    } catch (error) {
        console.error(`Error loading script from ${scriptPath}:`, error);
        throw error;
    }
}

// Jenkins設定用SSMパラメータ
const jenkinsVersionParam = new aws.ssm.Parameter(`${projectName}-jenkins-version`, {
    name: `/${projectName}/${environment}/jenkins/version`,
    type: "String",
    value: config.get("jenkinsVersion") || "latest",
    description: "Jenkins version to be installed",
    tags: {
        Environment: environment,
    },
});

const jenkinsModeParam = new aws.ssm.Parameter(`${projectName}-jenkins-mode`, {
    name: `/${projectName}/${environment}/jenkins/mode`,
    type: "String",
    value: config.getBoolean("recoveryMode") ? "recovery" : "normal",
    description: "Jenkins operating mode (normal/recovery)",
    tags: {
        Environment: environment,
    },
});

// Groovyスクリプトのパラメータ
const disableCliGroovyParam = new aws.ssm.Parameter(`${projectName}-jenkins-disable-cli-groovy`, {
    name: `/${projectName}/${environment}/jenkins/groovy/disable-cli`,
    type: "String",
    value: loadScript('../scripts/jenkins/groovy/disable-cli.groovy'),
    description: "Jenkins Groovy script to disable CLI",
    tier: "Standard",
    tags: {
        Environment: environment,
    },
});

const basicSettingsGroovyParam = new aws.ssm.Parameter(`${projectName}-jenkins-basic-settings-groovy`, {
    name: `/${projectName}/${environment}/jenkins/groovy/basic-settings`,
    type: "String",
    value: loadScript('../scripts/jenkins/groovy/basic-settings.groovy'),
    description: "Jenkins Groovy script for basic settings",
    tier: "Standard",
    tags: {
        Environment: environment,
    },
});

const recoveryModeGroovyParam = new aws.ssm.Parameter(`${projectName}-jenkins-recovery-mode-groovy`, {
    name: `/${projectName}/${environment}/jenkins/groovy/recovery-mode`,
    type: "String",
    value: loadScript('../scripts/jenkins/groovy/recovery-mode.groovy'),
    description: "Jenkins Groovy script for recovery mode",
    tier: "Standard",
    tags: {
        Environment: environment,
    },
});

// SSMドキュメント（Gitリポジトリ更新用）
const jenkinsUpdateRepoDocument = new aws.ssm.Document(`${projectName}-jenkins-update-repo`, {
    name: `${projectName}-jenkins-update-repo-${environment}`,
    documentType: "Command",
    content: JSON.stringify({
        schemaVersion: "2.2",
        description: "Update Git repository for Jenkins scripts",
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
            GitBranch: {
                type: "String",
                default: "main",
                description: "Git branch to checkout"
            },
            GitRepo: {
                type: "String",
                default: "https://github.com/your-org/infrastructure-as-code.git",
                description: "Git repository URL"
            }
        },
        mainSteps: [
            {
                action: "aws:runShellScript",
                name: "updateRepo",
                inputs: {
                    runCommand: [
                        "#!/bin/bash",
                        "set -e",
                        "export PROJECT_NAME={{ProjectName}}",
                        "export ENVIRONMENT={{Environment}}",
                        "export GIT_BRANCH={{GitBranch}}",
                        "export GIT_REPO={{GitRepo}}",
                        "echo \"Updating repository for $PROJECT_NAME in environment $ENVIRONMENT\"",
                        "echo \"Using branch: $GIT_BRANCH\"",
                        "cd /root",
                        "# Clone repository if it doesn't exist",
                        "if [ ! -d \"infrastructure-as-code\" ]; then",
                        "  echo \"Cloning repository from $GIT_REPO\"",
                        "  git clone $GIT_REPO infrastructure-as-code",
                        "  cd infrastructure-as-code",
                        "else",
                        "  echo \"Repository already exists, updating\"",
                        "  cd infrastructure-as-code",
                        "  git fetch --all",
                        "fi",
                        "# Checkout and pull the specified branch",
                        "git checkout $GIT_BRANCH",
                        "git pull origin $GIT_BRANCH",
                        "echo \"Repository updated to branch $GIT_BRANCH\"",
                        "git log -1 --format=\"%h %s by %an (%ar)\"",
                        "echo \"Making shell scripts executable\"",
                        "find scripts -name \"*.sh\" -exec chmod +x {} \\;",
                        "echo \"Git repository update completed\""
                    ]
                }
            }
        ]
    }),
    tags: {
        Environment: environment,
    },
});

// SSMドキュメント（インストール用）
const jenkinsInstallDocument = new aws.ssm.Document(`${projectName}-jenkins-install`, {
    name: `${projectName}-jenkins-install-${environment}`,
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
                default: "latest",
                description: "Jenkins version to install"
            },
            JenkinsColor: {
                type: "String",
                default: "blue",
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
    },
});

// SSMドキュメント（EFSマウント用）
const jenkinsMountEfsDocument = new aws.ssm.Document(`${projectName}-jenkins-mount-efs`, {
    name: `${projectName}-jenkins-mount-efs-${environment}`,
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
    },
});

// SSMドキュメント（設定用）
const jenkinsConfigureDocument = new aws.ssm.Document(`${projectName}-jenkins-configure`, {
    name: `${projectName}-jenkins-configure-${environment}`,
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
                default: "normal",
                allowedValues: ["normal", "recovery"],
                description: "Jenkins mode (normal/recovery)"
            },
            JenkinsColor: {
                type: "String",
                default: "blue",
                allowedValues: ["blue", "green"],
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
    },
});

// SSMドキュメント（起動用）
const jenkinsStartupDocument = new aws.ssm.Document(`${projectName}-jenkins-startup`, {
    name: `${projectName}-jenkins-startup-${environment}`,
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
                default: "blue",
                allowedValues: ["blue", "green"],
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
    },
});

// エクスポート
export const parametersPath = `/${projectName}/${environment}/jenkins`;
export const ssmDocuments = {
    updateRepo: jenkinsUpdateRepoDocument.name,
    install: jenkinsInstallDocument.name,
    mountEfs: jenkinsMountEfsDocument.name,
    configure: jenkinsConfigureDocument.name,
    startup: jenkinsStartupDocument.name,
};
