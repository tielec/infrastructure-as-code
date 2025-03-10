import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as fs from "fs";
import * as path from "path";

interface JenkinsAgentInput {
    projectName: string;
    environment: string;
    vpcId: pulumi.Input<string>;
    subnetIds: pulumi.Input<string>[];
    securityGroupId: pulumi.Input<string>;
    instanceProfileArn: pulumi.Input<string>;
    keyName?: string;
    agentAmi?: string;
    maxTargetCapacity?: number;
    spotPrice?: string;
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
export function createJenkinsAgentFleet(input: JenkinsAgentInput) {
    const config = new pulumi.Config();
    const keyName = input.keyName || config.get("keyName");
    const maxTargetCapacity = input.maxTargetCapacity || config.getNumber("maxTargetCapacity") || 10;
    const spotPrice = input.spotPrice || config.get("spotPrice") || "0.10";
    
    // デフォルトはAmazon Linux 2023
    const agentAmi = input.agentAmi || config.get("agentAmi") || aws.getAmi({
        mostRecent: true,
        owners: ["amazon"],
        filters: [{
            name: "name",
            values: ["al2023-ami-*-kernel-*-x86_64"],
        }],
    }).then(ami => ami.id);

    // エージェントセットアップスクリプトの読み込み
    let userDataScript;
    try {
        userDataScript = loadScript('../scripts/jenkins/shell/agent-setup.sh');
    } catch (error) {
        console.error("Error loading agent setup script:", error);
        throw new Error(`エージェントセットアップスクリプトが見つかりません。scripts/jenkins/shell/agent-setup.shを作成してください。`);
    }

    // Launch Template
    const launchTemplate = new aws.ec2.LaunchTemplate(`${input.projectName}-agent-lt`, {
        name: `${input.projectName}-agent-lt-${input.environment}`,
        imageId: agentAmi,
        keyName: keyName,
        vpcSecurityGroupIds: [input.securityGroupId],
        instanceMarketOptions: {
            marketType: "spot",
            spotOptions: {
                maxPrice: spotPrice,
                spotInstanceType: "persistent",
                instanceInterruptionBehavior: "terminate",
            },
        },
        iamInstanceProfile: {
            arn: input.instanceProfileArn,
        },
        blockDeviceMappings: [{
            deviceName: "/dev/xvda",
            ebs: {
                volumeSize: 30,
                volumeType: "gp3",
                deleteOnTermination: true,
                encrypted: true,
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
    });

    // SpotFleet用IAMロール
    const spotFleetRole = new aws.iam.Role(`${input.projectName}-spotfleet-role`, {
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

    // スポットフリートの設定
    const fleetLaunchTemplateConfig = {
        launchTemplateSpecification: {
            launchTemplateId: launchTemplate.id,
            version: launchTemplate.latestVersion,
        },
        overrides: [
            // t3.medium on both subnets
            ...input.subnetIds.map((subnetId, index) => ({
                instanceType: "t3.medium",
                subnetId: subnetId,
            })),
            // t3.large on both subnets
            ...input.subnetIds.map((subnetId, index) => ({
                instanceType: "t3.large",
                subnetId: subnetId,
            })),
            // m5.large on both subnets
            ...input.subnetIds.map((subnetId, index) => ({
                instanceType: "m5.large",
                subnetId: subnetId,
            })),
        ],
    };

    // SNSトピック
    const spotFleetSnsTopic = new aws.sns.Topic(`${input.projectName}-spot-fleet-alerts`, {
        name: `${input.projectName}-spot-fleet-alerts-${input.environment}`,
        tags: {
            Name: `${input.projectName}-spot-fleet-alerts-${input.environment}`,
            Environment: input.environment,
        },
    });

    // SpotFleetリクエスト
    const spotFleetRequest = new aws.ec2.SpotFleetRequest(`${input.projectName}-spot-fleet`, {
        iamFleetRole: spotFleetRole.arn,
        spotPrice: spotPrice,
        targetCapacity: 0, // 初期容量は0（Jenkinsから必要に応じて起動）
        allocationStrategy: "capacityOptimized",
        instanceInterruptionBehavior: "terminate",
        replaceUnhealthyInstances: true,
        launchTemplateConfigs: [fleetLaunchTemplateConfig],
        tagSpecifications: [{
            resourceType: "spot-fleet-request",
            tags: {
                Name: `${input.projectName}-fleet-${input.environment}`,
                Environment: input.environment,
            },
        }],
    });

    return {
        launchTemplate,
        spotFleetRole,
        spotFleetRequest,
        spotFleetSnsTopic,
    };
}

// エージェント設定用のスクリプトファイルが存在しない場合に作成するヘルパー関数
export function ensureAgentScriptFile() {
    const scriptDir = path.resolve(__dirname, '../scripts/jenkins/shell');
    const scriptPath = path.resolve(scriptDir, 'agent-setup.sh');
    const templatePath = path.resolve(scriptDir, 'agent-template.sh');
    
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