# テストシナリオ - Issue #431

## 0. Planning Documentの確認

Planning Phaseで策定された以下の戦略を踏まえてテストシナリオを作成します：

- **実装戦略**: EXTEND（既存のTrigger JobとJenkinsfileを拡張）
- **テスト戦略**: INTEGRATION_ONLY（GitHub Webhookからジョブ実行までのEnd-to-Endテスト）
- **テストコード戦略**: EXTEND_TEST（手動テスト、既存テストプロセスにドラフトPRケースを追加）
- **複雑度**: 簡単（2ファイルのみ修正、パラメータ追加とステージ追加）
- **見積もり工数**: 2~4時間
- **リスク評価**: 低（既存機能への影響が限定的）

## 1. テスト戦略サマリー

### 選択されたテスト戦略

**INTEGRATION_ONLY**

### テスト対象の範囲

本テストでは、以下のコンポーネント間の連携を統合的に検証します：

```
GitHub Webhook
    ↓
Generic Webhook Trigger Plugin
    ↓
Trigger Job (docx_generator_pull_request_comment_builder_github_trigger_job)
    ↓
Pipeline Job (pull_request_comment_builder)
    ↓
OpenAI API / GitHub API
```

**検証対象**:
1. GitHub Webhook PayloadからのPRドラフト状態の取得
2. Trigger JobでのGeneric Webhook Triggerによるパラメータ抽出
3. Trigger Jobから下流Pipeline Jobへのパラメータ伝播
4. Pipeline Jobでのドラフト判定ロジック
5. ドラフトPRの場合のスキップ動作
6. 非ドラフトPRの場合の既存動作維持

### テストの目的

- **目的1**: ドラフトPRに対してジョブが正しくスキップされることを確認
- **目的2**: 非ドラフトPRに対して既存動作が維持されることを確認（回帰テスト）
- **目的3**: パラメータ伝播が正しく機能することを確認
- **目的4**: エラーハンドリング（パラメータ欠落時のフェイルセーフ）を確認

### Unitテスト・BDDテスト不要の理由

**Unitテスト不要**:
- Groovyスクリプト（DSL、Jenkinsfile）はJenkinsランタイムに強く依存し、単体テストが困難
- 追加するロジックは単純な条件判定のみ（`if (isDraft == 'true')`）
- プロジェクトポリシーとしてJenkins Pipeline/DSLの自動テストコードは存在しない

**BDDテスト不要**:
- エンドユーザー向け機能ではなく、内部的な最適化（コスト削減）
- ユーザーストーリーというよりは技術的な改善

## 2. Integrationテストシナリオ

### 前提条件（全シナリオ共通）

#### システム環境
- Jenkins環境（dev環境）が正常に稼働している
- Generic Webhook Triggerプラグインがインストール済み
- GitHub Webhook設定が有効（Pull Request イベント）
- リポジトリ: `tielec/infrastructure-as-code`

#### 事前準備
1. ブランチで修正されたコードがコミット済み
2. シードジョブ（`Admin_Jobs/job-creator`）が実行され、DSL変更が反映されている
3. Trigger Job（`docx_generator_pull_request_comment_builder_github_trigger_job`）の設定に `PR_DRAFT` 変数が追加されている
4. Pipeline Job（`pull_request_comment_builder`）のJenkinsfileに「ドラフトPRチェック」ステージが追加されている

#### テスト実行者
- Jenkins管理者権限を持つ開発者
- GitHubリポジトリへのWrite権限を持つ開発者

---

## テストケース1: ドラフトPR作成時のスキップ確認

### シナリオ名
ドラフトPRが作成されたときに、ジョブが正しくスキップされることを確認する

### 目的
- GitHub Webhook Payloadからドラフト状態（`draft=true`）が正しく取得されることを確認
- Trigger Jobが `PR_DRAFT=true` を下流ジョブに渡すことを確認
- Pipeline Jobの「ドラフトPRチェック」ステージでスキップされることを確認
- ビルドステータスが `NOT_BUILT` になることを確認
- OpenAI API呼び出しが発生しないことを確認

### 前提条件
- GitHubリポジトリに変更をプッシュ済み
- Jenkins環境が正常稼働中
- OpenAI APIキーが設定されている（ただし今回は呼び出されない）

### テスト手順

#### Step 1: ドラフトPRの作成
1. GitHubリポジトリ（`tielec/infrastructure-as-code`）にアクセス
2. 新しいブランチを作成（例: `test/draft-pr-skip-431`）
3. 適当なファイルを編集（例: `README.md` に1行追加）
4. コミット・プッシュ
5. GitHubでPull Requestを作成
   - **重要**: 「Create draft pull request」を選択してドラフトPRとして作成
6. PR番号を記録（例: #500）

#### Step 2: Webhook送信の確認
1. GitHubリポジトリの「Settings」→「Webhooks」にアクセス
2. 該当するWebhook（Jenkins用）の「Recent Deliveries」を確認
3. 最新のPull RequestイベントのPayloadを確認
   - `pull_request.number` が正しいPR番号であること
   - `pull_request.draft` が `true` であること
   - `action` が `opened` であること

#### Step 3: Trigger Jobの実行確認
1. Jenkinsにアクセス
2. Trigger Job（`Docs-Generator-Jobs/docx_generator_pull_request_comment_builder_github_trigger_job`）のビルド履歴を確認
3. 最新のビルドを開き、コンソールログを確認
4. 以下を確認：
   - ビルドがWebhookによってトリガーされたこと
   - `PR_NUMBER` が正しいPR番号であること
   - `PR_DRAFT` が `true` として取得されていること
   - 下流ジョブ（`pull_request_comment_builder`）がトリガーされたこと

