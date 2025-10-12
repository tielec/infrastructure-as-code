# テストシナリオ - Issue #322

**プロジェクト**: AIワークフローのGitコミット時のユーザー名とメールアドレスを設定可能に
**Issue番号**: #322
**作成日**: 2025-10-12
**バージョン**: 1.0.0

---

## 0. Planning DocumentとRequirements Documentの確認

### 開発戦略の確認

Planning Phase (Phase 0)、Requirements Phase (Phase 1)、Design Phase (Phase 2) の成果物を確認しました。以下の開発戦略を踏まえてテストシナリオを作成します：

- **複雑度**: 簡単
- **見積もり工数**: 3時間
- **実装戦略**: EXTEND（既存コードの拡張）
- **テスト戦略**: UNIT_ONLY（ユニットテストのみ）
- **テストコード戦略**: EXTEND_TEST（既存テストファイルに追加）
- **リスク評価**: 低

**主要な変更箇所** (Design Documentより引用):
1. `scripts/ai-workflow/core/git_manager.py` - `_ensure_git_config()`メソッド拡張
2. `jenkins/jobs/dsl/ai-workflow/ai_workflow_orchestrator.groovy` - パラメータ追加
3. `jenkins/jobs/pipeline/ai-workflow/ai-workflow-orchestrator/Jenkinsfile` - environment設定追加
4. `scripts/ai-workflow/main.py` - CLIオプション追加（オプション）

---

## 1. テスト戦略サマリー

### 選択されたテスト戦略

**UNIT_ONLY**: ユニットテストのみ

**判断根拠** (Design Document Phase 2より引用):
- **純粋な関数処理**: 環境変数の読み取りとGit設定は、外部システムとの連携を必要としない純粋な関数処理
- **外部依存なし**: GitHub API、データベース、AWS等の外部サービスとの連携がない
- **モック化可能**: Gitコマンド（`git config`）はGitPythonライブラリを通じて実行され、モック化が容易
- **既存テストパターンの踏襲**: 既存の `test_git_manager.py` がユニットテストのみで構成されており、同様のパターンで十分
- **統合テストの必要性なし**: Jenkins環境での動作確認は手動テスト（Phase 6）で実施

### テスト対象の範囲

**主要テスト対象**:
1. `GitManager._ensure_git_config()` メソッド
   - 環境変数の優先順位ロジック
   - バリデーション処理
   - ログ出力
   - Git設定（ローカルリポジトリのみ）

2. `main.py execute` コマンド（オプション機能）
   - CLIオプション `--git-user` / `--git-email` の処理
   - 環境変数への設定ロジック

**テスト範囲外**:
- Jenkins環境での実際のパラメータ入力 → Phase 6で手動テスト
- Docker環境での環境変数継承 → Phase 6で手動テスト
- GitHub APIとの統合 → 既存の認証メカニズムを使用、本Issueでは変更なし

### テストの目的

1. **環境変数の優先順位検証**: `GIT_COMMIT_USER_NAME` > `GIT_AUTHOR_NAME` > デフォルト値
2. **バリデーション動作確認**: メールアドレス形式、ユーザー名長さのチェック
3. **後方互換性保証**: 既存の環境変数（`GIT_AUTHOR_NAME` / `GIT_AUTHOR_EMAIL`）が引き続き動作
4. **ログ出力検証**: 設定値が正しくログ出力される
5. **エラーハンドリング**: バリデーションエラー時のデフォルト値使用、警告ログ出力
6. **CLIオプション動作確認**: `--git-user` / `--git-email` オプションが環境変数に設定される

---

## 2. ユニットテストシナリオ

### 2.1. GitManager._ensure_git_config() メソッドのテスト

#### UT-GM-031: 環境変数 GIT_COMMIT_USER_NAME / GIT_COMMIT_USER_EMAIL 設定時

**テストケース名**: `test_ensure_git_config_with_git_commit_env`

**目的**: 新しい環境変数 `GIT_COMMIT_USER_NAME` と `GIT_COMMIT_USER_EMAIL` が設定されている場合、その値がGit設定に反映されることを検証

**前提条件**:
- Gitリポジトリが初期化されている
- `git config user.name` と `git config user.email` が未設定（またはクリア済み）
- 環境変数 `GIT_COMMIT_USER_NAME="Test User"` が設定されている
- 環境変数 `GIT_COMMIT_USER_EMAIL="test@example.com"` が設定されている

**入力**:
- 環境変数: `GIT_COMMIT_USER_NAME="Test User"`
- 環境変数: `GIT_COMMIT_USER_EMAIL="test@example.com"`

**期待結果**:
- `git config user.name` の値が `"Test User"` になる
- `git config user.email` の値が `"test@example.com"` になる
- ログ出力: `[INFO] Git設定完了: user.name=Test User, user.email=test@example.com`

**テストデータ**:
```python
env_vars = {
    'GIT_COMMIT_USER_NAME': 'Test User',
    'GIT_COMMIT_USER_EMAIL': 'test@example.com'
}
```

