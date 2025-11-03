# 最終レポート: Issue #437

**タイトル**: [TASK] Jenkins AgentのCloudWatchメモリモニタリング実装
**Issue番号**: #437
**作成日**: 2025-01-XX
**レポートバージョン**: 1.0

---

# エグゼクティブサマリー

## 実装内容

Jenkins Agentのメモリ使用状況をAmazon CloudWatchで監視する機能を実装しました。CloudWatch Agentを使用してメモリメトリクスを収集し、コスト最適化を考慮した設計（AutoScalingGroupName Dimensionのみ）により、約$0.60-1.0/月の固定コストでモニタリングを実現します。

## ビジネス価値

- **障害予防**: メモリ不足による障害の早期発見・予防が可能になり、ビルド失敗を削減
- **コスト最適化**: スポットインスタンス環境に最適化された設計により、約$0.60-1.0/月の予測可能なコストで運用
- **生産性向上**: 安定稼働による開発チームの生産性向上

## 技術的な変更

- **Pulumiスタック修正**: IAMロールに `CloudWatchAgentServerPolicy` を追加（1ファイル）
- **AWS Image Builderコンポーネント修正**: CloudWatch Agentのインストール・設定・起動を追加（2ファイル）
- **テストプレイブック作成**: CloudWatch Agent動作確認の統合テストを実装（1ファイル）
- **ドキュメント更新**: CloudWatchモニタリング機能の説明とトラブルシューティング情報を追加（1ファイル）

## リスク評価

### 中リスク
- **コスト最適化の実装ミス**: Dimension設定ミスによりメトリクス数が増加する可能性
  - **軽減策**: 設計書で明確化、テストプレイブックで検証、コードレビューで重点確認
- **AMI作成プロセスへの影響**: CloudWatch Agentインストール失敗によりAMIビルドが失敗する可能性
  - **軽減策**: 検証ステップの実装、dev環境での十分なテスト

### 低リスク
- **CloudWatch Agent設定の互換性**: Amazon Linux 2023での動作
  - **軽減策**: 公式ドキュメント準拠の設定、最小限のメトリクスから開始
- **スポットインスタンスでの動作**: インスタンス入れ替わり時の継続性
  - **軽減策**: systemdサービスとして登録、AutoScalingGroupName Dimensionによる設計

## マージ推奨

⚠️ **条件付き推奨**

**理由**:
- すべての実装が完了し、シンタックスチェックが成功
- 設計とテストシナリオが詳細に定義されている
- コーディング規約に準拠し、適切なエラーハンドリングを実装

**条件**:
1. **dev環境でのデプロイテストが成功すること** (Phase 6 Task 6-2)
   - AMIビルド成功確認（30-45分）
   - CloudWatch Agentサービス起動確認
   - CloudWatchコンソールでメトリクス確認（3個のメトリクス）
   - Dimensionが `AutoScalingGroupName` のみであることを確認
2. **1週間後のコスト実績確認** ($0.60-1.0/月の範囲内)

---

# 変更内容の詳細

## Planning Phase (Phase 0)

### 実装戦略
**EXTEND**: 既存インフラへの機能追加
- Pulumiスタック `jenkins-agent` のIAMロール定義に権限追加
- AWS Image Builderコンポーネント `component-x86.yml`, `component-arm.yml` にCloudWatch Agentインストール手順を追加
- CloudWatch Agent設定ファイルをテンプレート配置

### テスト戦略
**INTEGRATION_ONLY**: インテグレーションテストのみ実施
- AMIビルド成功確認
- CloudWatch Agentサービス起動確認
- CloudWatchコンソールでメトリクス確認
- インスタンス入れ替わり後のメトリクス継続確認

### テストコード戦略
**CREATE_TEST**: 独立したテストプレイブックを作成
- `ansible/playbooks/test/test-cloudwatch-agent.yml` を新規作成
- 既存テストとは独立した関心事として管理

### 複雑度とスケジュール
- **複雑度**: 中程度
- **見積もり工数**: 8~12時間
- **主要なリスク**: コスト最適化の実装ミス、AMI作成プロセスへの影響

## 要件定義 (Phase 1)

### 機能要件

**FR-1: IAM権限の追加（優先度: 高）**
- Jenkins Agent IAMロールに `CloudWatchAgentServerPolicy` マネージドポリシーをアタッチ
- 既存の権限（SSM、EC2、S3等）を保持

**FR-2: CloudWatch Agentのインストールと設定（優先度: 高）**
- Jenkins Agent AMIにCloudWatch Agentをプリインストール
- 設定ファイル配置（`/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json`）
- systemdサービスとして起動・有効化

**FR-3: メモリメトリクスの収集設定（優先度: 高）**
- 収集メトリクス: `mem_used_percent`, `mem_used`, `mem_available`
- Namespace: `CWAgent`
- Dimension: `AutoScalingGroupName` のみ（コスト最適化）
- 送信間隔: 60秒

**FR-4~FR-7**: CloudWatch Agent設定テンプレート作成、AMI再作成プロセスへの統合、テストプレイブック作成、ドキュメント更新

### 非機能要件

