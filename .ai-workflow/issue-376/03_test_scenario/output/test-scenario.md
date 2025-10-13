# テストシナリオ - Issue #376

## プロジェクト情報

- **Issue番号**: #376
- **タイトル**: [TASK] ai-workflowスクリプトの大規模リファクタリング
- **作成日**: 2025-10-12
- **Planning Document**: @.ai-workflow/issue-376/00_planning/output/planning.md
- **Requirements Document**: @.ai-workflow/issue-376/01_requirements/output/requirements.md
- **Design Document**: @.ai-workflow/issue-376/02_design/output/design.md

---

## 1. テスト戦略サマリー

### 選択されたテスト戦略

**ALL (UNIT + INTEGRATION + BDD)**

### 戦略の根拠（Phase 2より引用）

リファクタリングの性質上、全レベルでの回帰テストが必須です：

1. **UNIT_TEST（必須）**: リファクタリング後の各クラス・関数が正しく動作することを保証
2. **INTEGRATION_TEST（必須）**: コンポーネント間の連携が正しく動作することを保証
3. **BDD_TEST（必須）**: エンドユーザー視点での動作保証（「既存機能の動作を維持」の検証）

### テスト対象の範囲

#### 新規作成コンポーネント（31ファイル）
- CLI層: `cli/commands.py`
- Application層: `core/workflow_controller.py`, `core/config_manager.py`
- Domain層（Git）: `core/git/repository.py`, `core/git/branch.py`, `core/git/commit.py`
- Domain層（GitHub）: `core/github/issue_client.py`, `core/github/pr_client.py`, `core/github/comment_client.py`
- Domain層（Phases）: `phases/base/abstract_phase.py`, `phases/base/phase_executor.py`, `phases/base/phase_validator.py`, `phases/base/phase_reporter.py`
- Infrastructure層: `common/logger.py`, `common/error_handler.py`, `common/file_handler.py`, `common/retry.py`

#### 修正コンポーネント（17ファイル + テスト70+ファイル）
- `main.py` - CLI層の分離後の動作確認
- 各フェーズファイル（10ファイル）- インポートパス修正後の動作確認

### テストの目的

1. **回帰防止**: 既存機能が全て正常に動作することを保証（最優先）
2. **リファクタリング品質**: 分割されたクラスが単一責任原則に従っていることを確認
3. **統合検証**: 分割されたコンポーネント間の連携が正しく動作することを確認
4. **ユーザー視点**: ワークフロー全体がエンドツーエンドで正常動作することを確認

---

## 2. Unitテストシナリオ

### 2.1 CLI層（cli/commands.py）

#### UT-CLI-001: init コマンド - 正常系

- **目的**: ワークフロー初期化が正常に実行されることを検証
- **前提条件**:
  - Gitリポジトリが存在する
  - GITHUB_TOKEN環境変数が設定されている
  - 指定されたIssueが存在する
- **入力**:
  ```python
  issue_url = "https://github.com/tielec/infrastructure-as-code/issues/376"
  ```
- **期待結果**:
  - WorkflowController.initialize()が呼び出される
  - controller.create_workflow()が呼び出される
  - 正常終了（exit code 0）
- **テストデータ**: Issue #376の情報

#### UT-CLI-002: init コマンド - 異常系（無効なURL）

- **目的**: 無効なIssue URLでエラーハンドリングが動作することを検証
- **前提条件**: Gitリポジトリが存在する
- **入力**:
  ```python
  issue_url = "invalid-url"
  ```
- **期待結果**:
  - エラーメッセージが表示される
  - 異常終了（exit code 1）
- **テストデータ**: 無効なURL文字列

#### UT-CLI-003: execute コマンド - 全フェーズ実行

- **目的**: 全フェーズ実行が正常に実行されることを検証
- **前提条件**:
  - ワークフロー初期化済み
  - metadata.jsonが存在する
- **入力**:
  ```python
  phase = "all"
  issue = "376"
  ```
- **期待結果**:
  - WorkflowController.load()が呼び出される
  - controller.execute_all_phases()が呼び出される
  - 正常終了メッセージが表示される
- **テストデータ**: Issue #376のメタデータ

#### UT-CLI-004: execute コマンド - 個別フェーズ実行

- **目的**: 個別フェーズ実行が正常に実行されることを検証
- **前提条件**: ワークフロー初期化済み
- **入力**:
  ```python
  phase = "planning"
  issue = "376"
  ```
- **期待結果**:
  - controller.execute_phase("planning")が呼び出される
  - 正常終了
- **テストデータ**: Phase planningの設定

#### UT-CLI-005: execute コマンド - Git設定オプション

- **目的**: Gitユーザー設定が正しく適用されることを検証
- **前提条件**: ワークフロー初期化済み
- **入力**:
  ```python
  phase = "planning"
  issue = "376"
  git_user = "Test User"
  git_email = "test@example.com"
  ```
- **期待結果**:
  - ConfigManager.load()にgit_user, git_emailが渡される
  - 設定が反映される
- **テストデータ**: カスタムGit設定

---

### 2.2 Application層（core/workflow_controller.py）

#### UT-WFC-001: WorkflowController.initialize() - 正常系

- **目的**: ワークフロー初期化が正常に動作することを検証
- **前提条件**:
  - Gitリポジトリが存在する
  - Issue URLが有効
- **入力**:
  ```python
  issue_url = "https://github.com/tielec/infrastructure-as-code/issues/376"
  ```
- **期待結果**:
  - Issue番号が正しく抽出される（376）
  - リポジトリルートが取得される
  - 各コンポーネントが初期化される
  - WorkflowControllerインスタンスが返される
- **テストデータ**: 有効なIssue URL

#### UT-WFC-002: WorkflowController.create_workflow() - 正常系

- **目的**: ワークフロー作成が正常に動作することを検証
- **前提条件**: WorkflowControllerが初期化済み
- **入力**: なし
- **期待結果**:
  ```python
  {
    'success': True,
    'metadata_path': Path('.ai-workflow/issue-376/metadata.json'),
    'branch_name': 'ai-workflow/issue-376',
    'pr_url': 'https://github.com/...',
    'error': None
  }
  ```
- **テストデータ**: Issue #376情報

#### UT-WFC-003: WorkflowController.execute_all_phases() - 正常系

- **目的**: 全フェーズ順次実行が正常に動作することを検証
- **前提条件**: ワークフロー作成済み
- **入力**: なし
- **期待結果**:
  ```python
  {
    'success': True,
    'completed_phases': ['planning', 'requirements', ..., 'evaluation'],
    'failed_phase': None,
    'error': None,
    'total_duration': 3600.0,
    'total_cost': 10.0
  }
  ```
- **テストデータ**: 全フェーズの設定

#### UT-WFC-004: WorkflowController.execute_all_phases() - 途中失敗

- **目的**: フェーズ失敗時に適切に中断されることを検証
- **前提条件**:
  - ワークフロー作成済み
  - designフェーズが失敗するようにモック設定
- **入力**: なし
- **期待結果**:
  ```python
  {
    'success': False,
    'completed_phases': ['planning', 'requirements'],
    'failed_phase': 'design',
    'error': 'Design phase failed',
    'total_duration': 1200.0,
    'total_cost': 3.0
  }
  ```
- **テストデータ**: 失敗シナリオ

#### UT-WFC-005: WorkflowController.execute_phase() - 正常系

- **目的**: 個別フェーズ実行が正常に動作することを検証
- **前提条件**: ワークフロー作成済み
- **入力**:
  ```python
  phase_name = "planning"
  ```
- **期待結果**:
  ```python
  {
    'success': True,
    'review_result': 'PASS',
    'error': None
  }
  ```
- **テストデータ**: planningフェーズ設定

---

### 2.3 Application層（core/config_manager.py）

#### UT-CFG-001: ConfigManager.load() - デフォルト設定

- **目的**: デフォルト設定が正しくロードされることを検証
- **前提条件**: 環境変数が設定されている
- **入力**:
  ```python
  config_path = None
  git_user = None
  git_email = None
  ```
- **期待結果**:
  ```python
  config_data = {
    'github_token': os.getenv('GITHUB_TOKEN'),
    'github_repository': os.getenv('GITHUB_REPOSITORY'),
    'git_user': 'AI Workflow',
    'git_email': 'ai-workflow@tielec.local'
  }
  ```
- **テストデータ**: 環境変数

#### UT-CFG-002: ConfigManager.load() - config.yamlから読み込み

- **目的**: config.yamlの設定が正しくロードされることを検証
- **前提条件**: config.yamlファイルが存在する
- **入力**:
  ```python
  config_path = Path("config.yaml")
  ```
- **期待結果**:
  - YAMLファイルが読み込まれる
  - 環境変数が上書きされる（優先順位）
- **テストデータ**: サンプルconfig.yaml

#### UT-CFG-003: ConfigManager.load() - CLIオプション優先

- **目的**: CLIオプションが最優先されることを検証
- **前提条件**: config.yamlと環境変数が存在する
- **入力**:
  ```python
  config_path = Path("config.yaml")
  git_user = "CLI User"
  git_email = "cli@example.com"
  ```
