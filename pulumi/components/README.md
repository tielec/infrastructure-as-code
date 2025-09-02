# Pulumi Components 使用方法

このライブラリは、Pulumiプロジェクトで再利用可能なコンポーネントを提供します。

## インストール

### 方法1: 直接インストール
```bash
npm install ../components
```

### 方法2: package.jsonで自動インストール（推奨）
プロジェクトの`package.json`に以下を追加することで、`npm install`時に自動的にコンポーネントの依存関係もインストールされます：

```json
{
  "private": true,
  "dependencies": {
    "@tielec/pulumi-components": "file:../components"
  },
  "scripts": {
    "prepare": "cd ../components && npm install"
  }
}
```

この設定により：
- `npm install`実行時に自動的に`components`ディレクトリの依存関係もインストール
- Jenkinsパイプラインでの追加設定が不要
- `private: true`により誤ったnpm publishを防止

## コンポーネント

### 1. GitHubRepoCheckout

GitHubリポジトリをローカルにチェックアウトするコンポーネント。

#### 使用例

```typescript
import { GitHubRepoCheckout } from "@tielec/pulumi-components";

// パブリックリポジトリのチェックアウト
const repo = new GitHubRepoCheckout("my-repo", {
  repositoryUrl: "https://github.com/example/repo.git",
  branch: "main", // デフォルト: main
});

// プライベートリポジトリのチェックアウト
const privateRepo = new GitHubRepoCheckout("private-repo", {
  repositoryUrl: "https://github.com/example/private-repo.git",
  githubToken: config.requireSecret("githubToken"),
  branch: "develop",
});

// 特定のタグをチェックアウト
const taggedRepo = new GitHubRepoCheckout("tagged-repo", {
  repositoryUrl: "https://github.com/example/repo.git",
  tag: "v1.0.0",
});

// 特定のコミットをチェックアウト
const commitRepo = new GitHubRepoCheckout("commit-repo", {
  repositoryUrl: "https://github.com/example/repo.git",
  commit: "abc123def456",
});

// カスタム出力パスを指定
const customRepo = new GitHubRepoCheckout("custom-repo", {
  repositoryUrl: "https://github.com/example/repo.git",
  outputPath: "/tmp/my-custom-repo",
});

// チェックアウトしたリポジトリのパスを使用
export const repoPath = repo.localPath;
export const commitHash = repo.commitHash;
```

#### パラメータ

- `repositoryUrl` (必須): GitHubリポジトリのURL
- `branch` (オプション): チェックアウトするブランチ（デフォルト: main）
- `tag` (オプション): チェックアウトするタグ
- `commit` (オプション): チェックアウトするコミットハッシュ
- `outputPath` (オプション): リポジトリを保存するローカルパス
- `githubToken` (オプション): プライベートリポジトリ用のGitHubトークン

### 2. LambdaPackage

Lambda関数のコードをパッケージ化するコンポーネント。

#### 使用例

```typescript
import { LambdaPackage } from "@tielec/pulumi-components";
import * as aws from "@pulumi/aws";

// Node.js Lambda関数のパッケージング
const nodePackage = new LambdaPackage("node-lambda", {
  sourcePath: "./lambda-functions/api-handler",
  runtime: "nodejs18.x",
  installDependencies: true, // package.jsonから依存関係をインストール
});

// Python Lambda関数のパッケージング
const pythonPackage = new LambdaPackage("python-lambda", {
  sourcePath: "./lambda-functions/data-processor",
  runtime: "python3.11",
  installDependencies: true, // requirements.txtから依存関係をインストール
});

// ファイルの除外設定
const filteredPackage = new LambdaPackage("filtered-lambda", {
  sourcePath: "./lambda-functions/handler",
  excludePatterns: [
    "*.log",
    "temp/**",
    "docs/**",
  ],
  includePatterns: [
    "src/**",
    "package.json",
    "index.js",
  ],
});

// 追加ファイルを含める
const enrichedPackage = new LambdaPackage("enriched-lambda", {
  sourcePath: "./lambda-functions/handler",
  extraFiles: {
    ".env": "NODE_ENV=production",
    "config.json": JSON.stringify({
      apiUrl: "https://api.example.com",
      timeout: 30,
    }),
  },
});

// Lambda関数の作成
const lambdaFunction = new aws.lambda.Function("my-function", {
  code: nodePackage.createAsset(),
  handler: "index.handler",
  runtime: "nodejs18.x",
  role: lambdaRole.arn,
  sourceCodeHash: nodePackage.zipHash,
  environment: {
    variables: {
      NODE_ENV: "production",
    },
  },
});

// パッケージ情報の出力
export const packagePath = nodePackage.zipPath;
export const packageHash = nodePackage.zipHash;
export const packageSize = nodePackage.sizeBytes;
```

