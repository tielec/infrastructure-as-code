# 要件定義書 - Issue #385

## Issue情報

- **Issue番号**: #385
- **タイトル**: [TASK] SSMバックアップジョブをマルチリージョン対応化（us-west-2対応追加）
- **状態**: open
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/385
- **作成日**: 2025年度

---

## 0. Planning Documentの確認

Planning Phase（`.ai-workflow/issue-385/00_planning/output/planning.md`）で策定された以下の戦略を踏まえて要件定義を実施します：

### 開発計画の全体像

- **複雑度評価**: 中程度（見積もり工数: 約12時間）
- **実装戦略**: EXTEND（既存機能の拡張）
- **テスト戦略**: INTEGRATION_ONLY（統合テストのみ、手動実行）
- **テストコード戦略**: 該当なし（自動テストコード作成不要、手動統合テストを実施）
- **主要リスク**: 既存機能への影響（後方互換性）→ デフォルト値設定と回帰テストで軽減

### 実装アプローチ

1. 既存のJenkinsジョブ（admin_ssm_backup_job）を拡張し、リージョンをパラメータとして追加
2. ハードコードされた `AWS_REGION` を動的なパラメータに変更
3. 既存のap-northeast-1での動作に影響を与えない（デフォルト値で互換性確保）
4. us-west-2用の新規Pulumiスタックをデプロイ

### スコープ

- **対象リージョン**: ap-northeast-1（既存）、us-west-2（新規）
- **スコープ外**: 追加リージョン対応（eu-west-1、ap-southeast-1など）は今回対象外

---

## 1. 概要

### 背景

現在、SSM Parameter Storeバックアップジョブ（Admin_Jobs/ssm-backup）は ap-northeast-1 リージョンのみ対応しています。us-west-2 リージョンでもSSMパラメータを運用しており、同様にバックアップが必要な状況です。

### 目的

リージョンをパラメータ化して複数リージョンでバックアップを実行できるようにすることで、マルチリージョン運用に対応し、災害対策（DR）とデータ保全性を向上させます。

### ビジネス価値

- **リスク低減**: 複数リージョンでのバックアップにより、リージョン障害時のデータ保全性が向上
- **運用効率化**: 単一のJenkinsジョブで複数リージョンのバックアップを管理可能
- **拡張性**: 将来的な追加リージョン対応の基盤を構築

### 技術的価値

- **保守性向上**: ハードコードされたリージョン設定を動的パラメータ化
- **再利用性向上**: 既存のPulumiスタック構造を活用し、新規リージョンへの展開が容易
- **後方互換性**: 既存のap-northeast-1バックアップ機能は影響を受けない

---

## 2. 機能要件

### FR-1: リージョンパラメータの追加（優先度: 高）

**説明**: Jenkinsジョブにリージョン選択パラメータを追加する

**詳細**:
- パラメータ名: `AWS_REGION`
- パラメータ種別: Choice Parameter（選択式）
- 選択可能なリージョン: `ap-northeast-1`, `us-west-2`
- デフォルト値: `ap-northeast-1`（後方互換性のため）

**実装箇所**: `jenkins/jobs/dsl/admin/admin_ssm_backup_job.groovy`

**検証方法**:
- Jenkins UI上でジョブビルド時にリージョン選択肢が表示されること
- デフォルト値が `ap-northeast-1` であること
- 選択したリージョンがパラメータとして正しく渡されること

---

### FR-2: Jenkinsfileのリージョン動的取得（優先度: 高）

**説明**: Jenkinsfileでハードコードされたリージョンをパラメータから動的に取得する

**詳細**:
- 現在の実装: `AWS_REGION = 'ap-northeast-1'`（ハードコード）
- 変更後の実装: `AWS_REGION = params.AWS_REGION ?: 'ap-northeast-1'`
- フォールバック機能: パラメータ未指定時は `ap-northeast-1` を使用

**実装箇所**: `jenkins/jobs/pipeline/admin/ssm-backup/Jenkinsfile:21`

