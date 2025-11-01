# 要件定義書: Issue #431

**Issue番号**: #431
**タイトル**: [TASK] ドラフトPRに対するpull_request_comment_builderの実行を抑止
**URL**: https://github.com/tielec/infrastructure-as-code/issues/431
**作成日**: 2025-01-XX
**作成者**: Claude (AI Assistant)
**レビューステータス**: 未レビュー

---

## 0. Planning Documentの確認

### 開発計画の全体像

Planning Phase（`00_planning/output/planning.md`）で策定された計画を確認しました：

- **複雑度**: 簡単（単一機能追加、1ファイル修正、既存実装を参考可能）
- **見積もり工数**: 3~4時間（Phase 5はスキップ）
- **実装戦略**: **EXTEND** - 既存DSLファイルに条件を追加
- **テスト戦略**: **INTEGRATION_ONLY** - 手動インテグレーションテストで検証
- **テストコード戦略**: **Phase 5はスキップ** - Jenkins DSL自動テストは未導入
- **リスク評価**: 低（既存処理への影響が限定的、ロールバック容易）

### 本要件定義書への反映

Planning Documentで策定された以下の方針を要件定義に反映します：

1. **実装方針**: Triggerジョブでのドラフト判定（方法1を採用）
2. **影響範囲**: `docx_generator_pull_request_comment_builder_github_trigger_job.groovy`のみ変更
3. **受け入れ基準**: Planning Documentの「Task 1-2」で定義された3条件を採用
4. **テスト方法**: Planning Documentの「Phase 6」に従い、手動インテグレーションテストで検証

---

## 1. 概要

### 背景

現在、GitHub Webhook経由で`docx_generator_pull_request_comment_builder_github_trigger_job`が起動される際、PRのドラフト状態を判定せずに下流ジョブ（`pull_request_comment_builder`）を常に呼び出しています。その結果、ドラフトPRに対しても以下の不要な処理が実行されています：

- OpenAI APIを使用したコメント生成処理
- 計算リソースの消費
- APIコストの発生

### 目的

ドラフトPRに対する不要な処理を抑止し、以下を実現する：

- **コスト削減**: ドラフト状態のPRではOpenAI API呼び出しをスキップ
- **リソース効率化**: 実質的なレビューが不要な段階での処理を回避
- **運用改善**: PRのドラフト解除後に自動的に処理が再開される仕組み

### ビジネス価値・技術的価値

| 側面 | 価値 |
|------|------|
| **コスト** | OpenAI API呼び出しの削減（ドラフトPR分） |
| **運用効率** | 不要なビルド履歴の削減、ログの見通し向上 |
| **開発体験** | ドラフト段階ではコメント生成が不要という自然なワークフロー |
| **保守性** | 既存の類似実装（MultiBranchジョブ）との整合性向上 |

---

## 2. 機能要件

### FR-01: ドラフトPRの判定機能（優先度: 高）

**説明**:
GitHub Webhookペイロードから`pull_request.draft`フィールドを取得し、PRがドラフト状態かどうかを判定する機能を追加する。

**詳細仕様**:
- Generic Webhook Triggerの`genericVariable`に`PR_DRAFT`変数を追加
- JSONPath: `$.pull_request.draft`
- 型: boolean（GitHub APIの仕様に準拠）

**Planning Document参照**: Phase 4 - Task 4-1

---

### FR-02: 条件付き下流ジョブ実行（優先度: 高）

**説明**:
ドラフトPRの場合は下流ジョブ（`pull_request_comment_builder`）を起動せず、非ドラフトPRの場合のみ起動する。

**詳細仕様**:
- `conditionalSteps`ブロックで`downstreamParameterized`をラップ
- 条件: `stringsMatch('$PR_DRAFT', 'false', false)`（`draft=false`の場合のみ実行）
- スキップ時のビルドステータス: `SUCCESS`または`NOT_BUILT`（既存動作との整合性を考慮）

**Planning Document参照**: Phase 4 - Task 4-2

---

### FR-03: スキップ時のログ出力（優先度: 中）

**説明**:
ドラフトPRで処理をスキップする場合、その旨をビルドログに出力する。

**詳細仕様**:
- Jenkinsのコンソール出力に「Draft PR detected. Skipping downstream job.」等のメッセージを表示
- Generic Webhook Triggerの`causeString`パラメータを調整し、トリガー理由を明示

**Planning Document参照**: Phase 4 - Task 4-2（ログ出力部分）

---

### FR-04: 既存動作の維持（優先度: 高）

**説明**:
非ドラフトPR（通常のPR）に対する既存の動作を変更しない。

**詳細仕様**:
- `draft=false`の場合、従来通り下流ジョブが起動される
- Webhook受信時のパラメータ受け渡し方法は変更しない
- ビルド履歴の記録形式は既存と同一

