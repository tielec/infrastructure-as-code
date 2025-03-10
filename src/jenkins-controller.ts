import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as fs from "fs";
import * as path from "path";
import { dependsOn } from "./dependency-utils";

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

// 依存関係を考慮してJenkinsインスタンスを作成する
export function createJenkinsInstance(input: JenkinsInstanceInput, dependencies?: pulumi.Resource[]) {
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
    
    // バージョンが「latest」の場合は空文字に置き換え（バージョン指定なし）
    const versionString = jenkinsVersion === "latest" ? "" : `-${jenkinsVersion}`;
    userDataBase = userDataBase.replace(/\${jenkinsVersion}/g, versionString);
    userDataBase = userDataBase.replace(/\${color}/g, input.color);
    
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

    // EFSマウント部分（条件付き）
    let efsMount: pulumi.Output<string> = pulumi.output('');
    if (input.efsFileSystemId) {
        // スクリプトの読み込み
        const efsMountTemplate = loadScript('../scripts/jenkins/shell/efs-mount.sh');
        
        // リージョンを取得
        const regionPromise = aws.getRegion();
        
        // 文字列置換を使用して変数を置換する
        efsMount = pulumi.all([input.efsFileSystemId, regionPromise.then(r => r.name)]).apply(
            ([efsId, regionName]) => {
                return efsMountTemplate
                    .replace(/\${efsFileSystemId}/g, efsId)
                    .replace(/\${AWS_REGION}/g, regionName);
            }
        );
    }

    // 最終的なUserDataの組み立て - 文字列結合を使用
    const userData = pulumi.all([userDataBase, efsMount, configModeScript, startupScript])
        .apply(([base, efs, config, startup]) => {
            return `${base}\n${efs}\n${config}\n${startup}`;
        });

    // 最新のAmazon Linux 2023 AMIを取得
    const ami = pulumi.output(aws.ec2.getAmi({
        mostRecent: true,
        owners: ["amazon"],
        filters: [{
            name: "name",
            values: ["al2023-ami-*-kernel-*-x86_64"],
        }],
    }));

    // IAMロール作成（Jenkins用）
    let jenkinsRole = new aws.iam.Role(`${input.projectName}-jenkins-role-${input.color}`, {
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

    // 依存関係を設定
    if (dependencies && dependencies.length > 0) {
        jenkinsRole = dependsOn(jenkinsRole, dependencies);
    }

    // マネージドポリシーのアタッチ
    const ssmPolicy = new aws.iam.RolePolicyAttachment(`${input.projectName}-jenkins-ssm-policy-${input.color}`, {
        role: jenkinsRole.name,
        policyArn: "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
    });
    
    const efsPolicy = new aws.iam.RolePolicyAttachment(`${input.projectName}-jenkins-efs-policy-${input.color}`, {
        role: jenkinsRole.name,
        policyArn: "arn:aws:iam::aws:policy/AmazonElasticFileSystemClientReadWriteAccess",
    });

    // 依存関係を設定
    const rolePolicyAttachments = [
        dependsOn(ssmPolicy, [jenkinsRole]),
        dependsOn(efsPolicy, [jenkinsRole]),
    ];

    // Jenkins用インスタンスプロファイル
    let jenkinsInstanceProfile = new aws.iam.InstanceProfile(`${input.projectName}-jenkins-profile-${input.color}`, {
        role: jenkinsRole.name,
        tags: {
            Environment: input.environment,
            Color: input.color,
        },
    });

    // 依存関係を設定
    jenkinsInstanceProfile = dependsOn(jenkinsInstanceProfile, [jenkinsRole, ...rolePolicyAttachments]);

    // EC2インスタンスの作成
    let jenkinsInstance = new aws.ec2.Instance(`${input.projectName}-jenkins-${input.color}`, {
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

    // 依存関係を設定
    if (dependencies && dependencies.length > 0) {
        jenkinsInstance = dependsOn(jenkinsInstance, [...dependencies, jenkinsInstanceProfile]);
    } else {
        jenkinsInstance = dependsOn(jenkinsInstance, [jenkinsInstanceProfile]);
    }

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

// EFSファイルシステムを作成する関数
export function createJenkinsEfs(
    projectName: string, 
    environment: string, 
    vpcId: pulumi.Input<string>, 
    securityGroupId: pulumi.Input<string>, 
    subnetIds: pulumi.Input<string>[],
    dependencies?: pulumi.Resource[]
) {
    // EFSセキュリティグループ - 既に定義済みのため、ここでは使用するだけ
    const efsSecurityGroupId = securityGroupId;

    // EFSファイルシステム
    let efsFileSystem = new aws.efs.FileSystem(`${projectName}-efs`, {
        encrypted: true,
        performanceMode: "generalPurpose",
        throughputMode: "bursting",
        tags: {
            Name: `${projectName}-jenkins-efs-${environment}`,
            Environment: environment,
            ManagedBy: "pulumi",
        },
        lifecyclePolicies: [{
            transitionToIa: "AFTER_30_DAYS",
        }],
    });

    // 依存関係を設定
    if (dependencies && dependencies.length > 0) {
        efsFileSystem = dependsOn(efsFileSystem, dependencies);
    }

    // サブネットごとにマウントターゲットを作成
    const mountTargets = subnetIds.map((subnetId, index) => {
        const mountTarget = new aws.efs.MountTarget(`${projectName}-efs-mt-${index}`, {
            fileSystemId: efsFileSystem.id,
            subnetId: subnetId,
            securityGroups: [efsSecurityGroupId],
        });
        
        // 依存関係を設定
        if (dependencies && dependencies.length > 0) {
            return dependsOn(mountTarget, [efsFileSystem, ...dependencies]);
        }
        return dependsOn(mountTarget, [efsFileSystem]);
    });

    // EFSアクセスポイント
    let jenkinsAccessPoint = new aws.efs.AccessPoint(`${projectName}-jenkins-ap`, {
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
    
    // 依存関係を設定
    jenkinsAccessPoint = dependsOn(jenkinsAccessPoint, [efsFileSystem]);

    return {
        efsFileSystem,
        mountTargets,
        jenkinsAccessPoint,
    };
}