**検証方法**:
- パラメータ指定時、選択したリージョンが使用されること
- パラメータ未指定時、デフォルト値 `ap-northeast-1` が使用されること
- 環境変数 `AWS_REGION` が正しく設定されること

---

### FR-3: ビルド表示名へのリージョン情報追加（優先度: 中）

**説明**: Jenkinsビルド表示名にリージョン情報を含める

**詳細**:
- 現在の表示名: `#${env.BUILD_NUMBER} - ${params.ENVIRONMENT} Backup`
- 変更後の表示名: `#${env.BUILD_NUMBER} - ${params.ENVIRONMENT} (${params.AWS_REGION}) Backup`

**実装箇所**: `jenkins/jobs/pipeline/admin/ssm-backup/Jenkinsfile`

**検証方法**:
- Jenkins UI上でビルド表示名にリージョン情報が含まれること
- 例: `#42 - dev (us-west-2) Backup`

---

### FR-4: ログ出力へのリージョン情報追加（優先度: 中）

**説明**: Jenkinsジョブのログ出力にリージョン情報を含める

**詳細**:
- Initializeステージのログ出力に `Region: ${params.AWS_REGION}` を追加
- Dry Run Reportにリージョン情報を追加

**実装箇所**: `jenkins/jobs/pipeline/admin/ssm-backup/Jenkinsfile`

**検証方法**:
- コンソールログにリージョン情報が表示されること
- ドライランモードでのレポートにリージョン情報が含まれること

---

### FR-5: us-west-2リージョン用Pulumiスタックのデプロイ（優先度: 高）

**説明**: us-west-2リージョン用のS3バケットとSSMパラメータを作成する

**詳細**:
- 新規スタック設定ファイルの作成:
  - `Pulumi.us-west-2-dev.yaml`
  - `Pulumi.us-west-2-prod.yaml`
- スタック設定内容:
  - `projectName`: jenkins-infra
  - `environment`: dev / prod
  - `aws:region`: us-west-2
- 作成されるリソース:
  - S3バケット: `jenkins-infra-ssm-backup-{env}-{accountId}-us-west-2`
  - SSMパラメータ: `/jenkins/{env}/backup/s3-bucket-name`（us-west-2リージョン内）

**実装箇所**: `pulumi/jenkins-ssm-backup-s3/`

**検証方法**:
- `pulumi up` が正常に完了すること
- S3バケットが正しい命名規則で作成されること
- SSMパラメータがus-west-2リージョンに作成されること
- バケット名にリージョン名（us-west-2）が含まれること

---

### FR-6: リージョン別SSMパラメータ取得（優先度: 高）

**説明**: 選択したリージョンのSSMパラメータストアからバケット名を取得する

**詳細**:
- SSMパラメータパス: `/jenkins/{environment}/backup/s3-bucket-name`
- 取得時に `--region ${AWS_REGION}` オプションを指定
- リージョンごとに独立したパラメータストアを参照

**実装箇所**: `jenkins/jobs/pipeline/admin/ssm-backup/Jenkinsfile`（Get Backup Bucket Nameステージ）

**検証方法**:
- ap-northeast-1を選択時、ap-northeast-1のSSMパラメータが取得されること
- us-west-2を選択時、us-west-2のSSMパラメータが取得されること
- 取得したバケット名にリージョン名が含まれること

---

### FR-7: リージョン別S3バケット書き込み（優先度: 高）

**説明**: 選択したリージョンのS3バケットにバックアップファイルをアップロードする

**詳細**:
- S3アップロード先: リージョンごとに異なるバケット
- アップロードコマンドに `--region ${AWS_REGION}` オプションを指定
- ファイル名: `ssm-backup-${params.ENVIRONMENT}-${env.BACKUP_TIMESTAMP}.json`

**実装箇所**: `jenkins/jobs/pipeline/admin/ssm-backup/Jenkinsfile`（Upload to S3ステージ）

