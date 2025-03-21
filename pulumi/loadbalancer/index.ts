/**
 * pulumi/loadbalancer/index.ts
 * 
 * Jenkinsインフラのロードバランサーリソースを構築するPulumiスクリプト
 * ALBとBlue/Green環境用ターゲットグループを作成
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "jenkins-infra";
const environment = pulumi.getStack();

// ネットワークスタック名とセキュリティスタック名を設定から取得
const networkStackName = config.get("networkStackName") || "jenkins-network";
const securityStackName = config.get("securityStackName") || "jenkins-security";

// 既存のネットワークスタックとセキュリティスタックから値を取得
const networkStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${networkStackName}/${environment}`);
const securityStack = new pulumi.StackReference(`${pulumi.getOrganization()}/${securityStackName}/${environment}`);

// VPC ID、パブリックサブネットID、ALB用セキュリティグループIDを取得
const vpcId = networkStack.getOutput("vpcId");
const publicSubnetIds = networkStack.getOutput("publicSubnetIds");
const albSecurityGroupId = securityStack.getOutput("albSecurityGroupId");

// より短い名前の生成（ALBの名前制限に対応）
const shortProjectName = projectName.length > 10 ? projectName.substring(0, 10) : projectName;
const shortEnvName = environment.length > 3 ? environment.substring(0, 3) : environment;

// Application Load Balancerの作成
const alb = new aws.lb.LoadBalancer(`${shortProjectName}-alb`, {
    internal: false,
    loadBalancerType: "application",
    securityGroups: [albSecurityGroupId],
    subnets: publicSubnetIds,
    enableDeletionProtection: environment === "prod",
    tags: {
        Name: `${projectName}-jenkins-alb-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// Blue環境のターゲットグループ
const blueTargetGroup = new aws.lb.TargetGroup(`${shortProjectName}-blue-tg`, {
    port: 8080,
    protocol: "HTTP",
    vpcId: vpcId,
    targetType: "instance",
    healthCheck: {
        enabled: true,
        path: "/login",
        port: "8080",
        protocol: "HTTP",
        healthyThreshold: 3,
        unhealthyThreshold: 3,
        timeout: 5,
        interval: 30,
        matcher: "200-399",  // Jenkinsの場合、リダイレクトも正常と見なす
    },
    tags: {
        Name: `${projectName}-jenkins-blue-tg-${environment}`,
        Environment: environment,
        Color: "blue",
    },
});

// Green環境のターゲットグループ
const greenTargetGroup = new aws.lb.TargetGroup(`${shortProjectName}-green-tg`, {
    port: 8080,
    protocol: "HTTP",
    vpcId: vpcId,
    targetType: "instance",
    healthCheck: {
        enabled: true,
        path: "/login",
        port: "8080",
        protocol: "HTTP",
        healthyThreshold: 3,
        unhealthyThreshold: 3,
        timeout: 5,
        interval: 30,
        matcher: "200-399",  // Jenkinsの場合、リダイレクトも正常と見なす
    },
    tags: {
        Name: `${projectName}-jenkins-green-tg-${environment}`,
        Environment: environment,
        Color: "green",
    },
});

// SSL証明書の設定（オプション、証明書ARNが設定されている場合）
const certificateArn = config.get("certificateArn");

// HTTPリスナーの設定
let httpListener;
if (certificateArn) {
    // SSL証明書が設定されている場合はHTTPSにリダイレクト
    httpListener = new aws.lb.Listener(`${shortProjectName}-http`, {
        loadBalancerArn: alb.arn,
        port: 80,
        protocol: "HTTP",
        defaultActions: [{
            type: "redirect",
            redirect: {
                port: "443",
                protocol: "HTTPS",
                statusCode: "HTTP_301",
            },
        }],
    });
} else {
    // 証明書が設定されていない場合はBlue環境に直接転送
    httpListener = new aws.lb.Listener(`${shortProjectName}-http`, {
        loadBalancerArn: alb.arn,
        port: 80,
        protocol: "HTTP",
        defaultActions: [{
            type: "forward",
            targetGroupArn: blueTargetGroup.arn,
        }],
    });
}

// HTTPSリスナーの設定（SSL証明書が設定されている場合のみ）
let httpsListener;
if (certificateArn) {
    httpsListener = new aws.lb.Listener(`${shortProjectName}-https`, {
        loadBalancerArn: alb.arn,
        port: 443,
        protocol: "HTTPS",
        sslPolicy: "ELBSecurityPolicy-2016-08",
        certificateArn: certificateArn,
        defaultActions: [{
            type: "forward",
            targetGroupArn: blueTargetGroup.arn,
        }],
    });
}

// Jenkins専用ポート（8080）のバックアップリスナー
const httpDirectListener = new aws.lb.Listener(`${shortProjectName}-http-8080`, {
    loadBalancerArn: alb.arn,
    port: 8080,
    protocol: "HTTP",
    defaultActions: [{
        type: "forward",
        targetGroupArn: blueTargetGroup.arn,
    }],
});

// Blue/Green切り替え用のパラメータストア
const activeEnvironmentParam = new aws.ssm.Parameter(`${shortProjectName}-active-env`, {
    name: `/${projectName}/${environment}/jenkins/active-environment`,
    type: "String",
    value: "blue", // 初期値はblue
    description: "Currently active Jenkins environment (blue/green)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// エクスポート
export const albArn = alb.arn;
export const albDnsName = alb.dnsName;
export const albZoneId = alb.zoneId;
export const blueTargetGroupArn = blueTargetGroup.arn;
export const greenTargetGroupArn = greenTargetGroup.arn;
export const httpListenerArn = httpListener.arn;
export const httpsListenerArn = httpsListener ? httpsListener.arn : undefined;
export const httpDirectListenerArn = httpDirectListener.arn;
export const activeEnvironment = activeEnvironmentParam.value;