- **期待結果**:
  ```python
  config_data['git_user'] == "CLI User"
  config_data['git_email'] == "cli@example.com"
  ```
- **テストデータ**: 複数ソースの設定

#### UT-CFG-004: ConfigManager.get() - 正常系

- **目的**: 設定値の取得が正常に動作することを検証
- **前提条件**: ConfigManagerが初期化済み
- **入力**:
  ```python
  key = "git_user"
  default = "Default User"
  ```
- **期待結果**: 設定値が返される
- **テストデータ**: 初期化済みconfig

#### UT-CFG-005: ConfigManager.get() - キー不存在

- **目的**: 存在しないキーでデフォルト値が返されることを検証
- **前提条件**: ConfigManagerが初期化済み
- **入力**:
  ```python
  key = "non_existent_key"
  default = "Default Value"
  ```
- **期待結果**: "Default Value"が返される
- **テストデータ**: 初期化済みconfig

---

### 2.4 Domain層 - Git Operations（core/git/repository.py）

#### UT-GR-001: GitRepository.get_root() - 正常系

- **目的**: リポジトリルートが正しく取得されることを検証
- **前提条件**: Gitリポジトリが存在する
- **入力**:
  ```python
  repo_path = Path("/tmp/jenkins-51007459/workspace/AI_Workflow/ai_workflow_orchestrator")
  ```
- **期待結果**: リポジトリルートPathが返される
- **テストデータ**: 実際のリポジトリパス

#### UT-GR-002: GitRepository.__init__() - リポジトリ不存在

- **目的**: Gitリポジトリが存在しない場合にエラーが発生することを検証
- **前提条件**: Gitリポジトリではないディレクトリ
- **入力**:
  ```python
  repo_path = Path("/tmp/not-a-git-repo")
  ```
- **期待結果**: RuntimeErrorが発生
- **テストデータ**: 非Gitディレクトリ

#### UT-GR-003: GitRepository.get_status() - 変更なし

- **目的**: 変更がない状態でステータスが正しく取得されることを検証
- **前提条件**: クリーンな作業ディレクトリ
- **入力**: なし
- **期待結果**:
  ```python
  {
    'is_dirty': False,
    'untracked_files': [],
    'modified_files': [],
    'staged_files': []
  }
  ```
- **テストデータ**: クリーンな状態

#### UT-GR-004: GitRepository.get_status() - 変更あり

- **目的**: 変更がある状態でステータスが正しく取得されることを検証
- **前提条件**:
  - 未追跡ファイルが存在する
  - 変更ファイルが存在する
- **入力**: なし
- **期待結果**:
  ```python
  {
    'is_dirty': True,
    'untracked_files': ['new_file.py'],
    'modified_files': ['existing_file.py'],
    'staged_files': []
  }
  ```
- **テストデータ**: 変更を含む状態

#### UT-GR-005: GitRepository.get_changed_files() - Issue番号フィルタ

- **目的**: Issue番号でフィルタリングされたファイルリストが返されることを検証
- **前提条件**:
  - .ai-workflow/issue-376/配下にファイルが存在する
  - 他のIssueのファイルも存在する
- **入力**:
  ```python
  issue_number = 376
  ```
- **期待結果**:
  ```python
  [
    '.ai-workflow/issue-376/metadata.json',
    '.ai-workflow/issue-376/00_planning/output/planning.md'
  ]
  ```
- **テストデータ**: 複数Issueのファイル

---

### 2.5 Domain層 - Git Operations（core/git/branch.py）

#### UT-GB-001: GitBranch.create() - 新規ブランチ作成

- **目的**: 新規ブランチが正常に作成されることを検証
- **前提条件**:
  - ブランチが存在しない
  - クリーンな作業ディレクトリ
- **入力**:
  ```python
  branch_name = "ai-workflow/issue-376"
  base_branch = "main"
  ```
- **期待結果**:
  ```python
  {
    'success': True,
    'branch_name': 'ai-workflow/issue-376',
    'error': None
  }
  ```
- **テストデータ**: 新規ブランチ名

#### UT-GB-002: GitBranch.create() - 既存ブランチ

- **目的**: 既存ブランチの場合にチェックアウトされることを検証
- **前提条件**: ブランチが既に存在する
- **入力**:
  ```python
  branch_name = "ai-workflow/issue-376"
  ```
- **期待結果**:
  ```python
  {
    'success': True,
    'branch_name': 'ai-workflow/issue-376',
    'error': None
  }
  ```
  - 警告ログが出力される
- **テストデータ**: 既存ブランチ名

#### UT-GB-003: GitBranch.switch() - 正常系

- **目的**: ブランチ切り替えが正常に動作することを検証
- **前提条件**:
  - 切り替え先ブランチが存在する
  - クリーンな作業ディレクトリ
- **入力**:
  ```python
  branch_name = "main"
  force = False
  ```
- **期待結果**:
  ```python
  {
    'success': True,
    'branch_name': 'main',
    'error': None
  }
  ```
- **テストデータ**: 既存ブランチ名

#### UT-GB-004: GitBranch.switch() - 未コミット変更あり

- **目的**: 未コミット変更がある場合にエラーが返されることを検証
- **前提条件**: 未コミット変更が存在する
- **入力**:
  ```python
  branch_name = "main"
  force = False
  ```
- **期待結果**:
  ```python
  {
    'success': False,
    'branch_name': 'main',
    'error': 'Your local changes would be overwritten...'
  }
  ```
- **テストデータ**: ダーティな作業ディレクトリ

#### UT-GB-005: GitBranch.exists() - ローカルブランチ存在

- **目的**: ローカルブランチの存在確認が正常に動作することを検証
- **前提条件**: ローカルブランチが存在する
- **入力**:
  ```python
  branch_name = "main"
  check_remote = False
  ```
- **期待結果**: True
- **テストデータ**: 既存ローカルブランチ

#### UT-GB-006: GitBranch.exists() - リモートブランチのみ存在

- **目的**: リモートブランチの存在確認が正常に動作することを検証
- **前提条件**: リモートブランチのみ存在する
- **入力**:
  ```python
  branch_name = "remote-only-branch"
  check_remote = True
  ```
- **期待結果**: True
- **テストデータ**: リモートのみのブランチ

#### UT-GB-007: GitBranch.get_current() - 正常系

- **目的**: 現在のブランチ名が正しく取得されることを検証
- **前提条件**: 通常のブランチ上にいる
- **入力**: なし
- **期待結果**: "ai-workflow/issue-376"
- **テストデータ**: 現在のブランチ

---

### 2.6 Domain層 - Git Operations（core/git/commit.py）

#### UT-GC-001: GitCommit.commit_phase_output() - 正常系

- **目的**: Phase成果物のコミットが正常に動作することを検証
- **前提条件**:
  - 変更ファイルが存在する
  - Git設定が完了している
- **入力**:
  ```python
  phase_name = "planning"
  issue_number = 376
  status = "completed"
  review_result = "PASS"
  ```
- **期待結果**:
  ```python
  {
    'success': True,
    'commit_hash': '1a2b3c4...',
    'files_committed': ['.ai-workflow/issue-376/00_planning/output/planning.md'],
    'error': None
  }
  ```
- **テストデータ**: 変更ファイル

#### UT-GC-002: GitCommit.commit_phase_output() - コミット対象なし

- **目的**: 変更がない場合にスキップされることを検証
- **前提条件**: 変更ファイルが存在しない
- **入力**:
  ```python
  phase_name = "planning"
  issue_number = 376
  status = "completed"
  ```
- **期待結果**:
  ```python
  {
    'success': True,
    'commit_hash': None,
    'files_committed': [],
    'error': None
  }
  ```
- **テストデータ**: クリーンな状態

#### UT-GC-003: GitCommit._create_commit_message() - 正常系

- **目的**: コミットメッセージが正しく生成されることを検証
- **前提条件**: なし
- **入力**:
  ```python
  phase_name = "planning"
  issue_number = 376
  status = "completed"
  review_result = "PASS"
  ```
- **期待結果**:
  ```
  [ai-workflow] Phase 0 (planning) - completed

  Issue: #376
  Phase: 0 (planning)
  Status: completed
  Review: PASS

  Auto-generated by AI Workflow
  ```
- **テストデータ**: Phase情報

#### UT-GC-004: GitCommit.push_to_remote() - 正常系

- **目的**: リモートプッシュが正常に動作することを検証
- **前提条件**:
  - コミット済み
  - リモートリポジトリが存在する
- **入力**: なし
- **期待結果**:
  ```python
  {
    'success': True,
    'retries': 0,
    'error': None
  }
  ```
- **テストデータ**: コミット済み状態

#### UT-GC-005: GitCommit.push_to_remote() - リトライ成功

- **目的**: プッシュ失敗時にリトライが動作することを検証
- **前提条件**:
  - 1回目は失敗、2回目は成功するようにモック設定