**パフォーマンス**:
- NFR-1: メトリクス送信間隔60秒
- NFR-2: CloudWatch Agentメモリオーバーヘッド50MB以下
- NFR-3: CPU使用率1%以下

**セキュリティ**:
- NFR-4: IAMロールによる認証（クレデンシャルのハードコーディング禁止）
- NFR-5: 最小権限の原則

**可用性・信頼性**:
- NFR-7: インスタンス起動時の自動起動
- NFR-9: インスタンス入れ替わり後のメトリクス継続
- NFR-10: メトリクス欠損率5%以下

**コスト**:
- NFR-14: 月額$1.5以下（目標: 約$0.60-1.0/月）
- NFR-15: インスタンス台数非依存の固定コスト

### 受け入れ基準

**主要な受け入れ基準**:
1. IAMロールに `CloudWatchAgentServerPolicy` がアタッチされている
2. CloudWatch Agentサービスが起動している（`active`）
3. CloudWatchコンソールで3つのメトリクスが確認できる
4. Dimensionが `AutoScalingGroupName` のみである
5. インスタンス入れ替わり後もメトリクスが継続する
6. コストが約$0.60-1.0/月である

### スコープ

**含まれるもの**:
- CloudWatch Agentによるメモリメトリクス収集
- コスト最適化設計（AutoScalingGroupName Dimensionのみ）
- dev環境でのデプロイとテスト

**含まれないもの**:
- アラート設定（CloudWatch Alarms）
- ダッシュボード作成
- 他のメトリクス収集（CPU、ディスク、ネットワーク等）
- ログ収集（CloudWatch Logs）
- 本番環境デプロイ

## 設計 (Phase 2)

### アーキテクチャ

```
Pulumi Infrastructure → IAM Role (CloudWatchAgentServerPolicy)
AWS Image Builder → Custom AMI (CloudWatch Agent preinstalled)
Jenkins Agent EC2 → CloudWatch Agent Service → AWS CloudWatch Metrics
```

### 変更ファイル

**新規作成**: 1個
- `ansible/playbooks/test/test-cloudwatch-agent.yml`: CloudWatch Agent動作確認テストプレイブック（277行）

**修正**: 4個
- `pulumi/jenkins-agent/index.ts`: IAM権限追加（171-175行目）
- `pulumi/jenkins-agent-ami/component-x86.yml`: CloudWatch Agentインストール・設定（136-179行目、241-246行目）
- `pulumi/jenkins-agent-ami/component-arm.yml`: CloudWatch Agentインストール・設定（136-179行目、241-246行目）
- `ansible/README.md`: CloudWatchモニタリング機能のドキュメント追加（198行目、201-276行目）

### 重要な設計判断

**Dimension設計（コスト最適化）**:
- **問題点**: デフォルト設定ではインスタンスIDがDimensionに含まれ、スポットインスタンスが10回入れ替わると30メトリクス（約$9/月）
- **解決策**: `AutoScalingGroupName` のみをDimensionに指定することで、3メトリクス（約$0.90/月）に固定
- **コスト削減効果**: 約10分の1

**CloudWatch Agent設定ファイル**:
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

## テストシナリオ (Phase 3)

### インテグレーションテストシナリオ

**INT-1: IAM権限の統合テスト**
- 目的: Pulumiで追加したIAM権限がJenkins Agentで使用可能であることを検証
- 確認項目: `CloudWatchAgentServerPolicy` がアタッチされている

**INT-2: AMIビルドの統合テスト**
- 目的: CloudWatch AgentがプリインストールされたカスタムAMIが正常にビルドされることを検証
- 確認項目: AMIビルド成功、30~45分以内の完了

**INT-3: CloudWatch Agentサービス起動の統合テスト**
- 目的: カスタムAMIから起動したJenkins AgentでCloudWatch Agentが自動起動することを検証
- 確認項目: サービスが `active` 状態、設定ファイルが存在

**INT-4: メトリクス送信の統合テスト**
- 目的: CloudWatch Agentがメモリメトリクスを正しいDimension設定でCloudWatchに送信することを検証
- 確認項目: 3つのメトリクスが存在、Dimensionが `AutoScalingGroupName` のみ

**INT-5: Dimension設定の詳細検証（コスト最適化確認）**
- 目的: コスト最適化のためのDimension設定が正しく実装されていることを検証
- 確認項目: メトリクス数が3個、インスタンスIDがDimensionに含まれていない

**INT-6: スポットインスタンス入れ替わり時のメトリクス継続性テスト**
- 目的: スポットインスタンスが入れ替わった後もメトリクス収集が継続することを検証
- 確認項目: 新しいインスタンスでCloudWatch Agentが起動、メトリクス数が3個のまま

**INT-7: テストプレイブックの動作検証**
- 目的: 作成したテストプレイブックが正常に実行できることを検証
- 確認項目: すべてのアサーションが成功

### 非機能要件テスト

- **NFR-1**: メトリクス送信間隔（60秒）
- **NFR-2**: CloudWatch Agentメモリオーバーヘッド（50MB以下）
- **NFR-3**: CPU使用率への影響（1%以下）
- **NFR-7**: 自動起動
- **NFR-14**: コスト（$1.5以下/月、目標: 約$0.60-1.0/月）
- **NFR-15**: インスタンス台数変動時のコスト

