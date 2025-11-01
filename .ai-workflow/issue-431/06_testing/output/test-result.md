# 手動インテグレーションテスト実施ガイド

**Issue番号**: #431
**タイトル**: [TASK] ドラフトPRに対するpull_request_comment_builderの実行を抑止
**作成日**: 2025-01-28
**ドキュメント種別**: 手動テスト実施ガイド（Phase 6成果物）

---

## ⚠️ 重要な注意事項

### このドキュメントの位置づけ

このドキュメントは、**Phase 6（テスト実行）の成果物として作成された手動インテグレーションテスト実施ガイド**です。

**AI Workflowの制約により、以下の理由で実際のテスト実行は含まれていません**：

1. **実環境アクセスの制約**: dev環境のJenkinsへのアクセスが必要ですが、AIには権限がありません
2. **手動操作の必要性**: Jenkins UIでの操作、GitHub PRの作成、Webhook履歴の確認など、人間による手動操作が必須です
3. **スクリーンショット取得**: テスト証跡として必要なスクリーンショットは、実環境でのみ取得可能です

### テスト実施の必要性

**Phase 4で実装した機能が正しく動作するか検証するため、このガイドに従って手動インテグレーションテストを実施する必要があります。**

テスト実施後、結果を本ファイルの末尾に追記してください（記録フォーマットは後述）。

---

## スキップ判定の背景

### Planning Documentの判断

Planning Document（`00_planning/output/planning.md`）で以下の判断が行われました：

- **Phase 5（テストコード実装）**: スキップ
  - 理由: Jenkins DSL/Groovyの自動テストは本プロジェクトで未導入
  - テストフレームワーク（JCasC、Jenkins Test Harness）の設定が必要で、コストパフォーマンスが低い

- **Phase 6（テスト実行）**: 手動インテグレーションテストを実施
  - テスト戦略: **INTEGRATION_ONLY**
  - 実際のJenkins環境でシードジョブを実行し、生成されたジョブの動作を確認

### テスト戦略の根拠

**Planning Document（Phase 2）より引用**:
> **テスト戦略: INTEGRATION_ONLY** - 手動インテグレーションテストのみ

**判断理由**:
1. Jenkins DSL/Groovyコードは、Jenkins環境への依存が強く、ユニットテストのコストが高い
2. BDDフレームワークやユニットテストフレームワークを導入するメリットが少ない（ユーザーストーリーが単純）
3. 変更が小規模（1ファイルのみ、条件追加のみ）で、影響範囲が限定的（Triggerジョブのみ）
4. 手動インテグレーションテストで十分な品質保証が可能

---

## テスト実施の目的

### 受け入れ基準の検証

以下の受け入れ基準（`01_requirements/output/requirements.md`）を検証します：

- **AC-01**: ドラフトPRでビルドが起動しない
- **AC-02**: ドラフト解除後にビルドが正常に起動する
- **AC-03**: 既存の非ドラフトPRの動作に影響がない

### 実装の動作確認

Phase 4で実装した以下の変更が正しく動作するか確認します（`04_implementation/output/implementation.md`参照）：

1. Generic Webhook Trigger変数の追加（`PR_DRAFT`）
2. Conditional BuildStepの実装（`draft=false`の場合のみ下流ジョブ起動）
3. ログ出力の調整（`causeString`にドラフト状態を含める）
4. コメント追加（ドラフトPRフィルタリング機能の説明）

### テストシナリオ

詳細なテストシナリオは、Phase 3で作成された `03_test_scenario/output/test-scenario.md` に記載されています：

- **ITS-01**: ドラフトPRでジョブが起動しない（AC-01）
- **ITS-02**: ドラフト解除後にジョブが正常に起動する（AC-02）
- **ITS-03**: 非ドラフトPRの動作に影響がない（AC-03）
- **ITS-04**: ドラフトPRへのコミット追加時の動作（edge case、オプション）
- **ITS-05**: `draft`フィールド欠損時のフォールバック（オプション）

---

## 事前準備

### 1. dev環境のJenkinsへのアクセス確認

テストを実施する前に、dev環境のJenkinsにアクセスできることを確認してください：

```bash
# dev環境のJenkins URLを確認（README.mdまたはAnsible inventory参照）
# ブラウザでJenkins UIにアクセス
# 管理者権限でログインできることを確認
```

### 2. シードジョブでDSL変更を反映

実装した変更をJenkins環境に反映します：

