"""GitHub Operations - GitHub API操作モジュール

このモジュールは、GitHub API操作を責務別に分割したクラスを提供します。

Classes:
    IssueClient: Issue操作（Issue取得、情報抽出、クローズ等）
    PRClient: Pull Request操作（PR作成、更新、クローズ等）
    CommentClient: コメント操作（コメント投稿、進捗報告、レビュー結果投稿等）

使用例:
    >>> from core.github import IssueClient, PRClient, CommentClient
    >>>
    >>> issue_client = IssueClient(token, repository)
    >>> pr_client = PRClient(token, repository)
    >>> comment_client = CommentClient(token, repository)
    >>>
    >>> # Issue情報取得
    >>> issue_info = issue_client.get_info(376)
    >>>
    >>> # PR作成
    >>> result = pr_client.create('Title', 'Body', 'ai-workflow/issue-376')
    >>>
    >>> # コメント投稿
    >>> comment_client.post_progress(376, 'requirements', 'completed')
"""

from .issue_client import IssueClient
from .pr_client import PRClient
from .comment_client import CommentClient

__all__ = [
    'IssueClient',
    'PRClient',
    'CommentClient'
]
