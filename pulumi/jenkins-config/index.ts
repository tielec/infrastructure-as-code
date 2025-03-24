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

// バージョン管理のためのタイムスタンプ（ドキュメント名に含める）
const timestamp = new Date().toISOString().slice(0, 16).replace(/[-:]/g, "");

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
    value: loadScript('../../scripts/jenkins/groovy/disable-cli.groovy'),
    description: "Jenkins Groovy script to disable CLI",
    tier: "Standard",
    tags: {
        Environment: environment,
    },
});

const basicSettingsGroovyParam = new aws.ssm.Parameter(`${projectName}-jenkins-basic-settings-groovy`, {
    name: `/${projectName}/${environment}/jenkins/groovy/basic-settings`,
    type: "String",
    value: loadScript('../../scripts/jenkins/groovy/basic-settings.groovy'),
    description: "Jenkins Groovy script for basic settings",
    tier: "Standard",
    tags: {
        Environment: environment,
    },
});

const recoveryModeGroovyParam = new aws.ssm.Parameter(`${projectName}-jenkins-recovery-mode-groovy`, {
    name: `/${projectName}/${environment}/jenkins/groovy/recovery-mode`,
    type: "String",
    value: loadScript('../../scripts/jenkins/groovy/recovery-mode.groovy'),
    description: "Jenkins Groovy script for recovery mode",
    tier: "Standard",
    tags: {
        Environment: environment,
    },
});

// SSMドキュメント（Gitリポジトリ更新用）- 修正版
const jenkinsUpdateRepoDocument = new aws.ssm.Document(`${projectName}-jenkins-update-repo-${timestamp}`, {
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
                        "  # リセットして強制的に最新状態にする",
                        "  echo \"Resetting any local changes\"",
                        "  git reset --hard",
                        "  git clean -fd",
                        "  git fetch --all",
                        "fi",
                        "# Checkout and pull the specified branch",
                        "git checkout $GIT_BRANCH",
                        "git reset --hard origin/$GIT_BRANCH",
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
        Version: timestamp
    },
});

// SSMドキュメント（インストール用）- ログ出力対応版
const jenkinsInstallDocument = new aws.ssm.Document(`${projectName}-jenkins-install-${timestamp}`, {
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
                        "# 既存のログをクリア",
                        "rm -f /var/log/jenkins-install.log",
                        "# スクリプト実行",
                        `source /root/infrastructure-as-code/scripts/jenkins/shell/controller-install.sh`,
                        "# ログファイルの内容を表示",
                        "echo '===== BEGIN JENKINS INSTALL LOG ====='",
                        "cat /var/log/jenkins-install.log 2>/dev/null || echo 'No log file found'",
                        "echo '===== END JENKINS INSTALL LOG ====='",
                        "# インストール状態確認",
                        "echo '===== JENKINS INSTALL STATUS ====='",
                        "rpm -q jenkins || echo 'Jenkins not installed'",
                        "# 終了ステータス確認",
                        "exit ${PIPESTATUS[0]}"
                    ]
                }
            }
        ]
    }),
    tags: {
        Environment: environment,
        Version: timestamp
    },
});

// SSMドキュメント（EFSマウント用）- ログ出力対応版
const jenkinsMountEfsDocument = new aws.ssm.Document(`${projectName}-jenkins-mount-efs-${timestamp}`, {
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
                        "# 既存のログをクリア",
                        "rm -f /var/log/efs-mount.log",
                        "# スクリプト実行",
                        `source /root/infrastructure-as-code/scripts/jenkins/shell/controller-mount-efs.sh`,
                        "# ログファイルの内容を表示",
                        "echo '===== BEGIN EFS MOUNT LOG ====='",
                        "cat /var/log/efs-mount.log 2>/dev/null || echo 'No log file found'",
                        "echo '===== END EFS MOUNT LOG ====='",
                        "# マウント状態確認",
                        "echo '===== MOUNT STATUS ====='", 
                        "df -h | grep -i efs || echo 'EFS not mounted'",
                        "# 終了ステータス確認",
                        "exit ${PIPESTATUS[0]}"
                    ]
                }
            }
        ]
    }),
    tags: {
        Environment: environment,
        Version: timestamp
    },
});

// SSMドキュメント（設定用）- ログ出力対応版
const jenkinsConfigureDocument = new aws.ssm.Document(`${projectName}-jenkins-configure-${timestamp}`, {
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
                        "# 既存のログをクリア",
                        "rm -f /var/log/jenkins-configure.log",
                        "# スクリプト実行",
                        `source /root/infrastructure-as-code/scripts/jenkins/shell/controller-configure.sh`,
                        "# ログファイルの内容を表示",
                        "echo '===== BEGIN JENKINS CONFIGURE LOG ====='",
                        "cat /var/log/jenkins-configure.log 2>/dev/null || echo 'No log file found'",
                        "echo '===== END JENKINS CONFIGURE LOG ====='",
                        "# Jenkinsディレクトリ確認",
                        "echo '===== JENKINS DIRECTORY STATUS ====='",
                        "ls -la /mnt/efs/jenkins",
                        "# 終了ステータス確認",
                        "exit ${PIPESTATUS[0]}"
                    ]
                }
            }
        ]
    }),
    tags: {
        Environment: environment,
        Version: timestamp
    },
});

// SSMドキュメント（起動用）- ログ出力対応版
const jenkinsStartupDocument = new aws.ssm.Document(`${projectName}-jenkins-startup-${timestamp}`, {
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
                        "# 既存のログをクリア",
                        "rm -f /var/log/jenkins-startup.log",
                        "# スクリプト実行",
                        `source /root/infrastructure-as-code/scripts/jenkins/shell/controller-startup.sh`,
                        "# ログファイルの内容を表示",
                        "echo '===== BEGIN JENKINS STARTUP LOG ====='",
                        "cat /var/log/jenkins-startup.log 2>/dev/null || echo 'No log file found'",
                        "echo '===== END JENKINS STARTUP LOG ====='",
                        "# Jenkins サービス状態確認",
                        "echo '===== JENKINS SERVICE STATUS ====='",
                        "systemctl status jenkins --no-pager || echo 'Jenkins service not found'",
                        "# 終了ステータス確認",
                        "exit ${PIPESTATUS[0]}"
                    ]
                }
            }
        ]
    }),
    tags: {
        Environment: environment,
        Version: timestamp
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