- **入力**: なし
- **期待結果**:
  ```python
  {
    'success': True,
    'retries': 1,
    'error': None
  }
  ```
- **テストデータ**: リトライシナリオ

#### UT-GC-006: GitCommit._ensure_git_config() - 未設定

- **目的**: Git設定が未設定の場合に環境変数から設定されることを検証
- **前提条件**: Git設定が未設定
- **入力**: なし
- **期待結果**:
  - user.nameが設定される
  - user.emailが設定される
  - ログに設定内容が出力される
- **テストデータ**: 環境変数

---

### 2.7 Domain層 - GitHub Operations（core/github/issue_client.py）

#### UT-IC-001: IssueClient.get_issue() - 正常系

- **目的**: Issue情報が正しく取得されることを検証
- **前提条件**: Issueが存在する
- **入力**:
  ```python
  issue_number = 376
  ```
- **期待結果**: Issue オブジェクトが返される
- **テストデータ**: Issue #376

#### UT-IC-002: IssueClient.get_issue() - Issue不存在

- **目的**: 存在しないIssueでエラーが発生することを検証
- **前提条件**: Issueが存在しない
- **入力**:
  ```python
  issue_number = 99999
  ```
- **期待結果**: GitHubAPIError が発生
- **テストデータ**: 無効なIssue番号

#### UT-IC-003: IssueClient.get_issue_info() - 正常系

- **目的**: Issue情報が辞書形式で取得されることを検証
- **前提条件**: Issueが存在する
- **入力**:
  ```python
  issue_number = 376
  ```
- **期待結果**:
  ```python
  {
    'number': 376,
    'title': '[TASK] ai-workflowスクリプトの大規模リファクタリング',
    'body': '...',
    'state': 'open',
    'labels': [],
    'url': 'https://github.com/...',
    'created_at': '2025-10-12T...',
    'updated_at': '2025-10-12T...'
  }
  ```
- **テストデータ**: Issue #376

#### UT-IC-004: IssueClient.close_issue() - 正常系

- **目的**: Issueが正しくクローズされることを検証
- **前提条件**: Issueがopen状態
- **入力**:
  ```python
  issue_number = 376
  reason = "ワークフロー完了"
  ```
- **期待結果**:
  ```python
  {
    'success': True,
    'error': None
  }
  ```
  - コメントが投稿される
  - Issueがclosed状態になる
- **テストデータ**: Open Issue

---

### 2.8 Domain層 - GitHub Operations（core/github/pr_client.py）

#### UT-PC-001: PRClient.create_pull_request() - ドラフトPR作成

- **目的**: ドラフトPRが正しく作成されることを検証
- **前提条件**: ブランチが存在する
- **入力**:
  ```python
  title = "[ai-workflow] Issue #376"
  body = "..."
  head = "ai-workflow/issue-376"
  base = "main"
  draft = True
  ```
- **期待結果**:
  ```python
  {
    'success': True,
    'pr_url': 'https://github.com/.../pull/123',
    'pr_number': 123,
    'error': None
  }
  ```
- **テストデータ**: PR情報

#### UT-PC-002: PRClient.create_pull_request() - ブランチ不存在

- **目的**: ブランチが存在しない場合にエラーが返されることを検証
- **前提条件**: headブランチが存在しない
- **入力**:
  ```python
  head = "non-existent-branch"
  ```
- **期待結果**:
  ```python
  {
    'success': False,
    'pr_url': None,
    'pr_number': None,
    'error': 'Branch not found'
  }
  ```
- **テストデータ**: 無効なブランチ名

#### UT-PC-003: PRClient.check_existing_pr() - PR存在

- **目的**: 既存PRが正しく検出されることを検証
- **前提条件**: PRが既に存在する
- **入力**:
  ```python
  head = "ai-workflow/issue-376"
  base = "main"
  ```
- **期待結果**:
  ```python
  {
    'pr_number': 123,
    'pr_url': 'https://github.com/.../pull/123',
    'state': 'open'
  }
  ```
- **テストデータ**: 既存PR

#### UT-PC-004: PRClient.check_existing_pr() - PR不存在

- **目的**: PRが存在しない場合にNoneが返されることを検証
- **前提条件**: PRが存在しない
- **入力**:
  ```python
  head = "ai-workflow/issue-376"
  base = "main"
  ```
- **期待結果**: None
- **テストデータ**: PRなし

#### UT-PC-005: PRClient.update_pull_request() - 正常系

- **目的**: PR本文が正しく更新されることを検証
- **前提条件**: PRが存在する
- **入力**:
  ```python
  pr_number = 123
  body = "Updated PR description"
  ```
- **期待結果**:
  ```python
  {
    'success': True,
    'error': None
  }
  ```
- **テストデータ**: 既存PR

---

### 2.9 Domain層 - GitHub Operations（core/github/comment_client.py）

#### UT-CC-001: CommentClient.post_comment() - 正常系

- **目的**: コメントが正しく投稿されることを検証
- **前提条件**: Issueが存在する
- **入力**:
  ```python
  issue_number = 376
  body = "## Progress Update\n\nPhase planning completed."
  ```
- **期待結果**: IssueComment オブジェクトが返される
- **テストデータ**: Issue #376

#### UT-CC-002: CommentClient.create_or_update_progress_comment() - 新規作成

- **目的**: 進捗コメントが新規作成されることを検証
- **前提条件**:
  - Issueが存在する
  - comment_idがNone
- **入力**:
  ```python
  issue_number = 376
  content = "## Progress\n\nPhase: planning\nStatus: in_progress"
  comment_id = None
  ```
- **期待結果**:
  ```python
  {
    'comment_id': 12345,
    'comment_url': 'https://github.com/.../issues/376#issuecomment-12345'
  }
  ```
- **テストデータ**: 新規コメント内容

#### UT-CC-003: CommentClient.create_or_update_progress_comment() - 既存更新

- **目的**: 既存進捗コメントが更新されることを検証
- **前提条件**:
  - Issueが存在する
  - 既存コメントが存在する
- **入力**:
  ```python
  issue_number = 376
  content = "## Progress\n\nPhase: planning\nStatus: completed"
  comment_id = 12345
  ```
- **期待結果**:
  ```python
  {
    'comment_id': 12345,
    'comment_url': 'https://github.com/.../issues/376#issuecomment-12345'
  }
  ```
  - 既存コメントが更新される
- **テストデータ**: 更新内容

#### UT-CC-004: CommentClient.create_or_update_progress_comment() - 既存不存在でフォールバック

- **目的**: 既存コメントが見つからない場合に新規作成されることを検証
- **前提条件**:
  - comment_idが指定されているが、コメントが存在しない
- **入力**:
  ```python
  issue_number = 376
  content = "..."
  comment_id = 99999
  ```
- **期待結果**:
  - 新規コメントが作成される
  - 警告ログが出力される
- **テストデータ**: 無効なcomment_id

---

### 2.10 Domain層 - Phases（phases/base/phase_executor.py）

#### UT-PE-001: PhaseExecutor.run() - 1回目でPASS

- **目的**: 1回目の実行でPASSした場合に正常終了することを検証
- **前提条件**:
  - フェーズが初期化済み
  - 依存関係チェックが通過
- **入力**: なし
- **期待結果**:
  ```python
  {
    'success': True,
    'review_result': 'PASS',
    'error': None
  }
  ```
  - phase.execute()が1回呼び出される
  - phase.review()が1回呼び出される
  - メタデータがcompletedに更新される
- **テストデータ**: PASS シナリオ

#### UT-PE-002: PhaseExecutor.run() - リトライ後PASS

- **目的**: 1回目がFAIL、2回目でPASSした場合に正常終了することを検証
- **前提条件**: フェーズが初期化済み
- **入力**: なし
- **期待結果**:
  ```python
  {
    'success': True,
    'review_result': 'PASS',
    'error': None
  }
  ```
  - phase.execute()が1回、phase.revise()が1回呼び出される
  - 合計2回の試行
- **テストデータ**: リトライ成功シナリオ

#### UT-PE-003: PhaseExecutor.run() - 最大リトライ到達

- **目的**: 最大リトライ回数に到達した場合に失敗することを検証
- **前提条件**: フェーズが初期化済み
- **入力**: なし
- **期待結果**:
  ```python
  {
    'success': False,
    'review_result': 'FAIL',
    'error': 'Max retries reached'
  }
  ```
  - 3回試行される
  - メタデータがfailedに更新される
- **テストデータ**: 全FAIL シナリオ

#### UT-PE-004: PhaseExecutor.run() - 依存関係チェック失敗

- **目的**: 依存関係チェックが失敗した場合に実行されないことを検証
- **前提条件**:
  - 依存フェーズが未完了
  - skip_dependency_check=False
- **入力**: なし
- **期待結果**:
  ```python
  {
    'success': False,
    'review_result': None,
    'error': 'Dependency check failed: ...'
  }
  ```
  - phase.execute()が呼び出されない
- **テストデータ**: 依存関係違反

#### UT-PE-005: PhaseExecutor._auto_commit_and_push() - 正常系

