import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as fs from "fs";
import * as path from "path";

interface JenkinsInstanceInput {
    projectName: string;
    environment: string;
    vpcId: pulumi.Input<string>;
    subnetId: pulumi.Input<string>;
    securityGroupId: pulumi.Input<string>;
    targetGroupArn: pulumi.Input<string>;
    efsFileSystemId?: pulumi.Input<string>;
    efsAccessPointId?: pulumi.Input<string>;
    instanceType?: string;
    keyName?: string;
    color: "blue" | "green";
    jenkinsVersion?: string;
    recoveryMode?: boolean;
}

// スクリプトファイルの読み込み関数
function loadScript(scriptPath: string): string {
    try {
        return fs.readFileSync(path.resolve(__dirname, scriptPath), 'utf8');
    } catch (error) {
        console.error(`Error loading script from ${scriptPath}:`, error);
        throw error;
    }
}

export function createJenkinsInstance(input: JenkinsInstanceInput) {
    const config = new pulumi.Config();
    const instanceType = input.instanceType || config.get("instanceType") || "t3.medium";
    const keyName = input.keyName || config.get("keyName");
    // Jenkinsバージョンは指定しない（常に最新）
const jenkinsVersion = input.jenkinsVersion || config.get("jenkinsVersion") || "latest";
    const recoveryMode = input.recoveryMode !== undefined ? input.recoveryMode : false;
    
    // スクリプトファイルの読み込み
    const disableCliGroovy = loadScript('../scripts/jenkins/groovy/disable-cli.groovy');
    const basicSettingsGroovy = loadScript('../scripts/jenkins/groovy/basic-settings.groovy');
    const recoveryModeGroovy = loadScript('../scripts/jenkins/groovy/recovery-mode.groovy');
    
    // シェルスクリプトの読み込み
    let userDataBase = loadScript('../scripts/jenkins/shell/jenkins-setup.sh');
    const startupScript = loadScript('../scripts/jenkins/shell/jenkins-startup.sh');
    
    // 変数置換
    userDataBase = userDataBase.replace(/\${color}/g, input.color);
    // バージョンが「latest」の場合は空文字に置き換え（バージョン指定なし）
const versionString = jenkinsVersion === "latest" ? "" : `-${jenkinsVersion}`;
userDataBase = userDataBase.replace(/\${jenkinsVersion}/g, versionString);
    
    // 最新のAmazon Linux 2023 AMIを取得
    const ami = pulumi.output(aws.getAmi({
        mostRecent: true,
        owners: ["amazon"],
        filters: [{
            name: "name",
            values: ["al2023-ami-*-kernel-*-x86_64"],
        }],
    }));

    // IAMロール作成（Jenkins用）
    const jenkinsRole = new aws.iam.Role(`${input.projectName}-jenkins-role-${input.color}`, {
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
            Name: `${input.projectName}-jenkins-role-${input.color}-${input.environment}`,
            Environment: input.environment,
            Color: input.color,
        },
    });

    // マネージドポリシーのアタッチ
    const rolePolicyAttachments = [
        new aws.iam.RolePolicyAttachment(`${input.projectName}-jenkins-ssm-policy-${input.color}`, {
            role: jenkinsRole.name,
            policyArn: "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
        }),
        new aws.iam.RolePolicyAttachment(`${input.projectName}-jenkins-efs-policy-${input.color}`, {
            role: jenkinsRole.name,
            policyArn: "arn:aws:iam::aws:policy/AmazonElasticFileSystemClientReadWriteAccess",
        }),
    ];

    // Jenkins用インスタンスプロファイル
    const jenkinsInstanceProfile = new aws.iam.InstanceProfile(`${input.projectName}-jenkins-profile-${input.color}`, {
        role: jenkinsRole.name,
        tags: {
            Environment: input.environment,
            Color: input.color,
        },
    });

    // EFSマウント部分（条件付き）
    let efsMount = '';
    if (input.efsFileSystemId) {
        efsMount = loadScript('../scripts/jenkins/shell/efs-mount.sh');
        efsMount = efsMount.replace(/\${efsFileSystemId}/g, input.efsFileSystemId.toString());
    }

    // リカバリーモードまたは通常モードの設定
    let configModeScript;
    if (recoveryMode) {
        configModeScript = loadScript('../scripts/jenkins/shell/recovery-mode-setup.sh');
        configModeScript = configModeScript.replace(/\${recoveryModeGroovy}/g, recoveryModeGroovy);
    } else {
        configModeScript = loadScript('../scripts/jenkins/shell/normal-mode-setup.sh');
        configModeScript = configModeScript
            .replace(/\${disableCliGroovy}/g, disableCliGroovy)
            .replace(/\${basicSettingsGroovy}/g, basicSettingsGroovy);
    }
    
    // 最終的なUserDataの組み立て
    const userData = pulumi.interpolate`${userDataBase}${efsMount}${configModeScript}${startupScript}`;

    // EC2インスタンスの作成
    const jenkinsInstance = new aws.ec2.Instance(`${input.projectName}-jenkins-${input.color}`, {
        ami: ami.id,
        instanceType: instanceType,
        subnetId: input.subnetId,
        vpcSecurityGroupIds: [input.securityGroupId],
        keyName: keyName,
        iamInstanceProfile: jenkinsInstanceProfile.name,
        userData: userData,
        rootBlockDevice: {
            volumeSize: 50,
            volumeType: "gp3",
            deleteOnTermination: true,
            encrypted: true,
        },
        tags: {
            Name: `${input.projectName}-jenkins-${input.color}-${input.environment}`,
            Environment: input.environment,
            Color: input.color,
            Role: "jenkins-master",
        },
    });

    // ターゲットグループへの登録
    const targetGroupAttachment = new aws.lb.TargetGroupAttachment(`${input.projectName}-jenkins-tg-attachment-${input.color}`, {
        targetGroupArn: input.targetGroupArn,
        targetId: jenkinsInstance.id,
        port: 8080,
    });

    return {
        jenkinsInstance,
        jenkinsRole,
        instanceProfile: jenkinsInstanceProfile,
        targetGroupAttachment,
    };
}

