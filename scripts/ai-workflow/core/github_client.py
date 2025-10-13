"""GitHub API クライアント

GitHub APIを使ってIssue情報を取得・更新
- Issue情報の取得（タイトル、本文、ラベル）
- Issueコメントの取得・投稿
- ワークフロー進捗報告
"""
import os
from pathlib import Path
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

        テンプレートファイル:
            scripts/ai-workflow/templates/pr_body_template.md
        """
        from pathlib import Path

        # テンプレートファイルのパスを取得
        template_path = Path(__file__).parent.parent / 'templates' / 'pr_body_template.md'

        # テンプレートを読み込み
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()

        # プレースホルダーを置換
        return template.format(issue_number=issue_number, branch_name=branch_name)

    def create_issue_from_evaluation(
        self,
        issue_number: int,
        remaining_tasks: List[Dict[str, Any]],
        evaluation_report_path: str
    ) -> Dict[str, Any]:
        """
        評価結果から新しい Issue を作成

        Args:
            issue_number: 元の Issue 番号
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
        """
        try:
            # Issue タイトル
            title = f"[FOLLOW-UP] Issue #{issue_number} - 残タスク"

            # Issue 本文を生成
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

            # Issue 作成
            new_issue = self.repository.create_issue(
                title=title,
                body=body,
                labels=['enhancement', 'ai-workflow-follow-up']
            )

            return {
                'success': True,
                'issue_url': new_issue.html_url,
                'issue_number': new_issue.number,
                'error': None
            }

        except GithubException as e:
            error_message = f"GitHub API error: {e.status} - {e.data.get('message', 'Unknown error')}"
            print(f"[ERROR] Issue作成失敗: {error_message}")

            return {
                'success': False,
                'issue_url': None,
                'issue_number': None,
                'error': error_message
            }

        except Exception as e:
            print(f"[ERROR] Issue作成中に予期しないエラー: {e}")
            return {
                'success': False,
                'issue_url': None,
                'issue_number': None,
                'error': str(e)
            }

    def close_issue_with_reason(
        self,
        issue_number: int,
        reason: str
    ) -> Dict[str, Any]:
        """
        Issue をクローズ理由付きでクローズ

        Args:
            issue_number: Issue番号
            reason: クローズ理由

        Returns:
            Dict[str, Any]:
                - success: bool
                - error: Optional[str]
        """
        try:
            issue = self.get_issue(issue_number)

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

            # Issue をクローズ
            issue.edit(state='closed')

            print(f"[INFO] Issue #{issue_number} をクローズしました")

            return {
                'success': True,
                'error': None
            }

        except GithubException as e:
            error_message = f"GitHub API error: {e.status} - {e.data.get('message', 'Unknown error')}"
            print(f"[ERROR] Issueクローズ失敗: {error_message}")

            return {
                'success': False,
                'error': error_message
            }

        except Exception as e:
            print(f"[ERROR] Issueクローズ中に予期しないエラー: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def close_pull_request(
        self,
        pr_number: int,
        comment: str
    ) -> Dict[str, Any]:
        """
        Pull Request をクローズ

        Args:
            pr_number: PR番号
            comment: クローズコメント

        Returns:
            Dict[str, Any]:
                - success: bool
                - error: Optional[str]
        """
        try:
            pr = self.repository.get_pull(pr_number)

            # コメントを投稿
            pr.create_issue_comment(comment)

            # PR をクローズ
            pr.edit(state='closed')

            print(f"[INFO] PR #{pr_number} をクローズしました")

            return {
                'success': True,
                'error': None
            }

        except GithubException as e:
            error_message = f"GitHub API error: {e.status} - {e.data.get('message', 'Unknown error')}"
            print(f"[ERROR] PRクローズ失敗: {error_message}")

            return {
                'success': False,
                'error': error_message
            }

        except Exception as e:
            print(f"[ERROR] PRクローズ中に予期しないエラー: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_pull_request_number(
        self,
        issue_number: int
    ) -> Optional[int]:
        """
        Issue番号から関連するPR番号を取得

        Args:
            issue_number: Issue番号

        Returns:
            Optional[int]: PR番号（見つからない場合は None）
        """
        try:
            # Issue を取得
            issue = self.get_issue(issue_number)

            # Issue のタイムライン情報から PR を検索
            timeline = issue.get_timeline()
            for event in timeline:
                if event.event == 'cross-referenced' and hasattr(event.source, 'issue'):
                    # PRが見つかった場合
                    source_issue = event.source.issue
                    if hasattr(source_issue, 'pull_request') and source_issue.pull_request:
                        return source_issue.number

            # ブランチ名から PR を検索
            branch_name = f"ai-workflow/issue-{issue_number}"
            owner = self.repository.owner.login
            full_head = f"{owner}:{branch_name}"

            pulls = self.repository.get_pulls(
                state='all',
                head=full_head,
                base='main'
            )

            for pr in pulls:
                return pr.number

            # 見つからない場合
            print(f"[WARNING] Issue #{issue_number} に関連するPRが見つかりませんでした")
            return None

        except Exception as e:
            print(f"[WARNING] PR番号の取得に失敗: {e}")
            return None

    def create_or_update_progress_comment(
        self,
        issue_number: int,
        content: str,
        metadata_manager
    ) -> Dict[str, Any]:
        """
        進捗コメントを作成または更新

        Args:
            issue_number: Issue番号
            content: コメント本文（Markdown形式）
            metadata_manager: MetadataManagerインスタンス

        Returns:
            Dict[str, Any]:
                - comment_id (int): コメントID
                - comment_url (str): コメントURL

        Raises:
            GithubException: GitHub API呼び出しエラー

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
        """
        try:
            # メタデータから既存コメントIDを取得
            existing_comment_id = metadata_manager.get_progress_comment_id()

            if existing_comment_id:
                # コメントIDが存在する場合 → 既存コメントを編集
                try:
                    print(f"[INFO] 既存進捗コメント (ID: {existing_comment_id}) を更新します")
                    issue = self.get_issue(issue_number)
                    comment = issue.get_comment(existing_comment_id)
                    comment.edit(content)
                    print(f"[INFO] 進捗コメント更新成功: {comment.html_url}")

                    return {
                        'comment_id': comment.id,
                        'comment_url': comment.html_url
                    }

                except GithubException as e:
                    # Edit Comment API失敗時 → フォールバックで新規コメント作成
                    print(f"[WARNING] GitHub Edit Comment APIエラー: {e.status} - {e.data.get('message', 'Unknown')} (コメントID: {existing_comment_id})")
                    print(f"[INFO] フォールバック: 新規コメント作成")
                    # 以下の処理で新規コメント作成に進む

                except Exception as e:
                    # その他のエラー（コメントが存在しない等）もフォールバック
                    print(f"[WARNING] コメント取得/更新エラー: {e}")
                    print(f"[INFO] フォールバック: 新規コメント作成")
                    # 以下の処理で新規コメント作成に進む

            # コメントIDが存在しない場合、またはEdit失敗時 → 新規コメント作成
            issue = self.get_issue(issue_number)
            new_comment = issue.create_comment(content)
            print(f"[INFO] 新規進捗コメント作成成功: {new_comment.html_url}")

            # メタデータにコメントIDを保存
            metadata_manager.save_progress_comment_id(
                comment_id=new_comment.id,
                comment_url=new_comment.html_url
            )
            print(f"[INFO] コメントIDをメタデータに保存: {new_comment.id}")

            return {
                'comment_id': new_comment.id,
                'comment_url': new_comment.html_url
            }

        except GithubException as e:
            error_msg = f"GitHub API error: {e.status} - {e.data.get('message', 'Unknown error')}"
            print(f"[ERROR] 進捗コメント作成/更新に失敗: {error_msg}")
            raise RuntimeError(f"Failed to create or update progress comment: {error_msg}")

        except Exception as e:
            print(f"[ERROR] 予期しないエラー: {e}")
            raise RuntimeError(f"Unexpected error while creating or updating progress comment: {e}")

    def update_pull_request(
        self,
        pr_number: int,
        body: str
    ) -> Dict[str, Any]:
        """
        Pull Requestの本文を更新

        Args:
            pr_number: PR番号
            body: 新しいPR本文（Markdown形式）

        Returns:
            Dict[str, Any]:
                - success: bool - 成功/失敗
                - error: Optional[str] - エラーメッセージ（成功時はNone）

        処理フロー:
            1. repository.get_pull(pr_number)でPRを取得
            2. pr.edit(body=body)でPR本文を更新
            3. 成功時は {'success': True, 'error': None}を返却
            4. 失敗時はエラーメッセージを返却

        エラーハンドリング:
            - PR未存在（404 Not Found）: エラーメッセージを返却
            - 権限不足（401/403）: 権限エラーメッセージを返却
            - API制限到達（429 Rate Limit Exceeded）: rate limit警告メッセージを返却
        """
        try:
            # PRを取得
            pr = self.repository.get_pull(pr_number)

            # PR本文を更新
            pr.edit(body=body)

            return {
                'success': True,
                'error': None
            }

        except GithubException as e:
            # エラーの種類に応じてメッセージを設定
            if e.status == 404:
                error_message = f'PR #{pr_number} not found'
            elif e.status == 401 or e.status == 403:
                error_message = 'GitHub Token lacks PR edit permissions'
            elif e.status == 429:
                error_message = 'GitHub API rate limit exceeded'
            else:
                error_message = f'GitHub API error: {e.status} - {e.data.get("message", "Unknown")}'

            return {
                'success': False,
                'error': error_message
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {e}'
            }

    def _generate_pr_body_detailed(
        self,
        issue_number: int,
        branch_name: str,
        extracted_info: Dict[str, Any]
    ) -> str:
        """
        詳細版PR本文を生成

        Args:
            issue_number: Issue番号
            branch_name: ブランチ名
            extracted_info: 抽出された成果物情報
                - summary: 変更サマリー
                - implementation_details: 実装詳細
                - test_results: テスト結果
                - documentation_updates: ドキュメント更新リスト
                - review_points: レビューポイント

        Returns:
            str: 詳細版PR本文（Markdown形式）

        処理フロー:
            1. テンプレートファイル pr_body_detailed_template.md を読み込み
            2. プレースホルダーを置換
            3. 生成されたPR本文を返却

        エラーハンドリング:
            - FileNotFoundError: テンプレートファイルが存在しない
            - KeyError: 必須プレースホルダーが欠落している
        """
        from pathlib import Path

        try:
            # テンプレートファイルのパスを取得
            template_path = Path(__file__).parent.parent / 'templates' / 'pr_body_detailed_template.md'

            # テンプレートを読み込み
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()

            # プレースホルダーを置換
            return template.format(
                issue_number=issue_number,
                branch_name=branch_name,
                **extracted_info
            )

        except FileNotFoundError:
            raise FileNotFoundError(f"Template file not found: {template_path}")

        except KeyError as e:
            raise KeyError(f"Missing placeholder in template: {e}")

    def _extract_phase_outputs(
        self,
        issue_number: int,
        phase_outputs: Dict[str, Path]
    ) -> Dict[str, Any]:
        """
        各フェーズの成果物から情報を抽出

        Args:
            issue_number: Issue番号
            phase_outputs: フェーズ名 → 成果物パス

        Returns:
            Dict[str, Any]:
                - summary: 変更サマリー（Issueから抽出）
                - implementation_details: 実装詳細（Phase 4から抽出）
                - test_results: テスト結果（Phase 6から抽出）
                - documentation_updates: ドキュメント更新リスト（Phase 7から抽出）
                - review_points: レビューポイント（設計書から抽出）

        処理フロー:
            1. Issue本文から概要を抽出
            2. Phase 4の implementation.md から実装詳細を抽出
            3. Phase 6の test-result.md からテスト結果を抽出
            4. Phase 7の documentation-update-log.md からドキュメント更新リストを抽出
            5. Phase 2の design.md からレビューポイントを抽出

        エラーハンドリング:
            - 情報抽出に失敗した場合は警告ログを出力し、デフォルト値を使用
        """
        try:
            # Issue本文から概要を抽出
            issue = self.get_issue(issue_number)
            summary = self._extract_summary_from_issue(issue.body or '')

            # Phase 4から実装詳細を抽出
            impl_path = phase_outputs.get('implementation')
            if impl_path and impl_path.exists():
                content = impl_path.read_text(encoding='utf-8')
                implementation_details = self._extract_section(content, '## 実装内容')
                if not implementation_details:
                    implementation_details = '（実装詳細の記載なし）'
            else:
                implementation_details = '（実装詳細の記載なし）'

            # Phase 6からテスト結果を抽出
            test_path = phase_outputs.get('test_result')
            if test_path and test_path.exists():
                content = test_path.read_text(encoding='utf-8')
                test_results = self._extract_section(content, '## テスト結果サマリー')
                if not test_results:
                    test_results = '（テスト結果の記載なし）'
            else:
                test_results = '（テスト結果の記載なし）'

            # Phase 7からドキュメント更新リストを抽出
            doc_path = phase_outputs.get('documentation')
            if doc_path and doc_path.exists():
                content = doc_path.read_text(encoding='utf-8')
                documentation_updates = self._extract_section(content, '## 更新されたドキュメント')
                if not documentation_updates:
                    documentation_updates = '（ドキュメント更新の記載なし）'
            else:
                documentation_updates = '（ドキュメント更新の記載なし）'

            # Phase 2からレビューポイントを抽出
            design_path = phase_outputs.get('design')
            if design_path and design_path.exists():
                content = design_path.read_text(encoding='utf-8')
                review_points = self._extract_section(content, '## レビューポイント')
                if not review_points:
                    review_points = '（レビューポイントの記載なし）'
            else:
                review_points = '（レビューポイントの記載なし）'

            return {
                'summary': summary,
                'implementation_details': implementation_details,
                'test_results': test_results,
                'documentation_updates': documentation_updates,
                'review_points': review_points
            }

        except Exception as e:
            print(f"[WARNING] 成果物抽出中にエラー: {e}")
            # デフォルト値を返却
            return {
                'summary': '（情報抽出エラー）',
                'implementation_details': '（情報抽出エラー）',
                'test_results': '（情報抽出エラー）',
                'documentation_updates': '（情報抽出エラー）',
                'review_points': '（情報抽出エラー）'
            }

    def _extract_section(self, content: str, section_header: str) -> str:
        """
        Markdown文書から特定セクションを抽出

        Args:
            content: Markdown文書全体
            section_header: 抽出したいセクションのヘッダー（例: "## 実装内容"）

        Returns:
            str: 抽出されたセクションの内容（ヘッダー以降、次のヘッダーまで）
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

    def _extract_summary_from_issue(self, issue_body: str) -> str:
        """
        Issue本文から概要を抽出

        Args:
            issue_body: Issue本文

        Returns:
            str: 抽出された概要
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

    def close(self):
        """
        GitHub APIクライアントをクローズ
        """
        # PyGitHubはクローズ不要
        pass
