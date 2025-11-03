# 要件定義書: Issue #437

**タイトル**: [TASK] Jenkins AgentのCloudWatchメモリモニタリング実装
**Issue番号**: #437
**作成日**: 2025-01-XX
**バージョン**: 1.0

---

## 0. Planning Documentの確認

Planning Phaseで策定された開発計画を確認しました：

### 実装戦略
- **EXTEND**: 既存インフラへの機能追加
  - Pulumiスタック `jenkins-agent` のIAMロール定義に権限追加
  - Ansibleロール `jenkins_agent_ami` にCloudWatch Agentセットアップタスクを追加
  - CloudWatch Agent設定ファイルをテンプレート配置

### テスト戦略
- **INTEGRATION_ONLY**: インテグレーションテストのみ実施
  - AMIビルド成功確認
  - CloudWatch Agentサービス起動確認
  - CloudWatchコンソールでメトリクス確認
  - インスタンス入れ替わり後のメトリクス継続確認

### テストコード戦略
- **CREATE_TEST**: 独立したテストプレイブックを作成
  - `ansible/playbooks/test/test-cloudwatch-agent.yml` を新規作成
  - 既存テストとは独立した関心事として管理

### 複雑度とスケジュール
- **複雑度**: 中程度
- **見積もり工数**: 8~12時間
- **主要なリスク**: コスト最適化の実装ミス、AMI作成プロセスへの影響

この計画に基づき、以下の要件定義を実施します。

---

## 1. 概要

### 1.1. 背景

Jenkins Agentは、CI/CDパイプラインの実行環境として重要な役割を果たします。本プロジェクトでは、EC2 SpotFleetを使用してコスト効率の高いエージェント環境を提供していますが、現状ではメモリ使用状況の可視化がされていません。

安定稼働を実現するため、CloudWatchを使用してメモリ使用状況を監視・可視化する必要があります。特に、スポットインスタンスは頻繁に入れ替わるため、コスト最適化を考慮した設計が重要です。

### 1.2. 目的

- Jenkins Agentのメモリ使用状況をCloudWatchで可視化する
- スポットインスタンスの特性を考慮したコスト効率の高いメトリクス収集を実現する
- インスタンス入れ替わり時もメトリクスの継続性を保証する

### 1.3. ビジネス価値・技術的価値

**ビジネス価値**:
- メモリ不足による障害の予防（ビルド失敗の削減）
- 運用監視コストの最適化（約$0.60-1.0/月で固定コスト）
- 安定稼働による開発チームの生産性向上

**技術的価値**:
- インフラ監視のベストプラクティス実装
- スポットインスタンス環境での監視パターンの確立
- CloudWatch Agentの標準的な実装方法の提供

---

## 2. 機能要件

### FR-1: IAM権限の追加（優先度: 高）

**説明**: Jenkins Agent IAMロールにCloudWatch Agent用の権限を追加する。

**詳細要件**:
- `pulumi/jenkins-agent/index.ts` のIAMロール定義を修正
- `CloudWatchAgentServerPolicy` マネージドポリシーをアタッチ
- 既存の権限（SSM、EC2、S3等）を保持したまま追加

**依存関係**:
- 既存の `jenkins-agent` Pulumiスタックが存在すること

**受け入れ基準**: 「6. 受け入れ基準」セクションを参照

---

### FR-2: CloudWatch Agentのインストールと設定（優先度: 高）

**説明**: Jenkins Agent AMIにCloudWatch Agentをプリインストールし、設定ファイルを配置する。

**詳細要件**:
- `ansible/roles/jenkins_agent_ami/tasks/setup_cloudwatch_agent.yml` を新規作成
- CloudWatch Agentパッケージ（`amazon-cloudwatch-agent`）をインストール
- 設定ファイル（`/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json`）を配置
- CloudWatch Agentサービス（`amazon-cloudwatch-agent`）を起動・有効化
- systemdサービスとして登録し、OS再起動時に自動起動

