# CLAUDE.md

このファイルは、このリポジトリでコードを扱う際のClaude Code (claude.ai/code) へのガイダンスを提供します。

## プロジェクト概要

包括的なJenkins CI/CDインフラ自動化プロジェクトで、ブートストラップにCloudFormation、インフラプロビジョニングにPulumi (TypeScript)、オーケストレーションにAnsibleを使用しています。ブルーグリーンデプロイメント機能、自動スケーリングエージェント、高可用性機能を備えた本番環境対応のJenkins環境をAWS上にデプロイします。

## コーディングガイドライン

### 基本原則
- **思考**: 技術的な内容は英語、プロジェクト固有の内容は日本語で柔軟に思考
- **対話**: 日本語で対話 (Dialogue in Japanese with users)
- **ドキュメント**: 日本語で記述 (Documentation in Japanese)
- **コメント**: ソースコード内のコメントは日本語
- **README/ドキュメント**: すべて日本語で記述

### 重要な注意事項
- **Bootstrap修正時**: `bootstrap/` ディレクトリ内のファイルを修正した場合、必ずREADME.mdの更新が必要かチェックすること
- **依存関係の順序**: コンポーネント間の依存関係を常に意識し、デプロイ/削除順序を守ること
- **環境分離**: dev/staging/production環境を明確に分離すること

## Pulumiベストプラクティス

**Pulumiスタックの使用方法については [pulumi/README.md](pulumi/README.md) を参照してください。**
**開発者向けの詳細な実装方法は [pulumi/CONTRIBUTION.md](pulumi/CONTRIBUTION.md) を参照してください。**

### 重要な注意事項

- **Pulumi開発時**: Pulumiスタックを修正・追加した場合、必ず `pulumi/README.md` の更新が必要かチェックすること
- **ドキュメント更新対象**:
  - 新しいスタックの追加
  - スタック間の依存関係変更
  - 設定パラメータの変更
  - コーディング規約の追加
  - トラブルシューティング情報の追加

## Jenkinsベストプラクティス

**Jenkinsの設定、Job DSL、パイプライン、共有ライブラリについては [jenkins/README.md](jenkins/README.md) を参照してください。**
**開発者向けの詳細な実装方法は [jenkins/CONTRIBUTION.md](jenkins/CONTRIBUTION.md) を参照してください。**

### 重要な注意事項

- **Jenkins開発時**: Jenkins設定、ジョブ定義、パイプラインを修正・追加した場合、必ず `jenkins/README.md` の更新が必要かチェックすること
- **ドキュメント更新対象**:
  - 新しいジョブの追加
  - パイプラインの変更
  - 共有ライブラリの追加・変更
  - プラグインの変更
  - セキュリティ設定の変更
  - トラブルシューティング情報の追加

### ⚠️ Jenkinsパラメータ定義ルール

**重要**: Jenkinsfileでのパラメータ定義は禁止です。パラメータは必ずJob DSLファイルで定義してください。

```groovy
// ✅ 正しい: DSLファイルでパラメータ定義
pipelineJob(jobName) {
    parameters {
        stringParam('VERSION', '1.0.0', 'バージョン')
        choiceParam('ENV', ['dev', 'staging', 'prod'], '環境')
    }
}

// ❌ 間違い: Jenkinsfileでパラメータ定義
pipeline {
    parameters {  // 禁止！初回実行時に問題が発生
        string(name: 'VERSION', defaultValue: '1.0.0')
    }
}
```

