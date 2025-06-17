/**
 * pulumi/jenkins-application/index.ts
 * 
 * Jenkinsアプリケーション設定用の汎用的なSSMドキュメント
 * Gitリポジトリ内のスクリプトを実行するシンプルな基盤
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "jenkins-infra";
const environment = pulumi.getStack();

// 汎用的なスクリプト実行用SSMドキュメント
const jenkinsExecuteScriptDocument = new aws.ssm.Document(`${projectName}-jenkins-execute-script`, {
    name: `${projectName}-jenkins-execute-script-${environment}`,
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
                        "export PROJECT_NAME='${PROJECT_NAME:-" + projectName + "}'",
                        "export ENVIRONMENT='${ENVIRONMENT:-" + environment + "}'",
                        "export JENKINS_HOME='/mnt/efs/jenkins'",
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
});

// Jenkins再起動用SSMドキュメント（これは残す）
const jenkinsRestartDocument = new aws.ssm.Document(`${projectName}-jenkins-restart`, {
    name: `${projectName}-jenkins-restart-${environment}`,
    documentType: "Command",
    documentFormat: "JSON",
    content: JSON.stringify({
        schemaVersion: "2.2",
        description: "Restart Jenkins service",
        parameters: {},
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
                        "systemctl restart jenkins",
                        "",
                        "# 起動を待機",
                        "TIMEOUT=300",
                        "ELAPSED=0",
                        "while [ $ELAPSED -lt $TIMEOUT ]; do",
                        "  if systemctl is-active jenkins > /dev/null && curl -s -f http://localhost:8080/login > /dev/null; then",
                        "    echo 'Jenkins is running and responsive'",
                        "    break",
                        "  fi",
                        "  sleep 10",
                        "  ELAPSED=$((ELAPSED + 10))",
                        "done",
                        "",
                        "if [ $ELAPSED -ge $TIMEOUT ]; then",
                        "  echo 'ERROR: Jenkins failed to start within timeout'",
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

// エクスポート
export const ssmDocuments = {
    executeScript: jenkinsExecuteScriptDocument.name,
    restart: jenkinsRestartDocument.name,
};