**実装例**:
```python
@patch.dict(os.environ, {
    'GIT_COMMIT_USER_NAME': 'Test User',
    'GIT_COMMIT_USER_EMAIL': 'test@example.com'
})
def test_ensure_git_config_with_git_commit_env(temp_git_repo, mock_metadata):
    """UT-GM-031: GIT_COMMIT_USER_NAME/EMAIL環境変数設定時のGit設定"""
    git_manager = GitManager(
        repo_path=temp_git_repo,
        metadata_path=mock_metadata,
        github_token='dummy-token'
    )

    # _ensure_git_config()を呼び出し
    git_manager._ensure_git_config()

    # Git設定を確認
    config_reader = git_manager.repo.config_reader()
    user_name = config_reader.get_value('user', 'name')
    user_email = config_reader.get_value('user', 'email')

    assert user_name == 'Test User'
    assert user_email == 'test@example.com'
```

---

#### UT-GM-032: 環境変数 GIT_AUTHOR_NAME / GIT_AUTHOR_EMAIL 設定時（既存互換性）

**テストケース名**: `test_ensure_git_config_with_git_author_env`

**目的**: 既存の環境変数 `GIT_AUTHOR_NAME` と `GIT_AUTHOR_EMAIL` が設定されている場合、その値がGit設定に反映されることを検証（後方互換性）

**前提条件**:
- Gitリポジトリが初期化されている
- `git config user.name` と `git config user.email` が未設定
- 環境変数 `GIT_AUTHOR_NAME="Legacy User"` が設定されている
- 環境変数 `GIT_AUTHOR_EMAIL="legacy@example.com"` が設定されている
- 環境変数 `GIT_COMMIT_USER_NAME` と `GIT_COMMIT_USER_EMAIL` は**未設定**

**入力**:
- 環境変数: `GIT_AUTHOR_NAME="Legacy User"`
- 環境変数: `GIT_AUTHOR_EMAIL="legacy@example.com"`

**期待結果**:
- `git config user.name` の値が `"Legacy User"` になる
- `git config user.email` の値が `"legacy@example.com"` になる
- ログ出力: `[INFO] Git設定完了: user.name=Legacy User, user.email=legacy@example.com`

**テストデータ**:
```python
env_vars = {
    'GIT_AUTHOR_NAME': 'Legacy User',
    'GIT_AUTHOR_EMAIL': 'legacy@example.com'
}
```

**実装例**:
```python
@patch.dict(os.environ, {
    'GIT_AUTHOR_NAME': 'Legacy User',
    'GIT_AUTHOR_EMAIL': 'legacy@example.com'
}, clear=True)
def test_ensure_git_config_with_git_author_env(temp_git_repo, mock_metadata):
    """UT-GM-032: GIT_AUTHOR_NAME/EMAIL環境変数設定時のGit設定（既存互換性）"""
    git_manager = GitManager(
        repo_path=temp_git_repo,
        metadata_path=mock_metadata,
        github_token='dummy-token'
    )

    git_manager._ensure_git_config()

    config_reader = git_manager.repo.config_reader()
    user_name = config_reader.get_value('user', 'name')
    user_email = config_reader.get_value('user', 'email')

    assert user_name == 'Legacy User'
    assert user_email == 'legacy@example.com'
```

---

#### UT-GM-033: 環境変数の優先順位確認

**テストケース名**: `test_ensure_git_config_priority`

**目的**: 環境変数の優先順位が正しく機能することを検証（`GIT_COMMIT_USER_NAME` > `GIT_AUTHOR_NAME` > デフォルト値）

**前提条件**:
- Gitリポジトリが初期化されている
- `git config user.name` と `git config user.email` が未設定
- 環境変数 `GIT_COMMIT_USER_NAME="Primary User"` が設定されている
- 環境変数 `GIT_AUTHOR_NAME="Secondary User"` も設定されている（優先度2位）
- 同様に、`GIT_COMMIT_USER_EMAIL` と `GIT_AUTHOR_EMAIL` の両方が設定されている

**入力**:
- 環境変数: `GIT_COMMIT_USER_NAME="Primary User"` (優先度1)
- 環境変数: `GIT_AUTHOR_NAME="Secondary User"` (優先度2)
- 環境変数: `GIT_COMMIT_USER_EMAIL="primary@example.com"` (優先度1)
- 環境変数: `GIT_AUTHOR_EMAIL="secondary@example.com"` (優先度2)

**期待結果**:
- `git config user.name` の値が `"Primary User"` になる（優先度1が使用される）
- `git config user.email` の値が `"primary@example.com"` になる（優先度1が使用される）
- `"Secondary User"` や `"secondary@example.com"` は使用されない

**テストデータ**:
```python
env_vars = {
    'GIT_COMMIT_USER_NAME': 'Primary User',
    'GIT_AUTHOR_NAME': 'Secondary User',
    'GIT_COMMIT_USER_EMAIL': 'primary@example.com',
    'GIT_AUTHOR_EMAIL': 'secondary@example.com'
}
```