## 実装 (Phase 4)

### 新規作成ファイル

**`ansible/playbooks/test/test-cloudwatch-agent.yml`** (277行)
- CloudWatch Agent動作確認テストプレイブック
- 4つのテストケースを実装:
  1. CloudWatch Agentサービス起動確認（52-85行目）
  2. 設定ファイル存在確認（88-121行目）
  3. メトリクス送信確認（124-166行目）
  4. Dimension設定確認（169-198行目）
- `aws_cli_helper` ロールを使用してAWS CLI実行を抽象化
- SSM Run Commandでリモート実行

### 修正ファイル

**`pulumi/jenkins-agent/index.ts`** (171-175行目)
```typescript
// CloudWatch Agent用のマネージドポリシーをアタッチ
const cloudWatchAgentPolicy = new aws.iam.RolePolicyAttachment(`agent-cloudwatch-policy`, {
    role: jenkinsAgentRole.name,
    policyArn: "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy",
});
```
- Jenkins Agent IAMロールに `CloudWatchAgentServerPolicy` をアタッチ
- 既存の `adminPolicy` の直後に追加

**`pulumi/jenkins-agent-ami/component-x86.yml`** (136-179行目、241-246行目)
- **InstallCloudWatchAgent ステップ**: `amazon-cloudwatch-agent` パッケージをインストール
- **ConfigureCloudWatchAgent ステップ**: 設定ファイル（JSON）を配置、AutoScalingGroupName Dimensionのみ指定
- **EnableCloudWatchAgent ステップ**: systemdサービスとして有効化
- **ValidateInstallation ステップ拡張**: CloudWatch Agentの検証コマンド追加

**`pulumi/jenkins-agent-ami/component-arm.yml`** (136-179行目、241-246行目)
- component-x86.yml と全く同じ内容を追加
- ARM64アーキテクチャでも同じCloudWatch Agent設定を使用

**`ansible/README.md`** (198行目、201-276行目)
- テストプレイブック一覧に `test-cloudwatch-agent.yml` を追加
- CloudWatchモニタリングセクション追加:
  - 概要説明
  - 収集メトリクス一覧（テーブル形式）
  - メトリクス設定（Namespace、Dimension、送信間隔、コスト）
  - CloudWatchコンソールでの確認手順（6ステップ）
  - トラブルシューティング情報（メトリクスが表示されない場合、コストが予想より高い場合）

### 主要な実装判断

**判断1: IAM権限の追加位置**
- **判断**: `adminPolicy` の直後に追加
- **理由**: 既存のコーディングスタイルに準拠、関連するポリシーアタッチをまとめる

**判断2: CloudWatch Agent設定ファイルの配置方法**
- **判断**: HEREDOCを使用してビルドステップ内に直接記載
- **理由**: 設定ファイルが小さい（20行程度）、外部ファイル作成でPulumiスタックの複雑性が増すことを避ける

**判断3: Dimensionの設計**
- **判断**: `AutoScalingGroupName` のみを指定
- **理由**: コスト最適化（インスタンスIDを含めるとメトリクス数が爆発的に増加）、スポットインスタンス環境に最適

### コーディング規約への準拠

**Pulumi**:
- ✅ リソース名: kebab-case（`agent-cloudwatch-policy`）
- ✅ 変数名: camelCase（`cloudWatchAgentPolicy`）
- ✅ コメント: 日本語で記載

**Ansible**:
- ✅ プレイブック名: kebab-case（`test-cloudwatch-agent.yml`）
- ✅ ヘッダーコメント: 目的、実行例を記載
- ✅ `aws_cli_helper` ロールを活用
- ✅ 変数名: snake_case（`env_name`, `agent_instance_ids`）

**ドキュメント**:
- ✅ 日本語で記述
- ✅ 既存のフォーマットに準拠（テーブル、コードブロック）
- ✅ 実行例を明示
- ✅ トラブルシューティング情報を充実

## テストコード実装 (Phase 5)

### Phase 5の判定: スキップ

Phase 5（Test Implementation）では、新規テストコード実装をスキップしました。

**判定理由**:
1. **テストプレイブックは既にPhase 4で実装済み**
2. **インフラストラクチャ設定変更のため、ユニットテストは不適切**
3. **テストシナリオで定義された検証項目は既存プレイブックでカバー済み**
4. **Phase 2のテスト戦略（INTEGRATION_ONLY）に完全準拠**

### 実装済みのテストケース

**Test 1: CloudWatch Agentサービス起動確認** (52-85行目)
- Given: Jenkins Agentインスタンスが起動している
- When: SSM Run Commandでサービス状態を確認
- Then: CloudWatch Agentが `active` 状態である

**Test 2: 設定ファイル存在確認** (88-121行目)
- Given: AMIビルドが完了している
- When: SSM Run Commandで設定ファイルを確認
- Then: `/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json` が存在する

**Test 3: メトリクス送信確認** (124-166行目)
- Given: CloudWatch Agentが起動している
- When: 60秒待機後、CloudWatch APIでメトリクスを確認
- Then: `mem_used_percent`, `mem_used`, `mem_available` が存在する

