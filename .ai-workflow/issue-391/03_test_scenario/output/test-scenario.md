# Issue #391 テストシナリオ: SSMバックアップのマルチリージョン対応

## 1. テスト戦略サマリー
- **テスト戦略**: UNIT_INTEGRATION（Phase 2 決定事項に準拠）
- **テスト対象範囲**: Pulumiスタック（`pulumi/jenkins-ssm-backup-s3`）の多リージョンリソース生成ロジック、Jenkinsパイプライン（Pipeline/Jenkinsfile・DSL・シェルスクリプト）によるリージョン逐次バックアップ処理および通知フロー
- **テスト目的**:
  - FR-1/FR-2/NFRと整合したマルチリージョンS3バケット&SSMメタデータ生成の正当性を検証
  - FR-3/FR-4の逐次実行・失敗制御・UI互換性を担保
  - FR-5および監視観点として、ログ/通知の検証手順を明確化

## 2. Unitテストシナリオ（Pulumi Jest + Mocks）

### テストケース名: validateConfig_regions未設定_異常系
- **目的**: `regions` が未定義または空配列の場合に明示的な例外を発生させ、誤ったPulumi実行を防ぐ（FR-1保守性）
- **前提条件**: Pulumi Configに `regions` を設定しない
- **入力**: `pulumi.Config()` モック値 `{ projectName: "jenkins-infra", environment: "dev" }`
- **期待結果**: `validateConfig()` が `Error("No regions configured")` をthrowし、`pulumi.runtime.setMocks` 起動前にテストが失敗扱いとなる
- **テストデータ**: `__tests__/fixtures/config_no_regions.json`

### テストケース名: validateConfig_defaultRegion不整合_異常系
- **目的**: `defaultRegion` が `regions` に含まれない場合に検知して失敗させる（FR-2互換性）
- **前提条件**: Config: `regions = ["ap-northeast-1"]`, `defaultRegion = "us-west-2"`
- **入力**: Pulumi Configモック
- **期待結果**: `validateConfig()` が `Error("defaultRegion must be included in regions")` をthrow
- **テストデータ**: `__tests__/fixtures/config_invalid_default.json`

### テストケース名: createRegionalResources_正常系
- **目的**: 各リージョンでS3バケット・パブリックアクセスブロック・バケットポリシー・リージョン別SSMパラメータが生成されることを確認（FR-1, NFR-セキュリティ）
- **前提条件**: `regions = ["ap-northeast-1", "us-west-2"]`, `defaultRegion = "ap-northeast-1"`, `projectName = "jenkins-infra"`, `environment = "dev"`
- **入力**: Pulumi mocks (`aws:s3/bucket:Bucket` など) に期待リソースを返させ `require("../index")`
- **期待結果**:
  - バケット名が `<project>-ssm-backup-<env>-<accountId>-<region>` 形式で2リージョン分生成
  - SSE設定 (`AES256`) と PublicAccessBlock が両リージョンで有効
  - `/jenkins/dev/backup/{region}/s3-bucket-name` パラメータが2件作成
- **テストデータ**: `__tests__/fixtures/mock_account.ts`

### テストケース名: emitLegacyParameter_正常系
- **目的**: 旧SSMキー `/jenkins/{env}/backup/s3-bucket-name` が defaultRegion のバケット名に更新されることを確認（FR-2）
- **前提条件**: `defaultRegion = "ap-northeast-1"`, `bucketMap["ap-northeast-1"] = "jenkins-infra-...-ap-northeast-1"`
- **入力**: `emitLegacyParameter(bucketMap)` を実行
- **期待結果**: SSM Parameter resourceが1件追加され、`value` が defaultRegion のバケット名と一致
- **テストデータ**: `__tests__/fixtures/bucket_map.json`

### テストケース名: emitRegionMetadata_JSON整形_正常系
- **目的**: `/jenkins/{env}/backup/region-list` と `/jenkins/{env}/backup/default-region` がJSON/文字列ともに正しく出力されることを確認（FR-1, FR-2, FR-5通知手順依存メタデータ）
- **前提条件**: `regions = ["ap-northeast-1", "us-west-2"]`, `defaultRegion = "ap-northeast-1"`
- **入力**: `emitRegionMetadata(regions, defaultRegion, provider)` 実行
- **期待結果**:
  - `region-list` の `value` が `["ap-northeast-1","us-west-2"]` JSON文字列
  - `default-region` の `value` が `ap-northeast-1`
  - いずれも `ssmHomeRegion` プロバイダーで作成される
