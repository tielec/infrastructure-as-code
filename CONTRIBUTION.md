# Infrastructure as Code 開発ガイドライン

このドキュメントは、Infrastructure as Codeプロジェクト全体の開発ガイドラインと統一規約をまとめたものです。

## 📋 目次

- [プロジェクト概要](#プロジェクト概要)
- [開発環境セットアップ](#開発環境セットアップ)
- [コーディング規約](#コーディング規約)
- [コンポーネント別ガイド](#コンポーネント別ガイド)
- [セキュリティガイドライン](#セキュリティガイドライン)
- [コントリビューション手順](#コントリビューション手順)
- [トラブルシューティング](#トラブルシューティング)

## プロジェクト概要

### ディレクトリ構造

```
infrastructure-as-code/
├── ansible/              # オーケストレーション層
│   ├── inventory/        # インベントリと変数定義
│   ├── playbooks/        # 実行可能なプレイブック
│   └── roles/           # 再利用可能なロール
├── bootstrap/           # 初期セットアップ（CloudFormation）
├── docs/                # プロジェクトドキュメント（詳細手順）
│   ├── setup/           # セットアップ関連
│   ├── operations/      # 運用関連
│   ├── architecture/    # アーキテクチャ関連
│   └── development/     # 開発関連
├── jenkins/             # Jenkins設定とジョブ定義
│   ├── config/          # Jenkins設定ファイル
│   └── jobs/           # ジョブ定義（DSL/Pipeline）
├── lambda/              # Lambda関数実装
├── pulumi/              # インフラストラクチャ定義
│   ├── jenkins-*/       # Jenkinsコンポーネント
│   └── lambda-*/        # Lambdaコンポーネント
└── scripts/             # ヘルパースクリプト
    ├── aws/            # AWS関連スクリプト
    └── jenkins/        # Jenkins関連スクリプト
```

### 技術スタック

- **インフラ定義**: Pulumi (TypeScript)
- **オーケストレーション**: Ansible
- **CI/CD**: Jenkins (DSL/Pipeline as Code)
- **クラウドプロバイダー**: AWS
- **言語**: TypeScript, Python, Groovy, Bash

## 開発環境セットアップ

### 必要なツール

```bash
# Node.js/npm
node --version  # v18以上
npm --version   # v8以上

# Python/pip
python3 --version  # 3.8以上
pip3 --version

# Ansible
ansible --version  # 2.9以上

# Pulumi
pulumi version  # 3.0以上

# AWS CLI
aws --version  # 2.0以上
```

### 初期設定

```bash
# リポジトリクローン
git clone <repository-url>
cd infrastructure-as-code

# AWS認証設定
aws configure

# Pulumi設定
pulumi login

# Ansible設定
export ANSIBLE_HOST_KEY_CHECKING=False
```

## コーディング規約

### 命名規則

| 種別 | 規約 | 例 |
|------|------|-----|
| ファイル名（YAML） | kebab-case | `jenkins-network.yml` |
| ファイル名（TypeScript） | camelCase | `index.ts`, `utils.ts` |
| 変数名（YAML） | snake_case | `project_name`, `aws_region` |
| 変数名（TypeScript） | camelCase | `projectName`, `awsRegion` |
| リソース名（AWS） | kebab-case | `jenkins-vpc-dev` |
| 環境変数 | UPPER_SNAKE | `AWS_REGION`, `PROJECT_NAME` |

### コミットメッセージ

```
[Component] Action: 詳細な説明

Component: pulumi|ansible|jenkins|bootstrap|scripts|docs
Action: add|update|fix|remove|refactor

例:
[pulumi] add: Lambda関数用の新しいスタックを追加
[ansible] fix: jenkins_controllerロールのエラー処理を修正
[jenkins] update: ビルドパイプラインのタイムアウト設定を変更
```

### コメント規約

すべてのソースファイルには以下の情報を含むヘッダーを記載：

```
ファイルパス
目的・機能の説明
主要な依存関係
作成日・更新日（オプション）
```

## コンポーネント別ガイド

各コンポーネントの詳細な開発規約は、それぞれのCONTRIBUTION.mdを参照してください：

### Pulumi開発

詳細は [pulumi/CONTRIBUTION.md](pulumi/CONTRIBUTION.md) を参照。

#### 主要な規約

- **スタック名**: `{system}-{component}` (例: jenkins-network)
- **リソース名**: `${projectName}-{resource}-${environment}`
- **必須タグ**: Name, Environment, ManagedBy, Project
- **エクスポート**: ID, ARN, エンドポイントを必ず含める

### Ansible開発

詳細は [ansible/CONTRIBUTION.md](ansible/CONTRIBUTION.md) を参照。

#### 主要な規約

- **プレイブック名**: `{action}_{component}_{target}.yml`
- **ロール名**: `{component}_{function}`
- **変数管理**: グローバル → 環境別 → ロール → プレイブック
- **ヘルパーロール**: aws_cli_helper, ssm_parameter_store, pulumi_helperを活用

### Jenkins開発

詳細は [jenkins/CONTRIBUTION.md](jenkins/CONTRIBUTION.md) を参照。

#### 主要な規約

- **Job DSL**: `{Category}/{job-name}` 形式でフォルダー構造化
- **Pipeline**: Declarative Pipelineを推奨
- **共有ライブラリ**: src/とvars/に分離して管理
- **セキュリティ**: クレデンシャルはCredentials Storeで管理

## セキュリティガイドライン

### シークレット管理

- **SSMパラメータ名**: `/{project}/{environment}/{component}/{parameter}`
- **クレデンシャル**: Jenkins Credentials StoreまたはSSM SecureStringで管理
- **キーワード**: password, secret, key, token, credential, api_key, access_keyは自動検出

### IAMポリシー

- 最小権限の原則を適用
- 環境別にロールを分離
- MFAを本番環境で必須化
- クロスアカウントロールの最小化

### ネットワークセキュリティ

- プライベートサブネットの利用
- セキュリティグループの最小化
- NACLによる追加制御
- VPCフローログの有効化

### ログとモニタリング

- CloudWatch Logs
- VPC Flow Logs
- AWS CloudTrail
- Application Logs
- X-Ray Tracing

## コントリビューション手順

### ブランチ戦略

```
main           → 安定版（保護ブランチ）
develop        → 開発版
bug/*          → バグ修正
feature/*      → 機能開発
task/*         → タスク作業
hotfix/*       → 緊急修正（本番環境の重大な問題）
```

### ブランチ命名規則

```
{type}/issue-{番号}-{説明}

タイプはIssueテンプレートと対応:
- bug/      → [BUG] バグ報告
- feature/  → [FEATURE] 機能要望
- task/     → [TASK] タスク

例:
bug/issue-123-fix-memory-leak
feature/issue-456-add-monitoring
task/issue-789-update-documentation
```

### プルリクエスト

#### テンプレート

```markdown
## 概要
変更の概要を記載

## 主な変更内容
- [ ] 変更点1
- [ ] 変更点2

## テスト
- [ ] ローカルテスト実施
- [ ] dev環境デプロイ確認
- [ ] 既存機能への影響確認

## レビューポイント
レビュー時に特に確認してほしい点

## 関連Issue
#123
```

### レビュープロセス

1. セルフレビュー実施
2. プルリクエスト作成
3. CI/CDパイプライン通過確認
4. コードレビュー（最低1名）
5. 承認後マージ

### リリースプロセス

```bash
# バージョンタグ作成
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

## トラブルシューティング

### よくある問題と解決策

| エラー | 原因 | 解決方法 |
|--------|------|----------|
| Stack not found | スタック未作成 | 依存スタックを先にデプロイ |
| Permission denied | IAM権限不足 | 必要な権限を追加 |
| Resource limit | クォータ上限 | AWSサポートに上限緩和申請 |
| Invalid semantic version | バージョン形式エラー | X.Y.Z形式で指定（各部は整数） |
| IncludeRole retries error | include_roleでuntil使用 | shellモジュールでuntil/retries使用 |

### デバッグ方法

```bash
# Ansible詳細ログ
ansible-playbook playbook.yml -vvv

# Pulumi事前確認
pulumi preview --diff

# Jenkinsジョブコンソール
curl -u admin:password http://jenkins/job/JobName/lastBuild/consoleText
```

## 参考リンク

### コンポーネント別ドキュメント

- [Pulumi CONTRIBUTION](pulumi/CONTRIBUTION.md) - Pulumi開発詳細
- [Ansible CONTRIBUTION](ansible/CONTRIBUTION.md) - Ansible開発詳細
- [Jenkins CONTRIBUTION](jenkins/CONTRIBUTION.md) - Jenkins開発詳細

### 外部リソース

- [Pulumi Documentation](https://www.pulumi.com/docs/)
- [Ansible Documentation](https://docs.ansible.com/)
- [Jenkins Documentation](https://www.jenkins.io/doc/)
- [AWS Documentation](https://docs.aws.amazon.com/)

---

このガイドラインに従って開発を行うことで、一貫性があり保守性の高いインフラストラクチャコードを維持できます。