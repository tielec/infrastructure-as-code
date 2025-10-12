# テストコード実装ログ - Issue #355

## ドキュメント情報

- **Issue番号**: #355
- **タイトル**: [FEATURE] AI Workflow: Init時にドラフトPRを自動作成
- **作成日**: 2025-10-12
- **バージョン**: 1.0.0

---

## 実装サマリー

- **テスト戦略**: UNIT_INTEGRATION
- **テストファイル数**: 3個（1個拡張、2個新規作成）
- **テストケース数**: 25個
  - ユニットテスト: 16個
  - 統合テスト: 9個

### テストカバレッジ

| コンポーネント | ユニットテスト | 統合テスト | 合計 |
|--------------|-------------|-----------|------|
| GitHubClient | 9 | 3 | 12 |
| main.py init | 7 | 6 | 13 |
| **合計** | **16** | **9** | **25** |

---

## テストファイル一覧

### 既存ファイルの拡張

#### 1. `tests/unit/core/test_github_client.py`

**拡張内容**: GitHubClient PR作成機能のユニットテストクラスを追加

**追加したテストケース**:
- `TestGitHubClientPR` クラス（9個のテストメソッド）

**行数**: 約320行追加

### 新規作成

#### 2. `tests/unit/test_main_init_pr.py`

**説明**: main.py init コマンドのPR作成ロジックのユニットテスト

**テストクラス**:
- `TestMainInitPRCreation` クラス（7個のテストメソッド）

**行数**: 約380行

#### 3. `tests/integration/test_init_pr_workflow.py`

**説明**: init → commit → push → PR作成の統合テスト

**テストクラス**:
- `TestInitPRWorkflowIntegration` クラス（4個のテストメソッド）
- `TestGitManagerGitHubClientIntegration` クラス（2個のテストメソッド）
- `TestGitHubAPIIntegration` クラス（3個のテストメソッド）

**行数**: 約500行

---

## テストケース詳細

### ユニットテスト: `tests/unit/core/test_github_client.py`

#### TestGitHubClientPR クラス

##### TC-U-001: test_create_pull_request_success
- **目的**: PR作成が正常に成功することを検証
- **Given**: GitHubClientが初期化されている
- **When**: create_pull_request()を呼び出す
- **Then**: PR作成が成功し、PR URLとPR番号が返される
- **モック**: repository.create_pull()をモック
- **検証項目**:
  - `result['success']` が `True`
  - `result['pr_url']` が正しいURL
  - `result['pr_number']` が正しい番号
  - `result['error']` が `None`

##### TC-U-002: test_create_pull_request_auth_error
- **目的**: GitHub Token権限不足時に適切なエラーメッセージが返されることを検証
- **Given**: GitHubClientが初期化されている
- **When**: GitHub Tokenに権限がなくcreate_pull_request()を呼び出す
- **Then**: 権限エラーのメッセージが返される
- **モック**: GithubException(401)をraiseするようにモック
- **検証項目**:
  - `result['success']` が `False`
  - `result['error']` に "GitHub Token lacks 'repo' scope" が含まれる

##### TC-U-003: test_create_pull_request_existing_pr
- **目的**: 既存PRが存在する場合に適切なエラーメッセージが返されることを検証
- **Given**: GitHubClientが初期化されている
- **When**: 既存PRが存在する状態でcreate_pull_request()を呼び出す
- **Then**: 既存PR重複エラーのメッセージが返される
- **モック**: GithubException(422)をraiseするようにモック
- **検証項目**:
  - `result['success']` が `False`
  - `result['error']` に "A pull request already exists" が含まれる

##### TC-U-004: test_create_pull_request_network_error
- **目的**: ネットワークエラー時に適切なエラーメッセージが返されることを検証
- **Given**: GitHubClientが初期化されている
- **When**: ネットワークエラーが発生した状態でcreate_pull_request()を呼び出す
- **Then**: 予期しないエラーのメッセージが返される
- **モック**: Exception('Network unreachable')をraiseするようにモック
- **検証項目**:
  - `result['success']` が `False`
  - `result['error']` に "Unexpected error" と "Network unreachable" が含まれる

##### TC-U-005: test_check_existing_pr_found
- **目的**: 既存PRが存在する場合にPR情報が返されることを検証
- **Given**: GitHubClientが初期化されている
- **When**: 既存PRが存在する状態でcheck_existing_pr()を呼び出す
- **Then**: 既存PR情報が返される
- **モック**: repository.get_pulls()が既存PRを返すようにモック
- **検証項目**:
  - `result` が `None` ではない
  - `result['pr_number']` が正しい番号
  - `result['pr_url']` が正しいURL
  - `result['state']` が 'open'

