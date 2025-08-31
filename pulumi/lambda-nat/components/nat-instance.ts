/**
 * components/nat-instance.ts
 * 
 * NAT Instance（通常モード）用のコンポーネント
 * コスト最適化のため単一のNAT Instanceを使用
 * Amazon Linux 2023 + nftablesベース
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as fs from "fs";
import * as path from "path";

// Node.jsグローバル変数の型定義を確実にするため
declare const __dirname: string;
declare const process: NodeJS.Process;

/**
 * NAT Instance構成の入力パラメータ
 */
export interface NatInstanceArgs {
    /** プロジェクト名 */
    projectName: pulumi.Output<string>;
    /** 環境名 */
    environment: string;
    /** VPC CIDR */
    vpcCidr: pulumi.Output<string>;
    /** NAT Instanceタイプ */
    natInstanceType: pulumi.Output<string>;
    /** パブリックサブネットA ID */
    publicSubnetAId: pulumi.Output<string>;
    /** プライベートルートテーブルA ID */
    privateRouteTableAId: pulumi.Output<string>;
    /** プライベートルートテーブルB ID */
    privateRouteTableBId: pulumi.Output<string>;
    /** NAT Instance用セキュリティグループID */
    natInstanceSecurityGroupId: pulumi.Output<string>;
    /** 共通タグ */
    commonTags: Record<string, string>;
}

/**
 * NAT Instance構成の出力
 */
export interface NatInstanceOutputs {
    /** NAT Instance ID */
    natInstanceId: pulumi.Output<string>;
    /** NAT Instance Public IP */
    natInstancePublicIp: pulumi.Output<string>;
    /** NAT Instance Private IP */
    natInstancePrivateIp: pulumi.Output<string>;
    /** NAT リソースID配列 */
    natResourceIds: pulumi.Output<string>[];
}

/**
 * NAT Instance（通常モード）を作成
 * 
 * @param args NAT Instance構成パラメータ
 * @returns NAT Instanceリソース情報
 */
