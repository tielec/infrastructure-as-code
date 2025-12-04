# テストシナリオ - Issue #455

## Issue情報

- **Issue番号**: #455
- **タイトル**: [jenkins] AI WorkflowジョブにAPIキーパラメータを追加
- **状態**: open
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/455
- **作成日**: 2025-01-20

---

## 0. Planning Document・要件定義書・設計書の確認

### Planning Phaseで策定されたテスト戦略

Planning Document（`.ai-workflow/issue-455/00_planning/output/planning.md`）を確認し、以下のテスト戦略を把握しました：

- **テスト戦略**: INTEGRATION_ONLY（シードジョブ実行による動作確認）
- **テストコード戦略**: CREATE_TEST（手動検証手順書を作成）
- **判断根拠**:
  - Job DSLは宣言的な設定ファイルであり、ロジックが存在しない
  - シードジョブ実行によるジョブ生成とパラメータ表示の確認が必要
  - エンドユーザー向けの振る舞いではなく、開発者向けの設定変更

### 要件定義書の受け入れ基準

Requirements Document（`.ai-workflow/issue-455/01_requirements/output/requirements.md`）で定義された受け入れ基準（AC-1〜AC-8）を確認しました：

- **AC-1**: パラメータがDSLファイルに追加されている
- **AC-2**: パラメータがJenkins UIで表示される
- **AC-3**: パラメータ値がマスク表示される
- **AC-4**: パラメータが環境変数として利用可能
- **AC-5**: 5つのジョブすべてで一貫性がある
- **AC-6**: 既存のパラメータに影響がない
- **AC-7**: シードジョブが正常に実行される
- **AC-8**: 空パラメータでもジョブが実行可能

### 設計書のテストケース

Design Document（`.ai-workflow/issue-455/02_design/output/design.md`）で定義されたテストケース（TC-1〜TC-5）を確認しました：

- **TC-1**: シードジョブ実行
- **TC-2**: パラメータ表示確認
- **TC-3**: パスワードマスク確認
- **TC-4**: 環境変数として利用可能
- **TC-5**: 空パラメータでの実行

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略

**INTEGRATION_ONLY: Integrationテストのみ**

### 1.2 テスト対象の範囲

| テスト対象 | 範囲 |
|-----------|------|
| **DSLファイル** | 5つのAI Workflow DSLファイル |
| **シードジョブ** | `Admin_Jobs/job-creator` |
| **生成されるジョブ** | AI_Workflow配下の5つのジョブ |
| **統合ポイント** | DSLファイル → シードジョブ → Jenkinsジョブ生成 |

### 1.3 テストの目的

1. **DSLファイルの構文正当性**: 追加したパラメータ定義がGroovy DSL構文として正しいこと
2. **シードジョブの実行成功**: DSLファイルの変更がシードジョブでエラーなく処理されること
3. **ジョブ生成の正当性**: 生成されたJenkinsジョブに6つのAPIキーパラメータが正しく追加されること
4. **セキュリティ要件**: パスワードパラメータがJenkins UIとビルドログでマスク表示されること
5. **後方互換性**: 既存のパラメータやワークフローに影響がないこと

### 1.4 テスト種別の選択理由

**Unitテスト不要の理由**:
- Job DSLは宣言的な設定ファイルであり、テスト可能なロジックが存在しない
- パラメータ定義は単純なデータ構造であり、単体でテストする意味がない

**BDDテスト不要の理由**:
- エンドユーザー向けの機能ではなく、開発者向けの内部設定変更
- ユーザーストーリーベースのシナリオが適さない

**Integrationテスト必須の理由**:
- シードジョブによるDSL解析とジョブ生成の統合プロセスを検証する必要がある
- Jenkins環境での実際の動作確認が必須
- DSL構文の正当性は実行時にのみ検証可能

---

## 2. Integrationテストシナリオ

### 2.1 統合テストの全体構成

```mermaid
graph TB
    TS1[TS-1: DSL構文検証統合テスト] --> TS2[TS-2: シードジョブ実行統合テスト]
    TS2 --> TS3[TS-3: パラメータ表示統合テスト]
    TS3 --> TS4[TS-4: セキュリティ統合テスト]
    TS4 --> TS5[TS-5: 後方互換性統合テスト]
    TS5 --> TS6[TS-6: 環境変数統合テスト]
```

---

### TS-1: DSL構文検証統合テスト

#### 目的
追加したパラメータ定義がGroovy DSL構文として正しく、シードジョブで解析可能であることを検証する。

#### 前提条件
- 5つのDSLファイルにAPIキーパラメータが追加されている
- Git管理下で変更がコミット済み
- Jenkins環境にアクセス可能

#### テスト手順