##### TC-U-006: test_check_existing_pr_not_found
- **目的**: 既存PRが存在しない場合にNoneが返されることを検証
- **Given**: GitHubClientが初期化されている
- **When**: 既存PRが存在しない状態でcheck_existing_pr()を呼び出す
- **Then**: Noneが返される
- **モック**: repository.get_pulls()が空のリストを返すようにモック
- **検証項目**:
  - `result` が `None`

##### TC-U-007: test_check_existing_pr_api_error
- **目的**: GitHub APIエラー時にNoneが返され、警告ログが出力されることを検証
- **Given**: GitHubClientが初期化されている
- **When**: GitHub APIエラーが発生した状態でcheck_existing_pr()を呼び出す
- **Then**: Noneが返され、警告ログが出力される
- **モック**: GithubException(500)をraiseするようにモック
- **検証項目**:
  - `result` が `None`
  - 標準出力に "[WARNING] Failed to check existing PR" が含まれる

##### TC-U-008: test_generate_pr_body_template_success
- **目的**: PR本文テンプレートが正しい形式で生成されることを検証
- **Given**: GitHubClientが初期化されている
- **When**: _generate_pr_body_template()を呼び出す
- **Then**: 正しい形式のPR本文が生成される
- **モック**: なし（実際のメソッドを呼び出す）
- **検証項目**:
  - `body` に "Closes #355" が含まれる
  - `body` に "- [x] Phase 0: Planning" が含まれる
  - `body` に "- [ ] Phase 1: Requirements" が含まれる
  - `body` に ".ai-workflow/issue-355/" が含まれる
  - `body` に "ai-workflow/issue-355" が含まれる
  - `body` に "Claude Code Pro Max" が含まれる
  - `body` に "ContentParser" が含まれる

##### TC-U-009: test_generate_pr_body_template_different_issue
- **目的**: 異なるIssue番号に対応したテンプレートが生成されることを検証
- **Given**: GitHubClientが初期化されている
- **When**: 異なるIssue番号で_generate_pr_body_template()を呼び出す
- **Then**: 該当するIssue番号のPR本文が生成される
- **モック**: なし（実際のメソッドを呼び出す）
- **検証項目**:
  - `body` に "Closes #999" が含まれる
  - `body` に ".ai-workflow/issue-999/" が含まれる
  - `body` に "ai-workflow/issue-999" が含まれる

---

### ユニットテスト: `tests/unit/test_main_init_pr.py`

#### TestMainInitPRCreation クラス

##### TC-U-010: test_init_commit_success_then_push
- **目的**: commit成功後にpush処理が実行されることを検証
- **Given**: metadata.jsonが作成されている
- **When**: commitが成功する
- **Then**: push処理が実行される
- **モック**: GitManager、GitHubClient、その他の依存関係をモック
- **検証項目**:
  - `commit_phase_output()` が呼ばれた
  - `push_to_remote()` が呼ばれた

##### TC-U-011: test_init_commit_failure_skip_push
- **目的**: commit失敗時にpushとPR作成がスキップされることを検証
- **Given**: metadata.jsonが作成されている
- **When**: commitが失敗する
- **Then**: pushとPR作成がスキップされる
- **モック**: commit_phase_output()が失敗を返すようにモック
- **検証項目**:
  - `commit_phase_output()` が呼ばれた
  - `push_to_remote()` が呼ばれていない
  - 警告ログが出力されている

##### TC-U-012: test_init_push_failure_skip_pr
- **目的**: push失敗時にPR作成がスキップされることを検証
- **Given**: commitが成功している
- **When**: pushが失敗する
- **Then**: PR作成がスキップされる
- **モック**: push_to_remote()が失敗を返すようにモック
- **検証項目**:
  - `push_to_remote()` が呼ばれた
  - `create_pull_request()` が呼ばれていない
  - 警告ログが出力されている

##### TC-U-013: test_init_existing_pr_skip
- **目的**: 既存PRが存在する場合に新規PR作成がスキップされることを検証
- **Given**: commit、pushが成功している
- **When**: 既存PRが存在する
- **Then**: 新規PR作成がスキップされる
- **モック**: check_existing_pr()が既存PR情報を返すようにモック
- **検証項目**:
  - `check_existing_pr()` が呼ばれた
  - `create_pull_request()` が呼ばれていない
  - 警告ログが出力されている