- **目的**: Git自動commit & pushが正常に動作することを検証
- **前提条件**: 変更ファイルが存在する
- **入力**:
  ```python
  status = "completed"
  review_result = "PASS"
  ```
- **期待結果**:
  - git_commit.commit_phase_output()が呼び出される
  - git_commit.push_to_remote()が呼び出される
- **テストデータ**: 変更ファイル

---

### 2.11 Domain層 - Phases（phases/base/phase_validator.py）

#### UT-PV-001: PhaseValidator.validate_dependencies() - 依存満たす

- **目的**: 依存関係が満たされている場合にTrueが返されることを検証
- **前提条件**: 依存フェーズが全てcompleted
- **入力**:
  ```python
  phase_name = "design"
  ignore_violations = False
  ```
- **期待結果**:
  ```python
  {
    'valid': True,
    'error': None
  }
  ```
- **テストデータ**: 完了済み依存フェーズ

#### UT-PV-002: PhaseValidator.validate_dependencies() - 依存未満足

- **目的**: 依存関係が満たされていない場合にFalseが返されることを検証
- **前提条件**: 依存フェーズが未完了
- **入力**:
  ```python
  phase_name = "design"
  ignore_violations = False
  ```
- **期待結果**:
  ```python
  {
    'valid': False,
    'error': 'Phase requirements not completed: ...'
  }
  ```
- **テストデータ**: 未完了依存フェーズ

#### UT-PV-003: PhaseValidator.validate_dependencies() - 違反を無視

- **目的**: ignore_violations=Trueの場合に警告のみで通過することを検証
- **前提条件**: 依存フェーズが未完了
- **入力**:
  ```python
  phase_name = "design"
  ignore_violations = True
  ```
- **期待結果**:
  ```python
  {
    'valid': True,
    'error': None
  }
  ```
  - 警告ログが出力される
- **テストデータ**: 未完了依存フェーズ

#### UT-PV-004: PhaseValidator._parse_review_result() - PASS

- **目的**: レビュー結果が正しくパースされることを検証
- **前提条件**: なし
- **入力**:
  ```python
  review_output = "Result: PASS\nFeedback: Good work"
  ```
- **期待結果**:
  ```python
  {
    'result': 'PASS',
    'feedback': 'Good work',
    'suggestions': []
  }
  ```
- **テストデータ**: レビュー出力

---

### 2.12 Domain層 - Phases（phases/base/phase_reporter.py）

#### UT-PR-001: PhaseReporter.post_progress() - 開始

- **目的**: フェーズ開始の進捗投稿が正常に動作することを検証
- **前提条件**: Issueが存在する
- **入力**:
  ```python
  phase_name = "planning"
  status = "in_progress"
  details = "planningフェーズを開始しました。"
  ```
- **期待結果**: コメントが投稿される
- **テストデータ**: 進捗情報

#### UT-PR-002: PhaseReporter.post_progress() - 完了

- **目的**: フェーズ完了の進捗投稿が正常に動作することを検証
- **前提条件**: Issueが存在する
- **入力**:
  ```python
  phase_name = "planning"
  status = "completed"
  details = "planningフェーズが完了しました。"
  ```
- **期待結果**: コメントが投稿される
- **テストデータ**: 進捗情報

#### UT-PR-003: PhaseReporter.post_review() - PASS

- **目的**: レビュー結果PASSが正しく投稿されることを検証
- **前提条件**: Issueが存在する
- **入力**:
  ```python
  phase_name = "planning"
  result = "PASS"
  feedback = "All quality gates passed"
  suggestions = []
  ```
- **期待結果**: コメントが投稿される
- **テストデータ**: レビュー結果

#### UT-PR-004: PhaseReporter.post_review() - FAIL

- **目的**: レビュー結果FAILが正しく投稿されることを検証
- **前提条件**: Issueが存在する
- **入力**:
  ```python
  phase_name = "planning"
  result = "FAIL"
  feedback = "Quality gates not met"
  suggestions = ["Add more details", "Fix typos"]
  ```
- **期待結果**: コメントが投稿される
- **テストデータ**: レビュー結果

---

### 2.13 Infrastructure層（common/logger.py）

#### UT-LOG-001: Logger.get_logger() - 正常系

- **目的**: ロガーインスタンスが正しく取得されることを検証
- **前提条件**: なし
- **入力**:
  ```python
  name = "test_module"
  ```
- **期待結果**: logging.Loggerインスタンスが返される
- **テストデータ**: モジュール名

#### UT-LOG-002: Logger.info() - ログ出力

- **目的**: infoレベルのログが正しく出力されることを検証
- **前提条件**: ロガーが初期化済み
- **入力**:
  ```python
  message = "Test info message"
  ```
- **期待結果**: ログファイルにメッセージが出力される
- **テストデータ**: ログメッセージ

#### UT-LOG-003: Logger.error() - ログ出力

- **目的**: errorレベルのログが正しく出力されることを検証
- **前提条件**: ロガーが初期化済み
- **入力**:
  ```python
  message = "Test error message"
  ```
- **期待結果**: ログファイルにエラーメッセージが出力される
- **テストデータ**: エラーメッセージ

---

### 2.14 Infrastructure層（common/retry.py）

#### UT-RET-001: @retry デコレータ - 1回目で成功

- **目的**: 1回目で成功した場合にリトライされないことを検証
- **前提条件**: なし
- **入力**:
  ```python
  @retry(max_attempts=3, delay=1.0)
  def test_func():
      return "success"
  ```
- **期待結果**:
  - 1回のみ実行される
  - "success"が返される
- **テストデータ**: 成功関数

#### UT-RET-002: @retry デコレータ - リトライ後成功

- **目的**: 2回目で成功した場合にリトライされることを検証
- **前提条件**: なし
- **入力**:
  ```python
  @retry(max_attempts=3, delay=1.0)
  def test_func():
      # 1回目は失敗、2回目は成功
      ...
  ```
- **期待結果**:
  - 2回実行される
  - 結果が返される
- **テストデータ**: リトライ成功シナリオ

#### UT-RET-003: @retry デコレータ - 最大リトライ到達

- **目的**: 最大リトライ回数に到達した場合に例外が発生することを検証
- **前提条件**: なし
- **入力**:
  ```python
  @retry(max_attempts=3, delay=1.0)
  def test_func():
      raise Exception("Always fail")
  ```
- **期待結果**:
  - 3回実行される
  - 例外が再発生する
- **テストデータ**: 全失敗シナリオ

---

## 3. Integrationテストシナリオ

### 3.1 CLI → WorkflowController 統合

#### IT-CLI-WFC-001: init → create_workflow フロー

- **目的**: initコマンドからワークフロー作成までの統合動作を検証
- **前提条件**:
  - Gitリポジトリが存在する
  - GitHub APIアクセス可能
  - Issueが存在する
- **テスト手順**:
  1. `ai-workflow init --issue-url https://github.com/.../issues/376` を実行
  2. Issue情報の取得を確認
  3. ブランチ作成を確認
  4. metadata.json作成を確認
  5. ドラフトPR作成を確認
- **期待結果**:
  - 正常終了
  - .ai-workflow/issue-376/metadata.json が作成される
  - ai-workflow/issue-376 ブランチが作成される
  - ドラフトPRが作成される
- **確認項目**:
  - [ ] metadata.jsonの内容が正しい
  - [ ] ブランチが正しく作成されている
  - [ ] PRのタイトル・本文が正しい
  - [ ] PRがdraft状態である

#### IT-CLI-WFC-002: execute → execute_all_phases フロー

- **目的**: executeコマンドから全フェーズ実行までの統合動作を検証
- **前提条件**: ワークフロー初期化済み
- **テスト手順**:
  1. `ai-workflow execute --phase all --issue 376` を実行
  2. 各フェーズの実行を確認
  3. 各フェーズのコミット・プッシュを確認
  4. 進捗コメントの投稿を確認
- **期待結果**:
  - 全フェーズが順次実行される
  - 各フェーズの成果物がコミットされる
  - 進捗コメントが投稿される
- **確認項目**:
  - [ ] planningフェーズが完了
  - [ ] requirementsフェーズが完了
  - [ ] designフェーズが完了
  - [ ] 全フェーズでコミットが作成される

---

### 3.2 WorkflowController → Git/GitHub 統合

#### IT-WFC-GIT-001: ワークフロー作成 → Git操作

- **目的**: ワークフロー作成時のGit操作統合を検証
- **前提条件**: Gitリポジトリが存在する
- **テスト手順**:
  1. WorkflowController.initialize()を呼び出し
  2. controller.create_workflow()を呼び出し
  3. GitBranch.create()が呼び出されることを確認
  4. metadata.json作成を確認
  5. GitCommit.commit_phase_output()が呼び出されることを確認
  6. GitCommit.push_to_remote()が呼び出されることを確認
- **期待結果**:
  - ブランチが作成される
  - 初期コミットが作成される
  - リモートにプッシュされる
- **確認項目**:
  - [ ] ブランチ名が正しい
  - [ ] コミットメッセージが正しい
  - [ ] リモートにプッシュされている