**依存関係**:
- FR-1（IAM権限追加）が完了していること
- Ansibleロール `jenkins_agent_ami` が存在すること

**受け入れ基準**: 「6. 受け入れ基準」セクションを参照

---

### FR-3: メモリメトリクスの収集設定（優先度: 高）

**説明**: CloudWatch Agentがメモリメトリクスを収集し、CloudWatchに送信する設定を実装する。

**詳細要件**:
- **収集メトリクス**:
  - `mem_used_percent`: メモリ使用率（パーセント）
  - `mem_used`: メモリ使用量（MB）
  - `mem_available`: メモリ空き容量（MB）
- **Namespace**: `CWAgent`
- **Dimension**: `AutoScalingGroupName` のみ（インスタンスIDを含めない）
- **送信間隔**: 60秒（CloudWatch Agentデフォルト）
- **集約方法**: AutoScalingGroup全体の平均値として集約

**重要な設計判断**:
- インスタンスIDをDimensionに含めない理由: スポットインスタンスが頻繁に入れ替わるため、インスタンスIDごとにメトリクスが蓄積されるとコストが爆発的に増加する（10回入れ替わりで約$6/月 → ASG名のみで約$0.60-1.0/月に削減）

**依存関係**:
- FR-2（CloudWatch Agentインストール）が完了していること

**受け入れ基準**: 「6. 受け入れ基準」セクションを参照

---

### FR-4: CloudWatch Agent設定テンプレートの作成（優先度: 高）

**説明**: Ansible Jinja2テンプレートとしてCloudWatch Agent設定ファイルを作成する。

**詳細要件**:
- `ansible/roles/jenkins_agent_ami/templates/cloudwatch-agent-config.json.j2` を新規作成
- JSON形式でCloudWatch Agent設定を記述
- `append_dimensions` セクションで `AutoScalingGroupName` を明示的に指定
- インスタンスID等のデフォルトDimensionを含めない設定

**設定例**:
```json
{
  "metrics": {
    "namespace": "CWAgent",
    "metrics_collected": {
      "mem": {
        "measurement": [
          {"name": "mem_used_percent"},
          {"name": "mem_used"},
          {"name": "mem_available"}
        ],
        "metrics_collection_interval": 60
      }
    },
    "append_dimensions": {
      "AutoScalingGroupName": "${aws:AutoScalingGroupName}"
    }
  }
}
```

**依存関係**:
- なし（テンプレートファイル作成のみ）

**受け入れ基準**: 「6. 受け入れ基準」セクションを参照

---

### FR-5: AMI再作成プロセスへの統合（優先度: 高）

**説明**: CloudWatch Agentのセットアップを既存のAMIビルドプロセスに統合する。

**詳細要件**:
- `ansible/roles/jenkins_agent_ami/tasks/deploy.yml` を修正
- `setup_cloudwatch_agent.yml` タスクを呼び出すステップを追加
- AMIビルド（AWS Image Builder）が成功することを確認
- 既存のAMIビルドプロセスに影響を与えない

**依存関係**:
- FR-2（CloudWatch Agentセットアップタスク作成）が完了していること
- FR-4（設定テンプレート作成）が完了していること

**受け入れ基準**: 「6. 受け入れ基準」セクションを参照

---

### FR-6: テストプレイブックの作成（優先度: 中）

**説明**: CloudWatch Agentの動作を検証するための独立したテストプレイブックを作成する。

**詳細要件**:
- `ansible/playbooks/test/test-cloudwatch-agent.yml` を新規作成
- 以下の検証項目を含む:
  - CloudWatch Agentサービスの起動状態確認（`systemctl status`）
  - 設定ファイルの存在確認
  - メトリクスがCloudWatchに送信されているか確認（AWS CLI）
  - Dimension設定の正確性確認（`AutoScalingGroupName`のみ）
- テスト実行結果を分かりやすく出力

