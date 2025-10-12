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

    def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str = 'main',
        draft: bool = True
    ) -> Dict[str, Any]:
        """
        Pull Requestを作成

        Args:
            title: PRタイトル
            body: PR本文（Markdown形式）
            head: ヘッドブランチ名（例: "ai-workflow/issue-355"）
            base: ベースブランチ名（デフォルト: "main"）
            draft: ドラフトフラグ（デフォルト: True）

        Returns:
            Dict[str, Any]:
                - success: bool - 成功/失敗
                - pr_url: Optional[str] - PRのURL
                - pr_number: Optional[int] - PR番号
                - error: Optional[str] - エラーメッセージ

        Raises:
            GithubException: GitHub API呼び出しエラー

        処理フロー:
            1. repository.create_pull()を呼び出し
            2. draft=Trueの場合、PR作成後に draft ステータスを設定
            3. 成功時はPR URLとPR番号を返却
            4. 失敗時はエラーメッセージを返却

        エラーハンドリング:
            - 認証エラー: 401 Unauthorized → GITHUB_TOKENの権限不足
            - 既存PR重複: 422 Unprocessable Entity → 既存PRが存在
            - その他のエラー: 例外メッセージを返却
        """
        try:
            # Pull Request作成
            pr = self.repository.create_pull(
                title=title,
                body=body,
                head=head,
                base=base,
                draft=draft
            )

            return {
                'success': True,
                'pr_url': pr.html_url,
                'pr_number': pr.number,
                'error': None
            }

        except GithubException as e:
            error_message = f"GitHub API error: {e.status} - {e.data.get('message', 'Unknown error')}"

            # 権限エラーの判定
            if e.status == 401 or e.status == 403:
                error_message = "GitHub Token lacks 'repo' scope. Please regenerate token with appropriate permissions."

            # 既存PR重複エラーの判定
            elif e.status == 422:
                error_message = "A pull request already exists for this branch."

            return {
                'success': False,
                'pr_url': None,
                'pr_number': None,
                'error': error_message
            }

        except Exception as e:
            return {
                'success': False,
                'pr_url': None,
                'pr_number': None,
                'error': f'Unexpected error: {e}'
            }

    def check_existing_pr(
        self,
        head: str,
        base: str = 'main'
    ) -> Optional[Dict[str, Any]]:
        """
        既存Pull Requestの確認

        Args:
            head: ヘッドブランチ名（例: "ai-workflow/issue-355"）
            base: ベースブランチ名（デフォルト: "main"）

        Returns:
            Optional[Dict[str, Any]]:
                - PRが存在する場合:
                    - pr_number: int - PR番号
                    - pr_url: str - PRのURL
                    - state: str - PRの状態（open/closed）
                - PRが存在しない場合: None

        処理フロー:
            1. repository.get_pulls(head=head, base=base, state='open')を呼び出し
            2. 結果が存在する場合、最初のPRを返却
            3. 結果が存在しない場合、Noneを返却

        エラーハンドリング:
            - GitHub API呼び出しエラー → 例外をraiseしない、Noneを返却
        """
        try:
            # repository.nameは"owner/repo"形式なので、ownerを取得
            owner = self.repository.owner.login
            full_head = f"{owner}:{head}"

            # open状態のPRを検索
            pulls = self.repository.get_pulls(
                state='open',
                head=full_head,
                base=base
            )

            # イテレータから最初の要素を取得
            for pr in pulls:
                return {
                    'pr_number': pr.number,
                    'pr_url': pr.html_url,
                    'state': pr.state
                }

            # PRが存在しない場合
            return None

        except GithubException as e:
            # エラーが発生した場合はNoneを返却（存在しないとみなす）
            print(f"[WARNING] Failed to check existing PR: {e}")
            return None

        except Exception as e:
            print(f"[WARNING] Unexpected error while checking existing PR: {e}")
            return None

    def _generate_pr_body_template(
        self,
        issue_number: int,
        branch_name: str
    ) -> str:
        """
        PR本文テンプレートを生成

        Args:
            issue_number: Issue番号
            branch_name: ブランチ名

        Returns:
            str: PR本文（Markdown形式）

        テンプレート内容:
            - 関連Issue（Closes #XXX）
            - ワークフロー進捗チェックリスト（Phase 0のみ完了状態）
            - 成果物ディレクトリの説明
            - 実行環境情報（Claude Code Pro Max、ContentParser）
        """
        return f"""## AI Workflow自動生成PR

### 📋 関連Issue
Closes #{issue_number}

### 🔄 ワークフロー進捗

- [x] Phase 0: Planning
- [ ] Phase 1: Requirements
- [ ] Phase 2: Design
- [ ] Phase 3: Test Scenario
- [ ] Phase 4: Implementation
- [ ] Phase 5: Test Implementation
- [ ] Phase 6: Testing
- [ ] Phase 7: Documentation
- [ ] Phase 8: Report

### 📁 成果物

`.ai-workflow/issue-{issue_number}/` ディレクトリに各フェーズの成果物が格納されています。

### ⚙️ 実行環境

- **モデル**: Claude Code Pro Max (Sonnet 4.5)
- **ContentParser**: OpenAI GPT-4o mini
- **ブランチ**: {branch_name}
"""

    def close(self):
        """
        GitHub APIクライアントをクローズ
        """
        # PyGitHubはクローズ不要
        pass