詳細は [jenkins/CONTRIBUTION.md#重要-パラメータ定義のルール](jenkins/CONTRIBUTION.md#重要-パラメータ定義のルール) を参照。

## Ansibleベストプラクティス

**Ansibleプレイブックの開発・使用方法については [ansible/README.md](ansible/README.md) を参照してください。**
**開発者向けの詳細な実装方法は [ansible/CONTRIBUTION.md](ansible/CONTRIBUTION.md) を参照してください。**

### 重要な注意事項

- **Ansible開発時**: Ansibleプレイブックやロールを修正・追加した場合、必ず `ansible/README.md` の更新が必要かチェックすること
- **ドキュメント更新対象**:
  - 新しいプレイブックの追加
  - 新しいロールの追加
  - パラメータ変更
  - 依存関係の変更
  - 実行手順の変更
  - トラブルシューティング情報の追加
- **ヘルパーロールの活用**: `pulumi_helper`、`ssm_parameter_store`、`aws_cli_helper`、`aws_setup`を積極的に使用すること
- **meta/main.yml必須**: ヘルパーロールを使用する場合は、必ず`meta/main.yml`に依存関係を定義すること

## デプロイメントアーキテクチャ

**各システムのコンポーネント依存関係やデプロイ順序については [ansible/README.md#デプロイメントアーキテクチャ](ansible/README.md#デプロイメントアーキテクチャ) を参照してください。**

### 一般的なデプロイ原則

1. **初期化**: SSMパラメータの準備
2. **基盤**: ネットワーク → セキュリティ
3. **インフラ**: ストレージ、ロードバランサー等
4. **コンピュート**: EC2、Lambda等
5. **アプリケーション**: 設定、デプロイ

### 削除原則

削除は常にデプロイの逆順で実行すること。

## 開発ワークフロー

### ⚠️ 開発開始前の必須確認事項

**重要**: 開発を開始する前に、必ず対応するCONTRIBUTION.mdを確認してください。
- **Ansible開発**: `ansible/CONTRIBUTION.md` を必ず確認
- **Pulumi開発**: `pulumi/CONTRIBUTION.md` を必ず確認
- **Jenkins開発**: `jenkins/CONTRIBUTION.md` を必ず確認
- **スクリプト開発**: `scripts/CONTRIBUTION.md` を必ず確認

これらのドキュメントには、実装方法、コーディング規約、ベストプラクティスが記載されています。

### 1. 新機能追加時（Pulumiスタック）
```bash
# 0. 開発前にCONTRIBUTION.mdを確認 ⚠️ 必須
cat pulumi/CONTRIBUTION.md

# 1. Pulumiスタック作成
cd pulumi
mkdir {system}-{new-component}
cd {system}-{new-component}
pulumi new aws-typescript

# 2. デプロイテスト
npm run preview

# 3. Ansibleプレイブック統合
# ansible/README.mdの手順を参照
```

### 2. 既存コンポーネント修正時
```bash
# 0. 開発前にCONTRIBUTION.mdを確認 ⚠️ 必須
cat pulumi/CONTRIBUTION.md

# 1. 変更の影響範囲を確認
cd pulumi/{component}
npm run preview

# 2. デプロイテスト
# ansible/README.mdの手順を参照

# 3. 依存コンポーネントも更新
# 依存関係図を参照して下流コンポーネントを特定
```

### 3. Bootstrap環境の更新時
```bash
# 1. CloudFormationテンプレート更新
vi bootstrap/cfn-bootstrap-template.yaml

# 2. セットアップスクリプト更新
vi bootstrap/setup-bootstrap.sh

# 3. README.md更新確認 ⚠️ 重要
# - 新しいパラメータの説明追加
# - 手順の変更を反映
# - トラブルシューティング情報の更新
vi README.md

# 4. スタック更新（AWSコンソール）
# InstanceVersionパラメータを変更して再作成
```

### 4. Ansible開発時
```bash
# 0. 開発前にCONTRIBUTION.mdを確認 ⚠️ 必須
cat ansible/CONTRIBUTION.md

# 1. プレイブック・ロールの開発
cd ansible
# 開発作業を実施

# 2. ヘルパーロール使用時は meta/main.yml に依存関係を追加
vi roles/your_role/meta/main.yml
# dependencies:
#   - pulumi_helper
#   - ssm_parameter_store

# 3. ansible/README.md更新確認 ⚠️ 重要
# 以下の項目で更新が必要か確認：
# - プレイブック一覧（新規追加・変更）
# - ロール一覧（新規追加・変更）
# - パラメータ説明（追加・変更）
# - 実行例（新規・変更）
# - 依存関係図（変更があれば）
# - トラブルシューティング（新規問題）
vi ansible/README.md

# 4. ansible/CONTRIBUTION.md更新確認
# 開発者向けガイドラインの追加・変更があれば更新
vi ansible/CONTRIBUTION.md
```

### 5. Pulumi開発時
```bash
# 0. 開発前にCONTRIBUTION.mdを確認 ⚠️ 必須
cat pulumi/CONTRIBUTION.md

# 1. Pulumiスタックの開発
cd pulumi
# 開発作業を実施

# 2. pulumi/README.md更新確認 ⚠️ 重要
# 以下の項目で更新が必要か確認：
# - スタック一覧（新規追加・変更）
# - 依存関係（スタック間の参照変更）
# - 設定パラメータ（追加・変更）
# - 使用方法（新規コマンド・手順）
# - トラブルシューティング（新規問題）
vi pulumi/README.md

# 3. pulumi/CONTRIBUTION.md更新確認
# 開発者向けガイドラインの追加・変更があれば更新
vi pulumi/CONTRIBUTION.md
```

### 6. Jenkins開発時
```bash
# 0. 開発前にCONTRIBUTION.mdを確認 ⚠️ 必須
cat jenkins/CONTRIBUTION.md

# 1. 新規ジョブ作成の場合
# a. job-config.yamlにジョブ定義を追加
vi jenkins/jobs/pipeline/_seed/job-creator/job-config.yaml

# b. DSLファイルを作成（パラメータは必ずここで定義）
vi jenkins/jobs/dsl/category/your_job.groovy

# c. Jenkinsfileを作成（パラメータ定義は禁止）
vi jenkins/jobs/pipeline/category/your-job/Jenkinsfile

# d. シードジョブを実行
# Jenkins UI: Admin_Jobs/job-creator を実行

# 2. jenkins/README.md更新確認 ⚠️ 重要
# 以下の項目で更新が必要か確認：
# - ジョブ一覧（新規追加・変更）
# - パイプライン（新規・変更）
# - 共有ライブラリ（追加・変更）
# - プラグイン一覧（追加・削除）
# - 設定変更（JCasC、Groovyスクリプト）
# - トラブルシューティング（新規問題）
vi jenkins/README.md

# 3. jenkins/CONTRIBUTION.md更新確認
# 開発者向けガイドラインの追加・変更があれば更新
vi jenkins/CONTRIBUTION.md
```

### 7. スクリプト開発時
```bash
# 0. 開発前にCONTRIBUTION.mdを確認 ⚠️ 必須
cat scripts/CONTRIBUTION.md

# 1. 新規スクリプト作成の場合
# a. スクリプトファイルを作成
vi scripts/{category}/{action}-{target}.sh

# b. ヘッダーコメントテンプレートを記載
# scripts/CONTRIBUTION.mdのテンプレートを参照

# c. ShellCheckで検証
shellcheck scripts/{category}/*.sh

# 2. scripts/README.md更新確認 ⚠️ 重要
# 以下の項目で更新が必要か確認：
# - スクリプト一覧（新規追加・変更）
# - 使用方法（パラメータ・オプション変更）
# - 環境変数（追加・変更）
# - 依存関係（他スクリプトとの連携）
# - セキュリティ設定（権限・認証）
# - トラブルシューティング（新規問題）
vi scripts/README.md

# 3. scripts/CONTRIBUTION.md更新確認
# 開発者向けガイドラインの追加・変更があれば更新
vi scripts/CONTRIBUTION.md
```

## トラブルシューティングガイド

### Pulumi関連

**詳細なトラブルシューティング方法は [pulumi/README.md#トラブルシューティング](pulumi/README.md#トラブルシューティング) を参照してください。**

### Ansible関連

**詳細なトラブルシューティング方法は [ansible/README.md#トラブルシューティング](ansible/README.md#トラブルシューティング) を参照してください。**

### Jenkins関連

**詳細なトラブルシューティング方法は [jenkins/README.md#トラブルシューティング](jenkins/README.md#トラブルシューティング) を参照してください。**

### スクリプト関連

**詳細なトラブルシューティング方法は [scripts/README.md#トラブルシューティング](scripts/README.md#トラブルシューティング) を参照してください。**

## コミットメッセージ規約

```
[Component] Action: 詳細な説明

Component: pulumi|ansible|jenkins|bootstrap|scripts|docs
Action: add|update|fix|remove|refactor

例:
[pulumi] add: Lambda関数用の新しいスタックを追加
[ansible] fix: jenkins_controllerロールのエラー処理を修正
[bootstrap] update: Node.js v20へアップグレード（README更新含む）
```

### Gitコミット時の注意事項

**重要**: Gitコミットを作成する際は、Co-Authorにクレジットを追加しないでください。コミットメッセージは簡潔にし、変更内容のみを記載してください。

## セキュリティチェックリスト

- [ ] クレデンシャルのハードコーディングなし
- [ ] SSMパラメータはSecureString使用
- [ ] IAMロールは最小権限の原則
- [ ] セキュリティグループは必要最小限のポート開放
- [ ] ログに機密情報を出力しない
- [ ] APIキーは環境変数またはSSMで管理

## パフォーマンス最適化

### Pulumi

**Pulumiのパフォーマンス最適化については [pulumi/CONTRIBUTION.md](pulumi/CONTRIBUTION.md) を参照してください。**

### Ansible

**Ansibleのパフォーマンス最適化については [ansible/CONTRIBUTION.md#ベストプラクティス](ansible/CONTRIBUTION.md#ベストプラクティス) を参照してください。**

### Jenkins

**Jenkinsのパフォーマンス最適化については [jenkins/CONTRIBUTION.md#ベストプラクティス](jenkins/CONTRIBUTION.md#ベストプラクティス) を参照してください。**

## リソース命名規則

```
{project-name}-{component}-{resource-type}-{environment}

例:
jenkins-infra-vpc-dev
jenkins-infra-controller-ec2-prod
jenkins-infra-efs-staging
```

## 環境変数一覧

### 必須
```bash
PULUMI_CONFIG_PASSPHRASE  # Pulumi暗号化パスフレーズ
AWS_REGION                 # AWSリージョン（デフォルト: ap-northeast-1）
```

### オプション
```bash
JENKINS_VERSION           # Jenkinsバージョン
PULUMI_STATE_BUCKET_NAME  # S3バケット名（自動検出可能）
DEPLOY_ENV               # デプロイ環境（dev/staging/prod）
```

## スクリプトベストプラクティス

**スクリプトの使用方法については [scripts/README.md](scripts/README.md) を参照してください。**
**開発者向けの詳細な実装方法は [scripts/CONTRIBUTION.md](scripts/CONTRIBUTION.md) を参照してください。**

### 重要な注意事項

- **スクリプト開発時**: スクリプトを修正・追加した場合、必ず `scripts/README.md` の更新が必要かチェックすること
- **ドキュメント更新対象**:
  - 新しいスクリプトの追加
  - パラメータ・オプションの変更
  - 環境変数の追加・変更
  - 使用方法の変更
  - セキュリティ設定の変更
  - トラブルシューティング情報の追加

### スクリプト作成の基本ルール

1. **ヘッダーコメント必須**: 目的、使用方法、環境変数を明記
2. **エラーハンドリング**: `set -euo pipefail` を使用
3. **ログ出力**: 重要な処理はログ出力
4. **冪等性**: 複数回実行しても安全に動作
5. **セキュリティ**: 認証情報のハードコーディング禁止
6. **ShellCheck準拠**: 静的解析でエラーがないこと
7. **命名規則**: `{action}-{target}.sh` 形式（例: `setup-aws-credentials.sh`）

詳細な実装方法は [scripts/CONTRIBUTION.md](scripts/CONTRIBUTION.md) を参照。

## CI/CDパイプライン統合

現在は手動デプロイメントを推奨。将来的なCI/CD統合のために以下を考慮：

1. **自動テスト準備**
   - Pulumiプレビューの自動実行
   - Ansibleシンタックスチェック
   - Jenkins設定の検証
   - スクリプトのシンタックスチェック

2. **モニタリング準備**
   - CloudWatchダッシュボード設定
   - アラート設定の自動化

## 更新履歴管理

重要な変更は以下のドキュメントを更新：

### ユーザー向けドキュメント（README.md）
1. **README.md**: プロジェクト全体の使用方法
2. **ansible/README.md**: Ansibleプレイブックの使用方法
3. **pulumi/README.md**: Pulumiスタックの使用方法
4. **jenkins/README.md**: Jenkinsジョブの使用方法
5. **scripts/README.md**: スクリプトの使用方法

### 開発者向けドキュメント（CONTRIBUTION.md）
1. **CLAUDE.md**: Claude Code向けガイド（このファイル）
2. **CONTRIBUTION.md**: プロジェクト全体の開発ガイドライン
3. **ansible/CONTRIBUTION.md**: Ansible開発の詳細ガイド（ヘルパーロール、meta/main.yml）
4. **pulumi/CONTRIBUTION.md**: Pulumi開発の詳細ガイド（TypeScript、スタック管理）
5. **jenkins/CONTRIBUTION.md**: Jenkins開発の詳細ガイド（シードジョブ、DSL、パラメータルール）
6. **scripts/CONTRIBUTION.md**: スクリプト開発の詳細ガイド（Bash、ShellCheck、命名規則）

### ドキュメント責任分担の原則
- **README.md**: エンドユーザー向け（使い方、実行方法、トラブルシューティング）
- **CONTRIBUTION.md**: 開発者向け（実装方法、コーディング規約、ベストプラクティス）
- **CLAUDE.md**: AI向け（プロジェクト全体の文脈、重要な制約、開発フロー）