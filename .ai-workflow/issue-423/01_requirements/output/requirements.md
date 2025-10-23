# 要件定義書 - Issue #423

## 0. Planning Documentの確認

本要件定義は、Planning Phase（`.ai-workflow/issue-423/00_planning/output/planning.md`）で策定された以下の戦略に基づいて実施します：

- **実装戦略**: EXTEND（既存Jenkinsfileの拡張）
- **テスト戦略**: INTEGRATION_ONLY（Jenkins環境での統合テストのみ）
- **テストコード戦略**: CREATE_TEST（テストシナリオドキュメントの作成）
- **複雑度**: 中程度
- **見積もり工数**: 6~8時間

Planning Documentで特定されたリスク（Script Security承認、実行中ジョブへの影響、タイムアウト設定の妥当性）を考慮して要件を定義します。

---

## 1. 概要

### 1.1 背景

`jenkins/jobs/pipeline/infrastructure-management/shutdown-environment/Jenkinsfile`の実行時に、Jenkinsエージェントがジョブ実行中の場合にタイムアウトエラーが発生する問題が報告されています。

**現在の実装の問題点**:
1. SpotFleetのキャパシティを即座に0に設定
2. `waitUntil`でエージェントインスタンスの終了を待機
3. タイムアウト（デフォルト30分）で待機を中断
4. タイムアウト時にジョブが失敗

この挙動では、エージェント上で実行中のジョブが強制終了される可能性があり、ビルド成果物の破損やデータ不整合のリスクがあります。

### 1.2 目的

Jenkins環境のシャットダウン処理を、**実行中のジョブを尊重し、安全に完了させる**方式に改善します。具体的には：

1. **新しいジョブのキューを受け入れないようにする**（Jenkins quietDown機能）
2. **実行中のジョブが完了するまで待機する**（エージェント実行中ジョブ監視）
3. **ジョブがなくなったらスケールダウンする**（gracefulモード）

### 1.3 ビジネス価値

- **データ整合性の向上**: ジョブの途中終了によるデータ破損を防止
- **運用安全性の向上**: 計画的なシャットダウンによる予測可能な動作
- **コスト最適化**: 実行中ジョブの再実行コストを削減

### 1.4 技術的価値

- **gracefulモードの実装**: 段階的なシャットダウンによる高可用性の実現
- **Jenkins API活用**: quietDown/cancelQuietDownによる標準的な制御
- **監視機能の追加**: エージェント実行状況のリアルタイム監視

---

## 2. 機能要件

### 2.1 Jenkins QuietDownモード制御（優先度: 高）

**要件ID**: FR-001

**説明**: Jenkinsのビルドキューを制御し、新規ジョブの受付を停止する機能を実装する。

**詳細**:
- `setJenkinsQuietMode(boolean enable)`関数を実装
- `enable=true`の場合、`Jenkins.instance.quietDown()`を呼び出し
- `enable=false`の場合、`Jenkins.instance.cancelQuietDown()`を呼び出し
- gracefulモード時のみ有効化
- 処理完了後、Controller停止前に必ずquietDownをキャンセル

**検証可能性**:
- Jenkins UIで"Prepare for shutdown"メッセージが表示されること
- 新規ジョブがキューに追加されないこと
- `cancelQuietDown()`後、新規ジョブが受付可能になること

---

### 2.2 エージェント実行中ジョブ監視（優先度: 高）

**要件ID**: FR-002

**説明**: SpotFleetエージェント上で実行中のジョブ数をリアルタイムで監視する機能を実装する。

**詳細**:
- `getRunningAgentExecutors()`関数を実装
- `Jenkins.instance.computers`から全ノードを取得
- built-in以外のノード（エージェント）をフィルタ
- 各エージェントの`Executor.isBusy()`で実行中ジョブ数をカウント
- 定期的なログ出力（15秒間隔）

**検証可能性**:
- エージェント実行中ジョブ数が正確にカウントされること
- built-inエージェント（Controller）が除外されること
- ログに"残りのエージェント実行中ジョブ: X"が出力されること

---