##### TC-U-014: test_init_pr_creation_success
- **目的**: PR作成が正常に実行されることを検証
- **Given**: commit、pushが成功している
- **When**: 既存PRが存在しない
- **Then**: PR作成が成功する
- **モック**: 全ての処理が成功を返すようにモック
- **検証項目**:
  - `check_existing_pr()` が呼ばれた
  - `create_pull_request()` が呼ばれた
  - 成功ログが出力されている

##### TC-U-015: test_init_github_token_not_set
- **目的**: GITHUB_TOKEN未設定時にPR作成がスキップされることを検証
- **Given**: commit、pushが成功している
- **When**: GITHUB_TOKENが未設定
- **Then**: PR作成がスキップされる
- **モック**: 環境変数を未設定にする
- **検証項目**:
  - 警告ログが出力されている
  - "GITHUB_TOKEN" または "not set" が含まれる

##### TC-U-016: test_init_pr_creation_failure_but_init_success
- **目的**: PR作成失敗時でもinit全体が成功として完了することを検証
- **Given**: commit、pushが成功している
- **When**: PR作成が失敗する
- **Then**: init全体は成功として完了する
- **モック**: create_pull_request()が失敗を返すようにモック
- **検証項目**:
  - `create_pull_request()` が呼ばれた
  - initは成功（exit code 0）
  - 警告ログが出力されている

---

### 統合テスト: `tests/integration/test_init_pr_workflow.py`

#### TestInitPRWorkflowIntegration クラス

##### TC-I-001: test_init_e2e_success
- **目的**: init実行後、commit → push → PR作成が順番に実行されることを検証
- **Given**: Gitリポジトリが初期化されている
- **When**: initコマンドを実行する
- **Then**: metadata.json作成、commit、push、PR作成がすべて成功する
- **注意**: 実際のGitHub APIは使用せず、モックを使用
- **検証項目**:
  - initコマンドが成功
  - commit、push、PR作成が順番に呼ばれた

##### TC-I-002: test_init_e2e_existing_pr
- **目的**: 既存PRが存在する場合、新規PR作成がスキップされることを検証
- **Given**: 既存PRが存在する
- **When**: initコマンドを実行する
- **Then**: 新規PR作成がスキップされる
- **検証項目**:
  - commit、pushは成功
  - 既存PRチェックが実行された
  - 新規PR作成がスキップされた
  - 警告ログが出力されている

##### TC-I-003: test_init_e2e_push_retry
- **目的**: push失敗時に最大3回リトライされることを検証
- **Given**: push処理が1回目、2回目は失敗し、3回目に成功する
- **When**: initコマンドを実行する
- **Then**: pushが3回試行され、最終的に成功する
- **注意**: GitManager内部のリトライ機能をテスト
- **検証項目**:
  - pushが呼ばれた
  - 最終的にpushが成功した
  - PR作成が実行された

##### TC-I-004: test_init_e2e_commit_failure
- **目的**: commit失敗時にpushとPR作成がスキップされることを検証
- **Given**: commit処理が失敗する
- **When**: initコマンドを実行する
- **Then**: pushとPR作成がスキップされる
- **検証項目**:
  - commitが試行された
  - pushが実行されていない
  - PR作成が実行されていない
  - 警告ログが出力されている

#### TestGitManagerGitHubClientIntegration クラス

##### TC-I-005: test_git_manager_github_client_integration_success
- **目的**: GitManagerのcommit、push実行後、GitHubClientでPR作成が実行されることを検証
- **Given**: GitManagerとGitHubClientが初期化されている
- **When**: commit → push → PR作成を順番に実行する
- **Then**: すべての処理が成功する
- **検証項目**:
  - commitが成功
  - pushが成功
  - 既存PRチェックが実行された（結果はNone）
  - PR作成が成功

##### TC-I-006: test_git_manager_github_client_error_propagation
- **目的**: GitManagerのエラーがGitHubClient処理に影響しないことを検証
- **Given**: GitManagerのpush処理が失敗する
- **When**: commit → push → PR作成を順番に実行する
- **Then**: push失敗後、GitHubClient処理がスキップされる
- **検証項目**:
  - commitが成功
  - pushが失敗
  - GitHubClientが呼ばれていない

#### TestGitHubAPIIntegration クラス

##### TC-I-007: test_github_api_pr_creation
- **目的**: 実際のGitHub APIを使用してPRが作成されることを検証
- **注意**: このテストは実際にPRを作成するため、通常はスキップされます
- **スキップ理由**: 実際のGitHub APIを使用するため、手動実行のみ推奨