**手順**:
1. Jenkins UI: `Admin_Jobs/job-creator` を開く
2. 「Build Now」をクリック
3. ビルドが完了するまで待つ（通常1-3分）
4. コンソール出力で「GeneratedJob」セクションを確認
   - `docx_generator_pull_request_comment_builder_github_trigger_job`が表示されているか確認
   - エラーがないことを確認

**期待結果**:
- ビルドステータス: `SUCCESS`
- エラーなし
- ジョブ定義が更新されている

**記録事項**:
- ビルド番号: `Admin_Jobs/job-creator #____`
- 実施日時: `____-__-__ __:__`
- 実施者: `____________`

### 3. Webhook設定の確認

GitHub Webhookが正しく設定されていることを確認します：

**手順**:
1. GitHub > Settings > Webhooks を開く
2. Jenkins WebhookのURLを確認
3. `pull_request`イベントが有効であることを確認
4. Webhook配信履歴をクリア（テスト結果を明確にするため）

### 4. Jenkinsジョブ定義の確認

実装した変更がジョブ定義に反映されていることを確認します：

**手順**:
1. Jenkins UI: `Document_Generator/{repo-name}/PR_Comment_Builder_Trigger` を開く
2. 「Configure」をクリック
3. Generic Webhook Trigger設定を確認
   - `PR_DRAFT`変数が追加されていることを確認（JSONPath: `$.pull_request.draft`）
4. Build Steps設定を確認
   - `conditionalSteps`ブロックで`downstreamParameterized`がラップされていることを確認
   - 条件: `Strings match` → `$PR_DRAFT` / `false`

**期待結果**:
- `PR_DRAFT`変数が存在する
- Conditional BuildStepが正しく設定されている

---

## テストケースの実行

テストシナリオ（`03_test_scenario/output/test-scenario.md`）に従い、以下のテストケースを実施してください。

**必須テストケース**: ITS-01、ITS-02、ITS-03
**オプションテストケース**: ITS-04、ITS-05

---

### テストケース1: ITS-01（ドラフトPRでジョブが起動しない）

**シナリオID**: ITS-01
**目的**: ドラフトPRに対して下流ジョブが起動しないことを確認
**受け入れ基準**: AC-01
**優先度**: 高（クリティカルパス）

#### 手順

**ステップ1: テストブランチの作成**

```bash
git checkout main
git pull origin main
git checkout -b test/draft-pr-skip-its01
echo "Test for draft PR skip" > test-its01.txt
git add test-its01.txt
git commit -m "test(ITS-01): draft PR skip scenario"
git push origin test/draft-pr-skip-its01
```

**ステップ2: ドラフトPRの作成**

1. GitHub UIでリポジトリを開く
2. 「Pull requests」→「New pull request」をクリック
3. Base: `main`, Compare: `test/draft-pr-skip-its01` を選択
4. 「Create pull request」のドロップダウンから「**Create draft pull request**」を選択
5. PR番号をメモ（例: #432）

**ステップ3: Webhookペイロードの確認**

1. GitHub > Settings > Webhooks > 「Recent Deliveries」を開く
2. 最新の`pull_request`イベント（action: `opened`）を選択
3. Payloadタブで以下を確認：
   ```json
   {
     "action": "opened",
     "pull_request": {
       "number": 432,
       "draft": true,  // ← ドラフト状態であることを確認
       ...
     }
   }
   ```
4. Responseタブで`200 OK`が返されていることを確認

**ステップ4: Jenkinsビルド履歴の確認**

1. Jenkins UI: `Document_Generator/{repo-name}/PR_Comment_Builder_Trigger` を開く
2. ビルド履歴を確認
   - **パターンA（推奨）**: ビルド履歴に新規ビルドが**ない**
   - **パターンB（許容）**: ビルド履歴に新規ビルドがあるが、ステータスが`SUCCESS`で下流ジョブが起動していない

**ステップ5: Triggerジョブのコンソール出力確認（パターンBの場合）**

1. 最新ビルドをクリック
2. 「Console Output」を開く
3. 以下のログが出力されていることを確認：
   ```
   [Generic Webhook Trigger] Received POST for ...
   ...
   PR_DRAFT = true
   ...
   [Conditional BuildStep] Condition [Strings match] did not match, skipping all following steps
   Finished: SUCCESS
   ```

**ステップ6: 下流ジョブが起動していないことを確認**

1. Jenkins UI: `Document_Generator/{repo-name}/PR_Comment_Builder` を開く
2. ビルド履歴に新規ビルド（PR #432関連）が**ない**ことを確認

#### 確認項目チェックリスト