### 2.3 エージェントジョブ完了待機（優先度: 高）

**要件ID**: FR-003

**説明**: エージェント上の全ジョブが完了するまで待機する機能を実装する。

**詳細**:
- `waitForAgentJobsCompletion(timeoutMinutes)`関数を実装
- `waitUntil`ループで`getRunningAgentExecutors()`を定期的に呼び出し
- 実行中ジョブ数が0になったらループを抜ける
- タイムアウト設定（デフォルト30分）
- タイムアウト時は**警告ログを出力して処理を続行**（エラーにしない）

**検証可能性**:
- ジョブ完了後、待機が正常に終了すること
- タイムアウト時、警告ログが出力されること
- タイムアウト時、ジョブがfailureステータスにならないこと

---

### 2.4 scaleDownEC2Fleet関数の拡張（優先度: 高）

**要件ID**: FR-004

**説明**: 既存の`scaleDownEC2Fleet()`関数を、gracefulモード時に新しいフローで動作するよう修正する。

**詳細（gracefulモード時）**:
1. **QuietDown設定**: `setJenkinsQuietMode(true)`を呼び出し
2. **エージェントジョブ完了待機**: `waitForAgentJobsCompletion()`を呼び出し
3. **SpotFleetスケールダウン**: キャパシティを0に設定
4. **インスタンス終了待機**: 既存の`waitForSpotFleetTermination()`を実行
5. **QuietDownキャンセル**: `setJenkinsQuietMode(false)`を呼び出し（念のため）

**詳細（immediateモード時）**:
- 既存の動作を維持（即座にキャパシティ0、インスタンス終了待機）

**検証可能性**:
- gracefulモードで上記5ステップが順番に実行されること
- immediateモードで既存の動作が維持されること

---

### 2.5 エラーハンドリングの改善（優先度: 中）

**要件ID**: FR-005

**説明**: タイムアウトやAPI呼び出し失敗時の適切なエラーハンドリングを実装する。

**詳細**:
- **タイムアウト時の動作**: 警告ログを出力し、処理を続行（ジョブは成功）
- **Jenkins API呼び出し失敗時**: エラーログを出力し、処理をスキップ（リトライなし）
- **Script Security承認が必要な場合**: エラーメッセージに承認方法を含める

**検証可能性**:
- タイムアウト発生時、ジョブが成功ステータスになること
- API呼び出し失敗時、エラーログが出力されること

---

### 2.6 ログ出力の強化（優先度: 中）

**要件ID**: FR-006

**説明**: 処理の進行状況を明確に把握できるログ出力を実装する。

**詳細**:
- **QuietDown設定時**: "Jenkins QuietDownモードを有効化しました"
- **エージェントジョブ監視**: "残りのエージェント実行中ジョブ: X"（15秒間隔）
- **ジョブ完了待機**: "エージェントジョブの完了を待機中... (経過: X分)"
- **タイムアウト時**: "警告: エージェントジョブのタイムアウト（30分）に達しました。スケールダウンを続行します。"
- **処理フロー**: 各ステップの開始・完了をログ出力

**検証可能性**:
- ログから処理の進行状況が追跡できること
- タイムアウト時の警告メッセージが表示されること

---

### 2.7 既存パラメータの活用（優先度: 低）

**要件ID**: FR-007

**説明**: 既存のジョブパラメータ（`SHUTDOWN_MODE`、`WAIT_TIMEOUT_MINUTES`）をそのまま活用する。

**詳細**:
- `SHUTDOWN_MODE`: `graceful`と`immediate`の選択肢を維持
- `WAIT_TIMEOUT_MINUTES`: タイムアウト時間の設定（デフォルト30分）
- 新規パラメータは追加しない

**検証可能性**:
- 既存パラメータで新しい動作が制御できること

---

## 3. 非機能要件

### 3.1 パフォーマンス要件

**NFR-001: ポーリング間隔**
- エージェント実行中ジョブのチェック間隔: 15秒
- SpotFleetインスタンス終了のチェック間隔: 15秒（既存と同じ）

