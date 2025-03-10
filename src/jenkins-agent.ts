import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as fs from "fs";
import * as path from "path";
import { dependsOn } from "./dependency-utils";

interface JenkinsAgentInput {
    projectName: string;
    environment: string;
    vpcId: pulumi.Input<string>;
    subnetIds: pulumi.Input<string>[];
    securityGroupId: pulumi.Input<string>;
    keyName?: string;
    agentAmi?: string;
    maxTargetCapacity?: number;
    spotPrice?: string;
    // 既存のIAMロールを渡すオプションを残しておく（オプショナル）
    agentRoleArn?: pulumi.Input<string>;
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

// SpotFleetでJenkinsエージェントを作成する関数
export function createJenkinsAgentFleet(input: JenkinsAgentInput, dependencies?: pulumi.Resource[]) {
    const config = new pulumi.Config();
    const keyName = input.keyName || config.get("keyName");
    const maxTargetCapacity = input.maxTargetCapacity || config.getNumber("maxTargetCapacity") || 10;
    const spotPrice = input.spotPrice || config.get("spotPrice") || "0.10";
    
    // デフォルトはAmazon Linux 2023 - 警告修正のためにec2.getAmiを使用
    const agentAmi = input.agentAmi || config.get("agentAmi") || aws.ec2.getAmi({
        mostRecent: true,
        owners: ["amazon"],
        filters: [{
            name: "name",
            values: ["al2023-ami-*-kernel-*-x86_64"],
        }],
    }).then(ami => ami.id);

    // エージェント用のIAMロールとインスタンスプロファイルを作成
    // 既存のロールが指定されていない場合のみ作成
    let agentRole: aws.iam.Role | undefined;
    let agentPolicyAttachments: aws.iam.RolePolicyAttachment[] = [];
    let agentProfile: aws.iam.InstanceProfile | undefined;
    let instanceProfileArn: pulumi.Output<string>;

    if (input.agentRoleArn) {
        // 既存のロールを使用する場合
        instanceProfileArn = pulumi.output(input.agentRoleArn);
    } else {
        // 新規にロールとプロファイルを作成
        agentRole = new aws.iam.Role(`${input.projectName}-agent-role`, {
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
                Name: `${input.projectName}-agent-role-${input.environment}`,
                Environment: input.environment,
            },
        });

        // 依存関係を別途設定
        if (dependencies && dependencies.length > 0 && agentRole) {
            agentRole = dependsOn(agentRole, dependencies);
        }

        // 必要なポリシーをアタッチ
        const ssmPolicy = new aws.iam.RolePolicyAttachment(`${input.projectName}-agent-ssm-policy`, {
            role: agentRole.name,
            policyArn: "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
        });
        
        const efsPolicy = new aws.iam.RolePolicyAttachment(`${input.projectName}-agent-efs-policy`, {
            role: agentRole.name,
            policyArn: "arn:aws:iam::aws:policy/AmazonElasticFileSystemClientReadWriteAccess",
        });

        // 依存関係を設定
        if (agentRole) {
            agentPolicyAttachments = [
                dependsOn(ssmPolicy, [agentRole]),
                dependsOn(efsPolicy, [agentRole])
            ];
        }

        // インスタンスプロファイル
        agentProfile = new aws.iam.InstanceProfile(`${input.projectName}-agent-profile`, {
            role: agentRole.name,
            tags: {
                Name: `${input.projectName}-agent-profile-${input.environment}`,
                Environment: input.environment,
            },
        });
        
        // 依存関係を設定
        if (agentProfile && agentPolicyAttachments.length > 0 && agentRole) {
            agentProfile = dependsOn(agentProfile, [...agentPolicyAttachments, agentRole]);
        }

        instanceProfileArn = agentProfile.arn;
    }

    // エージェントセットアップスクリプトの読み込み
    let userDataScript;
    try {
        userDataScript = loadScript('../scripts/jenkins/shell/agent-setup.sh');
    } catch (error) {
        console.error("Error loading agent setup script:", error);
        throw new Error(`エージェントセットアップスクリプトが見つかりません。scripts/jenkins/shell/agent-setup.shを作成してください。`);
    }

    // Launch Template
    const launchTemplateArgs: aws.ec2.LaunchTemplateArgs = {
        name: `${input.projectName}-agent-lt-${input.environment}`,
        imageId: agentAmi,
        keyName: keyName,
        vpcSecurityGroupIds: [input.securityGroupId],
        // 型アサーションを使用
        instanceMarketOptions: {
            marketType: "spot",
            spotOptions: {
                maxPrice: spotPrice,
                spotInstanceType: "persistent",
                instanceInterruptionBehavior: "terminate", // APIには必要だが型定義にない
            } as any, // 型アサーション
        },
        iamInstanceProfile: {
            arn: instanceProfileArn,
        },
        blockDeviceMappings: [{
            deviceName: "/dev/xvda",
            ebs: {
                volumeSize: 30,
                volumeType: "gp3",
                deleteOnTermination: "true", // 文字列に変更
                encrypted: "true",           // 文字列に変更
            },
        }],
        metadataOptions: {
            httpEndpoint: "enabled",
            httpTokens: "required",
            httpPutResponseHopLimit: 2,
        },
        tagSpecifications: [{
            resourceType: "instance",
            tags: {
                Name: `${input.projectName}-agent-${input.environment}`,
                Environment: input.environment,
            },
        }],
        userData: pulumi.output(Buffer.from(userDataScript).toString("base64")),
    };