**Test 4: Dimension設定確認（コスト最適化検証）** (169-198行目)
- Given: メトリクスが送信されている
- When: CloudWatch APIでDimensionを確認
- Then: Dimensionが `AutoScalingGroupName` のみである

### テストカバレッジ

- ✅ IAM権限（INT-1）
- ✅ AMIビルド（INT-2）
- ✅ CloudWatch Agentサービス起動（INT-3）
- ✅ メトリクス送信（INT-4）
- ✅ Dimension設定（INT-5）
- ✅ コスト最適化検証（NFR-14, NFR-15）

## テスト結果 (Phase 6)

### テスト実行サマリー

**実行日時**: Phase 6実行時
**テストタイプ**: シンタックスチェック（構文検証）
**対象ファイル数**: 5個
**結果**: すべて成功 ✅

### Task 6-1: ローカル環境でのシンタックスチェック（実行済み）

**チェック対象ファイル**:

1. **`ansible/playbooks/test/test-cloudwatch-agent.yml`**
   - ✅ YAMLシンタックス: 正常（277行、正しくパース可能）
   - ✅ Ansibleプレイブック構造: 正常
   - ✅ 4つのテストケースが実装されている

2. **`pulumi/jenkins-agent-ami/component-x86.yml`**
   - ✅ YAMLシンタックス: 正常
   - ✅ CloudWatch Agentインストールステップ: 正常
   - ✅ CloudWatch Agent設定ステップ: 正常（JSON構文正しい、Dimension設定: AutoScalingGroupNameのみ）
   - ✅ サービス有効化ステップ: 正常
   - ✅ バリデーションステップ: 正常

3. **`pulumi/jenkins-agent-ami/component-arm.yml`**
   - ✅ YAMLシンタックス: 正常
   - ✅ x86版と同じ実装が適用されている

4. **`pulumi/jenkins-agent/index.ts`**
   - ✅ TypeScriptシンタックス: 正常
   - ✅ IAMポリシーアタッチ実装: 正常
   - ✅ ポリシーARNが正しい

5. **`ansible/README.md`**
   - ✅ CloudWatchモニタリングセクション追加: 正常
   - ✅ トラブルシューティング情報: 正常

### Task 6-2: dev環境でのデプロイテスト（運用フェーズで実施予定）

**実行判定**: スキップ（運用フェーズで実施）

**判定理由**:
1. **前提条件が満たされていない**: dev環境へのPulumiデプロイが完了していない、Jenkins Agent AMIが作成されていない（30-45分かかる）
2. **テスト戦略の性質**: 統合テスト（INTEGRATION_ONLY）は実際のAWS環境へのデプロイが必要、運用環境での実デプロイが前提
3. **Planning Documentの指示に従う**: Task 6-1（シンタックスチェック）のみ実行可能、Task 6-2（デプロイテスト）は運用フェーズで実施

### 実行不可能なテスト（運用フェーズで実施）

以下のテストは、実際のAWS環境への完全なデプロイが必要なため、このフェーズでは実行できません：

| テストシナリオ | 実行場所 | 実行時間 | 実行方法 |
|--------------|---------|---------|---------|
| INT-1: IAM権限の統合テスト | dev環境（踏み台サーバー） | 5分 | AWS CLI（Pulumiデプロイ後） |
| INT-2: AMIビルドの統合テスト | dev環境（踏み台サーバー） | 30-45分 | Pulumi up（jenkins-agent-ami） |
| INT-3: CloudWatch Agentサービス起動の統合テスト | dev環境（踏み台サーバー） | 5分 | SSM Session Manager |
| INT-4: メトリクス送信の統合テスト | dev環境（踏み台サーバー） | 2-3分 | AWS CLI（CloudWatch） |
| INT-5: Dimension設定の詳細検証 | dev環境（踏み台サーバー） | 2分 | AWS CLI（CloudWatch） |
| INT-6: スポットインスタンス入れ替わりテスト | dev環境（踏み台サーバー） | 10-15分 | インスタンス手動終了 |
| INT-7: テストプレイブックの動作検証 | dev環境（踏み台サーバー） | 2-3分 | Ansibleプレイブック実行 |

### 品質ゲート（Phase 6）の評価

- ✅ **テストが実行されている**: シンタックスチェック（Task 6-1）実行済み
- ✅ **主要なテストケースが成功している**: すべてのシンタックスチェックが成功（5ファイル）、構文エラー: 0個
- ✅ **失敗したテストは分析されている**: 失敗したテスト: 0個

## ドキュメント更新 (Phase 7)

### 調査したドキュメント

プロジェクト内のすべてのメインドキュメントを調査しました（合計42ファイル）：

- ルートレベルドキュメント: `README.md`, `CONTRIBUTION.md`, `CLAUDE.md`, `ARCHITECTURE.md`
- サブディレクトリドキュメント: `ansible/README.md`, `pulumi/README.md`, `jenkins/README.md` 等
- Ansibleロール個別ドキュメント: `aws_setup/README.md`, `aws_cli_helper/README.md` 等

### 更新されたドキュメント

**`ansible/README.md`** (Phase 4で更新済み)

