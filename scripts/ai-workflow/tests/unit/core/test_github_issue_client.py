"""
Unit tests for core/github/issue_client.py

Test Scenarios:
- UT-IC-001: IssueClient.get_issue() - 正常系
- UT-IC-002: IssueClient.get_issue() - Issue不存在
- UT-IC-003: IssueClient.get_issue_info() - 正常系
- UT-IC-004: IssueClient.close_issue() - 正常系
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from github import GithubException
from core.github.issue_client import IssueClient
from common.error_handler import GitHubAPIError


class TestIssueClient:
    """IssueClient クラスのユニットテスト"""

    def test_get_issue_returns_issue(self):
        """UT-IC-001: Issue情報が正しく取得されることを確認"""
        # Given: GitHub APIのモック
        mock_github = Mock()
        mock_repository = Mock()
        mock_issue = Mock()
        mock_issue.number = 376
        mock_issue.title = "[TASK] Test Issue"

        mock_repository.get_issue.return_value = mock_issue
        mock_github.get_repo.return_value = mock_repository

        issue_client = IssueClient(mock_github, "tielec/infrastructure-as-code")

        # When: Issue情報を取得
        result = issue_client.get_issue(376)

        # Then: Issueオブジェクトが返される
        assert result.number == 376
        assert result.title == "[TASK] Test Issue"
        mock_repository.get_issue.assert_called_once_with(number=376)

    def test_get_issue_raises_error_when_not_found(self):
        """UT-IC-002: 存在しないIssueでエラーが発生することを確認"""
        # Given: Issue取得がエラーを発生させるモック
        mock_github = Mock()
        mock_repository = Mock()
        mock_repository.get_issue.side_effect = GithubException(
            status=404,
            data={"message": "Not Found"}
        )

        mock_github.get_repo.return_value = mock_repository

        issue_client = IssueClient(mock_github, "tielec/infrastructure-as-code")

        # When/Then: GitHubAPIErrorが発生する
        with pytest.raises(GitHubAPIError, match="Failed to get issue #99999"):
            issue_client.get_issue(99999)

    def test_get_issue_info_returns_dict(self):
        """UT-IC-003: Issue情報が辞書形式で取得されることを確認"""
        # Given: GitHub APIのモック
        mock_github = Mock()
        mock_repository = Mock()

        # Issueのモック
        mock_issue = Mock()
        mock_issue.number = 376
        mock_issue.title = "[TASK] ai-workflowスクリプトの大規模リファクタリング"
        mock_issue.body = "## 概要\n\nリファクタリング..."
        mock_issue.state = "open"
        mock_issue.html_url = "https://github.com/tielec/infrastructure-as-code/issues/376"
        mock_issue.created_at = datetime(2025, 10, 12, 0, 0, 0)
        mock_issue.updated_at = datetime(2025, 10, 12, 1, 0, 0)

        # ラベルのモック
        mock_label = Mock()
        mock_label.name = "enhancement"
        mock_issue.labels = [mock_label]

        mock_repository.get_issue.return_value = mock_issue
        mock_github.get_repo.return_value = mock_repository

        issue_client = IssueClient(mock_github, "tielec/infrastructure-as-code")

        # When: Issue情報を辞書形式で取得
        info = issue_client.get_issue_info(376)

        # Then: 辞書形式で返される
        assert info['number'] == 376
        assert info['title'] == "[TASK] ai-workflowスクリプトの大規模リファクタリング"
        assert "リファクタリング" in info['body']
        assert info['state'] == "open"
        assert info['labels'] == ["enhancement"]
        assert info['url'] == "https://github.com/tielec/infrastructure-as-code/issues/376"
        assert '2025-10-12' in info['created_at']
        assert '2025-10-12' in info['updated_at']

    def test_get_issue_info_handles_empty_body(self):
        """Issue本文が空の場合の処理を確認"""
        # Given: 本文が空のIssueのモック
        mock_github = Mock()
        mock_repository = Mock()

        mock_issue = Mock()
        mock_issue.number = 376
        mock_issue.title = "Test Issue"
        mock_issue.body = None  # 本文なし
        mock_issue.state = "open"
        mock_issue.labels = []
        mock_issue.html_url = "https://github.com/test/repo/issues/376"
        mock_issue.created_at = datetime(2025, 10, 12)
        mock_issue.updated_at = datetime(2025, 10, 12)

        mock_repository.get_issue.return_value = mock_issue
        mock_github.get_repo.return_value = mock_repository

        issue_client = IssueClient(mock_github, "test/repo")

        # When: Issue情報を取得
        info = issue_client.get_issue_info(376)

        # Then: 本文が空文字列になる
        assert info['body'] == ''

    def test_close_issue_succeeds(self):
        """UT-IC-004: Issueが正しくクローズされることを確認"""
        # Given: GitHub APIのモック
        mock_github = Mock()
        mock_repository = Mock()

        mock_issue = Mock()
        mock_issue.create_comment = Mock()
        mock_issue.edit = Mock()

        mock_repository.get_issue.return_value = mock_issue
        mock_github.get_repo.return_value = mock_repository

        issue_client = IssueClient(mock_github, "tielec/infrastructure-as-code")

        # When: Issueをクローズ
        result = issue_client.close_issue(
            issue_number=376,
            reason="ワークフロー完了"
        )

        # Then: クローズが成功する
        assert result['success'] is True
        assert result['error'] is None

        # コメントが投稿される
        mock_issue.create_comment.assert_called_once()
        call_args = mock_issue.create_comment.call_args[0][0]
        assert "ワークフロー中止" in call_args
        assert "ワークフロー完了" in call_args

        # Issueがクローズされる
        mock_issue.edit.assert_called_once_with(state='closed')

    def test_close_issue_handles_error(self):
        """Issueクローズ失敗時にエラーが返されることを確認"""
        # Given: クローズがエラーを発生させるモック
        mock_github = Mock()
        mock_repository = Mock()

        mock_repository.get_issue.side_effect = GithubException(
            status=500,
            data={"message": "Internal Server Error"}
        )

        mock_github.get_repo.return_value = mock_repository

        issue_client = IssueClient(mock_github, "tielec/infrastructure-as-code")

        # When: Issueをクローズ
        result = issue_client.close_issue(
            issue_number=376,
            reason="ワークフロー完了"
        )

        # Then: エラーが返される
        assert result['success'] is False
        assert result['error'] is not None
        assert "Internal Server Error" in result['error']
