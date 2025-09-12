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
    /** 自動停止スケジュール情報（dev環境のみ） */
    autoStopSchedule?: pulumi.Output<string>;
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
    // 動的Public IP設定
    // ========================================
    // EIPは使用せず、動的Public IPを使用してコスト削減
    // NAT Instanceはパブリックサブネットに配置され、
    // associatePublicIpAddress: true で動的IPが割り当てられる

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
        associatePublicIpAddress: true, // 動的Public IPを自動割り当て
        vpcSecurityGroupIds: [natInstanceSecurityGroupId],
        iamInstanceProfile: natInstanceProfile.name,
        sourceDestCheck: false, // NATとして機能するために必要
        userData: userDataScript,
        rootBlockDevice: {
            volumeType: "gp3",
            volumeSize: 30, // Amazon Linux 2023の最小要件
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

    // EIP関連付けは削除（動的Public IPを使用）

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

    // NAT Instance Public IPは動的IPのため保存しない
    // 毎回のインスタンス起動時に新しいIPが割り当てられる

    // NAT Instance Private IPは動的に変化する可能性があるためSSMに保存しない

    // NATタイプを保存
    new aws.ssm.Parameter("nat-type", {
        name: pulumi.interpolate`${paramPrefix}/type`,
        type: "String",
        value: "instance",
        description: "NAT type (instance)",
        tags: commonTags,
    });

    // NAT設定情報はPulumiの出力で確認可能なためSSMに保存しない

    // コスト最適化情報はドキュメントで管理するためSSMに保存しない

    // ========================================
    // 自動停止設定（dev環境のみ）
    // ========================================
    let autoStopSchedule: pulumi.Output<string> | undefined;
    
    if (environment === 'dev') {
        // Maintenance Window用のIAMロール
        const maintenanceWindowRole = new aws.iam.Role("nat-maintenance-window-role", {
            assumeRolePolicy: JSON.stringify({
                Version: "2012-10-17",
                Statement: [{
                    Effect: "Allow",
                    Principal: {
                        Service: "ssm.amazonaws.com",
                    },
                    Action: "sts:AssumeRole",
                }],
            }),
            tags: {
                ...commonTags,
                Name: pulumi.interpolate`${projectName}-nat-maintenance-role-${environment}`,
            },
        });

        // SSMメンテナンスウィンドウロールポリシーを付与
        new aws.iam.RolePolicyAttachment("nat-maintenance-window-policy", {
            role: maintenanceWindowRole.name,
            policyArn: "arn:aws:iam::aws:policy/service-role/AmazonSSMMaintenanceWindowRole",
        });

        // EC2停止用のカスタムポリシー
        new aws.iam.RolePolicy("nat-maintenance-ec2-policy", {
            role: maintenanceWindowRole.name,
            policy: JSON.stringify({
                Version: "2012-10-17",
                Statement: [{
                    Effect: "Allow",
                    Action: [
                        "ec2:StopInstances",
                        "ec2:DescribeInstances",
                        "ec2:DescribeInstanceStatus",
                    ],
                    Resource: "*",
                }],
            }),
        });

        // SSM Maintenance Window (日本時間12時に停止)
        const stopInstanceMaintenanceWindow = new aws.ssm.MaintenanceWindow("nat-stop-window", {
            name: pulumi.interpolate`${projectName}-nat-stop-${environment}`,
            description: "Stop NAT instance daily at 12:00 PM JST (dev environment)",
            schedule: "cron(0 15 ? * * *)", // 毎日UTC 15:00（日本時間24:00）
            duration: 1, // 1時間のウィンドウ
            cutoff: 0, // ウィンドウ終了前に新しいタスクを開始しない
            allowUnassociatedTargets: false,
            tags: {
                ...commonTags,
                Name: pulumi.interpolate`${projectName}-nat-stop-window-${environment}`,
            },
        });

        // Maintenance Windowのターゲット（停止対象のインスタンス）
        const stopInstanceTarget = new aws.ssm.MaintenanceWindowTarget("nat-stop-target", {
            name: pulumi.interpolate`${projectName}-nat-stop-target-${environment}`,
            description: "Target for stopping NAT instance",
            windowId: stopInstanceMaintenanceWindow.id,
            resourceType: "INSTANCE",
            targets: [{
                key: "InstanceIds",
                values: [natInstance.id],
            }],
        });

        // Maintenance Windowのタスク（EC2停止コマンド）
        new aws.ssm.MaintenanceWindowTask("nat-stop-task", {
            name: pulumi.interpolate`${projectName}-nat-stop-task-${environment}`,
            description: "Stop NAT EC2 instance",
            windowId: stopInstanceMaintenanceWindow.id,
            serviceRoleArn: maintenanceWindowRole.arn,
            priority: 1,
            maxConcurrency: "1", // 同時実行数（1つのインスタンスのみ）
            maxErrors: "0", // エラー許容数（0 = エラーを許容しない）
            taskType: "AUTOMATION",
            taskArn: "AWS-StopEC2Instance", // AWS提供の自動化ドキュメント
            targets: [{
                key: "WindowTargetIds",
                values: [stopInstanceTarget.id],
            }],
            taskInvocationParameters: {
                automationParameters: {
                    parameters: [{
                        name: "InstanceId",
                        values: [natInstance.id],
                    }],
                },
            },
        });

        // スケジュール情報を設定
        autoStopSchedule = pulumi.output("Instance will be stopped daily at 12:00 PM JST (03:00 UTC) via SSM Maintenance Window");

        // SSMパラメータにスケジュール情報を保存
        new aws.ssm.Parameter("nat-auto-stop-schedule", {
            name: pulumi.interpolate`${paramPrefix}/auto-stop/schedule`,
            type: "String",
            value: "Daily at 12:00 PM JST",
            description: "NAT Instance auto-stop schedule (dev environment only)",
            tags: commonTags,
        });

        pulumi.log.info(`NAT Instance auto-stop enabled for dev environment: Daily at 12:00 PM JST`);
    }

    return {
        natInstanceId: natInstance.id,
        natInstancePublicIp: natInstance.publicIp || pulumi.output("Dynamic IP - changes on each deployment"),
        natInstancePrivateIp: natInstance.privateIp,
        natResourceIds: [natInstance.id],
        autoStopSchedule: autoStopSchedule,
    };
}