- [ ] GitHub Webhookが正常に配信された（`200 OK`）
- [ ] Webhookペイロードに`"draft": true`が含まれている
- [ ] Triggerジョブのコンソール出力に`PR_DRAFT = true`が表示されている
- [ ] Triggerジョブのコンソール出力に「Condition did not match, skipping」が表示されている
- [ ] 下流ジョブ（PR_Comment_Builder）が起動していない
- [ ] Triggerジョブのビルドステータスが`SUCCESS`または`NOT_BUILT`である
- [ ] GitHub PR画面にJenkinsからのコメントが投稿されていない

#### 期待結果

| 確認項目 | 期待値 |
|---------|--------|
| GitHub Webhook配信 | `200 OK` |
| Webhookペイロードの`draft`フィールド | `true` |
| Triggerジョブのビルド履歴 | 記録なし、またはSUCCESS（スキップのログ） |
| Triggerジョブのコンソール出力 | `PR_DRAFT = true`<br/>`Condition did not match, skipping` |
| 下流ジョブのビルド履歴 | PR #432関連のビルドなし |

#### スクリーンショット取得箇所

- [ ] Webhook配信履歴（GitHub）
- [ ] Triggerジョブのビルド履歴（Jenkins）
- [ ] Triggerジョブのコンソール出力（Jenkins）
- [ ] 下流ジョブのビルド履歴（Jenkins）
- [ ] GitHub PR画面（コメント未投稿確認）

---

### テストケース2: ITS-02（ドラフト解除後にジョブが正常に起動する）

**シナリオID**: ITS-02
**目的**: ドラフトPRを解除（Ready for review）した場合、下流ジョブが正常に起動することを確認
**受け入れ基準**: AC-02
**優先度**: 高（クリティカルパス）

#### 前提条件

- ITS-01が完了している（ドラフトPR #432が存在）
- ドラフトPRに対して下流ジョブが起動していないことが確認済み

#### 手順

**ステップ1: ドラフトの解除**

1. GitHub UIでドラフトPR（#432）を開く
2. 「Ready for review」ボタンをクリック
3. PRのステータスが「Open」（非ドラフト）に変更されることを確認

**ステップ2: Webhookペイロードの確認**

1. GitHub > Settings > Webhooks > 「Recent Deliveries」を開く
2. 最新の`pull_request`イベント（action: `ready_for_review`）を選択
3. Payloadタブで以下を確認：
   ```json
   {
     "action": "ready_for_review",
     "pull_request": {
       "number": 432,
       "draft": false,  // ← ドラフトが解除されたことを確認
       ...
     }
   }
   ```
4. Responseタブで`200 OK`が返されていることを確認

**ステップ3: Triggerジョブのビルド履歴確認**

1. Jenkins UI: `Document_Generator/{repo-name}/PR_Comment_Builder_Trigger` を開く
2. ビルド履歴に新規ビルドが追加されていることを確認
3. ビルドステータスが`SUCCESS`であることを確認

**ステップ4: Triggerジョブのコンソール出力確認**

1. 最新ビルドをクリック
2. 「Console Output」を開く
3. 以下のログが出力されていることを確認：
   ```
   [Generic Webhook Trigger] Received POST for ...
   ...
   PR_DRAFT = false
   ...
   [Conditional BuildStep] Condition [Strings match] matched, continuing
   Building project Document_Generator/{repo-name}/PR_Comment_Builder
   Finished: SUCCESS
   ```

**ステップ5: 下流ジョブが起動したことを確認**

1. Jenkins UI: `Document_Generator/{repo-name}/PR_Comment_Builder` を開く
2. ビルド履歴に新規ビルド（PR #432関連）が追加されていることを確認
3. ビルドステータスを確認（`SUCCESS`または処理中）

**ステップ6: 下流ジョブのコンソール出力確認**

1. 下流ジョブの最新ビルドをクリック
2. 「Console Output」を開く
3. 以下が正常に実行されていることを確認：
   - PRコメント生成処理が実行されている
   - OpenAI API呼び出しが成功している
   - GitHubへのコメント投稿が成功している

**ステップ7: GitHub PR画面でコメント確認**

1. GitHub UIでPR #432を開く
2. Jenkinsからのコメントが投稿されていることを確認
3. コメント内容が期待通りであることを確認

#### 確認項目チェックリスト

- [ ] GitHub Webhookが正常に配信された（`200 OK`、action: `ready_for_review`）
- [ ] Webhookペイロードに`"draft": false`が含まれている
- [ ] Triggerジョブのコンソール出力に`PR_DRAFT = false`が表示されている
- [ ] Triggerジョブのコンソール出力に「Condition matched, continuing」が表示されている
- [ ] 下流ジョブ（PR_Comment_Builder）が起動している
- [ ] 下流ジョブでOpenAI API呼び出しが成功している
- [ ] GitHub PR画面にJenkinsからのコメントが投稿されている
- [ ] コメント内容が既存動作と同じ形式である

