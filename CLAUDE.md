# CLAUDE.md

このファイルは、このリポジトリでコードを扱う際のClaude Code (claude.ai/code) へのガイダンスを提供します。

## プロジェクト概要

包括的なJenkins CI/CDインフラ自動化プロジェクトで、ブートストラップにCloudFormation、インフラプロビジョニングにPulumi (TypeScript)、オーケストレーションにAnsibleを使用しています。ブルーグリーンデプロイメント機能、自動スケーリングエージェント、高可用性機能を備えた本番環境対応のJenkins環境をAWS上にデプロイします。

## コーディングガイドライン

### 基本原則
- **思考**: 英語で論理的に考える (Think in English for logical reasoning)
- **対話**: 日本語で対話 (Dialogue in Japanese with users)
- **ドキュメント**: 日本語で記述 (Documentation in Japanese)
- **コメント**: ソースコード内のコメントは日本語
- **README/ドキュメント**: すべて日本語で記述

### 重要な注意事項
- **Bootstrap修正時**: `bootstrap/` ディレクトリ内のファイルを修正した場合、必ずREADME.mdの更新が必要かチェックすること
- **依存関係の順序**: コンポーネント間の依存関係を常に意識し、デプロイ/削除順序を守ること
- **環境分離**: dev/staging/production環境を明確に分離すること

## Pulumiベストプラクティス

**Pulumiスタックの開発・使用方法については [pulumi/README.md](pulumi/README.md) を参照してください。**

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

### 重要な注意事項

- **Jenkins開発時**: Jenkins設定、ジョブ定義、パイプラインを修正・追加した場合、必ず `jenkins/README.md` の更新が必要かチェックすること
- **ドキュメント更新対象**:
  - 新しいジョブの追加
  - パイプラインの変更
  - 共有ライブラリの追加・変更
  - プラグインの変更
  - セキュリティ設定の変更
  - トラブルシューティング情報の追加

## Ansibleベストプラクティス

**Ansibleプレイブックの開発・使用方法については [ansible/README.md](ansible/README.md) を参照してください。**

### 重要な注意事項

- **Ansible開発時**: Ansibleプレイブックやロールを修正・追加した場合、必ず `ansible/README.md` の更新が必要かチェックすること
- **ドキュメント更新対象**:
  - 新しいプレイブックの追加
  - 新しいロールの追加
  - パラメータ変更
  - 依存関係の変更
  - 実行手順の変更
  - トラブルシューティング情報の追加

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

### 1. 新機能追加時（Pulumiスタック）
```bash
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
# 1. プレイブック・ロールの開発
cd ansible
# 開発作業を実施

# 2. ansible/README.md更新確認 ⚠️ 重要
# 以下の項目で更新が必要か確認：
# - プレイブック一覧（新規追加・変更）
# - ロール一覧（新規追加・変更）
# - パラメータ説明（追加・変更）
# - 実行例（新規・変更）
# - 依存関係図（変更があれば）
# - トラブルシューティング（新規問題）
vi ansible/README.md
```

### 5. Pulumi開発時
```bash
# 1. Pulumiスタックの開発
cd pulumi
# 開発作業を実施

# 2. pulumi/README.md更新確認 ⚠️ 重要
# 以下の項目で更新が必要か確認：
# - スタック一覧（新規追加・変更）
# - 依存関係（スタック間の参照変更）
# - 設定パラメータ（追加・変更）
# - 使用方法（新規コマンド・手順）
# - コーディング規約（新規パターン）
# - トラブルシューティング（新規問題）
vi pulumi/README.md
```

### 6. Jenkins開発時
```bash
# 1. Jenkins設定・ジョブの開発
cd jenkins
# 開発作業を実施

# 2. jenkins/README.md更新確認 ⚠️ 重要
# 以下の項目で更新が必要か確認：
# - ジョブ一覧（新規追加・変更）
# - パイプライン（新規・変更）
# - 共有ライブラリ（追加・変更）
# - プラグイン一覧（追加・削除）
# - 設定変更（JCasC、Groovyスクリプト）
# - トラブルシューティング（新規問題）
vi jenkins/README.md
```

### 7. スクリプト開発時
```bash
# 1. スクリプトの開発
cd scripts
# 開発作業を実施

# 2. scripts/README.md更新確認 ⚠️ 重要
# 以下の項目で更新が必要か確認：
# - スクリプト一覧（新規追加・変更）
# - 使用方法（パラメータ・オプション変更）
# - 環境変数（追加・変更）
# - 依存関係（他スクリプトとの連携）
# - セキュリティ設定（権限・認証）
# - トラブルシューティング（新規問題）
vi scripts/README.md
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

## セキュリティチェックリスト

- [ ] クレデンシャルのハードコーディングなし
- [ ] SSMパラメータはSecureString使用
- [ ] IAMロールは最小権限の原則
- [ ] セキュリティグループは必要最小限のポート開放
- [ ] ログに機密情報を出力しない
- [ ] APIキーは環境変数またはSSMで管理

## パフォーマンス最適化

### Pulumi

**Pulumiのパフォーマンス最適化については [pulumi/README.md#パフォーマンス最適化](pulumi/README.md#パフォーマンス最適化) を参照してください。**

### Ansible

**Ansibleのパフォーマンス最適化については [ansible/README.md#ベストプラクティス](ansible/README.md#ベストプラクティス) を参照してください。**

### Jenkins

**Jenkinsのパフォーマンス最適化については [jenkins/README.md#パフォーマンス最適化](jenkins/README.md#パフォーマンス最適化) を参照してください。**

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

**スクリプトの開発・使用方法については [scripts/README.md](scripts/README.md) を参照してください。**

### 重要な注意事項

- **スクリプト開発時**: スクリプトを修正・追加した場合、必ず `scripts/README.md` の更新が必要かチェックすること
- **ドキュメント更新対象**:
  - 新しいスクリプトの追加
  - パラメータ・オプションの変更
  - 環境変数の追加・変更
  - 使用方法の変更
  - セキュリティ設定の変更
  - トラブルシューティング情報の追加

### スクリプト作成規約

1. **ヘッダーコメント必須**: 目的、使用方法、環境変数を明記
2. **エラーハンドリング**: `set -euo pipefail` を使用
3. **ログ出力**: 重要な処理はログ出力
4. **冪等性**: 複数回実行しても安全に動作
5. **セキュリティ**: 認証情報のハードコーディング禁止

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
1. **README.md**: ユーザー向け手順
2. **CLAUDE.md**: 開発者向けガイド（このファイル）
3. **ansible/README.md**: Ansibleプレイブック・ロールの詳細
4. **pulumi/README.md**: Pulumiスタックの詳細
5. **jenkins/README.md**: Jenkins設定・ジョブの詳細
6. **scripts/README.md**: スクリプトの詳細
7. **CONTRIBUTION.md**: コントリビューションガイド