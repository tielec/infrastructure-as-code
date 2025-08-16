/**
 * pulumi/loadbalancer/index.ts
 * 
 * Jenkinsインフラのロードバランサーリソースを構築するPulumiスクリプト
 * ALBとBlue/Green環境用ターゲットグループを作成
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
const certificateArnParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/certificate-arn`,
}, { async: true });

// ネットワークリソースのSSMパラメータを取得
const vpcIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/vpc-id`,
});
const publicSubnetAIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/public-subnet-a-id`,
});
const publicSubnetBIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/public-subnet-b-id`,
});

// セキュリティグループのSSMパラメータを取得
const albSecurityGroupIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/security/alb-sg-id`,
});

// 設定値を変数に設定
const projectName = pulumi.output(projectNameParam).apply(p => p.value);
const certificateArn = certificateArnParam.then(p => p.value).catch(() => undefined);

// ネットワークリソースIDを取得
const vpcId = pulumi.output(vpcIdParam).apply(p => p.value);
const publicSubnetAId = pulumi.output(publicSubnetAIdParam).apply(p => p.value);
const publicSubnetBId = pulumi.output(publicSubnetBIdParam).apply(p => p.value);
const publicSubnetIds = [publicSubnetAId, publicSubnetBId];
const albSecurityGroupId = pulumi.output(albSecurityGroupIdParam).apply(p => p.value);

// より短い名前の生成（ALBの名前制限に対応）
const shortEnvName = environment.length > 3 ? environment.substring(0, 3) : environment;

// Application Load Balancerの作成
const alb = new aws.lb.LoadBalancer(`alb`, {
    internal: false,
    loadBalancerType: "application",
    securityGroups: [albSecurityGroupId],
    subnets: publicSubnetIds,
    enableDeletionProtection: environment === "prod",
    tags: {
        Name: pulumi.interpolate`${projectName}-jenkins-alb-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// Blue環境のターゲットグループ
const blueTargetGroup = new aws.lb.TargetGroup(`blue-tg`, {
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
        Name: pulumi.interpolate`${projectName}-jenkins-blue-tg-${environment}`,
        Environment: environment,
        Color: "blue",
    },
});

// Green環境のターゲットグループ
const greenTargetGroup = new aws.lb.TargetGroup(`green-tg`, {
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
        Name: pulumi.interpolate`${projectName}-jenkins-green-tg-${environment}`,
        Environment: environment,
        Color: "green",
    },
});

// SSL証明書の設定は上部で取得済み

// HTTPリスナーの設定
let httpListener;
if (certificateArn) {
    // SSL証明書が設定されている場合はHTTPSにリダイレクト
    httpListener = new aws.lb.Listener(`http`, {
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
    httpListener = new aws.lb.Listener(`http`, {
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
    httpsListener = new aws.lb.Listener(`https`, {
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
const httpDirectListener = new aws.lb.Listener(`http-8080`, {
    loadBalancerArn: alb.arn,
    port: 8080,
    protocol: "HTTP",
    defaultActions: [{
        type: "forward",
        targetGroupArn: blueTargetGroup.arn,
    }],
});

// Blue/Green切り替え用のパラメータストア
const activeEnvironmentParam = new aws.ssm.Parameter(`active-env`, {
    name: `${ssmPrefix}/loadbalancer/active-environment`,
    type: "String",
    value: "blue", // 初期値はblue
    overwrite: true,
    description: "Currently active Jenkins environment (blue/green)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "loadbalancer",
    },
});

// Jenkins URLをSSMパラメータストアに保存
const jenkinsUrlParam = new aws.ssm.Parameter(`jenkins-url`, {
    name: `${ssmPrefix}/loadbalancer/jenkins-url`,
    type: "String",
    value: pulumi.interpolate`http://${alb.dnsName}/`,
    overwrite: true,
    description: "Jenkins URL for external access via ALB",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "loadbalancer",
    },
});

// ALBのARNをSSMパラメータに保存
const albArnParam = new aws.ssm.Parameter(`alb-arn`, {
    name: `${ssmPrefix}/loadbalancer/alb-arn`,
    type: "String",
    value: alb.arn,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "loadbalancer",
    },
});

// ALBのDNS名をSSMパラメータに保存
const albDnsNameParam = new aws.ssm.Parameter(`alb-dns-name`, {
    name: `${ssmPrefix}/loadbalancer/alb-dns-name`,
    type: "String",
    value: alb.dnsName,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "loadbalancer",
    },
});

// ALBのZone IDをSSMパラメータに保存
const albZoneIdParam = new aws.ssm.Parameter(`alb-zone-id`, {
    name: `${ssmPrefix}/loadbalancer/alb-zone-id`,
    type: "String",
    value: alb.zoneId,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "loadbalancer",
    },
});

// Blue Target GroupのARNをSSMパラメータに保存
const blueTargetGroupArnParam = new aws.ssm.Parameter(`blue-tg-arn`, {
    name: `${ssmPrefix}/loadbalancer/blue-target-group-arn`,
    type: "String",
    value: blueTargetGroup.arn,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "loadbalancer",
    },
});

// Green Target GroupのARNをSSMパラメータに保存
const greenTargetGroupArnParam = new aws.ssm.Parameter(`green-tg-arn`, {
    name: `${ssmPrefix}/loadbalancer/green-target-group-arn`,
    type: "String",
    value: greenTargetGroup.arn,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "loadbalancer",
    },
});

// HTTPリスナーのARNをSSMパラメータに保存
const httpListenerArnParam = new aws.ssm.Parameter(`http-listener-arn`, {
    name: `${ssmPrefix}/loadbalancer/http-listener-arn`,
    type: "String",
    value: httpListener.arn,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "loadbalancer",
    },
});

// HTTPSリスナーのARNをSSMパラメータに保存（存在する場合）
if (httpsListener) {
    const httpsListenerArnParam = new aws.ssm.Parameter(`https-listener-arn`, {
        name: `${ssmPrefix}/loadbalancer/https-listener-arn`,
        type: "String",
        value: httpsListener.arn,
        overwrite: true,
        tags: {
            Environment: environment,
            ManagedBy: "pulumi",
            Component: "loadbalancer",
        },
    });
}

// HTTP Direct ListenerのARNをSSMパラメータに保存
const httpDirectListenerArnParam = new aws.ssm.Parameter(`http-direct-listener-arn`, {
    name: `${ssmPrefix}/loadbalancer/http-direct-listener-arn`,
    type: "String",
    value: httpDirectListener.arn,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "loadbalancer",
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
export const jenkinsUrl = jenkinsUrlParam.value;
