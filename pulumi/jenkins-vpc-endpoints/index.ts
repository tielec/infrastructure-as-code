/**
 * pulumi/jenkins-vpc-endpoints/index.ts
 * 
 * VPCエンドポイントを作成してプライベートサブネットからAWSサービスへの接続を可能にする
 * SSM、EC2、S3などのエンドポイントを作成
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
const vpcIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/vpc-id`,
});
const privateSubnetAIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/private-subnet-a-id`,
});
const privateSubnetBIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/private-subnet-b-id`,
});
const jenkinsSecurityGroupIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/security/jenkins-sg-id`,
});

// 設定値を変数に設定
const projectName = pulumi.output(projectNameParam).apply(p => p.value);
const vpcId = pulumi.output(vpcIdParam).apply(p => p.value);
const privateSubnetAId = pulumi.output(privateSubnetAIdParam).apply(p => p.value);
const privateSubnetBId = pulumi.output(privateSubnetBIdParam).apply(p => p.value);
const jenkinsSecurityGroupId = pulumi.output(jenkinsSecurityGroupIdParam).apply(p => p.value);

// 現在のリージョンを取得
const current = aws.getRegion();
const region = current.then(r => r.name);

// VPCエンドポイント用セキュリティグループ
const vpcEndpointSecurityGroup = new aws.ec2.SecurityGroup(`vpc-endpoint-sg`, {
    vpcId: vpcId,
    description: "Security group for VPC endpoints",
    ingress: [
        {
            protocol: "tcp",
            fromPort: 443,
            toPort: 443,
            securityGroups: [jenkinsSecurityGroupId],
            description: "HTTPS access from Jenkins instances",
        },
        {
            protocol: "tcp",
            fromPort: 443,
            toPort: 443,
            cidrBlocks: ["10.0.0.0/16"],
            description: "HTTPS access from VPC",
        },
    ],
    egress: [
        {
            protocol: "-1",
            fromPort: 0,
            toPort: 0,
            cidrBlocks: ["0.0.0.0/0"],
            description: "Allow all outbound traffic",
        },
    ],
    tags: {
        Name: pulumi.interpolate`${projectName}-vpc-endpoint-sg-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// SSM用VPCエンドポイント
const ssmEndpoint = new aws.ec2.VpcEndpoint(`ssm-endpoint`, {
    vpcId: vpcId,
    serviceName: pulumi.interpolate`com.amazonaws.${region}.ssm`,
    vpcEndpointType: "Interface",
    subnetIds: [privateSubnetAId, privateSubnetBId],
    securityGroupIds: [vpcEndpointSecurityGroup.id],
    privateDnsEnabled: true,
    tags: {
        Name: pulumi.interpolate`${projectName}-ssm-endpoint-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// SSM Messages用VPCエンドポイント（Session Manager用）
const ssmMessagesEndpoint = new aws.ec2.VpcEndpoint(`ssm-messages-endpoint`, {
    vpcId: vpcId,
    serviceName: pulumi.interpolate`com.amazonaws.${region}.ssmmessages`,
    vpcEndpointType: "Interface",
    subnetIds: [privateSubnetAId, privateSubnetBId],
    securityGroupIds: [vpcEndpointSecurityGroup.id],
    privateDnsEnabled: true,
    tags: {
        Name: pulumi.interpolate`${projectName}-ssm-messages-endpoint-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// EC2 Messages用VPCエンドポイント（SSMエージェント用）
const ec2MessagesEndpoint = new aws.ec2.VpcEndpoint(`ec2-messages-endpoint`, {
    vpcId: vpcId,
    serviceName: pulumi.interpolate`com.amazonaws.${region}.ec2messages`,
    vpcEndpointType: "Interface",
    subnetIds: [privateSubnetAId, privateSubnetBId],
    securityGroupIds: [vpcEndpointSecurityGroup.id],
    privateDnsEnabled: true,
    tags: {
        Name: pulumi.interpolate`${projectName}-ec2-messages-endpoint-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// EC2用VPCエンドポイント
const ec2Endpoint = new aws.ec2.VpcEndpoint(`ec2-endpoint`, {
    vpcId: vpcId,
    serviceName: pulumi.interpolate`com.amazonaws.${region}.ec2`,
    vpcEndpointType: "Interface",
    subnetIds: [privateSubnetAId, privateSubnetBId],
    securityGroupIds: [vpcEndpointSecurityGroup.id],
    privateDnsEnabled: true,
    tags: {
        Name: pulumi.interpolate`${projectName}-ec2-endpoint-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// S3用VPCエンドポイント（ゲートウェイタイプ）
const s3Endpoint = new aws.ec2.VpcEndpoint(`s3-endpoint`, {
    vpcId: vpcId,
    serviceName: pulumi.interpolate`com.amazonaws.${region}.s3`,
    vpcEndpointType: "Gateway",
    routeTableIds: [], // 必要に応じてルートテーブルIDを追加
    tags: {
        Name: pulumi.interpolate`${projectName}-s3-endpoint-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// SSMパラメータとして保存
const vpcEndpointSgIdParam = new aws.ssm.Parameter("vpc-endpoint-sg-id", {
    name: `${ssmPrefix}/vpc-endpoints/security-group-id`,
    type: "String",
    value: vpcEndpointSecurityGroup.id,
    description: "VPC Endpoint security group ID",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

const ssmEndpointIdParam = new aws.ssm.Parameter("ssm-endpoint-id", {
    name: `${ssmPrefix}/vpc-endpoints/ssm-endpoint-id`,
    type: "String",
    value: ssmEndpoint.id,
    description: "SSM VPC Endpoint ID",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

const ssmMessagesEndpointIdParam = new aws.ssm.Parameter("ssm-messages-endpoint-id", {
    name: `${ssmPrefix}/vpc-endpoints/ssm-messages-endpoint-id`,
    type: "String",
    value: ssmMessagesEndpoint.id,
    description: "SSM Messages VPC Endpoint ID",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

const ec2MessagesEndpointIdParam = new aws.ssm.Parameter("ec2-messages-endpoint-id", {
    name: `${ssmPrefix}/vpc-endpoints/ec2-messages-endpoint-id`,
    type: "String",
    value: ec2MessagesEndpoint.id,
    description: "EC2 Messages VPC Endpoint ID",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

const ec2EndpointIdParam = new aws.ssm.Parameter("ec2-endpoint-id", {
    name: `${ssmPrefix}/vpc-endpoints/ec2-endpoint-id`,
    type: "String",
    value: ec2Endpoint.id,
    description: "EC2 VPC Endpoint ID",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

const s3EndpointIdParam = new aws.ssm.Parameter("s3-endpoint-id", {
    name: `${ssmPrefix}/vpc-endpoints/s3-endpoint-id`,
    type: "String",
    value: s3Endpoint.id,
    description: "S3 VPC Endpoint ID",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// エクスポート
export const vpcEndpointSecurityGroupId = vpcEndpointSecurityGroup.id;
export const ssmEndpointId = ssmEndpoint.id;
export const ssmMessagesEndpointId = ssmMessagesEndpoint.id;
export const ec2MessagesEndpointId = ec2MessagesEndpoint.id;
export const ec2EndpointId = ec2Endpoint.id;
export const s3EndpointId = s3Endpoint.id;