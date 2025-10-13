# 実装ログ - Issue #385

## Issue情報

- **Issue番号**: #385
- **タイトル**: [TASK] SSMバックアップジョブをマルチリージョン対応化（us-west-2対応追加）
- **状態**: open
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/385
- **実装日**: 2025年度

---

## 実装サマリー

- **実装戦略**: EXTEND（既存機能の拡張）
- **変更ファイル数**: 2個
- **新規作成ファイル数**: 2個
- **テストコード**: Phase 5（test_implementation）で実装予定

---

## 変更ファイル一覧

### 新規作成

1. **`pulumi/jenkins-ssm-backup-s3/Pulumi.us-west-2-dev.yaml`**
   - us-west-2リージョンのdev環境用Pulumiスタック設定ファイル
   - プロジェクト名: jenkins-infra
   - 環境: dev
   - リージョン: us-west-2

2. **`pulumi/jenkins-ssm-backup-s3/Pulumi.us-west-2-prod.yaml`**
   - us-west-2リージョンのprod環境用Pulumiスタック設定ファイル
   - プロジェクト名: jenkins-infra
   - 環境: prod
   - リージョン: us-west-2

### 修正

1. **`jenkins/jobs/dsl/admin/admin_ssm_backup_job.groovy`**
   - AWS_REGIONパラメータを追加（choiceParam）
   - 選択肢: ap-northeast-1, us-west-2
   - デフォルト値: ap-northeast-1（最初の選択肢、後方互換性のため）

2. **`jenkins/jobs/pipeline/admin/ssm-backup/Jenkinsfile`**
   - 環境変数の動的取得（AWS_REGION = params.AWS_REGION ?: 'ap-northeast-1'）
   - ビルド表示名へのリージョン情報追加
   - ログ出力へのリージョン情報追加（Initialize、Dry Run Report）
   - エラーメッセージへのリージョン情報追加

---

## 実装詳細

### ファイル1: `pulumi/jenkins-ssm-backup-s3/Pulumi.us-west-2-dev.yaml`

**変更内容**: 新規作成

**実装内容**:
```yaml
config:
  jenkins-ssm-backup-s3:projectName: jenkins-infra
  jenkins-ssm-backup-s3:environment: dev
  aws:region: us-west-2
```

**理由**:
- 既存のPulumiスタック構造（`index.ts`）を再利用し、us-west-2リージョン用の設定ファイルを追加
- 設定ファイルのみ追加することで、コードの重複を避け、保守性を向上
- 既存のap-northeast-1用スタック設定（`Pulumi.dev.yaml`）と同じ構造を維持

**注意点**:
- このファイル作成後、Pulumiスタックを初期化してデプロイする必要がある
- デプロイ手順:
  ```bash
  cd pulumi/jenkins-ssm-backup-s3
  pulumi stack init us-west-2-dev
  pulumi config set aws:region us-west-2
  pulumi up
  ```

---

### ファイル2: `pulumi/jenkins-ssm-backup-s3/Pulumi.us-west-2-prod.yaml`

**変更内容**: 新規作成

**実装内容**:
```yaml
config:
  jenkins-ssm-backup-s3:projectName: jenkins-infra
  jenkins-ssm-backup-s3:environment: prod
  aws:region: us-west-2
```

**理由**:
- prod環境用のus-west-2リージョン設定ファイル
- dev環境と同じ構造で、環境名のみ異なる
- 既存のap-northeast-1用スタック設定（`Pulumi.prod.yaml`）と同じ構造を維持

**注意点**:
- dev環境のデプロイ後、prod環境もデプロイする必要がある
- デプロイ手順:
  ```bash
  cd pulumi/jenkins-ssm-backup-s3
  pulumi stack init us-west-2-prod
  pulumi config set aws:region us-west-2
  pulumi up
  ```

---

### ファイル3: `jenkins/jobs/dsl/admin/admin_ssm_backup_job.groovy`

**変更内容**: AWS_REGIONパラメータの追加