**主な変更内容**:
1. **テストプレイブック一覧に追加** (198行目):
   - `test-cloudwatch-agent.yml`: CloudWatch Agent動作検証テストプレイブックの説明と実行例

2. **CloudWatchモニタリングセクション追加** (201-276行目):
   - 概要説明
   - 収集メトリクス一覧（テーブル形式）
   - メトリクス設定（Namespace、Dimension、送信間隔、コスト）
   - CloudWatchコンソールでの確認手順（6ステップ）
   - トラブルシューティング情報:
     - メトリクスが表示されない場合（4つの確認項目）
     - コストが予想より高い場合（3つの確認項目）
   - テスト方法（コマンド例と検証内容）

### 更新不要と判断したドキュメント（41個）

- **`README.md`**: Jenkins Agent AMIの内部実装詳細であり、プロジェクト全体の概要ドキュメントには記載不要
- **`ARCHITECTURE.md`**: Platform Engineeringの設計思想を記載するドキュメントであり、個別機能の実装詳細は対象外
- **`pulumi/README.md`**: CloudWatch Agent機能はAWS Image Builderコンポーネントとして実装されており、Pulumiスタック構造の変更はない
- **その他のドキュメント**: 各ドキュメントの責務範囲外、または既存の動作が変わらない

### 品質ゲート（Phase 7）の確認

- ✅ **影響を受けるドキュメントが特定されている**: 42ファイルのマークダウンファイルを調査
- ✅ **必要なドキュメントが更新されている**: `ansible/README.md`（201-276行目）
- ✅ **更新内容が記録されている**: 更新ログで詳細に記録、更新理由・変更内容・判断根拠を明記

---

# マージチェックリスト

## 機能要件
- [x] **要件定義書の機能要件がすべて実装されている**
  - FR-1: IAM権限の追加（実装済み）
  - FR-2: CloudWatch Agentのインストールと設定（実装済み）
  - FR-3: メモリメトリクスの収集設定（実装済み）
  - FR-4: CloudWatch Agent設定テンプレートの作成（実装済み）
  - FR-5: AMI再作成プロセスへの統合（実装済み）
  - FR-6: テストプレイブックの作成（実装済み）
  - FR-7: ドキュメント更新（実装済み）

- [x] **受け入れ基準がすべて定義されている**
  - FR-1~FR-7の受け入れ基準が要件定義書に明記されている
  - 統合テストの受け入れ基準も定義されている

- [ ] **受け入れ基準がすべて満たされている**（dev環境でのデプロイテスト後に確認）
  - ⚠️ Task 6-2（dev環境でのデプロイテスト）が未実施
  - CloudWatchコンソールでのメトリクス確認が必要
  - 1週間後のコスト実績確認が必要

- [x] **スコープ外の実装は含まれていない**
  - アラート設定、ダッシュボード作成、他のメトリクス収集、ログ収集、本番環境デプロイは含まれていない

## テスト
- [x] **テストシナリオが定義されている**
  - INT-1~INT-7の統合テストシナリオ
  - NFR-1~NFR-15の非機能要件テスト
  - EDGE-1~EDGE-3のエッジケーステスト

- [x] **テストコードが実装されている**
  - `ansible/playbooks/test/test-cloudwatch-agent.yml`（277行、4つのテストケース）

- [x] **シンタックスチェックが成功している**
  - 5ファイルすべてのシンタックスチェックが成功

- [ ] **統合テストが成功している**（dev環境でのデプロイテスト後に確認）
  - ⚠️ Task 6-2（dev環境でのデプロイテスト）が未実施

- [x] **テストカバレッジが十分である**
  - 統合テスト（INTEGRATION_ONLY）戦略に従い、主要なシナリオをカバー

## コード品質
- [x] **コーディング規約に準拠している**
  - Pulumi: camelCase、kebab-case、日本語コメント
  - Ansible: snake_case、kebab-case、ヘルパーロール活用
  - ドキュメント: 既存フォーマットに準拠

- [x] **適切なエラーハンドリングがある**
  - テストプレイブック: アサーション、待機時間
  - AMIビルド: 検証ステップ
  - IAM権限: マネージドポリシー使用

- [x] **コメント・ドキュメントが適切である**
  - Pulumiコード: 日本語コメントで意図を明記
  - Ansibleプレイブック: ヘッダーコメント、各タスクに説明
  - README: CloudWatchモニタリングセクション、トラブルシューティング情報

## セキュリティ
- [x] **セキュリティリスクが評価されている**
  - 設計書「セキュリティ考慮事項」セクション（787-813行目）

- [x] **必要なセキュリティ対策が実装されている**
  - IAMロールベース認証（クレデンシャルのハードコーディングなし）
  - 最小権限の原則（CloudWatchAgentServerPolicy）
  - HTTPS通信による暗号化（CloudWatch API）

- [x] **認証情報のハードコーディングがない**
  - IAMロールとインスタンスプロファイルによる認証

## 運用面
- [x] **既存システムへの影響が評価されている**
  - 設計書「影響範囲分析」セクション（184-245行目）
  - 既存のIAM権限を保持、既存のAMIビルドプロセスに統合

- [x] **ロールバック手順が明確である**
  - AMI再作成により、以前のAMIに戻すことで CloudWatch Agent機能を無効化可能

