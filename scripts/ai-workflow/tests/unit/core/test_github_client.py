"""GitHub Client ユニットテスト

GitHub APIクライアントの動作確認
"""
import pytest
from core.github_client import GitHubClient


@pytest.mark.unit
@pytest.mark.requires_github
class TestGitHubClient:
    """GitHubClientクラスのユニットテスト"""

    def test_client_initialization(self, github_token, github_repository):
        """クライアントの初期化テスト"""
        client = GitHubClient(token=github_token, repository=github_repository)
        assert client.repository == github_repository

    def test_get_issue_info(self, github_token, github_repository, test_issue_number):
        """Issue情報取得テスト"""
        client = GitHubClient(token=github_token, repository=github_repository)
        issue_info = client.get_issue_info(int(test_issue_number))

        assert 'title' in issue_info
        assert 'state' in issue_info
        assert 'url' in issue_info
        assert issue_info['number'] == int(test_issue_number)

    def test_get_issue_comments(self, github_token, github_repository, test_issue_number):
        """Issueコメント取得テスト"""
        client = GitHubClient(token=github_token, repository=github_repository)
        comments = client.get_issue_comments_dict(int(test_issue_number))

        assert isinstance(comments, list)

        # コメントがある場合、構造を検証
        if comments:
            comment = comments[0]
            assert 'id' in comment
            assert 'user' in comment
            assert 'created_at' in comment
            assert 'body' in comment