**検証方法**:
- ap-northeast-1を選択時、ap-northeast-1のS3バケットにアップロードされること
- us-west-2を選択時、us-west-2のS3バケットにアップロードされること
- アップロードされたファイルが正しいS3パスに配置されること

---

### FR-8: ドライランモードでのリージョン表示（優先度: 中）

**説明**: ドライランモード実行時にリージョン情報を表示する

**詳細**:
- Dry Run Reportに以下の情報を追加:
  - リージョン: `${params.AWS_REGION}`
  - S3バケット名（リージョン別）
  - SSMパラメータ取得元リージョン

**実装箇所**: `jenkins/jobs/pipeline/admin/ssm-backup/Jenkinsfile`（Dry Run Reportステージ）

**検証方法**:
- ドライランモード実行時、レポートにリージョン情報が含まれること
- 各リージョンで異なるS3バケット名が表示されること

---

## 3. 非機能要件

### NFR-1: パフォーマンス要件

**説明**: バックアップ実行時間は既存実装と同等であること

**詳細**:
- リージョン追加による実行時間への影響は最小限（±5%以内）
- S3アップロード速度はリージョン内通信のため高速に保たれること

**検証方法**:
- 各リージョンでバックアップ実行時間を計測
- 既存実装（ap-northeast-1のみ）と比較して有意な遅延がないこと

---

### NFR-2: セキュリティ要件

**説明**: 既存のセキュリティ要件を維持すること

**詳細**:
- S3バケットの暗号化: AES256（既存と同じ）
- パブリックアクセスブロック: 有効（既存と同じ）
- HTTPS通信の強制: 必須（既存と同じ）
- SSMパラメータ: SecureStringタイプで暗号化
- IAM権限: 両リージョンへのアクセス権限を確認

**検証方法**:
- S3バケット設定で暗号化が有効であること
- パブリックアクセスブロックが有効であること
- IAMロールが両リージョンのSSM、S3にアクセス可能であること

---

### NFR-3: 可用性・信頼性要件

**説明**: 片方のリージョンでの障害が他方のリージョンのバックアップに影響しないこと

**詳細**:
- リージョンごとに独立したS3バケットを使用
- リージョンごとに独立したSSMパラメータストアを使用
- 片方のリージョンでエラーが発生しても、他方のリージョンは独立して実行可能

**検証方法**:
- 各リージョンで独立してバックアップジョブが実行できること
- エラーメッセージにリージョン情報が含まれ、デバッグが容易であること

---

### NFR-4: 保守性・拡張性要件

**説明**: 将来的な追加リージョン対応が容易であること

**詳細**:
- リージョンのハードコーディングを排除
- Pulumiスタック構造は既存実装を再利用
- Jenkins DSLのchoiceParamに新しいリージョンを追加するだけで拡張可能

**検証方法**:
- リージョン追加時の変更箇所が最小限であること
- ドキュメントに拡張方法が明記されていること

---

### NFR-5: 運用要件

**説明**: バックアップの運用が容易であること

**詳細**:
- バックアップ保持期間: 30日（既存と同じ）
- ドライランモード: 対応必須
- エラーハンドリング: 既存と同等
- ログ出力: リージョン情報を含む詳細なログ

**検証方法**:
- ドライランモードが正常に動作すること
- エラー発生時に適切なエラーメッセージが表示されること
- ログからリージョン、環境、バケット名が特定可能であること

---

## 4. 制約事項

### 技術的制約

1. **既存実装の制約**
   - 既存のPulumiスタック構造（`pulumi/jenkins-ssm-backup-s3/`）を変更しない
   - 既存のJenkinsfile構造を維持する
   - 既存のSSMパラメータパス規則（`/jenkins/{env}/backup/s3-bucket-name`）を踏襲

2. **AWS制約**
   - S3バケット名は全AWSアカウント間でグローバルに一意である必要がある
   - IAMロールは両リージョンのリソースにアクセス可能な権限が必要
   - SSMパラメータストアはリージョン固有のサービス