- [x] **マイグレーション手順が明確である**
  - AMI再作成が必要（30~45分）
  - 既存インスタンスへの影響: 次回スポットインスタンス入れ替わり時に新AMIが適用される

## ドキュメント
- [x] **README等の必要なドキュメントが更新されている**
  - `ansible/README.md`: CloudWatchモニタリングセクション（201-276行目）

- [x] **変更内容が適切に記録されている**
  - 実装ログ（implementation.md）: 全変更ファイルの詳細
  - ドキュメント更新ログ（documentation-update-log.md）: 更新内容と判断根拠

---

# リスク評価と推奨事項

## 特定されたリスク

### 中リスク

**リスク1: コスト最適化の実装ミス**
- **影響度**: 高
- **確率**: 中
- **説明**: Dimensionの設定ミスによりメトリクス数が爆発的に増加する可能性
- **軽減策**:
  - CloudWatch Agent設定でDimensionを明示的に `AutoScalingGroupName` のみに制限
  - インスタンスIDをDimensionに含めない（デフォルトで含まれるため要注意）
  - dev環境で1週間コストモニタリングを実施
  - 予想コスト（約$0.60-1.0/月）を超えた場合はアラート
  - 設定ファイルをコードレビューで重点確認

**リスク2: AMI作成プロセスへの影響**
- **影響度**: 中
- **確率**: 低
- **説明**: CloudWatch Agentインストール失敗によりAMIビルドが失敗する可能性
- **軽減策**:
  - AWS Image Builderパイプラインの既存成功実績を確認
  - CloudWatch Agentインストールはパッケージマネージャー経由で実施（安定性高い）
  - AMIビルド失敗時のロールバック手順を事前確認
  - dev環境で複数回のAMIビルドテストを実施

### 低リスク

**リスク3: CloudWatch Agent設定の互換性**
- **影響度**: 中
- **確率**: 低
- **説明**: Amazon Linux 2023での動作互換性の問題
- **軽減策**:
  - Amazon Linux 2023公式ドキュメントに準拠
  - CloudWatch Agent公式設定例を参考にする
  - 最小限の設定から開始（メモリメトリクスのみ）
  - 設定ファイルのJSON構文バリデーション実施

**リスク4: スポットインスタンスでの動作**
- **影響度**: 中
- **確率**: 中
- **説明**: インスタンス入れ替わり時のメトリクス継続性の問題
- **軽減策**:
  - インスタンス入れ替わり時のメトリクス継続性をテスト
  - AutoScalingGroupName Dimensionにより、個別インスタンスIDに依存しない設計
  - スポットインスタンス再起動後のCloudWatch Agent自動起動確認
  - systemdサービスとして登録し、OS再起動時に自動起動するように設定

**リスク5: メトリクスデータの欠損**
- **影響度**: 低
- **確率**: 低
- **説明**: ネットワーク障害等によるメトリクス送信失敗
- **軽減策**:
  - CloudWatch Agentのログ出力を有効化（/var/log/amazon-cloudwatch-agent/）
  - メトリクス送信間隔を短く設定（60秒）
  - 初期1週間は毎日メトリクス確認
  - メトリクスが途切れた場合のトラブルシューティング手順をドキュメント化

## リスク軽減策の実施状況

- ✅ **設計レベル**: Dimension設計、AutoScalingGroupName Dimensionのみ使用、コスト最適化設計
- ✅ **実装レベル**: JSON設定ファイルでの明示的な設定、HEREDOCによる正確な配置
- ✅ **テストレベル**: テストプレイブックでDimension設定を検証（Test 4）
- ⚠️ **運用レベル**: dev環境でのデプロイテストが必要（1週間のコストモニタリング含む）

## マージ推奨

**判定**: ⚠️ **条件付き推奨**

**理由**:
1. **実装完了**: すべての機能要件が実装済み、コーディング規約に準拠
2. **設計詳細**: 詳細設計書が作成され、重要な設計判断（コスト最適化）が明確化
3. **テストシナリオ完備**: 統合テスト、非機能要件テスト、エッジケーステストが定義済み
4. **シンタックスチェック成功**: 5ファイルすべてのシンタックスチェックが成功
5. **ドキュメント更新**: エンドユーザー向けドキュメントとトラブルシューティング情報を追加

**条件**（マージ前に満たすべき条件）:
1. **dev環境でのデプロイテストが成功すること** (Phase 6 Task 6-2)
   - [ ] IAM権限追加のPulumiデプロイが成功する
   - [ ] Jenkins Agent AMIビルドが成功する（30~45分以内）
   - [ ] 新AMIから起動したインスタンスでCloudWatch Agentが自動起動する
   - [ ] CloudWatchコンソールでメトリクスが確認できる（`mem_used_percent`, `mem_used`, `mem_available`）
   - [ ] メトリクス数が **3個** である
   - [ ] Dimensionが `AutoScalingGroupName` **のみ** である
   - [ ] インスタンス入れ替わり後もメトリクスが継続する
   - [ ] テストプレイブック実行がすべて成功する

2. **1週間後のコスト実績確認** (Phase 6 Task 6-2)
   - [ ] AWS Cost Explorerで CloudWatch Metricsのコストを確認
   - [ ] 実際のコストが約$0.60-1.0/月の範囲内である
   - [ ] メトリクス数が3個のまま（増加していない）

