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

// SSMドキュメント（Gitリポジトリ更新用）- ログ出力対応版
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
    },
});

// SSMドキュメント（インストール用）- ログ出力対応版
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
                        "# エラーハンドリングを設定",
                        "set -e",
                        "set -o pipefail",
                        "",
                        "# 環境変数の設定",
                        "export PROJECT_NAME={{ProjectName}}",
                        "export ENVIRONMENT={{Environment}}",
                        "export JENKINS_VERSION={{JenkinsVersion}}",
                        "export JENKINS_COLOR={{JenkinsColor}}",
                        "",
                        "echo '===== Starting Jenkins Installation ====='",
                        "echo \"Project: $PROJECT_NAME\"",
                        "echo \"Environment: $ENVIRONMENT\"",
                        "echo \"Jenkins Version: $JENKINS_VERSION\"",
                        "echo \"Jenkins Color: $JENKINS_COLOR\"",
                        "",
                        "# スクリプトの存在確認",
                        "SCRIPT_PATH=/root/infrastructure-as-code/scripts/jenkins/shell/controller-install.sh",
                        "if [ ! -f \"$SCRIPT_PATH\" ]; then",
                        "  echo \"ERROR: Script not found: $SCRIPT_PATH\"",
                        "  exit 1",
                        "fi",
                        "",
                        "# スクリプト実行",
                        "echo 'Executing Jenkins installation script...'",
                        "bash $SCRIPT_PATH 2>&1 || EXIT_CODE=$?",
                        "",
                        "# インストール状態確認",
                        "echo ''",
                        "echo '===== Installation Result ====='",
                        "if rpm -q jenkins >/dev/null 2>&1; then",
                        "  JENKINS_VERSION=$(rpm -q jenkins --queryformat '%{VERSION}')",
                        "  echo \"SUCCESS: Jenkins $JENKINS_VERSION is installed\"",
                        "else",
                        "  echo \"ERROR: Jenkins installation failed\"",
                        "  exit 1",
                        "fi",
                        "",
                        "# エラーがあった場合は終了",
                        "if [ ! -z \"$EXIT_CODE\" ] && [ \"$EXIT_CODE\" -ne 0 ]; then",
                        "  echo \"ERROR: Installation script failed with exit code: $EXIT_CODE\"",
                        "  exit $EXIT_CODE",
                        "fi",
                        "",
                        "echo 'Jenkins installation completed successfully'",
                        "exit 0"
                    ]
                }
            }
        ]
    }),
    tags: {
        Environment: environment,
    },
});

// SSMドキュメント（EFSマウント用）- ログ出力対応版
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
                        "# エラーハンドリングを設定",
                        "set -e",
                        "set -o pipefail",
                        "",
                        "# 環境変数の設定",
                        "export PROJECT_NAME={{ProjectName}}",
                        "export ENVIRONMENT={{Environment}}",
                        "export EFS_ID={{EfsId}}",
                        "export AWS_REGION={{Region}}",
                        "",
                        "echo '===== Starting EFS Mount ====='",
                        "echo \"EFS ID: $EFS_ID\"",
                        "echo \"AWS Region: $AWS_REGION\"",
                        "",
                        "# EFS関連パッケージの確認",
                        "if ! rpm -q amazon-efs-utils >/dev/null 2>&1; then",
                        "  echo 'Installing amazon-efs-utils...'",
                        "  dnf install -y amazon-efs-utils || yum install -y amazon-efs-utils",
                        "fi",
                        "",
                        "# スクリプトの存在確認",
                        "SCRIPT_PATH=/root/infrastructure-as-code/scripts/jenkins/shell/controller-mount-efs.sh",
                        "if [ ! -f \"$SCRIPT_PATH\" ]; then",
                        "  echo \"ERROR: Script not found: $SCRIPT_PATH\"",
                        "  exit 1",
                        "fi",
                        "",
                        "# スクリプト実行",
                        "echo 'Executing EFS mount script...'",
                        "bash $SCRIPT_PATH 2>&1 || EXIT_CODE=$?",
                        "",
                        "# マウント状態確認",
                        "echo ''",
                        "echo '===== Mount Result ====='", 
                        "if df -h | grep -i efs >/dev/null 2>&1; then",
                        "  echo 'SUCCESS: EFS is mounted'",
                        "  df -h | grep -i efs",
                        "else",
                        "  echo 'ERROR: EFS mount failed'",
                        "  # エラー時のみ追加情報を表示",
                        "  echo ''",
                        "  echo 'Checking EFS mount helper log:'",
                        "  tail -20 /var/log/amazon/efs/mount.log 2>/dev/null || echo 'No EFS helper log found'",
                        "fi",
                        "",
                        "# エラーがあった場合は終了",
                        "if [ ! -z \"$EXIT_CODE\" ] && [ \"$EXIT_CODE\" -ne 0 ]; then",
                        "  echo \"ERROR: Mount script failed with exit code: $EXIT_CODE\"",
                        "  exit $EXIT_CODE",
                        "fi",
                        "",
                        "echo 'EFS mount completed successfully'",
                        "exit 0"
                    ]
                }
            }
        ]
    }),
    tags: {
        Environment: environment,
    },
});