    // Launch Templateの作成
    let launchTemplate = new aws.ec2.LaunchTemplate(
        `${input.projectName}-agent-lt`, 
        launchTemplateArgs
    );

    // 依存関係を設定
    const fullDependencies = [...(dependencies || [])];
    if (agentProfile) {
        fullDependencies.push(agentProfile);
    }
    if (fullDependencies.length > 0) {
        launchTemplate = dependsOn(launchTemplate, fullDependencies);
    }

    // SpotFleet用IAMロール
    let spotFleetRole = new aws.iam.Role(`${input.projectName}-spotfleet-role`, {
        name: `${input.projectName}-spotfleet-role-${input.environment}`,
        assumeRolePolicy: JSON.stringify({
            Version: "2012-10-17",
            Statement: [{
                Effect: "Allow",
                Principal: {
                    Service: "spotfleet.amazonaws.com",
                },
                Action: "sts:AssumeRole",
            }],
        }),
        managedPolicyArns: [
            "arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetTaggingRole",
        ],
    });

    // 依存関係を設定
    if (fullDependencies.length > 0) {
        spotFleetRole = dependsOn(spotFleetRole, fullDependencies);
    }

    // SpotFleetリクエスト設定
    try {
        // SpotFleetリクエスト - launchSpecifications を使用
        const spotFleetRequestArgs: aws.ec2.SpotFleetRequestArgs = {
            iamFleetRole: spotFleetRole.arn,
            spotPrice: spotPrice,
            targetCapacity: 0, // 初期容量は0（Jenkinsから必要に応じて起動）
            allocationStrategy: "capacityOptimized",
            replaceUnhealthyInstances: true,
            launchSpecifications: input.subnetIds.map(subnetId => ({
                instanceType: "t3.medium",
                ami: agentAmi,
                iamInstanceProfile: instanceProfileArn,
                keyName: keyName,
                vpcSecurityGroupIds: [input.securityGroupId],
                subnetId: subnetId,
                tags: {
                    Name: `${input.projectName}-agent-${input.environment}`,
                    Environment: input.environment,
                },
            })),
            tags: {
                Name: `${input.projectName}-fleet-${input.environment}`,
                Environment: input.environment,
            },
        };

        // SpotFleetリクエストの作成
        let spotFleetRequest = new aws.ec2.SpotFleetRequest(
            `${input.projectName}-spot-fleet`, 
            spotFleetRequestArgs
        );

        // 依存関係を設定
        spotFleetRequest = dependsOn(spotFleetRequest, [...fullDependencies, launchTemplate, spotFleetRole]);

        // SNSトピック
        let spotFleetSnsTopic = new aws.sns.Topic(`${input.projectName}-spot-fleet-alerts`, {
            name: `${input.projectName}-spot-fleet-alerts-${input.environment}`,
            tags: {
                Name: `${input.projectName}-spot-fleet-alerts-${input.environment}`,
                Environment: input.environment,
            },
        });

        // 依存関係を設定
        if (fullDependencies.length > 0) {
            spotFleetSnsTopic = dependsOn(spotFleetSnsTopic, fullDependencies);
        }

        return {
            agentRole,
            agentProfile,
            launchTemplate,
            spotFleetRole,
            spotFleetRequest,
            spotFleetSnsTopic,
        };
    } catch (error) {
        console.error("Error creating SpotFleetRequest:", error);
        // エラーが発生してもLaunchTemplateとロールは返す
        return {
            agentRole,
            agentProfile,
            launchTemplate,
            spotFleetRole,
            spotFleetSnsTopic: null,
        };
    }
}

// エージェント設定用のスクリプトファイルが存在しない場合に作成するヘルパー関数
export function ensureAgentScriptFile() {
    const scriptDir = path.resolve(__dirname, '../scripts/jenkins/shell');
    const scriptPath = path.resolve(scriptDir, 'agent-setup.sh');
    const templatePath = path.resolve(scriptDir, 'agent-setup-template.sh');
    
    // スクリプトファイルがすでに存在する場合はなにもしない
    if (fs.existsSync(scriptPath)) {
        console.log("Agent setup script already exists.");
        return;
    }
    
    // ディレクトリが存在するか確認し、なければ作成
    if (!fs.existsSync(scriptDir)) {
        fs.mkdirSync(scriptDir, { recursive: true });
        console.log(`Created directory: ${scriptDir}`);
    }
    
    try {
        // テンプレートファイルが存在するか確認
        if (fs.existsSync(templatePath)) {
            // テンプレートファイルが存在する場合はそれをコピー
            fs.copyFileSync(templatePath, scriptPath);
            console.log(`Created agent setup script from template: ${scriptPath}`);
        } else {
            // テンプレートファイルが存在しない場合はエラー
            throw new Error(`テンプレートファイル ${templatePath} が見つかりません。先にテンプレートファイルを作成してください。`);
        }
        
        // 実行権限を付与
        fs.chmodSync(scriptPath, 0o755);
        console.log("Please review and customize the script as needed.");
    } catch (error) {
        console.error("Error creating agent setup script:", error);
        throw error;
    }
}
