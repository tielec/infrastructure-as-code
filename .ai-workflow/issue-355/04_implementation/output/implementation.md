# 実装ログ - Issue #355

## ドキュメント情報

- **Issue番号**: #355
- **タイトル**: [FEATURE] AI Workflow: Init時にドラフトPRを自動作成
- **作成日**: 2025-10-12
- **バージョン**: 1.0.0

---

## 実装サマリー

- **実装戦略**: EXTEND（既存コードの拡張）
- **変更ファイル数**: 2個
- **新規作成ファイル数**: 0個
- **実装完了日**: 2025-10-12

### 実装内容の概要

設計書に基づき、以下の機能を実装しました：

1. **GitHubClient拡張**: PR作成、既存PRチェック、PR本文テンプレート生成の3つのメソッドを追加
2. **main.py init コマンド拡張**: metadata.json作成後に、commit → push → PR作成のフローを追加

---

## 変更ファイル一覧

### 修正ファイル

1. `scripts/ai-workflow/core/github_client.py`: GitHubClient クラスに3つのメソッドを追加（約200行追加）
2. `scripts/ai-workflow/main.py`: init コマンドにPR作成フローを追加（約87行追加）

### 新規作成ファイル

なし（すべて既存ファイルの拡張）

---

## 実装詳細

### 1. GitHubClient拡張 (scripts/ai-workflow/core/github_client.py)

#### 1.1 create_pull_request() メソッド

**実装内容**:
- PyGithub の `repository.create_pull()` を使用してPR作成
- draft パラメータでドラフト状態を指定
- エラーハンドリング: 401/403（権限エラー）、422（既存PR重複）を特別に処理
- 戻り値: Dict形式（success, pr_url, pr_number, error）

**理由**:
- 設計書の7.1.1セクションに従い、PyGithubを使用（gh CLI依存を排除）
- 権限エラーと既存PR重複エラーは、ユーザーフレンドリーなメッセージに変換
- 例外を内部でキャッチし、エラー情報を辞書で返却することで、呼び出し側でのエラーハンドリングを簡素化

**注意点**:
- PyGithub 2.0以降では `draft` パラメータが標準サポートされている
- エラーメッセージは日本語ではなく英語で記載（既存コードのパターンに準拠）

#### 1.2 check_existing_pr() メソッド

**実装内容**:
- PyGithub の `repository.get_pulls()` を使用して既存PRを検索
- head パラメータは `owner:branch_name` 形式で指定（GitHub API要件）
- 既存PR存在時: PR情報（pr_number, pr_url, state）を返却
- 既存PR不在時: None を返却
- エラー時: 警告ログを出力してNoneを返却（例外をraiseしない）

**理由**:
- 設計書の7.1.2セクションに従い実装
- エラー時にNoneを返却することで、呼び出し側は「PRが存在しない」と判断可能
- 例外をraiseせず警告ログで済ませることで、init処理が継続可能

**注意点**:
- `repository.get_pulls()` は PaginatedList を返すため、for ループで最初の要素を取得
- owner情報は `self.repository.owner.login` から取得

#### 1.3 _generate_pr_body_template() メソッド

**実装内容**:
- Markdown形式のPR本文テンプレートを生成
- Closes #{issue_number} でIssueと自動リンク
- ワークフロー進捗チェックリスト（Phase 0のみ完了状態）
- 成果物ディレクトリの説明
- 実行環境情報（モデル、ContentParser、ブランチ）

**理由**:
- 要件定義書 FR-03 の PR本文テンプレート仕様に準拠
- Phase 0（planning）完了時にPRが作成されるため、Phase 0のみチェック済み
- f-string を使用して動的な値（issue_number, branch_name）を埋め込み

**注意点**:
- テンプレートは絵文字を使用（📋, 🔄, 📁, ⚙️）してユーザーフレンドリーに
- Markdown形式のため、インデントとフォーマットに注意

---

### 2. main.py init コマンド拡張 (scripts/ai-workflow/main.py)

