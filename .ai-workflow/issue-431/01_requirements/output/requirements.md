# 要件定義書 - Issue #431

## 0. Planning Documentの確認

Planning Phaseで策定された以下の戦略を踏まえて要件定義を実施します：

- **実装戦略**: EXTEND（既存のTrigger JobとJenkinsfileを拡張）
- **テスト戦略**: INTEGRATION_ONLY（GitHub Webhookからジョブ実行までのEnd-to-Endテスト）
- **テストコード戦略**: EXTEND_TEST（手動テスト、既存テストプロセスにドラフトPRケースを追加）
- **複雑度**: 簡単（2ファイルのみ修正、パラメータ追加とステージ追加）
- **見積もり工数**: 2~4時間
- **リスク評価**: 低（既存機能への影響が限定的）

## 1. 概要

### 背景

現在、GitHub Webhookから起動される `docx_generator_pull_request_comment_builder_github_trigger_job` は、PRの状態（ドラフト/非ドラフト）を判定せずに下流の `pull_request_comment_builder` ジョブを常に実行しています。その結果、以下の問題が発生しています：

- ドラフトPRに対しても不要なOpenAI API呼び出しが発生し、コストが無駄になる
- ドラフトPRでの不要なジョブ実行により、ビルドリソースが浪費される
- ドラフトPRに対するコメント投稿が開発フローのノイズになる

### 目的

GitHub Webhook Payloadの `pull_request.draft` フィールドを活用し、ドラフトPRに対するジョブ実行を抑止することで、以下を実現します：

- OpenAI APIコストの削減
- ビルドリソースの効率的な利用
- 開発者体験の向上（ドラフトPRでの不要なノイズ削減）

### ビジネス価値・技術的価値

**ビジネス価値**：
- **コスト削減**: ドラフトPRでのOpenAI API呼び出し（約$0.01~0.05/回）を削減
- **生産性向上**: ビルドリソースを本番準備が整ったPRに集中できる

**技術的価値**：
- **運用効率化**: ビルド履歴でドラフトPRのスキップ理由が明確になる
- **拡張性**: 他の類似ジョブにも同じパターンを適用可能（ベストプラクティス確立）
- **保守性**: 追加プラグイン不要でメンテナンス負荷が増加しない

## 2. 機能要件

### FR-1: GitHub Webhook PayloadからPRドラフト状態の取得【優先度: 高】

**要件**:
- Trigger Job（DSLファイル）のGeneric Webhook Triggerが `$.pull_request.draft` フィールドを取得する
- 取得した値を `PR_DRAFT` 変数として保持する

**詳細**:
- JSONPath: `$.pull_request.draft`
- 変数名: `PR_DRAFT`
- データ型: 文字列（'true' または 'false'）
- デフォルト値: フィールドが存在しない場合は空文字列（非ドラフトとして扱う）

### FR-2: 下流ジョブへのパラメータ伝播【優先度: 高】

**要件**:
- Trigger Jobが下流ジョブ（`pull_request_comment_builder`）をトリガーする際に、`PR_DRAFT` パラメータを渡す
- 既存パラメータ（`PR_NUMBER`, `REPO_URL`, `UPDATE_TITLE`, `FORCE_ANALYSIS`）と同様のメカニズムを使用する

**詳細**:
- パラメータ名: `PR_DRAFT`
- 伝播方法: `predefinedProps` を使用
- 必須パラメータ: No（欠落時は非ドラフトとして処理）

### FR-3: Jenkinsfileでのドラフト判定ロジック【優先度: 高】

**要件**:
- Jenkinsfileの最初のステージとして「ドラフトPRチェック」ステージを追加する
- `PR_DRAFT` パラメータの値が `'true'` の場合、処理をスキップする
- `PR_DRAFT` パラメータが存在しない、または `'false'` の場合、処理を続行する

**詳細**:
- ステージ名: `ドラフトPRチェック`
- 配置位置: 全ステージの最初（既存の「パラメータ検証」ステージよりも前）
- 判定条件: `params.PR_DRAFT == 'true'` または `env.PR_DRAFT == 'true'`
- フォールバック: パラメータが存在しない場合は `'false'` とみなす