**依存関係**:
- FR-2〜FR-5が完了していること
- dev環境にJenkins Agentがデプロイされていること

**受け入れ基準**: 「6. 受け入れ基準」セクションを参照

---

### FR-7: ドキュメント更新（優先度: 中）

**説明**: CloudWatchモニタリング機能の追加を既存ドキュメントに反映する。

**詳細要件**:
- `ansible/README.md` にCloudWatchモニタリング機能を追加
  - 機能概要の説明
  - 収集メトリクスの説明
  - CloudWatchコンソールでの確認手順
  - コスト情報（約$0.60-1.0/月、固定コスト）
  - トラブルシューティング情報
- 必要に応じて `pulumi/jenkins-agent/README.md` も更新

**依存関係**:
- FR-1〜FR-6が完了していること

**受け入れ基準**: 「6. 受け入れ基準」セクションを参照

---

## 3. 非機能要件

### 3.1. パフォーマンス要件

- **NFR-1**: CloudWatch Agentがメトリクスを60秒間隔で送信すること
- **NFR-2**: CloudWatch Agentのメモリオーバーヘッドが50MB以下であること
- **NFR-3**: メトリクス送信がJenkinsビルドパフォーマンスに影響を与えないこと（CPU使用率1%以下）

### 3.2. セキュリティ要件

- **NFR-4**: CloudWatch Agentの認証にIAMロールを使用すること（クレデンシャルのハードコーディング禁止）
- **NFR-5**: IAMロールは最小権限の原則に従い、必要な権限のみを付与すること
- **NFR-6**: CloudWatch Agentのログファイルに機密情報を出力しないこと

### 3.3. 可用性・信頼性要件

- **NFR-7**: CloudWatch Agentサービスがインスタンス起動時に自動的に起動すること
- **NFR-8**: CloudWatch Agentの障害がJenkinsビルド実行に影響を与えないこと
- **NFR-9**: インスタンス入れ替わり後も、メトリクス収集が継続すること
- **NFR-10**: メトリクスの欠損率が5%以下であること

### 3.4. 保守性・拡張性要件

- **NFR-11**: CloudWatch Agent設定がAnsibleテンプレートで管理され、バージョン管理されていること
- **NFR-12**: 将来的に他のメトリクス（CPU、ディスク）を追加しやすい設計であること
- **NFR-13**: CloudWatch Agentのバージョンアップが容易に実施できること

### 3.5. コスト要件

- **NFR-14**: CloudWatchカスタムメトリクスのコストが月額$1.5以下であること
  - 目標: 約$0.60-1.0/月（ASG名のみをDimensionに使用）
  - 上限: $1.5/月（安全マージンを含む）
- **NFR-15**: インスタンス台数の増減によってコストが大幅に増加しないこと
- **NFR-16**: メトリクス数が固定され、予測可能なコストであること

---

## 4. 制約事項

### 4.1. 技術的制約

- **C-1**: Amazon Linux 2023を使用すること（既存環境との整合性）
- **C-2**: CloudWatch Agentの公式パッケージ（`amazon-cloudwatch-agent`）を使用すること
- **C-3**: AMIビルドプロセスはAWS Image Builderを使用すること（既存プロセスとの整合性）
- **C-4**: Pulumiスタックは既存の `jenkins-agent` スタックを拡張すること（新規スタック作成禁止）
- **C-5**: Ansibleロールは既存の `jenkins_agent_ami` ロールを拡張すること（新規ロール作成禁止）

### 4.2. リソース制約

- **C-6**: 実装工数は8~12時間以内（Planning Documentに基づく）
- **C-7**: AMIビルド時間は30~45分以内（既存のビルド時間を超えない）
- **C-8**: コストは月額$1.5以下（NFR-14の制約）

### 4.3. ポリシー制約