#### 2.1 実装フロー

**実装内容**:
1. metadata.json作成後、GitManagerインスタンスを生成
2. `commit_phase_output(phase_name='planning')` でmetadata.jsonをcommit
3. `push_to_remote()` でリモートにpush（最大3回リトライ）
4. GitHubClientインスタンスを生成（環境変数から認証情報取得）
5. `check_existing_pr()` で既存PRの有無を確認
6. 既存PR不在時に `create_pull_request()` でドラフトPR作成
7. 各ステップの結果をログ出力

**理由**:
- 設計書の7.2.2セクションに従い実装
- エラーハンドリング: commit/push失敗時はPR作成をスキップ（init自体は成功）
- PR作成失敗時はinit全体は成功として扱う（commit/pushは完了しているため）

**注意点**:
- GitManagerインスタンス生成には MetadataManager が必要
- GITHUB_TOKEN または GITHUB_REPOSITORY が未設定の場合、PR作成をスキップして手動作成を案内
- 既存PR存在時は警告メッセージを表示してスキップ（エラーではない）

#### 2.2 エラーハンドリング設計

**実装内容**:
- commit失敗: `[WARNING]` ログを出力してreturn（init全体は失敗）
- push失敗: `[WARNING]` ログを出力してreturn（init全体は失敗）
- 環境変数未設定: `[WARNING]` ログを出力してreturn（PR作成スキップ、init成功）
- 既存PR存在: `[WARNING]` ログを出力してreturn（PR作成スキップ、init成功）
- PR作成失敗: `[WARNING]` ログを出力（init成功）
- 予期しない例外: `[ERROR]` ログを出力してtraceback表示（init成功）

**理由**:
- 設計書の7.3.1セクション（エラー分類表）に準拠
- commitとpushは必須処理（失敗時はinitを中断）
- PR作成は付加価値機能（失敗してもinitは成功）

**注意点**:
- エラーメッセージは日本語と英語を混在させず、既存のログパターンに準拠
- return を使用して早期リターン（後続処理をスキップ）

#### 2.3 ログ出力設計

**実装内容**:
- `[INFO]`: 処理開始（"Committing metadata.json..."）
- `[OK]`: 処理成功（"Commit successful: abc1234"）
- `[WARNING]`: スキップまたは失敗（"PR already exists: ..."）
- `[ERROR]`: 予期しない例外（"Unexpected error during PR creation: ..."）

**理由**:
- 既存のmain.pyのログパターンに準拠
- ユーザーが進捗を追跡しやすいように、各ステップで明示的にログ出力

**注意点**:
- commit hash は最初の7文字のみ表示（Gitの慣例）
- PR URLは完全なURLを表示（ユーザーが直接アクセス可能）

---

## 実装時の判断事項

### 1. PyGithub vs gh CLI

**判断**: PyGithub を使用

**理由**:
- 設計書で「gh CLI依存を排除」と明記されている
- PyGithubはプロジェクトに既に導入済み（requirements.txtで確認）
- gh CLIはDocker環境へのインストールが必要（依存増加）

### 2. エラーハンドリングの粒度

**判断**: commit/pushは必須、PR作成は任意

**理由**:
- 設計書の7.3.2セクション（エラーハンドリングポリシー）に準拠
- commit/pushはGit履歴に残すため必須
- PR作成はGitHub上の可視化機能のため、失敗してもinit自体は有効

### 3. 既存PR重複チェックの実装

**判断**: PR作成前に `check_existing_pr()` を呼び出し

**理由**:
- GitHub APIでPR作成時に422エラーが発生するが、事前チェックでユーザーフレンドリーに
- 既存PRのURLを表示することで、ユーザーが直接確認可能

### 4. PR本文テンプレートのフォーマット

**判断**: Markdown形式、絵文字使用、Phase 0のみ完了

**理由**:
- 要件定義書 FR-03 のテンプレート仕様に準拠
- GitHub上で視認性が高いフォーマット
- Phase 0（planning）完了時にPR作成されるため、Phase 0のみチェック済み