**変更箇所**: 49-54行目（parametersブロック）

**変更前**:
```groovy
parameters {
    choiceParam('ENVIRONMENT', ['dev', 'prod'], '環境を選択')
    booleanParam('DRY_RUN', false, 'ドライランモード（実際のバックアップは実行しない）')
    stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileが格納されているブランチ')
}
```

**変更後**:
```groovy
parameters {
    choiceParam('ENVIRONMENT', ['dev', 'prod'], '環境を選択')
    choiceParam('AWS_REGION', ['ap-northeast-1', 'us-west-2'], 'バックアップ対象のAWSリージョン')
    booleanParam('DRY_RUN', false, 'ドライランモード（実際のバックアップは実行しない）')
    stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileが格納されているブランチ')
}
```

**理由**:
- Jenkinsジョブでリージョンを選択できるようにするため
- choiceParamの最初の選択肢（ap-northeast-1）がデフォルト値となり、後方互換性を確保
- CLAUDE.mdの「Jenkinsパラメータ定義ルール」に準拠（DSLファイルでパラメータ定義）

**注意点**:
- この変更後、シードジョブ（Admin_Jobs/job-creator）を実行してDSLを反映する必要がある
- 初回実行時はパラメータがまだ定義されていないため、Jenkinsfileでデフォルト値を使用する設計になっている

---

### ファイル4: `jenkins/jobs/pipeline/admin/ssm-backup/Jenkinsfile`

#### 変更箇所1: 環境変数の動的取得（19-34行目）

**変更前**:
```groovy
environment {
    // AWS設定
    AWS_REGION = 'ap-northeast-1'

    // タイムスタンプ
    BACKUP_DATE = sh(script: "date '+%Y-%m-%d'", returnStdout: true).trim()
    BACKUP_TIMESTAMP = sh(script: "date '+%Y%m%d_%H%M%S'", returnStdout: true).trim()

    // ディレクトリ構造
    WORK_DIR = "${WORKSPACE}/backup-work"
    DATA_DIR = "${WORK_DIR}/data"
    SCRIPT_DIR = "${WORKSPACE}/scripts"

    // 環境フィルタ（環境に含まれる文字列）
    ENV_FILTER = "/${params.ENVIRONMENT}/"
}
```

**変更後**:
```groovy
environment {
    // AWS設定
    AWS_REGION = params.AWS_REGION ?: 'ap-northeast-1'

    // タイムスタンプ
    BACKUP_DATE = sh(script: "date '+%Y-%m-%d'", returnStdout: true).trim()
    BACKUP_TIMESTAMP = sh(script: "date '+%Y%m%d_%H%M%S'", returnStdout: true).trim()

    // ディレクトリ構造
    WORK_DIR = "${WORKSPACE}/backup-work"
    DATA_DIR = "${WORK_DIR}/data"
    SCRIPT_DIR = "${WORKSPACE}/scripts"

    // 環境フィルタ（環境に含まれる文字列）
    ENV_FILTER = "/${params.ENVIRONMENT}/"
}
```

**理由**:
- ハードコードされたリージョン（'ap-northeast-1'）をパラメータから動的に取得
- Groovyのエルビス演算子（`?:`）により、パラメータ未指定時はデフォルト値（'ap-northeast-1'）を使用
- 後方互換性を確保：パラメータが存在しない場合（古いジョブ定義）でもエラーにならない

**注意点**:
- `params.AWS_REGION`は、シードジョブ実行後に利用可能になる
- 初回実行時はパラメータが未定義の可能性があるため、デフォルト値が重要

---

#### 変更箇所2: ビルド表示名とログ出力へのリージョン情報追加（39-55行目）