- **C-9**: コーディング規約はCLAUDE.md、CONTRIBUTION.mdに準拠すること
- **C-10**: Ansibleプレイブックはヘルパーロール（`aws_cli_helper`、`pulumi_helper`等）を活用すること
- **C-11**: Pulumiリソースには必須タグ（Name, Environment, ManagedBy, Project）を付与すること

### 4.4. 運用制約

- **C-12**: アラート設定は実装しないこと（メトリクス収集・可視化のみ）
- **C-13**: 既存のJenkins Agent環境を停止せずに実装すること（ダウンタイムなし）
- **C-14**: dev環境で十分なテストを実施してから本番環境に適用すること

---

## 5. 前提条件

### 5.1. システム環境

- **P-1**: Jenkins Agent環境が既にデプロイされていること
  - `jenkins-agent` Pulumiスタックが存在
  - `jenkins_agent_ami` Ansibleロールが存在
- **P-2**: AWS Image Builderパイプラインが正常に動作していること
- **P-3**: 踏み台サーバー（bootstrap環境）が構築済みであること

### 5.2. 依存コンポーネント

- **P-4**: Pulumi S3バックエンドが設定されていること
- **P-5**: SSM Parameter Storeに必要なパラメータが格納されていること
- **P-6**: Ansible実行環境にboto3、botocore、AWS CLIがインストールされていること
- **P-7**: Pulumiパスフレーズが環境変数またはSSMに設定されていること

### 5.3. 外部システム連携

- **P-8**: AWS CloudWatch APIにアクセス可能であること
- **P-9**: EC2インスタンスからCloudWatchエンドポイントへのアクセスが許可されていること
- **P-10**: IAMロールがCloudWatch Agentの実行に必要な権限を持つこと

---

## 6. 受け入れ基準

### FR-1: IAM権限の追加

**Given**: `jenkins-agent` Pulumiスタックが存在する
**When**: Pulumiスタックをデプロイする
**Then**:
- IAMロールに `CloudWatchAgentServerPolicy` がアタッチされている
- `pulumi preview` でエラーが発生しない
- `pulumi up` が成功する
- 既存の権限（SSM、EC2、S3等）が維持されている

---

### FR-2: CloudWatch Agentのインストールと設定

**Given**: AMIビルドプロセスが実行される
**When**: Ansibleロール `jenkins_agent_ami` が実行される
**Then**:
- CloudWatch Agentパッケージがインストールされている
- 設定ファイル `/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json` が存在する
- CloudWatch Agentサービスが起動している（`systemctl status amazon-cloudwatch-agent` でactive）
- CloudWatch Agentサービスが有効化されている（OS再起動時に自動起動）

---

### FR-3: メモリメトリクスの収集設定

**Given**: CloudWatch Agentが起動している
**When**: 1分以上待機する
**Then**:
- CloudWatchコンソールで以下のメトリクスが確認できる:
  - Namespace: `CWAgent`
  - Metric: `mem_used_percent`
  - Metric: `mem_used`
  - Metric: `mem_available`
  - Dimension: `AutoScalingGroupName` のみ（インスタンスIDを含まない）
- メトリクスが60秒間隔で送信されている

---

### FR-4: CloudWatch Agent設定テンプレートの作成

**Given**: 設定テンプレートファイルが存在する
**When**: JSON構文チェックを実行する
**Then**:
- JSON構文が正しい（`jq` でパースできる）
- `append_dimensions` セクションに `AutoScalingGroupName` が定義されている
- インスタンスID等のデフォルトDimensionが含まれていない

---

### FR-5: AMI再作成プロセスへの統合

**Given**: CloudWatch Agentセットアップタスクが実装されている
**When**: Jenkins Agent AMIを再作成する
**Then**:
- AMIビルドが成功する（AWS Image Builder パイプライン実行成功）
- AMIビルド時間が既存プロセスと同等（30~45分以内）
- 新規AMIから起動したインスタンスでCloudWatch Agentが動作している

---

### FR-6: テストプレイブックの作成

