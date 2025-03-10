import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

export function createLoadBalancer(
    projectName: string, 
    environment: string, 
    vpcId: pulumi.Input<string>,
    publicSubnets: pulumi.Input<string>[],
    securityGroupId: pulumi.Input<string>
) {
    // Application Load Balancer
    const alb = new aws.lb.LoadBalancer(`${projectName}-jenkins-alb`, {
        internal: false,
        loadBalancerType: "application",
        securityGroups: [securityGroupId],
        subnets: publicSubnets,
        enableDeletionProtection: environment === "prod",
        tags: {
            Name: `${projectName}-jenkins-alb-${environment}`,
            Environment: environment,
            ManagedBy: "pulumi",
        },
    });

    // Blue環境のターゲットグループ
    const blueTargetGroup = new aws.lb.TargetGroup(`${projectName}-jenkins-blue-tg`, {
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
    const greenTargetGroup = new aws.lb.TargetGroup(`${projectName}-jenkins-green-tg`, {
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
            matcher: "200-399",
        },
        tags: {
            Name: `${projectName}-jenkins-green-tg-${environment}`,
            Environment: environment,
            Color: "green",
        },
    });

    // HTTPリスナー（HTTPSにリダイレクト）
    const httpListener = new aws.lb.Listener(`${projectName}-jenkins-http-listener`, {
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

    // HTTPSリスナー
    let httpsListener;
    
    // 実際の環境ではいずれACM証明書を使用する想定
    const config = new pulumi.Config();
    const certificateArn = config.get("certificateArn");
    
    if (certificateArn) {
        // ACM証明書が設定されている場合はHTTPSリスナーを作成
        httpsListener = new aws.lb.Listener(`${projectName}-jenkins-https-listener`, {
            loadBalancerArn: alb.arn,
            port: 443,
            protocol: "HTTPS",
            sslPolicy: "ELBSecurityPolicy-2016-08",
            certificateArn: certificateArn,
            defaultActions: [{
                type: "forward",
                targetGroupArn: blueTargetGroup.arn, // デフォルトでBlue環境にトラフィックを送信
            }],
        });
    } else {
        // 証明書が設定されていない場合は一時的にHTTPリスナーでBlue環境に転送
        // 注: 本番環境ではHTTPSを推奨
        console.log("Warning: No SSL certificate provided. Creating HTTP listener for testing only.");
        httpsListener = new aws.lb.Listener(`${projectName}-jenkins-http-forward-listener`, {
            loadBalancerArn: alb.arn,
            port: 8080,
            protocol: "HTTP",
            defaultActions: [{
                type: "forward",
                targetGroupArn: blueTargetGroup.arn,
            }],
        });
    }

    // ブルーグリーン切り替え用のパラメータストア
    const activeEnvironmentParam = new aws.ssm.Parameter(`${projectName}-active-environment`, {
        name: `/${projectName}/${environment}/jenkins/active-environment`,
        type: "String",
        value: "blue", // 初期値はblue
        description: "Currently active Jenkins environment (blue/green)",
        tags: {
            Environment: environment,
            ManagedBy: "pulumi",
        },
    });

    return {
        alb,
        blueTargetGroup,
        greenTargetGroup,
        httpListener,
        httpsListener,
        activeEnvironmentParam,
        albDnsName: alb.dnsName,
    };
}