// SSMドキュメント（設定用）- ログ出力対応版
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
                        "# エラーハンドリングを設定",
                        "set -e",
                        "set -o pipefail",
                        "",
                        "# 環境変数の設定",
                        "export PROJECT_NAME={{ProjectName}}",
                        "export ENVIRONMENT={{Environment}}",
                        "export JENKINS_MODE={{JenkinsMode}}",
                        "export JENKINS_COLOR={{JenkinsColor}}",
                        "",
                        "echo '===== Starting Jenkins Configuration ====='",
                        "echo \"Mode: $JENKINS_MODE\"",
                        "echo \"Color: $JENKINS_COLOR\"",
                        "",
                        "# スクリプトの存在確認",
                        "SCRIPT_PATH=/root/infrastructure-as-code/scripts/jenkins/shell/controller-configure.sh",
                        "if [ ! -f \"$SCRIPT_PATH\" ]; then",
                        "  echo \"ERROR: Script not found: $SCRIPT_PATH\"",
                        "  exit 1",
                        "fi",
                        "",
                        "# スクリプト実行",
                        "echo 'Executing Jenkins configuration script...'",
                        "bash $SCRIPT_PATH 2>&1 || EXIT_CODE=$?",
                        "",
                        "# 設定結果確認",
                        "echo ''",
                        "echo '===== Configuration Result ====='",
                        "if [ -d /mnt/efs/jenkins ]; then",
                        "  echo 'SUCCESS: Jenkins directory configured'",
                        "  ls -la /mnt/efs/jenkins | head -10",
                        "else",
                        "  echo 'WARNING: Jenkins directory not found at /mnt/efs/jenkins'",
                        "fi",
                        "",
                        "# エラーがあった場合は終了",
                        "if [ ! -z \"$EXIT_CODE\" ] && [ \"$EXIT_CODE\" -ne 0 ]; then",
                        "  echo \"ERROR: Configuration script failed with exit code: $EXIT_CODE\"",
                        "  exit $EXIT_CODE",
                        "fi",
                        "",
                        "echo 'Jenkins configuration completed successfully'",
                        "exit 0"
                    ]
                }
            }
        ]
    }),
    tags: {
        Environment: environment,
    },
});


// SSMドキュメント（起動用）- ログ出力対応版
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
                        "# エラーハンドリングを設定",
                        "set -e",
                        "set -o pipefail",
                        "",
                        "# 環境変数の設定",
                        "export PROJECT_NAME={{ProjectName}}",
                        "export ENVIRONMENT={{Environment}}",
                        "export JENKINS_COLOR={{JenkinsColor}}",
                        "",
                        "echo '===== Starting Jenkins Service ====='",
                        "echo \"Project: $PROJECT_NAME\"",
                        "echo \"Environment: $ENVIRONMENT\"",
                        "echo \"Color: $JENKINS_COLOR\"",
                        "",
                        "# スクリプトの存在確認",
                        "SCRIPT_PATH=/root/infrastructure-as-code/scripts/jenkins/shell/controller-startup.sh",
                        "if [ ! -f \"$SCRIPT_PATH\" ]; then",
                        "  echo \"ERROR: Script not found: $SCRIPT_PATH\"",
                        "  exit 1",
                        "fi",
                        "",
                        "# スクリプト実行",
                        "echo 'Executing Jenkins startup script...'",
                        "bash $SCRIPT_PATH 2>&1 || EXIT_CODE=$?",
                        "",
                        "# サービス状態確認",
                        "echo ''",
                        "echo '===== Service Status ====='",
                        "if systemctl is-active jenkins >/dev/null 2>&1; then",
                        "  echo 'SUCCESS: Jenkins service is active'",
                        "  systemctl status jenkins --no-pager | head -20",
                        "else",
                        "  echo 'ERROR: Jenkins service is not active'",
                        "  systemctl status jenkins --no-pager || true",
                        "fi",
                        "",
                        "# エラーがあった場合は終了",
                        "if [ ! -z \"$EXIT_CODE\" ] && [ \"$EXIT_CODE\" -ne 0 ]; then",
                        "  echo \"ERROR: Startup script failed with exit code: $EXIT_CODE\"",
                        "  exit $EXIT_CODE",
                        "fi",
                        "",
                        "echo 'Jenkins startup completed successfully'",
                        "exit 0"
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
