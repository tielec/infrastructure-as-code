/**
 * pulumi/jenkins-config/index.ts
 * 
 * Jenkinsの設定関連リソースを構築するPulumiスクリプト
 * 汎用的なスクリプト実行用SSMドキュメントとパラメータのみを管理
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
const jenkinsRecoveryModeParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/jenkins-recovery-mode`,
});
const gitRepoParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/git-repo`,
});
const gitBranchParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/git-branch`,
});

// 設定値を変数に設定
const projectName = pulumi.output(projectNameParam).apply(p => p.value);
const jenkinsVersion = pulumi.output(jenkinsVersionParam).apply(p => p.value);
const jenkinsRecoveryMode = pulumi.output(jenkinsRecoveryModeParam).apply(p => p.value === "true");
const gitRepo = pulumi.output(gitRepoParam).apply(p => p.value);
const gitBranch = pulumi.output(gitBranchParam).apply(p => p.value);

// タイムスタンプを生成（ドキュメント名の一意性を保証）
const timestamp = new Date().toISOString().slice(0, 10).replace(/-/g, '');

// Jenkins設定用SSMパラメータ（ステータス情報を保存）
const jenkinsStatusParam = new aws.ssm.Parameter(`jenkins-status`, {
    name: `${ssmPrefix}/jenkins/status`,
    type: "String",
    value: "initializing",
    description: "Current Jenkins status",
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

const jenkinsConfiguredParam = new aws.ssm.Parameter(`jenkins-configured`, {
    name: `${ssmPrefix}/jenkins/configured`,
    type: "String",
    value: "false",
    description: "Jenkins configuration status",
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// 汎用的なスクリプト実行用SSMドキュメント（jenkins-applicationと同じ構造）
const jenkinsConfigExecuteScriptDocument = new aws.ssm.Document(`jenkins-config-execute-script`, {
    name: `jenkins-infra-jenkins-config-execute-script-${environment}`,
    documentType: "Command",
    documentFormat: "JSON",
    targetType: "/AWS::EC2::Instance",
    versionName: `v${timestamp}`,
    content: JSON.stringify({
        schemaVersion: "2.2",
        description: "Execute script from Git repository on Jenkins instance",
        parameters: {
            ScriptPath: {
                type: "String",
                description: "Path to script relative to repository root"
            },
            ScriptArgs: {
                type: "String",
                default: "",
                description: "Arguments to pass to the script"
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
                        "export PROJECT_NAME='jenkins-infra'",
                        "export ENVIRONMENT='" + environment + "'",
                        "export JENKINS_HOME='/mnt/efs/jenkins'",
                        "export REPO_PATH='/root/infrastructure-as-code'",
                        "",
                        "# リージョンの取得",
                        "TOKEN=$(curl -s -X PUT \"http://169.254.169.254/latest/api/token\" -H \"X-aws-ec2-metadata-token-ttl-seconds: 21600\")",
                        "export AWS_REGION=$(curl -s -H \"X-aws-ec2-metadata-token: $TOKEN\" http://169.254.169.254/latest/meta-data/placement/region)",
                        "export AWS_DEFAULT_REGION=$AWS_REGION",
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
                        "echo \"Executing: {{ScriptPath}} {{ScriptArgs}}\"",
                        "echo \"Environment: PROJECT_NAME=$PROJECT_NAME, ENVIRONMENT=$ENVIRONMENT, AWS_REGION=$AWS_REGION\"",
                        "",
                        "chmod +x \"{{ScriptPath}}\"",
                        "bash \"{{ScriptPath}}\" {{ScriptArgs}}"
                    ]
                }
            }
        ]
    }),
    tags: {
        Environment: environment,
    },
}, {
    replaceOnChanges: ["content", "targetType"]
});

// Gitリポジトリ更新用SSMドキュメント（これは残す）
const jenkinsUpdateRepoDocument = new aws.ssm.Document(`jenkins-update-repo`, {
    name: `jenkins-infra-jenkins-update-repo-${environment}`,
    documentType: "Command",
    documentFormat: "JSON",
    content: JSON.stringify({
        schemaVersion: "2.2",
        description: "Update Git repository for Jenkins scripts",
        parameters: {
            ProjectName: {
                type: "String",
                default: "jenkins-infra",
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

// SSMドキュメント名をSSMパラメータに保存
const updateRepoDocumentNameParam = new aws.ssm.Parameter(`update-repo-document-name`, {
    name: `${ssmPrefix}/config/update-repo-document-name`,
    type: "String",
    value: jenkinsUpdateRepoDocument.name,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

const executeScriptDocumentNameParam = new aws.ssm.Parameter(`execute-script-document-name`, {
    name: `${ssmPrefix}/config/execute-script-document-name`,
    type: "String",
    value: jenkinsConfigExecuteScriptDocument.name,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// パラメータパスをSSMパラメータに保存
const parametersPathParam = new aws.ssm.Parameter(`parameters-path`, {
    name: `${ssmPrefix}/config/parameters-path`,
    type: "String",
    value: `${ssmPrefix}/jenkins`,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "config",
    },
});

// エクスポート
export const parametersPath = `${ssmPrefix}/jenkins`;
export const ssmDocuments = {
    updateRepo: jenkinsUpdateRepoDocument.name,
    executeScript: jenkinsConfigExecuteScriptDocument.name,
};
export const statusParameterName = jenkinsStatusParam.name;
export const configuredParameterName = jenkinsConfiguredParam.name;