#### 期待結果

| 確認項目 | 期待値 |
|---------|--------|
| GitHub Webhook配信 | `200 OK`（action: `ready_for_review`） |
| Webhookペイロードの`draft`フィールド | `false` |
| Triggerジョブのビルド履歴 | 新規ビルドあり（SUCCESS） |
| Triggerジョブのコンソール出力 | `PR_DRAFT = false`<br/>`Condition matched, continuing` |
| 下流ジョブの起動 | PR #432関連のビルドあり |
| 下流ジョブの処理 | OpenAI API呼び出し成功、PRコメント投稿成功 |
| GitHub PRコメント | Jenkinsからのコメントが投稿されている |

#### スクリーンショット取得箇所

- [ ] Webhook配信履歴（GitHub、action: `ready_for_review`）
- [ ] Triggerジョブのビルド履歴（Jenkins）
- [ ] Triggerジョブのコンソール出力（Jenkins）
- [ ] 下流ジョブのビルド履歴（Jenkins）
- [ ] 下流ジョブのコンソール出力（Jenkins）
- [ ] GitHub PR画面（コメント投稿確認）

---

### テストケース3: ITS-03（非ドラフトPRの動作に影響がない）

**シナリオID**: ITS-03
**目的**: 既存の非ドラフトPR（通常のPR）に対する動作が、今回の変更で影響を受けていないことを検証（回帰テスト）
**受け入れ基準**: AC-03
**優先度**: 高（回帰テスト）

#### 手順

**ステップ1: テストブランチの作成**

```bash
git checkout main
git pull origin main
git checkout -b test/normal-pr-its03
echo "Test for normal PR regression" > test-its03.txt
git add test-its03.txt
git commit -m "test(ITS-03): normal PR regression scenario"
git push origin test/normal-pr-its03
```

**ステップ2: 通常PRの作成（非ドラフト）**

1. GitHub UIでリポジトリを開く
2. 「Pull requests」→「New pull request」をクリック
3. Base: `main`, Compare: `test/normal-pr-its03` を選択
4. 「**Create pull request**」をクリック（ドラフトにしない）
5. PR番号をメモ（例: #433）

**ステップ3: Webhookペイロードの確認**

1. GitHub > Settings > Webhooks > 「Recent Deliveries」を開く
2. 最新の`pull_request`イベント（action: `opened`）を選択
3. Payloadタブで以下を確認：
   ```json
   {
     "action": "opened",
     "pull_request": {
       "number": 433,
       "draft": false,  // ← 非ドラフトであることを確認
       ...
     }
   }
   ```
4. Responseタブで`200 OK`が返されていることを確認

**ステップ4: Triggerジョブのビルド履歴確認**

1. Jenkins UI: `Document_Generator/{repo-name}/PR_Comment_Builder_Trigger` を開く
2. ビルド履歴に新規ビルドが追加されていることを確認
3. ビルドステータスが`SUCCESS`であることを確認

**ステップ5: Triggerジョブのコンソール出力確認**

1. 最新ビルドをクリック
2. 「Console Output」を開く
3. 以下のログが出力されていることを確認：
   ```
   [Generic Webhook Trigger] Received POST for ...
   ...
   PR_DRAFT = false
   ...
   [Conditional BuildStep] Condition [Strings match] matched, continuing
   Building project Document_Generator/{repo-name}/PR_Comment_Builder
   Finished: SUCCESS
   ```

**ステップ6: 下流ジョブが起動したことを確認**

1. Jenkins UI: `Document_Generator/{repo-name}/PR_Comment_Builder` を開く
2. ビルド履歴に新規ビルド（PR #433関連）が追加されていることを確認
3. ビルドステータスを確認（`SUCCESS`または処理中）

**ステップ7: 下流ジョブのコンソール出力確認**

1. 下流ジョブの最新ビルドをクリック
2. 「Console Output」を開く
3. 以下が正常に実行されていることを確認：
   - PRコメント生成処理が実行されている
   - OpenAI API呼び出しが成功している
   - GitHubへのコメント投稿が成功している

**ステップ8: GitHub PR画面でコメント確認**

1. GitHub UIでPR #433を開く
2. Jenkinsからのコメントが投稿されていることを確認
3. コメント内容が既存の非ドラフトPRと同じ形式であることを確認