export function createJenkinsEfs(projectName: string, environment: string, vpcId: pulumi.Input<string>, securityGroupId: pulumi.Input<string>, subnetIds: pulumi.Input<string>[]) {
    // EFSセキュリティグループ
    const efsSecurityGroup = new aws.ec2.SecurityGroup(`${projectName}-efs-sg`, {
        vpcId: vpcId,
        description: "Security group for Jenkins EFS",
        ingress: [
            // NFS（2049ポート）を許可
            {
                protocol: "tcp",
                fromPort: 2049,
                toPort: 2049,
                securityGroups: [securityGroupId],
                description: "NFS access from Jenkins instances",
            },
        ],
        egress: [{
            protocol: "-1",
            fromPort: 0,
            toPort: 0,
            cidrBlocks: ["0.0.0.0/0"],
            description: "Allow all outbound traffic",
        }],
        tags: {
            Name: `${projectName}-efs-sg-${environment}`,
            Environment: environment,
        },
    });

    // EFSファイルシステム
    const efsFileSystem = new aws.efs.FileSystem(`${projectName}-efs`, {
        encrypted: true,
        performanceMode: "generalPurpose",
        throughputMode: "bursting",
        tags: {
            Name: `${projectName}-jenkins-efs-${environment}`,
            Environment: environment,
            ManagedBy: "pulumi",
        },
        lifecyclePolicy: {
            transitionToIa: "AFTER_30_DAYS",
        },
    });

    // サブネットごとにマウントターゲットを作成
    const mountTargets = subnetIds.map((subnetId, index) => {
        return new aws.efs.MountTarget(`${projectName}-efs-mt-${index}`, {
            fileSystemId: efsFileSystem.id,
            subnetId: subnetId,
            securityGroups: [efsSecurityGroup.id],
        });
    });

    // EFSアクセスポイント
    const jenkinsAccessPoint = new aws.efs.AccessPoint(`${projectName}-jenkins-ap`, {
        fileSystemId: efsFileSystem.id,
        posixUser: {
            gid: 994,  // Jenkinsのgid
            uid: 994,  // Jenkinsのuid
        },
        rootDirectory: {
            path: "/jenkins-home",
            creationInfo: {
                ownerGid: 994,
                ownerUid: 994,
                permissions: "755",
            },
        },
        tags: {
            Name: `${projectName}-jenkins-ap-${environment}`,
            Environment: environment,
        },
    });

    return {
        efsFileSystem,
        efsSecurityGroup,
        mountTargets,
        jenkinsAccessPoint,
    };
}
