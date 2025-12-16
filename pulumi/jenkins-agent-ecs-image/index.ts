/**
 * pulumi/jenkins-agent-ecs-image/index.ts
 *
 * Jenkins Agent向けのECSコンテナイメージをEC2 Image Builderで作成するPulumiスクリプト
 * 既存のDockerfile (docker/jenkins-agent-ecs/Dockerfile) をImage Builder向けに変換
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as fs from "fs";
import * as path from "path";

// 環境名とSSMパスのベース
const environment = pulumi.getStack();
const ssmPrefix = `/jenkins-infra/${environment}`;

// SSMパラメータから設定を取得
const projectNameParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/config/project-name`,
});
const publicSubnetAIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/public-subnet-a-id`,
});
const jenkinsAgentSecurityGroupIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/security/jenkins-agent-sg-id`,
});
const ecrRepositoryUrlParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/agent/ecr-repository-url`,
});

// 取得値をOutputに変換
const projectName = pulumi.output(projectNameParam).apply(p => p.value);
const publicSubnetAId = pulumi.output(publicSubnetAIdParam).apply(p => p.value);
const jenkinsAgentSecurityGroupId = pulumi.output(jenkinsAgentSecurityGroupIdParam).apply(p => p.value);
const ecrRepositoryUrl = pulumi.output(ecrRepositoryUrlParam).apply(p => p.value);

// ECRリポジトリ名とARNを取得
const ecrRepositoryName = ecrRepositoryUrl.apply(url => {
    const parts = url.split("/");
    return parts[parts.length - 1];
});
const ecrRepository = ecrRepositoryName.apply(name => aws.ecr.getRepository({ name }));
const ecrRepositoryArn = ecrRepository.apply(repo => repo.repositoryArn);

// バージョン管理（1.YYMMDD.秒数形式）
const now = new Date();
const year = String(now.getFullYear()).slice(-2);
const month = String(now.getMonth() + 1).padStart(2, "0");
const day = String(now.getDate()).padStart(2, "0");
const dateStr = `${year}${month}${day}`;
const secondsOfDay = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
const config = new pulumi.Config();
const componentVersion = config.get("componentVersion") || `1.${dateStr}.${secondsOfDay}`;
const recipeVersion = config.get("recipeVersion") || `1.${dateStr}.${secondsOfDay}`;

console.log(`[INFO] Component Version: ${componentVersion}`);
console.log(`[INFO] Recipe Version: ${recipeVersion}`);

// コンポーネント定義YAMLを読み込み
const componentYaml = fs.readFileSync(path.join(__dirname, "component.yml"), "utf8");

// Image Builder用IAMロール
const imageBuilderRole = new aws.iam.Role("imagebuilder-role", {
    assumeRolePolicy: JSON.stringify({
        Version: "2012-10-17",
        Statement: [{
            Effect: "Allow",
            Principal: {
                Service: "ec2.amazonaws.com",
            },
            Action: "sts:AssumeRole",
        }],
    }),
    tags: {
        Name: pulumi.interpolate`${projectName}-imagebuilder-role-${environment}`,
        Environment: environment,
    },
});

const basePolicyArns = [
    "arn:aws:iam::aws:policy/EC2InstanceProfileForImageBuilder",
    "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
    "arn:aws:iam::aws:policy/EC2InstanceProfileForImageBuilderECRContainerBuilds",
];

const imageBuilderBasePolicies = basePolicyArns.map((policyArn, index) => new aws.iam.RolePolicyAttachment(`imagebuilder-role-policy-${index}`, {
    role: imageBuilderRole.name,
    policyArn: policyArn,
}));

// ECRプッシュ用の追加ポリシー
const ecrPushPolicy = new aws.iam.Policy("imagebuilder-ecr-policy", {
    name: pulumi.interpolate`${projectName}-imagebuilder-ecr-policy-${environment}`,
    policy: pulumi.all([ecrRepositoryArn]).apply(([repoArn]) => JSON.stringify({
        Version: "2012-10-17",
        Statement: [{
            Effect: "Allow",
            Action: [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage",
            ],
            Resource: repoArn,
        }],
    })),
});

const ecrPushPolicyAttachment = new aws.iam.RolePolicyAttachment("imagebuilder-ecr-policy-attachment", {
    role: imageBuilderRole.name,
    policyArn: ecrPushPolicy.arn,
});

// インスタンスプロファイル
const imageBuilderInstanceProfile = new aws.iam.InstanceProfile("imagebuilder-profile", {
    role: imageBuilderRole.name,
    tags: {
        Environment: environment,
    },
});

// Image Builderコンポーネント
const ecsAgentComponent = new aws.imagebuilder.Component("ecs-agent-component", {
    name: pulumi.interpolate`${projectName}-ecs-agent-component-${environment}`,
    platform: "Linux",
    version: componentVersion,
    description: "Jenkins Agent ECS setup component",
    data: componentYaml,
    tags: {
        Name: pulumi.interpolate`${projectName}-ecs-agent-component-${environment}`,
        Environment: environment,
    },
});

// Container Recipe
const containerRecipe = new aws.imagebuilder.ContainerRecipe("ecs-agent-recipe", {
    name: pulumi.interpolate`${projectName}-ecs-agent-recipe-${environment}`,
    version: recipeVersion,
    containerType: "DOCKER",
    parentImage: "amazonlinux:2023",
    targetRepository: {
        repositoryName: ecrRepositoryName,
        service: "ECR",
    },
    components: [{
        componentArn: ecsAgentComponent.arn,
    }],
    dockerfileTemplateData: pulumi.interpolate`
FROM {{{ imagebuilder:parentImage }}}
{{{ imagebuilder:environments }}}
{{{ imagebuilder:components }}}
# Java環境変数
ENV JAVA_HOME=/usr/lib/jvm/java-21-amazon-corretto
ENV JENKINS_AGENT_HOME=/home/jenkins
RUN chmod +x /entrypoint.sh && chown jenkins:jenkins /entrypoint.sh
USER jenkins
WORKDIR /home/jenkins
ENTRYPOINT ["/entrypoint.sh"]
`,
    tags: {
        Name: pulumi.interpolate`${projectName}-ecs-agent-recipe-${environment}`,
        Environment: environment,
    },
}, {
    replaceOnChanges: ["version", "components[0].componentArn"],
});

// Infrastructure Configuration
const infraConfig = new aws.imagebuilder.InfrastructureConfiguration("ecs-agent-infra", {
    name: pulumi.interpolate`${projectName}-ecs-agent-infra-${environment}`,
    description: "Infrastructure configuration for Jenkins Agent ECS image builds",
    instanceProfileName: imageBuilderInstanceProfile.name,
    instanceTypes: ["t3.medium"],
    subnetId: publicSubnetAId,
    securityGroupIds: [jenkinsAgentSecurityGroupId],
    terminateInstanceOnFailure: true,
    tags: {
        Name: pulumi.interpolate`${projectName}-ecs-agent-infra-${environment}`,
        Environment: environment,
    },
});

// Distribution Configuration (ECR)
const distConfig = new aws.imagebuilder.DistributionConfiguration("ecs-agent-dist", {
    name: pulumi.interpolate`${projectName}-ecs-agent-dist-${environment}`,
    description: "Distribution configuration for Jenkins Agent ECS image",
    distributions: [{
        region: aws.getRegion().then(r => r.name),
        containerDistributionConfiguration: {
            description: pulumi.interpolate`${projectName}-ecs-agent-image-${environment}`,
            targetRepository: {
                repositoryName: ecrRepositoryName,
                service: "ECR",
            },
            containerTags: [
                "latest",
                "{{imagebuilder:buildDate}}",
            ],
        },
    }],
    tags: {
        Name: pulumi.interpolate`${projectName}-ecs-agent-dist-${environment}`,
        Environment: environment,
    },
});

// Image Pipeline
const ecsAgentPipeline = new aws.imagebuilder.ImagePipeline("ecs-agent-pipeline", {
    name: pulumi.interpolate`${projectName}-ecs-agent-pipeline-${environment}`,
    description: "Pipeline to build Jenkins Agent ECS container image",
    containerRecipeArn: containerRecipe.arn,
    infrastructureConfigurationArn: infraConfig.arn,
    distributionConfigurationArn: distConfig.arn,
    status: "ENABLED",
    imageTestsConfiguration: {
        imageTestsEnabled: true,
        timeoutMinutes: 60,
    },
    tags: {
        Name: pulumi.interpolate`${projectName}-ecs-agent-pipeline-${environment}`,
        Environment: environment,
    },
}, {
    replaceOnChanges: ["containerRecipeArn"],
    deleteBeforeReplace: true,
});

// SSMパラメータに主要な値を保存
const pipelineArnParam = new aws.ssm.Parameter("agent-ecs-image-pipeline-arn", {
    name: `${ssmPrefix}/agent-ecs-image/pipeline-arn`,
    type: "String",
    value: ecsAgentPipeline.arn,
    description: "Image Builder pipeline ARN for Jenkins Agent ECS image",
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "agent-ecs-image",
    },
});

const componentVersionParam = new aws.ssm.Parameter("agent-ecs-image-component-version", {
    name: `${ssmPrefix}/agent-ecs-image/component-version`,
    type: "String",
    value: componentVersion,
    description: "Component version for Jenkins Agent ECS image",
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "agent-ecs-image",
    },
});

const recipeVersionParam = new aws.ssm.Parameter("agent-ecs-image-recipe-version", {
    name: `${ssmPrefix}/agent-ecs-image/recipe-version`,
    type: "String",
    value: recipeVersion,
    description: "Recipe version for Jenkins Agent ECS image",
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "agent-ecs-image",
    },
});

// 参考用のエクスポート
export const imagePipelineArn = ecsAgentPipeline.arn;
export const componentArn = ecsAgentComponent.arn;
export const distributionConfigurationArn = distConfig.arn;
export const infrastructureConfigurationArn = infraConfig.arn;
export const currentComponentVersion = componentVersionParam.value;
export const currentRecipeVersion = recipeVersionParam.value;
