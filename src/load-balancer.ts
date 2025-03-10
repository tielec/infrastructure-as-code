import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import { dependsOn } from "./dependency-utils";

export function createLoadBalancer(
    projectName: string, 
    environment: string, 
    vpcId: pulumi.Input<string>,
    publicSubnets: pulumi.Input<string>[],
    securityGroupId: pulumi.Input<string>,
    dependencies?: pulumi.Resource[]
) {
    // より短い名前の生成（最大25文字で、7文字のランダム部分を追加して32文字以内に収める）
    const shortProjectName = projectName.length > 10 ? projectName.substring(0, 10) : projectName;
    const shortEnvName = environment.length > 3 ? environment.substring(0, 3) : environment;
    
    // Application Load Balancer
    let alb = new aws.lb.LoadBalancer(
        `${shortProjectName}-alb`, 
        {
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
        }
    );

    // 依存関係がある場合は設定
    if (dependencies && dependencies.length > 0) {
        alb = dependsOn(alb, dependencies);
    }

    // Blue環境のターゲットグループ - 名前を短くする
    let blueTargetGroup = new aws.lb.TargetGroup(`${shortProjectName}-blue-tg`, {
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

    // 依存関係を設定
    if (dependencies && dependencies.length > 0) {
        blueTargetGroup = dependsOn(blueTargetGroup, dependencies);
    }

    // Green環境のターゲットグループ - 名前を短くする
    let greenTargetGroup = new aws.lb.TargetGroup(`${shortProjectName}-green-tg`, {
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

    // 依存関係を設定
    if (dependencies && dependencies.length > 0) {
        greenTargetGroup = dependsOn(greenTargetGroup, dependencies);
    }

    // HTTPリスナー（HTTPSにリダイレクト）
    let httpListener = new aws.lb.Listener(`${shortProjectName}-http`, {
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

    // 依存関係を設定
    httpListener = dependsOn(httpListener, [alb]);

    // HTTPSリスナー
    let httpsListener;
    
    // 実際の環境ではいずれACM証明書を使用する想定
    const config = new pulumi.Config();
    const certificateArn = config.get("certificateArn");
    
    if (certificateArn) {
        // ACM証明書が設定されている場合はHTTPSリスナーを作成
        httpsListener = new aws.lb.Listener(`${shortProjectName}-https`, {
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

        // 依存関係を設定
        httpsListener = dependsOn(httpsListener, [alb, blueTargetGroup]);
    } else {
        // 証明書が設定されていない場合は一時的にHTTPリスナーでBlue環境に転送
        // 注: 本番環境ではHTTPSを推奨
        console.log("Warning: No SSL certificate provided. Creating HTTP listener for testing only.");
        httpsListener = new aws.lb.Listener(`${shortProjectName}-http-fwd`, {
            loadBalancerArn: alb.arn,
            port: 8080,
            protocol: "HTTP",
            defaultActions: [{
                type: "forward",
                targetGroupArn: blueTargetGroup.arn,
            }],
        });

        // 依存関係を設定
        httpsListener = dependsOn(httpsListener, [alb, blueTargetGroup]);
    }

    // ブルーグリーン切り替え用のパラメータストア
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
