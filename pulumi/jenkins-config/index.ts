/**
 * pulumi/jenkins-config/index.ts
 * 
 * Jenkinsの設定関連リソースを構築するPulumiスクリプト
 * 汎用的なスクリプト実行用SSMドキュメントを使用
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

// 汎用的なスクリプト実行用SSMドキュメント（jenkins-config専用）
const jenkinsConfigExecuteScriptDocument = new aws.ssm.Document(`${projectName}-jenkins-config-execute-script`, {
    name: `${projectName}-jenkins-config-execute-script-${environment}`,
    documentType: "Command",
    documentFormat: "JSON",
    content: JSON.stringify({
        schemaVersion: "2.2",
        description: "Execute script from Git repository on Jenkins instance",
        parameters: {
            ScriptPath: {
                type: "String",
                description: "Path to script relative to repository root"
            },
            EnvVars: {
                type: "String",
                default: "",
                description: "Environment variables in KEY=VALUE format, separated by spaces"
            },
            WorkingDirectory: {
                type: "String",
                default: "/root/infrastructure-as-code",
                description: "Working directory for script execution"
            }
        },
        mainSteps: [
            {
                action: "aws:runShellScript",
                name: "executeScript",
                inputs: {
                    runCommand: [
                        "#!/bin/bash",
                        "set -e",
                        "",
                        "# 環境変数の設定",
                        "export PROJECT_NAME='" + projectName + "'",
                        "export ENVIRONMENT='" + environment + "'",
                        "export JENKINS_HOME='/mnt/efs/jenkins'",
                        "",
                        "# リージョンの取得",
                        "TOKEN=$(curl -s -X PUT \"http://169.254.169.254/latest/api/token\" -H \"X-aws-ec2-metadata-token-ttl-seconds: 21600\")",
                        "export AWS_REGION=$(curl -s -H \"X-aws-ec2-metadata-token: $TOKEN\" http://169.254.169.254/latest/meta-data/placement/region)",
                        "export AWS_DEFAULT_REGION=$AWS_REGION",
                        "",
                        "# 渡された環境変数を設定",
                        "if [ -n \"{{EnvVars}}\" ]; then",
                        "  for env_var in {{EnvVars}}; do",
                        "    export \"$env_var\"",
                        "  done",
                        "fi",
                        "",
                        "# 作業ディレクトリに移動",
                        "cd {{WorkingDirectory}}",
                        "",
                        "# スクリプトの存在確認",
                        "if [ ! -f \"{{ScriptPath}}\" ]; then",
                        "  echo \"ERROR: Script not found: {{ScriptPath}}\"",
                        "  exit 1",
                        "fi",
                        "",
                        "# スクリプトを実行",
                        "echo \"Executing: {{ScriptPath}}\"",
                        "echo \"Environment: PROJECT_NAME=$PROJECT_NAME, ENVIRONMENT=$ENVIRONMENT, AWS_REGION=$AWS_REGION\"",
                        "",
                        "chmod +x \"{{ScriptPath}}\"",
                        "bash \"{{ScriptPath}}\""
                    ]
                }
            }
        ]
    }),
    tags: {
        Environment: environment,
    },
});

// Gitリポジトリ更新用SSMドキュメント（これは残す）
const jenkinsUpdateRepoDocument = new aws.ssm.Document(`${projectName}-jenkins-update-repo`, {
    name: `${projectName}-jenkins-update-repo-${environment}`,
    documentType: "Command",
    documentFormat: "JSON",
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

// エクスポート
export const parametersPath = `/${projectName}/${environment}/jenkins`;
export const ssmDocuments = {
    updateRepo: jenkinsUpdateRepoDocument.name,
    executeScript: jenkinsConfigExecuteScriptDocument.name,
};
