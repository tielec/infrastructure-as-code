/**
 * pulumi/network/index.ts
 * 
 * Jenkinsインフラのネットワークリソースを構築するPulumiスクリプト
 * VPC、サブネット、ルートテーブル、IGWのみを作成（NATは別スタックで管理）
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

// VPC作成
const vpc = new aws.ec2.Vpc(`vpc`, {
    cidrBlock: vpcCidrBlock,
    enableDnsHostnames: true,
    enableDnsSupport: true,
    tags: {
        Name: pulumi.interpolate`${projectName}-vpc-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// インターネットゲートウェイ
const igw = new aws.ec2.InternetGateway(`igw`, {
    vpcId: vpc.id,
    tags: {
        Name: pulumi.interpolate`${projectName}-igw-${environment}`,
        Environment: environment,
    },
});

// アベイラビリティゾーン情報の取得
const azs = pulumi.output(aws.getAvailabilityZones({}));

// パブリックサブネットA
const publicSubnetA = new aws.ec2.Subnet(`public-subnet-a`, {
    vpcId: vpc.id,
    cidrBlock: "10.0.0.0/24",
    availabilityZone: azs.names[0],
    mapPublicIpOnLaunch: true,
    tags: {
        Name: pulumi.interpolate`${projectName}-public-subnet-a-${environment}`,
        Environment: environment,
        Type: "public",
    },
});

// パブリックサブネットB
const publicSubnetB = new aws.ec2.Subnet(`public-subnet-b`, {
    vpcId: vpc.id,
    cidrBlock: "10.0.2.0/24",
    availabilityZone: azs.names[1],
    mapPublicIpOnLaunch: true,
    tags: {
        Name: pulumi.interpolate`${projectName}-public-subnet-b-${environment}`,
        Environment: environment,
        Type: "public",
    },
});

// プライベートサブネットA
const privateSubnetA = new aws.ec2.Subnet(`private-subnet-a`, {
    vpcId: vpc.id,
    cidrBlock: "10.0.1.0/24",
    availabilityZone: azs.names[0],
    tags: {
        Name: pulumi.interpolate`${projectName}-private-subnet-a-${environment}`,
        Environment: environment,
        Type: "private",
    },
});

// プライベートサブネットB
const privateSubnetB = new aws.ec2.Subnet(`private-subnet-b`, {
    vpcId: vpc.id,
    cidrBlock: "10.0.3.0/24",
    availabilityZone: azs.names[1],
    tags: {
        Name: pulumi.interpolate`${projectName}-private-subnet-b-${environment}`,
        Environment: environment,
        Type: "private",
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

// パブリックルート（インターネットゲートウェイ向け）
const publicRoute = new aws.ec2.Route(`public-route`, {
    routeTableId: publicRouteTable.id,
    destinationCidrBlock: "0.0.0.0/0",
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

const vpcCidrOutputParam = new aws.ssm.Parameter(`vpc-cidr-output`, {
    name: `${ssmPrefix}/network/vpc-cidr`,
    type: "String",
    value: vpc.cidrBlock,
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

// インターネットゲートウェイ情報をSSMに保官
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
export const publicSubnetIds = [publicSubnetA.id, publicSubnetB.id];
export const privateSubnetIds = [privateSubnetA.id, privateSubnetB.id];
export const publicSubnetAId = publicSubnetA.id;
export const publicSubnetBId = publicSubnetB.id;
export const privateSubnetAId = privateSubnetA.id;
export const privateSubnetBId = privateSubnetB.id;
export const internetGatewayId = igw.id;
export const publicRouteTableId = publicRouteTable.id;
export const privateRouteTableAId = privateRouteTableA.id;
export const privateRouteTableBId = privateRouteTableB.id;
export const privateRouteTableIds = [privateRouteTableA.id, privateRouteTableB.id];
