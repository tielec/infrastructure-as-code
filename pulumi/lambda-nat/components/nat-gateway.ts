/**
 * components/nat-gateway.ts
 * 
 * NAT Gateway（高可用性モード）用のコンポーネント
 * 2つのAZにNAT Gatewayを配置してHA構成を実現
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

/**
 * NAT Gateway構成の入力パラメータ
 */
export interface NatGatewayArgs {
    /** プロジェクト名 */
    projectName: pulumi.Output<string>;
    /** 環境名 */
    environment: string;
    /** パブリックサブネットA ID */
    publicSubnetAId: pulumi.Output<string>;
    /** パブリックサブネットB ID */
    publicSubnetBId: pulumi.Output<string>;
    /** プライベートルートテーブルA ID */
    privateRouteTableAId: pulumi.Output<string>;
    /** プライベートルートテーブルB ID */
    privateRouteTableBId: pulumi.Output<string>;
    /** 共通タグ */
    commonTags: Record<string, string>;
}

/**
 * NAT Gateway構成の出力
 */
export interface NatGatewayOutputs {
    /** NAT Gateway A ID */
    natGatewayAId: pulumi.Output<string>;
    /** NAT Gateway B ID */
    natGatewayBId: pulumi.Output<string>;
    /** NAT Gateway A Elastic IP */
    natGatewayEipAAddress: pulumi.Output<string>;
    /** NAT Gateway B Elastic IP */
    natGatewayEipBAddress: pulumi.Output<string>;
    /** NAT リソースID配列 */
    natResourceIds: pulumi.Output<string>[];
}

/**
 * NAT Gateway（高可用性モード）を作成
 * 
 * @param args NAT Gateway構成パラメータ
 * @returns NAT Gatewayリソース情報
 */
