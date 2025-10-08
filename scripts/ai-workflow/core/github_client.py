"""GitHub API クライアント

GitHub APIを使ってIssue情報を取得・更新
- Issue情報の取得（タイトル、本文、ラベル）
- Issueコメントの取得・投稿
- ワークフロー進捗報告
"""
import os
from typing import Optional, List, Dict, Any
from github import Github, GithubException
from github.Issue import Issue
from github.IssueComment import IssueComment


class GitHubClient:
    """GitHub API クライアント"""

    def __init__(
        self,
        token: Optional[str] = None,
        repository: Optional[str] = None
    ):
        """
        初期化

        Args:
            token: GitHub Personal Access Token（省略時は環境変数GITHUB_TOKENを使用）
            repository: リポジトリ名（例: tielec/infrastructure-as-code）
                       省略時は環境変数GITHUB_REPOSITORYを使用
        """
        self.token = token or os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("GitHub token is required. Set GITHUB_TOKEN environment variable.")

        self.repository_name = repository or os.getenv('GITHUB_REPOSITORY')
        if not self.repository_name:
            raise ValueError("Repository name is required. Set GITHUB_REPOSITORY environment variable.")

        # GitHub APIクライアントを初期化
        self.github = Github(self.token)
        self.repository = self.github.get_repo(self.repository_name)

    def get_issue(self, issue_number: int) -> Issue:
        """
        Issue情報を取得

        Args:
            issue_number: Issue番号

        Returns:
            Issue: Issue情報

        Raises:
            GithubException: API呼び出しエラー
        """
        try:
            return self.repository.get_issue(number=issue_number)
        except GithubException as e:
            raise RuntimeError(f"Failed to get issue #{issue_number}: {e}")

    def get_issue_info(self, issue_number: int) -> Dict[str, Any]:
        """
        Issue情報を辞書形式で取得

        Args:
            issue_number: Issue番号

        Returns:
            Dict[str, Any]: Issue情報
                - number: Issue番号
                - title: タイトル
                - body: 本文
                - state: 状態（open/closed）
                - labels: ラベル一覧
                - url: IssueのURL
                - created_at: 作成日時
                - updated_at: 更新日時
        """
        issue = self.get_issue(issue_number)

        return {
            'number': issue.number,
            'title': issue.title,
            'body': issue.body or '',
            'state': issue.state,
            'labels': [label.name for label in issue.labels],
            'url': issue.html_url,
            'created_at': issue.created_at.isoformat(),
            'updated_at': issue.updated_at.isoformat()
        }

    def get_issue_comments(self, issue_number: int) -> List[IssueComment]:
        """
        Issueコメント一覧を取得

        Args:
            issue_number: Issue番号

        Returns:
            List[IssueComment]: コメント一覧

        Raises:
            GithubException: API呼び出しエラー
        """
        try:
            issue = self.get_issue(issue_number)
            return list(issue.get_comments())
        except GithubException as e:
            raise RuntimeError(f"Failed to get comments for issue #{issue_number}: {e}")

    def get_issue_comments_dict(self, issue_number: int) -> List[Dict[str, Any]]:
        """
        Issueコメント一覧を辞書形式で取得

        Args:
            issue_number: Issue番号

        Returns:
            List[Dict[str, Any]]: コメント情報一覧
                - id: コメントID
                - user: ユーザー名
                - body: コメント本文
                - created_at: 作成日時
                - updated_at: 更新日時
        """
        comments = self.get_issue_comments(issue_number)

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

    def post_comment(self, issue_number: int, body: str) -> IssueComment:
        """
        Issueにコメントを投稿

        Args:
            issue_number: Issue番号
            body: コメント本文（Markdown形式）

        Returns:
            IssueComment: 投稿されたコメント

        Raises:
            GithubException: API呼び出しエラー
        """
        try:
            issue = self.get_issue(issue_number)
            return issue.create_comment(body)
        except GithubException as e:
            raise RuntimeError(f"Failed to post comment to issue #{issue_number}: {e}")

    def post_workflow_progress(
        self,
        issue_number: int,
        phase: str,
        status: str,
        details: Optional[str] = None
    ) -> IssueComment:
        """
        ワークフロー進捗をIssueにコメント投稿

        Args:
            issue_number: Issue番号
            phase: フェーズ名（requirements, design, test_scenario, implementation, testing, documentation）
            status: ステータス（pending, in_progress, completed, failed）
            details: 詳細情報（省略可）

        Returns:
            IssueComment: 投稿されたコメント

        Raises:
            GithubException: API呼び出しエラー
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

        return self.post_comment(issue_number, body)

    def post_review_result(
        self,
        issue_number: int,
        phase: str,
        result: str,
        feedback: Optional[str] = None,
        suggestions: Optional[List[str]] = None
    ) -> IssueComment:
        """
        レビュー結果をIssueにコメント投稿

        Args:
            issue_number: Issue番号
            phase: フェーズ名
            result: レビュー結果（PASS, PASS_WITH_SUGGESTIONS, FAIL）
            feedback: フィードバック（省略可）
            suggestions: 改善提案一覧（省略可）

        Returns:
            IssueComment: 投稿されたコメント

        Raises:
            GithubException: API呼び出しエラー
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

        return self.post_comment(issue_number, body)

    def extract_requirements(self, issue_body: str) -> List[str]:
        """
        Issue本文から要件を抽出

        Args:
            issue_body: Issue本文

        Returns:
            List[str]: 抽出された要件一覧

        Notes:
            - "## 概要"セクションと"## TODO"セクションを抽出
            - TODOリストのチェックボックス項目を要件として扱う
        """
        requirements = []

        # Issue本文を行ごとに分割
        lines = issue_body.split('\n')

        # 概要セクションを抽出
        in_overview = False
        overview_lines = []

        for line in lines:
            if line.strip().startswith('## 概要'):
                in_overview = True
                continue
            elif line.strip().startswith('##') and in_overview:
                in_overview = False
                break

            if in_overview and line.strip():
                overview_lines.append(line.strip())

        if overview_lines:
            requirements.append('## 概要\n' + '\n'.join(overview_lines))

        # TODOセクションからチェックボックス項目を抽出
        in_todo = False
        todo_items = []

        for line in lines:
            if line.strip().startswith('## TODO'):
                in_todo = True
                continue
            elif line.strip().startswith('##') and in_todo:
                in_todo = False
                break

            if in_todo:
                # チェックボックス項目を抽出（- [ ] または - [x]）
                stripped = line.strip()
                if stripped.startswith('- [ ]') or stripped.startswith('- [x]'):
                    todo_item = stripped.replace('- [ ]', '').replace('- [x]', '').strip()
                    if todo_item:
                        todo_items.append(todo_item)

        if todo_items:
            requirements.append('## 実装要件\n' + '\n'.join(f'- {item}' for item in todo_items))

        return requirements

    def close(self):
        """
        GitHub APIクライアントをクローズ
        """
        # PyGitHubはクローズ不要
        pass