**実装例**:
```python
@patch.dict(os.environ, {
    'GIT_COMMIT_USER_NAME': 'Primary User',
    'GIT_AUTHOR_NAME': 'Secondary User',
    'GIT_COMMIT_USER_EMAIL': 'primary@example.com',
    'GIT_AUTHOR_EMAIL': 'secondary@example.com'
})
def test_ensure_git_config_priority(temp_git_repo, mock_metadata):
    """UT-GM-033: 環境変数の優先順位確認"""
    git_manager = GitManager(
        repo_path=temp_git_repo,
        metadata_path=mock_metadata,
        github_token='dummy-token'
    )

    git_manager._ensure_git_config()

    config_reader = git_manager.repo.config_reader()
    user_name = config_reader.get_value('user', 'name')
    user_email = config_reader.get_value('user', 'email')

    # 優先度1（GIT_COMMIT_USER_NAME/EMAIL）が使用される
    assert user_name == 'Primary User'
    assert user_email == 'primary@example.com'

    # 優先度2（GIT_AUTHOR_NAME/EMAIL）は使用されない
    assert user_name != 'Secondary User'
    assert user_email != 'secondary@example.com'
```

---

#### UT-GM-034: 環境変数未設定時のデフォルト値

**テストケース名**: `test_ensure_git_config_default`

**目的**: すべての環境変数が未設定の場合、デフォルト値が使用されることを検証

**前提条件**:
- Gitリポジトリが初期化されている
- `git config user.name` と `git config user.email` が未設定
- すべてのGit関連環境変数が未設定（`GIT_COMMIT_USER_NAME`, `GIT_COMMIT_USER_EMAIL`, `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`）

**入力**:
- 環境変数: なし（すべて未設定）

**期待結果**:
- `git config user.name` の値が `"AI Workflow"` になる（デフォルト値）
- `git config user.email` の値が `"ai-workflow@tielec.local"` になる（デフォルト値）
- ログ出力: `[INFO] Git設定完了: user.name=AI Workflow, user.email=ai-workflow@tielec.local`

**テストデータ**:
```python
env_vars = {}  # すべて未設定
```

**実装例**:
```python
@patch.dict(os.environ, {}, clear=True)
def test_ensure_git_config_default(temp_git_repo, mock_metadata):
    """UT-GM-034: 環境変数未設定時のデフォルト値"""
    git_manager = GitManager(
        repo_path=temp_git_repo,
        metadata_path=mock_metadata,
        github_token='dummy-token'
    )

    git_manager._ensure_git_config()

    config_reader = git_manager.repo.config_reader()
    user_name = config_reader.get_value('user', 'name')
    user_email = config_reader.get_value('user', 'email')

    # デフォルト値が使用される
    assert user_name == 'AI Workflow'
    assert user_email == 'ai-workflow@tielec.local'
```

---

#### UT-GM-035: バリデーション - メールアドレス形式エラー

**テストケース名**: `test_ensure_git_config_validation_email`

**目的**: 不正なメールアドレス形式（`@`なし）の場合、警告ログを出力し、デフォルト値が使用されることを検証

**前提条件**:
- Gitリポジトリが初期化されている
- `git config user.name` と `git config user.email` が未設定
- 環境変数 `GIT_COMMIT_USER_EMAIL="invalid-email"` が設定されている（`@`なし）

**入力**:
- 環境変数: `GIT_COMMIT_USER_EMAIL="invalid-email"` (不正な形式)

**期待結果**:
- 警告ログ出力: `[WARN] Invalid email format: invalid-email, using default`
- `git config user.email` の値が `"ai-workflow@tielec.local"` になる（デフォルト値にフォールバック）
- 処理は継続される（エラーで停止しない）

**テストデータ**:
```python
invalid_emails = [
    'invalid-email',           # @なし
    'invalid',                 # @なし
    '',                        # 空文字列
    'user@',                   # ドメインなし（@のみ）
]
```

**実装例**:
```python
@patch.dict(os.environ, {'GIT_COMMIT_USER_EMAIL': 'invalid-email'})
@patch('builtins.print')
def test_ensure_git_config_validation_email(mock_print, temp_git_repo, mock_metadata):
    """UT-GM-035: バリデーション - メールアドレス形式エラー"""
    git_manager = GitManager(
        repo_path=temp_git_repo,
        metadata_path=mock_metadata,
        github_token='dummy-token'
    )

    git_manager._ensure_git_config()

    # 警告ログが出力されることを確認
    mock_print.assert_any_call('[WARN] Invalid email format: invalid-email, using default')

    # デフォルト値が使用される
    config_reader = git_manager.repo.config_reader()
    user_email = config_reader.get_value('user', 'email')
    assert user_email == 'ai-workflow@tielec.local'
```

---

#### UT-GM-036: バリデーション - ユーザー名長さエラー

**テストケース名**: `test_ensure_git_config_validation_username_length`