- **テストデータ**: `__tests__/fixtures/regions_dual.json`

### テストケース名: bucketMap_export_正常系
- **目的**: `index.ts` のエクスポート `bucketMap` が全リージョンの `{ region: bucketName }` を返すことを確認し、Jenkins統合テストの前提を担保（FR-3/NFR-保守性）
- **前提条件**: `regions` に複数リージョンを設定
- **入力**: `require("../index")` 後の `bucketMap.apply`
- **期待結果**: `bucketMap` の `keys` が `regions` と一致し、各値がPulumi生成バケット名
- **テストデータ**: `__tests__/fixtures/regions_triple.json`

## 3. Integrationテストシナリオ

### シナリオ名: JenkinsPipeline_多リージョン順次バックアップ_正常系
- **目的**: Jenkinsパイプラインがリージョン一覧を取り込み、ステージを動的に生成し順次成功するハッピーパスを検証（FR-3, NFR-パフォーマンス）
- **前提条件**:
  - jenkinsfile-runner Dockerイメージ取得済み
  - テスト用SSMレスポンス `tests/config/regions_sample.json` を `scripts/aws_mock.sh` で返却
  - `DRY_RUN=true` で実行
- **テスト手順**:
  1. `tests/jenkinsfile_runner.sh` を `MODE=success` で実行
  2. Pipeline Initializeで`regionList=["ap-northeast-1","us-west-2"]`が読み込まれる
  3. `stage("Backup ap-northeast-1")` → `collect_parameters.sh` が `data/ap-northeast-1` に成果物を生成
  4. `stage("Backup us-west-2")` が同様に完了
  5. `Finalize Report` で `region_summaries.json` がWORK_DIRに出力
- **期待結果**:
  - Jenkinsログに2つのBackupステージが順序通り表示
  - `region_summaries.json` に各リージョン `status: "SUCCESS"`, `parameterCount > 0`
  - `post { success { ... } }` でSlackダミーURLへHTTP 200のリクエスト送信（`tests/output/slack_payload.json`に書き出し）
- **確認項目**:
  - Jenkinsログ: ステージ順序と所要時間、`Region`ログが含まれること
  - Slackモック: 送信ペイロードのリージョン別サマリ
  - `collect_parameters.sh` 出力: 各リージョンディレクトリ配下に`parameter_names.txt`

### シナリオ名: JenkinsPipeline_途中失敗で後続停止_異常系
- **目的**: 2番目のリージョンでエラーが発生した場合に後続ステージが生成されず、Slack/メール通知が失敗内容を含むことを確認（FR-3, NFR-可用性）
- **前提条件**:
  - `tests/jenkinsfile_runner.sh MODE=fail_second_region`
  - `scripts/aws_mock.sh` が2番目のリージョンでexit 1を返しエラーメッセージ`"AccessDenied"`
- **テスト手順**:
  1. Pipeline Initializeでリージョンを読み込み
  2. `Backup ap-northeast-1` は成功
  3. `Backup us-west-2` 実行中に `collect_parameters.sh` が失敗し `error("Backup failed: AccessDenied")`
  4. Pipelineが即座に停止し `Finalize Report` はスキップ
  5. Post failureブロックがSlack/メールモックへ通知
- **期待結果**:
  - Jenkinsログに `Backup us-west-2` の失敗と `error` スタックトレースが記録
  - `regionSummaries` に `us-west-2` の `status: "FAILED"`, `failureMessage: "AccessDenied"`
  - Slackモックに `[FAIL]` 付き件名/本文、メールモックに失敗リージョン記載
- **確認項目**:
  - 後続リージョン（存在する場合）のステージが生成されていないこと
  - Slack/メールモックにRunbookリンクが含まれること
  - `tests/output/region_summaries_failure.json` に失敗詳細が保存されること

### シナリオ名: JenkinsDSL_UI互換性確認_正常系
- **目的**: `admin_ssm_backup_job.groovy` が既存ジョブパラメータを変更せず説明文とタイムアウトのみ更新されていることを確認（FR-4）
- **前提条件**:
  - Job DSL CLI または `jenkinsfile-runner` を `jobdsl` モードで実行可能
  - 既存ジョブ定義のsnapshot (`tests/config/jobdsl_baseline.xml`) を保持
