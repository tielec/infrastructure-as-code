# Jenkins Agent CPU 監視ガイド

Jenkins Agent AMI へ追加した CloudWatch Agent の CPU メトリクスを活用し、AutoScalingGroup 単位で負荷を可視化・検知するための初期値を記載します。

## ダッシュボード初期値
- 対象ディメンション: `AutoScalingGroupName`（ARM/x86 共通）
- 推奨ウィジェット:
  - CPU 使用率 (Average) 1 分粒度、AutoScalingGroupName で並列表示
  - CPU 使用率 (p95) 1 分粒度で突発的なスパイクを把握
  - CPU コア別の `cpu_usage_system` / `cpu_usage_user` 比率を 1 分粒度で並列表示
- フィルタ例: `jenkins-agent-*-asg` をワイルドカード指定し、ARM/x86 混在を許容

## アラーム初期値（例）
- 条件: CPU 使用率が **80% 超過** の状態が 5 分 (約 5 minutes) 継続
- ディメンション: `AutoScalingGroupName`（Auto Scaling グループ単位で通知）
- 推奨アクション: Slack/PagerDuty 等の通知トピックへ連携
- 備考: Translate 済み設定で 60 秒間隔収集を前提としています

### しきい値の調整手順
1. 運用フェーズで実測した負荷に合わせ、閾値（例: 75%〜90%）と継続時間（例: 5〜10 分）を調整してください（必要に応じていつでも adjust 可能）。
2. AutoScalingGroup 名が増減した場合は、ダッシュボードのワイルドカードフィルタを更新します。
3. 設定変更は IaC 管理（Pulumi 側のダッシュボード/アラーム定義追加時）と手動運用の双方で実施可能です。

## ログ/検証
- CloudWatch Agent 設定ファイルは AMI ビルド時に Translator で検証済みです。
- アラームやダッシュボードの更新履歴は CI のプレビュー結果を確認し、意図しないリソース追加がないことを確認してください。