**NFR-002: タイムアウト**
- デフォルトタイムアウト: 30分（パラメータで変更可能）
- Jenkins API呼び出しタイムアウト: 設定しない（即座にエラーまたは成功）

---

### 3.2 セキュリティ要件

**NFR-003: Script Security承認**
- `Jenkins.instance`の使用には、Script Approvalが必要になる可能性がある
- エラーメッセージに承認方法を明記

**NFR-004: IAM権限**
- 既存のIAMロール権限で動作すること（新規権限は不要）
- EC2 SpotFleet操作権限は既に付与済み

---

### 3.3 可用性・信頼性要件

**NFR-005: ジョブ実行の安全性**
- 実行中のジョブが強制終了されないこと
- タイムアウト時でもジョブが失敗ステータスにならないこと

**NFR-006: Controller自己参照問題の回避**
- built-inエージェント（Controller自身）で実行されること（既存仕様）
- Controller停止前にquietDownをキャンセルすること

**NFR-007: 冪等性**
- 複数回実行しても安全であること
- 既にquietDownモードの場合でもエラーにならないこと

---

### 3.4 保守性・拡張性要件

**NFR-008: コードの可読性**
- 関数に明確な命名とコメントを付与
- 処理フローが理解しやすい構造

**NFR-009: 既存コードとの整合性**
- 既存の関数命名規則に従う（例: `scaleDownSpotFleet`）
- 既存のエラーハンドリングパターンに従う

**NFR-010: 将来的な拡張**
- NATゲートウェイ停止など、他のリソース停止処理にも適用可能な設計

---

## 4. 制約事項

### 4.1 技術的制約

**CON-001: Jenkins環境の制約**
- Jenkins 2.426.1以上が必要
- Groovy 3.0以上が必要
- Script Security Pluginによる承認が必要な可能性がある

**CON-002: AWS環境の制約**
- SpotFleet Request IDがSSMパラメータストアに保存されていること
- IAMロールでEC2、SSM操作権限が付与されていること

**CON-003: 実装方式の制約**
- 既存Jenkinsfileを拡張（新規ファイルは作成しない）
- 既存パラメータ定義を変更しない
- DSLファイルの変更は不要（パラメータ定義が変更されないため）

---

### 4.2 リソース制約

**CON-004: 時間制約**
- 見積もり工数: 6~8時間
- Phase 4（実装）: 2.5~3時間

**CON-005: テスト環境**
- dev環境でのテスト実行が必須
- 本番環境での実行前に十分な検証が必要

---

### 4.3 ポリシー制約

**CON-006: セキュリティポリシー**
- Script Securityによる承認が必要な処理は、管理者に事前連絡
- 本番環境での実行は他ユーザーへの告知が必要

**CON-007: コーディング規約**
- `jenkins/CONTRIBUTION.md`に従う
- 関数定義はpipelineブロックの前に配置
- JavaDoc形式のコメントを付与

---

## 5. 前提条件

### 5.1 システム環境

**PRE-001: Jenkins環境**
- Jenkins 2.426.1以上がインストール済み
- 以下のプラグインがインストール済み:
  - Pipeline Plugin
  - AWS Steps Plugin
  - Script Security Plugin

**PRE-002: AWS環境**
- SpotFleet Request IDがSSMパラメータストアに保存済み
  - パラメータ名: `/jenkins-infra/{ENVIRONMENT}/agent/spotFleetRequestId`
- IAMロールで以下の権限が付与済み:
  - `ec2:DescribeSpotFleetRequests`
  - `ec2:ModifySpotFleetRequest`
  - `ec2:DescribeSpotFleetInstances`
  - `ssm:GetParameter`

---

### 5.2 依存コンポーネント

**PRE-003: SSMパラメータストア**
- SpotFleet Request IDが正しく登録されていること
- 値が空でないこと

**PRE-004: SpotFleet**
- SpotFleet Request IDが有効であること
- SpotFleetが`active`状態であること

---

### 5.3 外部システム連携

**PRE-005: Jenkins Controller**
- built-inエージェントが有効であること
- Script Security設定が有効であること

