/**
 * pulumi/network/index.ts
 * 
 * Jenkinsインフラのネットワークリソースを構築するPulumiスクリプト
 * IPv6デュアルスタック対応：VPC、サブネット、ルートテーブル、IGW、EIGW
 * NATは使用せず、IPv6によるインターネットアクセスを実現
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
const vpcCidrParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/vpc-cidr`,
});

// 設定値を変数に設定
const projectName = pulumi.output(projectNameParam).apply(p => p.value);
const vpcCidrBlock = pulumi.output(vpcCidrParam).apply(p => p.value);

// VPC作成（IPv6対応）
const vpc = new aws.ec2.Vpc(`vpc`, {
    cidrBlock: vpcCidrBlock,
    enableDnsHostnames: true,
    enableDnsSupport: true,
    assignGeneratedIpv6CidrBlock: true,  // IPv6 CIDRブロックを自動割り当て
    tags: {
        Name: pulumi.interpolate`${projectName}-vpc-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
        IPv6Enabled: "true",
    },
});

// インターネットゲートウェイ（IPv4/IPv6両対応）
const igw = new aws.ec2.InternetGateway(`igw`, {
    vpcId: vpc.id,
    tags: {
        Name: pulumi.interpolate`${projectName}-igw-${environment}`,
        Environment: environment,
        IPv6Enabled: "true",
    },
});

// Egress-only Internet Gateway（IPv6専用のアウトバウンド通信用）
const eigw = new aws.ec2.EgressOnlyInternetGateway(`eigw`, {
    vpcId: vpc.id,
    tags: {
        Name: pulumi.interpolate`${projectName}-eigw-${environment}`,
        Environment: environment,
    },
});

// アベイラビリティゾーン情報の取得
const azs = pulumi.output(aws.getAvailabilityZones({}));

// IPv6サブネットCIDRを計算する関数
// VPCは/56、サブネットは/64 (8ビット分のサブネット番号を追加)
const calculateIpv6SubnetCidr = (vpcCidr: string, subnetNum: number): string => {
    if (!vpcCidr) return "";
    // 例: "2406:da14:2fa:d900::/56" から "2406:da14:2fa:d9" を抽出
    const baseParts = vpcCidr.split(":");
    const prefix = baseParts.slice(0, 3).join(":"); // "2406:da14:2fa"
    const fourthSegment = baseParts[3].substring(0, 2); // "d9"
    const subnetHex = subnetNum.toString(16).padStart(2, "0"); // "00", "01", "02", "03"
    return `${prefix}:${fourthSegment}${subnetHex}::/64`;
};

// パブリックサブネットA用のIPv6 CIDR
const publicSubnetAIpv6Cidr = vpc.ipv6CidrBlock.apply(cidr => 
    cidr ? calculateIpv6SubnetCidr(cidr, 0) : undefined
);

// パブリックサブネットA（IPv6対応）
const publicSubnetA = new aws.ec2.Subnet(`public-subnet-a`, {
    vpcId: vpc.id,
    cidrBlock: "10.0.0.0/24",
    ipv6CidrBlock: publicSubnetAIpv6Cidr,
    availabilityZone: azs.names[0],
    mapPublicIpOnLaunch: true,
    assignIpv6AddressOnCreation: true,  // IPv6アドレスを自動割り当て
    tags: {
        Name: pulumi.interpolate`${projectName}-public-subnet-a-${environment}`,
        Environment: environment,
        Type: "public",
        IPv6Enabled: "true",
    },
});

// パブリックサブネットB用のIPv6 CIDR
const publicSubnetBIpv6Cidr = vpc.ipv6CidrBlock.apply(cidr => 
    cidr ? calculateIpv6SubnetCidr(cidr, 2) : undefined
);

// パブリックサブネットB（IPv6対応）
const publicSubnetB = new aws.ec2.Subnet(`public-subnet-b`, {
    vpcId: vpc.id,
    cidrBlock: "10.0.2.0/24",
    ipv6CidrBlock: publicSubnetBIpv6Cidr,
    availabilityZone: azs.names[1],
    mapPublicIpOnLaunch: true,
    assignIpv6AddressOnCreation: true,
    tags: {
        Name: pulumi.interpolate`${projectName}-public-subnet-b-${environment}`,
        Environment: environment,
        Type: "public",
        IPv6Enabled: "true",
    },
});

// プライベートサブネットA用のIPv6 CIDR
const privateSubnetAIpv6Cidr = vpc.ipv6CidrBlock.apply(cidr => 
    cidr ? calculateIpv6SubnetCidr(cidr, 1) : undefined
);

// プライベートサブネットA（IPv6対応）
const privateSubnetA = new aws.ec2.Subnet(`private-subnet-a`, {
    vpcId: vpc.id,
    cidrBlock: "10.0.1.0/24",
    ipv6CidrBlock: privateSubnetAIpv6Cidr,
    availabilityZone: azs.names[0],
    assignIpv6AddressOnCreation: true,  // プライベートサブネットでもIPv6を有効化
    tags: {
        Name: pulumi.interpolate`${projectName}-private-subnet-a-${environment}`,
        Environment: environment,
        Type: "private",
        IPv6Enabled: "true",
    },
});

// プライベートサブネットB用のIPv6 CIDR
const privateSubnetBIpv6Cidr = vpc.ipv6CidrBlock.apply(cidr => 
    cidr ? calculateIpv6SubnetCidr(cidr, 3) : undefined
);

// プライベートサブネットB（IPv6対応）
const privateSubnetB = new aws.ec2.Subnet(`private-subnet-b`, {
    vpcId: vpc.id,
    cidrBlock: "10.0.3.0/24",
    ipv6CidrBlock: privateSubnetBIpv6Cidr,
    availabilityZone: azs.names[1],
    assignIpv6AddressOnCreation: true,
    tags: {
        Name: pulumi.interpolate`${projectName}-private-subnet-b-${environment}`,
        Environment: environment,
        Type: "private",
        IPv6Enabled: "true",
    },
});

// パブリックルートテーブル
const publicRouteTable = new aws.ec2.RouteTable(`public-rt`, {
    vpcId: vpc.id,
    tags: {
        Name: pulumi.interpolate`${projectName}-public-rt-${environment}`,
        Environment: environment,
    },
});

// パブリックルート（IPv4 - インターネットゲートウェイ向け）
const publicRoute = new aws.ec2.Route(`public-route`, {
    routeTableId: publicRouteTable.id,
    destinationCidrBlock: "0.0.0.0/0",
    gatewayId: igw.id,
});

// パブリックルート（IPv6 - インターネットゲートウェイ向け）
const publicRouteIpv6 = new aws.ec2.Route(`public-route-ipv6`, {
    routeTableId: publicRouteTable.id,
    destinationIpv6CidrBlock: "::/0",
    gatewayId: igw.id,
});

// パブリックサブネットAとルートテーブルの関連付け
const publicRtAssociationA = new aws.ec2.RouteTableAssociation(`public-rta-a`, {
    subnetId: publicSubnetA.id,
    routeTableId: publicRouteTable.id,
});

// パブリックサブネットBとルートテーブルの関連付け
const publicRtAssociationB = new aws.ec2.RouteTableAssociation(`public-rta-b`, {
    subnetId: publicSubnetB.id,
    routeTableId: publicRouteTable.id,
});

// プライベートルートテーブルA
const privateRouteTableA = new aws.ec2.RouteTable(`private-rt-a`, {
    vpcId: vpc.id,
    tags: {
        Name: pulumi.interpolate`${projectName}-private-rt-a-${environment}`,
        Environment: environment,
    },
});

// プライベートルートテーブルB
const privateRouteTableB = new aws.ec2.RouteTable(`private-rt-b`, {
    vpcId: vpc.id,
    tags: {
        Name: pulumi.interpolate`${projectName}-private-rt-b-${environment}`,
        Environment: environment,
    },
});

// プライベートサブネットAとルートテーブルの関連付け
const privateRtAssociationA = new aws.ec2.RouteTableAssociation(`private-rta-a`, {
    subnetId: privateSubnetA.id,
    routeTableId: privateRouteTableA.id,
});

// プライベートサブネットBとルートテーブルの関連付け
const privateRtAssociationB = new aws.ec2.RouteTableAssociation(`private-rta-b`, {
    subnetId: privateSubnetB.id,
    routeTableId: privateRouteTableB.id,
});

// プライベートルート（IPv6 - Egress-only Internet Gateway向け）
const privateRouteAIpv6 = new aws.ec2.Route(`private-route-a-ipv6`, {
    routeTableId: privateRouteTableA.id,
    destinationIpv6CidrBlock: "::/0",
    egressOnlyGatewayId: eigw.id,
});

const privateRouteBIpv6 = new aws.ec2.Route(`private-route-b-ipv6`, {
    routeTableId: privateRouteTableB.id,
    destinationIpv6CidrBlock: "::/0",
    egressOnlyGatewayId: eigw.id,
});

// SSMパラメータストアへの保存
// VPC情報をSSMに保存
const vpcIdParam = new aws.ssm.Parameter(`vpc-id`, {
    name: `${ssmPrefix}/network/vpc-id`,
    type: "String",
    value: vpc.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "network",
    },
});

// IPv6 CIDRをSSMに保存
const vpcIpv6CidrParam = new aws.ssm.Parameter(`vpc-ipv6-cidr`, {
    name: `${ssmPrefix}/network/vpc-ipv6-cidr`,
    type: "String",
    value: vpc.ipv6CidrBlock,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "network",
    },
});

// サブネット情報をSSMに保存
const publicSubnetAIdParam = new aws.ssm.Parameter(`public-subnet-a-id`, {
    name: `${ssmPrefix}/network/public-subnet-a-id`,
    type: "String",
    value: publicSubnetA.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "network",
    },
});

const publicSubnetBIdParam = new aws.ssm.Parameter(`public-subnet-b-id`, {
    name: `${ssmPrefix}/network/public-subnet-b-id`,
    type: "String",
    value: publicSubnetB.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "network",
    },
});

const privateSubnetAIdParam = new aws.ssm.Parameter(`private-subnet-a-id`, {
    name: `${ssmPrefix}/network/private-subnet-a-id`,
    type: "String",
    value: privateSubnetA.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "network",
    },
});

const privateSubnetBIdParam = new aws.ssm.Parameter(`private-subnet-b-id`, {
    name: `${ssmPrefix}/network/private-subnet-b-id`,
    type: "String",
    value: privateSubnetB.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "network",
    },
});

// サブネットIDのリストをカンマ区切りで保存
const publicSubnetIdsParam = new aws.ssm.Parameter(`public-subnet-ids`, {
    name: `${ssmPrefix}/network/public-subnet-ids`,
    type: "StringList",
    value: pulumi.interpolate`${publicSubnetA.id},${publicSubnetB.id}`,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "network",
    },
});

const privateSubnetIdsParam = new aws.ssm.Parameter(`private-subnet-ids`, {
    name: `${ssmPrefix}/network/private-subnet-ids`,
    type: "StringList",
    value: pulumi.interpolate`${privateSubnetA.id},${privateSubnetB.id}`,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "network",
    },
});

// インターネットゲートウェイ情報をSSMに保存
const igwIdParam = new aws.ssm.Parameter(`igw-id`, {
    name: `${ssmPrefix}/network/igw-id`,
    type: "String",
    value: igw.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "network",
    },
});

// Egress-only Internet Gateway情報をSSMに保存
const eigwIdParam = new aws.ssm.Parameter(`eigw-id`, {
    name: `${ssmPrefix}/network/eigw-id`,
    type: "String",
    value: eigw.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "network",
    },
});

// ルートテーブル情報をSSMに保存
const publicRouteTableIdParam = new aws.ssm.Parameter(`public-rt-id`, {
    name: `${ssmPrefix}/network/public-route-table-id`,
    type: "String",
    value: publicRouteTable.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "network",
    },
});

const privateRouteTableAIdParam = new aws.ssm.Parameter(`private-rt-a-id`, {
    name: `${ssmPrefix}/network/private-route-table-a-id`,
    type: "String",
    value: privateRouteTableA.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "network",
    },
});

const privateRouteTableBIdParam = new aws.ssm.Parameter(`private-rt-b-id`, {
    name: `${ssmPrefix}/network/private-route-table-b-id`,
    type: "String",
    value: privateRouteTableB.id,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "network",
    },
});

const privateRouteTableIdsParam = new aws.ssm.Parameter(`private-rt-ids`, {
    name: `${ssmPrefix}/network/private-route-table-ids`,
    type: "StringList",
    value: pulumi.interpolate`${privateRouteTableA.id},${privateRouteTableB.id}`,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "network",
    },
});

// エクスポート（既存のスタック参照用に残す）
export const vpcId = vpc.id;
export const vpcCidr = vpc.cidrBlock;
export const vpcIpv6Cidr = vpc.ipv6CidrBlock;
export const publicSubnetIds = [publicSubnetA.id, publicSubnetB.id];
export const privateSubnetIds = [privateSubnetA.id, privateSubnetB.id];
export const publicSubnetAId = publicSubnetA.id;
export const publicSubnetBId = publicSubnetB.id;
export const privateSubnetAId = privateSubnetA.id;
export const privateSubnetBId = privateSubnetB.id;
export const internetGatewayId = igw.id;
export const egressOnlyInternetGatewayId = eigw.id;
export const publicRouteTableId = publicRouteTable.id;
export const privateRouteTableAId = privateRouteTableA.id;
export const privateRouteTableBId = privateRouteTableB.id;
export const privateRouteTableIds = [privateRouteTableA.id, privateRouteTableB.id];
