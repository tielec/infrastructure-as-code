"""GitHub Issue Client - Issue操作クラス

このモジュールは、GitHub Issueに関する操作を提供します。

機能:
    - Issue情報の取得
    - Issue本文からの要件抽出
    - Issueのクローズ
    - Follow-up Issueの作成

使用例:
    >>> from core.github.issue_client import IssueClient
    >>>
    >>> client = IssueClient(token='xxx', repository='owner/repo')
    >>> issue_info = client.get_info(376)
    >>> print(issue_info['title'])
"""

import os
from typing import Optional, Dict, Any, List
from github import Github, GithubException
from github.Issue import Issue
from common.logger import Logger
from common.error_handler import GitHubAPIError


logger = Logger.get_logger(__name__)


class IssueClient:
    """GitHub Issue操作クラス

    Issueの取得、情報抽出、クローズ等を提供します。

    Attributes:
        token: GitHub Personal Access Token
        repository_name: リポジトリ名（例: tielec/infrastructure-as-code）
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
            logger.info(f"IssueClient initialized for repository: {self.repository_name}")
        except Exception as e:
            raise GitHubAPIError(
                f"Failed to initialize GitHub client",
                details={'repository': self.repository_name},
                original_exception=e
            )

    def get(self, issue_number: int) -> Issue:
        """Issue情報を取得

        Args:
            issue_number: Issue番号

        Returns:
            Issue: PyGithubのIssueオブジェクト

        Raises:
            GitHubAPIError: API呼び出しエラー

        Example:
            >>> issue = client.get(376)
            >>> print(issue.title)
        """
        try:
            return self.repository.get_issue(number=issue_number)
        except GithubException as e:
            logger.error(f"Failed to get issue #{issue_number}: {e}")
            raise GitHubAPIError(
                f"Failed to get issue #{issue_number}",
                details={'issue_number': issue_number, 'status': e.status},
                original_exception=e
            )

    def get_info(self, issue_number: int) -> Dict[str, Any]:
        """Issue情報を辞書形式で取得

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

        Example:
            >>> info = client.get_info(376)
            >>> print(f"Title: {info['title']}")
        """
        issue = self.get(issue_number)

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

    def extract_requirements(self, issue_body: str) -> List[str]:
        """Issue本文から要件を抽出

        Args:
            issue_body: Issue本文

        Returns:
            List[str]: 抽出された要件一覧

        Notes:
            - "## 概要"セクションと"## TODO"セクションを抽出
            - TODOリストのチェックボックス項目を要件として扱う

        Example:
            >>> requirements = client.extract_requirements(issue.body)
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

        logger.debug(f"Extracted {len(requirements)} requirement sections from issue")
        return requirements

    def close_with_reason(
        self,
        issue_number: int,
        reason: str
    ) -> Dict[str, Any]:
        """Issueをクローズ理由付きでクローズ

        Args:
            issue_number: Issue番号
            reason: クローズ理由

        Returns:
            Dict[str, Any]:
                - success: bool
                - error: Optional[str]

        Example:
            >>> result = client.close_with_reason(376, "Critical issues found")
        """
        try:
            issue = self.get(issue_number)

            # コメントを投稿
            comment_body = "## ⚠️ ワークフロー中止\n\n"
            comment_body += "プロジェクト評価の結果、致命的な問題が発見されたため、ワークフローを中止します。\n\n"
            comment_body += "### 中止理由\n\n"
            comment_body += f"{reason}\n\n"
            comment_body += "### 推奨アクション\n\n"
            comment_body += "- アーキテクチャの再設計\n"
            comment_body += "- スコープの見直し\n"
            comment_body += "- 技術選定の再検討\n\n"
            comment_body += "---\n"
            comment_body += "*AI Workflow Phase 9 (Evaluation) - ABORT*\n"

            issue.create_comment(comment_body)

            # Issueをクローズ
            issue.edit(state='closed')
            logger.info(f"Closed issue #{issue_number} with reason")

            return {
                'success': True,
                'error': None
            }

        except GithubException as e:
            error_message = f"GitHub API error: {e.status} - {e.data.get('message', 'Unknown error')}"
            logger.error(f"Failed to close issue: {error_message}")

            return {
                'success': False,
                'error': error_message
            }

        except Exception as e:
            logger.error(f"Unexpected error while closing issue: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def create_from_evaluation(
        self,
        issue_number: int,
        remaining_tasks: List[Dict[str, Any]],
        evaluation_report_path: str
    ) -> Dict[str, Any]:
        """評価結果から新しいIssueを作成

        Args:
            issue_number: 元のIssue番号
            remaining_tasks: 残タスクリスト
                - task: str - タスク内容
                - phase: str - 発見されたフェーズ
                - priority: str - 優先度（高/中/低）
            evaluation_report_path: 評価レポートのパス

        Returns:
            Dict[str, Any]:
                - success: bool
                - issue_url: Optional[str]
                - issue_number: Optional[int]
                - error: Optional[str]

        Example:
            >>> tasks = [{'task': 'Fix bug', 'phase': 'implementation', 'priority': '高'}]
            >>> result = client.create_from_evaluation(376, tasks, '.ai-workflow/issue-376/eval.md')
        """
        try:
            # Issueタイトル
            title = f"[FOLLOW-UP] Issue #{issue_number} - 残タスク"

            # Issue本文を生成
            body_parts = []
            body_parts.append("## 概要\n")
            body_parts.append(f"AI Workflow Issue #{issue_number} の実装完了後に発見された残タスクです。\n")
            body_parts.append("\n## 残タスク一覧\n")

            for task in remaining_tasks:
                task_text = task.get('task', '')
                phase = task.get('phase', 'unknown')
                priority = task.get('priority', '中')
                body_parts.append(f"- [ ] {task_text}（Phase: {phase}、優先度: {priority}）\n")

            body_parts.append("\n## 関連\n")
            body_parts.append(f"- 元Issue: #{issue_number}\n")
            body_parts.append(f"- Evaluation Report: `{evaluation_report_path}`\n")
            body_parts.append("\n---\n")
            body_parts.append("*自動生成: AI Workflow Phase 9 (Evaluation)*\n")

            body = ''.join(body_parts)

            # Issue作成
            new_issue = self.repository.create_issue(
                title=title,
                body=body,
                labels=['enhancement', 'ai-workflow-follow-up']
            )

            logger.info(f"Created follow-up issue #{new_issue.number} for issue #{issue_number}")

            return {
                'success': True,
                'issue_url': new_issue.html_url,
                'issue_number': new_issue.number,
                'error': None
            }

        except GithubException as e:
            error_message = f"GitHub API error: {e.status} - {e.data.get('message', 'Unknown error')}"
            logger.error(f"Failed to create issue: {error_message}")

            return {
                'success': False,
                'issue_url': None,
                'issue_number': None,
                'error': error_message
            }

        except Exception as e:
            logger.error(f"Unexpected error while creating issue: {e}")
            return {
                'success': False,
                'issue_url': None,
                'issue_number': None,
                'error': str(e)
            }

    def extract_summary(self, issue_body: str) -> str:
        """Issue本文から概要を抽出

        Args:
            issue_body: Issue本文

        Returns:
            str: 抽出された概要

        Example:
            >>> summary = client.extract_summary(issue.body)
        """
        # "## 概要"セクションを抽出
        summary = self._extract_section(issue_body, '## 概要')

        if not summary:
            # 概要セクションがない場合は、最初の段落を使用
            lines = issue_body.strip().split('\n')
            for line in lines:
                if line.strip() and not line.strip().startswith('#'):
                    return line.strip()
            return '（概要の記載なし）'

        return summary

    def _extract_section(self, content: str, section_header: str) -> str:
        """Markdown文書から特定セクションを抽出

        Args:
            content: Markdown文書全体
            section_header: 抽出したいセクションのヘッダー（例: "## 概要"）

        Returns:
            str: 抽出されたセクションの内容
        """
        lines = content.split('\n')
        section_lines = []
        in_section = False

        for line in lines:
            if line.strip().startswith(section_header):
                in_section = True
                continue
            elif line.strip().startswith('##') and in_section:
                # 次のセクションに到達したら終了
                break
            elif in_section:
                section_lines.append(line)

        return '\n'.join(section_lines).strip()

    def close(self):
        """GitHub APIクライアントをクローズ"""
        # PyGitHubはクローズ不要
        pass