**ステップ9: 既存動作との比較（オプション）**

1. 以前の非ドラフトPRのビルドログを参照
2. 今回のビルドログと比較し、以下が同一であることを確認：
   - ビルドステップの順序
   - パラメータの受け渡し方法
   - 実行時間（大きな差異がない）

#### 確認項目チェックリスト

- [ ] GitHub Webhookが正常に配信された（`200 OK`、action: `opened`）
- [ ] Webhookペイロードに`"draft": false`が含まれている
- [ ] Triggerジョブのコンソール出力に`PR_DRAFT = false`が表示されている
- [ ] Triggerジョブのコンソール出力に「Condition matched, continuing」が表示されている
- [ ] 下流ジョブ（PR_Comment_Builder）が起動している
- [ ] 下流ジョブでOpenAI API呼び出しが成功している
- [ ] GitHub PR画面にJenkinsからのコメントが投稿されている
- [ ] コメント内容が既存の非ドラフトPRと同じ形式である
- [ ] ビルドステップの順序が既存と同一である
- [ ] 実行時間に大きな差異がない（±10%以内）

#### 期待結果

| 確認項目 | 期待値 |
|---------|--------|
| GitHub Webhook配信 | `200 OK` |
| Webhookペイロードの`draft`フィールド | `false` |
| Triggerジョブのビルド履歴 | 新規ビルドあり（SUCCESS） |
| Triggerジョブのコンソール出力 | `PR_DRAFT = false`<br/>`Condition matched, continuing` |
| 下流ジョブの起動 | PR #433関連のビルドあり |
| 下流ジョブの処理 | OpenAI API呼び出し成功、PRコメント投稿成功 |
| GitHub PRコメント | Jenkinsからのコメントが投稿されている |
| 既存動作との一貫性 | ビルドステップ、実行時間が既存と同等 |

#### スクリーンショット取得箇所

- [ ] Webhook配信履歴（GitHub）
- [ ] Triggerジョブのビルド履歴（Jenkins）
- [ ] Triggerジョブのコンソール出力（Jenkins）
- [ ] 下流ジョブのビルド履歴（Jenkins）
- [ ] 下流ジョブのコンソール出力（Jenkins）
- [ ] GitHub PR画面（コメント投稿確認）

---

### テストケース4: ITS-04（ドラフトPRへのコミット追加時の動作）

**シナリオID**: ITS-04
**目的**: ドラフトPRに対して追加コミットをプッシュした場合も、下流ジョブが起動しないことを確認（edge case）
**受け入れ基準**: AC-01（拡張）
**優先度**: 中（余裕があれば実施）

#### 前提条件

- ITS-01が完了している（ドラフトPR #432が存在）
- ドラフトPRがまだドラフト状態である

#### 手順

**ステップ1: 追加コミットのプッシュ**

```bash
git checkout test/draft-pr-skip-its01
echo "Additional change in draft PR" >> test-its01.txt
git add test-its01.txt
git commit -m "test(ITS-04): additional commit to draft PR"
git push origin test/draft-pr-skip-its01
```

**ステップ2: Webhookペイロードの確認**

1. GitHub > Settings > Webhooks > 「Recent Deliveries」を開く
2. 最新の`pull_request`イベント（action: `synchronize`）を選択
3. Payloadタブで以下を確認：
   ```json
   {
     "action": "synchronize",
     "pull_request": {
       "number": 432,
       "draft": true,  // ← まだドラフト状態であることを確認
       ...
     }
   }
   ```

**ステップ3: Jenkinsビルド履歴の確認**

1. Jenkins UI: `Document_Generator/{repo-name}/PR_Comment_Builder_Trigger` を開く
2. ビルド履歴を確認
   - ビルド履歴に新規ビルドが**ない**、またはSUCCESS（スキップのログ）

**ステップ4: 下流ジョブが起動していないことを確認**

1. Jenkins UI: `Document_Generator/{repo-name}/PR_Comment_Builder` を開く
2. ビルド履歴に新規ビルド（PR #432関連、追加コミット分）が**ない**ことを確認

#### 確認項目チェックリスト

- [ ] Webhookが配信された（action: `synchronize`）
- [ ] Webhookペイロードに`"draft": true`が含まれている
- [ ] 下流ジョブ（PR_Comment_Builder）が起動していない

#### 期待結果

| 確認項目 | 期待値 |
|---------|--------|
| GitHub Webhook配信 | `200 OK`（action: `synchronize`） |
| Webhookペイロードの`draft`フィールド | `true` |
| Triggerジョブのビルド履歴 | 記録なし、またはSUCCESS（スキップのログ） |
| 下流ジョブの起動 | 新規ビルドなし |