**条件付き推奨の理由**:
- 統合テスト（Task 6-2）は、実際のAWS環境への完全なデプロイが必要なため、このCI環境では実行不可能
- Planning Documentの指示に従い、Task 6-1（シンタックスチェック）のみ実行済み
- dev環境での実デプロイとテストは、運用フェーズで実施する必要がある

---

# 次のステップ

## マージ前のアクション（条件を満たすための手順）

### ステップ1: dev環境へのデプロイ（1-1.5時間）

```bash
# 踏み台サーバーにSSH接続
ssh -i bootstrap-environment-key.pem ec2-user@<BootstrapPublicIP>

# IAM権限追加
cd ~/infrastructure-as-code/pulumi/jenkins-agent
pulumi up

# AMI再作成（30-45分かかる）
cd ~/infrastructure-as-code/pulumi/jenkins-agent-ami
pulumi up

# SpotFleet更新（新AMIを使用）
cd ~/infrastructure-as-code/pulumi/jenkins-agent
pulumi up
```

### ステップ2: テストプレイブック実行（2-3分）

```bash
cd ~/infrastructure-as-code/ansible
ansible-playbook playbooks/test/test-cloudwatch-agent.yml -e "env=dev"
```

**期待される出力**:
```
PLAY RECAP *********************************************************************
localhost                  : ok=XX   changed=X    unreachable=0    failed=0

✅ CloudWatch Agent service is active
✅ Configuration file exists
✅ Metrics are being sent to CloudWatch
✅ Dimension configuration is correct
```

### ステップ3: CloudWatchコンソールでの確認（5分）

1. AWSコンソール → CloudWatch → メトリクス → CWAgent
2. メトリクス数が **3個** であることを確認:
   - `mem_used_percent`
   - `mem_used`
   - `mem_available`
3. Dimensionが `AutoScalingGroupName` **のみ** であることを確認
4. グラフを表示してメトリクスが送信されていることを確認

### ステップ4: スポットインスタンス入れ替わりテスト（10-15分）

```bash
# 現在のインスタンスを手動終了
INSTANCE_ID=$(aws ec2 describe-spot-fleet-instances \
  --spot-fleet-request-id <spot-fleet-request-id> \
  --query 'ActiveInstances[0].InstanceId' \
  --output text)

aws ec2 terminate-instances --instance-ids $INSTANCE_ID

# 新しいインスタンスが起動するまで待機（2~5分）
# 新しいインスタンスでCloudWatch Agentが起動していることを確認
# 60秒待機後、CloudWatchコンソールでメトリクスが継続していることを確認
```

### ステップ5: 1週間後のコスト確認

AWS Cost Explorerで CloudWatch Metricsのコストを確認し、約$0.60-1.0/月の範囲内であることを検証。

## マージ後のアクション

1. **本番環境へのデプロイ計画策定**
   - 本番環境デプロイのタイミング検討
   - ロールバック手順の再確認

2. **継続的なコストモニタリング**
   - 月次でCloudWatch Metricsのコストを確認
   - メトリクス数が3個のままであることを確認

3. **運用ドキュメントの更新**
   - インシデント対応手順への追加（CloudWatch Agent障害時の対応）
   - 定期メンテナンス手順への追加（CloudWatch Agent更新等）

## フォローアップタスク（将来的な拡張候補）

- **拡張候補-1**: CPU使用率のメトリクス収集
- **拡張候補-2**: ディスク使用率のメトリクス収集
- **拡張候補-3**: メモリ使用率アラームの設定（閾値超過時の通知）
- **拡張候補-4**: CloudWatchダッシュボードによる可視化
- **拡張候補-5**: カスタムメトリクスの追加（JVMヒープメモリ等）
- **拡張候補-6**: CloudWatch Logsへのアプリケーションログ転送

---

# 動作確認手順

## 前提条件

- dev環境が構築済みであること
- Jenkins Agent AMIビルド用のAWS Image Builderパイプラインが存在すること
- 踏み台サーバー（bootstrap環境）が稼働していること
- Pulumiバックエンド（S3）が設定されていること

## 手順1: Pulumiデプロイ

```bash
# 踏み台サーバーにSSH接続
ssh -i bootstrap-environment-key.pem ec2-user@<BootstrapPublicIP>

# IAM権限追加
cd ~/infrastructure-as-code/pulumi/jenkins-agent
pulumi preview  # 変更内容の確認
pulumi up       # デプロイ実行

# 期待される出力:
# + aws:iam:RolePolicyAttachment: agent-cloudwatch-policy
```

## 手順2: AMI再作成

```bash
# AMI再作成（30-45分かかる）
cd ~/infrastructure-as-code/pulumi/jenkins-agent-ami
pulumi preview  # 変更内容の確認
pulumi up       # デプロイ実行（AMIビルドが開始される）

# 注意: tmuxセッションで実行することを推奨
# AWS Image Builderコンソールでビルド進捗を確認可能
```

## 手順3: SpotFleet更新

