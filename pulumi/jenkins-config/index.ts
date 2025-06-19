/**
 * pulumi/jenkins-config/index.ts
 * 
 * Jenkinsの設定関連リソースを構築するPulumiスクリプト
 * 汎用的なスクリプト実行用SSMドキュメントとパラメータのみを管理
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "jenkins-infra";
const environment = pulumi.getStack();

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
            // 個別の環境変数パラメータ
            EfsId: {
                type: "String",
                default: "",
                description: "EFS File System ID"
            },
            AwsRegion: {
                type: "String",
                default: "",
                description: "AWS Region"
            },
            JenkinsVersion: {
                type: "String",
                default: "",
                description: "Jenkins version"
            },
            JenkinsColor: {
                type: "String",
                default: "",
                description: "Jenkins color (blue/green)"
            },
            JenkinsMode: {
                type: "String",
                default: "",
                description: "Jenkins mode (normal/recovery)"
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
                        "export REPO_PATH='/root/infrastructure-as-code'",
                        "",
                        "# リージョンの取得",
                        "TOKEN=$(curl -s -X PUT \"http://169.254.169.254/latest/api/token\" -H \"X-aws-ec2-metadata-token-ttl-seconds: 21600\")",
                        "export AWS_REGION=$(curl -s -H \"X-aws-ec2-metadata-token: $TOKEN\" http://169.254.169.254/latest/meta-data/placement/region)",
                        "export AWS_DEFAULT_REGION=$AWS_REGION",
                        "",
                        "# 個別パラメータから環境変数を設定",
                        "[ -n \"{{EfsId}}\" ] && export EFS_ID=\"{{EfsId}}\"",
                        "[ -n \"{{AwsRegion}}\" ] && export AWS_REGION=\"{{AwsRegion}}\"",
                        "[ -n \"{{JenkinsVersion}}\" ] && export JENKINS_VERSION=\"{{JenkinsVersion}}\"",
                        "[ -n \"{{JenkinsColor}}\" ] && export JENKINS_COLOR=\"{{JenkinsColor}}\"",
                        "[ -n \"{{JenkinsMode}}\" ] && export JENKINS_MODE=\"{{JenkinsMode}}\"",
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
                        "echo \"Environment variables set:\"",
                        "[ -n \"$EFS_ID\" ] && echo \"  EFS_ID=$EFS_ID\"",
                        "[ -n \"$JENKINS_VERSION\" ] && echo \"  JENKINS_VERSION=$JENKINS_VERSION\"",
                        "[ -n \"$JENKINS_COLOR\" ] && echo \"  JENKINS_COLOR=$JENKINS_COLOR\"",
                        "[ -n \"$JENKINS_MODE\" ] && echo \"  JENKINS_MODE=$JENKINS_MODE\"",
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