**PRE-006: AWS CLI**
- AWS CLI v2がインストール済み
- AWS認証情報が設定済み（IAMロール経由）

---

## 6. 受け入れ基準

### 6.1 機能要件の受け入れ基準

#### AC-001: Jenkins QuietDownモード制御（FR-001）

**Given**: gracefulモードでシャットダウンジョブを実行する
**When**: `scaleDownEC2Fleet()`が呼び出される
**Then**:
- Jenkins UIに"Prepare for shutdown"メッセージが表示される
- ログに"Jenkins QuietDownモードを有効化しました"が出力される
- 新規ジョブがキューに追加されない

---

#### AC-002: エージェント実行中ジョブ監視（FR-002）

**Given**: エージェント上でジョブが1つ実行中
**When**: `getRunningAgentExecutors()`を呼び出す
**Then**:
- 戻り値が`1`である
- built-inエージェント（Controller）が除外されている
- ログに"残りのエージェント実行中ジョブ: 1"が出力される

---

#### AC-003: エージェントジョブ完了待機（FR-003）

**Given**: エージェント上でジョブが実行中
**When**: `waitForAgentJobsCompletion(30)`を呼び出す
**Then**:
- ジョブ完了後、待機が正常に終了する
- ログに15秒間隔で進捗が表示される
- タイムアウト（30分）に達した場合、警告ログが出力される
- タイムアウト時でもジョブがfailureステータスにならない

---

#### AC-004: gracefulモードのフロー（FR-004）

**Given**: `SHUTDOWN_MODE=graceful`でジョブを実行
**When**: `scaleDownEC2Fleet()`が呼び出される
**Then**:
- 以下の順序で処理が実行される:
  1. QuietDown設定
  2. エージェントジョブ完了待機
  3. SpotFleetスケールダウン
  4. インスタンス終了待機
  5. QuietDownキャンセル（念のため）
- 各ステップのログが出力される

---

#### AC-005: immediateモードのフロー（FR-004）

**Given**: `SHUTDOWN_MODE=immediate`でジョブを実行
**When**: `scaleDownEC2Fleet()`が呼び出される
**Then**:
- QuietDown設定がスキップされる
- エージェントジョブ完了待機がスキップされる
- SpotFleetスケールダウンが即座に実行される
- 既存の動作と同じ

---

#### AC-006: タイムアウト時のエラーハンドリング（FR-005）

**Given**: エージェントジョブが30分以内に完了しない
**When**: `waitForAgentJobsCompletion(30)`がタイムアウトに達する
**Then**:
- 警告ログ"警告: エージェントジョブのタイムアウト（30分）に達しました。スケールダウンを続行します。"が出力される
- ジョブステータスが`SUCCESS`である
- 次のステップ（SpotFleetスケールダウン）が実行される

---

#### AC-007: Jenkins API呼び出し失敗時のエラーハンドリング（FR-005）

**Given**: Jenkins APIの呼び出しに失敗する
**When**: `setJenkinsQuietMode(true)`が失敗する
**Then**:
- エラーログが出力される
- Script Security承認が必要な場合、メッセージに承認方法が含まれる
- 処理がスキップされ、次のステップに進む

---

#### AC-008: ログ出力の強化（FR-006）

**Given**: gracefulモードでシャットダウンジョブを実行
**When**: 各処理ステップが実行される
**Then**:
- 以下のログが出力される:
  - "Jenkins QuietDownモードを有効化しました"
  - "残りのエージェント実行中ジョブ: X"（15秒間隔）
  - "エージェントジョブの完了を待機中..."
  - "SpotFleetのスケールダウンを開始"
  - "処理が完了しました"

---

### 6.2 非機能要件の受け入れ基準

#### AC-009: パフォーマンス（NFR-001）

**Given**: エージェントジョブ完了待機中
**When**: ポーリングが実行される
**Then**:
- 15秒間隔でチェックが実行される
- CPU使用率が不必要に高くならない

---

#### AC-010: セキュリティ（NFR-003）