**Step 1: DSLファイルの構文確認**
```bash
# 各DSLファイルの構文を目視確認
cd /tmp/ai-workflow-repos-12/infrastructure-as-code

# 1. ai_workflow_all_phases_job.groovy
grep -A 32 "// APIキー設定" jenkins/jobs/dsl/ai-workflow/ai_workflow_all_phases_job.groovy

# 2. ai_workflow_preset_job.groovy
grep -A 32 "// APIキー設定" jenkins/jobs/dsl/ai-workflow/ai_workflow_preset_job.groovy

# 3. ai_workflow_single_phase_job.groovy
grep -A 32 "// APIキー設定" jenkins/jobs/dsl/ai-workflow/ai_workflow_single_phase_job.groovy

# 4. ai_workflow_rollback_job.groovy
grep -A 32 "// APIキー設定" jenkins/jobs/dsl/ai-workflow/ai_workflow_rollback_job.groovy

# 5. ai_workflow_auto_issue_job.groovy
grep -A 32 "// APIキー設定" jenkins/jobs/dsl/ai-workflow/ai_workflow_auto_issue_job.groovy
```

**Step 2: パラメータ配置位置の確認**
```bash
# AWS認証情報セクションと「その他」セクションの間に配置されていることを確認
grep -B 5 -A 35 "// APIキー設定" jenkins/jobs/dsl/ai-workflow/ai_workflow_all_phases_job.groovy | grep -E "(AWS|その他|APIキー)"
```

**Step 3: パラメータ数の確認**
```bash
# ヘッダーコメントでパラメータ数が更新されていることを確認
head -10 jenkins/jobs/dsl/ai-workflow/ai_workflow_all_phases_job.groovy | grep "パラメータ数"
# 期待値: パラメータ数: 20個（14個 + APIキー6個）
```

#### 期待結果

**確認項目チェックリスト**:

- [ ] **コメントセクション**: `// ========================================` 形式で「APIキー設定」セクションが存在する
- [ ] **パラメータ定義**: 6つのパラメータ（GITHUB_TOKEN, OPENAI_API_KEY, CODEX_API_KEY, CLAUDE_CODE_OAUTH_TOKEN, CLAUDE_CODE_API_KEY, ANTHROPIC_API_KEY）が定義されている
- [ ] **パラメータタイプ**: すべて`password()`メソッドで定義されている
- [ ] **説明文**: 日本語で記載され、`.stripIndent().trim()`で整形されている
- [ ] **配置位置**: AWS認証情報セクションの後、「その他」セクションの前に配置されている
- [ ] **一貫性**: 5つのDSLファイルすべてで同じパターンが適用されている
- [ ] **ヘッダーコメント**: パラメータ数が14個→20個に更新されている（all_phases, rollback, auto_issue）
- [ ] **インデント**: 既存のパラメータと同じインデント（12スペース）が適用されている

#### テストデータ
- 対象ファイル: 5つのDSLファイル（Planning Documentで定義）
- パラメータ名リスト: Issue #455に記載された6つのパラメータ名

#### 合格基準
- すべての確認項目チェックリストが✅である

---

### TS-2: シードジョブ実行統合テスト

#### 目的
DSLファイルの変更がシードジョブでエラーなく処理され、Jenkinsジョブが正常に生成/更新されることを検証する。

#### 前提条件
- TS-1が合格している
- Jenkinsにログイン済み
- `Admin_Jobs/job-creator`の実行権限がある

#### テスト手順

**Step 1: シードジョブ実行前の状態確認**
```bash
# Jenkins UI操作:
# 1. AI_Workflow/infrastructure-as-code/01_All_Phasesジョブを開く
# 2. 「設定」を開き、現在のパラメータ数を確認
# 3. スクリーンショット取得（実行前の状態）
```

**Step 2: シードジョブの実行**
```bash
# Jenkins UI操作:
# 1. Admin_Jobs/job-creator を開く
# 2. 「ビルド実行」をクリック
# 3. ビルド番号が付与されることを確認（例: #42）
```

**Step 3: コンソール出力の監視**
```bash
# Jenkins UI操作:
# 1. ビルド番号（例: #42）をクリック
# 2. 「Console Output」を開く
# 3. リアルタイムでログを監視
```

**Step 4: 実行結果の確認**
```bash
# コンソール出力で以下を確認:
# - Processing DSL script ai_workflow_all_phases_job.groovy
# - Processing DSL script ai_workflow_preset_job.groovy
# - Processing DSL script ai_workflow_single_phase_job.groovy
# - Processing DSL script ai_workflow_rollback_job.groovy
# - Processing DSL script ai_workflow_auto_issue_job.groovy
# - Updated items:
#     AI_Workflow/infrastructure-as-code/01_All_Phases
#     AI_Workflow/infrastructure-as-code/02_Preset
#     AI_Workflow/infrastructure-as-code/03_Single_Phase
#     AI_Workflow/infrastructure-as-code/04_Rollback
#     AI_Workflow/infrastructure-as-code/05_Auto_Issue
# - BUILD SUCCESS
```

#### 期待結果

**確認項目チェックリスト**:

- [ ] **ビルドステータス**: SUCCESS（緑色のチェックマーク）
- [ ] **処理されたDSLファイル数**: 5つのDSLファイルすべてが処理されている
- [ ] **更新されたジョブ数**: 5つのジョブすべてが「Updated items」にリストアップされている
- [ ] **エラーメッセージ**: コンソール出力にエラーメッセージが含まれていない
- [ ] **警告メッセージ**: 重大な警告メッセージが含まれていない
- [ ] **実行時間**: 既存の実行時間から10%以上増加していない（NFR-1）
- [ ] **ジョブの有効状態**: 生成されたジョブがdisabledになっていない