**目的**: ユーザー名が100文字を超える、または0文字の場合、警告ログを出力し、デフォルト値が使用されることを検証

**前提条件**:
- Gitリポジトリが初期化されている
- `git config user.name` と `git config user.email` が未設定
- 環境変数 `GIT_COMMIT_USER_NAME` に101文字以上の文字列が設定されている

**入力**:
- 環境変数: `GIT_COMMIT_USER_NAME="A" * 101` (101文字)

**期待結果**:
- 警告ログ出力: `[WARN] User name length is invalid (101 chars), using default`
- `git config user.name` の値が `"AI Workflow"` になる（デフォルト値にフォールバック）
- 処理は継続される（エラーで停止しない）

**テストデータ**:
```python
invalid_usernames = [
    'A' * 101,                 # 101文字（上限超過）
    'A' * 150,                 # 150文字（上限超過）
    '',                        # 0文字（下限未満）
]
```

**実装例**:
```python
@patch.dict(os.environ, {'GIT_COMMIT_USER_NAME': 'A' * 101})
@patch('builtins.print')
def test_ensure_git_config_validation_username_length(mock_print, temp_git_repo, mock_metadata):
    """UT-GM-036: バリデーション - ユーザー名長さエラー"""
    git_manager = GitManager(
        repo_path=temp_git_repo,
        metadata_path=mock_metadata,
        github_token='dummy-token'
    )

    git_manager._ensure_git_config()

    # 警告ログが出力されることを確認
    mock_print.assert_any_call('[WARN] User name length is invalid (101 chars), using default')

    # デフォルト値が使用される
    config_reader = git_manager.repo.config_reader()
    user_name = config_reader.get_value('user', 'name')
    assert user_name == 'AI Workflow'
```

---

#### UT-GM-037: ログ出力の確認

**テストケース名**: `test_ensure_git_config_log_output`

**目的**: Git設定完了時に正しいログメッセージが出力されることを検証

**前提条件**:
- Gitリポジトリが初期化されている
- `git config user.name` と `git config user.email` が未設定
- 環境変数 `GIT_COMMIT_USER_NAME="Log Test User"` が設定されている
- 環境変数 `GIT_COMMIT_USER_EMAIL="logtest@example.com"` が設定されている

**入力**:
- 環境変数: `GIT_COMMIT_USER_NAME="Log Test User"`
- 環境変数: `GIT_COMMIT_USER_EMAIL="logtest@example.com"`

**期待結果**:
- ログ出力: `[INFO] Git設定完了: user.name=Log Test User, user.email=logtest@example.com`
- ログメッセージが標準出力に出力される

**テストデータ**:
```python
env_vars = {
    'GIT_COMMIT_USER_NAME': 'Log Test User',
    'GIT_COMMIT_USER_EMAIL': 'logtest@example.com'
}
```

**実装例**:
```python
@patch.dict(os.environ, {
    'GIT_COMMIT_USER_NAME': 'Log Test User',
    'GIT_COMMIT_USER_EMAIL': 'logtest@example.com'
})
@patch('builtins.print')
def test_ensure_git_config_log_output(mock_print, temp_git_repo, mock_metadata):
    """UT-GM-037: ログ出力の確認"""
    git_manager = GitManager(
        repo_path=temp_git_repo,
        metadata_path=mock_metadata,
        github_token='dummy-token'
    )

    git_manager._ensure_git_config()

    # INFOログが出力されることを確認
    mock_print.assert_any_call(
        '[INFO] Git設定完了: user.name=Log Test User, user.email=logtest@example.com'
    )
```

---

### 2.2. main.py execute コマンドのテスト（オプション機能）

#### UT-MAIN-001: CLIオプション --git-user / --git-email の環境変数設定

**テストケース名**: `test_main_cli_git_options`

**目的**: `--git-user` と `--git-email` オプションが指定された場合、環境変数 `GIT_COMMIT_USER_NAME` と `GIT_COMMIT_USER_EMAIL` に設定されることを検証

**前提条件**:
- Gitリポジトリが初期化されている
- metadata.jsonが存在する
- 環境変数 `GIT_COMMIT_USER_NAME` と `GIT_COMMIT_USER_EMAIL` は未設定

**入力**:
- CLIオプション: `--git-user "CLI User"`
- CLIオプション: `--git-email "cli@example.com"`

**期待結果**:
- 環境変数 `GIT_COMMIT_USER_NAME` の値が `"CLI User"` になる
- 環境変数 `GIT_COMMIT_USER_EMAIL` の値が `"cli@example.com"` になる
- ログ出力: `[INFO] Git user name set from CLI option: CLI User`
- ログ出力: `[INFO] Git user email set from CLI option: cli@example.com`

**テストデータ**:
```python
cli_args = {
    'git_user': 'CLI User',
    'git_email': 'cli@example.com'
}
```