- **テスト手順**:
  1. DSL seedジョブで `admin_ssm_backup_job.groovy` を適用し、生成XMLを `tests/output/admin_ssm_backup_job.xml` に保存
  2. 新旧XMLを `xmldiff` で比較
  3. `timeout` オプションと説明文以外の差分がないことを確認
- **期待結果**:
  - パラメータ定義 (`<hudson.model.StringParameterDefinition>`, `<ChoiceParameterDefinition>`) に差分なし
  - 新しい説明文に多リージョン対応の記述とRunbookリンクが追加
  - `options` 内 `timeout` が90分へ更新されている
- **確認項目**:
  - DSL適用時のログに警告が出ていないこと
  - Jenkins UIでリージョン選択パラメータが追加されていないこと（スモーク確認）

### シナリオ名: collectParameters_リージョン分離動作_正常系
- **目的**: `collect_parameters.sh` がリージョンごとのディレクトリを安全に扱い、既存ファイルを削除して最新の成果物だけを残すことを確認（FR-3/NFR-保守性）
- **前提条件**:
  - `DATA_DIR=/tmp/work/data/us-west-2` が既に存在し、旧ファイルが残っている
- **テスト手順**:
  1. `TARGET_REGION=us-west-2` `DRY_RUN=true` でスクリプトを起動
  2. 実行前に`touch /tmp/work/data/us-west-2/old.json`
  3. スクリプト完了後にディレクトリ内容を確認
- **期待結果**:
  - `old.json` が削除され、新たに `parameter_names.txt`, `parameters.json` のみ生成
  - ログに `Target Region: us-west-2` が出力
- **確認項目**:
  - `DATA_DIR` のパーミッションが保持されていること
  - エラー終了時にはクリーンアップが実施されないこと（別テストで確認済み）

## 4. テストデータ
- `__tests__/fixtures/config_no_regions.json`: `regions` 未設定のPulumi Config
- `__tests__/fixtures/config_invalid_default.json`: `defaultRegion` が `regions` と不整合な設定
- `__tests__/fixtures/regions_dual.json` / `regions_triple.json`: 多リージョン構成のConfigサンプル
- `__tests__/fixtures/mock_account.ts`: Pulumi mocks用の `accountId`・`region` 応答
- `__tests__/fixtures/bucket_map.json`: defaultRegionのバケット情報
- `jenkins/jobs/pipeline/admin/ssm-backup/tests/config/regions_sample.json`: Jenkins統合テスト用SSMレスポンスモック
- `tests/output/slack_payload.json`, `tests/output/region_summaries_failure.json`: Jenkins統合テストで生成される検証用成果物
- `tests/config/jobdsl_baseline.xml`: DSL差分比較のベースライン

## 5. テスト環境要件
- **ローカル/CI要件**:
  - Node.js 18系、npm、`ts-jest`/`@types/jest` をインストール済み
  - Pulumi CLI（プレビュー確認用、ユニットテストではモックを利用）
  - Docker 20.x 以上（jenkinsfile-runnerコンテナ実行用）
- **外部サービス/モック**:
  - AWSサービスは直接呼び出さず、Pulumi mocks と `scripts/aws_mock.sh` で全レスポンスをモック化
  - Slack/メール通知はHTTPサーバモックとローカルSMTPモック（`python -m smtpd` 等）を使用
- **CI/CD統合**:
  - Unitテスト: `npm test -- --runInBand`
  - Integrationテスト: `./jenkins/jobs/pipeline/admin/ssm-backup/tests/jenkinsfile_runner.sh MODE={success|fail_second_region}`
  - DSL差分検証: `./jenkins/jobs/pipeline/admin/ssm-backup/tests/jobdsl_verify.sh`（新規追加予定）

---

- [x] Phase 2の戦略（UNIT_INTEGRATION）に準拠したシナリオである  
- [x] 主要な正常系（Pulumi正常生成、Jenkins順次成功、DSL互換）がカバーされている  
- [x] 主要な異常系（Pulumi config不備、Jenkins途中失敗）がカバーされている  
- [x] 期待結果が各ケースで明確に記載されている  