##### TC-I-008: test_github_api_check_existing_pr
- **目的**: 実際のGitHub APIを使用して既存PRチェックが実行されることを検証
- **Given**: テストリポジトリへのアクセス権がある
- **When**: check_existing_pr()を呼び出す
- **Then**: 既存PR情報が返される（または None）
- **検証項目**:
  - 存在しないブランチの場合、Noneが返される

##### TC-I-009: test_github_api_permission_error
- **目的**: GitHub Token権限不足時に適切なエラーが返されることを検証
- **注意**: このテストは権限不足のトークンが必要なため、通常はスキップされます
- **スキップ理由**: 権限エラーのテストは手動実行のみ推奨

---

## モック/スタブの実装

### ユニットテストで使用するモック

#### 1. PyGithub APIのモック

```python
# repository.create_pull()のモック
mock_pr = mocker.Mock()
mock_pr.html_url = 'https://github.com/owner/repo/pull/123'
mock_pr.number = 123
mock_repository.create_pull.return_value = mock_pr
```

#### 2. repository.get_pulls()のモック

```python
# 既存PR存在時
mock_pr = mocker.Mock()
mock_pr.number = 123
mock_pr.html_url = 'https://github.com/owner/repo/pull/123'
mock_pr.state = 'open'
mock_repository.get_pulls.return_value = [mock_pr]

# 既存PR不在時
mock_repository.get_pulls.return_value = []
```

#### 3. GithubExceptionのモック

```python
from github import GithubException

# 401エラー
mock_repository.create_pull.side_effect = GithubException(
    status=401,
    data={'message': 'Bad credentials'},
    headers={}
)

# 422エラー
mock_repository.create_pull.side_effect = GithubException(
    status=422,
    data={'message': 'Validation Failed'},
    headers={}
)
```

#### 4. GitManagerのモック

```python
mock_git_manager = Mock()
mock_git_manager.commit_phase_output.return_value = {
    'success': True,
    'commit_hash': 'abc1234567890'
}
mock_git_manager.push_to_remote.return_value = {
    'success': True
}
```

#### 5. GitHubClientのモック

```python
mock_github_client = Mock()
mock_github_client.check_existing_pr.return_value = None
mock_github_client.create_pull_request.return_value = {
    'success': True,
    'pr_url': 'https://github.com/owner/repo/pull/123',
    'pr_number': 123,
    'error': None
}
```

---

## テスト実行方法

### すべてのユニットテストを実行

```bash
cd /tmp/jenkins-a990e07d/workspace/AI_Workflow/ai_workflow_orchestrator/scripts/ai-workflow
pytest tests/unit/ -v
```

### GitHubClientのテストのみ実行

```bash
pytest tests/unit/core/test_github_client.py -v
```

### main.py initのテストのみ実行

```bash
pytest tests/unit/test_main_init_pr.py -v
```

### すべての統合テストを実行

```bash
pytest tests/integration/ -v
```

### init PR workflowのテストのみ実行

```bash
pytest tests/integration/test_init_pr_workflow.py -v
```

### カバレッジ計測

```bash
pytest tests/unit/ tests/integration/ --cov=scripts/ai-workflow --cov-report=html
```

### 特定のマーカーのテストのみ実行

```bash
# ユニットテストのみ
pytest -m unit -v

# 統合テストのみ
pytest -m integration -v
```

---

## テスト環境要件

### 必須環境

- **Python**: 3.11以上
- **pytest**: 7.0以上
- **pytest-mock**: pytest モック機能
- **pytest-cov**: カバレッジ計測

### 環境変数（統合テストのみ）

```bash
export GITHUB_TOKEN="<有効なトークン>"
export GITHUB_REPOSITORY="owner/repo"
```

### 依存ライブラリ

- `PyGithub`: 2.0以上
- `GitPython`: 3.1以上
- `click`: CLIフレームワーク

---

## テストコード実装時の設計判断

### 1. モックの粒度

**判断**: PyGithub APIとGitManager、GitHubClientの外部依存をすべてモック

**理由**:
- ユニットテストでは外部依存を排除し、高速にテスト実行
- 統合テストでは必要最小限のモック（GitHub API呼び出しはモック、内部ロジックは実際に実行）

### 2. Given-When-Then形式の採用

**判断**: すべてのテストケースでGiven-When-Then形式を採用

**理由**:
- テストの意図が明確になる
- 他の開発者が理解しやすい
- テストシナリオ（Phase 3）との対応が明確

### 3. 既存テストファイルの拡張 vs 新規作成

**判断**: GitHubClientのテストは既存ファイルに追加、main.py initのテストは新規作成

**理由**:
- GitHubClientの機能拡張は既存テストファイルに追加することで、コヒージョンを維持
- main.py initのテストは独立した機能のため、新規ファイルで管理（可読性向上）

