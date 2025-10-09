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
