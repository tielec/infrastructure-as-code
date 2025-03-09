import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

export function createNetworkInfrastructure(projectName: string, environment: string) {
    // VPC作成
    const vpc = new aws.ec2.Vpc(`${projectName}-vpc`, {
        cidrBlock: "10.0.0.0/16",
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

    // パブリックサブネット
    const publicSubnet = new aws.ec2.Subnet(`${projectName}-public-subnet`, {
        vpcId: vpc.id,
        cidrBlock: "10.0.0.0/24",
        availabilityZone: azs.names[0],
        mapPublicIpOnLaunch: true,
        tags: {
            Name: `${projectName}-public-subnet-${environment}`,
            Environment: environment,
            Type: "public",
        },
    });

    // プライベートサブネット
    const privateSubnet = new aws.ec2.Subnet(`${projectName}-private-subnet`, {
        vpcId: vpc.id,
        cidrBlock: "10.0.1.0/24",
        availabilityZone: azs.names[0],
        tags: {
            Name: `${projectName}-private-subnet-${environment}`,
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

    // パブリックサブネットとルートテーブルの関連付け
    const publicRtAssociation = new aws.ec2.RouteTableAssociation(`${projectName}-public-rta`, {
        subnetId: publicSubnet.id,
        routeTableId: publicRouteTable.id,
    });

    // プライベートルートテーブル
    const privateRouteTable = new aws.ec2.RouteTable(`${projectName}-private-rt`, {
        vpcId: vpc.id,
        tags: {
            Name: `${projectName}-private-rt-${environment}`,
            Environment: environment,
        },
    });

    // プライベートサブネットとルートテーブルの関連付け
    const privateRtAssociation = new aws.ec2.RouteTableAssociation(`${projectName}-private-rta`, {
        subnetId: privateSubnet.id,
        routeTableId: privateRouteTable.id,
    });

    return {
        vpc,
        igw,
        publicSubnet,
        privateSubnet,
        publicRouteTable,
        privateRouteTable,
    };
}