---

### テストケース5: ITS-05（`draft`フィールド欠損時のフォールバック動作）

**シナリオID**: ITS-05
**目的**: GitHub Webhookペイロードに`pull_request.draft`フィールドが存在しない場合のフォールバック動作を検証（edge case、セキュリティ考慮）
**受け入れ基準**: NFR-03（エラーハンドリング）
**優先度**: 低（発生確率が極低、時間に余裕があれば実施）

#### 前提条件

- シードジョブでDSL変更が反映されている
- Webhook手動トリガー機能が使用可能

#### 手順

**ステップ1: 手動Webhookペイロードの作成**

以下の簡易ペイロード（`draft`フィールドを含まない）を準備：

```json
{
  "action": "opened",
  "pull_request": {
    "number": 999,
    "title": "Test PR without draft field"
  },
  "repository": {
    "html_url": "https://github.com/tielec/infrastructure-as-code"
  }
}
```

**ステップ2: Webhook手動送信**

以下のコマンドでWebhookを手動送信（またはPostman等を使用）：

```bash
curl -X POST "https://{jenkins-url}/generic-webhook-trigger/invoke?token={token}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "opened",
    "pull_request": {
      "number": 999,
      "title": "Test PR without draft field"
    },
    "repository": {
      "html_url": "https://github.com/tielec/infrastructure-as-code"
    }
  }'
```

**ステップ3: Triggerジョブのコンソール出力確認**

1. Triggerジョブの最新ビルドを開く
2. 「Console Output」を確認：
   ```
   PR_DRAFT =   // ← 空文字列または未定義
   ...
   [Conditional BuildStep] Condition [Strings match] did not match, skipping
   ```

**ステップ4: フォールバック動作の確認**

1. 下流ジョブが起動していないことを確認（安全側に倒す）

#### 確認項目チェックリスト

- [ ] Webhookを受信してもエラーが発生していない
- [ ] `PR_DRAFT`変数が空文字列または未定義である
- [ ] Conditional BuildStepが「条件不一致」と判定している
- [ ] 下流ジョブが起動していない（安全側に倒している）

#### 期待結果

| 確認項目 | 期待値 |
|---------|--------|
| Triggerジョブの実行 | エラーにならずに完了 |
| `PR_DRAFT`変数 | 空文字列または未定義 |
| Conditional BuildStepの判定 | 条件不一致（スキップ） |
| 下流ジョブの起動 | 起動しない（安全側に倒す） |

---

## テスト結果の記録フォーマット

### 各テストケースの結果記録

各テストケース実施後、以下の情報を記録してください：

```markdown
### ITS-XX: （テストケース名）

**実施日時**: YYYY-MM-DD HH:MM
**実施者**: （名前）
**PR番号**: #XXX
**結果**: ✅ Pass / ❌ Fail

#### 確認項目チェックリスト結果

（上記のチェックリストをコピーし、結果を記入）

#### スクリーンショット

- Webhook配信履歴: （スクリーンショット添付またはリンク）
- Triggerジョブのビルド履歴: （スクリーンショット添付またはリンク）
- Triggerジョブのコンソール出力: （スクリーンショット添付またはリンク）
- 下流ジョブのビルド履歴: （スクリーンショット添付またはリンク）
- （該当する場合）下流ジョブのコンソール出力: （スクリーンショット添付またはリンク）
- （該当する場合）GitHub PR画面: （スクリーンショット添付またはリンク）

#### 備考

（特記事項があれば記載）
```

### テスト結果サマリー

すべてのテストケース実施後、以下のサマリーを作成してください：