export function createNatGateway(args: NatGatewayArgs): NatGatewayOutputs {
    const {
        projectName,
        environment,
        publicSubnetAId,
        publicSubnetBId,
        privateRouteTableAId,
        privateRouteTableBId,
        commonTags
    } = args;

    // ========================================
    // NAT Gateway A（AZ-a）
    // ========================================
    // Elastic IP for NAT Gateway A
    const natGatewayEipA = new aws.ec2.Eip("nat-eip-a", {
        tags: {
            ...commonTags,
            Name: pulumi.interpolate`${projectName}-nat-eip-a-${environment}`,
            Type: "nat-gateway",
            AZ: "a",
        },
    });

    // NAT Gateway A
    const natGatewayA = new aws.ec2.NatGateway("nat-a", {
        allocationId: natGatewayEipA.id,
        subnetId: publicSubnetAId,
        tags: {
            ...commonTags,
            Name: pulumi.interpolate`${projectName}-nat-a-${environment}`,
            Type: "nat-gateway",
            AZ: "a",
        },
    });

    // プライベートサブネットAからのルート
    new aws.ec2.Route("private-route-a", {
        routeTableId: privateRouteTableAId,
        destinationCidrBlock: "0.0.0.0/0",
        natGatewayId: natGatewayA.id,
    }, {
        dependsOn: [natGatewayA],
    });

    // ========================================
    // NAT Gateway B（AZ-b）
    // ========================================
    // Elastic IP for NAT Gateway B
    const natGatewayEipB = new aws.ec2.Eip("nat-eip-b", {
        tags: {
            ...commonTags,
            Name: pulumi.interpolate`${projectName}-nat-eip-b-${environment}`,
            Type: "nat-gateway",
            AZ: "b",
        },
    });

    // NAT Gateway B
    const natGatewayB = new aws.ec2.NatGateway("nat-b", {
        allocationId: natGatewayEipB.id,
        subnetId: publicSubnetBId,
        tags: {
            ...commonTags,
            Name: pulumi.interpolate`${projectName}-nat-b-${environment}`,
            Type: "nat-gateway",
            AZ: "b",
        },
    });

    // プライベートサブネットBからのルート
    new aws.ec2.Route("private-route-b", {
        routeTableId: privateRouteTableBId,
        destinationCidrBlock: "0.0.0.0/0",
        natGatewayId: natGatewayB.id,
    }, {
        dependsOn: [natGatewayB],
    });

    // ========================================
    // CloudWatchアラーム（モニタリング）
    // ========================================
    // NAT Gateway Aのパケットドロップアラーム
    new aws.cloudwatch.MetricAlarm("nat-gateway-a-packet-drop", {
        alarmDescription: "Alert when NAT Gateway A drops packets",
        metricName: "PacketDropCount",
        namespace: "AWS/NATGateway",
        statistic: "Sum",
        period: 300,
        evaluationPeriods: 2,
        threshold: 100,
        comparisonOperator: "GreaterThanThreshold",
        dimensions: {
            NatGatewayId: natGatewayA.id,
        },
        treatMissingData: "notBreaching",
        tags: commonTags,
    });

    // NAT Gateway Bのパケットドロップアラーム
    new aws.cloudwatch.MetricAlarm("nat-gateway-b-packet-drop", {
        alarmDescription: "Alert when NAT Gateway B drops packets",
        metricName: "PacketDropCount",
        namespace: "AWS/NATGateway",
        statistic: "Sum",
        period: 300,
        evaluationPeriods: 2,
        threshold: 100,
        comparisonOperator: "GreaterThanThreshold",
        dimensions: {
            NatGatewayId: natGatewayB.id,
        },
        treatMissingData: "notBreaching",
        tags: commonTags,
    });

    // 接続数アラーム（高負荷検知）
    new aws.cloudwatch.MetricAlarm("nat-gateway-a-connections", {
        alarmDescription: "Alert when NAT Gateway A has high connection count",
        metricName: "ActiveConnectionCount",
        namespace: "AWS/NATGateway",
        statistic: "Max",
        period: 300,
        evaluationPeriods: 2,
        threshold: 50000, // NAT Gatewayの制限に近い値
        comparisonOperator: "GreaterThanThreshold",
        dimensions: {
            NatGatewayId: natGatewayA.id,
        },
        treatMissingData: "notBreaching",
        tags: commonTags,
    });

    new aws.cloudwatch.MetricAlarm("nat-gateway-b-connections", {
        alarmDescription: "Alert when NAT Gateway B has high connection count",
        metricName: "ActiveConnectionCount",
        namespace: "AWS/NATGateway",
        statistic: "Max",
        period: 300,
        evaluationPeriods: 2,
        threshold: 50000,
        comparisonOperator: "GreaterThanThreshold",
        dimensions: {
            NatGatewayId: natGatewayB.id,
        },
        treatMissingData: "notBreaching",
        tags: commonTags,
    });

    // ========================================
    // SSMパラメータへの保存
    // ========================================
    const paramPrefix = pulumi.interpolate`/${projectName}/${environment}/nat`;

    // NAT Gateway A IDを保存
    new aws.ssm.Parameter("nat-gateway-a-id", {
        name: pulumi.interpolate`${paramPrefix}/gateway/a-id`,
        type: "String",
        value: natGatewayA.id,
        description: "NAT Gateway A ID",
        tags: commonTags,
    });

    // NAT Gateway B IDを保存
    new aws.ssm.Parameter("nat-gateway-b-id", {
        name: pulumi.interpolate`${paramPrefix}/gateway/b-id`,
        type: "String",
        value: natGatewayB.id,
        description: "NAT Gateway B ID",
        tags: commonTags,
    });

    // NAT Gateway A Elastic IPを保存
    new aws.ssm.Parameter("nat-gateway-eip-a", {
        name: pulumi.interpolate`${paramPrefix}/gateway/eip-a`,
        type: "String",
        value: natGatewayEipA.publicIp,
        description: "NAT Gateway A Elastic IP",
        tags: commonTags,
    });

    // NAT Gateway B Elastic IPを保存
    new aws.ssm.Parameter("nat-gateway-eip-b", {
        name: pulumi.interpolate`${paramPrefix}/gateway/eip-b`,
        type: "String",
        value: natGatewayEipB.publicIp,
        description: "NAT Gateway B Elastic IP",
        tags: commonTags,
    });

    // NATタイプを保存
    new aws.ssm.Parameter("nat-type", {
        name: pulumi.interpolate`${paramPrefix}/type`,
        type: "String",
        value: "gateway-ha",
        description: "NAT type (gateway-ha)",
        tags: commonTags,
    });

    // NAT設定情報を保存
    new aws.ssm.Parameter("nat-config", {
        name: pulumi.interpolate`${paramPrefix}/config`,
        type: "String",
        value: pulumi.output(projectName).apply(proj => JSON.stringify({
            type: "gateway-ha",
            highAvailability: true,
            instanceType: "N/A",
            projectName: proj,
            environment: environment,
            createdAt: new Date().toISOString(),
        })),
        description: "NAT Gateway configuration for Lambda API infrastructure",
        tags: commonTags,
    });

    // コスト最適化情報のパラメータ
    new aws.ssm.Parameter("nat-cost-info", {
        name: `/lambda-api/${environment}/nat/cost-optimization`,
        type: "String",
        value: JSON.stringify({
            estimatedMonthlyCost: "$90 (NAT Gateway x2)",
            recommendations: [
                "Monitor data transfer costs using CloudWatch",
                "Consider VPC endpoints for AWS services to reduce NAT traffic",
                "Consider NAT Instance for dev/staging to reduce costs",
                "Enable detailed billing reports for accurate cost tracking"
            ],
            dataTransferThreshold: "> 100GB/month",
        }),
        description: "Cost optimization information for NAT Gateway configuration",
        tags: commonTags,
    });

    // デプロイメント完了フラグ
    new aws.ssm.Parameter("nat-deployed", {
        name: pulumi.interpolate`${paramPrefix}/deployment/complete`,
        type: "String",
        value: "true",
        description: "NAT Gateway stack deployment completion flag",
        tags: commonTags,
    });

    return {
        natGatewayAId: natGatewayA.id,
        natGatewayBId: natGatewayB.id,
        natGatewayEipAAddress: natGatewayEipA.publicIp,
        natGatewayEipBAddress: natGatewayEipB.publicIp,
        natResourceIds: [natGatewayA.id, natGatewayB.id],
    };
}