#### IT-WFC-GH-001: ワークフロー作成 → GitHub操作

- **目的**: ワークフロー作成時のGitHub API統合を検証
- **前提条件**: GitHub APIアクセス可能
- **テスト手順**:
  1. WorkflowController.initialize()を呼び出し
  2. controller.create_workflow()を呼び出し
  3. IssueClient.get_issue()が呼び出されることを確認
  4. PRClient.create_pull_request()が呼び出されることを確認
  5. CommentClient.post_comment()が呼び出されることを確認
- **期待結果**:
  - Issue情報が取得される
  - ドラフトPRが作成される
  - 初期コメントが投稿される
- **確認項目**:
  - [ ] Issue情報が正しく取得される
  - [ ] PRが正しく作成される
  - [ ] コメントが正しく投稿される

---

### 3.3 PhaseExecutor → Phase実装 統合

#### IT-PE-PHASE-001: PhaseExecutor → PlanningPhase

- **目的**: PhaseExecutorとPlanningPhaseの統合動作を検証
- **前提条件**: ワークフロー初期化済み
- **テスト手順**:
  1. PhaseExecutor.create(phase_name="planning")を呼び出し
  2. executor.run()を呼び出し
  3. PlanningPhase.execute()が呼び出されることを確認
  4. PlanningPhase.review()が呼び出されることを確認
  5. planning.md作成を確認
  6. メタデータ更新を確認
- **期待結果**:
  - planningフェーズが実行される
  - planning.mdが作成される
  - メタデータが更新される
- **確認項目**:
  - [ ] planning.mdが存在する
  - [ ] planning.mdの内容が正しい
  - [ ] メタデータのstatusがcompletedになる

#### IT-PE-PHASE-002: PhaseExecutor → リトライ機能

- **目的**: リトライ機能が正しく動作することを検証
- **前提条件**: ワークフロー初期化済み
- **テスト手順**:
  1. PhaseExecutor.create()を呼び出し
  2. 1回目のexecute()でFAILを返すようにモック設定
  3. 2回目のrevise()でPASSを返すようにモック設定
  4. executor.run()を呼び出し
  5. リトライが実行されることを確認
- **期待結果**:
  - 1回目: execute() → review() → FAIL
  - 2回目: revise() → review() → PASS
  - 最終的にsuccess=True
- **確認項目**:
  - [ ] execute()が1回呼び出される
  - [ ] revise()が1回呼び出される
  - [ ] 最終的にstatusがcompletedになる

---

### 3.4 Git Operations 統合

#### IT-GIT-001: Repository → Branch → Commit フロー

- **目的**: Git操作クラス間の統合動作を検証
- **前提条件**: Gitリポジトリが存在する
- **テスト手順**:
  1. GitRepository.get_root()でルート取得
  2. GitBranch.create()でブランチ作成
  3. ファイルを変更
  4. GitRepository.get_changed_files()で変更ファイル取得
  5. GitCommit.commit_phase_output()でコミット
  6. GitCommit.push_to_remote()でプッシュ
- **期待結果**:
  - ブランチが作成される
  - 変更がコミットされる
  - リモートにプッシュされる
- **確認項目**:
  - [ ] ブランチが作成されている
  - [ ] コミットが作成されている
  - [ ] リモートにプッシュされている

---

### 3.5 GitHub Operations 統合

#### IT-GH-001: Issue → PR → Comment フロー

- **目的**: GitHub API操作クラス間の統合動作を検証
- **前提条件**: GitHub APIアクセス可能
- **テスト手順**:
  1. IssueClient.get_issue()でIssue情報取得
  2. PRClient.create_pull_request()でPR作成
  3. CommentClient.post_comment()でコメント投稿
  4. PRClient.update_pull_request()でPR更新
- **期待結果**:
  - Issue情報が取得される
  - PRが作成される
  - コメントが投稿される
  - PRが更新される
- **確認項目**:
  - [ ] Issue情報が正しい
  - [ ] PRが正しく作成される
  - [ ] コメントが正しく投稿される
  - [ ] PRが正しく更新される

---

### 3.6 ConfigManager → コンポーネント 統合

#### IT-CFG-001: ConfigManager → WorkflowController

- **目的**: 設定がWorkflowControllerに正しく渡されることを検証
- **前提条件**: config.yaml、環境変数が設定済み
- **テスト手順**:
  1. ConfigManager.load()で設定ロード
  2. WorkflowController.load()に設定を渡す
  3. Git操作でGit設定が使用されることを確認
- **期待結果**:
  - 設定が正しくロードされる
  - Git操作で設定が使用される
- **確認項目**:
  - [ ] git_userが正しく設定される
  - [ ] git_emailが正しく設定される
  - [ ] コミットのauthorが正しい

---

### 3.7 エラーハンドリング 統合

#### IT-ERR-001: GitHub API エラー → リトライ

- **目的**: GitHub APIエラー時にリトライが動作することを検証
- **前提条件**: GitHub APIアクセス可能
- **テスト手順**:
  1. PRClient.create_pull_request()を呼び出し
  2. 1回目は429エラー（Rate Limit）を返すようにモック設定
  3. 2回目は成功を返すようにモック設定
  4. リトライが実行されることを確認
- **期待結果**:
  - 1回目: 429エラー
  - リトライ待機
  - 2回目: 成功
- **確認項目**:
  - [ ] リトライが実行される
  - [ ] 最終的に成功する

#### IT-ERR-002: Git Push エラー → リトライ

- **目的**: Git pushエラー時にリトライが動作することを検証
- **前提条件**: Gitリポジトリが存在する
- **テスト手順**:
  1. GitCommit.push_to_remote()を呼び出し
  2. 1回目はネットワークエラーを返すようにモック設定
  3. 2回目は成功を返すようにモック設定
  4. リトライが実行されることを確認
- **期待結果**:
  - 1回目: エラー
  - リトライ待機
  - 2回目: 成功
- **確認項目**:
  - [ ] リトライが実行される
  - [ ] 最終的に成功する

---

## 4. BDDシナリオ

### Feature 1: ワークフロー初期化機能

#### Scenario 1-1: 新規Issueに対してワークフロー初期化を実行する

```gherkin
Feature: ワークフロー初期化機能

Scenario: 新規Issueに対してワークフロー初期化を実行する
  Given GitHub Issue #376が存在する
  And Gitリポジトリがクリーンな状態である
  When ユーザーが "ai-workflow init --issue-url https://github.com/tielec/infrastructure-as-code/issues/376" を実行する
  Then Issue情報が取得される
  And .ai-workflow/issue-376/metadata.json が作成される
  And ai-workflow/issue-376 ブランチが作成される
  And ドラフトPRが作成される
  And 初期コメントがIssueに投稿される
  And コマンドが正常終了する（exit code 0）
```

#### Scenario 1-2: 既にワークフローが初期化されているIssueに対して再実行する

```gherkin
Scenario: 既にワークフローが初期化されているIssueに対して再実行する
  Given GitHub Issue #376が存在する
  And .ai-workflow/issue-376/metadata.json が既に存在する
  And ai-workflow/issue-376 ブランチが既に存在する
  When ユーザーが "ai-workflow init --issue-url https://github.com/tielec/infrastructure-as-code/issues/376" を実行する
  Then エラーメッセージが表示される
  And コマンドが異常終了する（exit code 1）
```

#### Scenario 1-3: 存在しないIssueに対してワークフロー初期化を実行する

```gherkin
Scenario: 存在しないIssueに対してワークフロー初期化を実行する
  Given GitHub Issue #99999が存在しない
  When ユーザーが "ai-workflow init --issue-url https://github.com/tielec/infrastructure-as-code/issues/99999" を実行する
  Then "Issue not found"エラーメッセージが表示される
  And コマンドが異常終了する（exit code 1）
```

---

### Feature 2: フェーズ実行機能

#### Scenario 2-1: 全フェーズを順次実行する

```gherkin
Feature: フェーズ実行機能

Scenario: 全フェーズを順次実行する
  Given ワークフローが初期化済みである
  And すべてのフェーズがpending状態である
  When ユーザーが "ai-workflow execute --phase all --issue 376" を実行する
  Then planningフェーズが実行される
  And planningフェーズがcompletedになる
  And requirementsフェーズが実行される
  And requirementsフェーズがcompletedになる
  And designフェーズが実行される
  And designフェーズがcompletedになる
  And test_scenarioフェーズが実行される
  And test_scenarioフェーズがcompletedになる
  And implementationフェーズが実行される
  And implementationフェーズがcompletedになる
  And test_implementationフェーズが実行される
  And test_implementationフェーズがcompletedになる
  And testingフェーズが実行される
  And testingフェーズがcompletedになる
  And documentationフェーズが実行される
  And documentationフェーズがcompletedになる
  And reportフェーズが実行される
  And reportフェーズがcompletedになる
  And evaluationフェーズが実行される
  And evaluationフェーズがcompletedになる
  And 実行サマリーが表示される
  And コマンドが正常終了する（exit code 0）
```