#### テストデータ
- シードジョブ: `Admin_Jobs/job-creator`
- 対象DSLファイル: 5つのAI Workflow DSLファイル

#### 合格基準
- ビルドステータスがSUCCESS
- すべての確認項目チェックリストが✅である
- コンソール出力にエラーが0件

#### 異常系シナリオ

**異常系-1: DSL構文エラーがある場合**

- **前提条件**: パラメータ定義に構文エラー（例: `password('GITHUB_TOKEN',`の閉じ括弧忘れ）
- **期待結果**:
  - ビルドステータスがFAILURE
  - コンソール出力に構文エラーメッセージが表示される
  - エラー行番号が示される
- **復旧手順**: Git revertで変更を戻し、シードジョブを再実行

---

### TS-3: パラメータ表示統合テスト

#### 目的
生成されたJenkinsジョブのパラメータ画面で、6つのAPIキーパラメータが正しく表示されることを検証する。

#### 前提条件
- TS-2が合格している（シードジョブが正常に完了）
- 5つのジョブが生成/更新されている

#### テスト手順

**Step 1: All Phasesジョブのパラメータ確認**
```bash
# Jenkins UI操作:
# 1. AI_Workflow/infrastructure-as-code/01_All_Phases を開く
# 2. 「Build with Parameters」をクリック
# 3. パラメータ一覧を確認
```

**Step 2: パラメータセクションの確認**
```
# パラメータ画面で以下のセクション順序を確認:

1. 基本設定
   - ISSUE_URL
   - BRANCH_NAME
   - AGENT_MODE

2. 実行オプション
   - DRY_RUN
   - SKIP_REVIEW
   - FORCE_RESET
   - MAX_RETRIES
   - CLEANUP_ON_COMPLETE_FORCE

3. Git 設定
   - GIT_COMMIT_USER_NAME
   - GIT_COMMIT_USER_EMAIL

4. AWS 認証情報（Infrastructure as Code 用）
   - AWS_ACCESS_KEY_ID
   - AWS_SECRET_ACCESS_KEY
   - AWS_SESSION_TOKEN

5. 【新規】APIキー設定 ← ここを重点確認
   - GITHUB_TOKEN
   - OPENAI_API_KEY
   - CODEX_API_KEY
   - CLAUDE_CODE_OAUTH_TOKEN
   - CLAUDE_CODE_API_KEY
   - ANTHROPIC_API_KEY

6. その他
   - COST_LIMIT_USD
   - LOG_LEVEL
```

**Step 3: 各パラメータの詳細確認**
```
# 各APIキーパラメータについて以下を確認:

GITHUB_TOKEN:
- 入力タイプ: パスワード（●●●●●表示）
- 説明文1行目: "GitHub Personal Access Token（任意）"
- 説明文2行目: "GitHub API呼び出しに使用されます"
- デフォルト値: 空欄

OPENAI_API_KEY:
- 入力タイプ: パスワード
- 説明文1行目: "OpenAI API キー（任意）"
- 説明文2行目: "Codex実行モードで使用されます"
- デフォルト値: 空欄

CODEX_API_KEY:
- 入力タイプ: パスワード
- 説明文1行目: "Codex API キー（任意）"
- 説明文2行目: "OPENAI_API_KEYの代替として使用可能"
- デフォルト値: 空欄

CLAUDE_CODE_OAUTH_TOKEN:
- 入力タイプ: パスワード
- 説明文1行目: "Claude Code OAuth トークン（任意）"
- 説明文2行目: "Claude実行モードで使用されます"
- デフォルト値: 空欄

CLAUDE_CODE_API_KEY:
- 入力タイプ: パスワード
- 説明文1行目: "Claude Code API キー（任意）"
- 説明文2行目: "Claude実行モードで使用されます"
- デフォルト値: 空欄

ANTHROPIC_API_KEY:
- 入力タイプ: パスワード
- 説明文1行目: "Anthropic API キー（任意）"
- 説明文2行目: "Claude実行モードで使用されます"
- デフォルト値: 空欄
```

**Step 4: 他の4つのジョブでも同様に確認**
```bash
# 各ジョブのパラメータ画面を確認:
# - AI_Workflow/infrastructure-as-code/02_Preset
# - AI_Workflow/infrastructure-as-code/03_Single_Phase
# - AI_Workflow/infrastructure-as-code/04_Rollback
# - AI_Workflow/infrastructure-as-code/05_Auto_Issue

# 確認項目:
# - 6つのAPIキーパラメータが存在する
# - パラメータ名、説明文、順序が01_All_Phasesと同一である
```

**Step 5: スクリーンショット取得**
```bash
# 各ジョブのパラメータ画面のスクリーンショットを取得:
# - 01_All_Phases_parameters.png
# - 02_Preset_parameters.png
# - 03_Single_Phase_parameters.png
# - 04_Rollback_parameters.png
# - 05_Auto_Issue_parameters.png
```

#### 期待結果

**確認項目チェックリスト**:

- [ ] **パラメータ数**: 20個（既存14個 + 新規6個）が表示される
- [ ] **セクション構成**: APIキー設定セクションがAWS認証情報と「その他」の間に配置されている
- [ ] **パラメータタイプ**: 6つのAPIキーパラメータすべてがパスワードタイプ（●●●●●表示）である
- [ ] **説明文の言語**: すべて日本語で記載されている
- [ ] **説明文の内容**: 各パラメータの用途が明確に記載されている
- [ ] **「任意」の明記**: すべてのパラメータで「（任意）」が明記されている
- [ ] **デフォルト値**: すべてのAPIキーパラメータがデフォルト空欄である
- [ ] **5つのジョブで一貫性**: すべてのジョブで同じパラメータ定義が適用されている
- [ ] **既存パラメータへの影響**: 既存の14個のパラメータが変更されていない
- [ ] **パラメータ順序**: 既存パラメータの順序が変更されていない

#### テストデータ
- 対象ジョブ: 5つのAI Workflowジョブ
- 検証パラメータ: 6つのAPIキーパラメータ

#### 合格基準
- すべての確認項目チェックリストが✅である
- 5つのジョブすべてで同じ結果が得られる

---

### TS-4: セキュリティ統合テスト（パスワードマスキング）

#### 目的
APIキーパラメータがJenkins UIとビルドログで正しくマスク表示されることを検証する。

#### 前提条件
- TS-3が合格している
- テスト用のダミーAPIキーを準備

#### テスト手順

**Step 1: テストデータの準備**
```bash
# テスト用のダミーAPIキー（実際には無効な値）
GITHUB_TOKEN_TEST="ghp_test1234567890abcdefghijklmnopqrstuvwxyz"
OPENAI_API_KEY_TEST="sk-test1234567890abcdefghijklmnopqrstuvwxyz"
CODEX_API_KEY_TEST="cx-test1234567890abcdefghijklmnopqrstuvwxyz"
CLAUDE_CODE_OAUTH_TOKEN_TEST="oauth_test1234567890abcdefghijklmnopqrst"
CLAUDE_CODE_API_KEY_TEST="claude_test1234567890abcdefghijklmnopqr"
ANTHROPIC_API_KEY_TEST="sk-ant-test1234567890abcdefghijklmnopqrst"
```

**Step 2: パラメータ入力**
```bash
# Jenkins UI操作:
# 1. AI_Workflow/infrastructure-as-code/01_All_Phases を開く
# 2. 「Build with Parameters」をクリック
# 3. 以下のパラメータを入力:

ISSUE_URL: https://github.com/tielec/infrastructure-as-code/issues/1
GITHUB_TOKEN: ghp_test1234567890abcdefghijklmnopqrstuvwxyz
OPENAI_API_KEY: sk-test1234567890abcdefghijklmnopqrstuvwxyz
DRY_RUN: true （ドライランモードで実行）
```

**Step 3: 入力値のマスク確認**
```bash
# パラメータ入力画面で確認:
# - GITHUB_TOKENの入力欄が●●●●●として表示される
# - 入力中の文字が●で隠される
# - 入力後、入力欄をクリックしても平文が表示されない
```

**Step 4: ジョブの実行**
```bash
# Jenkins UI操作:
# 1. 「ビルド」ボタンをクリック
# 2. ビルドが開始されることを確認
# 3. ビルド番号をクリックしてビルド詳細を開く
```

**Step 5: ビルドログでのマスク確認**
```bash
# Jenkins UI操作:
# 1. 「Console Output」を開く
# 2. パラメータ表示部分を確認

# 期待される出力:
# [Pipeline] Start of Pipeline
# [Pipeline] node
# Running on Jenkins in /var/jenkins_home/workspace/...
# [Pipeline] {
# [Pipeline] stage
# [Pipeline] { (Declarative: Checkout SCM)
# ...
# Parameters:
#   ISSUE_URL=https://github.com/tielec/infrastructure-as-code/issues/1
#   GITHUB_TOKEN=****
#   OPENAI_API_KEY=****
#   DRY_RUN=true
#   ...
```

**Step 6: パラメータ画面での再確認**
```bash
# Jenkins UI操作:
# 1. ビルド詳細画面で「Parameters」タブを開く
# 2. 各パラメータの値を確認

# 期待される表示:
# GITHUB_TOKEN: ****
# OPENAI_API_KEY: ****
# CODEX_API_KEY: （空欄）
```

**Step 7: ビルドログ全体の検索**
```bash
# Jenkins UI操作:
# 1. Console Outputを全文取得（ページの最後まで表示）
# 2. ブラウザの検索機能（Ctrl+F）で以下を検索:
#    - "ghp_test1234567890" → ヒット0件であることを確認
#    - "sk-test1234567890" → ヒット0件であることを確認

# 期待結果: ダミーAPIキーの平文がログに一切含まれていない
```

#### 期待結果

**確認項目チェックリスト**:

- [ ] **入力画面マスク**: パラメータ入力欄が●●●●●として表示される
- [ ] **入力中マスク**: 入力中の文字が●で隠される
- [ ] **ビルドログマスク**: パラメータ値が`****`として表示される
- [ ] **パラメータタブマスク**: ビルド詳細の「Parameters」タブでも`****`として表示される
- [ ] **平文漏洩なし**: ビルドログ全体にダミーAPIキーの平文が含まれていない
- [ ] **環境変数マスク**: 環境変数としてアクセスした場合も`****`として表示される
- [ ] **すべてのAPIキー**: 6つのパラメータすべてでマスキングが機能する

#### テストデータ
- テスト用ダミーAPIキー: 上記Step 1で定義
- テスト用Issue URL: https://github.com/tielec/infrastructure-as-code/issues/1

#### 合格基準
- すべての確認項目チェックリストが✅である
- ビルドログに平文が0件である

#### 異常系シナリオ

**異常系-1: パスワードマスキングが機能しない場合**

- **症状**: ビルドログにAPIキーの平文が表示される
- **原因**: `password()`メソッドではなく`stringParam()`を使用している
- **対処**: DSLファイルを修正し、`password()`メソッドに変更
- **再テスト**: シードジョブ再実行後、本テストを再実施

---

### TS-5: 後方互換性統合テスト

#### 目的
新規パラメータの追加が既存のワークフローに影響を与えないことを検証する。

#### 前提条件
- TS-3が合格している
- テスト用のIssue URLが利用可能

#### テスト手順

**Step 1: 空パラメータでの実行**
```bash
# Jenkins UI操作:
# 1. AI_Workflow/infrastructure-as-code/01_All_Phases を開く
# 2. 「Build with Parameters」をクリック
# 3. 以下のパラメータのみ入力（APIキーは空欄）:

ISSUE_URL: https://github.com/tielec/infrastructure-as-code/issues/1
DRY_RUN: true
SKIP_REVIEW: true （レビューをスキップして高速化）
FORCE_RESET: true
```

**Step 2: ジョブの実行**
```bash
# Jenkins UI操作:
# 1. 「ビルド」ボタンをクリック
# 2. ビルドが開始されることを確認
```

**Step 3: 実行結果の確認**
```bash
# Jenkins UI操作:
# 1. Console Outputを監視
# 2. エラーが発生しないことを確認

# 期待される動作:
# - パラメータ検証エラーが発生しない
# - "Parameter validation failed" 等のエラーメッセージがない
# - ワークフローがPlanning Phaseまで進む（DRY_RUNのため実際の処理はスキップ）
```

**Step 4: 既存パラメータの動作確認**
```bash
# Console Outputで以下を確認:
# - ISSUE_URLが正しく認識されている
# - DRY_RUNモードが有効になっている
# - SKIP_REVIEWが有効になっている
# - FORCE_RESETが有効になっている
# - ワークフローのメタデータが初期化されている
```

**Step 5: 既存のジョブとの比較**
```bash
# シードジョブ実行前のビルド履歴と比較:
# 1. ビルド履歴から、パラメータ追加前のビルドを選択
# 2. Console Outputを比較
# 3. 動作に差異がないことを確認（パラメータ追加以外）
```

#### 期待結果

**確認項目チェックリスト**:

- [ ] **ジョブ開始**: APIキーが空欄でもジョブが正常に開始される
- [ ] **パラメータ検証**: パラメータ検証エラーが発生しない
- [ ] **ワークフロー実行**: ワークフローがPlanning Phaseまで進む
- [ ] **既存パラメータ動作**: ISSUE_URL、DRY_RUN等の既存パラメータが正常に機能する
- [ ] **エラーメッセージなし**: Console Outputにパラメータ関連のエラーがない
- [ ] **ビルドステータス**: SUCCESS（DRY_RUNのため実際の処理はスキップされるが、エラーは発生しない）
- [ ] **既存動作との一貫性**: パラメータ追加前のビルドと動作が一貫している

#### テストデータ
- テスト用Issue URL: https://github.com/tielec/infrastructure-as-code/issues/1
- APIキーパラメータ: すべて空欄

#### 合格基準
- すべての確認項目チェックリストが✅である
- ビルドが正常に完了する（ドライランモードで）

---

### TS-6: 環境変数統合テスト

#### 目的
パラメータが環境変数としてJenkinsfileやシェルスクリプトから正しくアクセスできることを検証する。

#### 前提条件
- TS-4が合格している
- テスト用のJenkinsfileまたはシェルスクリプトを準備

#### テスト手順

**Step 1: テストジョブの準備**
```bash
# オプション1: 既存のJenkinsfileを一時的に修正（推奨しない）
# オプション2: 別のテスト用ジョブを作成（推奨しない）
# オプション3: DRY_RUNモードでログを確認（推奨）

# 本テストでは、オプション3を採用
# AI Workflow Agentは環境変数として params.GITHUB_TOKEN 等にアクセスする設計
```

**Step 2: パラメータ付きでジョブを実行**
```bash
# Jenkins UI操作:
# 1. AI_Workflow/infrastructure-as-code/01_All_Phases を開く
# 2. 「Build with Parameters」をクリック
# 3. 以下のパラメータを入力:

ISSUE_URL: https://github.com/tielec/infrastructure-as-code/issues/1
GITHUB_TOKEN: ghp_test1234567890abcdefghijklmnopqrstuvwxyz
DRY_RUN: true
SKIP_REVIEW: true
```