@pytest.mark.unit
class TestGitHubClientPR:
    """GitHubClient PR作成機能のユニットテスト (Issue #355)"""

    # TC-U-001: PR作成_正常系
    def test_create_pull_request_success(self, mocker):
        """
        TC-U-001: PR作成が正常に成功することを検証

        Given: GitHubClientが初期化されている
        When: create_pull_request()を呼び出す
        Then: PR作成が成功し、PR URLとPR番号が返される
        """
        # モックの準備
        mock_pr = mocker.Mock()
        mock_pr.html_url = 'https://github.com/owner/repo/pull/123'
        mock_pr.number = 123

        mock_repository = mocker.Mock()
        mock_repository.create_pull.return_value = mock_pr

        # GitHubClientのインスタンス作成
        client = GitHubClient(token='test_token', repository='owner/repo')
        client.repository = mock_repository

        # テスト実行
        result = client.create_pull_request(
            title='[AI-Workflow] Issue #355',
            body='## AI Workflow自動生成PR\n\nCloses #355',
            head='ai-workflow/issue-355',
            base='main',
            draft=True
        )

        # アサーション
        assert result['success'] is True
        assert result['pr_url'] == 'https://github.com/owner/repo/pull/123'
        assert result['pr_number'] == 123
        assert result['error'] is None

        # create_pullが正しいパラメータで呼ばれたことを確認
        mock_repository.create_pull.assert_called_once_with(
            title='[AI-Workflow] Issue #355',
            body='## AI Workflow自動生成PR\n\nCloses #355',
            head='ai-workflow/issue-355',
            base='main',
            draft=True
        )

    # TC-U-002: PR作成_認証エラー
    def test_create_pull_request_auth_error(self, mocker):
        """
        TC-U-002: GitHub Token権限不足時に適切なエラーメッセージが返されることを検証

        Given: GitHubClientが初期化されている
        When: GitHub Tokenに権限がなくcreate_pull_request()を呼び出す
        Then: 権限エラーのメッセージが返される
        """
        from github import GithubException

        # モックの準備（401エラーをシミュレート）
        mock_repository = mocker.Mock()
        mock_repository.create_pull.side_effect = GithubException(
            status=401,
            data={'message': 'Bad credentials'},
            headers={}
        )

        # GitHubClientのインスタンス作成
        client = GitHubClient(token='invalid_token', repository='owner/repo')
        client.repository = mock_repository

        # テスト実行
        result = client.create_pull_request(
            title='[AI-Workflow] Issue #355',
            body='## AI Workflow自動生成PR',
            head='ai-workflow/issue-355',
            base='main',
            draft=True
        )

        # アサーション
        assert result['success'] is False
        assert result['pr_url'] is None
        assert result['pr_number'] is None
        assert "GitHub Token lacks 'repo' scope" in result['error']

    # TC-U-003: PR作成_既存PR重複エラー
    def test_create_pull_request_existing_pr(self, mocker):
        """
        TC-U-003: 既存PRが存在する場合に適切なエラーメッセージが返されることを検証

        Given: GitHubClientが初期化されている
        When: 既存PRが存在する状態でcreate_pull_request()を呼び出す
        Then: 既存PR重複エラーのメッセージが返される
        """
        from github import GithubException

        # モックの準備（422エラーをシミュレート）
        mock_repository = mocker.Mock()
        mock_repository.create_pull.side_effect = GithubException(
            status=422,
            data={'message': 'Validation Failed: A pull request already exists'},
            headers={}
        )

        # GitHubClientのインスタンス作成
        client = GitHubClient(token='test_token', repository='owner/repo')
        client.repository = mock_repository

        # テスト実行
        result = client.create_pull_request(
            title='[AI-Workflow] Issue #355',
            body='## AI Workflow自動生成PR',
            head='ai-workflow/issue-355',
            base='main',
            draft=True
        )

        # アサーション
        assert result['success'] is False
        assert result['pr_url'] is None
        assert result['pr_number'] is None
        assert "A pull request already exists" in result['error']

    # TC-U-004: PR作成_ネットワークエラー
    def test_create_pull_request_network_error(self, mocker):
        """
        TC-U-004: ネットワークエラー時に適切なエラーメッセージが返されることを検証

        Given: GitHubClientが初期化されている
        When: ネットワークエラーが発生した状態でcreate_pull_request()を呼び出す
        Then: 予期しないエラーのメッセージが返される
        """
        # モックの準備（一般的なExceptionをシミュレート）
        mock_repository = mocker.Mock()
        mock_repository.create_pull.side_effect = Exception('Network unreachable')

        # GitHubClientのインスタンス作成
        client = GitHubClient(token='test_token', repository='owner/repo')
        client.repository = mock_repository

        # テスト実行
        result = client.create_pull_request(
            title='[AI-Workflow] Issue #355',
            body='## AI Workflow自動生成PR',
            head='ai-workflow/issue-355',
            base='main',
            draft=True
        )

        # アサーション
        assert result['success'] is False
        assert result['pr_url'] is None
        assert result['pr_number'] is None
        assert 'Unexpected error' in result['error']
        assert 'Network unreachable' in result['error']

    # TC-U-005: 既存PRチェック_PR存在
    def test_check_existing_pr_found(self, mocker):
        """
        TC-U-005: 既存PRが存在する場合にPR情報が返されることを検証

        Given: GitHubClientが初期化されている
        When: 既存PRが存在する状態でcheck_existing_pr()を呼び出す
        Then: 既存PR情報が返される
        """
        # モックの準備
        mock_pr = mocker.Mock()
        mock_pr.number = 123
        mock_pr.html_url = 'https://github.com/owner/repo/pull/123'
        mock_pr.state = 'open'

        mock_owner = mocker.Mock()
        mock_owner.login = 'owner'

        mock_repository = mocker.Mock()
        mock_repository.owner = mock_owner
        mock_repository.get_pulls.return_value = [mock_pr]  # イテレータをリストで模倣

        # GitHubClientのインスタンス作成
        client = GitHubClient(token='test_token', repository='owner/repo')
        client.repository = mock_repository

        # テスト実行
        result = client.check_existing_pr(
            head='ai-workflow/issue-355',
            base='main'
        )

        # アサーション
        assert result is not None
        assert result['pr_number'] == 123
        assert result['pr_url'] == 'https://github.com/owner/repo/pull/123'
        assert result['state'] == 'open'

        # get_pullsが正しいパラメータで呼ばれたことを確認
        mock_repository.get_pulls.assert_called_once_with(
            state='open',
            head='owner:ai-workflow/issue-355',
            base='main'
        )

    # TC-U-006: 既存PRチェック_PR不存在
    def test_check_existing_pr_not_found(self, mocker):
        """
        TC-U-006: 既存PRが存在しない場合にNoneが返されることを検証

        Given: GitHubClientが初期化されている
        When: 既存PRが存在しない状態でcheck_existing_pr()を呼び出す
        Then: Noneが返される
        """
        # モックの準備
        mock_owner = mocker.Mock()
        mock_owner.login = 'owner'

        mock_repository = mocker.Mock()
        mock_repository.owner = mock_owner
        mock_repository.get_pulls.return_value = []  # 空のリスト

        # GitHubClientのインスタンス作成
        client = GitHubClient(token='test_token', repository='owner/repo')
        client.repository = mock_repository

        # テスト実行
        result = client.check_existing_pr(
            head='ai-workflow/issue-355',
            base='main'
        )

        # アサーション
        assert result is None

    # TC-U-007: 既存PRチェック_APIエラー
    def test_check_existing_pr_api_error(self, mocker, capsys):
        """
        TC-U-007: GitHub APIエラー時にNoneが返され、警告ログが出力されることを検証

        Given: GitHubClientが初期化されている
        When: GitHub APIエラーが発生した状態でcheck_existing_pr()を呼び出す
        Then: Noneが返され、警告ログが出力される
        """
        from github import GithubException

        # モックの準備
        mock_owner = mocker.Mock()
        mock_owner.login = 'owner'

        mock_repository = mocker.Mock()
        mock_repository.owner = mock_owner
        mock_repository.get_pulls.side_effect = GithubException(
            status=500,
            data={'message': 'Internal Server Error'},
            headers={}
        )

        # GitHubClientのインスタンス作成
        client = GitHubClient(token='test_token', repository='owner/repo')
        client.repository = mock_repository

        # テスト実行
        result = client.check_existing_pr(
            head='ai-workflow/issue-355',
            base='main'
        )

        # アサーション
        assert result is None

        # 警告ログが出力されることを確認
        captured = capsys.readouterr()
        assert '[WARNING] Failed to check existing PR' in captured.out

    # TC-U-008: PR本文テンプレート生成_正常系
    def test_generate_pr_body_template_success(self):
        """
        TC-U-008: PR本文テンプレートが正しい形式で生成されることを検証

        Given: GitHubClientが初期化されている
        When: _generate_pr_body_template()を呼び出す
        Then: 正しい形式のPR本文が生成される
        """
        # GitHubClientのインスタンス作成
        client = GitHubClient(token='test_token', repository='owner/repo')

        # テスト実行
        body = client._generate_pr_body_template(
            issue_number=355,
            branch_name='ai-workflow/issue-355'
        )

        # アサーション
        assert 'Closes #355' in body
        assert '- [x] Phase 0: Planning' in body
        assert '- [ ] Phase 1: Requirements' in body
        assert '.ai-workflow/issue-355/' in body
        assert 'ai-workflow/issue-355' in body
        assert 'Claude Code Pro Max' in body
        assert 'ContentParser' in body

    # TC-U-009: PR本文テンプレート生成_異なるIssue番号
    def test_generate_pr_body_template_different_issue(self):
        """
        TC-U-009: 異なるIssue番号に対応したテンプレートが生成されることを検証

        Given: GitHubClientが初期化されている
        When: 異なるIssue番号で_generate_pr_body_template()を呼び出す
        Then: 該当するIssue番号のPR本文が生成される
        """
        # GitHubClientのインスタンス作成
        client = GitHubClient(token='test_token', repository='owner/repo')

        # テスト実行
        body = client._generate_pr_body_template(
            issue_number=999,
            branch_name='ai-workflow/issue-999'
        )

        # アサーション
        assert 'Closes #999' in body
        assert '.ai-workflow/issue-999/' in body
        assert 'ai-workflow/issue-999' in body