**Planning Document参照**: Phase 1 - Task 1-2（受け入れ基準3）

---

## 3. 非機能要件

### NFR-01: パフォーマンス要件

- **応答性**: ドラフトPR判定によるWebhook応答時間への影響は1秒未満であること
- **リソース効率**: ドラフトPRの場合、下流ジョブが起動しないため、以下のリソースが節約される
  - Jenkinsエージェントの実行時間（約2〜5分/ジョブ）
  - OpenAI API呼び出し（$0.002〜0.01/リクエスト）

### NFR-02: セキュリティ要件

- **認証・認可**: GitHub Webhookの既存の認証メカニズム（署名検証）をそのまま使用
- **機密情報**: `PR_DRAFT`フィールドは公開情報であり、セキュリティ上の懸念なし

### NFR-03: 可用性・信頼性要件

- **エラーハンドリング**: `pull_request.draft`フィールドが存在しない場合のフォールバック動作
  - 期待動作: `draft`フィールドが存在しない場合は`false`と見なす（後方互換性）
- **冪等性**: 同一PRに対して複数回Webhookが送信されても、一貫した動作を保証

### NFR-04: 保守性・拡張性要件

- **可読性**: DSLファイルにコメントを追加し、ドラフトPRフィルタリングの意図を明記
- **再利用性**: 他のGeneric Webhook Triggerジョブにも同様のパターンを適用可能な汎用的な実装
- **テスト容易性**: シードジョブでDSL変更を反映後、手動テストで動作確認可能

---

## 4. 制約事項

### 技術的制約

- **Jenkins DSL API**: Job DSL Pluginのバージョンに依存（`conditionalSteps`の互換性確認が必要）
- **Generic Webhook Trigger Plugin**: Webhookペイロードの変数抽出機能に依存
- **GitHub Webhook仕様**: `pull_request.draft`フィールドの存在が前提（GitHub APIの仕様変更リスクは極低）

### リソース制約

- **工数**: 合計3〜4時間（Planning Documentに記載）
- **テスト環境**: dev環境のJenkins、テスト用リポジトリ（`infrastructure-as-code`または専用リポジトリ）

### ポリシー制約

- **Jenkinsパラメータ定義ルール**: パラメータはJob DSLファイルで定義し、Jenkinsfileでは定義しない（プロジェクト規約）
- **コーディング規約**: コメントは日本語で記述（`CLAUDE.md`に記載）
- **コミットメッセージ規約**: `[jenkins] update: ドラフトPRフィルタリング機能を追加`形式

---

## 5. 前提条件

### システム環境

- **Jenkins**: バージョン 2.x以上（Generic Webhook Trigger Plugin、Conditional BuildStep Plugin導入済み）
- **プラグイン**:
  - Generic Webhook Trigger Plugin
  - Conditional BuildStep Plugin
  - Job DSL Plugin

### 依存コンポーネント

- **修正対象ファイル**: `jenkins/jobs/dsl/docs-generator/docx_generator_pull_request_comment_builder_github_trigger_job.groovy`
- **シードジョブ**: `Admin_Jobs/job-creator`（DSL変更を反映するために実行が必要）

### 外部システム連携

- **GitHub Webhook**: `pull_request`イベント（actions: `opened`, `reopened`, `synchronize`, `ready_for_review`）
- **Webhookペイロード**: `$.pull_request.draft`フィールドが存在すること

---

## 6. 受け入れ基準

Planning Documentの「Task 1-2: 受け入れ基準の定義」に従い、以下の3条件を受け入れ基準とします。

### AC-01: ドラフトPRでビルドが起動しない

**Given**: GitHubリポジトリにドラフト状態のPRが存在する
**When**: 対象ブランチにコミットをプッシュし、Webhookが送信される
**Then**:
- `docx_generator_pull_request_comment_builder_github_trigger_job`のビルド履歴に記録が**ない**、または
- ビルド履歴に記録があるが、ステータスが`NOT_BUILT`または`SUCCESS`で、下流ジョブが起動していない
- コンソール出力に「Draft PR detected. Skipping downstream job.」相当のメッセージが表示される

**テスト手順**（Planning Document Phase 6 - Task 6-2）:
1. テストリポジトリでドラフトPRを作成
2. Webhookが送信されることを確認（GitHub Webhookログ）
3. Jenkinsジョブのビルド履歴を確認

---

### AC-02: ドラフト解除後にビルドが正常に起動する

**Given**: ドラフト状態のPRが存在する
**When**: PRのドラフトを解除（"Ready for review"）し、Webhookが送信される
**Then**:
- `docx_generator_pull_request_comment_builder_github_trigger_job`が起動する
- 下流ジョブ（`pull_request_comment_builder`）が正常に起動する
- 既存の動作（OpenAI API呼び出し、コメント生成）が正常に実行される