**Step 3: Console Outputでの環境変数確認**
```bash
# Console Outputで以下を確認:
# - Jenkins Pipelineがパラメータを環境変数として認識している
# - AI Workflow Agentがパラメータにアクセスしようとしている（DRY_RUNのため実際には使用されない）

# 期待されるログ（一部抜粋）:
# [ai-workflow] Parameters:
#   ISSUE_URL=https://github.com/tielec/infrastructure-as-code/issues/1
#   GITHUB_TOKEN=****
#   DRY_RUN=true
```

**Step 4: パラメータのアクセス可能性確認**
```bash
# Jenkinsfileでのパラメータアクセス方法を確認:
# - params.GITHUB_TOKEN
# - env.GITHUB_TOKEN
# - ${params.GITHUB_TOKEN}（シェルスクリプト内）

# これらすべての方法でパラメータにアクセスできることを確認
```

#### 期待結果

**確認項目チェックリスト**:

- [ ] **params経由アクセス**: `params.GITHUB_TOKEN`でアクセス可能
- [ ] **env経由アクセス**: `env.GITHUB_TOKEN`でアクセス可能
- [ ] **シェル経由アクセス**: `$GITHUB_TOKEN`（シェルスクリプト内）でアクセス可能
- [ ] **マスキング維持**: アクセス時も値が`****`としてマスクされる
- [ ] **6つのパラメータすべて**: すべてのAPIキーパラメータが環境変数としてアクセス可能
- [ ] **既存パラメータとの一貫性**: 既存のパラメータ（ISSUE_URL等）と同じメカニズムでアクセス可能

#### テストデータ
- テスト用APIキー: TS-4と同じダミー値

#### 合格基準
- すべての確認項目チェックリストが✅である

---

## 3. テストデータ

### 3.1 テスト用ダミーAPIキー

| パラメータ名 | ダミー値 | 用途 |
|-------------|---------|------|
| `GITHUB_TOKEN` | `ghp_test1234567890abcdefghijklmnopqrstuvwxyz` | マスキング検証 |
| `OPENAI_API_KEY` | `sk-test1234567890abcdefghijklmnopqrstuvwxyz` | マスキング検証 |
| `CODEX_API_KEY` | `cx-test1234567890abcdefghijklmnopqrstuvwxyz` | マスキング検証 |
| `CLAUDE_CODE_OAUTH_TOKEN` | `oauth_test1234567890abcdefghijklmnopqrst` | マスキング検証 |
| `CLAUDE_CODE_API_KEY` | `claude_test1234567890abcdefghijklmnopqr` | マスキング検証 |
| `ANTHROPIC_API_KEY` | `sk-ant-test1234567890abcdefghijklmnopqrst` | マスキング検証 |

**注意**: これらは実際には無効な値であり、テスト専用です。

### 3.2 テスト用Issue URL

| Issue URL | 用途 |
|-----------|------|
| `https://github.com/tielec/infrastructure-as-code/issues/1` | 基本的な動作確認 |

### 3.3 対象DSLファイル

| # | ファイルパス | テスト対象 |
|---|-------------|-----------|
| 1 | `jenkins/jobs/dsl/ai-workflow/ai_workflow_all_phases_job.groovy` | すべてのテストシナリオ |
| 2 | `jenkins/jobs/dsl/ai-workflow/ai_workflow_preset_job.groovy` | TS-1, TS-2, TS-3 |
| 3 | `jenkins/jobs/dsl/ai-workflow/ai_workflow_single_phase_job.groovy` | TS-1, TS-2, TS-3 |
| 4 | `jenkins/jobs/dsl/ai-workflow/ai_workflow_rollback_job.groovy` | TS-1, TS-2, TS-3 |
| 5 | `jenkins/jobs/dsl/ai-workflow/ai_workflow_auto_issue_job.groovy` | TS-1, TS-2, TS-3 |

---

## 4. テスト環境要件

### 4.1 Jenkins環境

| 要件項目 | 必要条件 |
|---------|---------|
| **Jenkinsバージョン** | 2.426.1以上 |
| **必須プラグイン** | Job DSL Plugin, Pipeline Plugin, Credentials Binding Plugin |
| **アクセス権限** | ジョブ実行権限、シードジョブ実行権限 |
| **ネットワーク** | GitHub（https://github.com）へのアクセス可能 |

### 4.2 Git環境

| 要件項目 | 必要条件 |
|---------|---------|
| **リポジトリ** | infrastructure-as-codeリポジトリへのアクセス権限 |
| **ブランチ** | テスト用ブランチ（例: `feature/issue-455-api-keys`） |
| **コミット権限** | 変更をコミット・プッシュできる権限 |

### 4.3 テストツール

| ツール | 用途 |
|-------|------|
| **Webブラウザ** | Jenkins UIの操作（Chrome、Firefox推奨） |
| **スクリーンショットツール** | パラメータ画面のキャプチャ取得 |
| **テキストエディタ** | DSLファイルの確認・編集 |

### 4.4 モック/スタブの必要性