@pytest.mark.unit
class TestGitHubClientPRUpdate:
    """GitHubClient PR更新機能のユニットテスト (Issue #363)"""

    # UT-01: update_pull_request_正常系
    def test_update_pull_request_success(self, mocker):
        """
        UT-01: PR本文が正常に更新されることを検証

        Given: GitHubClientが初期化されている、PR #123が存在する
        When: update_pull_request()を呼び出す
        Then: PR本文が更新され、success=Trueが返される
        """
        # モックの準備
        mock_pr = mocker.Mock()
        mock_pr.edit = mocker.Mock()

        mock_repository = mocker.Mock()
        mock_repository.get_pull.return_value = mock_pr

        # GitHubClientのインスタンス作成
        client = GitHubClient(token='test_token', repository='owner/repo')
        client.repository = mock_repository

        # テスト実行
        result = client.update_pull_request(
            pr_number=123,
            body='## 更新されたPR本文\n\n詳細な内容...'
        )

        # アサーション
        assert result['success'] is True
        assert result['error'] is None

        # get_pullとeditが正しいパラメータで呼ばれたことを確認
        mock_repository.get_pull.assert_called_once_with(123)
        mock_pr.edit.assert_called_once_with(body='## 更新されたPR本文\n\n詳細な内容...')

    # UT-02: update_pull_request_PR未存在エラー
    def test_update_pull_request_not_found(self, mocker):
        """
        UT-02: 存在しないPR番号が指定された場合のエラーハンドリングを検証

        Given: GitHubClientが初期化されている、PR #999が存在しない
        When: update_pull_request()を呼び出す
        Then: success=False、PR未存在エラーが返される
        """
        from github import GithubException

        # モックの準備（404エラーをシミュレート）
        mock_repository = mocker.Mock()
        mock_repository.get_pull.side_effect = GithubException(
            status=404,
            data={'message': 'Not Found'},
            headers={}
        )

        # GitHubClientのインスタンス作成
        client = GitHubClient(token='test_token', repository='owner/repo')
        client.repository = mock_repository

        # テスト実行
        result = client.update_pull_request(
            pr_number=999,
            body='## 更新されたPR本文'
        )

        # アサーション
        assert result['success'] is False
        assert result['error'] == 'PR #999 not found'

    # UT-03: update_pull_request_権限エラー
    def test_update_pull_request_permission_error(self, mocker):
        """
        UT-03: GitHub Tokenに権限がない場合のエラーハンドリングを検証

        Given: GitHubClientが初期化されている、GitHub Tokenに権限がない
        When: update_pull_request()を呼び出す
        Then: success=False、権限不足エラーが返される
        """
        from github import GithubException

        # モックの準備（403エラーをシミュレート）
        mock_pr = mocker.Mock()
        mock_pr.edit.side_effect = GithubException(
            status=403,
            data={'message': 'Forbidden'},
            headers={}
        )

        mock_repository = mocker.Mock()
        mock_repository.get_pull.return_value = mock_pr

        # GitHubClientのインスタンス作成
        client = GitHubClient(token='test_token', repository='owner/repo')
        client.repository = mock_repository

        # テスト実行
        result = client.update_pull_request(
            pr_number=123,
            body='## 更新されたPR本文'
        )

        # アサーション
        assert result['success'] is False
        assert result['error'] == 'GitHub Token lacks PR edit permissions'

    # UT-04: update_pull_request_API制限エラー
    def test_update_pull_request_rate_limit_error(self, mocker):
        """
        UT-04: GitHub API rate limit到達時のエラーハンドリングを検証

        Given: GitHubClientが初期化されている、GitHub APIのrate limitに到達
        When: update_pull_request()を呼び出す
        Then: success=False、rate limitエラーが返される
        """
        from github import GithubException

        # モックの準備（429エラーをシミュレート）
        mock_repository = mocker.Mock()
        mock_repository.get_pull.side_effect = GithubException(
            status=429,
            data={'message': 'API rate limit exceeded'},
            headers={}
        )

        # GitHubClientのインスタンス作成
        client = GitHubClient(token='test_token', repository='owner/repo')
        client.repository = mock_repository

        # テスト実行
        result = client.update_pull_request(
            pr_number=123,
            body='## 更新されたPR本文'
        )

        # アサーション
        assert result['success'] is False
        assert result['error'] == 'GitHub API rate limit exceeded'

    # UT-05: update_pull_request_予期しないエラー
    def test_update_pull_request_unexpected_error(self, mocker):
        """
        UT-05: 予期しない例外発生時のエラーハンドリングを検証

        Given: GitHubClientが初期化されている
        When: 予期しない例外が発生
        Then: success=False、予期しないエラーメッセージが返される
        """
        # モックの準備（一般的なExceptionをシミュレート）
        mock_repository = mocker.Mock()
        mock_repository.get_pull.side_effect = Exception('Network error')

        # GitHubClientのインスタンス作成
        client = GitHubClient(token='test_token', repository='owner/repo')
        client.repository = mock_repository

        # テスト実行
        result = client.update_pull_request(
            pr_number=123,
            body='## 更新されたPR本文'
        )

        # アサーション
        assert result['success'] is False
        assert 'Unexpected error' in result['error']
        assert 'Network error' in result['error']

    # UT-06: _generate_pr_body_detailed_正常系
    def test_generate_pr_body_detailed_success(self, mocker):
        """
        UT-06: テンプレートから詳細版PR本文が正しく生成されることを検証

        Given: GitHubClientが初期化されている、テンプレートファイルが存在する
        When: _generate_pr_body_detailed()を呼び出す
        Then: プレースホルダーが正しく置換されたPR本文が返される
        """
        from pathlib import Path

        # モックの準備（テンプレートファイル読み込み）
        template_content = """## AI Workflow自動生成PR

### 📋 関連Issue
Closes #{issue_number}

### 📝 変更サマリー
{summary}

### 🔧 実装詳細
{implementation_details}

### ✅ テスト結果
{test_results}

### 📚 ドキュメント更新
{documentation_updates}

### 👀 レビューポイント
{review_points}

### ⚙️ 実行環境
- **ブランチ**: {branch_name}
"""

        mock_open = mocker.mock_open(read_data=template_content)
        mocker.patch('builtins.open', mock_open)

        # GitHubClientのインスタンス作成
        client = GitHubClient(token='test_token', repository='owner/repo')

        # テスト実行
        extracted_info = {
            'summary': '変更サマリーのテスト',
            'implementation_details': '実装詳細のテスト',
            'test_results': 'テスト結果のテスト',
            'documentation_updates': 'ドキュメント更新のテスト',
            'review_points': 'レビューポイントのテスト'
        }

        body = client._generate_pr_body_detailed(
            issue_number=363,
            branch_name='ai-workflow/issue-363',
            extracted_info=extracted_info
        )

        # アサーション
        assert 'Closes #363' in body
        assert 'ai-workflow/issue-363' in body
        assert '変更サマリーのテスト' in body
        assert '実装詳細のテスト' in body
        assert 'テスト結果のテスト' in body
        assert 'ドキュメント更新のテスト' in body
        assert 'レビューポイントのテスト' in body

    # UT-07: _generate_pr_body_detailed_テンプレート未存在エラー
    def test_generate_pr_body_detailed_template_not_found(self, mocker):
        """
        UT-07: テンプレートファイルが存在しない場合のエラーハンドリングを検証

        Given: GitHubClientが初期化されている、テンプレートファイルが存在しない
        When: _generate_pr_body_detailed()を呼び出す
        Then: FileNotFoundErrorが発生する
        """
        # モックの準備（ファイルが見つからない）
        mocker.patch('builtins.open', side_effect=FileNotFoundError())

        # GitHubClientのインスタンス作成
        client = GitHubClient(token='test_token', repository='owner/repo')

        # テスト実行とアサーション
        extracted_info = {
            'summary': 'test',
            'implementation_details': 'test',
            'test_results': 'test',
            'documentation_updates': 'test',
            'review_points': 'test'
        }

        with pytest.raises(FileNotFoundError) as exc_info:
            client._generate_pr_body_detailed(
                issue_number=363,
                branch_name='ai-workflow/issue-363',
                extracted_info=extracted_info
            )

        assert 'Template file not found' in str(exc_info.value)

    # UT-08: _generate_pr_body_detailed_プレースホルダー欠落エラー
    def test_generate_pr_body_detailed_missing_placeholder(self, mocker):
        """
        UT-08: 必須プレースホルダーが欠落している場合のエラーハンドリングを検証

        Given: GitHubClientが初期化されている
        When: extracted_infoに必須フィールドが欠落
        Then: KeyErrorが発生する
        """
        # モックの準備（テンプレートファイル読み込み）
        template_content = "{summary}\n{implementation_details}\n{missing_field}"
        mock_open = mocker.mock_open(read_data=template_content)
        mocker.patch('builtins.open', mock_open)

        # GitHubClientのインスタンス作成
        client = GitHubClient(token='test_token', repository='owner/repo')

        # テスト実行とアサーション（missing_fieldが欠落）
        extracted_info = {
            'summary': 'test',
            'implementation_details': 'test'
            # missing_field が欠落
        }

        with pytest.raises(KeyError) as exc_info:
            client._generate_pr_body_detailed(
                issue_number=363,
                branch_name='ai-workflow/issue-363',
                extracted_info=extracted_info
            )

        assert 'Missing placeholder in template' in str(exc_info.value)

    # UT-09: _extract_phase_outputs_正常系
    def test_extract_phase_outputs_success(self, mocker):
        """
        UT-09: 各フェーズの成果物から情報が正しく抽出されることを検証

        Given: GitHubClientが初期化されている、全フェーズの成果物が存在する
        When: _extract_phase_outputs()を呼び出す
        Then: 各フィールドに期待される内容が含まれる
        """
        from pathlib import Path

        # モックの準備
        mock_issue = mocker.Mock()
        mock_issue.body = """## 概要

AI Workflowの全フェーズ完了後にPR本文を更新する機能を実装する。
"""

        mock_repository = mocker.Mock()
        mock_repository.get_issue.return_value = mock_issue

        client = GitHubClient(token='test_token', repository='owner/repo')
        client.repository = mock_repository

        # 成果物ファイルのモック
        implementation_content = """# 実装ログ

## 実装内容

主要な変更ファイル:
- file1.py: 変更内容1
- file2.py: 変更内容2
"""

        test_result_content = """# テスト結果

## テスト結果サマリー

### カバレッジ
- ユニットテスト: 15件 (全てPASS)
- カバレッジ: 85%
"""

        documentation_content = """# ドキュメント更新ログ

## 更新されたドキュメント

- `README.md`: 機能説明を追加
- `API.md`: 新規API追加
"""

        design_content = """# 詳細設計書

## レビューポイント

1. エラーハンドリングが適切か
2. パース処理が堅牢か
"""

        # Pathのモック
        mock_impl_path = mocker.Mock(spec=Path)
        mock_impl_path.exists.return_value = True
        mock_impl_path.read_text.return_value = implementation_content

        mock_test_path = mocker.Mock(spec=Path)
        mock_test_path.exists.return_value = True
        mock_test_path.read_text.return_value = test_result_content

        mock_doc_path = mocker.Mock(spec=Path)
        mock_doc_path.exists.return_value = True
        mock_doc_path.read_text.return_value = documentation_content

        mock_design_path = mocker.Mock(spec=Path)
        mock_design_path.exists.return_value = True
        mock_design_path.read_text.return_value = design_content

        phase_outputs = {
            'implementation': mock_impl_path,
            'test_result': mock_test_path,
            'documentation': mock_doc_path,
            'design': mock_design_path
        }

        # テスト実行
        result = client._extract_phase_outputs(
            issue_number=363,
            phase_outputs=phase_outputs
        )

        # アサーション
        assert 'summary' in result
        assert 'AI Workflowの全フェーズ完了後にPR本文を更新する機能を実装する' in result['summary']
        assert 'implementation_details' in result
        assert 'file1.py' in result['implementation_details']
        assert 'test_results' in result
        assert 'カバレッジ' in result['test_results']
        assert 'documentation_updates' in result
        assert 'README.md' in result['documentation_updates']
        assert 'review_points' in result
        assert 'エラーハンドリング' in result['review_points']

    # UT-10: _extract_phase_outputs_成果物欠落時のフォールバック
    def test_extract_phase_outputs_missing_files(self, mocker):
        """
        UT-10: 成果物ファイルが欠落している場合のデフォルト値設定を検証

        Given: GitHubClientが初期化されている、Phase 4の成果物が存在しない
        When: _extract_phase_outputs()を呼び出す
        Then: 欠落フィールドにデフォルト値が設定される
        """
        from pathlib import Path

        # モックの準備
        mock_issue = mocker.Mock()
        mock_issue.body = "## 概要\n\n概要テスト"

        mock_repository = mocker.Mock()
        mock_repository.get_issue.return_value = mock_issue

        client = GitHubClient(token='test_token', repository='owner/repo')
        client.repository = mock_repository

        # implementation.mdは存在しない
        mock_impl_path = mocker.Mock(spec=Path)
        mock_impl_path.exists.return_value = False

        # 他のファイルは存在する
        mock_test_path = mocker.Mock(spec=Path)
        mock_test_path.exists.return_value = True
        mock_test_path.read_text.return_value = "## テスト結果サマリー\n\nテストOK"

        mock_doc_path = mocker.Mock(spec=Path)
        mock_doc_path.exists.return_value = True
        mock_doc_path.read_text.return_value = "## 更新されたドキュメント\n\nREADME.md"

        mock_design_path = mocker.Mock(spec=Path)
        mock_design_path.exists.return_value = True
        mock_design_path.read_text.return_value = "## レビューポイント\n\nレビューテスト"

        phase_outputs = {
            'implementation': mock_impl_path,
            'test_result': mock_test_path,
            'documentation': mock_doc_path,
            'design': mock_design_path
        }

        # テスト実行
        result = client._extract_phase_outputs(
            issue_number=363,
            phase_outputs=phase_outputs
        )

        # アサーション
        assert result['implementation_details'] == '（実装詳細の記載なし）'
        assert 'テストOK' in result['test_results']
        assert 'README.md' in result['documentation_updates']
        assert 'レビューテスト' in result['review_points']

    # UT-11: _extract_phase_outputs_Issue取得エラー
    def test_extract_phase_outputs_issue_error(self, mocker, capsys):
        """
        UT-11: Issue本文取得失敗時のエラーハンドリングを検証

        Given: GitHubClientが初期化されている
        When: GitHub APIからIssue取得が失敗する
        Then: 全フィールドにエラー表示が設定される
        """
        from pathlib import Path
        from github import GithubException

        # モックの準備（Issue取得失敗）
        mock_repository = mocker.Mock()
        mock_repository.get_issue.side_effect = GithubException(
            status=404,
            data={'message': 'Not Found'},
            headers={}
        )

        client = GitHubClient(token='test_token', repository='owner/repo')
        client.repository = mock_repository

        phase_outputs = {}

        # テスト実行
        result = client._extract_phase_outputs(
            issue_number=999,
            phase_outputs=phase_outputs
        )

        # アサーション
        assert result['summary'] == '（情報抽出エラー）'
        assert result['implementation_details'] == '（情報抽出エラー）'
        assert result['test_results'] == '（情報抽出エラー）'
        assert result['documentation_updates'] == '（情報抽出エラー）'
        assert result['review_points'] == '（情報抽出エラー）'

        # 警告ログが出力されることを確認
        captured = capsys.readouterr()
        assert '[WARNING] 成果物抽出中にエラー' in captured.out

    # UT-12: _extract_section_正常系
    def test_extract_section_success(self):
        """
        UT-12: Markdownセクションが正しく抽出されることを検証

        Given: GitHubClientが初期化されている、Markdown文書に対象セクションが存在する
        When: _extract_section()を呼び出す
        Then: セクションヘッダー以降、次のセクションまでの内容が抽出される
        """
        client = GitHubClient(token='test_token', repository='owner/repo')

        content = """# タイトル

## 実装内容

主要な変更ファイル:
- file1.py: 変更内容1
- file2.py: 変更内容2

## テスト結果

テストは全てPASSしました。
"""

        # テスト実行
        result = client._extract_section(content, '## 実装内容')

        # アサーション
        assert '主要な変更ファイル' in result
        assert 'file1.py' in result
        assert 'file2.py' in result
        assert 'テストは全てPASS' not in result  # 次のセクションは含まれない

    # UT-13: _extract_section_セクション未存在
    def test_extract_section_not_found(self):
        """
        UT-13: 対象セクションが存在しない場合の動作を検証

        Given: GitHubClientが初期化されている、Markdown文書に対象セクションが存在しない
        When: _extract_section()を呼び出す
        Then: 空文字列が返される
        """
        client = GitHubClient(token='test_token', repository='owner/repo')

        content = """# タイトル

## その他のセクション

内容...
"""

        # テスト実行
        result = client._extract_section(content, '## 実装内容')

        # アサーション
        assert result == ''

    # UT-14: _extract_section_複数セクション
    def test_extract_section_multiple_sections(self):
        """
        UT-14: 同名セクションが複数存在する場合、最初のセクションのみ抽出されることを検証

        Given: GitHubClientが初期化されている、同名セクションが2つ存在する
        When: _extract_section()を呼び出す
        Then: 最初のセクションのみが抽出される
        """
        client = GitHubClient(token='test_token', repository='owner/repo')

        content = """## 実装内容

最初のセクション内容

## 実装内容

2番目のセクション内容
"""

        # テスト実行
        result = client._extract_section(content, '## 実装内容')

        # アサーション
        assert '最初のセクション内容' in result
        assert '2番目のセクション内容' not in result
