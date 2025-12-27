# 変更履歴

> 📖 **親ドキュメント**: [README.md](../README.md)

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
