/**
 * pulumi/network/index.ts
 * 
 * Jenkinsインフラのネットワークリソースを構築するPulumiスクリプト
 * VPC、サブネット、ルートテーブル、IGWのみを作成（NATは別スタックで管理）
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// コンフィグから設定を取得
const config = new pulumi.Config();
const projectName = config.get("projectName") || "jenkins-infra";
const vpcCidrBlock = config.get("vpcCidr") || "10.0.0.0/16";
const environment = pulumi.getStack();

// VPC作成
const vpc = new aws.ec2.Vpc(`${projectName}-vpc`, {
    cidrBlock: vpcCidrBlock,
    enableDnsHostnames: true,
    enableDnsSupport: true,
    tags: {
        Name: `${projectName}-vpc-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// インターネットゲートウェイ
const igw = new aws.ec2.InternetGateway(`${projectName}-igw`, {
    vpcId: vpc.id,
    tags: {
        Name: `${projectName}-igw-${environment}`,
        Environment: environment,
    },
});

// アベイラビリティゾーン情報の取得
const azs = pulumi.output(aws.getAvailabilityZones({}));

// パブリックサブネットA
const publicSubnetA = new aws.ec2.Subnet(`${projectName}-public-subnet-a`, {
    vpcId: vpc.id,
    cidrBlock: "10.0.0.0/24",
    availabilityZone: azs.names[0],
    mapPublicIpOnLaunch: true,
    tags: {
        Name: `${projectName}-public-subnet-a-${environment}`,
        Environment: environment,
        Type: "public",
    },
});

// パブリックサブネットB
const publicSubnetB = new aws.ec2.Subnet(`${projectName}-public-subnet-b`, {
    vpcId: vpc.id,
    cidrBlock: "10.0.2.0/24",
    availabilityZone: azs.names[1],
    mapPublicIpOnLaunch: true,
    tags: {
        Name: `${projectName}-public-subnet-b-${environment}`,
        Environment: environment,
        Type: "public",
    },
});

// プライベートサブネットA
const privateSubnetA = new aws.ec2.Subnet(`${projectName}-private-subnet-a`, {
    vpcId: vpc.id,
    cidrBlock: "10.0.1.0/24",
    availabilityZone: azs.names[0],
    tags: {
        Name: `${projectName}-private-subnet-a-${environment}`,
        Environment: environment,
        Type: "private",
    },
});

// プライベートサブネットB
const privateSubnetB = new aws.ec2.Subnet(`${projectName}-private-subnet-b`, {
    vpcId: vpc.id,
    cidrBlock: "10.0.3.0/24",
    availabilityZone: azs.names[1],
    tags: {
        Name: `${projectName}-private-subnet-b-${environment}`,
        Environment: environment,
        Type: "private",
    },
});

// パブリックルートテーブル
const publicRouteTable = new aws.ec2.RouteTable(`${projectName}-public-rt`, {
    vpcId: vpc.id,
    tags: {
        Name: `${projectName}-public-rt-${environment}`,
        Environment: environment,
    },
});

// パブリックルート（インターネットゲートウェイ向け）
const publicRoute = new aws.ec2.Route(`${projectName}-public-route`, {
    routeTableId: publicRouteTable.id,
    destinationCidrBlock: "0.0.0.0/0",
    gatewayId: igw.id,
});

// パブリックサブネットAとルートテーブルの関連付け
const publicRtAssociationA = new aws.ec2.RouteTableAssociation(`${projectName}-public-rta-a`, {
    subnetId: publicSubnetA.id,
    routeTableId: publicRouteTable.id,
});

// パブリックサブネットBとルートテーブルの関連付け
const publicRtAssociationB = new aws.ec2.RouteTableAssociation(`${projectName}-public-rta-b`, {
    subnetId: publicSubnetB.id,
    routeTableId: publicRouteTable.id,
});

// プライベートルートテーブルA
const privateRouteTableA = new aws.ec2.RouteTable(`${projectName}-private-rt-a`, {
    vpcId: vpc.id,
    tags: {
        Name: `${projectName}-private-rt-a-${environment}`,
        Environment: environment,
    },
});

// プライベートルートテーブルB
const privateRouteTableB = new aws.ec2.RouteTable(`${projectName}-private-rt-b`, {
    vpcId: vpc.id,
    tags: {
        Name: `${projectName}-private-rt-b-${environment}`,
        Environment: environment,
    },
});

// プライベートサブネットAとルートテーブルの関連付け
const privateRtAssociationA = new aws.ec2.RouteTableAssociation(`${projectName}-private-rta-a`, {
    subnetId: privateSubnetA.id,
    routeTableId: privateRouteTableA.id,
});

// プライベートサブネットBとルートテーブルの関連付け
const privateRtAssociationB = new aws.ec2.RouteTableAssociation(`${projectName}-private-rta-b`, {
    subnetId: privateSubnetB.id,
    routeTableId: privateRouteTableB.id,
});

// ================ SSM Parameter Store への保存 ================

// VPC情報の保存
const vpcIdParameter = new aws.ssm.Parameter(`${projectName}-vpc-id-param`, {
    name: `/${projectName}/${environment}/network/vpcId`,
    type: "String",
    value: vpc.id,
    description: `VPC ID for ${projectName} ${environment}`,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

const vpcCidrParameter = new aws.ssm.Parameter(`${projectName}-vpc-cidr-param`, {
    name: `/${projectName}/${environment}/network/vpcCidr`,
    type: "String",
    value: vpc.cidrBlock,
    description: `VPC CIDR block for ${projectName} ${environment}`,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// パブリックサブネット情報の保存
const publicSubnetAIdParameter = new aws.ssm.Parameter(`${projectName}-public-subnet-a-id-param`, {
    name: `/${projectName}/${environment}/network/publicSubnetAId`,
    type: "String",
    value: publicSubnetA.id,
    description: `Public Subnet A ID for ${projectName} ${environment}`,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

const publicSubnetBIdParameter = new aws.ssm.Parameter(`${projectName}-public-subnet-b-id-param`, {
    name: `/${projectName}/${environment}/network/publicSubnetBId`,
    type: "String",
    value: publicSubnetB.id,
    description: `Public Subnet B ID for ${projectName} ${environment}`,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// プライベートサブネット情報の保存
const privateSubnetAIdParameter = new aws.ssm.Parameter(`${projectName}-private-subnet-a-id-param`, {
    name: `/${projectName}/${environment}/network/privateSubnetAId`,
    type: "String",
    value: privateSubnetA.id,
    description: `Private Subnet A ID for ${projectName} ${environment}`,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

const privateSubnetBIdParameter = new aws.ssm.Parameter(`${projectName}-private-subnet-b-id-param`, {
    name: `/${projectName}/${environment}/network/privateSubnetBId`,
    type: "String",
    value: privateSubnetB.id,
    description: `Private Subnet B ID for ${projectName} ${environment}`,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// サブネットIDリストの保存（JSON形式）
const publicSubnetIdsParameter = new aws.ssm.Parameter(`${projectName}-public-subnet-ids-param`, {
    name: `/${projectName}/${environment}/network/publicSubnetIds`,
    type: "StringList",
    value: pulumi.interpolate`${publicSubnetA.id},${publicSubnetB.id}`,
    description: `Public Subnet IDs for ${projectName} ${environment}`,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

const privateSubnetIdsParameter = new aws.ssm.Parameter(`${projectName}-private-subnet-ids-param`, {
    name: `/${projectName}/${environment}/network/privateSubnetIds`,
    type: "StringList",
    value: pulumi.interpolate`${privateSubnetA.id},${privateSubnetB.id}`,
    description: `Private Subnet IDs for ${projectName} ${environment}`,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// ルートテーブル情報の保存
const publicRouteTableIdParameter = new aws.ssm.Parameter(`${projectName}-public-rt-id-param`, {
    name: `/${projectName}/${environment}/network/publicRouteTableId`,
    type: "String",
    value: publicRouteTable.id,
    description: `Public Route Table ID for ${projectName} ${environment}`,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

const privateRouteTableAIdParameter = new aws.ssm.Parameter(`${projectName}-private-rt-a-id-param`, {
    name: `/${projectName}/${environment}/network/privateRouteTableAId`,
    type: "String",
    value: privateRouteTableA.id,
    description: `Private Route Table A ID for ${projectName} ${environment}`,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

const privateRouteTableBIdParameter = new aws.ssm.Parameter(`${projectName}-private-rt-b-id-param`, {
    name: `/${projectName}/${environment}/network/privateRouteTableBId`,
    type: "String",
    value: privateRouteTableB.id,
    description: `Private Route Table B ID for ${projectName} ${environment}`,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// インターネットゲートウェイ情報の保存
const igwIdParameter = new aws.ssm.Parameter(`${projectName}-igw-id-param`, {
    name: `/${projectName}/${environment}/network/internetGatewayId`,
    type: "String",
    value: igw.id,
    description: `Internet Gateway ID for ${projectName} ${environment}`,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// アベイラビリティゾーン情報の保存
const azNamesParameter = new aws.ssm.Parameter(`${projectName}-az-names-param`, {
    name: `/${projectName}/${environment}/network/availabilityZones`,
    type: "StringList",
    value: azs.names.apply(names => names.slice(0, 2).join(",")),
    description: `Availability Zones used for ${projectName} ${environment}`,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// エクスポート
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

// SSM Parameterのエクスポート（確認用）
export const ssmParameters = {
    vpcId: vpcIdParameter.name,
    vpcCidr: vpcCidrParameter.name,
    publicSubnetAId: publicSubnetAIdParameter.name,
    publicSubnetBId: publicSubnetBIdParameter.name,
    privateSubnetAId: privateSubnetAIdParameter.name,
    privateSubnetBId: privateSubnetBIdParameter.name,
    publicSubnetIds: publicSubnetIdsParameter.name,
    privateSubnetIds: privateSubnetIdsParameter.name,
    publicRouteTableId: publicRouteTableIdParameter.name,
    privateRouteTableAId: privateRouteTableAIdParameter.name,
    privateRouteTableBId: privateRouteTableBIdParameter.name,
    internetGatewayId: igwIdParameter.name,
    availabilityZones: azNamesParameter.name,
};