**変更前**:
```groovy
script {
    // ビルド表示名を設定
    currentBuild.displayName = "#${env.BUILD_NUMBER} - ${params.ENVIRONMENT} Backup"
    currentBuild.description = "Backup at ${env.BACKUP_TIMESTAMP}"

    echo """
    =============================================
    SSM Parameter Store Backup
    =============================================
    Environment: ${params.ENVIRONMENT}
    Filter: Parameters containing '${env.ENV_FILTER}'
    Dry Run: ${params.DRY_RUN}
    Timestamp: ${env.BACKUP_TIMESTAMP}
    Date: ${env.BACKUP_DATE}
    =============================================
    """.stripIndent()
```

**変更後**:
```groovy
script {
    // ビルド表示名を設定
    currentBuild.displayName = "#${env.BUILD_NUMBER} - ${params.ENVIRONMENT} (${params.AWS_REGION}) Backup"
    currentBuild.description = "Backup at ${env.BACKUP_TIMESTAMP}"

    echo """
    =============================================
    SSM Parameter Store Backup
    =============================================
    Environment: ${params.ENVIRONMENT}
    Region: ${params.AWS_REGION}
    Filter: Parameters containing '${env.ENV_FILTER}'
    Dry Run: ${params.DRY_RUN}
    Timestamp: ${env.BACKUP_TIMESTAMP}
    Date: ${env.BACKUP_DATE}
    =============================================
    """.stripIndent()
```

**理由**:
- ビルド履歴を見るだけでどのリージョンのバックアップか判別可能にするため
- リージョン情報をログの先頭で明示的に表示し、トラブルシューティングを容易にするため
- 括弧でリージョンを囲むことで可読性を向上

**注意点**:
- ビルド表示名は、Jenkins UIのビルド履歴に表示される
- ログ出力は、各ビルドのコンソールログに記録される

---

#### 変更箇所3: エラーメッセージへのリージョン情報追加（76-78行目）

**変更前**:
```groovy
if (!env.BACKUP_BUCKET) {
    error("バックアップ用S3バケットが見つかりません。Pulumiスタックがデプロイされていることを確認してください。")
}
```

**変更後**:
```groovy
if (!env.BACKUP_BUCKET) {
    error("バックアップ用S3バケットが見つかりません（リージョン: ${params.AWS_REGION}）。Pulumiスタックがデプロイされていることを確認してください。")
}
```

**理由**:
- どのリージョンで失敗したか明確にし、デバッグを容易にするため
- SSMパラメータ不存在エラー（Pulumiスタック未デプロイ）はテストシナリオ（IT-008）でカバーされている

**注意点**:
- このエラーは、Pulumiスタックがデプロイされていない場合に発生する
- エラーメッセージから即座に原因（リージョン）を特定できる

---

#### 変更箇所4: Dry Run Reportへのリージョン情報追加（214-233行目）

**変更前**:
```groovy
echo """
=============================================
DRY RUN - バックアップ実行レポート
=============================================

このドライランでは実際のS3アップロードは行われませんでした。

バックアップ対象:
- 環境: ${params.ENVIRONMENT}
- パラメータ数: ${paramCount}
- バックアップ日時: ${env.BACKUP_TIMESTAMP}

実行時の動作:
- S3バケット: ${env.BACKUP_BUCKET}
- S3パス: ${env.BACKUP_DATE}/
- ファイル名: ssm-backup-${params.ENVIRONMENT}-${env.BACKUP_TIMESTAMP}.json

=============================================
""".stripIndent()
```

**変更後**:
```groovy
echo """
=============================================
DRY RUN - バックアップ実行レポート
=============================================

このドライランでは実際のS3アップロードは行われませんでした。

バックアップ対象:
- 環境: ${params.ENVIRONMENT}
- リージョン: ${params.AWS_REGION}
- パラメータ数: ${paramCount}
- バックアップ日時: ${env.BACKUP_TIMESTAMP}

実行時の動作:
- S3バケット: ${env.BACKUP_BUCKET}
- S3パス: ${env.BACKUP_DATE}/
- ファイル名: ssm-backup-${params.ENVIRONMENT}-${env.BACKUP_TIMESTAMP}.json

=============================================
""".stripIndent()
```

