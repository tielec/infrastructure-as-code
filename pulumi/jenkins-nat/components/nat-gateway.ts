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
    /** SSMパラメータのプレフィックス */
    ssmPrefix: string;
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
        ssmPrefix,
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
    // SSMパラメータに保存
    // ========================================
    // NAT Gateway AのIDをSSMに保存
    new aws.ssm.Parameter("nat-gateway-a-id", {
        name: `${ssmPrefix}/nat/gateway-a-id`,
        type: "String",
        value: natGatewayA.id,
        overwrite: true,
        tags: {
            ...commonTags,
            Component: "nat",
        },
    });

    // NAT Gateway BのIDをSSMに保存
    new aws.ssm.Parameter("nat-gateway-b-id", {
        name: `${ssmPrefix}/nat/gateway-b-id`,
        type: "String",
        value: natGatewayB.id,
        overwrite: true,
        tags: {
            ...commonTags,
            Component: "nat",
        },
    });

    // NAT Gateway EIP AのアドレスをSSMに保存
    new aws.ssm.Parameter("nat-gateway-eip-a", {
        name: `${ssmPrefix}/nat/gateway-eip-a`,
        type: "String",
        value: natGatewayEipA.publicIp,
        overwrite: true,
        tags: {
            ...commonTags,
            Component: "nat",
        },
    });

    // NAT Gateway EIP BのアドレスをSSMに保存
    new aws.ssm.Parameter("nat-gateway-eip-b", {
        name: `${ssmPrefix}/nat/gateway-eip-b`,
        type: "String",
        value: natGatewayEipB.publicIp,
        overwrite: true,
        tags: {
            ...commonTags,
            Component: "nat",
        },
    });

    // ========================================
    // デバッグログ出力
    // ========================================
    pulumi.log.info("NAT Gateway HA configuration created successfully");
    natGatewayEipA.publicIp.apply(ip => {
        pulumi.log.info(`NAT Gateway A EIP: ${ip}`);
    });
    natGatewayEipB.publicIp.apply(ip => {
        pulumi.log.info(`NAT Gateway B EIP: ${ip}`);
    });

    return {
        natGatewayAId: natGatewayA.id,
        natGatewayBId: natGatewayB.id,
        natGatewayEipAAddress: natGatewayEipA.publicIp,
        natGatewayEipBAddress: natGatewayEipB.publicIp,
        natResourceIds: [natGatewayA.id, natGatewayB.id],
    };
}