#### パラメータ

- `sourcePath` (必須): ソースコードのパス
- `runtime` (オプション): Lambdaランタイム（デフォルト: nodejs18.x）
- `installDependencies` (オプション): 依存関係をインストールするか（デフォルト: true）
- `excludePatterns` (オプション): 除外するファイルパターンの配列
- `includePatterns` (オプション): 含めるファイルパターンの配列（デフォルト: ["**"]）
- `outputPath` (オプション): ZIPファイルの出力パス
- `extraFiles` (オプション): 追加するファイルのマップ（キー: ファイルパス、値: 内容）

#### デフォルトで除外されるファイル

以下のファイル・フォルダは自動的に除外されます：

- `*.zip`
- `.git/**`
- `.gitignore`
- `.env*`
- テストファイル（`*.test.js`, `*.test.ts`, `*.spec.js`, `*.spec.ts`）
- テストフォルダ（`__tests__/**`, `test/**`, `tests/**`）
- カバレッジ（`coverage/**`, `.nyc_output/**`）
- IDEフォルダ（`.vscode/**`, `.idea/**`）
- ソースマップ（`*.map`）
- 設定ファイル（`tsconfig.json`, `package-lock.json`, `yarn.lock`）

### 3. LambdaDeploymentBucket

Lambda関数のデプロイメントパッケージを管理するS3バケット。新規作成と既存バケットの参照の両方に対応。

**重要**: 通常は事前に作成された共有バケットを使用することを推奨します。

#### 使用例

```typescript
import { 
  LambdaDeploymentBucket,
  LambdaPackage 
} from "@tielec/pulumi-components";
import * as aws from "@pulumi/aws";

// 方法1: 既存の共有バケットを使用（デフォルト）
const deploymentBucket = new LambdaDeploymentBucket("deployment", {
  bucketName: "tielec-lambda-shipment-prod",
  // useExisting: true がデフォルト
});

// Lambdaパッケージを作成してS3にアップロード
const lambdaPackage = new LambdaPackage("api-handler", {
  sourcePath: "./lambda-functions/api",
  runtime: "nodejs18.x",
  installDependencies: true,
});

// S3にアップロード
const s3Object = deploymentBucket.uploadLambdaPackage(
  "api-handler",
  lambdaPackage.zipPath,
  lambdaPackage.zipHash,
  { project: "my-project" }
);

// S3からLambda関数をデプロイ
const lambdaFunction = new aws.lambda.Function("api-function", {
  s3Bucket: deploymentBucket.bucketName,
  s3Key: s3Object.key,
  handler: "index.handler",
  runtime: "nodejs18.x",
  role: lambdaRole.arn,
  sourceCodeHash: lambdaPackage.zipHash,
});

// 複数のLambda関数を一つのバケットで管理
const functions = ["api", "worker", "scheduler"];

functions.forEach((funcName) => {
  const pkg = new LambdaPackage(`${funcName}-package`, {
    sourcePath: `./lambda-functions/${funcName}`,
    runtime: "nodejs18.x",
  });

  const s3Obj = deploymentBucket.uploadLambdaPackage(
    funcName,
    pkg.zipPath,
    pkg.zipHash
  );

  new aws.lambda.Function(funcName, {
    s3Bucket: deploymentBucket.bucketName,
    s3Key: s3Obj.key,
    handler: "index.handler",
    runtime: "nodejs18.x",
    role: lambdaRole.arn,
    sourceCodeHash: pkg.zipHash,
  });
});

// 方法2: 新規バケットを作成（特別な要件がある場合のみ）
const customBucket = new LambdaDeploymentBucket("custom-deployment", {
  useExisting: false,  // 新規作成を明示的に指定
  bucketName: "tielec-lambda-shipment-custom", 
  lifecycleDays: 7,  // デフォルト: 7日
  versioning: true,
  tags: {
    Environment: "dev",
  },
});
```

#### パラメータ

- `useExisting` (オプション): 既存バケットを参照する場合はtrue、新規作成する場合はfalse（デフォルト: true）
- `bucketName` (オプション/必須): バケット名
  - 既存バケット参照時（デフォルト）は必須
  - 新規作成時はオプション（デフォルト: `tielec-lambda-shipment-{name}`）