**理由**:
- ドライラン時に、実行前に正しいリージョンが選択されているか確認可能にするため
- レポートの完全性を確保し、すべての重要パラメータを含める

**注意点**:
- ドライランモード（DRY_RUN=true）時のみ表示される
- S3アップロードは実行されない

---

## 設計書との整合性確認

### 設計書「変更・追加ファイルリスト」との対応

| 設計書の項目 | 実装状況 | 備考 |
|------------|---------|------|
| Pulumi.us-west-2-dev.yaml | ✅ 完了 | 新規作成 |
| Pulumi.us-west-2-prod.yaml | ✅ 完了 | 新規作成 |
| admin_ssm_backup_job.groovy | ✅ 完了 | AWS_REGIONパラメータ追加 |
| Jenkinsfile（環境変数） | ✅ 完了 | AWS_REGION動的取得 |
| Jenkinsfile（ビルド表示名） | ✅ 完了 | リージョン情報追加 |
| Jenkinsfile（ログ出力） | ✅ 完了 | リージョン情報追加 |
| Jenkinsfile（エラーメッセージ） | ✅ 完了 | リージョン情報追加 |
| Jenkinsfile（Dry Run Report） | ✅ 完了 | リージョン情報追加 |

### 設計書「詳細設計」との整合性

すべての実装は設計書の「詳細設計」セクション（セクション7）に従っています：
- 7.1 Job DSL設計 → ✅ 実装完了
- 7.2 Jenkinsfile設計（変更箇所1-4） → ✅ 実装完了
- 7.3 Pulumiスタック設計 → ✅ 実装完了
- 7.4 エラーハンドリング設計 → ✅ 実装完了

---

## 品質ゲート確認

### Phase 4の品質ゲート

- [x] **Phase 2の設計に沿った実装である**
  - 設計書の「詳細設計」セクションに完全に準拠
  - 設計書に記載されたファイルのみ変更
  - 実装戦略（EXTEND）に従った拡張

- [x] **既存コードの規約に準拠している**
  - CLAUDE.mdの「Jenkinsパラメータ定義ルール」に準拠（DSLでパラメータ定義）
  - 既存のコーディングスタイル（インデント、命名規則）を維持
  - 既存パターン（choiceParam、エルビス演算子）を踏襲

- [x] **基本的なエラーハンドリングがある**
  - SSMパラメータ不存在時のエラーメッセージ（リージョン情報含む）
  - デフォルト値によるフォールバック機能（`?: 'ap-northeast-1'`）
  - エラーメッセージにリージョン情報を含めデバッグを容易化

- [x] **明らかなバグがない**
  - シンタックスエラーなし
  - 論理エラーなし（エルビス演算子によるデフォルト値設定）
  - 後方互換性を確保（既存のap-northeast-1動作を維持）

---

## 後方互換性の確保

### デフォルト値による互換性

1. **Jenkins DSL**: choiceParamの最初の選択肢（ap-northeast-1）がデフォルト値
2. **Jenkinsfile**: エルビス演算子（`params.AWS_REGION ?: 'ap-northeast-1'`）によるフォールバック
3. **既存動作**: パラメータ未指定時は ap-northeast-1 を使用し、既存動作を維持

### 既存機能への影響

- **影響なし**: 既存のap-northeast-1バックアップ機能は変更なし
- **回帰テスト**: Phase 6（testing）でIT-001〜IT-003により既存機能を確認予定

---

## 次のステップ

### Phase 5（test_implementation）

**Phase 4では実コードのみを実装しました。テストコードは Phase 5 で実装します。**

Phase 3で作成されたテストシナリオ（`.ai-workflow/issue-385/03_test_scenario/output/test-scenario.md`）を参照し、以下を実装：
- IT-010, IT-011: Pulumiスタックデプロイのテスト手順
- IT-001〜IT-009: 統合テストのテスト手順

### Phase 6（testing）

