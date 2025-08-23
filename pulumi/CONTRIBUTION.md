# Pulumi開発規約

このドキュメントは、Pulumiスタック開発における詳細な規約とベストプラクティスを定めたものです。

## 📋 目次

- [プロジェクト構造](#プロジェクト構造)
- [コーディング規約](#コーディング規約)
- [命名規則](#命名規則)
- [設定管理](#設定管理)
- [スタック間の依存関係](#スタック間の依存関係)
- [エラーハンドリング](#エラーハンドリング)
- [テストとバリデーション](#テストとバリデーション)
- [パフォーマンス最適化](#パフォーマンス最適化)
- [セキュリティベストプラクティス](#セキュリティベストプラクティス)

## プロジェクト構造

### 必須ファイル構成

```
{stack-name}/
├── Pulumi.yaml             # プロジェクト定義（必須）
├── Pulumi.{env}.yaml       # 環境別設定（オプション）
├── index.ts                # メインエントリーポイント（必須）
├── package.json            # Node.js依存関係（必須）
├── tsconfig.json           # TypeScript設定（必須）
├── bin/                    # コンパイル出力ディレクトリ
└── README.md              # スタック説明（推奨）
```

### package.json テンプレート

```json
{
  "name": "@project/{stack-name}",
  "version": "1.0.0",
  "main": "bin/index.js",
  "scripts": {
    "build": "tsc",
    "preview": "pulumi preview",
    "deploy": "pulumi up -y",
    "destroy": "pulumi destroy -y",
    "refresh": "pulumi refresh -y",
    "export": "pulumi stack export > stack-state.json",
    "import": "pulumi stack import --file=stack-state.json"
  },
  "devDependencies": {
    "@types/node": "^18.0.0",
    "typescript": "^4.0.0"
  },
  "dependencies": {
    "@pulumi/pulumi": "^3.0.0",
    "@pulumi/aws": "^6.0.0"
  }
}
```

### tsconfig.json テンプレート

```json
{
  "compilerOptions": {
    "strict": true,
    "outDir": "bin",
    "target": "es2016",
    "module": "commonjs",
    "moduleResolution": "node",
    "sourceMap": true,
    "experimentalDecorators": true,
    "pretty": true,
    "noFallthroughCasesInSwitch": true,
    "noImplicitReturns": true,
    "forceConsistentCasingInFileNames": true,
    "esModuleInterop": true
  },
  "files": ["index.ts"],
  "exclude": ["node_modules", "bin"]
}
```

### index.ts 標準構造

```typescript
/**
 * pulumi/{stack-name}/index.ts
 * {stack}のインフラストラクチャ定義
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// ========================================
// 環境変数取得
// ========================================
const environment = pulumi.getStack();

// ========================================
// SSMパラメータ参照（Single Source of Truth）
// ========================================
// 重要: Pulumi ConfigやStackReferenceは使用せず、
// SSMパラメータストアから全ての設定を取得する

// プロジェクト名を取得
const projectNameParam = aws.ssm.getParameter({
    name: `/{system-name}/${environment}/common/project-name`,
});
const projectName = pulumi.output(projectNameParam).apply(p => p.value);

// 他の設定値も同様にSSMから取得
const vpcIdParam = aws.ssm.getParameter({
    name: `/${projectName}/${environment}/network/vpc-id`,
});
const vpcId = pulumi.output(vpcIdParam).apply(p => p.value);

// ========================================
// リソース定義
// ========================================
// リソース名は固定文字列を使用（Output<T>エラー回避）
const resource = new aws.ec2.Instance("fixed-resource-name", {
    // プロパティにはpulumi.interpolateを使用
    tags: {
        Name: pulumi.interpolate`${projectName}-instance-${environment}`,
        Environment: environment,
    },
});

// ========================================
// SSMパラメータへの保存
// ========================================
// 他のスタックが参照する値はSSMに保存
const outputParam = new aws.ssm.Parameter("output-param", {
    name: pulumi.interpolate`/${projectName}/${environment}/component/output-value`,
    type: "String",
    value: resource.id,
    description: "Component output value",
    tags: {
        Environment: environment,
    },
});

// ========================================
// エクスポート（表示用のみ）
// ========================================
// エクスポートは表示・確認用のみ
// 他のスタックはSSMパラメータから値を取得すること
export const outputs = {
    resourceId: resource.id,
    ssmParameterName: outputParam.name,
};
```

## コーディング規約

### Output<T>エラーの回避

```typescript
// ❌ 間違い: リソース名にOutput<T>を使用
const bucket = new aws.s3.Bucket(`${projectName}-bucket`, {});

// ✅ 正しい: リソース名は固定文字列
const bucket = new aws.s3.Bucket("my-bucket", {
    bucket: pulumi.interpolate`${projectName}-bucket-${environment}`,
});

// ❌ 間違い: JSON.stringify内でOutput<T>を使用
const config = JSON.stringify({
    name: projectName,  // projectNameがOutput<T>の場合エラー
    environment: environment,
});

// ✅ 正しい: pulumi.allで解決してからJSON.stringify
const config = pulumi.all([projectName]).apply(([name]) => 
    JSON.stringify({
        name: name,
        environment: environment,
    })
);

// ❌ 間違い: テンプレートリテラルでOutput<T>を使用
const name = `${projectName}-${environment}`;

// ✅ 正しい: pulumi.interpolateを使用
const name = pulumi.interpolate`${projectName}-${environment}`;
```

### TypeScript規約

#### 型定義

```typescript
// インターフェース定義
interface ResourceConfig {
    instanceType: string;
    volumeSize: number;
    enableMonitoring: boolean;
}

// 型エイリアス
type Environment = "dev" | "staging" | "production";

// 列挙型
enum ResourceState {
    Creating = "CREATING",
    Active = "ACTIVE",
    Deleting = "DELETING",
}
```

#### 非同期処理

```typescript
// Promiseの適切な処理
const parameter = await aws.ssm.getParameter({
    name: "/path/to/parameter",
});

// Output値の変換
const upperCaseName = resourceName.apply(name => name.toUpperCase());

// 複数Output値の結合
const connectionString = pulumi.all([host, port, database]).apply(
    ([h, p, d]) => `postgresql://${h}:${p}/${d}`
);
```

### Pulumiリソース定義規約

#### リソースオプション

```typescript
const resource = new aws.s3.Bucket("my-bucket", {
    // リソース設定
    bucket: "my-unique-bucket-name",
    acl: "private",
}, {
    // リソースオプション
    protect: true,                    // 削除保護
    ignoreChanges: ["tags"],         // 変更無視
    deleteBeforeReplace: true,        // 置換時の削除優先
    replaceOnChanges: ["bucket"],    // 特定プロパティ変更時に置換
    dependsOn: [otherResource],      // 明示的な依存関係
    parent: parentResource,          // 親リソース
    provider: customProvider,        // カスタムプロバイダー
    transformations: [transformer],  // リソース変換
});
```

#### カスタムコンポーネント

```typescript
export class WebServerComponent extends pulumi.ComponentResource {
    public readonly instance: aws.ec2.Instance;
    public readonly securityGroup: aws.ec2.SecurityGroup;
    public readonly elasticIp: aws.ec2.Eip;
    
    constructor(
        name: string, 
        args: WebServerComponentArgs, 
        opts?: pulumi.ComponentResourceOptions
    ) {
        super("custom:app:WebServer", name, {}, opts);
        
        // セキュリティグループ
        this.securityGroup = new aws.ec2.SecurityGroup(`${name}-sg`, {
            vpcId: args.vpcId,
            ingress: [{
                protocol: "tcp",
                fromPort: 443,
                toPort: 443,
                cidrBlocks: ["0.0.0.0/0"],
            }],
            egress: [{
                protocol: "-1",
                fromPort: 0,
                toPort: 0,
                cidrBlocks: ["0.0.0.0/0"],
            }],
            tags: {
                ...args.tags,
                Name: `${name}-sg`,
            },
        }, { parent: this });
        
        // EC2インスタンス
        this.instance = new aws.ec2.Instance(`${name}-instance`, {
            instanceType: args.instanceType || "t3.micro",
            ami: args.ami,
            subnetId: args.subnetId,
            vpcSecurityGroupIds: [this.securityGroup.id],
            tags: {
                ...args.tags,
                Name: `${name}-instance`,
            },
        }, { parent: this });
        
        // Elastic IP
        this.elasticIp = new aws.ec2.Eip(`${name}-eip`, {
            instance: this.instance.id,
            vpc: true,
            tags: {
                ...args.tags,
                Name: `${name}-eip`,
            },
        }, { parent: this });
        
        // 出力の登録
        this.registerOutputs({
            instanceId: this.instance.id,
            publicIp: this.elasticIp.publicIp,
            securityGroupId: this.securityGroup.id,
        });
    }
}

interface WebServerComponentArgs {
    vpcId: pulumi.Input<string>;
    subnetId: pulumi.Input<string>;
    ami: pulumi.Input<string>;
    instanceType?: string;
    tags?: { [key: string]: string };
}
```

## 命名規則

### スタック命名

```
{system}-{component}

例:
- jenkins-network
- jenkins-controller
- lambda-functions
- lambda-api-gateway
```

### リソース命名

```typescript
// 基本パターン
const resourceName = `${projectName}-${resourceType}-${environment}`;

// 例
const vpc = new aws.ec2.Vpc(`${projectName}-vpc`, {});
const bucket = new aws.s3.Bucket(`${projectName}-artifacts-${environment}`, {});

// 複数リソースの場合
const publicSubnetA = new aws.ec2.Subnet(`${projectName}-public-subnet-a`, {});
const publicSubnetB = new aws.ec2.Subnet(`${projectName}-public-subnet-b`, {});
```

### タグ命名

```typescript
// 必須タグ
const requiredTags = {
    Name: `${projectName}-${resourceType}-${environment}`,
    Environment: environment,
    ManagedBy: "pulumi",
    Project: projectName,
    Stack: pulumi.getProject(),
};

// オプションタグ
const optionalTags = {
    Owner: "DevOps",
    CostCenter: "Engineering",
    CreatedAt: new Date().toISOString(),
    Version: "1.0.0",
};
```

## 設定管理

### ⚠️ 重要: SSMパラメータストアが唯一の設定源

**Pulumi ConfigやStackReferenceは使用禁止です。** すべての設定値はSSMパラメータストアから取得してください。

### SSMパラメータ取得パターン

```typescript
// ❌ 間違い: Pulumi Configの使用
const config = new pulumi.Config();
const projectName = config.get("projectName");

// ❌ 間違い: StackReferenceの使用
const networkStack = new pulumi.StackReference("org/stack/env");
const vpcId = networkStack.getOutput("vpcId");

// ✅ 正しい: SSMパラメータストアから取得
const projectNameParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/common/project-name`,
});
const projectName = pulumi.output(projectNameParam).apply(p => p.value);

// 数値の取得
const memorySizeParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/lambda/memory-size`,
});
const memorySize = pulumi.output(memorySizeParam).apply(p => parseInt(p.value) || 256);

// ブール値の取得
const enableMonitoringParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/monitoring/enabled`,
});
const enableMonitoring = pulumi.output(enableMonitoringParam).apply(p => p.value === "true");

// JSON設定の取得
const configParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/config`,
});
const config = pulumi.output(configParam).apply(p => JSON.parse(p.value));

// SecureStringの取得（機密情報）
const dbPasswordParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/database/password`,
    withDecryption: true,  // SecureStringの復号化
});
const dbPassword = pulumi.output(dbPasswordParam).apply(p => p.value);
```

### SSMパラメータの命名規則

```
/{system-name}/{environment}/{component}/{parameter-name}

例：
/lambda-api/dev/common/project-name
/lambda-api/dev/network/vpc-id
/lambda-api/dev/database/connection-string
/jenkins-infra/production/controller/instance-type
```

### 初期パラメータの設定（ssm-initスタック）

各システムには`ssm-init`スタックを用意し、初期パラメータを設定します：

```typescript
// lambda-ssm-init/index.ts
const parameters = {
    [`${paramPrefix}/common/project-name`]: projectName,
    [`${paramPrefix}/common/aws-region`]: awsRegion,
    [`${paramPrefix}/lambda/memory-size`]: "512",
    [`${paramPrefix}/lambda/timeout`]: "30",
    [`${paramPrefix}/monitoring/enabled`]: "true",
};

Object.entries(parameters).forEach(([name, value]) => {
    new aws.ssm.Parameter(name.replace(/\//g, "-"), {
        name: name,
        type: "String",
        value: value,
        description: `Initial parameter for ${name}`,
        tags: {
            Environment: environment,
            ManagedBy: "pulumi",
        },
    });
});
```

## スタック間の依存関係

### ⚠️ StackReferenceは使用禁止

**スタック間の値の受け渡しはSSMパラメータストアを使用してください。**

### SSMを使用した依存関係管理

```typescript
// ❌ 間違い: StackReferenceの使用
const networkStack = new pulumi.StackReference(
    `${pulumi.getOrganization()}/jenkins-network/${environment}`
);
const vpcId = networkStack.requireOutput("vpcId");

// ✅ 正しい: SSMパラメータから取得
const vpcIdParam = aws.ssm.getParameter({
    name: `/${projectName}/${environment}/network/vpc-id`,
});
const vpcId = pulumi.output(vpcIdParam).apply(p => p.value);

// 複数の値を取得
const privateSubnetAIdParam = aws.ssm.getParameter({
    name: `/${projectName}/${environment}/network/subnets/private-a-id`,
});
const privateSubnetBIdParam = aws.ssm.getParameter({
    name: `/${projectName}/${environment}/network/subnets/private-b-id`,
});

const privateSubnetIds = pulumi.all([
    pulumi.output(privateSubnetAIdParam).apply(p => p.value),
    pulumi.output(privateSubnetBIdParam).apply(p => p.value),
]);

// JSON形式で複数の値を取得
const networkConfigParam = aws.ssm.getParameter({
    name: `/${projectName}/${environment}/network/config`,
});
const networkConfig = pulumi.output(networkConfigParam).apply(p => JSON.parse(p.value));
const vpcId = networkConfig.apply(c => c.vpcId);
const subnetIds = networkConfig.apply(c => c.subnetIds);
```

### 値の保存パターン

```typescript
// 単一の値を保存
const vpcIdParam = new aws.ssm.Parameter("vpc-id", {
    name: pulumi.interpolate`/${projectName}/${environment}/network/vpc-id`,
    type: "String",
    value: vpc.id,
    description: "VPC ID",
    tags: {
        Environment: environment,
    },
});

// 複数の値をJSON形式で保存
const networkConfigParam = new aws.ssm.Parameter("network-config", {
    name: pulumi.interpolate`/${projectName}/${environment}/network/config`,
    type: "String",
    value: pulumi.all([vpc.id, privateSubnetIds, publicSubnetIds]).apply(
        ([vpcId, privateIds, publicIds]) => JSON.stringify({
            vpcId: vpcId,
            privateSubnetIds: privateIds,
            publicSubnetIds: publicIds,
            region: aws.config.region,
            lastUpdated: new Date().toISOString(),
        })
    ),
    description: "Network configuration",
    tags: {
        Environment: environment,
    },
});
```

## エラーハンドリング

### 基本的なエラーハンドリング

```typescript
// try-catchパターン
try {
    const instance = new aws.ec2.Instance("app", {
        instanceType: "t3.micro",
        ami: amiId,
    });
} catch (error) {
    console.error(`Failed to create instance: ${error}`);
    throw new Error(`Instance creation failed: ${error.message}`);
}

// Output値のバリデーション
const subnetId = networkStack.getOutput("subnetId").apply(id => {
    if (!id) {
        throw new Error("Subnet ID not found in network stack");
    }
    if (typeof id !== "string") {
        throw new Error(`Invalid subnet ID type: ${typeof id}`);
    }
    return id;
});
```

### カスタムエラークラス

```typescript
class StackConfigurationError extends Error {
    constructor(message: string, public readonly stack: string) {
        super(`Stack ${stack}: ${message}`);
        this.name = "StackConfigurationError";
    }
}

class ResourceValidationError extends Error {
    constructor(message: string, public readonly resource: string) {
        super(`Resource ${resource}: ${message}`);
        this.name = "ResourceValidationError";
    }
}

// 使用例
if (!config.get("vpcCidr")) {
    throw new StackConfigurationError("VPC CIDR is required", pulumi.getProject());
}
```

## テストとバリデーション

### 入力バリデーション

```typescript
// CIDR検証
function validateCidr(cidr: string): void {
    const cidrRegex = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/;
    if (!cidrRegex.test(cidr)) {
        throw new Error(`Invalid CIDR format: ${cidr}`);
    }
}

// インスタンスタイプ検証
function validateInstanceType(type: string): void {
    const validTypes = ["t3.micro", "t3.small", "t3.medium", "t3.large"];
    if (!validTypes.includes(type)) {
        throw new Error(`Invalid instance type: ${type}. Valid types: ${validTypes.join(", ")}`);
    }
}
```

### リソース検証

```typescript
// VPC設定の検証
const vpc = new aws.ec2.Vpc("main", {
    cidrBlock: vpcCidr,
    enableDnsHostnames: true,
    enableDnsSupport: true,
});

// 出力値の検証
export const vpcCidr = vpc.cidrBlock.apply(cidr => {
    if (!cidr.startsWith("10.") && !cidr.startsWith("172.") && !cidr.startsWith("192.168.")) {
        console.warn(`VPC CIDR ${cidr} is not in private IP range`);
    }
    return cidr;
});
```

### Pulumiポリシー

```typescript
// policy.ts
import * as pulumi from "@pulumi/pulumi/policy";

new pulumi.policy.PolicyPack("aws-policies", {
    policies: [
        {
            name: "required-tags",
            description: "Ensure required tags are present",
            enforcementLevel: "mandatory",
            validateResource: (args, reportViolation) => {
                if (args.type.startsWith("aws:")) {
                    const tags = args.props.tags;
                    if (!tags || !tags.Environment) {
                        reportViolation("Missing required Environment tag");
                    }
                    if (!tags || !tags.ManagedBy) {
                        reportViolation("Missing required ManagedBy tag");
                    }
                }
            },
        },
        {
            name: "encrypted-storage",
            description: "Ensure storage is encrypted",
            enforcementLevel: "mandatory",
            validateResource: (args, reportViolation) => {
                if (args.type === "aws:s3:Bucket") {
                    const encryption = args.props.serverSideEncryptionConfiguration;
                    if (!encryption) {
                        reportViolation("S3 bucket must have encryption enabled");
                    }
                }
                if (args.type === "aws:ebs:Volume") {
                    if (!args.props.encrypted) {
                        reportViolation("EBS volume must be encrypted");
                    }
                }
            },
        },
    ],
});
```

## パフォーマンス最適化

### リソースのバッチ処理

```typescript
// 効率的なサブネット作成
const availabilityZones = ["a", "b", "c"];
const publicSubnets = availabilityZones.map((az, index) => 
    new aws.ec2.Subnet(`public-subnet-${az}`, {
        vpcId: vpc.id,
        cidrBlock: `10.0.${index}.0/24`,
        availabilityZone: `${region}${az}`,
        mapPublicIpOnLaunch: true,
        tags: {
            ...commonTags,
            Name: `${projectName}-public-subnet-${az}`,
            Type: "public",
        },
    })
);
```

### 条件付きリソース作成

```typescript
// 環境に応じたリソース作成
if (environment === "production") {
    new aws.cloudwatch.Dashboard("monitoring", {
        dashboardName: `${projectName}-dashboard`,
        dashboardBody: JSON.stringify(dashboardConfig),
    });
    
    new aws.backup.Plan("backup", {
        name: `${projectName}-backup-plan`,
        rules: [{
            ruleName: "daily-backup",
            targetVaultName: backupVault.name,
            schedule: "cron(0 5 ? * * *)",
        }],
    });
}
```

### 並列実行の最適化

```typescript
// pulumi-config.yaml
runtime:
  parallel: 10  # 並列実行数の制限

// または環境変数
// PULUMI_PARALLEL=10
```

## セキュリティベストプラクティス

### 機密情報の管理

```typescript
// Pulumi Secretsの使用
const dbPassword = config.requireSecret("dbPassword");

// SSM SecureStringへの保存
const passwordParameter = new aws.ssm.Parameter("db-password", {
    name: `${ssmPrefix}/database/password`,
    type: "SecureString",
    value: dbPassword,
    description: "Database password",
    tags: commonTags,
});

// Secrets Managerの使用
const secret = new aws.secretsmanager.Secret("db-secret", {
    name: `${projectName}-db-secret`,
    description: "Database credentials",
    tags: commonTags,
});

const secretVersion = new aws.secretsmanager.SecretVersion("db-secret-version", {
    secretId: secret.id,
    secretString: pulumi.interpolate`{
        "username": "admin",
        "password": "${dbPassword}"
    }`,
});
```

### IAMベストプラクティス

```typescript
// 最小権限の原則
const role = new aws.iam.Role("app-role", {
    assumeRolePolicy: aws.iam.assumeRolePolicyForPrincipal({
        Service: "ec2.amazonaws.com",
    }),
    tags: commonTags,
});

// インラインポリシーよりも管理ポリシーを優先
const policy = new aws.iam.Policy("app-policy", {
    name: `${projectName}-app-policy`,
    policy: JSON.stringify({
        Version: "2012-10-17",
        Statement: [
            {
                Effect: "Allow",
                Action: [
                    "s3:GetObject",
                    "s3:ListBucket",
                ],
                Resource: [
                    bucket.arn,
                    pulumi.interpolate`${bucket.arn}/*`,
                ],
            },
        ],
    }),
    tags: commonTags,
});

const rolePolicyAttachment = new aws.iam.RolePolicyAttachment("app-policy-attachment", {
    role: role.name,
    policyArn: policy.arn,
});
```

### ネットワークセキュリティ

```typescript
// セキュリティグループの厳格な設定
const appSecurityGroup = new aws.ec2.SecurityGroup("app-sg", {
    vpcId: vpc.id,
    description: "Security group for application servers",
    ingress: [
        {
            description: "HTTPS from ALB",
            protocol: "tcp",
            fromPort: 443,
            toPort: 443,
            securityGroups: [albSecurityGroup.id], // 特定のSGからのみ
        },
    ],
    egress: [
        {
            description: "HTTPS to internet",
            protocol: "tcp",
            fromPort: 443,
            toPort: 443,
            cidrBlocks: ["0.0.0.0/0"],
        },
    ],
    tags: {
        ...commonTags,
        Name: `${projectName}-app-sg`,
    },
});

// NACLによる追加保護
const privateNacl = new aws.ec2.NetworkAcl("private-nacl", {
    vpcId: vpc.id,
    tags: {
        ...commonTags,
        Name: `${projectName}-private-nacl`,
    },
});

// 必要最小限のルールのみ追加
new aws.ec2.NetworkAclRule("private-nacl-ingress-https", {
    networkAclId: privateNacl.id,
    ruleNumber: 100,
    protocol: "tcp",
    ruleAction: "allow",
    cidrBlock: vpc.cidrBlock,
    fromPort: 443,
    toPort: 443,
});
```

### 暗号化

```typescript
// S3バケットの暗号化
const bucket = new aws.s3.Bucket("secure-bucket", {
    serverSideEncryptionConfiguration: {
        rule: {
            applyServerSideEncryptionByDefault: {
                sseAlgorithm: "AES256",
            },
        },
    },
    versioning: {
        enabled: true,
    },
    publicAccessBlock: {
        blockPublicAcls: true,
        blockPublicPolicy: true,
        ignorePublicAcls: true,
        restrictPublicBuckets: true,
    },
    tags: commonTags,
});

// EBSボリュームの暗号化
const volume = new aws.ebs.Volume("encrypted-volume", {
    availabilityZone: `${region}a`,
    size: 100,
    type: "gp3",
    encrypted: true,
    kmsKeyId: kmsKey.id,
    tags: {
        ...commonTags,
        Name: `${projectName}-encrypted-volume`,
    },
});

// RDSの暗号化
const database = new aws.rds.Instance("encrypted-db", {
    engine: "mysql",
    engineVersion: "8.0",
    instanceClass: "db.t3.micro",
    allocatedStorage: 20,
    storageEncrypted: true,
    kmsKeyId: kmsKey.id,
    tags: commonTags,
});
```

## バージョニングパターン

### セマンティックバージョニング

```typescript
// AWS Image Builder等で必要なX.Y.Z形式のバージョン生成
function generateSemanticVersion(): string {
    const now = new Date();
    const major = 1;
    const minor = `${String(now.getFullYear()).slice(-2)}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`;
    const patch = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
    
    return `${major}.${minor}.${patch}`;
    // 例: 1.241225.43200 (1.日付.秒数)
}

// 設定から取得または自動生成
const version = config.get("version") || generateSemanticVersion();
```

## デバッグとトラブルシューティング

### デバッグ出力

```typescript
// 開発環境でのデバッグ出力
if (environment === "dev") {
    console.log("VPC ID:", vpc.id);
    console.log("Subnet IDs:", subnetIds);
}

// 条件付きログ
const debug = config.getBoolean("debug") || false;
if (debug) {
    pulumi.log.info(`Creating VPC with CIDR: ${vpcCidr}`);
    pulumi.log.debug(`Tags: ${JSON.stringify(commonTags)}`);
}
```

### スタック診断

```bash
# スタック状態の確認
pulumi stack --show-ids
pulumi stack export > stack-state.json

# リソースグラフの表示
pulumi stack graph

# 詳細ログ
export PULUMI_DEBUG=true
pulumi up --logtostderr -v=9 2> debug.log
```

## 関連ドキュメント

- [README.md](README.md) - Pulumiスタックの使用方法
- [メインCONTRIBUTION.md](../CONTRIBUTION.md) - プロジェクト全体の開発規約
- [CLAUDE.md](../CLAUDE.md) - AI開発アシスタント向けガイドライン
- [Pulumi公式ドキュメント](https://www.pulumi.com/docs/)