- `lifecycleDays` (オプション): 古いバージョンを削除するまでの日数（デフォルト: 7）※新規作成時のみ
- `versioning` (オプション): バージョニングを有効にするか（デフォルト: true）※新規作成時のみ
- `tags` (オプション): バケットに付与するタグ ※新規作成時のみ

#### 機能

- **自動セキュリティ設定**
  - プライベートACL
  - パブリックアクセスブロック
  - AES256暗号化

- **ライフサイクル管理**
  - 古いバージョンの自動削除
  - 不完全なマルチパートアップロードのクリーンアップ

- **メタデータ管理**
  - パッケージハッシュの記録
  - アップロード時刻の記録
  - ランタイム情報の記録

## 実装例

### GitHubリポジトリからLambda関数をS3経由でデプロイ

```typescript
import { 
  GitHubRepoCheckout, 
  LambdaPackage,
  LambdaDeploymentBucket 
} from "@tielec/pulumi-components";
import * as aws from "@pulumi/aws";

// 既存の共有バケットを使用（デフォルト）
const deploymentBucket = new LambdaDeploymentBucket("deployment", {
  bucketName: "tielec-lambda-shipment-prod",
});

// GitHubからコードをチェックアウト
const lambdaRepo = new GitHubRepoCheckout("lambda-repo", {
  repositoryUrl: "https://github.com/myorg/lambda-functions.git",
  branch: "main",
  githubToken: config.requireSecret("githubToken"),
});

// チェックアウトしたコードをパッケージ化
const lambdaPackage = new LambdaPackage("lambda-package", {
  sourcePath: pulumi.interpolate`${lambdaRepo.localPath}/api-handler`,
  runtime: "nodejs18.x",
  installDependencies: true,
});

// S3にアップロード
const s3Object = deploymentBucket.uploadLambdaPackage(
  "api-handler",
  lambdaPackage.zipPath,
  lambdaPackage.zipHash
);

// Lambda関数を作成（S3から）
const apiFunction = new aws.lambda.Function("api-function", {
  s3Bucket: deploymentBucket.bucketName,
  s3Key: s3Object.key,
  handler: "index.handler",
  runtime: "nodejs18.x",
  role: lambdaRole.arn,
  sourceCodeHash: lambdaPackage.zipHash,
  timeout: 30,
  memorySize: 256,
});
```

### 複数のLambda関数を一括デプロイ

```typescript
import { LambdaPackage } from "@tielec/pulumi-components";
import * as aws from "@pulumi/aws";

const lambdaFunctions = [
  { name: "api-handler", path: "./functions/api" },
  { name: "data-processor", path: "./functions/processor" },
  { name: "notification", path: "./functions/notification" },
];

lambdaFunctions.forEach(({ name, path }) => {
  const package = new LambdaPackage(`${name}-package`, {
    sourcePath: path,
    runtime: "nodejs18.x",
    installDependencies: true,
  });

  new aws.lambda.Function(name, {
    code: package.createAsset(),
    handler: "index.handler",
    runtime: "nodejs18.x",
    role: lambdaRole.arn,
    sourceCodeHash: package.zipHash,
  });
});
```

## トラブルシューティング

### GitHubRepoCheckout

**問題**: プライベートリポジトリへのアクセスが失敗する
- **解決策**: GitHubトークンが正しく設定されているか確認してください
- Personal Access Token (PAT) に必要な権限があるか確認してください

**問題**: チェックアウトに時間がかかる
- **解決策**: デフォルトでは浅いクローン（depth=1）を使用しています
- 必要に応じて、キャッシュディレクトリ（`.pulumi/repos/`）を削除してください

### LambdaPackage

**問題**: パッケージサイズが大きすぎる
- **解決策**: `excludePatterns`を使用して不要なファイルを除外してください
- node_modulesの中の開発依存関係が含まれていないか確認してください

**問題**: 依存関係のインストールが失敗する
- **解決策**: `npm ci`が失敗する場合、自動的に`npm install`にフォールバックします
- プライベートレジストリを使用している場合は、適切な認証情報を設定してください

## ベストプラクティス

1. **GitHubトークンの管理**: Pulumi ConfigやAWS Secrets Managerを使用してトークンを安全に管理
2. **パッケージの最適化**: 本番環境では開発依存関係を除外し、最小限のファイルのみを含める
3. **キャッシング**: リポジトリとパッケージは自動的にキャッシュされるため、再実行が高速化される
4. **バージョン管理**: タグやコミットハッシュを使用して、デプロイするコードのバージョンを固定する