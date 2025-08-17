/**
 * pulumi/jenkins-application/index.ts
 * 
 * Jenkinsアプリケーション設定用のステータスパラメータを管理
 * SSMドキュメントはjenkins-configで作成されたものを使用
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

// SSMドキュメントはjenkins-configで作成されたものを使用するため、
// ここでは作成しない

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
export const applicationStatusParameterName = applicationStatusParam.name;