#### Step 4: Pipeline Jobの実行確認
1. Pipeline Job（`Docs-Generator-Jobs/pull_request_comment_builder`）のビルド履歴を確認
2. 最新のビルド（PR番号に対応）を開く
3. ビルドステータスを確認：
   - **期待値**: ステータスが `NOT_BUILT`（灰色）であること
4. ビルド説明文を確認：
   - **期待値**: 「ドラフトPRのためスキップ」と表示されていること

#### Step 5: コンソールログの確認
1. Pipeline Jobのコンソールログを表示
2. 以下のログメッセージが出力されていることを確認：
   ```
   [Pipeline] stage
   [Pipeline] { (ドラフトPRチェック)
   [Pipeline] script
   [Pipeline] {
   [Pipeline] echo
   このPR (#500) はドラフト状態です。処理をスキップします。
   [Pipeline] echo
   理由: ドラフトPRではOpenAI API呼び出しやコメント投稿が不要です。
   [Pipeline] }
   [Pipeline] // script
   [Pipeline] }
   [Pipeline] // stage
   [Pipeline] End of Pipeline
   ```
3. 後続のステージ（「パラメータ検証」「環境準備」等）が**実行されていない**ことを確認

#### Step 6: OpenAI API呼び出しの確認
1. コンソールログ全体を検索
2. OpenAI APIに関連するログが**存在しない**ことを確認：
   - 「OpenAI API呼び出し」
   - 「GPT-4」
   - 「API response」
   - 等のキーワードが見つからないこと

#### Step 7: GitHubへのコメント投稿の確認
1. 作成したドラフトPR（#500）をGitHubで開く
2. PRのコメント欄を確認
3. Jenkinsからのコメント（AI分析結果）が**投稿されていない**ことを確認

### 期待結果