---

## テストに関する注意事項

**Phase 4では実コードのみを実装し、テストコードは Phase 5（test_implementation）で実装します。**

### 手動テストの推奨事項

Phase 5でのテスト実装前に、以下の手動テストを推奨します：

1. **正常系テスト**:
   - `python main.py init --issue-url https://github.com/owner/repo/issues/355`
   - commit、push、PR作成がすべて成功することを確認

2. **既存PRチェックテスト**:
   - 同じIssueに対して2回目のinitを実行
   - "PR already exists" の警告が表示されることを確認

3. **環境変数未設定テスト**:
   - `unset GITHUB_TOKEN` で環境変数を削除
   - "GITHUB_TOKEN or GITHUB_REPOSITORY not set" の警告が表示されることを確認

4. **push失敗テスト**:
   - ネットワークを遮断してpushが失敗することを確認
   - リトライが実行され、最終的に失敗メッセージが表示されることを確認

---

## 既存コードとの整合性

### コーディングスタイル

- **インデント**: 4スペース（既存コードに準拠）
- **命名規則**: snake_case（既存のPythonコードに準拠）
- **ドキュメント文字列**: Google Style（既存のgithub_client.pyに準拠）
- **エラーハンドリング**: try-except with 戻り値辞書（既存のgit_manager.pyに準拠）

### 依存関係

- **PyGithub**: 既存のrequirements.txtに記載済み（バージョン 2.0以降）
- **GitPython**: 既存のgit_manager.pyで使用中
- **click**: 既存のmain.pyで使用中

### ログ出力パターン

- `[INFO]`: 既存のmain.pyで使用中
- `[OK]`: 既存のmain.pyで使用中
- `[WARNING]`: 既存のmain.pyで使用中
- `[ERROR]`: 既存のmain.pyで使用中

---

## 品質ゲート確認

### Phase 4の品質ゲート

- [x] **Phase 2の設計に沿った実装である**: 設計書の7.1、7.2セクションに完全準拠
- [x] **既存コードの規約に準拠している**: コーディングスタイル、命名規則、ログパターンを維持
- [x] **基本的なエラーハンドリングがある**: commit/push/PR作成の各ステップでエラーハンドリング実装
- [x] **明らかなバグがない**: 設計書の実装例に準拠し、エッジケースを考慮

---

## 次のステップ

### Phase 5（test_implementation）

以下のテストコードを実装します：

1. **ユニットテスト**:
   - `tests/unit/core/test_github_client.py`: 新規メソッドのテスト追加
   - `tests/unit/test_main_init_pr.py`: init コマンドのPR作成ロジックのテスト（新規作成）

2. **統合テスト**:
   - `tests/integration/test_init_pr_workflow.py`: init → commit → push → PR作成の統合テスト（新規作成）

### Phase 6（testing）

テストコード実装後、以下を実行します：

1. ユニットテスト実行: `pytest tests/unit/ -v`
2. 統合テスト実行: `pytest tests/integration/ -v`
3. カバレッジ確認: `pytest --cov=scripts/ai-workflow --cov-report=html`

---

## 参考情報

### 実装ファイル

1. **scripts/ai-workflow/core/github_client.py:336-525** - 新規メソッド3つ
2. **scripts/ai-workflow/main.py:406-492** - init コマンド拡張

### 設計ドキュメント

1. **planning.md**: 実装戦略（EXTEND）、見積もり工数（3時間）
2. **requirements.md**: 機能要件（FR-01〜FR-08）、受け入れ基準（AC-01〜AC-08）
3. **design.md**: 詳細設計（7.1〜7.3セクション）
4. **test-scenario.md**: テストシナリオ（TC-U-001〜TC-I-009）

---

**実装ログバージョン**: 1.0.0
**作成日**: 2025-10-12
**次のフェーズ**: Phase 5（test_implementation）

**実装完了**: すべての実コードが設計書に従って実装されました。Phase 5でテストコードを実装します。
