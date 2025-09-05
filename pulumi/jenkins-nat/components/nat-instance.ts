/**
 * components/nat-instance.ts
 * 
 * NAT Instance（通常モード）用のコンポーネント
 * Amazon Linux 2023 + nftablesを使用したNATインスタンス構成
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as fs from "fs";
import * as path from "path";

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
    /** キーペア名（"none"の場合は使用しない） */
    keyName: pulumi.Output<string>;
    /** パブリックサブネットA ID */
    publicSubnetAId: pulumi.Output<string>;
    /** プライベートルートテーブルA ID */
    privateRouteTableAId: pulumi.Output<string>;
    /** プライベートルートテーブルB ID */
    privateRouteTableBId: pulumi.Output<string>;
    /** NAT Instance用セキュリティグループID */
    natInstanceSecurityGroupId: pulumi.Output<string>;
    /** SSMパラメータのプレフィックス */
    ssmPrefix: string;
    /** 共通タグ */
    commonTags: Record<string, string>;
}

/**
 * NAT Instance構成の出力
 */
export interface NatInstanceOutputs {
    /** NAT Instance ID */
    natInstanceId: pulumi.Output<string>;
    /** NAT Instance Private IP */
    natInstancePrivateIp: pulumi.Output<string>;
    /** NAT Instance Type */
    natInstanceType: pulumi.Output<string>;
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
        keyName,
        publicSubnetAId,
        privateRouteTableAId,
        privateRouteTableBId,
        natInstanceSecurityGroupId,
        ssmPrefix,
        commonTags
    } = args;

    pulumi.log.info("Creating NAT Instance resources for normal mode (Amazon Linux 2023 with nftables)");

    // ========================================
    // AMI選択（ARM64版とx86_64版を自動選択）
    // ========================================
    const amiArch = natInstanceType.apply(instanceType => {
        const isArm = instanceType.startsWith("t4g") || 
                     instanceType.startsWith("m6g") || 
                     instanceType.startsWith("m7g") ||
                     instanceType.startsWith("c6g") ||
                     instanceType.startsWith("c7g");
        return isArm ? "arm64" : "x86_64";
    });
    
    const natAmi = amiArch.apply(arch => 
        aws.ec2.getAmi({
            mostRecent: true,
            owners: ["amazon"],
            filters: [{
                name: "name",
                values: [`al2023-ami-*-kernel-*-${arch}`],
            }],
        })
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

    // インスタンスプロファイル
    const natInstanceProfile = new aws.iam.InstanceProfile("nat-instance-profile", {
        role: natInstanceRole.name,
        tags: commonTags,
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
        pulumi.log.error(`Error: ${errorMessage}`);
        
        throw new Error(`Cannot read NAT instance setup script: ${errorMessage}`);
    }

    // テンプレート変数を実際の値に置換
    const userDataScript = pulumi.all([vpcCidr, projectName]).apply(([cidr, proj]) => {
        return userDataTemplate
            .replace(/\$\{VPC_CIDR\}/g, cidr)
            .replace(/\$\{PROJECT_NAME\}/g, proj)
            .replace(/\$\{ENVIRONMENT\}/g, environment)
            .replace(/\$\{AWS_REGION\}/g, aws.config.region || 'ap-northeast-1')
            .replace(/\$\{ENABLE_MONITORING\}/g, 'false')  // Jenkins環境ではモニタリングを無効化
            .replace(/\$\{ENABLE_SSM\}/g, 'true');  // SSMエージェントは有効化
    });

    // ========================================
    // EC2インスタンス
    // ========================================
    const natInstance = new aws.ec2.Instance("nat-instance", {
        ami: pulumi.output(natAmi).apply(ami => ami.id),
        instanceType: natInstanceType,
        // keyNameは"none"の場合は設定しない（空文字として扱う）
        keyName: keyName.apply(k => k === "none" ? "" : k),
        subnetId: publicSubnetAId,
        vpcSecurityGroupIds: [natInstanceSecurityGroupId],
        iamInstanceProfile: natInstanceProfile.name,
        sourceDestCheck: false, // NATとして機能するために必要
        associatePublicIpAddress: true, // 動的パブリックIPを自動割り当て
        userData: userDataScript,
        tags: {
            ...commonTags,
            Name: pulumi.interpolate`${projectName}-nat-instance-${environment}`,
            Role: "nat-instance",
            InstanceType: pulumi.interpolate`${natInstanceType}`,
        },
    });

    // ========================================
    // ルート設定
    // ========================================
    // 両方のプライベートサブネットからのルート（単一NATインスタンス経由）
    new aws.ec2.Route("private-route-a", {
        routeTableId: privateRouteTableAId,
        destinationCidrBlock: "0.0.0.0/0",
        instanceId: natInstance.id,
    }, {
        dependsOn: [natInstance],
    });

    new aws.ec2.Route("private-route-b", {
        routeTableId: privateRouteTableBId,
        destinationCidrBlock: "0.0.0.0/0",
        instanceId: natInstance.id,
    }, {
        dependsOn: [natInstance],
    });

    // ========================================
    // 監視とアラーム
    // ========================================
    // NATインスタンスの自動復旧設定
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

    // ========================================
    // SSMパラメータに保存
    // ========================================
    // NAT Instance IDをSSMに保存
    new aws.ssm.Parameter("nat-instance-id", {
        name: `${ssmPrefix}/nat/instance-id`,
        type: "String",
        value: natInstance.id,
        overwrite: true,
        tags: {
            ...commonTags,
            Component: "nat",
        },
    });

    // NAT Instance Private IPをSSMに保存
    new aws.ssm.Parameter("nat-instance-private-ip", {
        name: `${ssmPrefix}/nat/instance-private-ip`,
        type: "String",
        value: natInstance.privateIp,
        overwrite: true,
        tags: {
            ...commonTags,
            Component: "nat",
        },
    });

    // ========================================
    // デバッグログ出力
    // ========================================
    natInstanceType.apply(type => {
        pulumi.log.info(`NAT Instance Type: ${type}`);
    });
    natInstance.publicIp.apply(ip => {
        pulumi.log.info(`NAT Instance Public IP (Dynamic): ${ip || 'Pending'}`);
    });
    natInstance.privateIp.apply(ip => {
        pulumi.log.info(`NAT Instance Private IP: ${ip}`);
    });

    return {
        natInstanceId: natInstance.id,
        natInstancePrivateIp: natInstance.privateIp,
        natInstanceType: natInstanceType,
        natResourceIds: [natInstance.id],
    };
}