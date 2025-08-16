/**
 * pulumi/jenkins-application/index.ts
 * 
 * Jenkinsアプリケーション設定用の汎用的なSSMドキュメント
 * Gitリポジトリ内のスクリプトを実行するシンプルな基盤
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

// 設定値を変数に設定
const projectName = pulumi.output(projectNameParam).apply(p => p.value);

// タイムスタンプを生成（ドキュメント名の一意性を保証）
const timestamp = new Date().toISOString().slice(0, 10).replace(/-/g, '');

// 汎用的なスクリプト実行用SSMドキュメント
const jenkinsExecuteScriptDocument = new aws.ssm.Document(`jenkins-execute-script`, {
    name: `jenkins-infra-jenkins-execute-script-${environment}`,
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

// Jenkins再起動用SSMドキュメント（これは残す）
const jenkinsRestartDocument = new aws.ssm.Document(`jenkins-restart`, {
    name: `jenkins-infra-jenkins-restart-${environment}`,
    documentType: "Command",
    documentFormat: "JSON",
    targetType: "/AWS::EC2::Instance",
    versionName: `v${timestamp}`,
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
                        "",
                        "# Jenkins CLIまたはREST APIを使用した安全な再起動を試みる",
                        "JENKINS_URL='http://localhost:8080'",
                        "JENKINS_HOME='/mnt/efs/jenkins'",
                        "",
                        "# まずJenkinsが応答するか確認",
                        "if curl -sf $JENKINS_URL/login > /dev/null 2>&1; then",
                        "    echo 'Jenkins is responsive, attempting safe restart...'",
                        "    ",
                        "    # REST APIを使用した再起動を試みる",
                        "    if [ -f \"${JENKINS_HOME}/secrets/initialAdminPassword\" ]; then",
                        "        ADMIN_TOKEN=$(cat ${JENKINS_HOME}/secrets/initialAdminPassword)",
                        "        curl -X POST -u admin:$ADMIN_TOKEN $JENKINS_URL/safeRestart || true",
                        "    else",
                        "        # APIが使えない場合は、quietDownして再起動",
                        "        curl -X POST $JENKINS_URL/quietDown || true",
                        "        sleep 10",
                        "    fi",
                        "fi",
                        "",
                        "# systemctl経由で停止と起動を分けて実行",
                        "echo 'Stopping Jenkins service...'",
                        "systemctl stop jenkins",
                        "",
                        "# プラグインディレクトリのキャッシュをクリア（プラグインの確実な再読み込みのため）",
                        "if [ -d \"${JENKINS_HOME}/plugins\" ]; then",
                        "    echo 'Clearing plugin cache...'",
                        "    find ${JENKINS_HOME}/plugins -name '*.jpi.pinned' -delete 2>/dev/null || true",
                        "    find ${JENKINS_HOME}/plugins -name '*.jpi.disabled' -delete 2>/dev/null || true",
                        "fi",
                        "",
                        "# 少し待機してから起動",
                        "sleep 5",
                        "",
                        "echo 'Starting Jenkins service...'",
                        "systemctl start jenkins",
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
                        "# プラグインの読み込み完了を待つ",
                        "echo 'Waiting for plugins to be fully loaded...'",
                        "sleep 30",
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
}, {
    replaceOnChanges: ["content", "targetType"]
});

// SSMドキュメント名をSSMパラメータに保存
const executeScriptDocumentNameParam = new aws.ssm.Parameter(`execute-script-document-name`, {
    name: `${ssmPrefix}/application/execute-script-document-name`,
    type: "String",
    value: jenkinsExecuteScriptDocument.name,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "application",
    },
});

const restartDocumentNameParam = new aws.ssm.Parameter(`restart-document-name`, {
    name: `${ssmPrefix}/application/restart-document-name`,
    type: "String",
    value: jenkinsRestartDocument.name,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "application",
    },
});

// アプリケーションステータス用SSMパラメータ
const applicationStatusParam = new aws.ssm.Parameter(`application-status`, {
    name: `${ssmPrefix}/application/status`,
    type: "String",
    value: "initialized",
    overwrite: true,
    description: "Jenkins application deployment status",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "application",
    },
});

// エクスポート
export const ssmDocuments = {
    executeScript: jenkinsExecuteScriptDocument.name,
    restart: jenkinsRestartDocument.name,
};
export const applicationStatusParameterName = applicationStatusParam.name;
