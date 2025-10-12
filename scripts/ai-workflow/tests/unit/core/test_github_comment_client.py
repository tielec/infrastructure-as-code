"""
Unit tests for core/github/comment_client.py

Test Scenarios:
- UT-CC-001: CommentClient.post_comment() - 正常系
- UT-CC-002: CommentClient.create_or_update_progress_comment() - 新規作成
- UT-CC-003: CommentClient.create_or_update_progress_comment() - 既存更新
- UT-CC-004: CommentClient.create_or_update_progress_comment() - 既存不存在でフォールバック
"""
import pytest
from unittest.mock import Mock
from github import GithubException
from core.github.comment_client import CommentClient


class TestCommentClient:
    """CommentClient クラスのユニットテスト"""

    def test_post_comment_succeeds(self):
        """UT-CC-001: コメントが正しく投稿されることを確認"""
        # Given: GitHub APIのモック
        mock_github = Mock()
        mock_repository = Mock()

        # Issueのモック
        mock_issue = Mock()
        mock_comment = Mock()
        mock_comment.id = 12345
        mock_comment.html_url = "https://github.com/test/repo/issues/376#issuecomment-12345"

        mock_issue.create_comment.return_value = mock_comment
        mock_repository.get_issue.return_value = mock_issue

        mock_github.get_repo.return_value = mock_repository

        comment_client = CommentClient(mock_github, "test/repo")

        # When: コメントを投稿
        result = comment_client.post_comment(
            issue_number=376,
            body="## Progress Update\n\nPhase planning completed."
        )

        # Then: コメントが投稿される
        assert result is not None
        assert result.id == 12345
        mock_repository.get_issue.assert_called_once_with(number=376)
        mock_issue.create_comment.assert_called_once_with(
            "## Progress Update\n\nPhase planning completed."
        )

    def test_post_comment_raises_error_on_failure(self):
        """コメント投稿失敗時にエラーが発生することを確認"""
        # Given: コメント投稿がエラーを発生させるモック
        mock_github = Mock()
        mock_repository = Mock()

        mock_issue = Mock()
        mock_issue.create_comment.side_effect = GithubException(
            status=500,
            data={"message": "Internal Server Error"}
        )

        mock_repository.get_issue.return_value = mock_issue
        mock_github.get_repo.return_value = mock_repository

        comment_client = CommentClient(mock_github, "test/repo")

        # When/Then: GithubExceptionが発生する
        with pytest.raises(GithubException):
            comment_client.post_comment(
                issue_number=376,
                body="Test comment"
            )

    def test_create_or_update_progress_comment_creates_new(self):
        """UT-CC-002: 進捗コメントが新規作成されることを確認"""
        # Given: GitHub APIのモック
        mock_github = Mock()
        mock_repository = Mock()

        # Issueのモック
        mock_issue = Mock()
        mock_new_comment = Mock()
        mock_new_comment.id = 12345
        mock_new_comment.html_url = "https://github.com/test/repo/issues/376#issuecomment-12345"

        mock_issue.create_comment.return_value = mock_new_comment
        mock_repository.get_issue.return_value = mock_issue

        mock_github.get_repo.return_value = mock_repository

        comment_client = CommentClient(mock_github, "test/repo")

        # When: 新規進捗コメントを作成（comment_id=None）
        result = comment_client.create_or_update_progress_comment(
            issue_number=376,
            content="## Progress\n\nPhase: planning\nStatus: in_progress",
            comment_id=None
        )

        # Then: 新規コメントが作成される
        assert result['comment_id'] == 12345
        assert result['comment_url'] == "https://github.com/test/repo/issues/376#issuecomment-12345"

        mock_issue.create_comment.assert_called_once()

    def test_create_or_update_progress_comment_updates_existing(self):
        """UT-CC-003: 既存進捗コメントが更新されることを確認"""
        # Given: GitHub APIのモック
        mock_github = Mock()
        mock_repository = Mock()

        # Issueのモック
        mock_issue = Mock()

        # 既存コメントのモック
        mock_existing_comment = Mock()
        mock_existing_comment.id = 12345
        mock_existing_comment.html_url = "https://github.com/test/repo/issues/376#issuecomment-12345"
        mock_existing_comment.edit = Mock()

        mock_issue.get_comment.return_value = mock_existing_comment
        mock_repository.get_issue.return_value = mock_issue

        mock_github.get_repo.return_value = mock_repository

        comment_client = CommentClient(mock_github, "test/repo")

        # When: 既存進捗コメントを更新
        result = comment_client.create_or_update_progress_comment(
            issue_number=376,
            content="## Progress\n\nPhase: planning\nStatus: completed",
            comment_id=12345
        )

        # Then: 既存コメントが更新される
        assert result['comment_id'] == 12345
        assert result['comment_url'] == "https://github.com/test/repo/issues/376#issuecomment-12345"

        mock_issue.get_comment.assert_called_once_with(12345)
        mock_existing_comment.edit.assert_called_once_with(
            "## Progress\n\nPhase: planning\nStatus: completed"
        )

    def test_create_or_update_progress_comment_fallback_to_create_when_not_found(self):
        """UT-CC-004: 既存コメントが見つからない場合に新規作成されることを確認"""
        # Given: 既存コメント取得がエラーを発生させるモック
        mock_github = Mock()
        mock_repository = Mock()

        mock_issue = Mock()
        mock_issue.get_comment.side_effect = GithubException(
            status=404,
            data={"message": "Not Found"}
        )

        # 新規コメント作成のモック
        mock_new_comment = Mock()
        mock_new_comment.id = 67890
        mock_new_comment.html_url = "https://github.com/test/repo/issues/376#issuecomment-67890"

        mock_issue.create_comment.return_value = mock_new_comment
        mock_repository.get_issue.return_value = mock_issue

        mock_github.get_repo.return_value = mock_repository

        comment_client = CommentClient(mock_github, "test/repo")

        # When: 存在しないcomment_idで更新しようとする
        result = comment_client.create_or_update_progress_comment(
            issue_number=376,
            content="## Progress\n\nNew content",
            comment_id=99999  # 存在しないID
        )

        # Then: 新規コメントが作成される（フォールバック）
        assert result['comment_id'] == 67890
        assert result['comment_url'] == "https://github.com/test/repo/issues/376#issuecomment-67890"

        # 既存コメント取得が試行される
        mock_issue.get_comment.assert_called_once_with(99999)

        # 新規コメント作成にフォールバック
        mock_issue.create_comment.assert_called_once_with("## Progress\n\nNew content")

    def test_create_or_update_progress_comment_raises_error_on_critical_failure(self):
        """重大なエラー時に例外が発生することを確認"""
        # Given: Issue取得自体がエラーを発生させるモック
        mock_github = Mock()
        mock_repository = Mock()

        mock_repository.get_issue.side_effect = GithubException(
            status=500,
            data={"message": "Internal Server Error"}
        )

        mock_github.get_repo.return_value = mock_repository

        comment_client = CommentClient(mock_github, "test/repo")

        # When/Then: GithubExceptionが発生する
        with pytest.raises(GithubException):
            comment_client.create_or_update_progress_comment(
                issue_number=376,
                content="Test content",
                comment_id=None
            )

    def test_create_or_update_with_long_content(self):
        """長いコンテンツでも正しく動作することを確認"""
        # Given: GitHub APIのモック
        mock_github = Mock()
        mock_repository = Mock()

        mock_issue = Mock()
        mock_comment = Mock()
        mock_comment.id = 12345
        mock_comment.html_url = "https://github.com/test/repo/issues/376#issuecomment-12345"

        mock_issue.create_comment.return_value = mock_comment
        mock_repository.get_issue.return_value = mock_issue

        mock_github.get_repo.return_value = mock_repository

        comment_client = CommentClient(mock_github, "test/repo")

        # When: 長いコンテンツで進捗コメントを作成
        long_content = "## Progress\n\n" + ("Line\n" * 100)
        result = comment_client.create_or_update_progress_comment(
            issue_number=376,
            content=long_content,
            comment_id=None
        )

        # Then: 正しく作成される
        assert result['comment_id'] == 12345
        mock_issue.create_comment.assert_called_once_with(long_content)