### 4. 統合テストのスキップ戦略

**判断**: 実際のGitHub APIを使用するテストは `@pytest.mark.skip` でスキップ

**理由**:
- 実際にPRを作成するテストは、テストリポジトリを汚染する可能性がある
- CI/CD環境で実行する場合は、専用のテストリポジトリを使用
- 通常のローカル開発ではモックで十分

### 5. エラーケースの網羅性

**判断**: 認証エラー（401）、既存PR重複（422）、ネットワークエラーをすべてカバー

**理由**:
- テストシナリオ（Phase 3）で定義されたエラーケースをすべて実装
- 実装コード（Phase 4）のエラーハンドリングと対応

---

## 品質ゲート確認（Phase 5）

テストコード実装は以下の品質ゲートを満たしています：

- [x] **Phase 3のテストシナリオがすべて実装されている**
  - ユニットテスト: TC-U-001 〜 TC-U-016（16個）
  - 統合テスト: TC-I-001 〜 TC-I-009（9個）
  - すべてのテストシナリオが実装済み

- [x] **テストコードが実行可能である**
  - pytest で実行可能な形式で実装
  - モックとフィクスチャが適切に設定されている
  - 既存のテストフレームワークと統合されている

- [x] **テストの意図がコメントで明確**
  - すべてのテストメソッドにdocstringを記載
  - Given-When-Then形式でテストの意図を明確に記述
  - テストシナリオIDを明記（例: TC-U-001）

---

## 既存テストとの整合性

### 1. テストマーカー

既存のテストと同様に、以下のマーカーを使用：
- `@pytest.mark.unit`: ユニットテスト
- `@pytest.mark.integration`: 統合テスト
- `@pytest.mark.skipif`: 条件付きスキップ
- `@pytest.mark.skip`: 無条件スキップ

### 2. フィクスチャの活用

既存のフィクスチャを活用：
- `github_token`: GitHub Personal Access Token
- `github_repository`: GitHubリポジトリ名
- `mocker`: pytest-mockのフィクスチャ

### 3. テストディレクトリ構造

既存のディレクトリ構造に準拠：
- `tests/unit/core/`: coreモジュールのユニットテスト
- `tests/unit/`: mainモジュールのユニットテスト
- `tests/integration/`: 統合テスト

---

## 既知の制約事項

### 1. main.py initコマンドのテスト

**制約**: main.pyの内部実装に強く依存しているため、main.pyの変更によりテストが失敗する可能性がある

**対策**: main.pyの変更時には、テストコードも同時に更新する

### 2. GitHub APIの実際の通信テスト

**制約**: 実際のGitHub APIを使用するテストは、テストリポジトリへのアクセス権が必要

**対策**: CI/CD環境では専用のテストリポジトリを使用する

### 3. モックの限界

**制約**: モックでは実際のGitHub APIの動作を完全に再現できない

**対策**: 統合テストで実際のGitHub APIを使用したテストを追加（CI/CD環境のみ）

---

## 次のステップ

### Phase 6（testing）

以下のテストを実行します：

1. **ローカルテスト実行**:
   ```bash
   pytest tests/unit/ -v
   pytest tests/integration/ -v
   ```

2. **カバレッジ確認**:
   ```bash
   pytest tests/unit/ tests/integration/ --cov=scripts/ai-workflow --cov-report=html
   ```
   - 目標カバレッジ: 85%以上

3. **Docker環境テスト**:
   - Dockerイメージビルド
   - Docker環境でのテスト実行

4. **CI/CDテスト**:
   - JenkinsでのE2Eテスト実行
   - テストリポジトリでのPR作成確認

---

## 参考情報

### テストファイル

1. **tests/unit/core/test_github_client.py** - GitHubClientのユニットテスト（拡張）
2. **tests/unit/test_main_init_pr.py** - main.py initコマンドのユニットテスト（新規）
3. **tests/integration/test_init_pr_workflow.py** - init PR workflowの統合テスト（新規）

### テストシナリオ

- **test-scenario.md** - Phase 3で作成されたテストシナリオ（25個のテストケース）

### 実装コード

- **core/github_client.py:336-525** - GitHubClient PR作成機能の実装
- **main.py:406-492** - main.py init コマンド拡張

---

**テストコード実装ログバージョン**: 1.0.0
**作成日**: 2025-10-12
**次のフェーズ**: Phase 6（testing）

**テストコード実装完了**: すべてのテストシナリオに基づいてテストコードが実装されました。Phase 6でテストを実行します。