3. **Jenkins制約**
   - パラメータはJob DSLファイルで定義する（Jenkinsfileでのパラメータ定義は禁止）
   - choiceParamの最初の選択肢がデフォルト値となる

### リソース制約

1. **時間制約**
   - 見積もり工数: 約12時間
   - 実装期間: 2〜3営業日を想定

2. **人員制約**
   - 開発者: 1名
   - レビュー: 必要に応じて

3. **予算制約**
   - 追加コスト: S3バケット、SSMパラメータの追加（微小）
   - NAT Gateway / NAT Instanceの通信料金（既存インフラ利用）

### ポリシー制約

1. **セキュリティポリシー**
   - S3バケットは暗号化必須
   - SSMパラメータはSecureStringタイプ必須
   - IAMロールは最小権限の原則に従う

2. **コーディング規約**
   - CLAUDE.md、CONTRIBUTION.md、jenkins/CONTRIBUTION.mdに準拠
   - パラメータ定義はJob DSLで行う
   - コメントは日本語で記述

3. **ドキュメント規約**
   - 実装完了後、jenkins/README.mdを更新
   - 必要に応じてjenkins/CONTRIBUTION.mdを更新

---

## 5. 前提条件

### システム環境

1. **Jenkins環境**
   - Jenkinsコントローラーが既にデプロイされていること
   - Job DSLプラグインがインストールされていること
   - Admin_Jobs/ssm-backup ジョブが既に存在すること

2. **AWS環境**
   - ap-northeast-1 リージョンに既存のS3バケットとSSMパラメータが存在すること
   - us-west-2 リージョンにVPCと必要なネットワークリソースが構築されていること
   - IAMロールが両リージョンのSSM、S3にアクセス可能であること

3. **Pulumi環境**
   - Pulumiがインストールされていること
   - S3バックエンドが設定されていること
   - 認証情報（PULUMI_CONFIG_PASSPHRASE）が設定されていること

### 依存コンポーネント

1. **Pulumiスタック**
   - `jenkins-ssm-backup-s3`（ap-northeast-1用、既存）
   - `jenkins-ssm-backup-s3`（us-west-2用、新規）

2. **AWSサービス**
   - S3（Simple Storage Service）
   - SSM Parameter Store
   - IAM（Identity and Access Management）

3. **Jenkinsプラグイン**
   - Pipeline Plugin
   - Job DSL Plugin
   - AWS CLI（Jenkinsエージェント上）

### 外部システム連携

1. **GitHub連携**
   - Jenkinsfileとジョブ定義ファイルはGitHubリポジトリで管理
   - リポジトリ: `tielec/infrastructure-as-code`

2. **AWS CLI**
   - Jenkinsエージェント上でAWS CLIを使用してSSMパラメータ取得、S3アップロードを実行

---

## 6. 受け入れ基準

### AC-1: リージョンパラメータの追加

**Given**: Jenkins UI上でAdmin_Jobs/ssm-backupジョブのビルドページを開く
**When**: 「Build with Parameters」ボタンをクリックする
**Then**:
- AWS_REGIONパラメータが表示されること
- 選択肢として「ap-northeast-1」「us-west-2」が表示されること
- デフォルト値が「ap-northeast-1」であること

---

### AC-2: ap-northeast-1での後方互換性

**Given**: Admin_Jobs/ssm-backupジョブを実行する
**When**: AWS_REGIONパラメータに「ap-northeast-1」を選択してビルドを実行する
**Then**:
- 既存のap-northeast-1のS3バケットにバックアップファイルがアップロードされること
- SSMパラメータが正常に取得されること
- ジョブが成功（SUCCESS）ステータスで完了すること
- ログに「Region: ap-northeast-1」が表示されること

---

### AC-3: us-west-2での新規バックアップ