Phase 5で実装したテストコード（テストシナリオ）を実行し、結果を記録：
1. IT-010, IT-011: Pulumiスタックデプロイ（us-west-2）
2. IT-001〜IT-003: 回帰テスト（ap-northeast-1）
3. IT-004〜IT-006: 新規機能テスト（us-west-2）
4. IT-007: マトリクステスト（環境×リージョン）
5. IT-008, IT-009: エラーケーステスト

### Phase 7（documentation）

テスト結果を反映してドキュメントを更新：
- `jenkins/README.md`: SSMバックアップジョブの説明にマルチリージョン対応を追加
- 必要に応じて `jenkins/CONTRIBUTION.md` を更新

---

## 実装上の注意点

### Pulumiスタックデプロイ

実装完了後、以下の手順でPulumiスタックをデプロイする必要があります：

```bash
# us-west-2 dev環境
cd pulumi/jenkins-ssm-backup-s3
pulumi stack init us-west-2-dev
pulumi config set aws:region us-west-2
pulumi up

# us-west-2 prod環境
pulumi stack init us-west-2-prod
pulumi config set aws:region us-west-2
pulumi up
```

### Jenkinsシードジョブの実行

DSL変更を反映するため、シードジョブ（Admin_Jobs/job-creator）を実行する必要があります：
1. Jenkins UI → Admin_Jobs → job-creator を開く
2. 「Build Now」をクリック
3. ビルドが成功したことを確認
4. Admin_Jobs/ssm-backup に AWS_REGION パラメータが追加されたことを確認

### 動作確認の順序

1. **Pulumiデプロイ**: IT-010, IT-011（us-west-2のS3バケット・SSMパラメータ作成）
2. **シードジョブ実行**: DSL変更を反映
3. **ドライランモード**: IT-003, IT-006（S3アップロードなし）
4. **回帰テスト**: IT-001〜IT-003（ap-northeast-1）
5. **新規機能テスト**: IT-004〜IT-006（us-west-2）
6. **マトリクステスト**: IT-007（全組み合わせ）
7. **エラーケーステスト**: IT-008, IT-009

---

## 実装の品質

### コーディング規約への準拠

- [x] **CLAUDE.md準拠**: Jenkinsパラメータ定義ルール（DSLで定義）
- [x] **既存スタイル維持**: インデント、命名規則、既存パターンを踏襲
- [x] **コメント**: 日本語コメントを追加（AWS設定の説明）

### セキュリティ考慮

- [x] **クレデンシャル**: SSMパラメータストアで管理（変更なし）
- [x] **暗号化**: S3バケット暗号化（AES256、既存と同じ）
- [x] **HTTPS通信**: 強制（既存と同じ）
- [x] **IAM権限**: 両リージョンへのアクセス権限（事前確認必須）

### パフォーマンス考慮

- [x] **リージョン内通信**: 同一リージョン内のSSMパラメータストアとS3バケット間の通信（最小レイテンシ）
- [x] **処理フローの変更なし**: リージョン追加による処理の複雑化なし
- [x] **並列実行不要**: 単一リージョンのバックアップのみ

---

## まとめ

Issue #385「SSMバックアップジョブをマルチリージョン対応化（us-west-2対応追加）」の実装（Phase 4）が完了しました。

### 実装内容

1. **Pulumiスタック設定ファイル**: us-west-2用の新規ファイルを2つ作成
2. **Jenkins DSL**: AWS_REGIONパラメータを追加
3. **Jenkinsfile**: リージョン動的取得、ログ表示、エラーメッセージにリージョン情報を追加

### 品質保証

- すべての品質ゲートを満たしている
- 設計書に完全に準拠
- 既存コードの規約を踏襲
- 後方互換性を確保

### 次のアクション

1. **Phase 5（test_implementation）**: テストコード（テストシナリオ実行手順）の実装
2. **Phase 6（testing）**: テストシナリオの実行とテスト結果の記録
3. **Phase 7（documentation）**: ドキュメントの更新

---

**実装者**: AI Workflow Orchestrator
**実装日**: 2025年度
**レビュー状態**: 実装完了、Phase 5へ移行準備完了
