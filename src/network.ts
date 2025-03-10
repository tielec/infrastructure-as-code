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

    // NATゲートウェイのEIPを作成
    const natGatewayEipA = new aws.ec2.Eip(`${projectName}-nat-eip-a`, {
        vpc: true,
        tags: {
            Name: `${projectName}-nat-eip-a-${environment}`,
            Environment: environment,
        },
    });

    const natGatewayA = new aws.ec2.NatGateway(`${projectName}-nat-a`, {
        allocationId: natGatewayEipA.id,
        subnetId: publicSubnetA.id,
        tags: {
            Name: `${projectName}-nat-a-${environment}`,
            Environment: environment,
        },
    });

    const privateRouteToNatA = new aws.ec2.Route(`${projectName}-private-route-a`, {
        routeTableId: privateRouteTableA.id,
        destinationCidrBlock: "0.0.0.0/0",
        natGatewayId: natGatewayA.id,
    });
    
    // 高可用性のための2つ目のNATゲートウェイ
    const natGatewayEipB = new aws.ec2.Eip(`${projectName}-nat-eip-b`, {
        vpc: true,
        tags: {
            Name: `${projectName}-nat-eip-b-${environment}`,
            Environment: environment,
        },
    });

    const natGatewayB = new aws.ec2.NatGateway(`${projectName}-nat-b`, {
        allocationId: natGatewayEipB.id,
        subnetId: publicSubnetB.id,
        tags: {
            Name: `${projectName}-nat-b-${environment}`,
            Environment: environment,
        },
    });

    const privateRouteToNatB = new aws.ec2.Route(`${projectName}-private-route-b`, {
        routeTableId: privateRouteTableB.id,
        destinationCidrBlock: "0.0.0.0/0",
        natGatewayId: natGatewayB.id,
    });

    return {
        vpc,
        igw,
        publicSubnets: [publicSubnetA, publicSubnetB],
        privateSubnets: [privateSubnetA, privateSubnetB],
        publicSubnetA,
        publicSubnetB,
        privateSubnetA,
        privateSubnetB,
        publicRouteTable,
        privateRouteTableA,
        privateRouteTableB,
        natGatewayA,
        natGatewayB,
    };
}