**Given**: テストプレイブック `test-cloudwatch-agent.yml` が存在する
**When**: テストプレイブックを実行する
**Then**:
- すべてのテストタスクが成功する
- CloudWatch Agentサービスの起動状態が確認できる
- 設定ファイルの存在が確認できる
- メトリクスがCloudWatchに送信されていることが確認できる
- Dimension設定の正確性が確認できる

---

### FR-7: ドキュメント更新

**Given**: CloudWatchモニタリング機能が実装されている
**When**: `ansible/README.md` を確認する
**Then**:
- CloudWatchモニタリング機能の説明が記載されている
- 収集メトリクスの一覧が記載されている
- CloudWatchコンソールでの確認手順が記載されている
- コスト情報（約$0.60-1.0/月）が記載されている
- トラブルシューティング情報が記載されている

---

### インテグレーションテスト（全体）

**Given**: すべての実装が完了している
**When**: dev環境にデプロイする
**Then**:
- AMIビルドが成功する
- 新規AMIから起動したインスタンスでCloudWatch Agentが自動起動する
- CloudWatchコンソールでメトリクスが確認できる
- インスタンス入れ替わり後もメトリクスが継続して収集される
- コストが約$0.60-1.0/月で推移する（1週間後に確認）

---

## 7. スコープ外

以下の項目は本Issueのスコープ外とし、将来的な拡張候補とします：

### 7.1. 明確にスコープ外とする事項

- **アラート設定**: CloudWatchアラームの設定（Issue本文で明示的に不要と記載）
- **ダッシュボード作成**: CloudWatchダッシュボードの作成（メトリクス確認はコンソールで実施）
- **他のメトリクス収集**: CPU、ディスク、ネットワーク等のメトリクス（メモリのみ）
- **ログ収集**: CloudWatch Logsへのログ転送（メトリクス収集のみ）
- **本番環境デプロイ**: dev環境での検証のみ（本番環境デプロイは別Issue）

### 7.2. 将来的な拡張候補

- **拡張候補-1**: CPU使用率のメトリクス収集
- **拡張候補-2**: ディスク使用率のメトリクス収集
- **拡張候補-3**: メモリ使用率アラームの設定（閾値超過時の通知）
- **拡張候補-4**: CloudWatchダッシュボードによる可視化
- **拡張候補-5**: カスタムメトリクスの追加（JVMヒープメモリ等）
- **拡張候補-6**: CloudWatch Logsへのアプリケーションログ転送

---

## 8. 補足情報

### 8.1. コスト最適化の重要性

本実装の最も重要な設計判断は、**Dimensionを `AutoScalingGroupName` のみに制限すること**です。

**理由**:
- Jenkins Agentはスポットインスタンスのため、頻繁に入れ替わる
- デフォルト設定ではインスタンスIDがDimensionに含まれる
- インスタンスが10回入れ替わると、20メトリクス（2メトリクス × 10インスタンス）が蓄積
- CloudWatchカスタムメトリクスは$0.30/メトリクス/月のため、約$6/月のコスト

**対策**:
- `append_dimensions` で `AutoScalingGroupName` のみを明示的に指定
- インスタンスIDを含めない設定にすることで、メトリクス数を2-3個に固定
- コストを約$0.60-1.0/月に削減（10分の1）

### 8.2. 参考リンク

- [CloudWatch Agent 公式ドキュメント](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)
- [CloudWatch Agent設定リファレンス](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-Configuration-File-Details.html)
- [CloudWatch カスタムメトリクス料金](https://aws.amazon.com/cloudwatch/pricing/)
- [Amazon Linux 2023 CloudWatch Agent](https://docs.aws.amazon.com/linux/al2023/ug/monitoring-cloudwatch-agent.html)

---

**要件定義書バージョン**: 1.0
**最終更新日**: 2025-01-XX
**レビュー状態**: 初稿（クリティカルシンキングレビュー待ち）
