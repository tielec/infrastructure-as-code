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

// 証明書ARNは別途チェック（オプション）
const certificateArnParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/certificate-arn`,
}).then(p => p.value).catch(() => undefined);

// ネットワークリソースIDを取得
const vpcId = pulumi.output(vpcIdParam).apply(p => p.value);
const publicSubnetAId = pulumi.output(publicSubnetAIdParam).apply(p => p.value);
const publicSubnetBId = pulumi.output(publicSubnetBIdParam).apply(p => p.value);
const publicSubnetIds = [publicSubnetAId, publicSubnetBId];
const albSecurityGroupId = pulumi.output(albSecurityGroupIdParam).apply(p => p.value);

// より短い名前の生成（ALBの名前制限に対応）
const shortEnvName = environment.length > 3 ? environment.substring(0, 3) : environment;

// Application Load Balancerの作成（IPv6対応）
const alb = new aws.lb.LoadBalancer(`alb`, {
    internal: false,
    loadBalancerType: "application",
    securityGroups: [albSecurityGroupId],
    subnets: publicSubnetIds,
    enableDeletionProtection: environment === "prod",
    ipAddressType: "dualstack",  // IPv4/IPv6デュアルスタック対応
    idleTimeout: 3600,  // WebSocket接続用に1時間に延長
    tags: {
        Name: pulumi.interpolate`${projectName}-jenkins-alb-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
        IPv6Enabled: "true",
    },
});

// Blue環境のターゲットグループ（IPv6対応）
const blueTargetGroup = new aws.lb.TargetGroup(`blue-tg`, {
    port: 8080,
    protocol: "HTTP",
    vpcId: vpcId,
    targetType: "instance",
    // ipAddressType は targetType: "ip" の場合のみ有効なため削除
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
        IPv6Enabled: "true",
    },
});

// Green環境のターゲットグループ（IPv6対応）
const greenTargetGroup = new aws.lb.TargetGroup(`green-tg`, {
    port: 8080,
    protocol: "HTTP",
    vpcId: vpcId,
    targetType: "instance",
    // ipAddressType は targetType: "ip" の場合のみ有効なため削除
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
        IPv6Enabled: "true",
    },
});

// SSL証明書の設定は上部で取得済み

// HTTPリスナーの設定
// 証明書ARNは同期的に取得できないため、常にBlue環境に転送
const httpListener = new aws.lb.Listener(`http`, {
    loadBalancerArn: alb.arn,
    port: 80,
    protocol: "HTTP",
    defaultActions: [{
        type: "forward",
        targetGroupArn: blueTargetGroup.arn,
    }],
});

// HTTPSリスナーの設定（将来の実装用にコメントアウト）
// 証明書ARNの取得はPromiseなので、条件付き作成が難しい
// TODO: 証明書ARNが設定されている場合のHTTPS対応

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

// ========================================
// Route 53プライベートホストゾーン（VPC内部アクセス用）
// ========================================
// ECS FargateエージェントがNAT Instance経由せずにALBに直接接続するため
// Issue #497: WebSocket接続が約6分で切断される問題の解決策

// Route 53プライベートホストゾーンの作成
const privateZone = new aws.route53.Zone(`jenkins-private-zone`, {
    name: `jenkins.internal`,
    vpcs: [{
        vpcId: vpcId,
    }],
    comment: `Private hosted zone for Jenkins internal access - ${environment}`,
    tags: {
        Name: pulumi.interpolate`${projectName}-jenkins-private-zone-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "loadbalancer",
    },
});

// ALBへのALIASレコード（VPC内部ではALBのプライベートIPに解決される）
const albPrivateRecord = new aws.route53.Record(`alb-private-record`, {
    zoneId: privateZone.zoneId,
    name: `jenkins.internal`,
    type: "A",
    aliases: [{
        name: alb.dnsName,
        zoneId: alb.zoneId,
        evaluateTargetHealth: true,
    }],
});

// VPC内部アクセス用のプライベートURL（新規追加）
const jenkinsInternalUrlParam = new aws.ssm.Parameter(`jenkins-internal-url`, {
    name: `${ssmPrefix}/loadbalancer/jenkins-internal-url`,
    type: "String",
    value: `http://jenkins.internal/`,
    overwrite: true,  // 初期設定スタックのため許可
    description: "Jenkins URL for internal VPC access (ECS Fargate)",
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

// HTTPSリスナーのARNは現在未実装

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
export const httpsListenerArn = undefined; // 現在未実装
export const httpDirectListenerArn = httpDirectListener.arn;
export const activeEnvironment = activeEnvironmentParam.value;
export const jenkinsUrl = jenkinsUrlParam.value;

// Route 53プライベートホストゾーン関連のエクスポート（VPC内部アクセス用）
export const privateZoneId = privateZone.zoneId;
export const privateZoneName = privateZone.name;
export const jenkinsInternalUrl = jenkinsInternalUrlParam.value;
