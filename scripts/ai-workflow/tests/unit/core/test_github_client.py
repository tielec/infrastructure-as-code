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