**実装例**:
```python
def test_main_cli_git_options(temp_git_repo, mock_metadata):
    """UT-MAIN-001: CLIオプション --git-user / --git-email の環境変数設定"""
    from click.testing import CliRunner
    from main import execute

    runner = CliRunner()

    # CLIオプションを指定して実行（dryrun的なテスト）
    with patch.dict(os.environ, {}, clear=True):
        result = runner.invoke(execute, [
            '--phase', 'requirements',
            '--issue', '322',
            '--git-user', 'CLI User',
            '--git-email', 'cli@example.com'
        ])

        # 環境変数が設定されることを確認
        assert os.environ.get('GIT_COMMIT_USER_NAME') == 'CLI User'
        assert os.environ.get('GIT_COMMIT_USER_EMAIL') == 'cli@example.com'
```

---

#### UT-MAIN-002: CLIオプションが環境変数より優先される

**テストケース名**: `test_main_cli_git_options_priority`

**目的**: CLIオプションが環境変数より優先されることを検証

**前提条件**:
- Gitリポジトリが初期化されている
- metadata.jsonが存在する
- 環境変数 `GIT_COMMIT_USER_NAME="Env User"` が設定されている
- 環境変数 `GIT_COMMIT_USER_EMAIL="env@example.com"` が設定されている

**入力**:
- 環境変数: `GIT_COMMIT_USER_NAME="Env User"` (優先度2)
- 環境変数: `GIT_COMMIT_USER_EMAIL="env@example.com"` (優先度2)
- CLIオプション: `--git-user "CLI User"` (優先度1)
- CLIオプション: `--git-email "cli@example.com"` (優先度1)

**期待結果**:
- 環境変数 `GIT_COMMIT_USER_NAME` の値が `"CLI User"` に上書きされる（CLIオプションが優先）
- 環境変数 `GIT_COMMIT_USER_EMAIL` の値が `"cli@example.com"` に上書きされる（CLIオプションが優先）

**テストデータ**:
```python
initial_env = {
    'GIT_COMMIT_USER_NAME': 'Env User',
    'GIT_COMMIT_USER_EMAIL': 'env@example.com'
}
cli_args = {
    'git_user': 'CLI User',
    'git_email': 'cli@example.com'
}
```

**実装例**:
```python
def test_main_cli_git_options_priority(temp_git_repo, mock_metadata):
    """UT-MAIN-002: CLIオプションが環境変数より優先される"""
    from click.testing import CliRunner
    from main import execute

    runner = CliRunner()

    # 環境変数を設定
    with patch.dict(os.environ, {
        'GIT_COMMIT_USER_NAME': 'Env User',
        'GIT_COMMIT_USER_EMAIL': 'env@example.com'
    }):
        # CLIオプションを指定して実行
        result = runner.invoke(execute, [
            '--phase', 'requirements',
            '--issue', '322',
            '--git-user', 'CLI User',
            '--git-email', 'cli@example.com'
        ])

        # CLIオプションが優先される
        assert os.environ.get('GIT_COMMIT_USER_NAME') == 'CLI User'
        assert os.environ.get('GIT_COMMIT_USER_EMAIL') == 'cli@example.com'
```

---

## 3. テストデータ

### 3.1. 正常データ

```python
VALID_TEST_DATA = {
    'user_name': [
        'Test User',                    # 通常のユーザー名
        'AI Workflow Bot',              # デフォルトユーザー名
        'A',                            # 最小長（1文字）
        'A' * 100,                      # 最大長（100文字）
        'User With Spaces',             # スペース含む
        'User-With-Hyphen',             # ハイフン含む
        'User_With_Underscore',         # アンダースコア含む
    ],
    'user_email': [
        'test@example.com',             # 通常のメールアドレス
        'ai-workflow@tielec.local',     # デフォルトメールアドレス
        'user+tag@example.com',         # +タグ付き
        'user.name@example.co.jp',      # ドット、サブドメイン
        'user_name@example-domain.com', # アンダースコア、ハイフン
    ]
}
```

### 3.2. 異常データ

```python
INVALID_TEST_DATA = {
    'user_name': [
        '',                             # 空文字列（下限未満）
        'A' * 101,                      # 101文字（上限超過）
        'A' * 150,                      # 150文字（上限超過）
    ],
    'user_email': [
        'invalid-email',                # @なし
        'invalid',                      # @なし
        '',                             # 空文字列
        'user@',                        # ドメインなし
        '@example.com',                 # ユーザー名なし
    ]
}
```

### 3.3. 境界値データ

```python
BOUNDARY_TEST_DATA = {
    'user_name': [
        'A',                            # 最小長（1文字）
        'A' * 100,                      # 最大長（100文字）
        'A' * 101,                      # 上限超過（101文字）
    ],
    'user_email': [
        'a@b.c',                        # 最短メールアドレス
    ]
}
```

### 3.4. 環境変数パターン

