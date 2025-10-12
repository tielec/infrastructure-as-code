"""GitHub Comment Client - コメント操作クラス

このモジュールは、GitHub Issueコメントに関する操作を提供します。

機能:
    - コメント取得
    - コメント投稿
    - ワークフロー進捗報告
    - レビュー結果投稿
    - 進捗コメントの作成・更新

使用例:
    >>> from core.github.comment_client import CommentClient
    >>>
    >>> client = CommentClient(token='xxx', repository='owner/repo')
    >>> client.post_progress(376, 'requirements', 'completed')
"""

import os
from typing import Optional, Dict, Any, List
from github import Github, GithubException
from github.IssueComment import IssueComment
from common.logger import Logger
from common.error_handler import GitHubAPIError


logger = Logger.get_logger(__name__)


class CommentClient:
    """GitHub Comment操作クラス

    コメントの取得、投稿、進捗報告等を提供します。

    Attributes:
        token: GitHub Personal Access Token
        repository_name: リポジトリ名
        github: PyGithubクライアント
        repository: リポジトリオブジェクト
    """

    def __init__(
        self,
        token: Optional[str] = None,
        repository: Optional[str] = None
    ):
        """初期化

        Args:
            token: GitHub Personal Access Token（省略時は環境変数GITHUB_TOKENを使用）
            repository: リポジトリ名（省略時は環境変数GITHUB_REPOSITORYを使用）

        Raises:
            GitHubAPIError: トークンまたはリポジトリ名が未指定の場合
        """
        self.token = token or os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise GitHubAPIError(
                "GitHub token is required",
                details={'hint': 'Set GITHUB_TOKEN environment variable'}
            )

        self.repository_name = repository or os.getenv('GITHUB_REPOSITORY')
        if not self.repository_name:
            raise GitHubAPIError(
                "Repository name is required",
                details={'hint': 'Set GITHUB_REPOSITORY environment variable'}
            )

        # GitHub APIクライアントを初期化
        try:
            self.github = Github(self.token)
            self.repository = self.github.get_repo(self.repository_name)
            logger.info(f"CommentClient initialized for repository: {self.repository_name}")
        except Exception as e:
            raise GitHubAPIError(
                f"Failed to initialize GitHub client",
                details={'repository': self.repository_name},
                original_exception=e
            )

    def get_comments(self, issue_number: int) -> List[IssueComment]:
        """Issueコメント一覧を取得

        Args:
            issue_number: Issue番号

        Returns:
            List[IssueComment]: PyGithubのIssueCommentオブジェクトのリスト

        Raises:
            GitHubAPIError: API呼び出しエラー

        Example:
            >>> comments = client.get_comments(376)
            >>> for comment in comments:
            ...     print(comment.body)
        """
        try:
            issue = self.repository.get_issue(issue_number)
            return list(issue.get_comments())
        except GithubException as e:
            logger.error(f"Failed to get comments for issue #{issue_number}: {e}")
            raise GitHubAPIError(
                f"Failed to get comments for issue #{issue_number}",
                details={'issue_number': issue_number, 'status': e.status},
                original_exception=e
            )

    def get_comments_dict(self, issue_number: int) -> List[Dict[str, Any]]:
        """Issueコメント一覧を辞書形式で取得

        Args:
            issue_number: Issue番号

        Returns:
            List[Dict[str, Any]]: コメント情報一覧
                - id: コメントID
                - user: ユーザー名
                - body: コメント本文
                - created_at: 作成日時
                - updated_at: 更新日時

        Example:
            >>> comments = client.get_comments_dict(376)
            >>> for comment in comments:
            ...     print(f"{comment['user']}: {comment['body']}")
        """
        comments = self.get_comments(issue_number)

        return [
            {
                'id': comment.id,
                'user': comment.user.login,
                'body': comment.body,
                'created_at': comment.created_at.isoformat(),
                'updated_at': comment.updated_at.isoformat()
            }
            for comment in comments
        ]

    def post(self, issue_number: int, body: str) -> IssueComment:
        """Issueにコメントを投稿

        Args:
            issue_number: Issue番号
            body: コメント本文（Markdown形式）

        Returns:
            IssueComment: 投稿されたコメント

        Raises:
            GitHubAPIError: API呼び出しエラー

        Example:
            >>> comment = client.post(376, "## Progress Update\\n\\nPhase 1 completed!")
        """
        try:
            issue = self.repository.get_issue(issue_number)
            comment = issue.create_comment(body)
            logger.info(f"Posted comment to issue #{issue_number}")
            return comment
        except GithubException as e:
            logger.error(f"Failed to post comment to issue #{issue_number}: {e}")
            raise GitHubAPIError(
                f"Failed to post comment to issue #{issue_number}",
                details={'issue_number': issue_number, 'status': e.status},
                original_exception=e
            )

    def post_progress(
        self,
        issue_number: int,
        phase: str,
        status: str,
        details: Optional[str] = None
    ) -> IssueComment:
        """ワークフロー進捗をIssueにコメント投稿

        Args:
            issue_number: Issue番号
            phase: フェーズ名（requirements, design, test_scenario, implementation, testing, documentation）
            status: ステータス（pending, in_progress, completed, failed）
            details: 詳細情報（省略可）

        Returns:
            IssueComment: 投稿されたコメント

        Raises:
            GitHubAPIError: API呼び出しエラー

        Example:
            >>> client.post_progress(376, 'requirements', 'completed', 'All requirements documented')
        """
        # ステータス絵文字マッピング
        status_emoji = {
            'pending': '⏸️',
            'in_progress': '🔄',
            'completed': '✅',
            'failed': '❌'
        }

        # フェーズ名の日本語マッピング
        phase_names = {
            'requirements': '要件定義',
            'design': '設計',
            'test_scenario': 'テストシナリオ',
            'implementation': '実装',
            'testing': 'テスト',
            'documentation': 'ドキュメント'
        }

        emoji = status_emoji.get(status, '📝')
        phase_jp = phase_names.get(phase, phase)

        body = f"## {emoji} AI Workflow - {phase_jp}フェーズ\n\n"
        body += f"**ステータス**: {status.upper()}\n\n"

        if details:
            body += f"{details}\n\n"

        body += "---\n"
        body += "*AI駆動開発自動化ワークフロー (Claude Agent SDK)*"

        return self.post(issue_number, body)

    def post_review_result(
        self,
        issue_number: int,
        phase: str,
        result: str,
        feedback: Optional[str] = None,
        suggestions: Optional[List[str]] = None
    ) -> IssueComment:
        """レビュー結果をIssueにコメント投稿

        Args:
            issue_number: Issue番号
            phase: フェーズ名
            result: レビュー結果（PASS, PASS_WITH_SUGGESTIONS, FAIL）
            feedback: フィードバック（省略可）
            suggestions: 改善提案一覧（省略可）

        Returns:
            IssueComment: 投稿されたコメント

        Raises:
            GitHubAPIError: API呼び出しエラー

        Example:
            >>> client.post_review_result(
            ...     376, 'design', 'PASS_WITH_SUGGESTIONS',
            ...     feedback='Good design overall',
            ...     suggestions=['Consider adding error handling']
            ... )
        """
        # レビュー結果絵文字マッピング
        result_emoji = {
            'PASS': '✅',
            'PASS_WITH_SUGGESTIONS': '⚠️',
            'FAIL': '❌'
        }

        # フェーズ名の日本語マッピング
        phase_names = {
            'requirements': '要件定義',
            'design': '設計',
            'test_scenario': 'テストシナリオ',
            'implementation': '実装',
            'testing': 'テスト',
            'documentation': 'ドキュメント'
        }

        emoji = result_emoji.get(result, '📝')
        phase_jp = phase_names.get(phase, phase)

        body = f"## {emoji} レビュー結果 - {phase_jp}フェーズ\n\n"
        body += f"**判定**: {result}\n\n"

        if feedback:
            body += f"### フィードバック\n\n{feedback}\n\n"

        if suggestions:
            body += "### 改善提案\n\n"
            for i, suggestion in enumerate(suggestions, 1):
                body += f"{i}. {suggestion}\n"
            body += "\n"

        body += "---\n"
        body += "*AI駆動開発自動化ワークフロー - クリティカルシンキングレビュー*"

        return self.post(issue_number, body)

    def create_or_update_progress(
        self,
        issue_number: int,
        content: str,
        metadata_manager
    ) -> Dict[str, Any]:
        """進捗コメントを作成または更新

        Args:
            issue_number: Issue番号
            content: コメント本文（Markdown形式）
            metadata_manager: MetadataManagerインスタンス

        Returns:
            Dict[str, Any]:
                - comment_id (int): コメントID
                - comment_url (str): コメントURL

        Raises:
            GitHubAPIError: GitHub API呼び出しエラー

        処理フロー:
            1. メタデータから既存コメントIDを取得
            2. コメントIDが存在する場合:
               - repository.get_issue_comment(comment_id)でコメント取得
               - comment.edit(content)でコメント編集
            3. コメントIDが存在しない場合:
               - issue.create_comment(content)で新規コメント作成
               - メタデータにコメントIDを保存
            4. コメントIDとURLを返却

        エラーハンドリング:
            - Edit Comment API失敗時: ログ出力してから新規コメント作成にフォールバック
            - コメントIDが無効な場合: 新規コメント作成としてリトライ

        Example:
            >>> result = client.create_or_update_progress(
            ...     376, "## Progress\\n\\nPhase 1: Completed", metadata_manager
            ... )
            >>> print(f"Comment URL: {result['comment_url']}")
        """
        try:
            # メタデータから既存コメントIDを取得
            existing_comment_id = metadata_manager.get_progress_comment_id()

            if existing_comment_id:
                # コメントIDが存在する場合 → 既存コメントを編集
                try:
                    logger.info(f"Updating existing progress comment (ID: {existing_comment_id})")
                    issue = self.repository.get_issue(issue_number)
                    comment = issue.get_comment(existing_comment_id)
                    comment.edit(content)
                    logger.info(f"Progress comment updated successfully: {comment.html_url}")

                    return {
                        'comment_id': comment.id,
                        'comment_url': comment.html_url
                    }

                except GithubException as e:
                    # Edit Comment API失敗時 → フォールバックで新規コメント作成
                    logger.warning(
                        f"GitHub Edit Comment API error: {e.status} - "
                        f"{e.data.get('message', 'Unknown')} (Comment ID: {existing_comment_id})"
                    )
                    logger.info("Fallback: Creating new comment")
                    # 以下の処理で新規コメント作成に進む

                except Exception as e:
                    # その他のエラー（コメントが存在しない等）もフォールバック
                    logger.warning(f"Comment retrieval/update error: {e}")
                    logger.info("Fallback: Creating new comment")
                    # 以下の処理で新規コメント作成に進む

            # コメントIDが存在しない場合、またはEdit失敗時 → 新規コメント作成
            issue = self.repository.get_issue(issue_number)
            new_comment = issue.create_comment(content)
            logger.info(f"New progress comment created successfully: {new_comment.html_url}")

            # メタデータにコメントIDを保存
            metadata_manager.save_progress_comment_id(
                comment_id=new_comment.id,
                comment_url=new_comment.html_url
            )
            logger.info(f"Comment ID saved to metadata: {new_comment.id}")

            return {
                'comment_id': new_comment.id,
                'comment_url': new_comment.html_url
            }

        except GithubException as e:
            error_msg = f"GitHub API error: {e.status} - {e.data.get('message', 'Unknown error')}"
            logger.error(f"Failed to create or update progress comment: {error_msg}")
            raise GitHubAPIError(
                "Failed to create or update progress comment",
                details={'issue_number': issue_number, 'status': e.status},
                original_exception=e
            )

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise GitHubAPIError(
                "Unexpected error while creating or updating progress comment",
                original_exception=e
            )

    def close(self):
        """GitHub APIクライアントをクローズ"""
        # PyGitHubはクローズ不要
        pass