**Given**: Script Security承認が必要
**When**: Jenkins APIを呼び出す
**Then**:
- エラーメッセージに承認方法が明記されている
- Jenkins管理画面でScript Approvalが確認できる

---

#### AC-011: ジョブ実行の安全性（NFR-005）

**Given**: エージェント上でジョブが実行中
**When**: gracefulモードでシャットダウンを実行
**Then**:
- ジョブが強制終了されない
- ジョブが正常に完了してからスケールダウンが実行される

---

#### AC-012: 冪等性（NFR-007）

**Given**: 既にquietDownモードが有効
**When**: `setJenkinsQuietMode(true)`を再度呼び出す
**Then**:
- エラーが発生しない
- 既存の状態が維持される

---

## 7. スコープ外

以下の項目は本Issue（#423）のスコープ外とし、将来的な拡張候補とします：

### 7.1 明確にスコープ外とする事項

**OUT-001: NATゲートウェイの段階的停止**
- 現在の実装は維持（即座に停止）
- 理由: NATゲートウェイにはジョブ実行の概念がないため

**OUT-002: Controllerインスタンスの段階的停止**
- 現在の実装は維持（即座に停止コマンド送信）
- 理由: Controllerはbuilt-inエージェントで実行されるため、自身の停止前にジョブが完了する

**OUT-003: 複数環境（dev/staging/prod）の同時シャットダウン**
- 単一環境のみを対象とする
- 理由: パラメータで環境を選択する現在の仕様を維持

**OUT-004: Slack/Email通知の追加**
- ログ出力のみで通知機能は追加しない
- 理由: 既存のジョブでも通知機能は実装されていない

**OUT-005: タイムアウト時の自動リトライ**
- タイムアウト時は警告ログを出力して続行
- 理由: 無限ループのリスクを避けるため

---

### 7.2 将来的な拡張候補

**FUTURE-001: NATゲートウェイの段階的停止**
- SpotFleet終了後、一定時間待機してからNATを停止
- 実装優先度: 低

**FUTURE-002: Slack/Email通知**
- 処理開始・完了時に通知を送信
- 実装優先度: 中

**FUTURE-003: ロールバック機能**
- タイムアウト時にキャパシティを元に戻す
- 実装優先度: 低

**FUTURE-004: カスタムタイムアウトロジック**
- ジョブの種類に応じて動的にタイムアウト時間を調整
- 実装優先度: 低

---

## 8. 補足情報

### 8.1 用語定義

| 用語 | 定義 |
|------|------|
| **QuietDown** | Jenkinsの機能。新規ジョブの受付を停止し、既存ジョブの完了を待つモード |
| **SpotFleet** | AWS EC2のスポットインスタンスを管理する機能 |
| **built-inエージェント** | Jenkins Controller自身の実行環境 |
| **gracefulモード** | 段階的なシャットダウンモード（ジョブ完了を待つ） |
| **immediateモード** | 即座のシャットダウンモード（ジョブを待たない） |

### 8.2 参考資料

- [Planning Document](../../00_planning/output/planning.md)
- [Jenkins CONTRIBUTION.md](/tmp/ai-workflow-repos-3/infrastructure-as-code/jenkins/CONTRIBUTION.md)
- [Jenkins公式ドキュメント - Prepare for Shutdown](https://www.jenkins.io/doc/book/managing/prepare-for-shutdown/)
- [AWS EC2 SpotFleet Documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-fleet.html)

---

## 9. レビューチェックリスト

本要件定義書が品質ゲート（Phase 1）を満たしていることを確認するためのチェックリスト：

- [x] **機能要件が明確に記載されている**: FR-001〜FR-007で具体的に定義
- [x] **受け入れ基準が定義されている**: AC-001〜AC-012でGiven-When-Then形式で記述
- [x] **スコープが明確である**: セクション2（機能要件）とセクション7（スコープ外）で明確化
- [x] **論理的な矛盾がない**: Planning Documentの戦略と整合性があり、各要件間に矛盾なし

---

**作成日**: 2025年1月
**作成者**: AI Workflow Phase 1 (Requirements)
**レビュー状態**: レビュー待ち