**不要**

理由: Integrationテストでは実際のJenkins環境で動作を検証するため、モック/スタブは使用しない。

---

## 5. テスト実行計画

### 5.1 テスト実行順序

```mermaid
graph TB
    TS1[TS-1: DSL構文検証] -->|合格| TS2[TS-2: シードジョブ実行]
    TS2 -->|合格| TS3[TS-3: パラメータ表示]
    TS3 -->|合格| TS4[TS-4: セキュリティ]
    TS3 -->|合格| TS5[TS-5: 後方互換性]
    TS4 -->|合格| TS6[TS-6: 環境変数]

    TS2 -->|不合格| FIX1[DSL修正]
    FIX1 --> TS2

    TS4 -->|不合格| FIX2[パラメータタイプ修正]
    FIX2 --> TS1
```

### 5.2 テスト実行スケジュール

| テストシナリオ | 見積もり時間 | 累計時間 | 実施者 |
|--------------|------------|---------|-------|
| TS-1: DSL構文検証 | 0.1h | 0.1h | 開発者 |
| TS-2: シードジョブ実行 | 0.1h | 0.2h | 開発者 |
| TS-3: パラメータ表示 | 0.1h | 0.3h | 開発者 |
| TS-4: セキュリティ | 0.1h | 0.4h | 開発者 |
| TS-5: 後方互換性 | 0.1h | 0.5h | 開発者 |
| TS-6: 環境変数 | 0.1h | 0.6h | 開発者 |
| **合計** | **0.6h** | - | - |

**注**: Planning Documentでは0.5hを見積もっていたが、6つのテストシナリオを実施するため0.6hに調整。

### 5.3 テスト実行の前提条件

- [ ] Phase 4（実装）が完了している
- [ ] 5つのDSLファイルにAPIキーパラメータが追加されている
- [ ] Git管理下で変更がコミット済み
- [ ] Jenkins環境にアクセス可能
- [ ] シードジョブ実行権限がある

---

## 6. 受け入れ基準との対応表

| 受け入れ基準 | 対応テストシナリオ | 検証方法 |
|------------|-------------------|---------|
| **AC-1**: パラメータがDSLファイルに追加されている | TS-1 | DSLファイルの構文確認 |
| **AC-2**: パラメータがJenkins UIで表示される | TS-3 | パラメータ画面の目視確認 |
| **AC-3**: パラメータ値がマスク表示される | TS-4 | ビルドログとUI画面の確認 |
| **AC-4**: パラメータが環境変数として利用可能 | TS-6 | Jenkinsfileでのアクセス確認 |
| **AC-5**: 5つのジョブすべてで一貫性がある | TS-3 | 5つのジョブのパラメータ比較 |
| **AC-6**: 既存のパラメータに影響がない | TS-5 | 後方互換性テスト |
| **AC-7**: シードジョブが正常に実行される | TS-2 | シードジョブの実行結果確認 |
| **AC-8**: 空パラメータでもジョブが実行可能 | TS-5 | 空パラメータでの実行テスト |

---

## 7. テスト成功基準

### 7.1 品質ゲート（Phase 3）

- [x] **Phase 2の戦略に沿ったテストシナリオである**
  - INTEGRATION_ONLY戦略に従い、6つの統合テストシナリオを作成
  - Unitテスト、BDDテストは作成していない（戦略に含まれないため）

- [x] **主要な正常系がカバーされている**
  - TS-1〜TS-6で主要な正常系をカバー
  - シードジョブ実行、パラメータ表示、セキュリティ、後方互換性、環境変数アクセス

- [x] **主要な異常系がカバーされている**
  - TS-2の異常系-1: DSL構文エラー
  - TS-4の異常系-1: パスワードマスキング未動作

- [x] **期待結果が明確である**
  - 各テストシナリオで確認項目チェックリストを定義
  - 合格基準を明確に記載

### 7.2 全体の成功基準

**必須条件**:
- [ ] TS-1〜TS-6のすべてのテストシナリオが合格
- [ ] AC-1〜AC-8のすべての受け入れ基準が満たされている
- [ ] 品質ゲート（Phase 3）の4つの項目がすべて✅

**推奨条件**:
- [ ] テスト実行時間が見積もり（0.6h）以内に完了
- [ ] スクリーンショットがすべて取得できている
- [ ] テスト結果ドキュメントが作成されている

---

## 8. テスト実行チェックリスト

### 8.1 テスト実行前

- [ ] Phase 4（実装）が完了している
- [ ] 5つのDSLファイルが修正されている
- [ ] Git commit済み（ロールバック可能な状態）
- [ ] Jenkins環境にログイン済み
- [ ] シードジョブ実行権限を確認済み

### 8.2 テスト実行中

- [ ] TS-1: DSL構文検証が合格
- [ ] TS-2: シードジョブ実行が合格
- [ ] TS-3: パラメータ表示が合格
- [ ] TS-4: セキュリティが合格
- [ ] TS-5: 後方互換性が合格
- [ ] TS-6: 環境変数が合格

### 8.3 テスト実行後