```markdown
---

## テスト実施結果

### インテグレーションテスト結果サマリー

**実施日**: YYYY-MM-DD
**実施者**: （名前）
**Jenkins環境**: dev
**テストリポジトリ**: infrastructure-as-code
**DSL反映ビルド**: Admin_Jobs/job-creator #XXX

### テスト結果

| シナリオID | テストケース | 結果 | 備考 |
|-----------|------------|------|------|
| ITS-01 | ドラフトPRでジョブが起動しない | ✅ Pass / ❌ Fail | |
| ITS-02 | ドラフト解除後にジョブが正常に起動する | ✅ Pass / ❌ Fail | |
| ITS-03 | 非ドラフトPRの動作に影響がない | ✅ Pass / ❌ Fail | |
| ITS-04 | ドラフトPRへのコミット追加時の動作 | ✅ Pass / ❌ Fail / ⏭️ Skip | （オプション） |
| ITS-05 | `draft`フィールド欠損時のフォールバック | ✅ Pass / ❌ Fail / ⏭️ Skip | （オプション） |

### 受け入れ基準の検証結果

| 受け入れ基準 | 対応テストケース | 結果 |
|------------|---------------|------|
| AC-01: ドラフトPRでビルドが起動しない | ITS-01, ITS-04 | ✅ Pass / ❌ Fail |
| AC-02: ドラフト解除後にビルドが正常に起動する | ITS-02 | ✅ Pass / ❌ Fail |
| AC-03: 既存の非ドラフトPRの動作に影響がない | ITS-03 | ✅ Pass / ❌ Fail |

### 総合判定

**✅ 合格 / ❌ 不合格**

### 不具合・懸念事項

（不具合や懸念事項があれば記載）
```

---

## テスト実施後のクリーンアップ

テスト完了後、テスト用PRとブランチをクリーンアップしてください：

```bash
# PR #XXX（ドラフトPR）をクローズ
gh pr close XXX --comment "テスト完了。このPRはクローズします。"

# PR #YYY（非ドラフトPR）をクローズ
gh pr close YYY --comment "テスト完了。このPRはクローズします。"

# テスト用ブランチを削除
git branch -D test/draft-pr-skip-its01
git push origin --delete test/draft-pr-skip-its01

git branch -D test/normal-pr-its03
git push origin --delete test/normal-pr-its03
```

---

## トラブルシューティング

テスト実施時に問題が発生した場合、以下を参照してください：

### ITS-01でTriggerジョブが起動してしまう場合

**対処法**:
- シードジョブ（`Admin_Jobs/job-creator`）を再実行
- Triggerジョブの「Configure」画面で`PR_DRAFT`変数が存在することを確認
- Conditional BuildStepの条件が`stringsMatch('$PR_DRAFT', 'false', false)`であることを確認

### ITS-02で下流ジョブが起動しない場合

**対処法**:
- GitHub > Webhooks > Recent Deliveries で配信状態を確認
- Triggerジョブのコンソール出力で`PR_DRAFT`の値を確認
- Webhookペイロードに`"draft": false`が含まれているか確認

### ITS-03で既存動作と異なる結果が出る場合

**対処法**:
- DSLファイルで`downstreamParameterized`のパラメータが既存と同一であることを確認
- Gitで変更差分を確認：
  ```bash
  git diff HEAD~1 -- jenkins/jobs/dsl/docs-generator/docx_generator_pull_request_comment_builder_github_trigger_job.groovy
  ```

---

## 次フェーズへの推奨

### テスト成功時

すべての必須テストケース（ITS-01〜ITS-03）が成功した場合：
- **Phase 7（Documentation）へ進んでください**

テスト結果サマリーを本ファイルの末尾に追記し、Phase 7で以下のドキュメント更新を実施：
- `jenkins/CONTRIBUTION.md`: ドラフトPRフィルタリングパターンの追加
- DSLファイル内コメント（既にPhase 4で実装済み）

### テスト失敗時

テストケースが失敗した場合：
- **Phase 4（Implementation）に戻って修正が必要です**

失敗したテストケースの原因分析を実施し、以下を明記：
- エラー内容
- 原因分析
- 対処方針

修正後、Phase 6（手動インテグレーションテスト）を再実施してください。

---

## 参考資料

### Planning Documentの関連セクション

- **Phase 5（テストコード実装）**: "スキップ - Jenkins DSL/Groovyの自動テストは未導入"
- **Phase 6（テスト実行）**: "手動インテグレーションテスト - 0.5h"
- **テスト戦略判断**: "INTEGRATION_ONLY - インテグレーションテストが最適"

### テストシナリオ

詳細なテストシナリオは `03_test_scenario/output/test-scenario.md` を参照：
- **セクション0（Planning Documentの確認）**: "テスト戦略: INTEGRATION_ONLY"
- **セクション2（Integrationテストシナリオ）**: ITS-01〜ITS-05の詳細手順
- **セクション3（テストデータ）**: Webhookペイロードパターン
- **セクション5（テスト結果記録フォーマット）**: 記録方法
- **セクション8（トラブルシューティング）**: よくある問題の対処法

### 実装ログ

Phase 4の実装内容は `04_implementation/output/implementation.md` を参照：
- Generic Webhook Trigger変数の追加
- Conditional BuildStepの実装
- ログ出力の調整
- コメント追加

---

## Phase 6の成果物説明（AI Workflowにおける制約の明記）

