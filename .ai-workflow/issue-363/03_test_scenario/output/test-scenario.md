# テストシナリオ - Issue #363

**作成日**: 2025-10-12
**対象Issue**: [AI-WORKFLOW] 全フェーズ完了後のPull Request内容の自動更新
**Issue URL**: https://github.com/tielec/infrastructure-as-code/issues/363

---

## 目次

1. [テスト戦略サマリー](#1-テスト戦略サマリー)
2. [Unitテストシナリオ](#2-unitテストシナリオ)
3. [Integrationテストシナリオ](#3-integrationテストシナリオ)
4. [テストデータ](#4-テストデータ)
5. [テスト環境要件](#5-テスト環境要件)
6. [品質ゲート確認](#6-品質ゲート確認)

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略

**UNIT_INTEGRATION** (Phase 2設計書より)

- **ユニットテスト**: `GitHubClient`クラスの新規メソッドの単体テスト
- **インテグレーションテスト**: Phase 8完了 → PR更新の一連のE2Eフロー

### 1.2 テスト対象の範囲

#### 新規実装コンポーネント
1. **GitHubClient.update_pull_request()**: PR本文更新API呼び出し
2. **GitHubClient._generate_pr_body_detailed()**: 詳細版PR本文生成
3. **GitHubClient._extract_phase_outputs()**: 成果物情報抽出
4. **GitHubClient._extract_section()**: Markdownセクション抽出ヘルパー
5. **ReportPhase.execute()**: PR更新処理統合（既存メソッドへの追加）

#### 統合ポイント
- Phase 8完了トリガー → PR更新実行
- 成果物収集 → 情報抽出 → テンプレート生成 → GitHub API更新

### 1.3 テストの目的

#### ユニットテストの目的
- 各メソッドが仕様通りに動作することを検証
- 異常系（エラーハンドリング）が正しく実装されていることを確認
- GitHub APIとの通信をモック化して、ロジックのみを検証

#### インテグレーションテストの目的
- Phase 8完了から PR更新までの一連のフローが正常に動作することを検証
- 各コンポーネント間のデータ受け渡しが正しく行われることを確認
- エラー発生時もPhase 8全体は成功として継続することを検証

---

## 2. Unitテストシナリオ

### 2.1 GitHubClient.update_pull_request()

#### UT-01: update_pull_request_正常系

- **目的**: PR本文が正常に更新されることを検証
- **前提条件**:
  - PR #123が存在する
  - GitHub Tokenに適切な権限がある
- **入力**:
  ```python
  pr_number = 123
  body = "## 更新されたPR本文\n\n詳細な内容..."
  ```
- **期待結果**:
  ```python
  {
      'success': True,
      'error': None
  }
  ```
- **テストデータ**: `test_data/pr_body_detailed_sample.md`
- **モック**: `repository.get_pull(123)` が正常なPullRequestオブジェクトを返す
- **検証項目**:
  - `pr.edit(body=body)` が1回呼び出される
  - 戻り値が `{'success': True, 'error': None}` である

---

#### UT-02: update_pull_request_PR未存在エラー

- **目的**: 存在しないPR番号が指定された場合のエラーハンドリングを検証
- **前提条件**:
  - PR #999が存在しない
- **入力**:
  ```python
  pr_number = 999
  body = "## 更新されたPR本文"
  ```
- **期待結果**:
  ```python
  {
      'success': False,
      'error': 'PR #999 not found'
  }
  ```
- **モック**: `repository.get_pull(999)` が `GithubException(status=404)` をスロー
- **検証項目**:
  - エラーメッセージに PR番号が含まれる
  - `pr.edit()` は呼び出されない

---

#### UT-03: update_pull_request_権限エラー

- **目的**: GitHub Tokenに権限がない場合のエラーハンドリングを検証
- **前提条件**:
  - GitHub Tokenに `repo` スコープがない
- **入力**:
  ```python
  pr_number = 123
  body = "## 更新されたPR本文"
  ```
- **期待結果**:
  ```python
  {
      'success': False,
      'error': 'GitHub Token lacks PR edit permissions'
  }
  ```
- **モック**: `pr.edit(body=body)` が `GithubException(status=403)` をスロー
- **検証項目**:
  - エラーメッセージが権限不足を示す
  - 適切にエラーハンドリングされる

---

#### UT-04: update_pull_request_API制限エラー

- **目的**: GitHub API rate limit到達時のエラーハンドリングを検証
- **前提条件**:
  - GitHub APIのrate limitに到達している
- **入力**:
  ```python
  pr_number = 123
  body = "## 更新されたPR本文"
  ```
- **期待結果**:
  ```python
  {
      'success': False,
      'error': 'GitHub API rate limit exceeded'
  }
  ```
- **モック**: `repository.get_pull(123)` が `GithubException(status=429)` をスロー
- **検証項目**:
  - rate limit エラーが適切に検知される
  - エラーメッセージが明確である

---

#### UT-05: update_pull_request_予期しないエラー

- **目的**: 予期しない例外発生時のエラーハンドリングを検証
- **前提条件**:
  - GitHub APIが予期しないエラーを返す
- **入力**:
  ```python
  pr_number = 123
  body = "## 更新されたPR本文"
  ```
- **期待結果**:
  ```python
  {
      'success': False,
      'error': 'Unexpected error: <エラー内容>'
  }
  ```
- **モック**: `pr.edit(body=body)` が `Exception("Network error")` をスロー
- **検証項目**:
  - 予期しない例外がキャッチされる
  - エラーメッセージにエラー内容が含まれる
  - アプリケーション全体がクラッシュしない

---

### 2.2 GitHubClient._generate_pr_body_detailed()

#### UT-06: _generate_pr_body_detailed_正常系

- **目的**: テンプレートから詳細版PR本文が正しく生成されることを検証
- **前提条件**:
  - テンプレートファイル `pr_body_detailed_template.md` が存在する
  - 抽出された成果物情報が用意されている
- **入力**:
  ```python
  issue_number = 363
  branch_name = "ai-workflow/issue-363"
  extracted_info = {
      'summary': '変更サマリーのテスト',
      'implementation_details': '実装詳細のテスト',
      'test_results': 'テスト結果のテスト',
      'documentation_updates': 'ドキュメント更新のテスト',
      'review_points': 'レビューポイントのテスト'
  }
  ```
- **期待結果**:
  - Markdown形式のPR本文が返される
  - プレースホルダーが正しく置換されている
    - `{issue_number}` → `363`
    - `{branch_name}` → `ai-workflow/issue-363`
    - `{summary}` → `変更サマリーのテスト`
    - 他のプレースホルダーも同様
- **テストデータ**: `test_data/pr_body_detailed_template.md`（テンプレートのモック）
- **検証項目**:
  - 生成されたPR本文に全てのプレースホルダーが置換されている
  - Markdown書式が正しい
  - テンプレートファイルが正しいパスから読み込まれる

---

#### UT-07: _generate_pr_body_detailed_テンプレート未存在エラー

- **目的**: テンプレートファイルが存在しない場合のエラーハンドリングを検証
- **前提条件**:
  - テンプレートファイル `pr_body_detailed_template.md` が存在しない
- **入力**:
  ```python
  issue_number = 363
  branch_name = "ai-workflow/issue-363"
  extracted_info = {...}
  ```
- **期待結果**:
  - `FileNotFoundError` が発生する
  - エラーメッセージにテンプレートパスが含まれる
- **検証項目**:
  - 適切な例外がスローされる
  - エラーメッセージが明確である

---

#### UT-08: _generate_pr_body_detailed_プレースホルダー欠落エラー

- **目的**: 必須プレースホルダーが欠落している場合のエラーハンドリングを検証
- **前提条件**:
  - `extracted_info` に必須フィールドが欠落している
- **入力**:
  ```python
  issue_number = 363
  branch_name = "ai-workflow/issue-363"
  extracted_info = {
      'summary': '変更サマリーのテスト',
      # implementation_details が欠落
  }
  ```
- **期待結果**:
  - `KeyError` が発生する
  - エラーメッセージに欠落しているプレースホルダー名が含まれる
- **検証項目**:
  - 適切な例外がスローされる
  - エラーメッセージが欠落フィールドを示す

---

### 2.3 GitHubClient._extract_phase_outputs()

#### UT-09: _extract_phase_outputs_正常系

- **目的**: 各フェーズの成果物から情報が正しく抽出されることを検証
- **前提条件**:
  - 全フェーズの成果物ファイルが存在する
  - 各ファイルに期待されるセクションが含まれている
- **入力**:
  ```python
  issue_number = 363
  phase_outputs = {
      'requirements': Path('.ai-workflow/issue-363/01_requirements/output/requirements.md'),
      'design': Path('.ai-workflow/issue-363/02_design/output/design.md'),
      'implementation': Path('.ai-workflow/issue-363/04_implementation/output/implementation.md'),
      'test_result': Path('.ai-workflow/issue-363/06_testing/output/test-result.md'),
      'documentation': Path('.ai-workflow/issue-363/07_documentation/output/documentation-update-log.md')
  }
  ```
- **期待結果**:
  ```python
  {
      'summary': 'Issue本文から抽出された概要',
      'implementation_details': 'Phase 4から抽出された実装詳細',
      'test_results': 'Phase 6から抽出されたテスト結果',
      'documentation_updates': 'Phase 7から抽出されたドキュメント更新リスト',
      'review_points': '設計書から抽出されたレビューポイント'
  }
  ```
- **テストデータ**: `test_data/phase_outputs/`（各フェーズの成果物モック）
- **検証項目**:
  - 各フィールドに期待される内容が含まれる
  - 全ての成果物ファイルが読み込まれる
  - セクション抽出ロジックが正しく動作する

---

#### UT-10: _extract_phase_outputs_成果物欠落時のフォールバック

- **目的**: 成果物ファイルが欠落している場合のデフォルト値設定を検証
- **前提条件**:
  - Phase 4の成果物ファイルが存在しない
- **入力**:
  ```python
  issue_number = 363
  phase_outputs = {
      'requirements': Path('...'),
      'design': Path('...'),
      # 'implementation' が欠落
      'test_result': Path('...'),
      'documentation': Path('...')
  }
  ```
- **期待結果**:
  ```python
  {
      'summary': '...',
      'implementation_details': '（実装詳細の記載なし）',  # デフォルト値
      'test_results': '...',
      'documentation_updates': '...',
      'review_points': '...'
  }
  ```
- **検証項目**:
  - 欠落フィールドにデフォルト値が設定される
  - 警告ログが出力される
  - 他のフィールドは正常に抽出される
  - エラーにならない（処理継続）

---

#### UT-11: _extract_phase_outputs_Issue取得エラー

- **目的**: Issue本文取得失敗時のエラーハンドリングを検証
- **前提条件**:
  - GitHub APIからIssue取得が失敗する
- **入力**:
  ```python
  issue_number = 999  # 存在しないIssue
  phase_outputs = {...}
  ```
- **期待結果**:
  ```python
  {
      'summary': '（情報抽出エラー）',
      'implementation_details': '（情報抽出エラー）',
      'test_results': '（情報抽出エラー）',
      'documentation_updates': '（情報抽出エラー）',
      'review_points': '（情報抽出エラー）'
  }
  ```
- **モック**: `self.get_issue(999)` が `GithubException(status=404)` をスロー
- **検証項目**:
  - 全フィールドにエラー表示が設定される
  - 警告ログが出力される
  - 例外がスローされない（処理継続）

---

### 2.4 GitHubClient._extract_section()

#### UT-12: _extract_section_正常系

- **目的**: Markdownセクションが正しく抽出されることを検証
- **前提条件**:
  - Markdown文書に対象セクションが存在する
- **入力**:
  ```python
  content = """
  # タイトル

  ## 実装内容

  主要な変更ファイル:
  - file1.py: 変更内容1
  - file2.py: 変更内容2

  ## テスト結果

  テストは全てPASSしました。
  """
  section_header = "## 実装内容"
  ```
- **期待結果**:
  ```
  主要な変更ファイル:
  - file1.py: 変更内容1
  - file2.py: 変更内容2
  ```
- **検証項目**:
  - セクションヘッダー以降、次のセクションまでの内容が抽出される
  - ヘッダー行自体は含まれない
  - 前後の空白が適切にトリムされる

---

#### UT-13: _extract_section_セクション未存在

- **目的**: 対象セクションが存在しない場合の動作を検証
- **前提条件**:
  - Markdown文書に対象セクションが存在しない
- **入力**:
  ```python
  content = """
  # タイトル

  ## その他のセクション

  内容...
  """
  section_header = "## 実装内容"
  ```
- **期待結果**:
  ```
  ""  # 空文字列
  ```
- **検証項目**:
  - 空文字列が返される
  - 例外がスローされない

---

#### UT-14: _extract_section_複数セクション

- **目的**: 同名セクションが複数存在する場合、最初のセクションのみ抽出されることを検証
- **前提条件**:
  - Markdown文書に同名セクションが2つ存在する
- **入力**:
  ```python
  content = """
  ## 実装内容

  最初のセクション内容

  ## 実装内容

  2番目のセクション内容
  """
  section_header = "## 実装内容"
  ```
- **期待結果**:
  ```
  最初のセクション内容
  ```
- **検証項目**:
  - 最初のセクションのみが抽出される
  - 2番目のセクションは含まれない

---

### 2.5 ReportPhase.execute() - PR更新処理部分

#### UT-15: ReportPhase_execute_PR更新成功

- **目的**: Phase 8完了時にPR更新処理が正常に実行されることを検証
- **前提条件**:
  - メタデータに `pr_number` が保存されている
  - 全フェーズの成果物が存在する
- **入力**:
  ```python
  metadata.data['pr_number'] = 123
  issue_number = 363
  ```
- **期待結果**:
  - `GitHubClient.update_pull_request()` が1回呼び出される
  - 成功ログ `[INFO] PR本文の更新に成功しました: PR #123` が出力される
  - Phase 8のステータスが `completed` になる
- **モック**:
  - `update_pull_request()` が `{'success': True, 'error': None}` を返す
- **検証項目**:
  - PR更新処理が実行される
  - 成功ログが出力される
  - Phase 8全体が成功する

---

#### UT-16: ReportPhase_execute_PR番号未保存時の検索

- **目的**: メタデータにPR番号がない場合、既存PR検索が実行されることを検証
- **前提条件**:
  - メタデータに `pr_number` が保存されていない
  - ブランチに対応するPRが存在する
- **入力**:
  ```python
  metadata.data['pr_number'] = None
  metadata.data['branch_name'] = 'ai-workflow/issue-363'
  ```
- **期待結果**:
  - `GitHubClient.check_existing_pr(head='ai-workflow/issue-363')` が1回呼び出される
  - PR番号が取得される
  - PR更新処理が実行される
- **モック**:
  - `check_existing_pr()` が `{'pr_number': 123, ...}` を返す
- **検証項目**:
  - 既存PR検索が実行される
  - 取得したPR番号でPR更新が実行される

---

#### UT-17: ReportPhase_execute_PR未発見時のスキップ

- **目的**: PRが見つからない場合、警告ログを出力してスキップすることを検証
- **前提条件**:
  - メタデータに `pr_number` が保存されていない
  - 対応するPRが存在しない
- **入力**:
  ```python
  metadata.data['pr_number'] = None
  metadata.data['branch_name'] = 'ai-workflow/issue-363'
  ```
- **期待結果**:
  - 警告ログ `[WARNING] PRが見つかりませんでした。PR更新をスキップします。` が出力される
  - `update_pull_request()` は呼び出されない
  - Phase 8のステータスは `completed` になる（失敗扱いにしない）
- **モック**:
  - `check_existing_pr()` が `None` を返す
- **検証項目**:
  - PR更新がスキップされる
  - 警告ログが出力される
  - Phase 8全体は成功する

---

#### UT-18: ReportPhase_execute_PR更新失敗時の継続

- **目的**: PR更新失敗時も Phase 8全体は成功として継続することを検証
- **前提条件**:
  - PR更新処理がエラーを返す
- **入力**:
  ```python
  metadata.data['pr_number'] = 123
  ```
- **期待結果**:
  - 警告ログ `[WARNING] PR本文の更新に失敗しました: <エラーメッセージ>` が出力される
  - Phase 8のステータスは `completed` になる（失敗扱いにしない）
- **モック**:
  - `update_pull_request()` が `{'success': False, 'error': 'API error'}` を返す
- **検証項目**:
  - 警告ログが出力される
  - Phase 8全体は失敗しない
  - エラーメッセージが明確である

---

#### UT-19: ReportPhase_execute_予期しない例外時の継続

- **目的**: PR更新処理で予期しない例外が発生しても Phase 8全体は成功として継続することを検証
- **前提条件**:
  - PR更新処理が予期しない例外をスローする
- **入力**:
  ```python
  metadata.data['pr_number'] = 123
  ```
- **期待結果**:
  - 警告ログ `[WARNING] PR更新処理でエラーが発生しました: <例外内容>` が出力される
  - 情報ログ `[INFO] Phase 8は成功として継続します` が出力される
  - Phase 8のステータスは `completed` になる
- **モック**:
  - `update_pull_request()` が `Exception("Unexpected error")` をスロー
- **検証項目**:
  - 例外がキャッチされる
  - 警告ログと情報ログが出力される
  - Phase 8全体は失敗しない
  - アプリケーション全体がクラッシュしない

---

## 3. Integrationテストシナリオ

### 3.1 Phase 8完了 → PR更新の E2Eフロー

#### IT-01: E2Eフロー_全フェーズ成果物あり_正常系

- **目的**: Phase 8完了から PR更新までの一連のフローが正常に動作することを検証
- **前提条件**:
  - Phase 1-7の成果物が全て生成されている
  - メタデータに `pr_number=123` が保存されている
  - GitHub TokenにPR編集権限がある
- **テスト手順**:
  1. `ReportPhase.execute()` を実行
  2. `report.md` が生成される
  3. メタデータから `pr_number=123` を取得
  4. `_get_phase_outputs()` で各フェーズの成果物パスを取得
  5. `_extract_phase_outputs()` で各成果物から情報を抽出
  6. `_generate_pr_body_detailed()` で詳細版PR本文を生成
  7. `update_pull_request(123, body)` でPR本文を更新
  8. 成功ログを出力
- **期待結果**:
  - `report.md` が正常に生成される
  - PR #123の本文が詳細版に更新される
  - 成功ログ `[INFO] PR本文の更新に成功しました: PR #123` が出力される
  - Phase 8のステータスが `completed` になる
- **確認項目**:
  - [ ] report.md が生成されている
  - [ ] PR本文に以下の情報が含まれている:
    - [ ] 関連Issue（Closes #363）
    - [ ] 変更サマリー
    - [ ] ワークフロー進捗チェックリスト（全てチェック済み）
    - [ ] 実装詳細
    - [ ] テスト結果
    - [ ] ドキュメント更新リスト
    - [ ] レビューポイント
  - [ ] GitHub APIが2回呼び出されている（PR取得1回、PR更新1回）
  - [ ] Phase 8のステータスが `completed`

---

#### IT-02: E2Eフロー_PR番号未保存_検索成功

- **目的**: メタデータにPR番号がない場合でも、既存PR検索で取得して更新できることを検証
- **前提条件**:
  - Phase 1-7の成果物が全て生成されている
  - メタデータに `pr_number` が保存されていない
  - ブランチ `ai-workflow/issue-363` に対応するPR #123が存在する
- **テスト手順**:
  1. `ReportPhase.execute()` を実行
  2. メタデータから `pr_number` 取得を試みる（存在しない）
  3. `check_existing_pr(head='ai-workflow/issue-363')` でPR検索
  4. PR #123が見つかる
  5. 以降は IT-01 と同じフロー
- **期待結果**:
  - 警告ログ `[WARNING] メタデータにpr_numberが保存されていません。既存PRを検索します。` が出力される
  - 情報ログ `[INFO] 既存PRが見つかりました: #123` が出力される
  - PR #123の本文が詳細版に更新される
  - Phase 8のステータスが `completed` になる
- **確認項目**:
  - [ ] 既存PR検索が実行される
  - [ ] PR番号が正しく取得される
  - [ ] PR本文が更新される
  - [ ] Phase 8全体が成功する

---

#### IT-03: E2Eフロー_PR未発見_スキップ

- **目的**: PRが見つからない場合でも Phase 8全体は成功することを検証
- **前提条件**:
  - Phase 1-7の成果物が全て生成されている
  - メタデータに `pr_number` が保存されていない
  - 対応するPRが存在しない
- **テスト手順**:
  1. `ReportPhase.execute()` を実行
  2. メタデータから `pr_number` 取得を試みる（存在しない）
  3. `check_existing_pr(head='ai-workflow/issue-363')` でPR検索
  4. PRが見つからない
  5. 警告ログを出力してPR更新をスキップ
  6. `report.md` は正常に生成される
- **期待結果**:
  - 警告ログ `[WARNING] PRが見つかりませんでした。PR更新をスキップします。` が出力される
  - `update_pull_request()` は呼び出されない
  - `report.md` は正常に生成される
  - Phase 8のステータスが `completed` になる
- **確認項目**:
  - [ ] PR更新がスキップされる
  - [ ] Phase 8全体は失敗しない
  - [ ] report.md が生成されている

---

#### IT-04: E2Eフロー_成果物一部欠落_デフォルト値使用

- **目的**: 一部の成果物が欠落していても PR更新が継続されることを検証
- **前提条件**:
  - Phase 1, 2, 6, 7の成果物は存在
  - Phase 4（implementation.md）の成果物が欠落
  - メタデータに `pr_number=123` が保存されている
- **テスト手順**:
  1. `ReportPhase.execute()` を実行
  2. `_extract_phase_outputs()` で情報抽出を試みる
  3. Phase 4の成果物が見つからない
  4. 警告ログを出力し、`implementation_details` にデフォルト値を設定
  5. 他のフィールドは正常に抽出
  6. デフォルト値を含むPR本文を生成
  7. PR #123を更新
- **期待結果**:
  - 警告ログ `[WARNING] Phase 4の成果物が見つかりません` が出力される（または類似メッセージ）
  - PR本文の実装詳細セクションに `（実装詳細の記載なし）` が表示される
  - 他のセクションは正常に表示される
  - PR更新が成功する
  - Phase 8のステータスが `completed` になる
- **確認項目**:
  - [ ] 警告ログが出力される
  - [ ] 欠落フィールドにデフォルト値が設定される
  - [ ] 他のフィールドは正常に表示される
  - [ ] PR更新が成功する
  - [ ] Phase 8全体は失敗しない

---

#### IT-05: E2Eフロー_GitHub API制限到達_継続

- **目的**: GitHub API制限到達時も Phase 8全体は成功することを検証
- **前提条件**:
  - Phase 1-7の成果物が全て生成されている
  - メタデータに `pr_number=123` が保存されている
  - GitHub APIのrate limitに到達している
- **テスト手順**:
  1. `ReportPhase.execute()` を実行
  2. PR更新処理で `update_pull_request(123, body)` を呼び出す
  3. GitHub APIが `429 Rate Limit Exceeded` を返す
  4. 警告ログを出力
  5. Phase 8全体は成功として継続
- **期待結果**:
  - 警告ログ `[WARNING] PR本文の更新に失敗しました: GitHub API rate limit exceeded` が出力される
  - `report.md` は正常に生成される
  - Phase 8のステータスが `completed` になる
- **確認項目**:
  - [ ] rate limitエラーが適切にハンドリングされる
  - [ ] 警告ログが出力される
  - [ ] Phase 8全体は失敗しない
  - [ ] report.md が生成されている

---

### 3.2 GitHub API連携テスト（モック使用）

#### IT-06: GitHub API連携_PR取得と更新

- **目的**: GitHub APIとの連携（PR取得 → 更新）が正常に動作することを検証
- **前提条件**:
  - GitHub API連携をモック化
  - PR #123が存在する（モック）
- **テスト手順**:
  1. `repository.get_pull(123)` を呼び出す（モック）
  2. PullRequestオブジェクトが返される
  3. `pr.edit(body=new_body)` を呼び出す（モック）
  4. PR本文が更新される
- **期待結果**:
  - `repository.get_pull(123)` が1回呼び出される
  - `pr.edit(body=new_body)` が1回呼び出される
  - 呼び出しパラメータが正しい
- **モック設定**:
  ```python
  mock_pr = MagicMock()
  mock_repository.get_pull.return_value = mock_pr
  mock_pr.edit.return_value = None
  ```
- **確認項目**:
  - [ ] get_pull()が正しいPR番号で呼び出される
  - [ ] edit()が正しいbodyで呼び出される
  - [ ] 呼び出し順序が正しい

---

#### IT-07: GitHub API連携_複数回実行の冪等性

- **目的**: 同じPRに対して複数回実行しても、最新の成果物に基づいて正しく更新されることを検証
- **前提条件**:
  - PR #123が存在する
  - Phase 8を2回実行する
- **テスト手順**:
  1. 1回目: `ReportPhase.execute()` を実行 → PR更新
  2. 成果物の一部を変更（例: test-result.md を更新）
  3. 2回目: `ReportPhase.execute()` を再実行 → PR更新
- **期待結果**:
  - 1回目: PR本文が初回内容で更新される
  - 2回目: PR本文が最新内容で更新される（完全に上書き）
  - 両方とも成功する
- **確認項目**:
  - [ ] 1回目のPR本文が正しい
  - [ ] 2回目のPR本文が最新内容を反映している
  - [ ] 2回目は1回目を上書きしている（追記ではなく）
  - [ ] 両方とも Phase 8が成功する

---

### 3.3 エラーリカバリーフロー

#### IT-08: エラーリカバリー_テンプレート読み込み失敗

- **目的**: テンプレート読み込み失敗時のエラーリカバリーを検証
- **前提条件**:
  - テンプレートファイル `pr_body_detailed_template.md` が存在しない
  - Phase 1-7の成果物が全て生成されている
- **テスト手順**:
  1. `ReportPhase.execute()` を実行
  2. `_generate_pr_body_detailed()` でテンプレート読み込みを試みる
  3. `FileNotFoundError` が発生
  4. エラーがキャッチされ、警告ログが出力される
  5. Phase 8全体は成功として継続
- **期待結果**:
  - 警告ログ `[WARNING] PR更新処理でエラーが発生しました: Template file not found...` が出力される
  - Phase 8のステータスが `completed` になる
  - `report.md` は正常に生成される
- **確認項目**:
  - [ ] テンプレート読み込みエラーが適切にハンドリングされる
  - [ ] Phase 8全体は失敗しない
  - [ ] エラーメッセージが明確である

---

#### IT-09: エラーリカバリー_Issue取得失敗

- **目的**: Issue本文取得失敗時のエラーリカバリーを検証
- **前提条件**:
  - Issue #363の取得がGitHub APIエラーで失敗する
  - Phase 1-7の成果物が全て生成されている
- **テスト手順**:
  1. `ReportPhase.execute()` を実行
  2. `_extract_phase_outputs()` でIssue取得を試みる
  3. `GithubException(status=500)` が発生
  4. エラーがキャッチされ、デフォルト値が設定される
  5. デフォルト値を含むPR本文を生成
  6. PR更新が実行される
- **期待結果**:
  - 警告ログ `[WARNING] 成果物抽出中にエラー: ...` が出力される
  - PR本文の各セクションに `（情報抽出エラー）` が表示される
  - PR更新が実行される
  - Phase 8のステータスが `completed` になる
- **確認項目**:
  - [ ] Issue取得エラーが適切にハンドリングされる
  - [ ] デフォルト値が設定される
  - [ ] PR更新が実行される（エラー内容を含むPR本文）
  - [ ] Phase 8全体は失敗しない

---

## 4. テストデータ

### 4.1 正常系テストデータ

#### TD-01: 成果物サンプルデータ

**ディレクトリ**: `test_data/phase_outputs/`

**ファイル構成**:
```
test_data/phase_outputs/
├── requirements.md          # Phase 1成果物サンプル
├── design.md                # Phase 2成果物サンプル
├── test-scenario.md         # Phase 3成果物サンプル
├── implementation.md        # Phase 4成果物サンプル
├── test-implementation.md   # Phase 5成果物サンプル
├── test-result.md           # Phase 6成果物サンプル
└── documentation-update-log.md  # Phase 7成果物サンプル
```

**requirements.md** (抜粋):
```markdown
# 要件定義書 - Issue #363

## 1. 概要

### 背景
AI Workflowの全フェーズ完了後にPR本文を更新する機能を実装する。

### 目的
レビュアーがPR本文だけで変更内容を把握できるようにする。
```

**design.md** (抜粋):
```markdown
# 詳細設計書 - Issue #363

## レビューポイント

1. `GitHubClient.update_pull_request()` のエラーハンドリングが適切か
2. 成果物パース処理が堅牢か
3. Phase 8完了時のタイミングが適切か
```

**implementation.md** (抜粋):
```markdown
# 実装ログ - Issue #363

## 実装内容

### 変更ファイル
- `scripts/ai-workflow/core/github_client.py`: PR更新メソッドを追加
- `scripts/ai-workflow/phases/report.py`: Phase 8にPR更新処理を統合
- `scripts/ai-workflow/templates/pr_body_detailed_template.md`: 詳細版テンプレートを作成
```

**test-result.md** (抜粋):
```markdown
# テスト結果 - Issue #363

## テスト結果サマリー

### カバレッジ
- ユニットテスト: 15件 (全てPASS)
- インテグレーションテスト: 9件 (全てPASS)
- カバレッジ: 85%
```

**documentation-update-log.md** (抜粋):
```markdown
# ドキュメント更新ログ - Issue #363

## 更新されたドキュメント

- `scripts/ai-workflow/core/github_client.py`: docstringを追加
- `README.md`: PR更新機能の説明を追加
```

---

#### TD-02: PR本文テンプレートサンプル

**ファイル**: `test_data/pr_body_detailed_template.md`

```markdown
## AI Workflow自動生成PR

### 📋 関連Issue
Closes #{issue_number}

### 📝 変更サマリー
{summary}

### 🔄 ワークフロー進捗

- [x] Phase 0: Planning
- [x] Phase 1: Requirements
- [x] Phase 2: Design
- [x] Phase 3: Test Scenario
- [x] Phase 4: Implementation
- [x] Phase 5: Test Implementation
- [x] Phase 6: Testing
- [x] Phase 7: Documentation
- [x] Phase 8: Report

### 🔧 実装詳細

{implementation_details}

### ✅ テスト結果

{test_results}

### 📚 ドキュメント更新

{documentation_updates}

### 👀 レビューポイント

{review_points}

### 📁 成果物

`.ai-workflow/issue-{issue_number}/` ディレクトリに各フェーズの成果物が格納されています。

### ⚙️ 実行環境

- **モデル**: Claude Code Pro Max (Sonnet 4.5)
- **ContentParser**: OpenAI GPT-4o mini
- **ブランチ**: {branch_name}
```

---

#### TD-03: 期待されるPR本文サンプル

**ファイル**: `test_data/expected_pr_body.md`

```markdown
## AI Workflow自動生成PR

### 📋 関連Issue
Closes #363

### 📝 変更サマリー
AI Workflowの全フェーズ完了後にPR本文を更新する機能を実装する。
レビュアーがPR本文だけで変更内容を把握できるようにする。

### 🔄 ワークフロー進捗

- [x] Phase 0: Planning
- [x] Phase 1: Requirements
- [x] Phase 2: Design
- [x] Phase 3: Test Scenario
- [x] Phase 4: Implementation
- [x] Phase 5: Test Implementation
- [x] Phase 6: Testing
- [x] Phase 7: Documentation
- [x] Phase 8: Report

### 🔧 実装詳細

### 変更ファイル
- `scripts/ai-workflow/core/github_client.py`: PR更新メソッドを追加
- `scripts/ai-workflow/phases/report.py`: Phase 8にPR更新処理を統合
- `scripts/ai-workflow/templates/pr_body_detailed_template.md`: 詳細版テンプレートを作成

### ✅ テスト結果

### カバレッジ
- ユニットテスト: 15件 (全てPASS)
- インテグレーションテスト: 9件 (全てPASS)
- カバレッジ: 85%

### 📚 ドキュメント更新

- `scripts/ai-workflow/core/github_client.py`: docstringを追加
- `README.md`: PR更新機能の説明を追加

### 👀 レビューポイント

1. `GitHubClient.update_pull_request()` のエラーハンドリングが適切か
2. 成果物パース処理が堅牢か
3. Phase 8完了時のタイミングが適切か

### 📁 成果物

`.ai-workflow/issue-363/` ディレクトリに各フェーズの成果物が格納されています。

### ⚙️ 実行環境

- **モデル**: Claude Code Pro Max (Sonnet 4.5)
- **ContentParser**: OpenAI GPT-4o mini
- **ブランチ**: ai-workflow/issue-363
```

---

### 4.2 異常系テストデータ

#### TD-04: 成果物欠落シナリオ

**ディレクトリ**: `test_data/phase_outputs_partial/`

**ファイル構成**:
```
test_data/phase_outputs_partial/
├── requirements.md          # 存在する
├── design.md                # 存在する
├── test-result.md           # 存在する
├── documentation-update-log.md  # 存在する
# implementation.md は存在しない
```

**期待される抽出結果**:
```python
{
    'summary': '（正常に抽出された内容）',
    'implementation_details': '（実装詳細の記載なし）',  # デフォルト値
    'test_results': '（正常に抽出された内容）',
    'documentation_updates': '（正常に抽出された内容）',
    'review_points': '（正常に抽出された内容）'
}
```

---

#### TD-05: GitHub APIエラーレスポンス

**404 Not Found**:
```python
GithubException(
    status=404,
    data={'message': 'Not Found'}
)
```

**403 Forbidden**:
```python
GithubException(
    status=403,
    data={'message': 'Resource not accessible by personal access token'}
)
```

**429 Rate Limit Exceeded**:
```python
GithubException(
    status=429,
    data={'message': 'API rate limit exceeded'}
)
```

---

### 4.3 境界値テストデータ

#### TD-06: 長いPR本文

**ファイル**: `test_data/long_pr_body.md`

- **サイズ**: 約10KB（GitHub APIの実用的な上限）
- **内容**: 各セクションに詳細な情報を含む長文

**検証項目**:
- [ ] 10KBのPR本文が正常に送信される
- [ ] GitHub APIが受け付ける
- [ ] PR本文が正しく表示される

---

#### TD-07: 空のセクション

**成果物に空のセクションが含まれる場合**:

**implementation.md**:
```markdown
# 実装ログ

## 実装内容

（記載なし）

## その他

...
```

**期待される抽出結果**:
```
（記載なし）
```

**検証項目**:
- [ ] 空のセクションが抽出される（空文字列ではなく "（記載なし）"）
- [ ] PR本文に反映される

---

## 5. テスト環境要件

### 5.1 ローカル環境

#### 必要なソフトウェア
- **Python**: 3.8以上
- **pytest**: 7.x以上
- **pytest-mock**: 3.x以上（モック機能）
- **pytest-cov**: 4.x以上（カバレッジ測定）

#### 環境変数
```bash
# ユニットテスト用（モック使用のため実際のトークンは不要）
export GITHUB_TOKEN="mock_token_for_testing"
export GITHUB_REPOSITORY="tielec/infrastructure-as-code"
```

#### テスト実行コマンド
```bash
# ユニットテストのみ
pytest tests/unit/core/test_github_client.py -v

# インテグレーションテストのみ
pytest tests/integration/test_pr_update_integration.py -v

# 全テスト実行
pytest tests/ -v

# カバレッジ測定
pytest tests/ --cov=scripts/ai-workflow --cov-report=html
```

---

### 5.2 CI/CD環境

#### GitHub Actions設定

**ワークフローファイル**: `.github/workflows/test.yml`（既存）

**実行トリガー**:
- Push to `ai-workflow/issue-363` ブランチ
- Pull Request作成時

**テスト実行ステップ**:
```yaml
- name: Run Unit Tests
  run: pytest tests/unit/ -v

- name: Run Integration Tests
  run: pytest tests/integration/ -v

- name: Generate Coverage Report
  run: pytest tests/ --cov=scripts/ai-workflow --cov-report=xml
```

---

### 5.3 モック/スタブの必要性

#### モックが必要な箇所

| 対象 | モック方法 | 理由 |
|------|-----------|------|
| `repository.get_pull()` | `pytest-mock` | 実際のGitHub APIを呼び出さない |
| `pr.edit()` | `pytest-mock` | 実際のPR更新を実行しない |
| `repository.get_issue()` | `pytest-mock` | 実際のIssue取得を実行しない |
| `Path.read_text()` | `pytest-mock` または テストデータファイル | 実際の成果物ファイルではなくテストデータを使用 |
| `Path.exists()` | `pytest-mock` | 成果物欠落シナリオのため |

#### モック実装例

```python
# ユニットテスト用モック
def test_update_pull_request_success(mocker):
    # GitHubClientのモック設定
    mock_repository = mocker.MagicMock()
    mock_pr = mocker.MagicMock()
    mock_repository.get_pull.return_value = mock_pr

    github_client = GitHubClient(token="test_token", repo_name="test/repo")
    github_client.repository = mock_repository

    # テスト実行
    result = github_client.update_pull_request(pr_number=123, body="Test body")

    # 検証
    assert result['success'] is True
    mock_repository.get_pull.assert_called_once_with(123)
    mock_pr.edit.assert_called_once_with(body="Test body")
```

---

### 5.4 外部サービス依存

#### GitHub API

**依存内容**:
- PR取得: `GET /repos/{owner}/{repo}/pulls/{number}`
- PR更新: `PATCH /repos/{owner}/{repo}/pulls/{number}`
- Issue取得: `GET /repos/{owner}/{repo}/issues/{number}`

**モック戦略**:
- ユニットテスト: 全てモック化（実際のAPI呼び出しなし）
- インテグレーションテスト: 全てモック化（実際のAPI呼び出しなし）
- E2Eテスト（将来的）: 実際のGitHub APIを使用（テスト用リポジトリ）

**API制限への対応**:
- テストではモックを使用するため、API制限は発生しない
- 実環境での動作確認は別途手動で実施

---

## 6. 品質ゲート確認

### ✅ Phase 2の戦略に沿ったテストシナリオである

- **Phase 2の決定事項**: UNIT_INTEGRATION（ユニットテスト + インテグレーションテスト）
- **本ドキュメントの構成**:
  - セクション2: Unitテストシナリオ（19ケース）
  - セクション3: Integrationテストシナリオ（9ケース）
- **判定**: ✅ **PASS** - Phase 2の戦略に完全に準拠

---

### ✅ 主要な正常系がカバーされている

#### 正常系テストケース

| ID | テストケース名 | カバーする機能 |
|----|--------------|---------------|
| UT-01 | update_pull_request_正常系 | PR更新成功 |
| UT-06 | _generate_pr_body_detailed_正常系 | PR本文生成成功 |
| UT-09 | _extract_phase_outputs_正常系 | 成果物情報抽出成功 |
| UT-12 | _extract_section_正常系 | Markdownセクション抽出成功 |
| UT-15 | ReportPhase_execute_PR更新成功 | Phase 8完了時のPR更新成功 |
| IT-01 | E2Eフロー_全フェーズ成果物あり_正常系 | Phase 8 → PR更新の完全フロー |
| IT-06 | GitHub API連携_PR取得と更新 | GitHub API連携成功 |

- **判定**: ✅ **PASS** - 主要な正常系が全てカバーされている

---

### ✅ 主要な異常系がカバーされている

#### 異常系テストケース

| ID | テストケース名 | カバーする異常系 |
|----|--------------|-----------------|
| UT-02 | update_pull_request_PR未存在エラー | PR未存在（404） |
| UT-03 | update_pull_request_権限エラー | 権限不足（403） |
| UT-04 | update_pull_request_API制限エラー | API制限（429） |
| UT-05 | update_pull_request_予期しないエラー | 予期しない例外 |
| UT-07 | _generate_pr_body_detailed_テンプレート未存在エラー | テンプレート欠落 |
| UT-08 | _generate_pr_body_detailed_プレースホルダー欠落エラー | プレースホルダー欠落 |
| UT-10 | _extract_phase_outputs_成果物欠落時のフォールバック | 成果物欠落 |
| UT-11 | _extract_phase_outputs_Issue取得エラー | Issue取得失敗 |
| UT-17 | ReportPhase_execute_PR未発見時のスキップ | PR未発見 |
| UT-18 | ReportPhase_execute_PR更新失敗時の継続 | PR更新失敗 |
| UT-19 | ReportPhase_execute_予期しない例外時の継続 | 予期しない例外 |
| IT-03 | E2Eフロー_PR未発見_スキップ | PR未発見時のスキップ動作 |
| IT-04 | E2Eフロー_成果物一部欠落_デフォルト値使用 | 成果物欠落時のリカバリー |
| IT-05 | E2Eフロー_GitHub API制限到達_継続 | API制限時のリカバリー |
| IT-08 | エラーリカバリー_テンプレート読み込み失敗 | テンプレートエラー時のリカバリー |
| IT-09 | エラーリカバリー_Issue取得失敗 | Issue取得エラー時のリカバリー |

- **判定**: ✅ **PASS** - 主要な異常系が全てカバーされている

---

### ✅ 期待結果が明確である

#### 各テストケースの期待結果の明確性

**ユニットテスト**:
- 各テストケースに「期待結果」セクションが含まれている
- 戻り値、例外、ログ出力が具体的に記載されている
- 検証項目（assert文の内容）が明確に記載されている

**例（UT-01）**:
```python
期待結果:
{
    'success': True,
    'error': None
}

検証項目:
- pr.edit(body=body) が1回呼び出される
- 戻り値が {'success': True, 'error': None} である
```

**インテグレーションテスト**:
- 各テストケースに「期待結果」と「確認項目」が含まれている
- チェックリスト形式で検証項目が列挙されている
- ログ出力、ファイル生成、APIリクエストが具体的に記載されている

**例（IT-01）**:
```
期待結果:
- report.md が正常に生成される
- PR #123の本文が詳細版に更新される
- 成功ログ "[INFO] PR本文の更新に成功しました: PR #123" が出力される
- Phase 8のステータスが completed になる

確認項目:
- [ ] report.md が生成されている
- [ ] PR本文に以下の情報が含まれている:
  - [ ] 関連Issue（Closes #363）
  - [ ] 変更サマリー
  - [ ] （以下省略）
```

- **判定**: ✅ **PASS** - 全てのテストケースで期待結果が明確に記載されている

---

## 品質ゲート総合判定

| 品質ゲート項目 | 判定 |
|--------------|------|
| Phase 2の戦略に沿ったテストシナリオである | ✅ PASS |
| 主要な正常系がカバーされている | ✅ PASS |
| 主要な異常系がカバーされている | ✅ PASS |
| 期待結果が明確である | ✅ PASS |

### 総合判定: ✅ **全ての品質ゲートをPASS**

---

## まとめ

本テストシナリオは、Phase 2で決定された **UNIT_INTEGRATION** テスト戦略に基づき、以下の範囲をカバーしています：

### テストケース数
- **ユニットテスト**: 19ケース
  - `update_pull_request()`: 5ケース
  - `_generate_pr_body_detailed()`: 3ケース
  - `_extract_phase_outputs()`: 3ケース
  - `_extract_section()`: 3ケース
  - `ReportPhase.execute()`: 5ケース

- **インテグレーションテスト**: 9ケース
  - E2Eフロー: 5ケース
  - GitHub API連携: 2ケース
  - エラーリカバリー: 2ケース

### カバレッジ
- **正常系**: 7ケース（主要な機能動作を検証）
- **異常系**: 16ケース（エラーハンドリングを検証）
- **境界値**: 5ケース（エッジケースを検証）

### 品質保証
- **Phase 2戦略準拠**: ✅ UNIT_INTEGRATION戦略に完全準拠
- **要件カバレッジ**: ✅ 要件定義書の全機能要件をカバー
- **実行可能性**: ✅ 全テストケースが実装可能で実行可能
- **品質ゲート**: ✅ 4つの必須要件を全て満たす

本テストシナリオに基づいて、Phase 5（Test Implementation）でテストコードを実装することで、Issue #363の機能が高品質で実装されることが保証されます。