```python
ENV_VAR_PATTERNS = {
    # パターン1: 新しい環境変数のみ
    'pattern_1': {
        'GIT_COMMIT_USER_NAME': 'Primary User',
        'GIT_COMMIT_USER_EMAIL': 'primary@example.com'
    },

    # パターン2: 既存環境変数のみ（互換性）
    'pattern_2': {
        'GIT_AUTHOR_NAME': 'Legacy User',
        'GIT_AUTHOR_EMAIL': 'legacy@example.com'
    },

    # パターン3: 両方設定（優先順位確認）
    'pattern_3': {
        'GIT_COMMIT_USER_NAME': 'Primary User',
        'GIT_AUTHOR_NAME': 'Secondary User',
        'GIT_COMMIT_USER_EMAIL': 'primary@example.com',
        'GIT_AUTHOR_EMAIL': 'secondary@example.com'
    },

    # パターン4: すべて未設定（デフォルト値）
    'pattern_4': {},

    # パターン5: 不正な値
    'pattern_5': {
        'GIT_COMMIT_USER_NAME': 'A' * 101,  # 長さエラー
        'GIT_COMMIT_USER_EMAIL': 'invalid-email'  # 形式エラー
    }
}
```

---

## 4. テスト環境要件

### 4.1. ローカル開発環境

**必要なツール**:
- Python 3.8以上
- pytest
- GitPython ライブラリ
- Git 2.0以上

**環境変数**:
- テスト実行時に環境変数を動的に設定・削除できること
- `patch.dict(os.environ)` を使用して環境変数を制御

**Gitリポジトリ**:
- 各テストケースで一時的なGitリポジトリを作成（`temp_git_repo` フィクスチャ）
- テスト終了後に自動的にクリーンアップ

### 4.2. CI/CD環境（GitHub Actions）

**必要な設定**:
- Python環境のセットアップ
- Gitのインストール
- pytestの実行

**環境変数**:
- テスト実行時に環境変数が他のテストに影響を与えないように隔離

**カバレッジ**:
- コードカバレッジ80%以上を目標

### 4.3. モック/スタブの必要性

**モック対象**:
1. **標準出力（print）**: `@patch('builtins.print')` でモック化
   - ログ出力の検証に使用

2. **環境変数**: `@patch.dict(os.environ)` でモック化
   - 環境変数の設定・削除をテスト間で隔離

3. **GitPythonライブラリ**: 実際のGitリポジトリを使用（モック不要）
   - `temp_git_repo` フィクスチャで一時リポジトリを作成

**スタブ対象**:
- `mock_metadata`: metadata.jsonのモック（既存フィクスチャ）

### 4.4. テストフィクスチャ

```python
@pytest.fixture
def temp_git_repo(tmp_path):
    """一時的なGitリポジトリを作成"""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    repo = git.Repo.init(repo_path)
    yield repo_path
    # テスト終了後、自動的に削除される（tmp_pathの機能）

@pytest.fixture
def mock_metadata(tmp_path):
    """metadata.jsonのモック"""
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text('{"issue_number": 322, "phase": "test"}')
    yield metadata_path
```

---

## 5. Jenkins動作確認シナリオ（手動テスト）

### 5.1. シナリオ1: Jenkinsパラメータでの設定

**目的**: Jenkinsパラメータで指定したGit設定がコミットに反映されることを確認

**前提条件**:
- Jenkins環境が利用可能
- Job DSL (`ai_workflow_orchestrator.groovy`) が最新版にデプロイ済み
- Jenkinsfile が最新版にデプロイ済み

**テスト手順**:

1. **Job DSL再実行**:
   - Jenkins UI: `Admin_Jobs/job-creator` シードジョブを実行
   - Job DSL変更を反映

2. **パラメータ確認**:
   - `AI_Workflow/ai_workflow_orchestrator` ジョブを開く
   - 「Build with Parameters」を選択
   - 新しいパラメータ `GIT_COMMIT_USER_NAME` と `GIT_COMMIT_USER_EMAIL` が表示されることを確認
   - デフォルト値が設定されていることを確認