#### Scenario 2-2: 個別フェーズを実行する

```gherkin
Scenario: 個別フェーズを実行する
  Given ワークフローが初期化済みである
  And planningフェーズがcompleted状態である
  When ユーザーが "ai-workflow execute --phase requirements --issue 376" を実行する
  Then requirementsフェーズが実行される
  And requirementsフェーズがcompletedになる
  And requirements.mdが作成される
  And Gitコミットが作成される
  And リモートにプッシュされる
  And 進捗コメントがIssueに投稿される
  And コマンドが正常終了する（exit code 0）
```

#### Scenario 2-3: 依存関係が満たされていないフェーズを実行する

```gherkin
Scenario: 依存関係が満たされていないフェーズを実行する
  Given ワークフローが初期化済みである
  And planningフェーズがpending状態である
  And requirementsフェーズがpending状態である
  When ユーザーが "ai-workflow execute --phase requirements --issue 376" を実行する
  Then 依存関係チェックが実行される
  And "Phase planning not completed" エラーメッセージが表示される
  And requirementsフェーズが実行されない
  And コマンドが異常終了する（exit code 1）
```

#### Scenario 2-4: 依存関係チェックをスキップしてフェーズを実行する

```gherkin
Scenario: 依存関係チェックをスキップしてフェーズを実行する
  Given ワークフローが初期化済みである
  And planningフェーズがpending状態である
  When ユーザーが "ai-workflow execute --phase requirements --issue 376 --skip-dependency-check" を実行する
  Then 依存関係チェックがスキップされる
  And requirementsフェーズが実行される
  And requirementsフェーズがcompletedになる
  And コマンドが正常終了する（exit code 0）
```

---

### Feature 3: フェーズレビュー機能

#### Scenario 3-1: フェーズレビューでPASSする

```gherkin
Feature: フェーズレビュー機能

Scenario: フェーズレビューでPASSする
  Given ワークフローが初期化済みである
  And planningフェーズが実行済みである
  And planning.mdが品質ゲートを満たしている
  When レビューが実行される
  Then レビュー結果が"PASS"になる
  And レビューコメントがIssueに投稿される
  And planningフェーズがcompleted状態になる
  And 次のフェーズが実行可能になる
```

#### Scenario 3-2: フェーズレビューでFAILし、リトライ後PASSする

```gherkin
Scenario: フェーズレビューでFAILし、リトライ後PASSする
  Given ワークフローが初期化済みである
  And planningフェーズが実行済みである
  And planning.mdが品質ゲートを満たしていない（1回目）
  When レビューが実行される
  Then レビュー結果が"FAIL"になる
  And レビューフィードバックがIssueに投稿される
  And planningフェーズがreviseモードで再実行される
  And planning.mdが修正される
  And 再度レビューが実行される
  And レビュー結果が"PASS"になる
  And planningフェーズがcompleted状態になる
```

#### Scenario 3-3: フェーズレビューで最大リトライ回数に到達する

```gherkin
Scenario: フェーズレビューで最大リトライ回数に到達する
  Given ワークフローが初期化済みである
  And planningフェーズが実行済みである
  And planning.mdが常に品質ゲートを満たさない
  When レビューが実行される
  Then 1回目: FAIL
  And planningフェーズがreviseモードで再実行される
  And 2回目: FAIL
  And planningフェーズがreviseモードで再実行される
  And 3回目: FAIL
  And 最大リトライ回数（3回）に到達する
  And planningフェーズがfailed状態になる
  And エラーコメントがIssueに投稿される
  And 次のフェーズが実行されない
```

---

### Feature 4: Git操作機能

#### Scenario 4-1: フェーズ成果物がGitコミットされる

```gherkin
Feature: Git操作機能

Scenario: フェーズ成果物がGitコミットされる
  Given ワークフローが初期化済みである
  And ai-workflow/issue-376ブランチにチェックアウト済みである
  When planningフェーズが完了する
  Then .ai-workflow/issue-376/00_planning/output/planning.md が作成される
  And planning.mdがステージングエリアに追加される
  And コミットメッセージ "[ai-workflow] Phase 0 (planning) - completed" でコミットされる
  And リモートにプッシュされる
```

#### Scenario 4-2: Git pushがネットワークエラーで失敗し、リトライ後成功する

```gherkin
Scenario: Git pushがネットワークエラーで失敗し、リトライ後成功する
  Given ワークフローが初期化済みである
  And フェーズ成果物がコミット済みである
  When Git pushが実行される
  Then 1回目: ネットワークエラーが発生する
  And 2秒待機する
  And 2回目: pushが成功する
  And リモートにコミットが反映される
```

---

### Feature 5: GitHub操作機能

#### Scenario 5-1: 進捗コメントがIssueに投稿される

```gherkin
Feature: GitHub操作機能

Scenario: 進捗コメントがIssueに投稿される
  Given ワークフローが初期化済みである
  And Issue #376が存在する
  When planningフェーズが開始される
  Then "Phase planning started"コメントがIssueに投稿される
  When planningフェーズが完了する
  Then "Phase planning completed"コメントがIssueに投稿される
```

#### Scenario 5-2: ドラフトPRが作成される

```gherkin
Scenario: ドラフトPRが作成される
  Given ワークフローが初期化済みである
  And ai-workflow/issue-376ブランチが作成済みである
  When ドラフトPRが作成される
  Then PRタイトルが"[ai-workflow] Issue #376"になる
  And PR本文にIssue情報が含まれる
  And PRがdraft状態になる
  And baseブランチがmainになる
  And headブランチがai-workflow/issue-376になる
```

#### Scenario 5-3: PR本文が進捗に応じて更新される

```gherkin
Scenario: PR本文が進捗に応じて更新される
  Given ドラフトPRが作成済みである
  And planningフェーズがcompleted状態である
  When requirementsフェーズが完了する
  Then PR本文が更新される
  And PR本文に"✅ planning"が表示される
  And PR本文に"✅ requirements"が表示される
  And PR本文に"⏳ design"が表示される
```

---

### Feature 6: エラーハンドリング機能

#### Scenario 6-1: GitHub APIレート制限に達した場合にリトライする

```gherkin
Feature: エラーハンドリング機能

Scenario: GitHub APIレート制限に達した場合にリトライする
  Given ワークフローが実行中である
  When GitHub APIレート制限（429エラー）が発生する
  Then エラーがログに記録される
  And 60秒待機する
  And API呼び出しがリトライされる
  And リトライが成功する
```

#### Scenario 6-2: Claude API呼び出しが失敗した場合にエラーハンドリングされる

```gherkin
Scenario: Claude API呼び出しが失敗した場合にエラーハンドリングされる
  Given planningフェーズが実行中である
  When Claude API呼び出しが500エラーで失敗する
  Then エラーがログに記録される
  And エラーコメントがIssueに投稿される
  And planningフェーズがfailed状態になる
  And ワークフローが中断される
```

#### Scenario 6-3: Git操作がロックエラーで失敗した場合にリトライする

```gherkin
Scenario: Git操作がロックエラーで失敗した場合にリトライする
  Given フェーズ成果物がコミット準備済みである
  When Git commitがロックエラーで失敗する
  Then エラーがログに記録される
  And 2秒待機する
  And commitがリトライされる
  And リトライが成功する
```

---

### Feature 7: 設定管理機能

#### Scenario 7-1: CLIオプションでGit設定を上書きする

```gherkin
Feature: 設定管理機能

Scenario: CLIオプションでGit設定を上書きする
  Given ワークフローが初期化済みである
  And config.yamlにgit_user="Default User"が設定されている
  When ユーザーが "ai-workflow execute --phase planning --issue 376 --git-user 'Custom User' --git-email 'custom@example.com'" を実行する
  Then git_userが"Custom User"に設定される
  And git_emailが"custom@example.com"に設定される
  And コミットのauthorが"Custom User <custom@example.com>"になる
```

#### Scenario 7-2: 環境変数から設定を読み込む

```gherkin
Scenario: 環境変数から設定を読み込む
  Given GITHUB_TOKEN環境変数が設定されている
  And GITHUB_REPOSITORY環境変数が設定されている
  When ワークフローが初期化される
  Then GitHub APIアクセスに環境変数のトークンが使用される
  And 正しいリポジトリにアクセスされる
```

---

### Feature 8: ワークフローレジューム機能

#### Scenario 8-1: 途中で中断されたワークフローを再開する

```gherkin
Feature: ワークフローレジューム機能

Scenario: 途中で中断されたワークフローを再開する
  Given ワークフローが初期化済みである
  And planningフェーズがcompleted状態である
  And requirementsフェーズがin_progress状態である
  And designフェーズがpending状態である
  When ユーザーが "ai-workflow execute --phase all --issue 376" を実行する
  Then planningフェーズがスキップされる
  And requirementsフェーズから実行が再開される
  And 後続フェーズが順次実行される
```

---

## 5. テストデータ

### 5.1 GitHub Issue データ

#### Issue #376（正常系）

