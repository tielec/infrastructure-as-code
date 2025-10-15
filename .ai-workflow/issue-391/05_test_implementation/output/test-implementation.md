# テストコード実装ログ

## 実装サマリー
- テスト戦略: UNIT_INTEGRATION
- テストファイル数: 3個
- テストケース数: 9個

## テストファイル一覧

### 新規作成
- `pulumi/jenkins-ssm-backup-s3/__tests__/index.test.ts`: Pulumiスタックのユニットテスト。Config検証エラー、多リージョンバケット生成、SSMメタデータ/互換キー、`bucketMap` エクスポートを検証。
- `jenkins/jobs/pipeline/admin/ssm-backup/tests/test_pipeline_runner.py`: Jenkinsパイプラインの統合テスト。モックAWSと`collect_parameters.sh`を組み合わせて成功/途中失敗シナリオをシミュレート。
- `jenkins/jobs/pipeline/admin/ssm-backup/tests/test_collect_parameters.py`: `collect_parameters.sh` のディレクトリ初期化と成果物生成を検証する統合テスト。

## テストケース詳細

### ファイル: pulumi/jenkins-ssm-backup-s3/__tests__/index.test.ts
- **throws when regions are not configured**: `regions` 未設定時に明示的な例外が出ることを確認。
- **throws when defaultRegion is not part of regions**: `defaultRegion` がリージョン配列に含まれない場合に失敗することを確認。
- **creates regional S3 buckets with encryption and public access block**: 各リージョンで暗号化・公開遮断設定付きバケットが生成されることを確認。
- **emits region-specific SSM parameters and legacy parameter for default region**: リージョン別SSMパラメータとレガシー互換キーが正しく出力されることを確認。
- **publishes region metadata list and default region parameters**: リージョン一覧・デフォルトリージョンのメタデータがSSMに登録されることを確認。
- **exports bucketMap containing all configured regions**: `bucketMap` が全リージョンのバケット名を返すことを確認。

### ファイル: jenkins/jobs/pipeline/admin/ssm-backup/tests/test_pipeline_runner.py
- **test_success_sequence_creates_summaries_for_all_regions**: モックAWSで全リージョン成功時にサマリーが生成されることを確認。
- **test_failure_on_second_region_marks_summary_and_stops**: 2番目のリージョンでAWSエラーが発生した場合に処理が停止し失敗情報が残ることを確認。

### ファイル: jenkins/jobs/pipeline/admin/ssm-backup/tests/test_collect_parameters.py
- **test_region_directory_is_reset_and_artifacts_created**: リージョンディレクトリが初期化され、`backup.json`・`summary.json`・`parameter_names.txt` が生成されることを確認。

## 次のステップ
- Phase 6で `npm test -- --runInBand` および `python -m unittest discover jenkins/jobs/pipeline/admin/ssm-backup/tests` を実行して動作を確認。