**Given**: us-west-2リージョン用のPulumiスタックがデプロイ済みである
**When**: AWS_REGIONパラメータに「us-west-2」を選択してビルドを実行する
**Then**:
- us-west-2リージョンのSSMパラメータからS3バケット名が取得されること
- 取得したバケット名に「us-west-2」が含まれること
- us-west-2リージョンのS3バケットにバックアップファイルがアップロードされること
- ジョブが成功（SUCCESS）ステータスで完了すること
- ログに「Region: us-west-2」が表示されること

---

### AC-4: ドライランモードでのリージョン表示

**Given**: Admin_Jobs/ssm-backupジョブを実行する
**When**: DRY_RUNパラメータをtrueに設定し、AWS_REGIONに「us-west-2」を選択してビルドを実行する
**Then**:
- ジョブが成功（SUCCESS）ステータスで完了すること
- Dry Run Reportにリージョン情報「us-west-2」が表示されること
- S3バケット名に「us-west-2」が含まれること
- 実際のS3アップロードは実行されないこと

---

### AC-5: ビルド表示名へのリージョン情報表示

**Given**: Admin_Jobs/ssm-backupジョブを実行する
**When**: ENVIRONMENTに「dev」、AWS_REGIONに「us-west-2」を選択してビルドを実行する
**Then**:
- ビルド表示名が「#<ビルド番号> - dev (us-west-2) Backup」の形式で表示されること
- Jenkins UI上のビルド履歴にリージョン情報が含まれること

---

### AC-6: 環境×リージョンのマトリクステスト

**Given**: Admin_Jobs/ssm-backupジョブを実行する
**When**: 以下の4パターンの組み合わせでビルドを実行する
- dev + ap-northeast-1
- dev + us-west-2
- prod + ap-northeast-1
- prod + us-west-2

**Then**:
- すべてのパターンでジョブが成功（SUCCESS）ステータスで完了すること
- 各パターンで正しいS3バケットにバックアップがアップロードされること
- バケット名が「jenkins-infra-ssm-backup-{env}-{accountId}-{region}」の形式であること

---

### AC-7: エラーケース - SSMパラメータ不存在

**Given**: us-west-2リージョンのSSMパラメータが存在しない状態である（テスト用に一時削除）
**When**: AWS_REGIONに「us-west-2」を選択してビルドを実行する
**Then**:
- ジョブが失敗（FAILURE）ステータスで完了すること
- エラーメッセージに「us-west-2」リージョン情報が含まれること
- エラーメッセージにSSMパラメータパス（`/jenkins/{env}/backup/s3-bucket-name`）が含まれること

---

### AC-8: us-west-2用Pulumiスタックのデプロイ

**Given**: Pulumiスタック設定ファイル（`Pulumi.us-west-2-dev.yaml`, `Pulumi.us-west-2-prod.yaml`）が作成されている
**When**: `pulumi up` を実行する
**Then**:
- S3バケットが作成されること
  - バケット名: `jenkins-infra-ssm-backup-dev-{accountId}-us-west-2`（dev環境）
  - バケット名: `jenkins-infra-ssm-backup-prod-{accountId}-us-west-2`（prod環境）
- SSMパラメータが作成されること
  - パラメータ名: `/jenkins/dev/backup/s3-bucket-name`（us-west-2リージョン）
  - パラメータ名: `/jenkins/prod/backup/s3-bucket-name`（us-west-2リージョン）
- パラメータ値がS3バケット名と一致すること

---

### AC-9: ドキュメント更新

**Given**: 実装が完了している
**When**: jenkins/README.mdを確認する
**Then**:
- SSMバックアップジョブの説明にマルチリージョン対応が記載されていること
- AWS_REGIONパラメータの説明が記載されていること
- 使用可能なリージョン（ap-northeast-1, us-west-2）が明記されていること
- リージョンごとの独立したS3バケットの説明が記載されていること
- 実行例にリージョンパラメータが含まれていること

---

## 7. スコープ外

### 今回のスコープ外とする事項

1. **追加リージョン対応**
   - eu-west-1、ap-southeast-1、us-east-1などの追加リージョンは今回対象外
   - 理由: 今回はap-northeast-1とus-west-2の2リージョンのみに限定

