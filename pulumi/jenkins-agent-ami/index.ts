/**
 * pulumi/jenkins-agent-ami/index.ts
 * 
 * Jenkins Agent用のカスタムAMIをEC2 Image Builderで作成するPulumiスクリプト
 * 起動時間を短縮するため、必要なソフトウェアを事前インストール
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

// 設定値を変数に設定
const projectName = pulumi.output(projectNameParam).apply(p => p.value);

// バージョン管理（自動インクリメント）
// Image Builderは X.Y.Z 形式のセマンティックバージョンのみ受け付ける
// 各セグメントは整数で、通常は 0-999999 の範囲を推奨
const now = new Date();

// 日付をマイナーバージョンに（YYMMDD形式）
const year = String(now.getFullYear()).slice(-2); // 年の下2桁
const month = String(now.getMonth() + 1).padStart(2, '0');
const day = String(now.getDate()).padStart(2, '0');
const dateStr = `${year}${month}${day}`; // 例: 250809

// 時刻を0-86399の範囲の数値に変換（1日の秒数）
// これにより、パッチバージョンが有効な範囲内に収まる
const hours = now.getHours();
const minutes = now.getMinutes();
const seconds = now.getSeconds();
const secondsOfDay = hours * 3600 + minutes * 60 + seconds; // 0-86399

// バージョンフォーマット: 1.YYMMDD.秒数 (X.Y.Z形式)
// 例: 1.250809.41809 (11:30:09の場合)
const config = new pulumi.Config();
const componentVersion = config.get("componentVersion") || `1.${dateStr}.${secondsOfDay}`;
const recipeVersion = config.get("recipeVersion") || `1.${dateStr}.${secondsOfDay}`;

// バージョン情報をログ出力
console.log(`[INFO] Component Version: ${componentVersion}`);
console.log(`[INFO] Recipe Version: ${recipeVersion}`);

// ネットワークリソースのSSMパラメータを取得
const vpcIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/vpc-id`,
});
const publicSubnetAIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/public-subnet-a-id`,
});
const publicSubnetBIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/network/public-subnet-b-id`,
});

// セキュリティグループのSSMパラメータを取得
const jenkinsAgentSecurityGroupIdParam = aws.ssm.getParameter({
    name: `${ssmPrefix}/security/jenkins-agent-sg-id`,
});

// リソースIDを取得
const vpcId = pulumi.output(vpcIdParam).apply(p => p.value);
const publicSubnetAId = pulumi.output(publicSubnetAIdParam).apply(p => p.value);
const publicSubnetBId = pulumi.output(publicSubnetBIdParam).apply(p => p.value);
const publicSubnetIds = [publicSubnetAId, publicSubnetBId];
const jenkinsAgentSecurityGroupId = pulumi.output(jenkinsAgentSecurityGroupIdParam).apply(p => p.value);

// IAMロール（EC2 Image Builder用）
const imageBuilderRole = new aws.iam.Role(`imagebuilder-role`, {
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
        Name: pulumi.interpolate`${projectName}-imagebuilder-role-${environment}`,
        Environment: environment,
    },
});

// 必要なポリシーをアタッチ
const ec2InstanceProfilePolicy = new aws.iam.RolePolicyAttachment(`imagebuilder-ec2-policy`, {
    role: imageBuilderRole.name,
    policyArn: "arn:aws:iam::aws:policy/EC2InstanceProfileForImageBuilder",
});

const ssmManagedPolicy = new aws.iam.RolePolicyAttachment(`imagebuilder-ssm-policy`, {
    role: imageBuilderRole.name,
    policyArn: "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
});

// インスタンスプロファイル
const imageBuilderInstanceProfile = new aws.iam.InstanceProfile(`imagebuilder-profile`, {
    role: imageBuilderRole.name,
    tags: {
        Environment: environment,
    },
});

// Jenkins Agent用コンポーネント（x86_64）
const jenkinsAgentComponentX86 = new aws.imagebuilder.Component(`agent-component-x86`, {
    name: pulumi.interpolate`${projectName}-agent-component-x86-${environment}`,
    platform: "Linux",
    version: componentVersion,
    description: "Jenkins Agent setup component for x86_64",
    data: `name: JenkinsAgentSetup-x86
description: Install and configure Jenkins Agent dependencies
schemaVersion: 1.0

phases:
  - name: build
    steps:
      - name: UpdateSystem
        action: ExecuteBash
        inputs:
          commands:
            - echo "Starting Jenkins Agent setup"
            - dnf update -y

      - name: InstallBasicPackages
        action: ExecuteBash
        inputs:
          commands:
            - dnf install -y git jq wget tar gzip unzip which
            - dnf install -y amazon-ssm-agent

      - name: InstallDocker
        action: ExecuteBash
        inputs:
          commands:
            - dnf install -y docker
            - systemctl enable docker
            - groupadd -f docker
            - chmod 666 /var/run/docker.sock || true

      - name: InstallJava
        action: ExecuteBash
        inputs:
          commands:
            - dnf install -y java-21-amazon-corretto
            - java -version

      - name: InstallBuildTools
        action: ExecuteBash
        inputs:
          commands:
            - dnf install -y gcc gcc-c++ make
            - dnf install -y python3 python3-pip
            - pip3 install --upgrade pip
            - pip3 install awscli

      - name: InstallNodeJS
        action: ExecuteBash
        inputs:
          commands:
            - curl -sL https://rpm.nodesource.com/setup_18.x | bash -
            - dnf install -y nodejs
            - npm install -g npm@latest
            - node --version
            - npm --version

      - name: CreateJenkinsUser
        action: ExecuteBash
        inputs:
          commands:
            - useradd -m -d /home/jenkins -s /bin/bash jenkins || true
            - usermod -aG docker jenkins
            - newgrp docker || true
            - mkdir -p /home/jenkins/agent
            - mkdir -p /home/jenkins/.docker
            - chown -R jenkins:jenkins /home/jenkins
            - echo '{"group":"docker"}' > /etc/docker/daemon.json || true
            - chmod 666 /var/run/docker.sock || true

      - name: SetupSwap
        action: ExecuteBash
        inputs:
          commands:
            - dd if=/dev/zero of=/swapfile bs=1M count=2048
            - chmod 600 /swapfile
            - mkswap /swapfile
            - echo '/swapfile none swap sw 0 0' >> /etc/fstab

      - name: ConfigureTmp
        action: ExecuteBash
        inputs:
          commands:
            - echo 'tmpfs /tmp tmpfs defaults,noatime,size=2G 0 0' >> /etc/fstab

      - name: CleanupCache
        action: ExecuteBash
        inputs:
          commands:
            - dnf clean all
            - rm -rf /var/cache/dnf
            - rm -rf /tmp/*

  - name: validate
    steps:
      - name: ValidateInstallation
        action: ExecuteBash
        inputs:
          commands:
            - java -version
            - docker --version
            - git --version
            - node --version
            - npm --version
            - python3 --version
            - aws --version
`,
    tags: {
        Name: pulumi.interpolate`${projectName}-agent-component-x86-${environment}`,
        Environment: environment,
        Architecture: "x86_64",
    },
});

// Jenkins Agent用コンポーネント（ARM64）
const jenkinsAgentComponentArm = new aws.imagebuilder.Component(`agent-component-arm`, {
    name: pulumi.interpolate`${projectName}-agent-component-arm-${environment}`,
    platform: "Linux",
    version: componentVersion,
    description: "Jenkins Agent setup component for ARM64",
    data: `name: JenkinsAgentSetup-arm64
description: Install and configure Jenkins Agent dependencies for ARM64
schemaVersion: 1.0

phases:
  - name: build
    steps:
      - name: UpdateSystem
        action: ExecuteBash
        inputs:
          commands:
            - echo "Starting Jenkins Agent setup for ARM64"
            - dnf update -y

      - name: InstallBasicPackages
        action: ExecuteBash
        inputs:
          commands:
            - dnf install -y git jq wget tar gzip unzip which
            - dnf install -y amazon-ssm-agent

      - name: InstallDocker
        action: ExecuteBash
        inputs:
          commands:
            - dnf install -y docker
            - systemctl enable docker
            - groupadd -f docker
            - chmod 666 /var/run/docker.sock || true

      - name: InstallJava
        action: ExecuteBash
        inputs:
          commands:
            - dnf install -y java-21-amazon-corretto
            - java -version

      - name: InstallBuildTools
        action: ExecuteBash
        inputs:
          commands:
            - dnf install -y gcc gcc-c++ make
            - dnf install -y python3 python3-pip
            - pip3 install --upgrade pip
            - pip3 install awscli

      - name: InstallNodeJS
        action: ExecuteBash
        inputs:
          commands:
            - curl -sL https://rpm.nodesource.com/setup_18.x | bash -
            - dnf install -y nodejs
            - npm install -g npm@latest
            - node --version
            - npm --version

      - name: CreateJenkinsUser
        action: ExecuteBash
        inputs:
          commands:
            - useradd -m -d /home/jenkins -s /bin/bash jenkins || true
            - usermod -aG docker jenkins
            - newgrp docker || true
            - mkdir -p /home/jenkins/agent
            - mkdir -p /home/jenkins/.docker
            - chown -R jenkins:jenkins /home/jenkins
            - echo '{"group":"docker"}' > /etc/docker/daemon.json || true
            - chmod 666 /var/run/docker.sock || true

      - name: SetupSwap
        action: ExecuteBash
        inputs:
          commands:
            - dd if=/dev/zero of=/swapfile bs=1M count=2048
            - chmod 600 /swapfile
            - mkswap /swapfile
            - echo '/swapfile none swap sw 0 0' >> /etc/fstab

      - name: ConfigureTmp
        action: ExecuteBash
        inputs:
          commands:
            - echo 'tmpfs /tmp tmpfs defaults,noatime,size=2G 0 0' >> /etc/fstab

      - name: CleanupCache
        action: ExecuteBash
        inputs:
          commands:
            - dnf clean all
            - rm -rf /var/cache/dnf
            - rm -rf /tmp/*

  - name: validate
    steps:
      - name: ValidateInstallation
        action: ExecuteBash
        inputs:
          commands:
            - java -version
            - docker --version
            - git --version
            - node --version
            - npm --version
            - python3 --version
            - aws --version
`,
    tags: {
        Name: pulumi.interpolate`${projectName}-agent-component-arm-${environment}`,
        Environment: environment,
        Architecture: "arm64",
    },
});

// 最新のAmazon Linux 2023 AMIを取得
const amiX86 = aws.ec2.getAmi({
    mostRecent: true,
    owners: ["amazon"],
    filters: [{
        name: "name",
        values: ["al2023-ami-*-kernel-*-x86_64"],
    }],
});

const amiArm = aws.ec2.getAmi({
    mostRecent: true,
    owners: ["amazon"],
    filters: [{
        name: "name",
        values: ["al2023-ami-*-kernel-*-arm64"],
    }],
});

// Image Recipe（x86_64）
const jenkinsAgentRecipeX86 = new aws.imagebuilder.ImageRecipe(`agent-recipe-x86`, {
    name: pulumi.interpolate`${projectName}-agent-recipe-x86-${environment}`,
    version: recipeVersion,
    description: "Jenkins Agent AMI recipe for x86_64",
    parentImage: amiX86.then(ami => ami.id),
    components: [{
        componentArn: jenkinsAgentComponentX86.arn,
    }],
    blockDeviceMappings: [{
        deviceName: "/dev/xvda",
        ebs: {
            volumeSize: 30,
            volumeType: "gp3",
            deleteOnTermination: "true",
            encrypted: "true",
        },
    }],
    tags: {
        Name: pulumi.interpolate`${projectName}-agent-recipe-x86-${environment}`,
        Environment: environment,
        Architecture: "x86_64",
    },
}, {
    // バージョンやコンポーネントが変更される場合は、レシピを置き換える
    replaceOnChanges: ["version", "components[0].componentArn"],
});

// Image Recipe（ARM64）
const jenkinsAgentRecipeArm = new aws.imagebuilder.ImageRecipe(`agent-recipe-arm`, {
    name: pulumi.interpolate`${projectName}-agent-recipe-arm-${environment}`,
    version: recipeVersion,
    description: "Jenkins Agent AMI recipe for ARM64",
    parentImage: amiArm.then(ami => ami.id),
    components: [{
        componentArn: jenkinsAgentComponentArm.arn,
    }],
    blockDeviceMappings: [{
        deviceName: "/dev/xvda",
        ebs: {
            volumeSize: 30,
            volumeType: "gp3",
            deleteOnTermination: "true",
            encrypted: "true",
        },
    }],
    tags: {
        Name: pulumi.interpolate`${projectName}-agent-recipe-arm-${environment}`,
        Environment: environment,
        Architecture: "arm64",
    },
}, {
    // バージョンやコンポーネントが変更される場合は、レシピを置き換える
    replaceOnChanges: ["version", "components[0].componentArn"],
});

// Infrastructure Configuration（x86_64）
const infraConfigX86 = new aws.imagebuilder.InfrastructureConfiguration(`agent-infra-x86`, {
    name: pulumi.interpolate`${projectName}-agent-infra-x86-${environment}`,
    description: "Infrastructure configuration for Jenkins Agent x86_64",
    instanceProfileName: imageBuilderInstanceProfile.name,
    instanceTypes: ["t3.medium"],
    subnetId: publicSubnetAId,
    securityGroupIds: [jenkinsAgentSecurityGroupId],
    terminateInstanceOnFailure: true,
    tags: {
        Name: pulumi.interpolate`${projectName}-agent-infra-x86-${environment}`,
        Environment: environment,
        Architecture: "x86_64",
    },
});

// Infrastructure Configuration（ARM64）
const infraConfigArm = new aws.imagebuilder.InfrastructureConfiguration(`agent-infra-arm`, {
    name: pulumi.interpolate`${projectName}-agent-infra-arm-${environment}`,
    description: "Infrastructure configuration for Jenkins Agent ARM64",
    instanceProfileName: imageBuilderInstanceProfile.name,
    instanceTypes: ["t4g.medium"],
    subnetId: publicSubnetAId,
    securityGroupIds: [jenkinsAgentSecurityGroupId],
    terminateInstanceOnFailure: true,
    tags: {
        Name: pulumi.interpolate`${projectName}-agent-infra-arm-${environment}`,
        Environment: environment,
        Architecture: "arm64",
    },
});

// Distribution Configuration（x86_64）
const distConfigX86 = new aws.imagebuilder.DistributionConfiguration(`agent-dist-x86`, {
    name: pulumi.interpolate`${projectName}-agent-dist-x86-${environment}`,
    description: "Distribution configuration for Jenkins Agent x86_64",
    distributions: [{
        region: aws.getRegion().then(r => r.name),
        amiDistributionConfiguration: {
            name: pulumi.interpolate`${projectName}-agent-x86-${environment}-{{imagebuilder:buildDate}}`,
            description: "Jenkins Agent AMI for x86_64",
            amiTags: {
                Name: pulumi.interpolate`${projectName}-agent-x86-${environment}`,
                Environment: environment,
                Architecture: "x86_64",
                BuildDate: "{{imagebuilder:buildDate}}",
                BuildVersion: "{{imagebuilder:buildVersion}}",
            },
        },
    }],
    tags: {
        Name: pulumi.interpolate`${projectName}-agent-dist-x86-${environment}`,
        Environment: environment,
    },
});

// Distribution Configuration（ARM64）
const distConfigArm = new aws.imagebuilder.DistributionConfiguration(`agent-dist-arm`, {
    name: pulumi.interpolate`${projectName}-agent-dist-arm-${environment}`,
    description: "Distribution configuration for Jenkins Agent ARM64",
    distributions: [{
        region: aws.getRegion().then(r => r.name),
        amiDistributionConfiguration: {
            name: pulumi.interpolate`${projectName}-agent-arm-${environment}-{{imagebuilder:buildDate}}`,
            description: "Jenkins Agent AMI for ARM64",
            amiTags: {
                Name: pulumi.interpolate`${projectName}-agent-arm-${environment}`,
                Environment: environment,
                Architecture: "arm64",
                BuildDate: "{{imagebuilder:buildDate}}",
                BuildVersion: "{{imagebuilder:buildVersion}}",
            },
        },
    }],
    tags: {
        Name: pulumi.interpolate`${projectName}-agent-dist-arm-${environment}`,
        Environment: environment,
    },
});

// Image Pipeline（x86_64）- スケジュール実行なし
const imagePipelineX86 = new aws.imagebuilder.ImagePipeline(`agent-pipeline-x86`, {
    name: pulumi.interpolate`${projectName}-agent-pipeline-x86-${environment}`,
    description: "Pipeline to build Jenkins Agent AMI for x86_64",
    imageRecipeArn: jenkinsAgentRecipeX86.arn,
    infrastructureConfigurationArn: infraConfigX86.arn,
    distributionConfigurationArn: distConfigX86.arn,
    status: "ENABLED",
    imageTestsConfiguration: {
        imageTestsEnabled: true,
        timeoutMinutes: 60,
    },
    tags: {
        Name: pulumi.interpolate`${projectName}-agent-pipeline-x86-${environment}`,
        Environment: environment,
        Architecture: "x86_64",
    },
}, {
    // レシピが変更される場合は、パイプラインを置き換える
    replaceOnChanges: ["imageRecipeArn"],
    deleteBeforeReplace: true,
});

// Image Pipeline（ARM64）- スケジュール実行なし
const imagePipelineArm = new aws.imagebuilder.ImagePipeline(`agent-pipeline-arm`, {
    name: pulumi.interpolate`${projectName}-agent-pipeline-arm-${environment}`,
    description: "Pipeline to build Jenkins Agent AMI for ARM64",
    imageRecipeArn: jenkinsAgentRecipeArm.arn,
    infrastructureConfigurationArn: infraConfigArm.arn,
    distributionConfigurationArn: distConfigArm.arn,
    status: "ENABLED",
    imageTestsConfiguration: {
        imageTestsEnabled: true,
        timeoutMinutes: 60,
    },
    tags: {
        Name: pulumi.interpolate`${projectName}-agent-pipeline-arm-${environment}`,
        Environment: environment,
        Architecture: "arm64",
    },
}, {
    // レシピが変更される場合は、パイプラインを置き換える
    replaceOnChanges: ["imageRecipeArn"],
    deleteBeforeReplace: true,
});

// カスタムAMI IDを格納するSSMパラメータ（仮の値）
const customAmiX86Parameter = new aws.ssm.Parameter(`agent-custom-ami-x86`, {
    name: `${ssmPrefix}/agent-ami/custom-ami-x86`,
    type: "String",
    value: "ami-placeholder-x86",  // 手動で更新する仮の値
    overwrite: true,
    description: "Custom AMI ID for Jenkins Agent x86_64 (manually update after Image Builder execution)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "agent-ami",
        Architecture: "x86_64",
        Note: "Update this value manually after running Image Builder pipeline",
    },
});

const customAmiArmParameter = new aws.ssm.Parameter(`agent-custom-ami-arm`, {
    name: `${ssmPrefix}/agent-ami/custom-ami-arm`,
    type: "String",
    value: "ami-placeholder-arm",  // 手動で更新する仮の値
    overwrite: true,
    description: "Custom AMI ID for Jenkins Agent ARM64 (manually update after Image Builder execution)",
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "agent-ami",
        Architecture: "arm64",
        Note: "Update this value manually after running Image Builder pipeline",
    },
});

// パイプラインARNをSSMパラメータに保存
const pipelineX86ArnParam = new aws.ssm.Parameter(`pipeline-x86-arn`, {
    name: `${ssmPrefix}/agent-ami/pipeline-x86-arn`,
    type: "String",
    value: imagePipelineX86.arn,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "agent-ami",
    },
});

const pipelineArmArnParam = new aws.ssm.Parameter(`pipeline-arm-arn`, {
    name: `${ssmPrefix}/agent-ami/pipeline-arm-arn`,
    type: "String",
    value: imagePipelineArm.arn,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "agent-ami",
    },
});

// コンポーネントバージョンをSSMパラメータに保存
const componentVersionParam = new aws.ssm.Parameter(`component-version`, {
    name: `${ssmPrefix}/agent-ami/component-version`,
    type: "String",
    value: componentVersion,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "agent-ami",
    },
});

// レシピバージョンをSSMパラメータに保存
const recipeVersionParam = new aws.ssm.Parameter(`recipe-version`, {
    name: `${ssmPrefix}/agent-ami/recipe-version`,
    type: "String",
    value: recipeVersion,
    overwrite: true,
    tags: {
        Environment: environment,
        ManagedBy: "pulumi",
        Component: "agent-ami",
    },
});

// エクスポート
export const imagePipelineX86Arn = imagePipelineX86.arn;
export const imagePipelineArmArn = imagePipelineArm.arn;
export const imageBuilderRoleArn = imageBuilderRole.arn;
export const jenkinsAgentComponentX86Arn = jenkinsAgentComponentX86.arn;
export const jenkinsAgentComponentArmArn = jenkinsAgentComponentArm.arn;
export const customAmiX86ParameterName = customAmiX86Parameter.name;
export const customAmiArmParameterName = customAmiArmParameter.name;
export const currentComponentVersion = componentVersion;
export const currentRecipeVersion = recipeVersion;