| 項目 | 期待値 | 確認方法 |
|------|--------|----------|
| GitHub Webhook送信 | `pull_request.draft=true` が送信される | GitHub Webhook Recent Deliveries |
| Trigger Jobのパラメータ取得 | `PR_DRAFT=true` が取得される | Trigger Jobのコンソールログ |
| Trigger Jobから下流ジョブへの伝播 | `PR_DRAFT=true` が渡される | Trigger Jobのコンソールログ |
| Pipeline Jobのビルドステータス | `NOT_BUILT` | ビルド履歴画面 |
| Pipeline Jobのビルド説明文 | 「ドラフトPRのためスキップ」 | ビルド履歴画面 |
| コンソールログ（スキップメッセージ） | 「このPR (#X) はドラフト状態です。処理をスキップします。」 | Pipeline Jobのコンソールログ |
| コンソールログ（理由） | 「理由: ドラフトPRではOpenAI API呼び出しやコメント投稿が不要です。」 | Pipeline Jobのコンソールログ |
| 後続ステージの実行 | 実行されない | Pipeline Jobのコンソールログ |
| OpenAI API呼び出し | 発生しない | Pipeline Jobのコンソールログ（関連ログなし） |
| GitHubへのコメント投稿 | 投稿されない | GitHub PR画面 |

### 確認項目チェックリスト

- [ ] GitHub Webhookが正しく送信されている
- [ ] Webhook Payloadに `pull_request.draft=true` が含まれている
- [ ] Trigger Jobが `PR_DRAFT` 変数を取得している
- [ ] Trigger Jobが下流ジョブに `PR_DRAFT=true` を渡している
- [ ] Pipeline Jobのビルドステータスが `NOT_BUILT` である
- [ ] Pipeline Jobのビルド説明文が「ドラフトPRのためスキップ」である
- [ ] コンソールログに「ドラフト状態です。処理をスキップします。」が出力されている
- [ ] コンソールログに理由説明が出力されている
- [ ] 「パラメータ検証」ステージが実行されていない
- [ ] 「環境準備」ステージが実行されていない
- [ ] 「PR情報と差分の取得」ステージが実行されていない
- [ ] OpenAI API呼び出しのログが存在しない
- [ ] GitHubへのコメントが投稿されていない

### テスト完了条件

- すべての確認項目がチェック済み
- 期待結果と実際の結果が一致
- 異常なエラーログが存在しない

---

## テストケース2: ドラフト解除時の実行確認

### シナリオ名
ドラフトPRが「Ready for review」に変更されたときに、ジョブが正常に実行されることを確認する

### 目的
- ドラフト解除時のWebhook（`action=ready_for_review`）が正しく処理されることを確認
- Trigger Jobが `PR_DRAFT=false` を下流ジョブに渡すことを確認
- Pipeline Jobの「ドラフトPRチェック」ステージを通過することを確認
- 全ステージが正常に実行されることを確認
- OpenAI API呼び出しとGitHubコメント投稿が成功することを確認

### 前提条件
- テストケース1でドラフトPRが作成済み（例: #500）
- テストケース1が成功している（ドラフトPRでスキップされた）
- Jenkins環境が正常稼働中
- OpenAI APIキーが正しく設定されている

### テスト手順

#### Step 1: ドラフトの解除
1. GitHubで作成したドラフトPR（#500）にアクセス
2. 「Ready for review」ボタンをクリック
3. PRがドラフトではなくなったことを確認（Draft PRバッジが消える）

#### Step 2: Webhook送信の確認
1. GitHubリポジトリの「Settings」→「Webhooks」にアクセス
2. 該当するWebhook（Jenkins用）の「Recent Deliveries」を確認
3. 最新のPull Requestイベント（`action=ready_for_review`）のPayloadを確認
   - `pull_request.number` が正しいPR番号であること
   - `pull_request.draft` が `false` であること
   - `action` が `ready_for_review` であること

#### Step 3: Trigger Jobの実行確認
1. Jenkinsにアクセス
2. Trigger Job（`Docs-Generator-Jobs/docx_generator_pull_request_comment_builder_github_trigger_job`）のビルド履歴を確認
3. 最新のビルド（ドラフト解除後）を開き、コンソールログを確認
4. 以下を確認：
   - ビルドがWebhookによってトリガーされたこと
   - `PR_NUMBER` が正しいPR番号であること
   - `PR_DRAFT` が `false` として取得されていること
   - 下流ジョブ（`pull_request_comment_builder`）がトリガーされたこと

#### Step 4: Pipeline Jobの実行確認
1. Pipeline Job（`Docs-Generator-Jobs/pull_request_comment_builder`）のビルド履歴を確認
2. 最新のビルド（ドラフト解除後）を開く
3. ビルドステータスを確認：
   - **期待値**: ステータスが `SUCCESS`（緑）または `FAILURE`（赤）であること（`NOT_BUILT` ではない）

#### Step 5: コンソールログの確認（ドラフトチェックステージ）
1. Pipeline Jobのコンソールログを表示
2. 「ドラフトPRチェック」ステージのログを確認：
   ```
   [Pipeline] stage
   [Pipeline] { (ドラフトPRチェック)
   [Pipeline] script
   [Pipeline] {
   [Pipeline] echo
   このPR (#500) は非ドラフト状態です。処理を続行します。
   [Pipeline] }
   [Pipeline] // script
   [Pipeline] }
   [Pipeline] // stage
   ```
3. ステージが正常に通過し、`return` が実行されていないことを確認

#### Step 6: 全ステージの実行確認
1. コンソールログで以下のステージが実行されていることを確認：
   - 「ドラフトPRチェック」（通過）
   - 「パラメータ検証」
   - 「環境準備」
   - 「PR情報と差分の取得」
   - 「OpenAI API呼び出し」
   - 「コメント投稿」
   - 等（既存の全ステージ）

#### Step 7: OpenAI API呼び出しの確認
1. コンソールログでOpenAI APIに関連するログを確認：
   - 「OpenAI API呼び出し」または類似のメッセージ
   - API requestとresponseのログ
   - エラーが発生していないこと

#### Step 8: GitHubへのコメント投稿の確認
1. 作成したPR（#500）をGitHubで開く
2. PRのコメント欄を確認
3. Jenkinsからのコメント（AI分析結果）が投稿されていることを確認
4. コメント内容が適切であることを確認（PRの差分に基づく分析結果）

#### Step 9: ビルド完了の確認
1. Pipeline Jobのビルドが正常に完了していることを確認
2. ビルドステータスが `SUCCESS` であることを確認（エラーがない場合）

### 期待結果

| 項目 | 期待値 | 確認方法 |
|------|--------|----------|
| GitHub Webhook送信 | `pull_request.draft=false` が送信される | GitHub Webhook Recent Deliveries |
| Trigger Jobのパラメータ取得 | `PR_DRAFT=false` が取得される | Trigger Jobのコンソールログ |
| Trigger Jobから下流ジョブへの伝播 | `PR_DRAFT=false` が渡される | Trigger Jobのコンソールログ |
| Pipeline Jobのビルドステータス | `SUCCESS` または `FAILURE`（`NOT_BUILT` ではない） | ビルド履歴画面 |
| コンソールログ（通過メッセージ） | 「このPR (#X) は非ドラフト状態です。処理を続行します。」 | Pipeline Jobのコンソールログ |
| 「パラメータ検証」ステージ | 実行される | Pipeline Jobのコンソールログ |
| 「環境準備」ステージ | 実行される | Pipeline Jobのコンソールログ |
| 「PR情報と差分の取得」ステージ | 実行される | Pipeline Jobのコンソールログ |
| OpenAI API呼び出し | 成功する | Pipeline Jobのコンソールログ |
| GitHubへのコメント投稿 | 投稿される | GitHub PR画面 |
| ビルド完了 | `SUCCESS` | ビルド履歴画面 |

### 確認項目チェックリスト

- [ ] GitHub Webhookが正しく送信されている（`action=ready_for_review`）
- [ ] Webhook Payloadに `pull_request.draft=false` が含まれている
- [ ] Trigger Jobが `PR_DRAFT` 変数を取得している（値: `false`）
- [ ] Trigger Jobが下流ジョブに `PR_DRAFT=false` を渡している
- [ ] Pipeline Jobのビルドステータスが `NOT_BUILT` ではない
- [ ] コンソールログに「非ドラフト状態です。処理を続行します。」が出力されている
- [ ] 「ドラフトPRチェック」ステージで `return` が実行されていない
- [ ] 「パラメータ検証」ステージが実行されている
- [ ] 「環境準備」ステージが実行されている
- [ ] 「PR情報と差分の取得」ステージが実行されている
- [ ] OpenAI API呼び出しのログが存在する
- [ ] OpenAI API呼び出しが成功している（エラーなし）
- [ ] GitHubへのコメントが投稿されている
- [ ] コメント内容が適切である（PRの差分に基づく分析）
- [ ] ビルドが正常に完了している（`SUCCESS`）

### テスト完了条件

- すべての確認項目がチェック済み
- 期待結果と実際の結果が一致
- ビルドが `SUCCESS` で完了
- GitHubにコメントが投稿されている

---

## テストケース3: 非ドラフトPRの回帰テスト

### シナリオ名
新規に非ドラフトPRを作成したときに、既存動作が維持されることを確認する（回帰テスト）

### 目的
- 既存の非ドラフトPRの動作に影響がないことを確認
- 「ドラフトPRチェック」ステージ追加による回帰がないことを確認
- パフォーマンスへの影響がないことを確認

### 前提条件
- Jenkins環境が正常稼働中
- OpenAI APIキーが正しく設定されている
- 過去の非ドラフトPRのビルド履歴がある（比較用）

### テスト手順

#### Step 1: 非ドラフトPRの作成
1. GitHubリポジトリ（`tielec/infrastructure-as-code`）にアクセス
2. 新しいブランチを作成（例: `test/non-draft-pr-regression-431`）
3. 適当なファイルを編集（例: `README.md` に1行追加）
4. コミット・プッシュ
5. GitHubでPull Requestを作成
   - **重要**: 通常のPRとして作成（ドラフトではない）
   - 「Create draft pull request」を選択しない
6. PR番号を記録（例: #501）

#### Step 2: Webhook送信の確認
1. GitHubリポジトリの「Settings」→「Webhooks」にアクセス
2. 該当するWebhook（Jenkins用）の「Recent Deliveries」を確認
3. 最新のPull RequestイベントのPayloadを確認
   - `pull_request.number` が正しいPR番号であること
   - `pull_request.draft` が `false` であること
   - `action` が `opened` であること

#### Step 3: Trigger Jobの実行確認
1. Jenkinsにアクセス
2. Trigger Job（`Docs-Generator-Jobs/docx_generator_pull_request_comment_builder_github_trigger_job`）のビルド履歴を確認
3. 最新のビルドを開き、コンソールログを確認
4. 以下を確認：
   - ビルドがWebhookによってトリガーされたこと
   - `PR_NUMBER` が正しいPR番号であること
   - `PR_DRAFT` が `false` として取得されていること
   - 下流ジョブ（`pull_request_comment_builder`）がトリガーされたこと

#### Step 4: Pipeline Jobの実行確認
1. Pipeline Job（`Docs-Generator-Jobs/pull_request_comment_builder`）のビルド履歴を確認
2. 最新のビルド（PR #501）を開く
3. ビルドステータスを確認：
   - **期待値**: ステータスが `SUCCESS`（緑）であること

#### Step 5: 全ステージの実行確認
1. Pipeline Jobのコンソールログを表示
2. 以下のステージが既存と同じ順序で実行されていることを確認：
   - 「ドラフトPRチェック」（新規追加、通過するのみ）
   - 「パラメータ検証」
   - 「環境準備」
   - 「PR情報と差分の取得」
   - 「OpenAI API呼び出し」
   - 「コメント投稿」
   - 等（既存の全ステージ）

#### Step 6: 既存ステージのログ比較
1. 過去の非ドラフトPRのビルドログを開く（修正前のビルド）
2. 今回のビルドログと比較
3. 以下を確認：
   - 「パラメータ検証」以降のステージのログ内容が既存と同じであること
   - エラーメッセージが増えていないこと
   - ステージの実行順序が変わっていないこと

#### Step 7: パフォーマンスの比較
1. 過去の非ドラフトPRのビルド時間を確認
2. 今回のビルド時間を確認
3. 差分を計算：
   - **期待値**: ビルド時間の差が±5%以内であること
   - 「ドラフトPRチェック」ステージの追加による影響がほぼゼロであること

#### Step 8: OpenAI API呼び出しとコメント投稿の確認
1. コンソールログでOpenAI API呼び出しが成功していることを確認
2. GitHubのPR（#501）にコメントが投稿されていることを確認
3. コメント内容が適切であることを確認

#### Step 9: ビルド成功率の確認
1. Pipeline Jobのビルド履歴を確認
2. 今回のビルドが `SUCCESS` で完了していることを確認
3. 既存の非ドラフトPRのビルド成功率と比較：
   - **期待値**: ビルド成功率が100%維持されていること

### 期待結果

| 項目 | 期待値 | 確認方法 |
|------|--------|----------|
| GitHub Webhook送信 | `pull_request.draft=false` が送信される | GitHub Webhook Recent Deliveries |
| Trigger Jobのパラメータ取得 | `PR_DRAFT=false` が取得される | Trigger Jobのコンソールログ |
| Pipeline Jobのビルドステータス | `SUCCESS` | ビルド履歴画面 |
| ステージ実行順序 | 既存と同じ（「ドラフトPRチェック」が最初に追加されるのみ） | Pipeline Jobのコンソールログ |
| 「パラメータ検証」以降のログ | 既存と同じ | Pipeline Jobのコンソールログ比較 |
| ビルド時間 | 既存±5%以内 | ビルド履歴画面 |
| OpenAI API呼び出し | 成功する | Pipeline Jobのコンソールログ |
| GitHubへのコメント投稿 | 投稿される | GitHub PR画面 |
| ビルド成功率 | 100%維持 | ビルド履歴画面 |

### 確認項目チェックリスト

- [ ] GitHub Webhookが正しく送信されている
- [ ] Webhook Payloadに `pull_request.draft=false` が含まれている
- [ ] Trigger Jobが `PR_DRAFT` 変数を取得している（値: `false`）
- [ ] Pipeline Jobのビルドステータスが `SUCCESS` である
- [ ] 「ドラフトPRチェック」ステージが最初のステージとして追加されている
- [ ] 「ドラフトPRチェック」ステージが正常に通過している
- [ ] 「パラメータ検証」以降のステージが既存と同じ順序で実行されている
- [ ] 既存ステージのログ内容が変わっていない
- [ ] ビルド時間が既存±5%以内である
- [ ] OpenAI API呼び出しが成功している
- [ ] GitHubへのコメントが投稿されている
- [ ] コメント内容が適切である
- [ ] ビルドが `SUCCESS` で完了している
- [ ] エラーメッセージが増えていない
- [ ] ビルド成功率が100%維持されている

### テスト完了条件

- すべての確認項目がチェック済み
- 期待結果と実際の結果が一致
- 既存動作に回帰がない
- パフォーマンスへの影響が許容範囲内

---

## テストケース4: パラメータ欠落時のフェイルセーフ確認

### シナリオ名
GitHub Webhookが `pull_request.draft` フィールドを送信しない場合でも、エラーなく非ドラフトとして処理されることを確認する

### 目的
- パラメータ欠落時のフェイルセーフ機能を確認
- 古いWebhook形式や異常なPayloadでもジョブが失敗しないことを確認
- デフォルト値（`'false'`）が正しく適用されることを確認

### 前提条件
- Jenkins環境が正常稼働中
- Trigger Jobを手動でトリガーできる環境

### テスト手順

#### Step 1: Trigger Jobの手動トリガー（PR_DRAFTなし）
1. Jenkinsにアクセス
2. Trigger Job（`Docs-Generator-Jobs/docx_generator_pull_request_comment_builder_github_trigger_job`）を開く
3. 「Build with Parameters」をクリック
4. パラメータを入力：
   - `REPO_URL`: `https://github.com/tielec/infrastructure-as-code`
   - `PR_NUMBER`: 既存の非ドラフトPR番号（例: `501`）
   - `PR_DRAFT`: **入力しない**（空欄のまま）
5. 「Build」をクリック

#### Step 2: Trigger Jobの実行確認
1. Trigger Jobのビルド履歴を確認
2. 最新のビルドを開き、コンソールログを確認
3. エラーが発生していないことを確認
4. 下流ジョブがトリガーされたことを確認

#### Step 3: Pipeline Jobの実行確認
1. Pipeline Job（`Docs-Generator-Jobs/pull_request_comment_builder`）のビルド履歴を確認
2. 最新のビルド（Trigger Jobから起動されたもの）を開く
3. ビルドステータスを確認：
   - **期待値**: ステータスが `NOT_BUILT` ではない（`SUCCESS` または `FAILURE`）

#### Step 4: コンソールログの確認（デフォルト値の適用）
1. Pipeline Jobのコンソールログを表示
2. 「ドラフトPRチェック」ステージのログを確認：
   ```
   [Pipeline] stage
   [Pipeline] { (ドラフトPRチェック)
   [Pipeline] script
   [Pipeline] {
   [Pipeline] echo
   このPR (#501) は非ドラフト状態です。処理を続行します。
   [Pipeline] }
   [Pipeline] // script
   [Pipeline] }
   [Pipeline] // stage
   ```
3. `PR_DRAFT` が欠落しているが、デフォルト値 `'false'` として扱われていることを確認

#### Step 5: 全ステージの実行確認
1. コンソールログで全ステージが実行されていることを確認：
   - 「ドラフトPRチェック」（通過）
   - 「パラメータ検証」
   - 「環境準備」
   - 「PR情報と差分の取得」
   - 等（既存の全ステージ）

#### Step 6: エラーログの確認
1. コンソールログ全体を確認
2. `PR_DRAFT` に関連するエラーメッセージがないことを確認
3. ビルドが正常に完了していることを確認

### 期待結果

| 項目 | 期待値 | 確認方法 |
|------|--------|----------|
| Trigger Jobのビルド | エラーなく完了 | Trigger Jobのコンソールログ |
| Pipeline Jobのトリガー | 正常にトリガーされる | Trigger Jobのコンソールログ |
| Pipeline Jobのビルドステータス | `SUCCESS` または `FAILURE`（`NOT_BUILT` ではない） | ビルド履歴画面 |
| デフォルト値の適用 | `PR_DRAFT` が欠落していても `'false'` として扱われる | Pipeline Jobのコンソールログ |
| コンソールログ（通過メッセージ） | 「このPR (#X) は非ドラフト状態です。処理を続行します。」 | Pipeline Jobのコンソールログ |
| 全ステージの実行 | 実行される | Pipeline Jobのコンソールログ |
| エラーログ | `PR_DRAFT` に関連するエラーなし | Pipeline Jobのコンソールログ |
| ビルド完了 | エラーなく完了 | ビルド履歴画面 |

### 確認項目チェックリスト

- [ ] Trigger Jobがエラーなく完了している
- [ ] 下流Pipeline Jobが正常にトリガーされている
- [ ] Pipeline Jobのビルドステータスが `NOT_BUILT` ではない
- [ ] 「ドラフトPRチェック」ステージで「非ドラフト状態です。処理を続行します。」が出力されている
- [ ] `PR_DRAFT` が欠落していてもエラーにならない
- [ ] デフォルト値 `'false'` が適用されている
- [ ] 全ステージが実行されている
- [ ] `PR_DRAFT` に関連するエラーメッセージがない
- [ ] ビルドが正常に完了している

### テスト完了条件

- すべての確認項目がチェック済み
- パラメータ欠落時でもジョブが正常に動作
- フェイルセーフ機能が正しく機能している

---

## テストケース5: シードジョブでのDSL反映確認

### シナリオ名
Trigger JobのDSLファイル修正がシードジョブ実行によって正しく反映されることを確認する

### 目的
- DSLファイルの変更がJenkinsジョブ定義に正しく反映されることを確認
- Generic Webhook Trigger設定に `PR_DRAFT` 変数が追加されることを確認
- エラーなくシードジョブが完了することを確認

### 前提条件
- DSLファイル（`docx_generator_pull_request_comment_builder_github_trigger_job.groovy`）が修正済み
- Jenkinsfileが修正済み
- Jenkins環境が正常稼働中
- シードジョブ（`Admin_Jobs/job-creator`）が存在する

### テスト手順

#### Step 1: シードジョブの実行
1. Jenkinsにアクセス
2. シードジョブ（`Admin_Jobs/job-creator`）を開く
3. 「Build Now」をクリック
4. ビルドが開始されることを確認

#### Step 2: シードジョブの完了確認
1. シードジョブのビルド履歴を確認
2. 最新のビルドを開く
3. ビルドステータスが `SUCCESS` であることを確認
4. コンソールログを開く

#### Step 3: コンソールログの確認
1. コンソールログで以下を確認：
   - DSLファイル（`docx_generator_pull_request_comment_builder_github_trigger_job.groovy`）が処理されたこと
   - 「GeneratedJob」のログが表示されていること
   - エラーメッセージがないこと

#### Step 4: Trigger Job設定の確認
1. Trigger Job（`Docs-Generator-Jobs/docx_generator_pull_request_comment_builder_github_trigger_job`）を開く
2. 「Configure」（設定）をクリック
3. 「Build Triggers」セクションを確認
4. 「Generic Webhook Trigger」設定を確認：
   - 「Generic Variables」リストに `PR_DRAFT` が追加されていること
   - `PR_DRAFT` の「Variable name」が `PR_DRAFT` であること
   - `PR_DRAFT` の「Expression」が `$.pull_request.draft` であること
   - `PR_DRAFT` の「Expression type」が `JSONPath` であること

#### Step 5: 下流ジョブパラメータの確認
1. Trigger Jobの設定画面で「Build」セクションを確認
2. 「Trigger parameterized build on other projects」設定を確認：
   - 「Predefined parameters」に `PR_DRAFT=$PR_DRAFT` が含まれていること

#### Step 6: Pipeline Job設定の確認
1. Pipeline Job（`Docs-Generator-Jobs/pull_request_comment_builder`）を開く
2. 「Configure」（設定）をクリック
3. 「Pipeline」セクションを確認：
   - 「Definition」が「Pipeline script from SCM」であること
   - 「Script Path」がJenkinsfileのパスを指していること
4. パラメータ定義に `PR_DRAFT` が**追加されていない**ことを確認（Triggerジョブから渡されるため）

#### Step 7: Jenkinsfileの内容確認
1. GitHubでJenkinsfileを開く
2. 「ドラフトPRチェック」ステージが追加されていることを確認：
   - ステージ名: `ドラフトPRチェック`
   - 配置位置: 全ステージの最初
   - ロジック: `params.PR_DRAFT` または `env.PR_DRAFT` を評価

### 期待結果

| 項目 | 期待値 | 確認方法 |
|------|--------|----------|
| シードジョブのビルドステータス | `SUCCESS` | ビルド履歴画面 |
| DSLファイル処理 | エラーなく処理される | シードジョブのコンソールログ |
| Generic Webhook Trigger設定 | `PR_DRAFT` 変数が追加される | Trigger Job設定画面 |
| `PR_DRAFT` 変数名 | `PR_DRAFT` | Trigger Job設定画面 |
| `PR_DRAFT` Expression | `$.pull_request.draft` | Trigger Job設定画面 |
| `PR_DRAFT` Expression type | `JSONPath` | Trigger Job設定画面 |
| 下流ジョブパラメータ | `PR_DRAFT=$PR_DRAFT` が含まれる | Trigger Job設定画面 |
| Pipeline Job パラメータ定義 | `PR_DRAFT` が追加されていない | Pipeline Job設定画面 |
| Jenkinsfile | 「ドラフトPRチェック」ステージが追加されている | GitHubまたはJenkins画面 |

### 確認項目チェックリスト

- [ ] シードジョブが `SUCCESS` で完了している
- [ ] DSLファイルがエラーなく処理されている
- [ ] Trigger Job設定の「Generic Webhook Trigger」に `PR_DRAFT` 変数が表示されている
- [ ] `PR_DRAFT` の変数名が `PR_DRAFT` である
- [ ] `PR_DRAFT` のExpressionが `$.pull_request.draft` である
- [ ] `PR_DRAFT` のExpression typeが `JSONPath` である
- [ ] Trigger Job設定の「Predefined parameters」に `PR_DRAFT=$PR_DRAFT` が含まれている
- [ ] Pipeline Job設定のパラメータ定義に `PR_DRAFT` が追加されていない
- [ ] Jenkinsfileに「ドラフトPRチェック」ステージが追加されている
- [ ] ステージが最初のステージとして配置されている

### テスト完了条件

- すべての確認項目がチェック済み
- DSL変更が正しく反映されている
- ジョブ設定が期待通りである

---

## 3. テストデータ

### 3.1 GitHub Webhook Payload（ドラフトPR作成時）

```json
{
  "action": "opened",
  "number": 500,
  "pull_request": {
    "number": 500,
    "draft": true,
    "state": "open",
    "title": "Test: Draft PR for Issue #431",
    "html_url": "https://github.com/tielec/infrastructure-as-code/pull/500",
    "head": {
      "ref": "test/draft-pr-skip-431"
    },
    "base": {
      "ref": "main"
    }
  },
  "repository": {
    "name": "infrastructure-as-code",
    "full_name": "tielec/infrastructure-as-code",
    "html_url": "https://github.com/tielec/infrastructure-as-code"
  }
}
```

### 3.2 GitHub Webhook Payload（ドラフト解除時）

```json
{
  "action": "ready_for_review",
  "number": 500,
  "pull_request": {
    "number": 500,
    "draft": false,
    "state": "open",
    "title": "Test: Draft PR for Issue #431",
    "html_url": "https://github.com/tielec/infrastructure-as-code/pull/500",
    "head": {
      "ref": "test/draft-pr-skip-431"
    },
    "base": {
      "ref": "main"
    }
  },
  "repository": {
    "name": "infrastructure-as-code",
    "full_name": "tielec/infrastructure-as-code",
    "html_url": "https://github.com/tielec/infrastructure-as-code"
  }
}
```

### 3.3 GitHub Webhook Payload（非ドラフトPR作成時）

```json
{
  "action": "opened",
  "number": 501,
  "pull_request": {
    "number": 501,
    "draft": false,
    "state": "open",
    "title": "Test: Non-draft PR for Issue #431",
    "html_url": "https://github.com/tielec/infrastructure-as-code/pull/501",
    "head": {
      "ref": "test/non-draft-pr-regression-431"
    },
    "base": {
      "ref": "main"
    }
  },
  "repository": {
    "name": "infrastructure-as-code",
    "full_name": "tielec/infrastructure-as-code",
    "html_url": "https://github.com/tielec/infrastructure-as-code"
  }
}
```

### 3.4 Trigger Job → Pipeline Job のパラメータ（ドラフト）

```
REPO_URL=https://github.com/tielec/infrastructure-as-code
PR_NUMBER=500
PR_DRAFT=true
UPDATE_TITLE=true
FORCE_ANALYSIS=true
```

### 3.5 Trigger Job → Pipeline Job のパラメータ（非ドラフト）

```
REPO_URL=https://github.com/tielec/infrastructure-as-code
PR_NUMBER=501
PR_DRAFT=false
UPDATE_TITLE=true
FORCE_ANALYSIS=true
```

### 3.6 Trigger Job → Pipeline Job のパラメータ（PR_DRAFT欠落）

```
REPO_URL=https://github.com/tielec/infrastructure-as-code
PR_NUMBER=501
UPDATE_TITLE=true
FORCE_ANALYSIS=true
```
（`PR_DRAFT` が存在しない）

---

## 4. テスト環境要件

### 4.1 必要なテスト環境

#### Jenkins環境
- **環境**: dev環境（本番環境でのテストは避ける）
- **Jenkins バージョン**: 2.426.1以上
- **必要プラグイン**:
  - Generic Webhook Trigger（既存インストール済み）
  - Job DSL
  - Pipeline
  - Git

#### GitHub環境
- **リポジトリ**: `tielec/infrastructure-as-code`
- **権限**: Write権限（PRを作成・編集できる）
- **Webhook**: Pull Requestイベントが有効化されている

#### 外部サービス
- **OpenAI API**: APIキーが正しく設定されている（テストケース2, 3で使用）

### 4.2 テストに必要なアクセス権限

- Jenkins管理者権限（ジョブ設定の確認、シードジョブの実行）
- GitHubリポジトリへのWrite権限（PR作成・編集）
- GitHub Webhook設定の閲覧権限（Recent Deliveriesの確認）

### 4.3 モック/スタブの必要性

**不要**: すべて実際のシステム（GitHub、Jenkins、OpenAI API）を使用する統合テスト

---

## 5. テスト実行スケジュール

### 5.1 推奨実行順序

1. **テストケース5**: シードジョブでのDSL反映確認（最初に実行）
2. **テストケース1**: ドラフトPR作成時のスキップ確認
3. **テストケース2**: ドラフト解除時の実行確認（テストケース1のPRを使用）
4. **テストケース3**: 非ドラフトPRの回帰テスト
5. **テストケース4**: パラメータ欠落時のフェイルセーフ確認（最後に実行）

### 5.2 見積もり時間

| テストケース | 見積もり時間 | 備考 |
|-------------|------------|------|
| TC5: シードジョブでのDSL反映確認 | 0.25h | DSL変更の反映とジョブ設定確認 |
| TC1: ドラフトPRスキップ確認 | 0.5h | ドラフトPR作成とジョブ実行確認 |
| TC2: ドラフト解除時の実行確認 | 0.5h | ドラフト解除とOpenAI API呼び出し確認 |
| TC3: 非ドラフトPRの回帰テスト | 0.5h | 新規PR作成と既存動作との比較 |
| TC4: パラメータ欠落時のフェイルセーフ確認 | 0.25h | 手動トリガーとフェイルセーフ確認 |
| **合計** | **2h** | |

### 5.3 テスト実施タイミング

- **Phase 6（テスト実行フェーズ）**: 実装完了後に実施
- **前提条件**: Phase 4（実装）が完了していること

---

## 6. 品質ゲート（Phase 3）

### ✅ Phase 2の戦略に沿ったテストシナリオである

- テスト戦略「INTEGRATION_ONLY」に基づき、統合テストシナリオのみを作成
- Unitテスト、BDDテストは含まれていない（Phase 2の判断に基づく）

### ✅ 主要な正常系がカバーされている

- **テストケース2**: ドラフト解除時の実行確認（正常系の主要フロー）
- **テストケース3**: 非ドラフトPRの回帰テスト（既存の正常系）
- **テストケース5**: シードジョブでのDSL反映確認（設定反映の正常系）

### ✅ 主要な異常系がカバーされている

- **テストケース4**: パラメータ欠落時のフェイルセーフ確認（異常系）
- **テストケース1**: ドラフトPRのスキップ（特殊ケース）

### ✅ 期待結果が明確である

- 各テストケースに「期待結果」セクションを記載
- 確認項目チェックリストで検証可能な項目を列挙
- 表形式で期待値と確認方法を明記

---

## 7. テスト結果記録フォーマット

各テストケース実行後、以下の形式で結果を記録してください：

### テスト結果記録テンプレート

```markdown
## テストケースX: [テストケース名]

- **実行日時**: YYYY-MM-DD HH:MM
- **実行者**: [名前]
- **テスト環境**: [dev/staging/prod]
- **結果**: [PASS/FAIL]

### 確認項目チェックリスト結果

- [x] 項目1
- [x] 項目2
- [ ] 項目3（FAIL理由: ...）

### 実際の結果

| 項目 | 期待値 | 実際の値 | 判定 |
|------|--------|----------|------|
| ... | ... | ... | PASS/FAIL |

### スクリーンショット

- [ビルド履歴のスクリーンショット]
- [コンソールログのスクリーンショット]
- [GitHub PR画面のスクリーンショット]

### 備考

- 特記事項があれば記載
```

---

## 8. トラブルシューティング

### 8.1 GitHub Webhookが送信されない

**症状**: PRを作成してもTrigger Jobがトリガーされない

**確認方法**:
1. GitHubリポジトリの「Settings」→「Webhooks」にアクセス
2. Webhook URLが正しいか確認
3. 「Recent Deliveries」でエラーがないか確認

**対処法**:
- Webhook URLを修正
- JenkinsのGeneric Webhook Trigger設定を確認
- Jenkinsファイアウォール設定を確認

### 8.2 PR_DRAFTが取得できない

**症状**: Trigger Jobのログに `PR_DRAFT` が表示されない、または空文字列

**確認方法**:
1. Trigger Jobのコンソールログで `PR_DRAFT` の値を確認
2. GitHub Webhook PayloadのJSONを確認（`pull_request.draft` フィールドの有無）

**対処法**:
- JSONPathが正しいか確認: `$.pull_request.draft`
- GitHub Webhook Payloadに `draft` フィールドが含まれているか確認
- フィールドが欠落している場合は、テストケース4（フェイルセーフ）で期待通りの動作か確認

### 8.3 Pipeline Jobでパラメータが渡されない

**症状**: Pipeline Jobで `params.PR_DRAFT` が `null` または未定義

**確認方法**:
1. Trigger Jobのコンソールログで下流ジョブに渡したパラメータを確認
2. Pipeline Jobのコンソールログで `params.PR_DRAFT` の値を確認

**対処法**:
- Trigger JobのDSLファイルで `predefinedProps` に `PR_DRAFT` が追加されているか確認
- シードジョブを再実行してDSL変更を反映
- Trigger Jobを再実行してパラメータ伝播を確認

### 8.4 ドラフトPRでスキップされない

**症状**: ドラフトPRでも全ステージが実行されてしまう

**確認方法**:
1. Pipeline Jobのコンソールログで「ドラフトPRチェック」ステージのログを確認
2. `params.PR_DRAFT` の値を確認

**対処法**:
- Jenkinsfileの「ドラフトPRチェック」ステージが追加されているか確認
- `params.PR_DRAFT` が `'true'` として渡されているか確認（文字列型）
- ドラフト判定ロジック（`if (isDraft == 'true')`）が正しいか確認

---

## 9. 参考情報

### 9.1 関連ドキュメント

- [GitHub Webhook Payload](https://docs.github.com/en/webhooks/webhook-events-and-payloads#pull_request)
- [Generic Webhook Triggerプラグイン](https://plugins.jenkins.io/generic-webhook-trigger/)
- [Jenkins Declarative Pipeline](https://www.jenkins.io/doc/book/pipeline/syntax/)
- [jenkins/CONTRIBUTION.md](jenkins/CONTRIBUTION.md) - Jenkinsジョブ開発規約
- [CLAUDE.md](CLAUDE.md) - プロジェクト全体のガイドライン

### 9.2 Planning/Requirements/Design Documents

- [Planning Document](.ai-workflow/issue-431/00_planning/output/planning.md)
- [要件定義書](.ai-workflow/issue-431/01_requirements/output/requirements.md)
- [設計書](.ai-workflow/issue-431/02_design/output/design.md)

---

**テストシナリオ作成日**: 2025-01-XX
**作成者**: Claude Code
**レビューステータス**: 未レビュー（クリティカルシンキングレビュー待ち）
