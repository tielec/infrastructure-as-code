/**
 * pulumi/jenkins-application/index.ts
 * 
 * Jenkinsアプリケーション設定リソースを構築するPulumiスクリプト
 * SSMドキュメント、パラメータ、アプリケーション設定を管理
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as fs from "fs";
import * as path from "path";

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "jenkins-infra";
const environment = pulumi.getStack();
const jenkinsVersion = config.get("jenkinsVersion") || "latest";

// スクリプトファイルの読み込み関数
function loadScript(scriptPath: string): string {
    try {
        return fs.readFileSync(path.resolve(__dirname, scriptPath), 'utf8');
    } catch (error) {
        console.error(`Error loading script from ${scriptPath}:`, error);
        throw error;
    }
}

// プラグインインストールスクリプトをSSMパラメータとして保存
const installPluginsGroovyParam = new aws.ssm.Parameter(`${projectName}-jenkins-install-plugins-groovy`, {
    name: `/${projectName}/${environment}/jenkins/groovy/install-plugins`,
    type: "String",
    value: loadScript('../../scripts/jenkins/groovy/install-plugins.groovy'),
    description: "Jenkins Groovy script to install plugins",
    tier: "Advanced", // 大きなスクリプトの場合
    tags: {
        Environment: environment,
    },
});

// CLIユーザー作成スクリプトをSSMパラメータとして保存
const createCliUserGroovyParam = new aws.ssm.Parameter(`${projectName}-jenkins-create-cli-user-groovy`, {
    name: `/${projectName}/${environment}/jenkins/groovy/create-cli-user`,
    type: "String",
    value: loadScript('../../scripts/jenkins/groovy/create-cli-user.groovy'),
    description: "Jenkins Groovy script to create CLI user",
    tier: "Advanced",
    tags: {
        Environment: environment,
    },
});

// クレデンシャル設定スクリプトをSSMパラメータとして保存
const setupCredentialsGroovyParam = new aws.ssm.Parameter(`${projectName}-jenkins-setup-credentials-groovy`, {
    name: `/${projectName}/${environment}/jenkins/groovy/setup-credentials`,
    type: "String",
    value: loadScript('../../scripts/jenkins/groovy/setup-credentials.groovy'),
    description: "Jenkins Groovy script to setup credentials",
    tier: "Advanced",
    tags: {
        Environment: environment,
    },
});

// SSMドキュメント（バージョン更新用）
const jenkinsUpdateVersionDocument = new aws.ssm.Document(`${projectName}-jenkins-update-version`, {
    name: `${projectName}-jenkins-update-version-${environment}`,
    documentType: "Command",
    content: JSON.stringify({
        schemaVersion: "2.2",
        description: "Update Jenkins version",
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
            }
        },
        mainSteps: [
            {
                action: "aws:runShellScript",
                name: "updateJenkinsVersion",
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
                        "",
                        "echo '===== Starting Jenkins Version Update ====='",
                        "echo \"Target version: $JENKINS_VERSION\"",
                        "",
                        "# スクリプトの存在確認",
                        "SCRIPT_PATH=/root/infrastructure-as-code/scripts/jenkins/shell/application-update-version.sh",
                        "if [ ! -f \"$SCRIPT_PATH\" ]; then",
                        "  echo \"ERROR: Update script not found: $SCRIPT_PATH\"",
                        "  exit 1",
                        "fi",
                        "",
                        "# スクリプト実行",
                        "echo 'Executing Jenkins version update script...'",
                        "bash $SCRIPT_PATH 2>&1 || EXIT_CODE=$?",
                        "",
                        "# エラーがあった場合は終了",
                        "if [ ! -z \"$EXIT_CODE\" ] && [ \"$EXIT_CODE\" -ne 0 ]; then",
                        "  echo \"ERROR: Update script failed with exit code: $EXIT_CODE\"",
                        "  exit $EXIT_CODE",
                        "fi",
                        "",
                        "echo 'Jenkins version update completed successfully'",
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

// SSMドキュメント（プラグインインストール用）
const jenkinsInstallPluginsDocument = new aws.ssm.Document(`${projectName}-jenkins-install-plugins`, {
    name: `${projectName}-jenkins-install-plugins-${environment}`,
    documentType: "Command",
    content: JSON.stringify({
        schemaVersion: "2.2",
        description: "Install/Update Jenkins plugins",
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
            }
        },
        mainSteps: [
            {
                action: "aws:runShellScript",
                name: "installPlugins",
                inputs: {
                    runCommand: [
                        "#!/bin/bash",
                        "set -e",
                        "export PROJECT_NAME={{ProjectName}}",
                        "export ENVIRONMENT={{Environment}}",
                        "",
                        "echo '===== Installing Jenkins Plugins ====='",
                        "",
                        "# SSMパラメータからGroovyスクリプトを取得",
                        "SCRIPT_PATH=/mnt/efs/jenkins/init.groovy.d/install-plugins.groovy",
                        "aws ssm get-parameter \\",
                        "  --name \"/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/groovy/install-plugins\" \\",
                        "  --with-decryption \\",
                        "  --query \"Parameter.Value\" \\",
                        "  --output text > $SCRIPT_PATH",
                        "",
                        "chown jenkins:jenkins $SCRIPT_PATH",
                        "chmod 644 $SCRIPT_PATH",
                        "",
                        "# Jenkinsを再起動してプラグインをインストール",
                        "echo 'Restarting Jenkins to install plugins...'",
                        "systemctl restart jenkins",
                        "",
                        "# 起動を待機",
                        "echo 'Waiting for Jenkins to start...'",
                        "TIMEOUT=600",
                        "ELAPSED=0",
                        "while [ $ELAPSED -lt $TIMEOUT ]; do",
                        "  if curl -s -f http://localhost:8080/login > /dev/null; then",
                        "    echo 'Jenkins is running'",
                        "    break",
                        "  fi",
                        "  sleep 10",
                        "  ELAPSED=$((ELAPSED + 10))",
                        "done",
                        "",
                        "# プラグインインストールの完了を待機",
                        "echo 'Waiting for plugin installation to complete...'",
                        "sleep 60",
                        "",
                        "# スクリプトファイルを削除（次回起動時に実行されないように）",
                        "rm -f $SCRIPT_PATH",
                        "",
                        "echo 'Plugin installation completed'"
                    ]
                }
            }
        ]
    }),
    tags: {
        Environment: environment,
    },
});

// SSMドキュメント（Jenkins再起動用）
const jenkinsRestartDocument = new aws.ssm.Document(`${projectName}-jenkins-restart`, {
    name: `${projectName}-jenkins-restart-${environment}`,
    documentType: "Command",
    content: JSON.stringify({
        schemaVersion: "2.2",
        description: "Restart Jenkins service",
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
            }
        },
        mainSteps: [
            {
                action: "aws:runShellScript",
                name: "restartJenkins",
                inputs: {
                    runCommand: [
                        "#!/bin/bash",
                        "set -e",
                        "",
                        "echo '===== Restarting Jenkins Service ====='",
                        "",
                        "# 現在の状態を確認",
                        "echo 'Current Jenkins status:'",
                        "systemctl status jenkins --no-pager || true",
                        "",
                        "# Jenkinsを再起動",
                        "echo 'Restarting Jenkins...'",
                        "systemctl restart jenkins",
                        "",
                        "# 起動を待機",
                        "echo 'Waiting for Jenkins to start...'",
                        "TIMEOUT=300",
                        "ELAPSED=0",
                        "while [ $ELAPSED -lt $TIMEOUT ]; do",
                        "  if systemctl is-active jenkins > /dev/null && curl -s -f http://localhost:8080/login > /dev/null; then",
                        "    echo 'Jenkins is running and responsive'",
                        "    break",
                        "  fi",
                        "  echo 'Still waiting... (elapsed: ${ELAPSED}s)'",
                        "  sleep 10",
                        "  ELAPSED=$((ELAPSED + 10))",
                        "done",
                        "",
                        "if [ $ELAPSED -ge $TIMEOUT ]; then",
                        "  echo 'ERROR: Jenkins failed to start within timeout'",
                        "  systemctl status jenkins --no-pager",
                        "  exit 1",
                        "fi",
                        "",
                        "echo 'Jenkins restart completed successfully'"
                    ]
                }
            }
        ]
    }),
    tags: {
        Environment: environment,
    },
});

// SSMドキュメント（CLIユーザー作成専用）
const jenkinsCreateCliUserDocument = new aws.ssm.Document(`${projectName}-jenkins-create-cli-user`, {
    name: `${projectName}-jenkins-create-cli-user-${environment}`,
    documentType: "Command",
    content: JSON.stringify({
        schemaVersion: "2.2",
        description: "Create Jenkins CLI user and generate token",
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
            }
        },
        mainSteps: [
            {
                action: "aws:runShellScript",
                name: "createCliUser",
                inputs: {
                    runCommand: [
                        "#!/bin/bash",
                        "set -e",
                        "export PROJECT_NAME={{ProjectName}}",
                        "export ENVIRONMENT={{Environment}}",
                        "",
                        "echo '===== Creating Jenkins CLI User ====='",
                        "",
                        "# Groovyスクリプトを配置",
                        "GROOVY_DIR=/mnt/efs/jenkins/init.groovy.d",
                        "mkdir -p $GROOVY_DIR",
                        "",
                        "# CLIユーザー作成スクリプトのみを取得",
                        "echo 'Fetching CLI user creation script...'",
                        "aws ssm get-parameter \\",
                        "  --name \"/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/groovy/create-cli-user\" \\",
                        "  --with-decryption \\",
                        "  --query \"Parameter.Value\" \\",
                        "  --output text > $GROOVY_DIR/create-cli-user.groovy",
                        "",
                        "# 権限設定",
                        "chown jenkins:jenkins $GROOVY_DIR/create-cli-user.groovy",
                        "chmod 644 $GROOVY_DIR/create-cli-user.groovy",
                        "",
                        "# Jenkinsを再起動してスクリプトを実行",
                        "echo 'Restarting Jenkins to create CLI user...'",
                        "systemctl restart jenkins",
                        "",
                        "# 起動を待機",
                        "echo 'Waiting for Jenkins to start...'",
                        "TIMEOUT=300",
                        "ELAPSED=0",
                        "while [ $ELAPSED -lt $TIMEOUT ]; do",
                        "  if curl -s -f http://localhost:8080/login > /dev/null; then",
                        "    echo 'Jenkins is running'",
                        "    break",
                        "  fi",
                        "  sleep 10",
                        "  ELAPSED=$((ELAPSED + 10))",
                        "done",
                        "",
                        "# 処理完了を待機",
                        "echo 'Waiting for CLI user creation to complete...'",
                        "sleep 30",
                        "",
                        "# スクリプトファイルを削除",
                        "rm -f $GROOVY_DIR/create-cli-user.groovy",
                        "",
                        "# トークンが作成されたか確認",
                        "TOKEN_EXISTS=$(aws ssm get-parameter \\",
                        "  --name \"/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/cli-user-token\" \\",
                        "  --region $(curl -s http://169.254.169.254/latest/meta-data/placement/region) \\",
                        "  2>&1 | grep -q ParameterNotFound && echo \"false\" || echo \"true\")",
                        "",
                        "if [ \"$TOKEN_EXISTS\" = \"true\" ]; then",
                        "  echo 'CLI user token successfully created in SSM'",
                        "else",
                        "  echo 'ERROR: CLI user token was not created'",
                        "  exit 1",
                        "fi",
                        "",
                        "echo 'CLI user creation completed'"
                    ]
                }
            }
        ]
    }),
    tags: {
        Environment: environment,
    },
});

// SSMドキュメント（クレデンシャル設定専用）
const jenkinsSetupCredentialsDocument = new aws.ssm.Document(`${projectName}-jenkins-setup-credentials`, {
    name: `${projectName}-jenkins-setup-credentials-${environment}`,
    documentType: "Command",
    content: JSON.stringify({
        schemaVersion: "2.2",
        description: "Setup Jenkins credentials from CLI user token",
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
            }
        },
        mainSteps: [
            {
                action: "aws:runShellScript",
                name: "setupCredentials",
                inputs: {
                    runCommand: [
                        "#!/bin/bash",
                        "set -e",
                        "export PROJECT_NAME={{ProjectName}}",
                        "export ENVIRONMENT={{Environment}}",
                        "",
                        "echo '===== Setting up Jenkins Credentials ====='",
                        "",
                        "# トークンがSSMに存在するか確認",
                        "echo 'Checking if CLI token exists in SSM...'",
                        "TOKEN_EXISTS=$(aws ssm get-parameter \\",
                        "  --name \"/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/cli-user-token\" \\",
                        "  --region $(curl -s http://169.254.169.254/latest/meta-data/placement/region) \\",
                        "  2>&1 | grep -q ParameterNotFound && echo \"false\" || echo \"true\")",
                        "",
                        "if [ \"$TOKEN_EXISTS\" != \"true\" ]; then",
                        "  echo 'ERROR: CLI token not found in SSM. Please run CLI user setup first.'",
                        "  exit 1",
                        "fi",
                        "",
                        "# Groovyスクリプトを配置",
                        "GROOVY_DIR=/mnt/efs/jenkins/init.groovy.d",
                        "mkdir -p $GROOVY_DIR",
                        "",
                        "# クレデンシャル設定スクリプトのみを取得",
                        "echo 'Fetching credentials setup script...'",
                        "aws ssm get-parameter \\",
                        "  --name \"/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/groovy/setup-credentials\" \\",
                        "  --with-decryption \\",
                        "  --query \"Parameter.Value\" \\",
                        "  --output text > $GROOVY_DIR/setup-credentials.groovy",
                        "",
                        "# 権限設定",
                        "chown jenkins:jenkins $GROOVY_DIR/setup-credentials.groovy",
                        "chmod 644 $GROOVY_DIR/setup-credentials.groovy",
                        "",
                        "# Jenkinsを再起動してスクリプトを実行",
                        "echo 'Restarting Jenkins to setup credentials...'",
                        "systemctl restart jenkins",
                        "",
                        "# 起動を待機",
                        "echo 'Waiting for Jenkins to start...'",
                        "TIMEOUT=300",
                        "ELAPSED=0",
                        "while [ $ELAPSED -lt $TIMEOUT ]; do",
                        "  if curl -s -f http://localhost:8080/login > /dev/null; then",
                        "    echo 'Jenkins is running'",
                        "    break",
                        "  fi",
                        "  sleep 10",
                        "  ELAPSED=$((ELAPSED + 10))",
                        "done",
                        "",
                        "# 処理完了を待機",
                        "echo 'Waiting for credentials setup to complete...'",
                        "sleep 30",
                        "",
                        "# スクリプトファイルを削除",
                        "rm -f $GROOVY_DIR/setup-credentials.groovy",
                        "",
                        "echo 'Credentials setup completed'"
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
    updateVersion: jenkinsUpdateVersionDocument.name,
    installPlugins: jenkinsInstallPluginsDocument.name,
    restartJenkins: jenkinsRestartDocument.name,
    createCliUser: jenkinsCreateCliUserDocument.name,
    setupCredentials: jenkinsSetupCredentialsDocument.name,
};