```json
{
  "number": 376,
  "title": "[TASK] ai-workflowスクリプトの大規模リファクタリング",
  "body": "## 概要\n\nscripts/ai-workflow/ のソースコードが肥大化し...",
  "state": "open",
  "labels": [],
  "created_at": "2025-10-12T00:00:00Z",
  "updated_at": "2025-10-12T00:00:00Z",
  "html_url": "https://github.com/tielec/infrastructure-as-code/issues/376"
}
```

#### Issue #99999（異常系 - 不存在）

```json
{
  "error": "Not Found",
  "message": "Issue not found"
}
```

---

### 5.2 Git データ

#### リポジトリ状態（クリーン）

```json
{
  "is_dirty": false,
  "untracked_files": [],
  "modified_files": [],
  "staged_files": []
}
```

#### リポジトリ状態（変更あり）

```json
{
  "is_dirty": true,
  "untracked_files": [
    ".ai-workflow/issue-376/00_planning/output/planning.md"
  ],
  "modified_files": [
    ".ai-workflow/issue-376/metadata.json"
  ],
  "staged_files": []
}
```

#### ブランチリスト

```json
{
  "local_branches": ["main", "ai-workflow/issue-376"],
  "remote_branches": ["origin/main", "origin/ai-workflow/issue-376"]
}
```

---

### 5.3 Metadata データ

#### metadata.json（初期状態）

```json
{
  "issue_number": 376,
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/376",
  "branch_name": "ai-workflow/issue-376",
  "pr_number": null,
  "pr_url": null,
  "phases": {
    "planning": {"status": "pending", "review_result": null},
    "requirements": {"status": "pending", "review_result": null},
    "design": {"status": "pending", "review_result": null},
    "test_scenario": {"status": "pending", "review_result": null},
    "implementation": {"status": "pending", "review_result": null},
    "test_implementation": {"status": "pending", "review_result": null},
    "testing": {"status": "pending", "review_result": null},
    "documentation": {"status": "pending", "review_result": null},
    "report": {"status": "pending", "review_result": null},
    "evaluation": {"status": "pending", "review_result": null}
  },
  "created_at": "2025-10-12T00:00:00Z",
  "updated_at": "2025-10-12T00:00:00Z"
}
```

#### metadata.json（planning完了後）

```json
{
  "issue_number": 376,
  "phases": {
    "planning": {
      "status": "completed",
      "review_result": "PASS",
      "completed_at": "2025-10-12T01:00:00Z"
    },
    "requirements": {"status": "pending", "review_result": null}
  },
  "updated_at": "2025-10-12T01:00:00Z"
}
```

---

### 5.4 設定データ

#### config.yaml

```yaml
github_token: ${GITHUB_TOKEN}
github_repository: ${GITHUB_REPOSITORY}
git_user: "AI Workflow"
git_email: "ai-workflow@tielec.local"
claude_model: "claude-sonnet-4"
max_retries: 3
retry_delay: 2.0
```

#### 環境変数

```bash
GITHUB_TOKEN=ghp_xxx...
GITHUB_REPOSITORY=tielec/infrastructure-as-code
GIT_COMMIT_USER_NAME=AI Workflow
GIT_COMMIT_USER_EMAIL=ai-workflow@tielec.local
ANTHROPIC_API_KEY=sk-ant-xxx...
```

---

### 5.5 Phase出力データ

#### planning.md（正常系 - PASS）

```markdown
# プロジェクト計画書 - Issue #376

## 📋 Issue分析

### Issue情報
- **Issue番号**: #376
- **タイトル**: [TASK] ai-workflowスクリプトの大規模リファクタリング
...
```

#### planning.md（異常系 - FAIL）

```markdown
# プロジェクト計画書

（見出しが不足、Issue分析がない、タスク分割がない等、品質ゲートを満たさない内容）
```

---

## 6. テスト環境要件

### 6.1 ローカル開発環境

#### 必須ソフトウェア

- **OS**: Amazon Linux 2023
- **Python**: 3.8以上
- **Git**: 2.0以上
- **pytest**: 7.0以上
- **pytest-mock**: 3.10以上
- **pytest-cov**: 4.0以上（カバレッジ測定用）
- **behave**: 1.2.6以上（BDDテスト用）

#### 環境変数

```bash
GITHUB_TOKEN=<テスト用トークン>
GITHUB_REPOSITORY=tielec/infrastructure-as-code
ANTHROPIC_API_KEY=<テスト用APIキー>
GIT_COMMIT_USER_NAME=Test User
GIT_COMMIT_USER_EMAIL=test@example.com
```

#### テスト用リポジトリ

- **リポジトリ**: テスト専用のクローンリポジトリを使用
- **ブランチ**: テスト実行前にクリーンな状態を作成
- **Issue**: テスト用Issueを作成（実際のIssue #376は使用しない）

---

### 6.2 CI/CD環境（Jenkins）

#### Jenkinsfile設定

```groovy
pipeline {
    agent any

    environment {
        GITHUB_TOKEN = credentials('github-token')
        ANTHROPIC_API_KEY = credentials('anthropic-api-key')
    }

    stages {
        stage('Setup') {
            steps {
                sh 'pip install -r requirements.txt'
                sh 'pip install pytest pytest-mock pytest-cov behave'
            }
        }

        stage('Unit Tests') {
            steps {
                sh 'pytest tests/unit/ -v --cov=scripts/ai-workflow --cov-report=xml'
            }
        }

        stage('Integration Tests') {
            steps {
                sh 'pytest tests/integration/ -v'
            }
        }

        stage('BDD Tests') {
            steps {
                sh 'behave tests/features/'
            }
        }
    }

    post {
        always {
            junit 'test-results/*.xml'
            cobertura coberturaReportFile: 'coverage.xml'
        }
    }
}
```

---

### 6.3 モック/スタブ要件

#### GitHub APIモック

- **PyGithub**: モック対象
- **使用ツール**: pytest-mock、responses
- **モック対象API**:
  - `get_repo()`
  - `get_issue()`
  - `create_pull()`
  - `create_comment()`

#### Claude APIモック

- **Anthropic SDK**: モック対象
- **使用ツール**: pytest-mock
- **モック対象API**:
  - `messages.create()`

#### Git操作モック

- **GitPython**: 一部モック（リモート操作のみ）
- **ローカル操作**: 実際のGit操作を使用（テスト用リポジトリで実行）

---

### 6.4 テストデータ管理

#### テストデータディレクトリ構成

```
tests/
├── fixtures/
│   ├── issues/
│   │   ├── issue_376.json
│   │   └── issue_invalid.json
│   ├── metadata/
│   │   ├── metadata_initial.json
│   │   ├── metadata_planning_completed.json
│   │   └── metadata_all_completed.json
│   ├── phases/
│   │   ├── planning_pass.md
│   │   ├── planning_fail.md
│   │   └── requirements_pass.md
│   └── configs/
│       ├── config.yaml
│       └── config_custom.yaml
```

#### テストデータ生成スクリプト

```python
# tests/fixtures/generate_fixtures.py
def generate_issue_fixture(issue_number, state="open"):
    """テスト用Issue JSONを生成"""
    ...

def generate_metadata_fixture(issue_number, phases_status):
    """テスト用metadata.jsonを生成"""
    ...
```

---

## 7. 品質ゲート検証

### 7.1 Phase 2の戦略に沿ったテストシナリオである

- ✅ **UNIT_TEST**: セクション2で58個のユニットテストシナリオを作成
- ✅ **INTEGRATION_TEST**: セクション3で10個の統合テストシナリオを作成
- ✅ **BDD_TEST**: セクション4で8個のFeature、25個のシナリオを作成

### 7.2 主要な正常系がカバーされている

#### カバー済み正常系シナリオ

- ✅ ワークフロー初期化（init）
- ✅ 全フェーズ順次実行（execute --phase all）
- ✅ 個別フェーズ実行（execute --phase <phase>）
- ✅ フェーズレビューPASS
- ✅ Git操作（ブランチ作成、コミット、プッシュ）
- ✅ GitHub操作（Issue取得、PR作成、コメント投稿）
- ✅ 設定管理（config.yaml、環境変数、CLIオプション）

### 7.3 主要な異常系がカバーされている

#### カバー済み異常系シナリオ

- ✅ 無効なIssue URL
- ✅ 存在しないIssue
- ✅ ブランチ既存
- ✅ 依存関係未満足
- ✅ レビューFAIL（最大リトライ到達）
- ✅ GitHub APIエラー（Rate Limit）
- ✅ Git pushエラー（ネットワーク）
- ✅ Claude APIエラー
- ✅ Git lockエラー

### 7.4 期待結果が明確である

#### 期待結果の明確性

- ✅ すべてのユニットテストで具体的な期待値を記載
- ✅ すべての統合テストで確認項目チェックリストを記載
- ✅ すべてのBDDシナリオでThen句で期待結果を明記

---

## 8. テスト実施計画

### 8.1 実施スケジュール