2. **リージョン間のバックアップ複製**
   - あるリージョンのバックアップを別リージョンにコピーする機能は対象外
   - 理由: 各リージョンのバックアップは独立して管理

3. **バックアップの自動検証機能**
   - バックアップファイルの整合性チェックやリストアテストは対象外
   - 理由: 既存実装にも含まれていない機能

4. **バックアップファイルの差分管理**
   - 前回バックアップとの差分を記録する機能は対象外
   - 理由: S3ライフサイクルポリシーによる保持期間管理で十分

5. **自動テストコードの作成**
   - Groovyによる自動テストフレームワークの構築は対象外
   - 理由: Planning Documentでテストコード戦略が「該当なし」と判断されている

6. **新規Jenkinsプラグインの導入**
   - マルチリージョン対応のための新規プラグイン導入は対象外
   - 理由: 既存のプラグインとAWS CLIで実現可能

7. **IAMロールの新規作成**
   - 既存のIAMロールを使用（必要に応じて権限追加のみ）
   - 理由: 既存のロールが両リージョンにアクセス可能であることを前提

### 将来的な拡張候補

1. **追加リージョン対応（Phase 2）**
   - eu-west-1、ap-southeast-1、us-east-1などへの拡張
   - choiceParamに新しいリージョンを追加するだけで実現可能

2. **リージョン選択のデフォルト値を環境変数で制御（Phase 2）**
   - 環境ごとに優先リージョンを設定可能にする

3. **バックアップの自動検証機能（Phase 3）**
   - バックアップファイルの整合性チェック
   - リストアテストの自動実行

4. **バックアップファイルの差分管理機能（Phase 3）**
   - 前回バックアップとの差分を可視化
   - 変更履歴の追跡

5. **クロスリージョンレプリケーション（Phase 3）**
   - あるリージョンのバックアップを別リージョンに自動複製
   - DR（災害復旧）対策の強化

---

## 8. 補足情報

### 参考ドキュメント

- **Jenkins開発ガイド**: `jenkins/CONTRIBUTION.md`
- **Pulumi開発ガイド**: `pulumi/CONTRIBUTION.md`
- **プロジェクト全体ガイド**: `CLAUDE.md`
- **アーキテクチャ設計思想**: `ARCHITECTURE.md`

### 関連Issue

- なし（現時点では関連Issueなし）

### 実装の優先順位

以下の順序で実装を進めることを推奨：

1. **Phase 1**: Pulumiスタックデプロイ（us-west-2）
2. **Phase 2**: Jenkins DSL修正（リージョンパラメータ追加）
3. **Phase 3**: Jenkinsfile修正（リージョン動的取得、ログ表示）
4. **Phase 4**: 動作確認・テスト
5. **Phase 5**: ドキュメント更新

---

## 9. レビューチェックリスト

要件定義書の品質ゲート確認：

- [x] **機能要件が明確に記載されている**
  - FR-1〜FR-8まで8つの機能要件を具体的に記載
  - 各要件に優先度、詳細、実装箇所、検証方法を明記

- [x] **受け入れ基準が定義されている**
  - AC-1〜AC-9まで9つの受け入れ基準をGiven-When-Then形式で記載
  - 各基準は検証可能（テスト可能）な形で記述

- [x] **スコープが明確である**
  - 対象リージョン（ap-northeast-1, us-west-2）を明記
  - スコープ外（追加リージョン、自動検証機能など）を明示
  - 将来的な拡張候補を記載

- [x] **論理的な矛盾がない**
  - 機能要件と受け入れ基準が対応
  - 非機能要件と制約事項に矛盾なし
  - Planning Documentの戦略（EXTEND、INTEGRATION_ONLY）と整合

---

**作成日**: 2025年度
**最終更新日**: 2025年度
**作成者**: AI Workflow Orchestrator
**レビュー状態**: 初版作成完了、レビュー待ち