**テスト手順**（Planning Document Phase 6 - Task 6-3）:
1. ドラフトPRを解除（Ready for review）
2. Webhookが送信されることを確認
3. Jenkinsジョブが正常に起動し、下流ジョブが実行されることを確認

---

### AC-03: 既存の非ドラフトPRの動作に影響がない

**Given**: 非ドラフト状態のPR（通常のPR）が存在する
**When**: 対象ブランチにコミットをプッシュし、Webhookが送信される
**Then**:
- `docx_generator_pull_request_comment_builder_github_trigger_job`が起動する
- 下流ジョブ（`pull_request_comment_builder`）が正常に起動する
- 既存の動作と同一の結果が得られる（ビルドステータス、ログ内容、実行時間）

**テスト手順**（Planning Document Phase 6 - Task 6-3）:
1. 非ドラフトPRを作成または既存のPRを使用
2. コミットをプッシュしてWebhookをトリガー
3. ジョブの実行結果が既存動作と一致することを確認

---

## 7. スコープ外

### 明確にスコープ外とする事項

1. **他のジョブへの適用**:
   - Issue #431は`pull_request_comment_builder`のみが対象
   - 他のWebhookトリガージョブ（例: `code_quality_reflection`）への展開は別Issueで対応（Planning Document「リスク4」参照）

2. **Jenkinsfileでの判定実装**:
   - Planning Documentで「方法1: Triggerジョブで判定」を採用
   - 「方法2: Jenkinsfileで判定」は実装しない

3. **ドラフトPR以外のフィルタリング条件**:
   - ラベルによるフィルタリング（例: `WIP`ラベル）
   - PRタイトルによるフィルタリング（例: `[WIP]`プレフィックス）
   - これらは将来的な拡張候補

4. **MultiBranchジョブへの影響**:
   - `code_quality_reflection_cloud_api_multibranch_job.groovy`は既に`gitHubIgnoreDraftPullRequestFilter()`を使用
   - 本Issueでは変更不要

### 将来的な拡張候補

- **ドラフトPRフィルタリングパターンの標準化**:
  - `jenkins/CONTRIBUTION.md`に「よくあるパターン集」を追加
  - 他のWebhookジョブにも同様のパターンを適用するためのテンプレート化

- **ビルド履歴への詳細な記録**:
  - スキップ理由をビルド説明（Build Description）に自動記録
  - ドラフトPRのスキップ統計をダッシュボードに表示

---

## 8. 補足情報

### 参考実装

**類似実装**: `jenkins/jobs/dsl/code-quality-checker/code_quality_reflection_cloud_api_multibranch_job.groovy`
- MultiBranchジョブでの`gitHubIgnoreDraftPullRequestFilter()`の使用例
- ドラフトPRを自動的にスキップする既存実装

### GitHub Webhook仕様

**公式ドキュメント**: https://docs.github.com/en/webhooks/webhook-events-and-payloads#pull_request

**`pull_request.draft`フィールド**:
- 型: boolean
- 説明: PRがドラフト状態かどうか
- 値: `true`（ドラフト）、`false`（非ドラフト）

### 実装サンプル（Planning Document参照）

```groovy
// Generic Webhook Trigger変数の追加
genericVariable {
    key('PR_DRAFT')
    value('$.pull_request.draft')
    expressionType('JSONPath')
    regexpFilter('')
}

// 条件付きビルドステップ
steps {
    conditionalSteps {
        condition {
            stringsMatch('$PR_DRAFT', 'false', false)
        }
        steps {
            downstreamParameterized {
                trigger(downstreamJobName) {
                    // 既存の設定
                }
            }
        }
    }
}
```

---

## 9. 品質ゲート確認

### ✅ 機能要件が明確に記載されている
- FR-01〜FR-04で4つの機能要件を具体的に定義
- 各要件に詳細仕様、Planning Document参照を明記

### ✅ 受け入れ基準が定義されている
- AC-01〜AC-03でGiven-When-Then形式の受け入れ基準を定義
- Planning Documentの「Task 1-2」と整合
- 各基準にテスト手順を明記

### ✅ スコープが明確である
- 機能要件（4項目）、非機能要件（4項目）を明確に定義
- スコープ外事項を明記（他ジョブへの展開、Jenkinsfile実装等）

### ✅ 論理的な矛盾がない
- Planning Documentの方針（方法1採用、Phase 5スキップ）と整合
- 機能要件と受け入れ基準が対応
- 非機能要件と制約事項が矛盾していない

---

**レビュー準備完了**: この要件定義書はクリティカルシンキングレビューを受ける準備ができています。
