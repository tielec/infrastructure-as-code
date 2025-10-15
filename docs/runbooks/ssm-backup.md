# SSM Parameter Store Backup Runbook

## 概要
- 対象ジョブ: `Admin_Jobs/admin_ssm_backup_job`
- 目的: Pulumi が生成した各リージョンの S3 バケットへ、SSM Parameter Store の内容を暗号化した JSON として日次バックアップする。
- リージョン構成: Pulumi Config (`pulumi/jenkins-ssm-backup-s3/Pulumi.<env>.yaml`) の `regions` 配列に従い動的に決定。
- メタデータ保管: `/jenkins/<env>/backup/` プレフィックスの SSM パラメータ（`region-list`, `default-region`, `s3-bucket-name`, `<region>/s3-bucket-name`）。

## 運用手順
1. Jenkins ジョブが自動実行（毎日 JST 22:00）。開始時に `Initialize` ステージでリージョン一覧とデフォルトリージョンを SSM から取得。
2. `Backup <region>` ステージがリージョンごとに逐次実行され、`collect_parameters.sh` を用いて SSM パラメータを収集。
3. 取得した JSON は `s3://<bucket>/<YYYY-MM-DD>/<region>/ssm-backup-<env>-<region>-<timestamp>.json` にアップロードされ、`latest-<region>.txt`（デフォルトリージョンは互換用に `latest.txt` も更新）を発行。
4. 実行結果は `backup-work/region_summaries.json` に出力され、アーティファクトとして保存。Slack/メール通知には同ファイルの要約を添付。

## リージョン追加・削除手順
1. `pulumi/jenkins-ssm-backup-s3/Pulumi.<env>.yaml` の `regions` 配列を更新し、`defaultRegion` と `ssmHomeRegion` を必要に応じて調整。
2. Pulumi スタックディレクトリで `npm install`（依存未導入時）後、`npm run build` → `pulumi preview` を実施し差分を確認。
3. 変更内容をレビュー後、`pulumi up` を本番／ステージング順に適用。
4. Jenkins ジョブをドライラン（`DRY_RUN=true`）で実行し、`Backup <region>` ステージが追加リージョンを認識することを確認。
5. 運用チームへ Slack `#infra-announcements` でリージョン変更点と実施日時を共有。

## ロールバック手順
1. Pulumi Config を直前のコミットへ戻し `pulumi up` を実行。不要になった S3 バケットと SSM パラメータが削除されることを `pulumi preview` で確認。
2. Jenkins ジョブを手動実行し、`region_summaries.json` に旧構成のみが記録されることを確認。
3. 影響が大きい場合は Runbook の通知テンプレートを利用し、CLI 利用者とオンコール SRE へ速やかに連絡。

## 監視・通知
- 成功時: Slack `#infra-backup-alerts` にリージョン別件数・処理時間を通知。メール `ops-alerts@example.com` に同内容のサマリーを送付。
- 失敗時: 失敗リージョンの `message` が通知ペイロードに含まれる。30 分以内に一次報告、復旧後 1 営業日以内に事後報告を行う。
- 参照ログ: Jenkins 実行ログ・`backup-work/region_summaries.json`・S3 バケットの `latest-<region>.txt`。

## トラブルシューティング
| 症状 | 対処 |
| ---- | ---- |
| `Region list parameter ... is missing` | Pulumi スタックが未適用。`pulumi config get regions` と SSM の `/backup/region-list` を確認。 |
| `Bucket definition missing for region` | `/backup/<region>/s3-bucket-name` の作成漏れ。Pulumi Config のリージョン一覧と SSM を照合。 |
| `Backup file was not created` | `collect_parameters.sh` の AWS 認証／フィルタ設定を確認。`DATA_DIR/<region>` に生成物があるか検証。 |
| S3 アップロードに失敗 | `aws s3 cp` コマンドのエラー詳細をログで確認。IAM 権限またはリージョン設定を見直し。 |

## 参考コマンド
```bash
# Pulumi Stack でリージョンを確認
pulumi config get regions --path --stack <env>

# Jenkins アーティファクトからサマリーを取得
aws s3 cp s3://<bucket>/<YYYY-MM-DD>/<region>/ssm-backup-<env>-<region>-<timestamp>.json ./
```