export function createNatInstance(args: NatInstanceArgs): NatInstanceOutputs {
    const {
        projectName,
        environment,
        vpcCidr,
        natInstanceType,
        publicSubnetAId,
        privateRouteTableAId,
        privateRouteTableBId,
        natInstanceSecurityGroupId,
        commonTags
    } = args;

    // ========================================
    // AMI選択（ARM64/x86_64自動判定）
    // ========================================
    const isArmInstance = natInstanceType.apply(type => 
        type.startsWith("t4g") || 
        type.startsWith("m6g") || 
        type.startsWith("m7g") ||
        type.startsWith("c6g") ||
        type.startsWith("c7g")
    );
    
    // AMIは両方取得して後で選択
    const armAmi = aws.ec2.getAmi({
        mostRecent: true,
        owners: ["amazon"],
        filters: [{
            name: "name",
            values: ["al2023-ami-*-kernel-*-arm64"],
        }],
    });

    const x86Ami = aws.ec2.getAmi({
        mostRecent: true,
        owners: ["amazon"],
        filters: [{
            name: "name",
            values: ["al2023-ami-*-kernel-*-x86_64"],
        }],
    });

    const natAmiId = isArmInstance.apply(isArm => 
        isArm ? armAmi.then(ami => ami.id) : x86Ami.then(ami => ami.id)
    );

    // ========================================
    // IAMロール設定
    // ========================================
    const natInstanceRole = new aws.iam.Role("nat-instance-role", {
        assumeRolePolicy: JSON.stringify({
            Version: "2012-10-17",
            Statement: [{
                Action: "sts:AssumeRole",
                Effect: "Allow",
                Principal: {
                    Service: "ec2.amazonaws.com",
                },
            }],
        }),
        tags: {
            ...commonTags,
            Name: pulumi.interpolate`${projectName}-nat-instance-role-${environment}`,
        },
    });

    // 必要な権限を付与
    new aws.iam.RolePolicyAttachment("nat-instance-ssm-policy", {
        role: natInstanceRole.name,
        policyArn: "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
    });

    new aws.iam.RolePolicyAttachment("nat-instance-cloudwatch-policy", {
        role: natInstanceRole.name,
        policyArn: "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy",
    });

    // カスタムポリシー（メトリクス送信用）
    const natInstancePolicy = new aws.iam.RolePolicy("nat-instance-custom-policy", {
        role: natInstanceRole.name,
        policy: JSON.stringify({
            Version: "2012-10-17",
            Statement: [
                {
                    Effect: "Allow",
                    Action: [
                        "cloudwatch:PutMetricData",
                        "ec2:DescribeInstances",
                        "ec2:DescribeNetworkInterfaces",
                    ],
                    Resource: "*",
                },
            ],
        }),
    });

    // インスタンスプロファイル
    const natInstanceProfile = new aws.iam.InstanceProfile("nat-instance-profile", {
        role: natInstanceRole.name,
        tags: commonTags,
    });

    // ========================================
    // Elastic IP
    // ========================================
    const natInstanceEip = new aws.ec2.Eip("nat-instance-eip", {
        tags: {
            ...commonTags,
            Name: pulumi.interpolate`${projectName}-nat-instance-eip-${environment}`,
            Type: "nat-instance",
        },
    });

    // ========================================
    // ユーザーデータスクリプト
    // ========================================
    // NAT Instance用のユーザーデータスクリプトを外部ファイルから読み込み
    const scriptPath = path.resolve(__dirname, '..', '..', '..', 'scripts', 'aws', 'userdata', 'nat-instance-setup.sh');
    let userDataTemplate: string;
    
    try {
        // ファイルの存在確認
        if (!fs.existsSync(scriptPath)) {
            // 別の可能なパスを試す
            const alternativePath = path.resolve(process.cwd(), 'scripts', 'aws', 'userdata', 'nat-instance-setup.sh');
            if (fs.existsSync(alternativePath)) {
                userDataTemplate = fs.readFileSync(alternativePath, 'utf8');
                pulumi.log.info(`Successfully loaded NAT instance setup script from alternative path: ${alternativePath}`);
            } else {
                throw new Error(`Script not found at ${scriptPath} or ${alternativePath}`);
            }
        } else {
            userDataTemplate = fs.readFileSync(scriptPath, 'utf8');
            pulumi.log.info(`Successfully loaded NAT instance setup script from: ${scriptPath}`);
        }
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        pulumi.log.error(`Failed to read NAT instance setup script`);
        pulumi.log.error(`Attempted path: ${scriptPath}`);
        pulumi.log.error(`Current directory: ${process.cwd()}`);
        pulumi.log.error(`__dirname: ${__dirname}`);
        pulumi.log.error(`Error: ${errorMessage}`);
        
        // より詳細なヘルプメッセージ
        pulumi.log.error(`
Please ensure the NAT instance setup script exists at one of these locations:
1. ${scriptPath}
2. ${path.resolve(process.cwd(), 'scripts', 'aws', 'userdata', 'nat-instance-setup.sh')}

The script should be located in the 'scripts' directory relative to your project root.
        `);
        
        throw new Error(`Cannot read NAT instance setup script: ${errorMessage}`);
    }

    // テンプレート変数を実際の値に置換
    const userDataScript = pulumi.all([vpcCidr, projectName]).apply(([cidr, proj]) => {
        return userDataTemplate
            .replace(/\${VPC_CIDR}/g, cidr)
            .replace(/\${PROJECT_NAME}/g, proj)
            .replace(/\${ENVIRONMENT}/g, environment)
            .replace(/\${AWS_REGION}/g, aws.config.region || 'ap-northeast-1');
    });

    // ========================================
    // NAT Instance
    // ========================================
    const natInstance = new aws.ec2.Instance("nat-instance", {
        ami: natAmiId,
        instanceType: natInstanceType,
        subnetId: publicSubnetAId,
        vpcSecurityGroupIds: [natInstanceSecurityGroupId],
        iamInstanceProfile: natInstanceProfile.name,
        sourceDestCheck: false, // NATとして機能するために必要
        userData: userDataScript,
        rootBlockDevice: {
            volumeType: "gp3",
            volumeSize: 8,
            encrypted: true,
            deleteOnTermination: true,
        },
        metadataOptions: {
            httpEndpoint: "enabled",
            httpTokens: "required", // IMDSv2を強制
            httpPutResponseHopLimit: 1,
        },
        monitoring: true, // 詳細モニタリング有効化
        tags: {
            ...commonTags,
            Name: pulumi.interpolate`${projectName}-nat-instance-${environment}`,
            Role: "nat-instance",
            InstanceType: natInstanceType,
            Architecture: isArmInstance.apply(isArm => isArm ? "arm64" : "x86_64"),
        },
    });

    // Elastic IPをNAT Instanceに関連付け
    const natInstanceEipAssociation = new aws.ec2.EipAssociation("nat-instance-eip-assoc", {
        instanceId: natInstance.id,
        allocationId: natInstanceEip.id,
    });

    // ========================================
    // ルーティング設定
    // ========================================
    // プライベートサブネットAからのルート
    new aws.ec2.Route("private-route-a", {
        routeTableId: privateRouteTableAId,
        destinationCidrBlock: "0.0.0.0/0",
        instanceId: natInstance.id,
    }, {
        dependsOn: [natInstance],
    });

    // プライベートサブネットBからのルート
    new aws.ec2.Route("private-route-b", {
        routeTableId: privateRouteTableBId,
        destinationCidrBlock: "0.0.0.0/0",
        instanceId: natInstance.id,
    }, {
        dependsOn: [natInstance],
    });

    // ========================================
    // CloudWatchアラーム（モニタリング）
    // ========================================
    // インスタンス自動復旧設定
    new aws.cloudwatch.MetricAlarm("nat-instance-recovery", {
        alarmDescription: "Recover NAT instance when it fails",
        metricName: "StatusCheckFailed_System",
        namespace: "AWS/EC2",
        statistic: "Maximum",
        period: 60,
        evaluationPeriods: 2,
        threshold: 1,
        comparisonOperator: "GreaterThanThreshold",
        dimensions: {
            InstanceId: natInstance.id,
        },
        alarmActions: [
            pulumi.interpolate`arn:aws:automate:${aws.config.region}:ec2:recover`,
        ],
        tags: commonTags,
    });

    // CPU使用率アラーム
    new aws.cloudwatch.MetricAlarm("nat-instance-cpu", {
        alarmDescription: "Alert when NAT instance CPU is high",
        metricName: "CPUUtilization",
        namespace: "AWS/EC2",
        statistic: "Average",
        period: 300,
        evaluationPeriods: 2,
        threshold: 80,
        comparisonOperator: "GreaterThanThreshold",
        dimensions: {
            InstanceId: natInstance.id,
        },
        tags: commonTags,
    });

    // メモリ使用率アラーム（CloudWatchエージェント経由）
    new aws.cloudwatch.MetricAlarm("nat-instance-memory", {
        alarmDescription: "Alert when NAT instance memory is high",
        metricName: "mem_used_percent",
        namespace: "CWAgent",
        statistic: "Average",
        period: 300,
        evaluationPeriods: 2,
        threshold: 80,
        comparisonOperator: "GreaterThanThreshold",
        dimensions: {
            InstanceId: natInstance.id,
            ImageId: natAmiId,
            InstanceType: natInstanceType,
        },
        treatMissingData: "notBreaching",
        tags: commonTags,
    });

    // ネットワーク接続数アラーム（カスタムメトリクス）
    new aws.cloudwatch.MetricAlarm("nat-instance-connections", {
        alarmDescription: "Alert when NAT instance has high connection count",
        metricName: "ActiveConnections",
        namespace: "LambdaAPI/NAT",
        statistic: "Average",
        period: 300,
        evaluationPeriods: 2,
        threshold: 1000, // Lambda関数の同時実行数に応じて調整
        comparisonOperator: "GreaterThanThreshold",
        dimensions: {
            InstanceId: natInstance.id,
            Environment: environment,
        },
        treatMissingData: "notBreaching",
        tags: commonTags,
    });

    // ネットワークスループットアラーム
    new aws.cloudwatch.MetricAlarm("nat-instance-network-out", {
        alarmDescription: "Alert when NAT instance network output is high",
        metricName: "NetworkOut",
        namespace: "AWS/EC2",
        statistic: "Average",
        period: 300,
        evaluationPeriods: 2,
        threshold: 100000000, // 100MB/5min
        comparisonOperator: "GreaterThanThreshold",
        dimensions: {
            InstanceId: natInstance.id,
        },
        tags: commonTags,
    });

    // ========================================
    // SSMパラメータへの保存
    // ========================================
    const paramPrefix = pulumi.interpolate`/${projectName}/${environment}/nat`;

    // NAT Instance IDを保存
    new aws.ssm.Parameter("nat-instance-id", {
        name: pulumi.interpolate`${paramPrefix}/instance/id`,
        type: "String",
        value: natInstance.id,
        description: "NAT Instance ID",
        tags: commonTags,
    });

    // NAT Instance Public IPを保存
    new aws.ssm.Parameter("nat-instance-public-ip", {
        name: pulumi.interpolate`${paramPrefix}/instance/public-ip`,
        type: "String",
        value: natInstanceEip.publicIp,
        description: "NAT Instance Public IP",
        tags: commonTags,
    });

    // NAT Instance Private IPを保存
    new aws.ssm.Parameter("nat-instance-private-ip", {
        name: pulumi.interpolate`${paramPrefix}/instance/private-ip`,
        type: "String",
        value: natInstance.privateIp,
        description: "NAT Instance Private IP",
        tags: commonTags,
    });

    // NATタイプを保存
    new aws.ssm.Parameter("nat-type", {
        name: pulumi.interpolate`${paramPrefix}/type`,
        type: "String",
        value: "instance",
        description: "NAT type (instance)",
        tags: commonTags,
    });

    // NAT設定情報を保存
    new aws.ssm.Parameter("nat-config", {
        name: pulumi.interpolate`${paramPrefix}/config`,
        type: "String",
        value: pulumi.all([natInstanceType, projectName]).apply(([instanceType, proj]) => JSON.stringify({
            type: "instance",
            highAvailability: false,
            instanceType: instanceType,
            projectName: proj,
            environment: environment,
            createdAt: new Date().toISOString(),
        })),
        description: "NAT Instance configuration for Lambda API infrastructure",
        tags: commonTags,
    });

    // コスト最適化情報のパラメータ
    new aws.ssm.Parameter("nat-cost-info", {
        name: `/lambda-api/${environment}/nat/cost-optimization`,
        type: "String",
        value: natInstanceType.apply(instanceType => JSON.stringify({
            estimatedMonthlyCost: `$${instanceType === "t4g.nano" ? "3-5" : instanceType === "t4g.micro" ? "7-10" : "15-20"} (NAT Instance)`,
            recommendations: [
                "Monitor data transfer costs using CloudWatch",
                "Consider VPC endpoints for AWS services to reduce NAT traffic",
                "Consider NAT Gateway for production for high availability",
                "Enable detailed billing reports for accurate cost tracking",
                "Use Reserved Instances or Savings Plans for cost reduction"
            ],
            dataTransferThreshold: "< 50GB/month",
        })),
        description: "Cost optimization information for NAT Instance configuration",
        tags: commonTags,
    });

    // デプロイメント完了フラグ
    new aws.ssm.Parameter("nat-deployed", {
        name: pulumi.interpolate`${paramPrefix}/deployment/complete`,
        type: "String",
        value: "true",
        description: "NAT Instance stack deployment completion flag",
        tags: commonTags,
    });

    return {
        natInstanceId: natInstance.id,
        natInstancePublicIp: natInstanceEip.publicIp,
        natInstancePrivateIp: natInstance.privateIp,
        natResourceIds: [natInstance.id],
    };
}