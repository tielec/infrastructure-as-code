"""
Unit tests for core/github/pr_client.py

Test Scenarios:
- UT-PC-001: PRClient.create_pull_request() - ドラフトPR作成
- UT-PC-002: PRClient.create_pull_request() - ブランチ不存在
- UT-PC-003: PRClient.check_existing_pr() - PR存在
- UT-PC-004: PRClient.check_existing_pr() - PR不存在
- UT-PC-005: PRClient.update_pull_request() - 正常系
"""
import pytest
from unittest.mock import Mock
from github import GithubException
from core.github.pr_client import PRClient


class TestPRClient:
    """PRClient クラスのユニットテスト"""

    def test_create_pull_request_as_draft_succeeds(self):
        """UT-PC-001: ドラフトPRが正しく作成されることを確認"""
        # Given: GitHub APIのモック
        mock_github = Mock()
        mock_repository = Mock()

        # PRのモック
        mock_pr = Mock()
        mock_pr.html_url = "https://github.com/tielec/infrastructure-as-code/pull/123"
        mock_pr.number = 123

        mock_repository.create_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repository

        pr_client = PRClient(mock_github, "tielec/infrastructure-as-code")

        # When: ドラフトPRを作成
        result = pr_client.create_pull_request(
            title="[ai-workflow] Issue #376",
            body="## Summary\n\nTest PR",
            head="ai-workflow/issue-376",
            base="main",
            draft=True
        )

        # Then: PRが作成される
        assert result['success'] is True
        assert result['pr_url'] == "https://github.com/tielec/infrastructure-as-code/pull/123"
        assert result['pr_number'] == 123
        assert result['error'] is None

        # create_pullが正しいパラメータで呼ばれる
        mock_repository.create_pull.assert_called_once_with(
            title="[ai-workflow] Issue #376",
            body="## Summary\n\nTest PR",
            head="ai-workflow/issue-376",
            base="main",
            draft=True
        )

    def test_create_pull_request_fails_when_branch_not_exists(self):
        """UT-PC-002: ブランチが存在しない場合にエラーが返されることを確認"""
        # Given: ブランチが存在しないエラーを発生させるモック
        mock_github = Mock()
        mock_repository = Mock()

        mock_repository.create_pull.side_effect = GithubException(
            status=422,
            data={"message": "Validation Failed", "errors": [{"message": "Branch not found"}]}
        )

        mock_github.get_repo.return_value = mock_repository

        pr_client = PRClient(mock_github, "tielec/infrastructure-as-code")

        # When: 存在しないブランチでPRを作成
        result = pr_client.create_pull_request(
            title="[ai-workflow] Issue #376",
            body="Test PR",
            head="non-existent-branch",
            base="main",
            draft=True
        )

        # Then: エラーが返される
        assert result['success'] is False
        assert result['pr_url'] is None
        assert result['pr_number'] is None
        assert result['error'] is not None

    def test_check_existing_pr_returns_pr_info_when_exists(self):
        """UT-PC-003: 既存PRが正しく検出されることを確認"""
        # Given: 既存PRがあるモック
        mock_github = Mock()
        mock_repository = Mock()

        # ownerのモック
        mock_owner = Mock()
        mock_owner.login = "tielec"
        mock_repository.owner = mock_owner

        # PRのモック
        mock_pr = Mock()
        mock_pr.number = 123
        mock_pr.html_url = "https://github.com/tielec/infrastructure-as-code/pull/123"
        mock_pr.state = "open"

        # get_pullsがPRを返す
        mock_repository.get_pulls.return_value = [mock_pr]

        mock_github.get_repo.return_value = mock_repository

        pr_client = PRClient(mock_github, "tielec/infrastructure-as-code")

        # When: 既存PRをチェック
        result = pr_client.check_existing_pr(
            head="ai-workflow/issue-376",
            base="main"
        )

        # Then: PR情報が返される
        assert result is not None
        assert result['pr_number'] == 123
        assert result['pr_url'] == "https://github.com/tielec/infrastructure-as-code/pull/123"
        assert result['state'] == "open"

        # get_pullsが正しいパラメータで呼ばれる
        mock_repository.get_pulls.assert_called_once_with(
            state='open',
            head='tielec:ai-workflow/issue-376',
            base='main'
        )

    def test_check_existing_pr_returns_none_when_not_exists(self):
        """UT-PC-004: PRが存在しない場合にNoneが返されることを確認"""
        # Given: PRが存在しないモック
        mock_github = Mock()
        mock_repository = Mock()

        mock_owner = Mock()
        mock_owner.login = "tielec"
        mock_repository.owner = mock_owner

        # get_pullsが空リストを返す
        mock_repository.get_pulls.return_value = []

        mock_github.get_repo.return_value = mock_repository

        pr_client = PRClient(mock_github, "tielec/infrastructure-as-code")

        # When: 存在しないPRをチェック
        result = pr_client.check_existing_pr(
            head="ai-workflow/issue-376",
            base="main"
        )

        # Then: Noneが返される
        assert result is None

    def test_check_existing_pr_handles_api_error(self):
        """APIエラー時にNoneが返されることを確認"""
        # Given: APIエラーを発生させるモック
        mock_github = Mock()
        mock_repository = Mock()

        mock_repository.owner = Mock(login="tielec")
        mock_repository.get_pulls.side_effect = Exception("API Error")

        mock_github.get_repo.return_value = mock_repository

        pr_client = PRClient(mock_github, "tielec/infrastructure-as-code")

        # When: 既存PRをチェック
        result = pr_client.check_existing_pr(
            head="ai-workflow/issue-376",
            base="main"
        )

        # Then: Noneが返される（エラーハンドリング）
        assert result is None

    def test_update_pull_request_succeeds(self):
        """UT-PC-005: PR本文が正しく更新されることを確認"""
        # Given: GitHub APIのモック
        mock_github = Mock()
        mock_repository = Mock()

        # PRのモック
        mock_pr = Mock()
        mock_pr.edit = Mock()

        mock_repository.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repository

        pr_client = PRClient(mock_github, "tielec/infrastructure-as-code")

        # When: PR本文を更新
        result = pr_client.update_pull_request(
            pr_number=123,
            body="## Updated Summary\n\nNew content"
        )

        # Then: 更新が成功する
        assert result['success'] is True
        assert result['error'] is None

        # editが正しいパラメータで呼ばれる
        mock_repository.get_pull.assert_called_once_with(123)
        mock_pr.edit.assert_called_once_with(body="## Updated Summary\n\nNew content")

    def test_update_pull_request_handles_error(self):
        """PR更新失敗時にエラーが返されることを確認"""
        # Given: 更新がエラーを発生させるモック
        mock_github = Mock()
        mock_repository = Mock()

        mock_repository.get_pull.side_effect = GithubException(
            status=404,
            data={"message": "Not Found"}
        )

        mock_github.get_repo.return_value = mock_repository

        pr_client = PRClient(mock_github, "tielec/infrastructure-as-code")

        # When: 存在しないPRを更新
        result = pr_client.update_pull_request(
            pr_number=99999,
            body="New content"
        )

        # Then: エラーが返される
        assert result['success'] is False
        assert result['error'] is not None
        assert "Not Found" in result['error']

    def test_create_pull_request_without_draft(self):
        """draft=Falseで通常のPRが作成されることを確認"""
        # Given: GitHub APIのモック
        mock_github = Mock()
        mock_repository = Mock()

        mock_pr = Mock()
        mock_pr.html_url = "https://github.com/test/repo/pull/1"
        mock_pr.number = 1

        mock_repository.create_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repository

        pr_client = PRClient(mock_github, "test/repo")

        # When: 通常のPRを作成
        result = pr_client.create_pull_request(
            title="Test PR",
            body="Test",
            head="feature",
            base="main",
            draft=False
        )

        # Then: draft=Falseで作成される
        assert result['success'] is True
        mock_repository.create_pull.assert_called_once_with(
            title="Test PR",
            body="Test",
            head="feature",
            base="main",
            draft=False
        )