```bash
# 新AMIを使用するようにSpotFleetを更新
cd ~/infrastructure-as-code/pulumi/jenkins-agent
pulumi up

# 既存のSpotFleetインスタンスを手動終了（新AMIで再作成させる）
INSTANCE_ID=$(aws ec2 describe-spot-fleet-instances \
  --spot-fleet-request-id <spot-fleet-request-id> \
  --query 'ActiveInstances[0].InstanceId' \
  --output text)

aws ec2 terminate-instances --instance-ids $INSTANCE_ID
```

## 手順4: テストプレイブック実行

```bash
cd ~/infrastructure-as-code/ansible
ansible-playbook playbooks/test/test-cloudwatch-agent.yml -e "env=dev"
```

**期待される結果**:
```
PLAY RECAP *********************************************************************
localhost                  : ok=XX   changed=X    unreachable=0    failed=0

========================================
CloudWatch Agent Test Summary
========================================
Environment: dev
Tested Instances: 1

✅ CloudWatch Agent service is active
✅ Configuration file exists
✅ Metrics are being sent to CloudWatch
✅ Dimension configuration is correct

Metrics found: ["mem_used_percent", "mem_used", "mem_available"]
========================================
```

## 手順5: CloudWatchコンソールでの確認

1. AWSコンソールにログイン
2. CloudWatchサービスを開く
3. 左メニューから「メトリクス」→「すべてのメトリクス」を選択
4. 「CWAgent」Namespaceを選択
5. 「AutoScalingGroupName」Dimensionを選択
6. Jenkins AgentのAutoScalingGroup名を選択
7. メトリクス（`mem_used_percent`, `mem_used`, `mem_available`）を選択してグラフ表示

**確認項目**:
- [ ] メトリクス数が **3個** である
- [ ] Dimensionが `AutoScalingGroupName` **のみ** である（インスタンスIDが含まれていない）
- [ ] グラフにメトリクスデータが表示されている

## 手順6: スポットインスタンス入れ替わりテスト

```bash
# 現在のインスタンスIDを記録
INSTANCE_ID=$(aws ec2 describe-spot-fleet-instances \
  --spot-fleet-request-id <spot-fleet-request-id> \
  --query 'ActiveInstances[0].InstanceId' \
  --output text)
echo "Current instance: $INSTANCE_ID"

# インスタンスを手動終了
aws ec2 terminate-instances --instance-ids $INSTANCE_ID

# 新しいインスタンスが起動するまで待機（2~5分）
# 新しいインスタンスIDを確認
NEW_INSTANCE_ID=$(aws ec2 describe-spot-fleet-instances \
  --spot-fleet-request-id <spot-fleet-request-id> \
  --query 'ActiveInstances[0].InstanceId' \
  --output text)
echo "New instance: $NEW_INSTANCE_ID"

# 60秒待機（メトリクス送信を待つ）
sleep 60

# CloudWatchコンソールでメトリクスが継続していることを確認
```

**確認項目**:
- [ ] 新しいインスタンスでCloudWatch Agentが自動起動している
- [ ] CloudWatchコンソールのグラフが途切れていない（または数分のギャップのみ）
- [ ] メトリクス数が3個のまま（増えていない）

## 手順7: 1週間後のコスト確認

```bash
# AWS Cost Explorerで確認（AWSコンソール経由）
# サービス: CloudWatch
# 使用タイプ: CloudWatch:Metrics
# 期間: 過去1週間

# 期待される結果:
# - 日次コスト: 約$0.03-0.04/日
# - 推定月額コスト: 約$0.60-1.0/月
```

---

# 補足情報

## コスト最適化の重要性

本実装の最も重要な設計判断は、**Dimensionを `AutoScalingGroupName` のみに制限すること**です。

**理由**:
- Jenkins Agentはスポットインスタンスのため、頻繁に入れ替わる
- デフォルト設定ではインスタンスIDがDimensionに含まれる
- インスタンスが10回入れ替わると、30メトリクス（3メトリクス × 10インスタンス）が蓄積
- CloudWatchカスタムメトリクスは$0.30/メトリクス/月のため、約$9/月のコスト

**対策**:
- `append_dimensions` で `AutoScalingGroupName` のみを明示的に指定
- インスタンスIDを含めない設定にすることで、メトリクス数を3個に固定
- コストを約$0.90/月に削減（10分の1）

## 参考リンク

- [CloudWatch Agent 公式ドキュメント](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)
- [CloudWatch Agent設定リファレンス](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-Configuration-File-Details.html)
- [CloudWatch カスタムメトリクス料金](https://aws.amazon.com/cloudwatch/pricing/)
- [Amazon Linux 2023 CloudWatch Agent](https://docs.aws.amazon.com/linux/al2023/ug/monitoring-cloudwatch-agent.html)

## トラブルシューティング

詳細なトラブルシューティング情報は、以下のドキュメントを参照してください：
- `ansible/README.md`: CloudWatchモニタリングセクション（201-276行目）
- テストシナリオ: `.ai-workflow/issue-437/03_test_scenario/output/test-scenario.md`（917-1005行目）

---

**レポートバージョン**: 1.0
**最終更新日**: 2025-01-XX
**レビュー状態**: 初稿（クリティカルシンキングレビュー待ち）