3. **ジョブ実行**:
   - パラメータを以下のように設定:
     - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/322`
     - `GIT_COMMIT_USER_NAME`: `Jenkins Test Bot`
     - `GIT_COMMIT_USER_EMAIL`: `jenkins-test@example.com`
   - ジョブを実行

4. **ログ確認**:
   - Jenkinsコンソールログを確認
   - 環境変数が設定されていることを確認:
     ```
     [INFO] Git user name set to: Jenkins Test Bot
     [INFO] Git user email set to: jenkins-test@example.com
     [INFO] Git設定完了: user.name=Jenkins Test Bot, user.email=jenkins-test@example.com
     ```

5. **コミット履歴確認**:
   - GitHub上で `ai-workflow/issue-322` ブランチを確認
   - 最新のコミットのAuthorを確認
   - Author: `Jenkins Test Bot <jenkins-test@example.com>` になっていることを確認

**期待結果**:
- [ ] Jenkinsパラメータが正しく表示される
- [ ] 環境変数がJenkinsfileからDockerコンテナに渡される
- [ ] コミットのAuthorが指定した値になる
- [ ] ログに設定値が出力される

---

### 5.2. シナリオ2: デフォルト値での実行

**目的**: パラメータをデフォルト値のまま実行した場合、デフォルトGit設定が使用されることを確認

**前提条件**:
- Jenkins環境が利用可能
- Job DSL、Jenkinsfileが最新版

**テスト手順**:

1. **ジョブ実行**:
   - `AI_Workflow/ai_workflow_orchestrator` ジョブを開く
   - 「Build with Parameters」を選択
   - パラメータをデフォルト値のまま変更せずに実行:
     - `GIT_COMMIT_USER_NAME`: `AI Workflow Bot` (デフォルト)
     - `GIT_COMMIT_USER_EMAIL`: `ai-workflow@example.com` (デフォルト)

2. **コミット履歴確認**:
   - GitHub上で `ai-workflow/issue-322` ブランチを確認
   - 最新のコミットのAuthorを確認
   - Author: `AI Workflow Bot <ai-workflow@example.com>` になっていることを確認

**期待結果**:
- [ ] デフォルト値がコミットに反映される
- [ ] 既存のワークフローと動作が一致する

---

### 5.3. シナリオ3: 環境変数未設定時の後方互換性

**目的**: 環境変数が未設定の場合、既存のGit設定が使用されることを確認（後方互換性）

**前提条件**:
- Jenkins環境が利用可能
- 古いバージョンのJob DSL（パラメータなし）を使用

**テスト手順**:

1. **Job DSLを一時的にロールバック**:
   - Job DSLファイルから `GIT_COMMIT_USER_NAME` と `GIT_COMMIT_USER_EMAIL` パラメータを削除
   - シードジョブを実行

2. **ジョブ実行**:
   - パラメータなしでジョブを実行

3. **コミット履歴確認**:
   - GitHub上でコミットのAuthorを確認
   - 既存のデフォルト値（`AI Workflow <ai-workflow@tielec.local>`）が使用されることを確認

**期待結果**:
- [ ] パラメータが存在しない場合でもワークフローが正常に動作する
- [ ] 既存のGit設定が使用される
- [ ] エラーが発生しない

---

### 5.4. シナリオ4: Docker環境での環境変数継承

**目的**: Jenkinsfileで設定した環境変数がDockerコンテナに正しく継承されることを確認

**前提条件**:
- Jenkins環境が利用可能
- Jenkinsfile、Job DSLが最新版

**テスト手順**:

1. **ジョブ実行**:
   - パラメータを設定してジョブを実行:
     - `GIT_COMMIT_USER_NAME`: `Docker Test User`
     - `GIT_COMMIT_USER_EMAIL`: `docker-test@example.com`

2. **Dockerコンテナ内で環境変数確認**:
   - Jenkinsfileに一時的なデバッグステージを追加:
     ```groovy
     stage('Debug Environment') {
         steps {
             sh 'echo "GIT_COMMIT_USER_NAME=$GIT_COMMIT_USER_NAME"'
             sh 'echo "GIT_COMMIT_USER_EMAIL=$GIT_COMMIT_USER_EMAIL"'
         }
     }
     ```
   - ジョブを実行

3. **コンソールログ確認**:
   - 環境変数が正しく設定されていることを確認:
     ```
     GIT_COMMIT_USER_NAME=Docker Test User
     GIT_COMMIT_USER_EMAIL=docker-test@example.com
     ```

**期待結果**:
- [ ] 環境変数がDockerコンテナに継承される
- [ ] Python スクリプト内で環境変数が読み取れる

---

## 6. 品質ゲートチェックリスト

### Phase 3: テストシナリオの品質ゲート

- [x] **Phase 2の戦略に沿ったテストシナリオである**
  - テスト戦略: UNIT_ONLY
  - ユニットテストシナリオのみ作成（UT-GM-031〜UT-GM-037、UT-MAIN-001〜UT-MAIN-002）
  - Integrationテスト、BDDテストは作成していない（Phase 2の戦略に準拠）

- [x] **主要な正常系がカバーされている**
  - UT-GM-031: 新しい環境変数設定時の動作 ✓
  - UT-GM-032: 既存環境変数設定時の動作（互換性） ✓
  - UT-GM-033: 環境変数の優先順位 ✓
  - UT-GM-034: デフォルト値の使用 ✓
  - UT-GM-037: ログ出力 ✓
  - UT-MAIN-001: CLIオプションの動作 ✓

- [x] **主要な異常系がカバーされている**
  - UT-GM-035: メールアドレス形式エラー ✓
  - UT-GM-036: ユーザー名長さエラー ✓
  - バリデーションエラー時のデフォルト値使用 ✓
  - 警告ログ出力 ✓

- [x] **期待結果が明確である**
  - すべてのテストケースに明確な期待結果を記載
  - 検証可能な形式で記述（assert文による検証）
  - Given-When-Then形式の要素を含む
  - 実装例コードを提供

### 要件定義書との対応確認

| 要件ID | 要件内容 | テストシナリオ | カバー状況 |
|--------|----------|---------------|-----------|
| FR-001 | 環境変数でのGit設定 | UT-GM-031, UT-GM-033, UT-GM-034 | ✓ |
| FR-002 | Jenkinsパラメータでの設定 | Jenkins動作確認シナリオ5.1 | ✓ |
| FR-003 | GitManagerでの環境変数読み取り | UT-GM-031〜UT-GM-037 | ✓ |
| FR-004 | Python CLIでの設定 | UT-MAIN-001, UT-MAIN-002 | ✓ |
| NFR-001 | 後方互換性 | UT-GM-032, UT-GM-034 | ✓ |
| NFR-002 | セキュリティ（バリデーション） | UT-GM-035, UT-GM-036 | ✓ |
| NFR-003 | ログ出力 | UT-GM-037 | ✓ |

### 受け入れ基準との対応確認

| 受け入れ基準 | テストシナリオ | カバー状況 |
|-------------|---------------|-----------|
| AC-001: 環境変数による設定 | UT-GM-031 | ✓ |
| AC-002: Jenkinsパラメータによる設定 | Jenkins動作確認シナリオ5.1 | ✓ |
| AC-003: 環境変数未設定時のデフォルト動作 | UT-GM-034 | ✓ |
| AC-004: 環境変数の優先順位 | UT-GM-033 | ✓ |
| AC-005: バリデーション（メールアドレス） | UT-GM-035 | ✓ |
| AC-006: バリデーション（ユーザー名長さ） | UT-GM-036 | ✓ |
| AC-007: CLIオプションの優先順位 | UT-MAIN-002 | ✓ |
| AC-008: グローバル設定の非変更 | ユニットテストで暗黙的に検証 | ✓ |

---

## 7. テスト実行計画

### 7.1. ユニットテスト実行

**実行コマンド**:
```bash
# すべてのユニットテストを実行
pytest scripts/ai-workflow/tests/unit/core/test_git_manager.py -v

