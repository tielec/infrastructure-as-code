# 変更履歴

> 📖 **親ドキュメント**: [README.md](../README.md)

## 2026-05-01: Jenkins バージョン LTS 固定 + アップグレード Runbook 整備

Jenkins のバージョン指定を `latest` から LTS 固定バージョン `2.555.1` に変更し、計画的なアップグレード運用を実現するための Runbook を整備しました。Issue #574（JCasC `excludeClientIPFromCrumb` 互換性事故）の根本原因対策として、「デプロイのたびに予期せずバージョンが上がる」問題を解消します。

- **対象Issue**: [#576](https://github.com/tielec/infrastructure-as-code/issues/576)
- **変更ファイル**:
  - `pulumi/jenkins-ssm-init/index.ts`: SSM パラメータ `jenkins-version` の値を `latest` から LTS 固定バージョン `2.555.1` に変更し、変更理由と Runbook 参照コメントを追加
  - `docs/jenkins-upgrade-runbook.md`: Jenkins アップグレード手順を7セクション（事前準備・dev/staging/prod 環境展開・ロールバック・CVE 対応特例・運用方針）でまとめた Runbook を新規作成
  - `jenkins/README.md`: 関連ドキュメントセクションにアップグレード Runbook へのリンクを追加
  - `CLAUDE.md`: Jenkins ベストプラクティスセクションにバージョン変更時の Runbook 参照ガイダンスを追加
  - `docs/operations/jenkins-management.md`: バージョン更新コマンド例付近と管理タスクテーブルに Runbook へのリンクを追加
  - `tests/issue-576/verify-version-format.sh`: バージョン文字列フォーマット（`X.Y.Z` 形式）を検証するスクリプトを新規作成
  - `tests/issue-576/verify-docs-integrity.sh`: Runbook 必須セクション存在と既存ドキュメントからのリンク有効性を検証するスクリプトを新規作成
  - `tests/integration/test_jenkins_version_pinning.py`: 上記すべての変更を静的検証する統合テスト（13件）を新規作成
- **主要な効果**:
  - SSM パラメータ `jenkins-version` を固定値にすることで、デプロイタイミングによるバージョン差異を排除し再現可能なデプロイを実現
  - dev → staging → prod の段階展開フローと1週間/3〜5日/24時間の安定稼働観察期間を Runbook として標準化
  - CVE 対応の特例フロー（Critical/High かつ exploitable の場合に同日対応を許容）を明文化
  - 既存の `controller-install.sh` は固定バージョン対応済みのため、コードの構造変更は不要
- **テスト結果**: TypeScript 構文チェック成功、統合テスト 13 件成功、バージョン文字列フォーマット検証成功、ドキュメント整合性検証成功

これにより、Jenkins バージョン管理が計画的・透明性の高い運用プロセスとなり、予期しないアップグレードに起因するインシデントを防止する基盤が整備されました。

## 2026-04-30: Jenkins Controller インスタンスタイプ t4g.large 化 + JavaMelody 導入

Jenkins Controller の CPU クレジット枯渇対策として、インスタンスタイプを `t4g.large` に変更し、JavaMelody（monitoring プラグイン）を導入しました。

- **対象Issue**: [#568](https://github.com/tielec/infrastructure-as-code/issues/568)
- **変更ファイル**:
  - `pulumi/jenkins-ssm-init/index.ts`: SSM パラメータ `controller-instance-type` のデフォルト値を `t4g.medium` から `t4g.large` に変更
  - `scripts/jenkins/groovy/install-plugins.groovy`: `monitoring`（JavaMelody）プラグインをプラグインリストに追加
  - `jenkins/README.md`: JavaMelody モニタリングセクションおよびデプロイ反映手順を追加
  - `tests/integration/test_jenkins_controller_monitoring.py`: 変更内容を検証する統合テスト（18件）を新規作成
  - `tests/issue-568/verify-instance-type.sh`: インスタンスタイプ値検証スクリプトを新規作成
  - `tests/issue-568/verify-plugins.sh`: プラグインリスト検証スクリプトを新規作成
- **主要機能**:
  - `t4g.large`（CPU ベースライン 60%）への変更により、平均 CPU 使用率 53% がベースライン内に収まり CPU クレジット課金をゼロ化
  - JavaMelody の `/monitoring` エンドポイントで CPU 内訳・JVM メモリ・GC・スレッド情報をリアルタイム可視化
  - Pulumi スタック依存関係（jenkins-ssm-init → jenkins-controller → jenkins-application）を考慮した段階的デプロイ手順を整備
- **コスト効果**:
  - CPU クレジット課金: $19/月 → $0/月（見込み）
  - 実コスト削減: 最大 $19/月（クレジット課金消滅分）
  - 補足: t4g.large はオンデマンド単価が t4g.medium の約 2 倍だが、既存 Savings Plan の余剰枠で吸収される範囲では追加課金は発生しない見込み。実際の Savings Plan 増額判断は実施後 1〜2 ヶ月のメトリクスを見て別タスクで対応する
- **テスト結果**: 統合テスト 18 件すべて成功、検証スクリプト（verify-instance-type.sh: 3件 PASS、verify-plugins.sh: 4件 PASS）、TypeScript ビルド成功

これにより、Jenkins Controller の CPU コスト構造が健全化され、JavaMelody によるメトリクスを活用した継続的な効果検証基盤が整備されました。

## 2026-04-01: Jenkins Agent EC2 Fleet への Amazon ECR Credential Helper 導入

Jenkins Agent EC2 Fleet インスタンスに Amazon ECR Credential Helper を導入し、ECR 認証を自動化しました。

- **対象Issue**: [#556](https://github.com/tielec/infrastructure-as-code/issues/556)
- **変更ファイル**:
  - `pulumi/jenkins-agent-ami/component-x86.yml`: ECR Credential Helper インストールステップ、config.json 生成、バリデーションを追加
  - `pulumi/jenkins-agent-ami/component-arm.yml`: x86版と同様の変更を ARM64 版に適用
  - `scripts/aws/userdata/jenkins-agent-setup.sh`: デフォルトAMI向けに credential-helper 導入と config.json 生成を追加
  - `scripts/aws/userdata/jenkins-agent-custom-ami.sh`: カスタムAMI向けに config.json のフォールバック生成を追加
  - `jenkins/DOCKER_IMAGES.md`: ECR credential-helper の利用方法と EC2 Fleet/ECS Fargate の認証方式の違いを追記
- **主要機能**:
  - AMI ビルド時に `amazon-ecr-credential-helper` パッケージをインストール
  - AWS アカウント ID を動的取得し `/home/jenkins/.docker/config.json` と `/root/.docker/config.json` を生成（`credHelpers` 設定）
  - IMDSv2 を使用したセキュアなメタデータアクセス
  - AMI ビルド時とEC2起動時の二重保護メカニズム（フォールバック設計）
- **効果**:
  - Jenkinsfile での `aws ecr get-login-password` による認証ボイラープレートが不要に
  - ECR トークン（有効期限12時間）の自動取得・更新により運用負荷を削減
  - EC2 Fleet Agent でのみ有効（ECS Fargate Agent は従来の認証方式を継続）
- **テスト結果**: 統合テスト 27件すべて成功（Python 18件 + ShellCheck 2件 + config.json バリデーション 7件）、成功率100%

これにより、EC2 Fleet 上での Docker イメージ操作が透過的に行えるようになり、開発者の生産性向上と保守コストの削減を実現しました。
## 2026-04-01: Lambda関数のNode.jsランタイムをnodejs22.xに更新

Lambda関数のNode.jsランタイム指定を最新LTSバージョンである`nodejs22.x`に統一的に更新しました。

- **対象Issue**: [#561](https://github.com/tielec/infrastructure-as-code/issues/561)
- **変更ファイル**:
  - `pulumi/components/src/lambda-packager/constants.ts`: `DEFAULT_RUNTIME`を`nodejs18.x`から`nodejs22.x`に更新
  - `pulumi/lambda-functions/components/lambda-factory.ts`: デフォルトランタイムを`nodejs20.x`から`nodejs22.x`に更新
  - `pulumi/lambda-functions/index.ts`: ランタイム指定2箇所を`nodejs20.x`から`nodejs22.x`に更新
  - `pulumi/components/src/lambda-packager/types.ts`: JSDocコメント内のランタイム例示を`nodejs18.x`から`nodejs22.x`に更新
  - `pulumi/components/README.md`: サンプルコード11箇所のランタイム指定を`nodejs18.x`から`nodejs22.x`に更新
- **主要な効果**:
  - Node.js 20.xのEOL（サポート終了）リスクを排除し、セキュリティパッチの継続的な提供を確保
  - プロジェクト内で混在していたランタイムバージョン（nodejs18.x/nodejs20.x）を`nodejs22.x`に統一し、バージョン不整合を解消
  - Node.js 22.x LTSは2027年4月までサポートされ、長期的な安定運用が可能
  - V8エンジンの改善によるパフォーマンス向上とWebSocket API改善等の最新機能を活用可能
- **互換性**: 使用中の全依存パッケージ（archiver v6.0.1, simple-git v3.20.0, @pulumi/aws v7.0.0等）はNode.js 22.xに対応済み
- **テスト結果**: ユニットテスト20件すべて成功、TypeScriptコンパイル成功、テストカバレッジ100%達成

これにより、Lambda関数のセキュリティと保守性が向上し、将来のNode.jsバージョン更新作業も容易になりました。

## 2025-02-07: GitHubリポジトリベースライン一括適用Adminジョブ追加

GitHubリポジトリに共通ベースライン設定を一括適用する管理ジョブ（Github_Repo_Baseline）を追加しました。

- **対象Issue**: [#554](https://github.com/tielec/infrastructure-as-code/issues/554)
- **新規ファイル**:
  - `jenkins/jobs/dsl/admin/admin_github_repo_baseline_job.groovy`: Job DSL定義（パラメータ、ジョブ設定）
  - `jenkins/jobs/pipeline/admin/github-repo-baseline/Jenkinsfile`: パイプライン実装（ステージ定義、ロジック）
  - `jenkins/jobs/pipeline/admin/github-repo-baseline/config/baseline-config.yaml`: ベースライン定義（テンプレート設定）
- **拡張ファイル**:
  - `jenkins/jobs/shared/src/jp/co/tielec/git/GitHubSettings.groovy`: Ruleset/BranchProtection/Security/Label操作メソッド追加
  - `jenkins/jobs/shared/vars/gitUtils.groovy`: ベースライン操作ファサードメソッド追加
  - `jenkins/jobs/pipeline/_seed/job-creator/job-config.yaml`: 新規ジョブエントリ追加
- **主要機能**:
  - ルールセット（Rulesets）の作成・更新・削除
  - ブランチ保護（Branch Protection）の設定
  - セキュリティ設定（Dependabot Alerts、Secret Scanning）の有効化
  - ラベル（Labels）の一括作成・同期
  - DRY_RUNモードによる事前確認と差分レポート
  - 複数リポジトリへの一括適用（Rate Limit対策付き）
- **テンプレート**: `default`（推奨設定）、`strict`（セキュリティ重視）、`minimal`（基本設定のみ）の3種類
- **テスト結果**: 統合テスト65件中62件成功、3件スキップ（外部ツール未インストールのため想定スキップ）、成功率100%

これにより、新規リポジトリ作成時のベースライン設定作業が自動化され、設定漏れゼロ・運用負荷削減・セキュリティ向上を実現しました。

## 2025-01-20: Lambda パッケージ作成時のzip出力ストリームエラーハンドリング改善

Pulumi Components の LambdaPackage で使用される ZipArchiver において、zip出力ストリームのエラー未処理によるデプロイハング問題を修正しました。

- **対象Issue**: [#549](https://github.com/tielec/infrastructure-as-code/issues/549)
- **修正内容**:
  - `ZipArchiver.createArchive()` メソッドに出力ストリーム（`output`）のエラーイベントリスナーを追加
  - エラー発生時にアーカイブリソースを適切に破棄（`archive.destroy()`）
  - エラー発生時にPromiseを適切にrejectしてハング防止
  - エラー内容の詳細ログ出力（`pulumi.log.error()`）
- **対象ファイル**: `pulumi/components/src/lambda-packager/zip-archiver.ts`
- **効果**: 権限不足やディスク枯渇時のLambdaパッケージ作成エラーが即座に検知され、Pulumiデプロイのタイムアウトを防止
- **テスト結果**: 単体テスト 8件すべて成功（成功率100%）

これにより、CI/CDパイプラインでのLambdaデプロイがより安定し、エラー発生時の原因特定が容易になりました。

## 2025-12-27: Jenkins Agent AMI の CloudWatch Agent CPU メトリクス共通化

Jenkins Agent AMI に CloudWatch Agent 設定テンプレートを追加し、CPU/メモリメトリクスを AutoScalingGroup 単位で 60 秒間隔収集するよう ARM/x86 間で統一しました。

- **対象Issue**: [#544](https://github.com/tielec/infrastructure-as-code/issues/544)
- **変更ファイル**:
  - `pulumi/jenkins-agent-ami/templates/cloudwatch-agent-config.json`: CPU（active/user/system/iowait）とメモリ（used/available）を共通定義し ASG ディメンションを付与
  - `pulumi/jenkins-agent-ami/component-arm.yml` / `pulumi/jenkins-agent-ami/component-x86.yml`: テンプレートをインライン展開し Translator 検証ステップを追加
  - `pulumi/jenkins-agent-ami/index.ts`: テンプレート読み込みとインデント保持の置換処理を実装
- **効果**: CloudWatch Agent 設定の差分を排除し、Translator による構文検証で AMI ビルド失敗を早期検知。ASG 単位のダッシュボード/アラームが即時利用可能に
- **テスト結果**: `pytest tests/integration/test_jenkins_agent_ami_cloudwatch.py -q` を実行し 5 件すべて成功

## 2025-01-20: SpotFleetエージェントのCPUクレジットUnlimited設定適用完了

Jenkins Agent SpotFleetで利用するt3/t3a/t4g系インスタンスにCPUクレジットUnlimited設定を適用しました。

- **対象Issue**: [#542](https://github.com/tielec/infrastructure-as-code/issues/542)
- **変更ファイル**:
  - `pulumi/jenkins-agent/index.ts`: x86_64/ARM64 LaunchTemplateに`creditSpecification.cpuCredits="unlimited"`を追加
  - `docs/architecture/infrastructure.md`: CPUクレジット設定の詳細説明を追記
- **効果**: CI/CD高負荷時のCPUスロットリング防止により、ビルド/テスト時間の安定化とタイムアウト回避を実現
- **コスト影響**: ベースライン超過分の追加課金が発生するため、CloudWatch `CPUSurplusCreditBalance`監視を推奨
- **適用方法**: Pulumiスタック更新でLaunchTemplate新バージョンを作成し、新規インスタンスからローリング適用
- **テスト結果**: 統合テスト 7件すべて成功（成功率100%）

これにより、Jenkins CI/CDパイプラインの信頼性と性能が向上し、開発者の待ち時間短縮が実現されました。

## 2024-01-23: ECS Fargateエージェント構成のドキュメント化完了

Jenkins Agent infrastructure の ECS Fargate 構成に関するドキュメントを整備しました。

- **対象ドキュメント**: `docs/architecture/infrastructure.md`
- **追加内容**:
  - ECS Fargate エージェント専用セクション（構成詳細、SSMパラメータ一覧）
  - SpotFleet と ECS Fargate の併存関係および使い分け指針
  - `docker/jenkins-agent-ecs` ディレクトリの役割と利用手順
- **更新ドキュメント**: `jenkins/README.md` - ECS Fargateエージェント情報の詳細化
- **関連Issue**: [#540](https://github.com/tielec/infrastructure-as-code/issues/540)
- **実装との整合性**: 統合テストで検証済み（100%成功率）

これにより、エージェント管理やトラブルシューティング時の正確な手順参照が可能となり、運用効率が向上しました。

## 2025-10-16: AI Workflow V1 (Python版) の削除完了

AI Workflow V2 (TypeScript版) への移行が完了し、V1 (Python版) を削除しました。

- **削除対象**: `scripts/ai-workflow/` ディレクトリ全体（127ファイル）
- **削除実行日**: 2025年10月17日
- **削除コミット**: `0dce7388f878bca303457ca3707dbb78b39929c9`
- **バックアップ**: `archive/ai-workflow-v1-python` ブランチに保存
- **復元時間**: 1秒未満（Issue #411で検証済み）
- **V2の場所**: `scripts/ai-workflow-v2/`
- **V2のドキュメント**: [scripts/ai-workflow-v2/README.md](scripts/ai-workflow-v2/README.md)
- **関連Issue**: [#411](https://github.com/tielec/infrastructure-as-code/issues/411), [#415](https://github.com/tielec/infrastructure-as-code/issues/415)

必要に応じて、以下のコマンドでV1を復元できます（1秒未満）：

```bash
git checkout archive/ai-workflow-v1-python -- scripts/ai-workflow/
```

## 関連ドキュメント

- [README.md](../README.md)
