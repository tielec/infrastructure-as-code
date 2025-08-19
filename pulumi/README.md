# Pulumiインフラストラクチャスタック

Infrastructure as Code (IaC) を実現するPulumiスタック集です。AWS上にインフラストラクチャを宣言的に構築・管理します。

## 📋 目次

- [概要](#概要)
- [前提条件](#前提条件)
- [ディレクトリ構造](#ディレクトリ構造)
- [スタック一覧](#スタック一覧)
- [使用方法](#使用方法)
- [開発ガイドライン](#開発ガイドライン)
- [トラブルシューティング](#トラブルシューティング)

## 概要

このPulumiプロジェクトは、TypeScriptを使用してAWSインフラストラクチャを管理します：

### 特徴

- **宣言的インフラ管理**: TypeScriptコードでインフラを定義
- **マルチ環境対応**: dev/staging/production環境の分離管理
- **S3バックエンド**: 状態ファイルをS3で一元管理
- **SSM連携**: パラメータストアとの密接な統合
- **モジュール化**: 各コンポーネントを独立したスタックとして管理

### サポートシステム

- **Jenkins CI/CD**: 完全なJenkins環境のインフラストラクチャ
- **Lambda Functions**: サーバーレスアプリケーションのインフラ
- **共通コンポーネント**: ネットワーク、セキュリティ、ストレージ等

## 前提条件

### 必要なソフトウェア

- Node.js 18以上
- npm または yarn
- Pulumi CLI 3.0以上
- AWS CLI v2
- TypeScript 4.0以上

### AWS権限

実行するIAMユーザー/ロールには以下の権限が必要です：

- EC2フルアクセス
- VPCフルアクセス
- IAMロール作成・管理権限
- S3（Pulumiステート管理用）
- Systems Manager（パラメータストア）
- CloudFormation読み取り（既存リソース参照用）
- Lambda（サーバーレス構築時）
- EFS、RDS等（使用するサービスに応じて）

### 環境セットアップ

```bash
# Pulumi CLIのインストール
curl -fsSL https://get.pulumi.com | sh

# または Homebrew（Mac）
brew install pulumi

# AWS認証情報の設定
aws configure

# 環境変数の設定
export PULUMI_CONFIG_PASSPHRASE=your-secure-passphrase
export AWS_REGION=ap-northeast-1
```

## ディレクトリ構造

```
pulumi/
├── jenkins-*/              # Jenkins関連スタック
│   ├── jenkins-ssm-init/   # SSMパラメータ初期化
│   ├── jenkins-network/    # VPC、サブネット
│   ├── jenkins-security/   # セキュリティグループ、IAM
│   ├── jenkins-nat/        # NATゲートウェイ
│   ├── jenkins-storage/    # EFS、EBS
│   ├── jenkins-loadbalancer/ # ALB
│   ├── jenkins-controller/ # Jenkinsコントローラー
│   ├── jenkins-agent-ami/  # エージェント用AMI
│   ├── jenkins-agent/      # Jenkinsエージェント
│   ├── jenkins-config/     # Jenkins設定
│   └── jenkins-application/ # Jenkinsアプリケーション
├── lambda-*/               # Lambda関連スタック
│   ├── lambda-account-setup/ # アカウント初期設定
│   ├── lambda-network/     # Lambda用VPC
│   ├── lambda-security/    # セキュリティ設定
│   ├── lambda-nat/         # NAT設定
│   ├── lambda-functions/   # Lambda関数
│   ├── lambda-api-gateway/ # API Gateway
│   ├── lambda-database/    # データベース
│   ├── lambda-vpce/        # VPCエンドポイント
│   ├── lambda-waf/         # WAF設定
│   └── lambda-websocket/   # WebSocket API
└── test-*/                 # テスト用スタック
    └── test-s3/            # S3バケットテスト
```

### 各スタックの共通構造

```
{stack-name}/
├── Pulumi.yaml             # プロジェクト定義
├── Pulumi.{env}.yaml       # 環境別設定（オプション）
├── index.ts                # メインエントリーポイント
├── package.json            # Node.js依存関係
└── tsconfig.json           # TypeScript設定
```

## スタック一覧

### Jenkins CI/CDスタック

| スタック名 | 説明 | 依存関係 | 主要リソース |
|-----------|------|----------|--------------|
| `jenkins-ssm-init` | SSMパラメータ初期化 | なし | SSMパラメータ |
| `jenkins-network` | ネットワーク基盤 | ssm-init | VPC、サブネット、ルートテーブル |
| `jenkins-security` | セキュリティ設定 | network | セキュリティグループ、IAMロール |
| `jenkins-nat` | NATゲートウェイ | security | NAT Gateway、Elastic IP |
| `jenkins-storage` | ストレージ | security | EFS、バックアップ設定 |
| `jenkins-loadbalancer` | ロードバランサー | security | ALB、ターゲットグループ |
| `jenkins-controller` | Jenkinsコントローラー | nat, storage, loadbalancer | EC2、Auto Scaling |
| `jenkins-agent-ami` | エージェントAMI | security | カスタムAMI |
| `jenkins-agent` | Jenkinsエージェント | controller, agent-ami | EC2 Fleet、Auto Scaling |
| `jenkins-config` | Jenkins設定 | controller | SSMドキュメント、設定 |
| `jenkins-application` | Jenkinsアプリ | config, agent | ジョブ、プラグイン設定 |

### Lambda Functionsスタック

| スタック名 | 説明 | 依存関係 | 主要リソース |
|-----------|------|----------|--------------|
| `lambda-account-setup` | アカウント初期設定 | なし | IAMロール、ポリシー |
| `lambda-network` | Lambda用VPC | account-setup | VPC、サブネット |
| `lambda-security` | セキュリティ設定 | network | セキュリティグループ |
| `lambda-nat` | NAT設定 | security | NAT Gateway |
| `lambda-functions` | Lambda関数 | nat | Lambda関数、レイヤー |
| `lambda-api-gateway` | API Gateway | functions | REST API、リソース |
| `lambda-database` | データベース | security | RDS、DynamoDB |
| `lambda-vpce` | VPCエンドポイント | network | VPCエンドポイント |
| `lambda-waf` | WAF設定 | api-gateway | WAF ACL、ルール |
| `lambda-websocket` | WebSocket API | functions | WebSocket API |

### テストスタック

| スタック名 | 説明 | 用途 |
|-----------|------|------|
| `test-s3` | S3バケットテスト | Pulumiバックエンド検証 |

## 使用方法

### 基本的な操作

#### 1. スタックの初期化

```bash
cd pulumi/{stack-name}
npm install
pulumi stack init {environment}
```

#### 2. 設定値の設定

```bash
# 基本設定
pulumi config set aws:region ap-northeast-1

# 機密情報（暗号化）
pulumi config set --secret dbPassword mySecurePassword

# 構造化された設定
pulumi config set --path 'tags.Environment' dev
pulumi config set --path 'tags.Project' jenkins-infra
```

#### 3. プレビュー（変更内容の確認）

```bash
pulumi preview

# 詳細な差分表示
pulumi preview --diff

# 特定のリソースのみ
pulumi preview --target 'urn:pulumi:dev::jenkins-network::*'
```

#### 4. デプロイ

```bash
# 対話的デプロイ
pulumi up

# 非対話的デプロイ（CI/CD用）
pulumi up -y

# 並列度の指定
pulumi up --parallel 10
```

#### 5. スタック出力の確認

```bash
# すべての出力
pulumi stack output

# 特定の出力
pulumi stack output vpcId

# JSON形式
pulumi stack output --json
```

#### 6. リソースの削除

```bash
# プレビュー
pulumi destroy --preview

# 実行
pulumi destroy -y
```

### 環境別の管理

```bash
# 開発環境
pulumi stack select dev
pulumi up

# ステージング環境
pulumi stack select staging
pulumi up

# 本番環境
pulumi stack select production
pulumi up --confirm
```

### S3バックエンドの使用

```bash
# S3バックエンドへのログイン
pulumi login s3://your-pulumi-state-bucket

# または環境変数で指定
export PULUMI_BACKEND_URL=s3://your-pulumi-state-bucket
```

## 開発ガイドライン

### プロジェクト構造

#### 基本的なindex.ts構造

```typescript
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// 環境名の取得
const environment = pulumi.getStack();
const config = new pulumi.Config();

// SSMパラメータの参照
const ssmPrefix = `/jenkins-infra/${environment}`;
const projectNameParam = await aws.ssm.getParameter({
    name: `${ssmPrefix}/config/project-name`,
});

// リソースの作成
const vpc = new aws.ec2.Vpc("main", {
    cidrBlock: "10.0.0.0/16",
    enableDnsHostnames: true,
    enableDnsSupport: true,
    tags: {
        Name: pulumi.interpolate`${projectName}-vpc-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
    },
});

// 出力のエクスポート
export const vpcId = vpc.id;
export const vpcCidr = vpc.cidrBlock;
```

### コーディング規約

#### 1. SSMパラメータの活用

```typescript
// ✅ 良い例：SSMから設定を取得
const environment = pulumi.getStack();
const ssmPrefix = `/jenkins-infra/${environment}`;
const projectNameParam = await aws.ssm.getParameter({
    name: `${ssmPrefix}/config/project-name`,
});
const projectName = projectNameParam.value;

// ❌ 悪い例：ハードコーディング
const projectName = "jenkins-project";
```

#### 2. リソースタグの統一

```typescript
// 共通タグの定義
const commonTags = {
    Environment: environment,
    ManagedBy: "pulumi",
    Project: projectName,
    CreatedAt: new Date().toISOString(),
};

// すべてのリソースに適用
const resource = new aws.ec2.Instance("example", {
    // ... 他の設定
    tags: {
        ...commonTags,
        Name: pulumi.interpolate`${projectName}-instance-${environment}`,
        Type: "web-server",
    },
});
```

#### 3. スタック間の参照

```typescript
// 他スタックの出力を参照
const networkStack = new pulumi.StackReference(
    `organization/jenkins-network/${environment}`
);
const vpcId = networkStack.getOutput("vpcId");
const privateSubnetIds = networkStack.getOutput("privateSubnetIds");

// 参照した値の使用
const instance = new aws.ec2.Instance("app", {
    subnetId: privateSubnetIds[0],
    // ... 他の設定
});
```

#### 4. エラーハンドリング

```typescript
// 非同期操作の適切な処理
const securityGroup = pulumi.output(vpcId).apply(async (id) => {
    if (!id) {
        throw new Error("VPC ID is required");
    }
    
    return new aws.ec2.SecurityGroup("app", {
        vpcId: id,
        // ... 他の設定
    });
});

// リソース削除時の依存関係
const database = new aws.rds.Instance("db", {
    // ... 設定
    skipFinalSnapshot: true, // 削除時のスナップショットをスキップ
}, {
    dependsOn: [securityGroup], // 明示的な依存関係
});
```

### ベストプラクティス

#### 1. 設定の外部化

```typescript
// Pulumi.yaml で設定スキーマを定義
const config = new pulumi.Config();
const instanceType = config.get("instanceType") || "t3.medium";
const volumeSize = config.getNumber("volumeSize") || 100;
const enableMonitoring = config.getBoolean("enableMonitoring") ?? false;
```

#### 2. コンポーネントリソースの活用

```typescript
// 再利用可能なコンポーネントクラス
class WebServerComponent extends pulumi.ComponentResource {
    public readonly instance: aws.ec2.Instance;
    public readonly securityGroup: aws.ec2.SecurityGroup;
    
    constructor(name: string, args: WebServerArgs, opts?: pulumi.ComponentResourceOptions) {
        super("custom:app:WebServer", name, {}, opts);
        
        // リソースの作成
        this.securityGroup = new aws.ec2.SecurityGroup(`${name}-sg`, {
            // ... 設定
        }, { parent: this });
        
        this.instance = new aws.ec2.Instance(`${name}-instance`, {
            // ... 設定
        }, { parent: this });
    }
}
```

#### 3. 出力の適切な管理

```typescript
// 構造化された出力
export const outputs = {
    network: {
        vpcId: vpc.id,
        publicSubnetIds: publicSubnets.map(s => s.id),
        privateSubnetIds: privateSubnets.map(s => s.id),
    },
    loadBalancer: {
        dnsName: alb.dnsName,
        zoneId: alb.zoneId,
    },
};

// SSMパラメータへの出力保存
const vpcIdParameter = new aws.ssm.Parameter("vpc-id", {
    name: `${ssmPrefix}/network/vpc-id`,
    type: "String",
    value: vpc.id,
});
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. Pulumi認証エラー

```bash
# エラー: error: getting secrets manager: passphrase must be set
# 解決方法:
export PULUMI_CONFIG_PASSPHRASE=your-passphrase

# または設定ファイルで永続化
pulumi config set --secret encryptionPassphrase your-passphrase
```

#### 2. S3バックエンドアクセスエラー

```bash
# エラー: error: failed to get bucket location
# 解決方法: バケットが存在し、適切な権限があることを確認
aws s3 ls s3://your-pulumi-state-bucket/

# IAMポリシーの確認
aws iam get-user-policy --user-name your-user --policy-name s3-access
```

#### 3. スタックが見つからない

```bash
# エラー: error: no stack named 'dev' found
# 解決方法: スタックを初期化
pulumi stack init dev

# 既存スタックの一覧表示
pulumi stack ls
```

#### 4. リソースの依存関係エラー

```bash
# エラー: error: resource depends on resource that is not in the stack
# 解決方法: 依存スタックが先にデプロイされていることを確認

# 依存関係の確認
pulumi stack graph

# 正しい順序でデプロイ
cd ../jenkins-network && pulumi up -y
cd ../jenkins-security && pulumi up -y
```

#### 5. 型エラー（TypeScript）

```bash
# エラー: TSError: ⨯ Unable to compile TypeScript
# 解決方法: TypeScriptの設定とタイプ定義を確認

# 依存関係の再インストール
rm -rf node_modules package-lock.json
npm install

# TypeScriptコンパイルチェック
npx tsc --noEmit
```

### デバッグ方法

```bash
# 詳細ログの有効化
export PULUMI_DEBUG=true
pulumi up --logtostderr -v=9 2> debug.log

# 特定のリソースのみ更新
pulumi up --target="aws:ec2/instance:Instance::web-server"

# スタック状態の確認
pulumi stack --show-ids
pulumi stack export > stack-state.json

# リフレッシュ（実際のリソース状態と同期）
pulumi refresh -y

# スタックのインポート（災害復旧）
pulumi stack import --file=stack-backup.json
```

### パフォーマンス最適化

#### 1. 大規模スタックの分割

```typescript
// ❌ 悪い例：単一の巨大スタック
// 1000以上のリソースを単一スタックで管理

// ✅ 良い例：論理的な単位で分割
// network スタック: VPC、サブネット
// security スタック: セキュリティグループ、IAM
// compute スタック: EC2、Auto Scaling
```

#### 2. 並列実行の最適化

```bash
# デフォルトは無制限の並列実行
# リソースが多い場合は制限を設定
pulumi up --parallel 10

# または設定ファイルで指定
pulumi config set --path 'pulumi:parallel' 10
```

#### 3. 不要なリフレッシュの回避

```bash
# リフレッシュをスキップ（注意して使用）
pulumi up --skip-refresh

# 特定のリソースのみリフレッシュ
pulumi refresh --target="aws:s3/bucket:Bucket::my-bucket"
```

## CI/CD統合

### Jenkins Pipeline統合例

```groovy
pipeline {
    agent any
    
    environment {
        PULUMI_CONFIG_PASSPHRASE = credentials('pulumi-passphrase')
        AWS_REGION = 'ap-northeast-1'
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'npm install -g pulumi'
            }
        }
        
        stage('Deploy') {
            steps {
                dir('pulumi/jenkins-network') {
                    sh '''
                        npm install
                        pulumi stack select dev
                        pulumi up -y
                    '''
                }
            }
        }
    }
}
```

## リソース命名規則

```
{project-name}-{component}-{resource-type}-{environment}

例:
jenkins-infra-vpc-dev
jenkins-infra-controller-ec2-prod
lambda-functions-api-gateway-staging
```

## セキュリティベストプラクティス

### 1. 機密情報の管理

```typescript
// ✅ 良い例：Pulumi Secretsを使用
const dbPassword = config.requireSecret("dbPassword");

// ✅ 良い例：SSM SecureStringを使用
const password = new aws.ssm.Parameter("password", {
    type: "SecureString",
    value: dbPassword,
});

// ❌ 悪い例：平文でハードコード
const dbPassword = "mypassword123";
```

### 2. IAMロールの最小権限

```typescript
const role = new aws.iam.Role("app", {
    assumeRolePolicy: aws.iam.assumeRolePolicyForPrincipal({
        Service: "ec2.amazonaws.com",
    }),
});

// 必要最小限の権限のみ付与
const policy = new aws.iam.RolePolicy("app-policy", {
    role: role.id,
    policy: pulumi.output({
        Version: "2012-10-17",
        Statement: [{
            Effect: "Allow",
            Action: ["s3:GetObject"],
            Resource: ["arn:aws:s3:::my-bucket/*"],
        }],
    }),
});
```

### 3. ネットワークセキュリティ

```typescript
// プライベートサブネットの使用
const privateSubnet = new aws.ec2.Subnet("private", {
    vpcId: vpc.id,
    cidrBlock: "10.0.1.0/24",
    mapPublicIpOnLaunch: false, // パブリックIPを割り当てない
});

// セキュリティグループの厳格な設定
const sg = new aws.ec2.SecurityGroup("app", {
    vpcId: vpc.id,
    ingress: [{
        protocol: "tcp",
        fromPort: 443,
        toPort: 443,
        cidrBlocks: ["10.0.0.0/16"], // 内部ネットワークのみ
    }],
    egress: [{
        protocol: "-1",
        fromPort: 0,
        toPort: 0,
        cidrBlocks: ["0.0.0.0/0"],
    }],
});
```

## 関連ドキュメント

- [メインREADME](../README.md) - プロジェクト全体の概要
- [Ansible README](../ansible/README.md) - Ansibleプレイブックとの連携
- [Jenkins README](../jenkins/README.md) - Jenkins設定の詳細
- [CLAUDE.md](../CLAUDE.md) - 開発者向けガイドライン
- [Pulumi公式ドキュメント](https://www.pulumi.com/docs/)

## サポート

問題が発生した場合は、以下を確認してください：

1. このREADMEのトラブルシューティングセクション
2. 各スタックのindex.tsのコメント
3. [Pulumi公式ドキュメント](https://www.pulumi.com/docs/)
4. [AWS公式ドキュメント](https://docs.aws.amazon.com/)

## ライセンス

このプロジェクトは内部利用を目的としています。詳細は[LICENSE](../LICENSE)を参照してください。