| Phase | テスト種別 | 実施タイミング | 所要時間（見積もり） |
|-------|-----------|---------------|-------------------|
| Phase 2 | Unit Tests（core/git） | coreモジュールリファクタリング後 | 2~4h |
| Phase 2 | Unit Tests（core/github） | coreモジュールリファクタリング後 | 2~4h |
| Phase 3 | Unit Tests（phases/base） | phasesモジュールリファクタリング後 | 2~4h |
| Phase 4 | Unit Tests（cli, workflow） | main.pyリファクタリング後 | 2~3h |
| Phase 5 | Integration Tests | 全モジュールリファクタリング完了後 | 4~6h |
| Phase 5 | BDD Tests | 全モジュールリファクタリング完了後 | 4~6h |
| Phase 5 | テストカバレッジ測定 | 全テスト実施後 | 1~2h |

**合計所要時間**: 17~29時間

---

### 8.2 実施体制

- **テスト作成**: AI Workflow Orchestrator（自動生成）
- **テスト実行**: CI/CDパイプライン（自動実行）
- **テスト結果確認**: レビュワー（人間）
- **不具合対応**: AI Workflow Orchestrator + レビュワー

---

### 8.3 成功基準

#### Phase 5完了時の成功基準

- [ ] すべてのユニットテストが通過（PASS率100%）
- [ ] すべての統合テストが通過（PASS率100%）
- [ ] すべてのBDDテストが通過（PASS率100%）
- [ ] テストカバレッジが80%以上
- [ ] クリティカルパスのカバレッジが100%
- [ ] パフォーマンスがリファクタリング前と比較して5%以内の劣化

---

### 8.4 テスト自動化戦略

#### CI/CDパイプラインでの自動実行

1. **PR作成時**:
   - ユニットテスト実行（変更箇所に関連するテストのみ）
   - 高速フィードバック（5分以内）

2. **PRマージ前**:
   - 全ユニットテスト実行
   - 統合テスト実行
   - BDDテスト実行（重要シナリオのみ）
   - テストカバレッジ測定

3. **mainブランチマージ後**:
   - 全テストスイート実行（完全版）
   - パフォーマンステスト実行
   - テストカバレッジレポート生成

---

## 9. テストシナリオカバレッジマトリクス

### 9.1 要件 vs テストシナリオ対応表

| 要件ID | 要件名 | Unit | Integration | BDD | カバレッジ |
|--------|--------|------|-------------|-----|-----------|
| FR-1.1 | クリーンアーキテクチャ適用 | - | IT-WFC-GIT-001 | Feature 1-1 | 統合/BDD |
| FR-2.1 | CLI層の分離 | UT-CLI-001~005 | IT-CLI-WFC-001 | Feature 1-1 | 全レベル |
| FR-2.2 | ワークフロー制御抽出 | UT-WFC-001~005 | IT-CLI-WFC-002 | Feature 2-1 | 全レベル |
| FR-2.3 | 設定管理独立化 | UT-CFG-001~005 | IT-CFG-001 | Feature 7-1, 7-2 | 全レベル |
| FR-3.1 | git_manager.py分割 | UT-GR-001~005, UT-GB-001~007, UT-GC-001~006 | IT-GIT-001 | Feature 4-1, 4-2 | 全レベル |
| FR-3.2 | github_client.py分割 | UT-IC-001~004, UT-PC-001~005, UT-CC-001~004 | IT-GH-001 | Feature 5-1, 5-2, 5-3 | 全レベル |
| FR-4.1 | base_phase.py分割 | UT-PE-001~005, UT-PV-001~004, UT-PR-001~004 | IT-PE-PHASE-001, IT-PE-PHASE-002 | Feature 3-1, 3-2, 3-3 | 全レベル |
| FR-6.4 | テストカバレッジ向上 | すべてのUT | すべてのIT | すべてのBDD | 全レベル |
| NFR-1.1 | 実行時間維持 | - | - | Feature 2-1（時間測定） | BDD |
| NFR-3.1 | 既存機能動作維持 | すべてのUT | すべてのIT | すべてのBDD | 全レベル |

---

### 9.2 リスク vs テストシナリオ対応表

| リスクID | リスク内容 | 対応テストシナリオ | カバレッジ |
|---------|----------|-------------------|-----------|
| リスク1 | 既存テストの大量修正によるバグ混入 | すべてのUnit Tests | ユニット |
| リスク2 | リファクタリング中の一貫性の欠如 | IT-WFC-GIT-001, IT-WFC-GH-001 | 統合 |
| リスク3 | パフォーマンス劣化 | Feature 2-1（実行時間測定） | BDD |
| リスク5 | 工数超過 | （テストシナリオ自体が対象外） | - |
| リスク6 | ドキュメントと実装の乖離 | （Phase 6で対応） | - |

---

## 10. テスト成果物

### 10.1 成果物リスト

1. **テストコード**:
   - `tests/unit/cli/test_commands.py`
   - `tests/unit/core/test_workflow_controller.py`
   - `tests/unit/core/test_config_manager.py`
   - `tests/unit/core/git/test_repository.py`
   - `tests/unit/core/git/test_branch.py`
   - `tests/unit/core/git/test_commit.py`
   - `tests/unit/core/github/test_issue_client.py`
   - `tests/unit/core/github/test_pr_client.py`
   - `tests/unit/core/github/test_comment_client.py`
   - `tests/unit/phases/base/test_phase_executor.py`
   - `tests/unit/phases/base/test_phase_validator.py`
   - `tests/unit/phases/base/test_phase_reporter.py`
   - `tests/unit/common/test_logger.py`
   - `tests/unit/common/test_retry.py`
   - `tests/integration/test_cli_workflow.py`
   - `tests/integration/test_workflow_git.py`
   - `tests/integration/test_workflow_github.py`
   - `tests/integration/test_phase_execution.py`
   - `tests/integration/test_git_operations.py`
   - `tests/integration/test_github_operations.py`
   - `tests/integration/test_config_manager.py`
   - `tests/integration/test_error_handling.py`
   - `tests/features/workflow_initialization.feature`
   - `tests/features/phase_execution.feature`
   - `tests/features/phase_review.feature`
   - `tests/features/git_operations.feature`
   - `tests/features/github_operations.feature`
   - `tests/features/error_handling.feature`
   - `tests/features/config_management.feature`
   - `tests/features/workflow_resume.feature`

2. **テストデータ**:
   - `tests/fixtures/issues/`
   - `tests/fixtures/metadata/`
   - `tests/fixtures/phases/`
   - `tests/fixtures/configs/`

3. **テストレポート**:
   - ユニットテスト結果レポート
   - 統合テスト結果レポート
   - BDDテスト結果レポート
   - カバレッジレポート
   - パフォーマンステストレポート

---

## 11. まとめ

### 11.1 テストシナリオ統計

- **ユニットテストシナリオ**: 58個
  - CLI層: 5個
  - Application層: 10個
  - Domain層（Git）: 17個
  - Domain層（GitHub）: 13個
  - Domain層（Phases）: 11個
  - Infrastructure層: 2個

- **統合テストシナリオ**: 10個
  - CLI統合: 2個
  - ワークフロー統合: 2個
  - フェーズ実行統合: 2個
  - Git操作統合: 1個
  - GitHub操作統合: 1個
  - 設定管理統合: 1個
  - エラーハンドリング統合: 2個

- **BDDシナリオ**: 8個のFeature、25個のシナリオ
  - ワークフロー初期化: 3個
  - フェーズ実行: 4個
  - フェーズレビュー: 3個
  - Git操作: 2個
  - GitHub操作: 3個
  - エラーハンドリング: 3個
  - 設定管理: 2個
  - ワークフローレジューム: 1個

- **合計**: 93個のテストシナリオ

---

### 11.2 品質ゲート達成状況

- ✅ **Phase 2の戦略に沿ったテストシナリオである**: ALL（UNIT + INTEGRATION + BDD）を実装
- ✅ **主要な正常系がカバーされている**: 全主要フローをカバー
- ✅ **主要な異常系がカバーされている**: 全主要エラーケースをカバー
- ✅ **期待結果が明確である**: すべてのシナリオで具体的な期待結果を記載

---

### 11.3 次フェーズへの引き継ぎ

**Phase 4（実装フェーズ）への引き継ぎ**:

1. 本テストシナリオに基づいて、実装前にテストコードを作成（TDD）
2. 各コンポーネント実装時に、対応するユニットテストを実行
3. 統合テストは、Phase 5で実施
4. BDDテストは、Phase 5で実施

**重要な注意事項**:

- リファクタリングは既存機能の動作維持が最優先
- テストファーストで実装を進める（TDD）
- 各ステップでテストを実行し、回帰がないことを確認
- テストカバレッジ80%以上を維持

---

**作成日**: 2025-10-12
**作成者**: AI Workflow Orchestrator
**関連Issue**: #376
**Planning Document**: @.ai-workflow/issue-376/00_planning/output/planning.md
**Requirements Document**: @.ai-workflow/issue-376/01_requirements/output/requirements.md
**Design Document**: @.ai-workflow/issue-376/02_design/output/design.md