# 特定のテストケースのみ実行
pytest scripts/ai-workflow/tests/unit/core/test_git_manager.py::test_ensure_git_config_with_git_commit_env -v

# カバレッジ付きで実行
pytest scripts/ai-workflow/tests/unit/core/test_git_manager.py --cov=scripts/ai-workflow/core/git_manager --cov-report=html
```

**目標**:
- すべてのテストがPASS
- コードカバレッジ80%以上

### 7.2. Jenkins動作確認（手動テスト）

**実行タイミング**: Phase 6（テスト実行フェーズ）

**担当者**: 開発者 + レビュアー

**所要時間**: 約30分

**チェックリスト**:
- [ ] シナリオ5.1: Jenkinsパラメータでの設定
- [ ] シナリオ5.2: デフォルト値での実行
- [ ] シナリオ5.3: 環境変数未設定時の後方互換性
- [ ] シナリオ5.4: Docker環境での環境変数継承

---

## 8. テストシナリオの保守性

### 8.1. テストケースの追加

今後、以下のような拡張が必要になった場合のテストケース追加例：

**例1: SSMパラメータストアからの設定読み込み**
- 新規テストケース: `UT-GM-039: SSMパラメータストアからの設定読み込み`
- テスト対象: 新しい環境変数 `GIT_COMMIT_CONFIG_SOURCE=ssm` を使用した場合の動作

**例2: Git署名機能**
- 新規テストケース: `UT-GM-040: GPG署名の設定`
- テスト対象: `git config user.signingkey` の設定

### 8.2. テストデータの拡張

新しいエッジケースが発見された場合、`VALID_TEST_DATA`、`INVALID_TEST_DATA`、`BOUNDARY_TEST_DATA` にデータを追加。

---

## 9. まとめ

### テストシナリオの概要

Issue #322のテストシナリオは、**UNIT_ONLY戦略**に基づき、以下のテストケースを作成しました：

**ユニットテストシナリオ** (合計9ケース):
- UT-GM-031〜UT-GM-037: GitManager._ensure_git_config() メソッドのテスト（7ケース）
- UT-MAIN-001〜UT-MAIN-002: main.py execute コマンドのテスト（2ケース）

**Jenkins動作確認シナリオ** (合計4シナリオ):
- 手動テストとして Phase 6 で実施

### カバレッジ

**機能要件**: すべての機能要件（FR-001〜FR-004）がテストケースでカバーされている

**非機能要件**: すべての非機能要件（NFR-001〜NFR-003）がテストケースでカバーされている

**受け入れ基準**: すべての受け入れ基準（AC-001〜AC-008）がテストケースでカバーされている

### 次のステップ

1. **Phase 4: 実装** - 設計書とテストシナリオに基づいた実装
2. **Phase 5: テスト実装** - UT-GM-031〜UT-GM-037、UT-MAIN-001〜UT-MAIN-002の実装
3. **Phase 6: テスト実行** - ユニットテスト実行 + Jenkins動作確認
4. **Phase 7: ドキュメント作成** - README.md更新、docstring追加

---

**テストシナリオ作成日**: 2025-10-12
**作成者**: AI Workflow (Test Scenario Phase)
**Issue**: #322