- [ ] スクリーンショット取得完了（5ジョブ分）
- [ ] テスト結果ドキュメント作成完了
- [ ] 不合格項目の修正完了（該当する場合）
- [ ] 再テスト完了（該当する場合）
- [ ] Phase 7（ドキュメント）への引き継ぎ準備完了

---

## 9. リスクと対策

### 9.1 テストリスク

| リスク | 影響度 | 確率 | 対策 |
|--------|--------|------|------|
| **シードジョブ実行失敗** | 高 | 低 | Git revertで即座にロールバック |
| **パスワードマスキング未動作** | 高 | 極低 | Jenkins標準機能のため動作保証あり |
| **Jenkins環境の不具合** | 中 | 低 | 事前に環境の動作確認を実施 |
| **テスト時間超過** | 低 | 低 | 各テストシナリオの時間を厳守 |

### 9.2 ロールバック手順

**DSL構文エラーが発生した場合**:

```bash
# 1. Git revert
git revert <commit-hash>
git push origin <branch>

# 2. シードジョブ再実行
# Jenkins UI: Admin_Jobs/job-creator > ビルド実行

# 3. エラー修正
# DSLファイルを修正

# 4. 再テスト
# TS-1から再実行
```

---

## 10. 次フェーズへの引き継ぎ事項

### 10.1 Phase 6（テスト実行）への引き継ぎ

**テストシナリオ**:
- TS-1〜TS-6: 詳細な実行手順と期待結果を記載済み

**テストデータ**:
- ダミーAPIキー: セクション3.1
- テスト用Issue URL: セクション3.2

**テスト環境**:
- Jenkins環境要件: セクション4.1
- Git環境要件: セクション4.2

### 10.2 Phase 7（ドキュメント）への引き継ぎ

**テスト結果報告事項**:
- 各テストシナリオの合格/不合格
- スクリーンショット（5ジョブ分）
- 不合格項目と修正内容（該当する場合）

### 10.3 Phase 8（レポート）への引き継ぎ

**実装完了レポートに含めるべき事項**:
- テスト実行サマリー（6テストシナリオの結果）
- 受け入れ基準の達成状況（AC-1〜AC-8）
- スクリーンショット（パラメータ表示画面）
- Issue #455へのコメント投稿内容

---

## 11. 付録

### 11.1 参照ドキュメント

- **Planning Document**: `.ai-workflow/issue-455/00_planning/output/planning.md`
- **Requirements Document**: `.ai-workflow/issue-455/01_requirements/output/requirements.md`
- **Design Document**: `.ai-workflow/issue-455/02_design/output/design.md`
- **Issue #455**: https://github.com/tielec/infrastructure-as-code/issues/455

### 11.2 用語集

| 用語 | 説明 |
|------|------|
| **DSLファイル** | Job DSL Pluginで使用するGroovyスクリプトファイル |
| **シードジョブ** | DSLファイルを読み込んでJenkinsジョブを自動生成するジョブ |
| **パスワードパラメータ** | Jenkins UIでマスク表示される、セキュアなパラメータタイプ |
| **マスキング** | パスワード等の機密情報を`****`として表示する機能 |
| **統合テスト** | 複数のコンポーネントが連携して正しく動作するかを検証するテスト |
| **ドライランモード** | 実際の処理を実行せず、動作確認のみを行うモード |

### 11.3 テストシナリオ一覧（再掲）

| # | テストシナリオ名 | 目的 | 所要時間 |
|---|----------------|------|---------|
| TS-1 | DSL構文検証統合テスト | DSL構文の正当性検証 | 0.1h |
| TS-2 | シードジョブ実行統合テスト | ジョブ生成の正当性検証 | 0.1h |
| TS-3 | パラメータ表示統合テスト | パラメータUIの検証 | 0.1h |
| TS-4 | セキュリティ統合テスト | パスワードマスキング検証 | 0.1h |
| TS-5 | 後方互換性統合テスト | 既存ワークフローへの影響検証 | 0.1h |
| TS-6 | 環境変数統合テスト | 環境変数アクセスの検証 | 0.1h |

---

## 12. 承認

### 12.1 品質ゲート確認

- [x] **Phase 2の戦略に沿ったテストシナリオである** → **達成**（INTEGRATION_ONLY戦略）
- [x] **主要な正常系がカバーされている** → **達成**（TS-1〜TS-6）
- [x] **主要な異常系がカバーされている** → **達成**（TS-2, TS-4の異常系シナリオ）
- [x] **期待結果が明確である** → **達成**（各テストシナリオに確認項目チェックリスト）

### 12.2 レビュー結果

- **クリティカルシンキングレビュー**: 未実施（次ステップ）
- **ブロッカー**: なし（想定）
- **改善提案**: レビュー後に反映

### 12.3 次フェーズへの移行判断

- [ ] 品質ゲート（Phase 3）をすべてクリア
- [ ] レビューでブロッカーが検出されない
- [ ] すべてのテストシナリオが実行可能である

**判断**: テストシナリオフェーズ完了、実装フェーズ（Phase 4）へ移行可能

---

**文書作成日**: 2025-01-20
**作成者**: AI Workflow Agent
**バージョン**: 1.0
**ステータス**: レビュー待ち