### このドキュメントの位置づけ（再掲）

**AI Workflowの設計上の課題**:

本プロジェクトでは、Planning Documentで「Phase 5（テストコード実装）をスキップし、Phase 6で手動インテグレーションテストを実施する」と判断されました。しかし、**AIには実環境（dev環境のJenkins）へのアクセス権限がないため、手動テストを実際に実行することができません。**

そのため、Phase 6の成果物は以下のように定義されます：

- **Phase 6の成果物**: 手動インテグレーションテスト実施ガイド（このドキュメント）
- **Phase 6の範囲外**: 実際のテスト実行と結果記録（人間による手動作業が必要）

### Planning Documentとの整合性

Planning DocumentのPhase 6タスクチェックリスト：

- [ ] Task 6-1: シードジョブでのDSL適用 (0.1h)
  - **AI成果物**: 実施手順の記載（事前準備セクション）
  - **人間作業**: 実際のシードジョブ実行と結果記録

- [ ] Task 6-2: ドラフトPRでのテスト (0.2h)
  - **AI成果物**: テスト手順とチェックリストの作成（テストケース1）
  - **人間作業**: 実際のPR作成、Webhook確認、結果記録

- [ ] Task 6-3: ドラフト解除後のテスト (0.2h)
  - **AI成果物**: テスト手順とチェックリストの作成（テストケース2）
  - **人間作業**: 実際のドラフト解除、Jenkins確認、結果記録

### テスト実施の責任分担

| 項目 | AI（Phase 6成果物） | 人間（手動作業） |
|-----|-------------------|---------------|
| テスト計画 | ✅ 完了 | - |
| テストシナリオ詳細化 | ✅ 完了 | - |
| テスト手順書作成 | ✅ 完了 | - |
| 確認項目チェックリスト作成 | ✅ 完了 | - |
| テスト結果記録フォーマット定義 | ✅ 完了 | - |
| トラブルシューティングガイド | ✅ 完了 | - |
| **実際のテスト実行** | ❌ 不可能 | ⚠️ 必要 |
| **テスト結果の記録** | ❌ 不可能 | ⚠️ 必要 |
| **スクリーンショット取得** | ❌ 不可能 | ⚠️ 必要 |

### 品質ゲート確認（Phase 6）

Planning DocumentのPhase 6品質ゲート：

- ✅ **テスト手順が明確である**: このガイドで手順を詳細に記載
- ⚠️ **テストが実行されている**: 人間による実施が必要
- ⚠️ **主要なテストケースが成功している**: テスト実施後に判定
- ⚠️ **失敗したテストは分析されている**: テスト実施後に判定

**Phase 6（AI成果物）の品質ゲート判定**: ✅ PASS（テスト実施ガイドとして）
**Phase 6（Planning Document定義）の品質ゲート判定**: ⚠️ PENDING（テスト実施待ち）

---

## 次ステップ（重要）

### テスト実施者へのお願い

1. **このガイドに従って手動インテグレーションテストを実施してください**
   - 最低限ITS-01〜ITS-03は必須
   - ITS-04、ITS-05は余裕があれば実施

2. **テスト結果を本ファイルの末尾に追記してください**
   - 「テスト結果の記録フォーマット」セクションのテンプレートを使用
   - 各テストケースの確認項目チェックリストを埋める
   - スクリーンショットを添付

3. **テスト実施後、AI Workflowに復帰してください**
   - テスト結果が記録されたことを確認
   - Phase 7（Documentation）に進む

### テスト未実施の場合の影響

テストを実施せずにPhase 7に進んだ場合：

- ❌ 受け入れ基準（AC-01〜AC-03）が検証されていない
- ❌ Phase 4で実装した機能が正しく動作するか不明
- ❌ 本番環境へのデプロイ前にバグが発見されるリスクが高い
- ❌ プロジェクトの品質保証プロセスが不完全

**重要**: テストの実施は、品質保証の観点から**必須**です。

---

**Phase 6完了ステータス（AI成果物）**: ✅ 完了（手動テスト実施ガイド作成完了）
**Phase 6完了ステータス（Planning Document定義）**: ⚠️ 実施待ち（手動テスト未実施）

**作成日**: 2025-01-28
**作成者**: Claude (AI Assistant)
**ドキュメント種別**: 手動インテグレーションテスト実施ガイド

---

## テスト実施結果（このセクションに結果を追記してください）

**⚠️ テスト実施者へ**: このセクションに、上記のフォーマットに従ってテスト結果を記録してください。

（テスト実施後、ここに結果を追記）