### FR-4: スキップ時のビルドステータス設定【優先度: 高】

**要件**:
- ドラフトPRと判定された場合、ビルドステータスを `NOT_BUILT` に設定する
- ビルド説明文（description）に「ドラフトPRのためスキップ」と記録する
- スキップ理由をコンソールログに出力する

**詳細**:
- ビルドステータス: `currentBuild.result = 'NOT_BUILT'`
- ビルド説明文: `currentBuild.description = "ドラフトPRのためスキップ"`
- ログメッセージ:
  - 「このPR (#${params.PR_NUMBER}) はドラフト状態です。処理をスキップします。」
  - 「理由: ドラフトPRではOpenAI API呼び出しやコメント投稿が不要です。」

### FR-5: 非ドラフトPRの既存動作維持【優先度: 高】

**要件**:
- 非ドラフトPR（`PR_DRAFT == 'false'` または パラメータ欠落）の場合、既存の動作を完全に維持する
- 既存ステージ（「パラメータ検証」「環境準備」「PR情報取得」等）に一切の変更を加えない

**詳細**:
- ドラフトチェックステージ通過後は、既存フローを100%維持
- 非ドラフトPRのOpenAI API呼び出し、コメント投稿は変更なし
- 処理時間、ログ出力、エラーハンドリングは既存と同一

## 3. 非機能要件

### NFR-1: パフォーマンス要件

- **ドラフト判定の処理時間**: 1秒以内
- **非ドラフトPRの処理時間**: 既存から変化なし（±5%以内）
- **Trigger Jobの処理時間**: 既存から変化なし（パラメータ追加の影響は無視可能）

### NFR-2: セキュリティ要件

- **パラメータインジェクション対策**: `PR_DRAFT` パラメータは文字列比較のみで使用し、eval等の動的実行は行わない
- **権限管理**: ドラフト判定ロジックは既存の権限管理の影響を受けない（全ユーザーに適用）
- **監査ログ**: スキップされたドラフトPRのビルド履歴はJenkinsビルド履歴に記録される

### NFR-3: 可用性・信頼性要件

- **Webhook障害時の動作**: GitHub Webhookが `pull_request.draft` フィールドを送信しない場合でも、ジョブはエラーなく実行される（非ドラフトとして処理）
- **下位互換性**: 既存の非ドラフトPRのビルド成功率は100%維持（回帰なし）
- **フェイルセーフ**: ドラフト判定ロジックでエラーが発生した場合でも、非ドラフトとして処理を続行する

### NFR-4: 保守性・拡張性要件

- **コードの可読性**: ドラフト判定ロジックはJenkinsfileに明示的に記述され、コメントで意図が明確化される
- **プラグイン依存**: 新規プラグインを追加しない（既存のGeneric Webhook Triggerプラグインのみ使用）
- **他ジョブへの適用**: 同じパターンを他の類似ジョブ（PR関連ジョブ）に適用可能
- **ドキュメント化**: `jenkins/CONTRIBUTION.md` にベストプラクティスとして記載

## 4. 制約事項

### 技術的制約

- **使用技術**: Jenkins Declarative Pipeline、Groovy（Job DSL）、Generic Webhook Triggerプラグイン
- **既存システムとの整合性**:
  - GitHub Webhook Payloadの標準フィールド（`pull_request.draft`）のみ使用
  - Jenkinsパラメータ定義のルールに従う（パラメータはDSLファイルで定義しない）
- **プラグイン制約**: 新規プラグイン追加不可（conditional-buildstepプラグインは使用しない）

### リソース制約

- **時間**: 見積もり工数2~4時間（Planning Documentに基づく）
- **人員**: 開発者1名
- **予算**: OpenAI APIコスト削減効果を期待（追加コスト不要）

### ポリシー制約

- **セキュリティポリシー**: パラメータはSSM Parameter Storeで管理しない（一時的な値のため）
- **コーディング規約**:
  - Jenkinsパラメータ定義はDSLファイルで行う（ただし今回はTriggerジョブから渡されるため定義不要）
  - コメントは日本語で記述
  - CLAUDE.mdのガイドラインに従う

## 5. 前提条件

### システム環境

- **Jenkins**: バージョン2.426.1以上
- **プラグイン**: Generic Webhook Trigger（既存インストール済み）
- **OS**: Amazon Linux 2023（Jenkinsコントローラー）
- **GitHub Webhook**: Pull Request イベントが有効化されている

### 依存コンポーネント

- **Trigger Job**: `docx_generator_pull_request_comment_builder_github_trigger_job`（既存）
- **下流ジョブ**: `pull_request_comment_builder`（既存）
- **GitHub Repository**: `tielec/infrastructure-as-code`（Webhook設定済み）
- **OpenAI API**: 非ドラフトPRのみ呼び出される

### 外部システム連携

- **GitHub Webhook**: Pull Requestイベント（opened, synchronize, reopened, ready_for_review, converted_to_draft）
- **Webhook Payload**: 標準フォーマット（`pull_request.draft` フィールドを含む）

## 6. 受け入れ基準

### AC-1: ドラフトPRでスキップされる

**Given**: ドラフト状態のPRが作成される
**When**: GitHub WebhookがTrigger Jobをトリガーする
**Then**:
- Trigger Jobが `PR_DRAFT=true` を下流ジョブに渡す
- 下流ジョブの「ドラフトPRチェック」ステージでスキップされる
- ビルドステータスが `NOT_BUILT` になる
- ビルド説明文が「ドラフトPRのためスキップ」になる
- コンソールログに「このPR (#X) はドラフト状態です。処理をスキップします。」が出力される
- OpenAI API呼び出しが発生しない
- PRへのコメント投稿が発生しない

### AC-2: ドラフト解除後に正常実行される

**Given**: ドラフトPRが「Ready for review」に変更される
**When**: GitHub WebhookがTrigger Jobをトリガーする
**Then**:
- Trigger Jobが `PR_DRAFT=false` を下流ジョブに渡す
- 下流ジョブの「ドラフトPRチェック」ステージを通過する
- コンソールログに「このPR (#X) は非ドラフト状態です。処理を続行します。」が出力される
- 全ステージ（パラメータ検証、環境準備、PR情報取得、等）が実行される
- OpenAI API呼び出しが成功する
- PRへのコメント投稿が成功する
- ビルドステータスが `SUCCESS` または `FAILURE`（既存と同じ）になる

### AC-3: 非ドラフトPRの回帰テスト

**Given**: 新規に非ドラフトPRが作成される
**When**: GitHub WebhookがTrigger Jobをトリガーする
**Then**:
- 既存と完全に同じ動作をする
- Trigger Jobが `PR_DRAFT=false` を下流ジョブに渡す
- 下流ジョブの「ドラフトPRチェック」ステージを通過する
- 全ステージが既存と同じ順序で実行される
- OpenAI API呼び出しとコメント投稿が既存と同じ動作をする
- ビルド成功率が既存と同等（100%維持）

### AC-4: パラメータ欠落時のフェイルセーフ

**Given**: GitHub Webhookが `pull_request.draft` フィールドを送信しない（古いWebhook形式）
**When**: Trigger Jobがトリガーされる
**Then**:
- `PR_DRAFT` パラメータが空文字列または `null` になる
- 下流ジョブは非ドラフトとして処理を続行する（既存動作を維持）
- エラーやジョブ失敗が発生しない
- ビルドステータスが `SUCCESS` または `FAILURE`（既存と同じ）になる

### AC-5: ビルド履歴の記録

**Given**: ドラフトPRと非ドラフトPRの両方が存在する
**When**: 両方のPRでジョブが実行される
**Then**:
- Jenkinsビルド履歴でドラフトPRのビルドが `NOT_BUILT` と表示される
- 非ドラフトPRのビルドが `SUCCESS` または `FAILURE` と表示される
- ドラフトPRのビルド説明文が「ドラフトPRのためスキップ」と記録される
- ビルドコンソールログからスキップ理由が確認できる

### AC-6: シードジョブでのDSL反映

**Given**: Trigger JobのDSLファイルが修正される
**When**: シードジョブ（`Admin_Jobs/job-creator`）が実行される
**Then**:
- DSLファイルの変更が正常に反映される
- Trigger Jobの設定画面で「Generic Webhook Trigger」セクションに `PR_DRAFT` 変数が表示される
- エラーやビルド失敗が発生しない

## 7. スコープ外

### 明確にスコープ外とする事項

以下は今回のタスクのスコープ外とし、将来的な拡張候補として扱います：

- **他のPR関連ジョブへの適用**:
  - 今回は `pull_request_comment_builder` のみ対応
  - 他のジョブ（マルチブランチジョブ等）は別タスクで対応

- **ドラフト状態の通知**:
  - SlackやGitHub Statusへの通知は実装しない
  - ビルド履歴とコンソールログのみで記録

- **ドラフトPRの自動再実行**:
  - ドラフト解除時に自動的にジョブを再トリガーする機能は実装しない
  - GitHub Webhookの標準動作に依存

- **条件付きビルドプラグインの導入**:
  - conditional-buildstepプラグインは使用しない
  - Jenkinsfileでのスクリプト判定のみ使用

- **パラメータのSSM保存**:
  - `PR_DRAFT` は一時的な値のためSSM Parameter Storeに保存しない

- **テスト自動化**:
  - Jenkins Pipelineのユニットテストは作成しない（プロジェクトポリシー）
  - 手動テストのみ実施

### 将来的な拡張候補

- **ドラフトPRフィルタリングパターンの汎用化**:
  - 共有ライブラリ（vars/）にドラフトチェック関数を実装
  - 他のジョブから簡単に利用可能にする

- **ドラフト状態の可視化**:
  - Jenkins Dashboard上でドラフトPRのビルドを視覚的に区別
  - ビルドバッジやアイコンのカスタマイズ

- **コスト削減効果のモニタリング**:
  - ドラフトPRでのAPI呼び出しスキップ回数を記録
  - 月次レポートでコスト削減効果を可視化

## 8. 補足情報

### GitHub Webhook Payloadの構造

```json
{
  "action": "opened",
  "pull_request": {
    "number": 123,
    "draft": true,
    "html_url": "https://github.com/tielec/infrastructure-as-code/pull/123"
  },
  "repository": {
    "html_url": "https://github.com/tielec/infrastructure-as-code"
  }
}
```

- `pull_request.draft`: PRがドラフト状態かどうか（boolean）
- `action`: Webhookイベントの種類（opened, synchronize, reopened, ready_for_review, converted_to_draft）

### 参考ドキュメント

- [GitHub Webhook Payload](https://docs.github.com/en/webhooks/webhook-events-and-payloads#pull_request)
- [Generic Webhook Triggerプラグイン](https://plugins.jenkins.io/generic-webhook-trigger/)
- [Jenkins Declarative Pipeline](https://www.jenkins.io/doc/book/pipeline/syntax/)
- [jenkins/CONTRIBUTION.md](jenkins/CONTRIBUTION.md) - Jenkinsジョブ開発規約
- [CLAUDE.md](CLAUDE.md) - プロジェクト全体のガイドライン

### リスク軽減策（Planning Documentより）

- **リスク1: GitHub Webhook Payloadの`draft`フィールドが送信されない**
  - 軽減策: フィールド欠落時はデフォルトで非ドラフトとして扱う（安全側に倒れる）

- **リスク2: Trigger JobとJenkinsfile間のパラメータ伝播失敗**
  - 軽減策: 既存の `PR_NUMBER`、`REPO_URL` パラメータと同じパターンを使用（実績あり）

- **リスク3: ドラフトPRの判定ロジックのバグ**
  - 軽減策: シンプルな文字列比較（`isDraft == 'true'`）のみで実装

- **リスク4: 回帰リスク（非ドラフトPRの動作変更）**
  - 軽減策: 既存ステージに一切変更を加えない（追加のみ）

---

**要件定義書作成日**: 2025-01-XX
**作成者**: Claude Code
**レビューステータス**: 未レビュー（クリティカルシンキングレビュー待ち）
