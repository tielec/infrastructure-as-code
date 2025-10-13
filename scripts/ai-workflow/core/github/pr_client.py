"""GitHub PR Client - Pull Request操作クラス

このモジュールは、GitHub Pull Requestに関する操作を提供します。

機能:
    - Pull Requestの作成
    - Pull Requestの更新
    - Pull Requestのクローズ
    - 既存Pull Requestの確認
    - PR番号の取得

使用例:
    >>> from core.github.pr_client import PRClient
    >>>
    >>> client = PRClient(token='xxx', repository='owner/repo')
    >>> result = client.create('Title', 'Body', 'feature/test')
    >>> if result['success']:
    ...     print(f"PR created: {result['pr_url']}")
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from github import Github, GithubException
from common.logger import Logger
from common.error_handler import GitHubAPIError


logger = Logger.get_logger(__name__)


class PRClient:
    """GitHub Pull Request操作クラス

    Pull Requestの作成、更新、クローズ等を提供します。

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
            logger.info(f"PRClient initialized for repository: {self.repository_name}")
        except Exception as e:
            raise GitHubAPIError(
                f"Failed to initialize GitHub client",
                details={'repository': self.repository_name},
                original_exception=e
            )

    def create(
        self,
        title: str,
        body: str,
        head: str,
        base: str = 'main',
        draft: bool = True
    ) -> Dict[str, Any]:
        """Pull Requestを作成

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

        処理フロー:
            1. repository.create_pull()を呼び出し
            2. draft=Trueの場合、PR作成後に draft ステータスを設定
            3. 成功時はPR URLとPR番号を返却
            4. 失敗時はエラーメッセージを返却

        エラーハンドリング:
            - 認証エラー: 401 Unauthorized → GITHUB_TOKENの権限不足
            - 既存PR重複: 422 Unprocessable Entity → 既存PRが存在
            - その他のエラー: 例外メッセージを返却

        Example:
            >>> result = client.create(
            ...     'Fix bug', 'This PR fixes...', 'feature/test'
            ... )
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

            logger.info(f"Created PR #{pr.number}: {pr.html_url}")

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

            logger.error(f"Failed to create PR: {error_message}")

            return {
                'success': False,
                'pr_url': None,
                'pr_number': None,
                'error': error_message
            }

        except Exception as e:
            logger.error(f"Unexpected error creating PR: {e}")
            return {
                'success': False,
                'pr_url': None,
                'pr_number': None,
                'error': f'Unexpected error: {e}'
            }

    def check_existing(
        self,
        head: str,
        base: str = 'main'
    ) -> Optional[Dict[str, Any]]:
        """既存Pull Requestの確認

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

        Example:
            >>> existing = client.check_existing('feature/test')
            >>> if existing:
            ...     print(f"PR already exists: {existing['pr_url']}")
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
                logger.debug(f"Found existing PR #{pr.number}")
                return {
                    'pr_number': pr.number,
                    'pr_url': pr.html_url,
                    'state': pr.state
                }

            # PRが存在しない場合
            return None

        except GithubException as e:
            # エラーが発生した場合はNoneを返却（存在しないとみなす）
            logger.warning(f"Failed to check existing PR: {e}")
            return None

        except Exception as e:
            logger.warning(f"Unexpected error while checking existing PR: {e}")
            return None

    def update(
        self,
        pr_number: int,
        body: str
    ) -> Dict[str, Any]:
        """Pull Requestの本文を更新

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

        Example:
            >>> result = client.update(123, "Updated PR body")
        """
        try:
            # PRを取得
            pr = self.repository.get_pull(pr_number)

            # PR本文を更新
            pr.edit(body=body)
            logger.info(f"Updated PR #{pr_number}")

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

            logger.error(f"Failed to update PR: {error_message}")

            return {
                'success': False,
                'error': error_message
            }

        except Exception as e:
            logger.error(f"Unexpected error updating PR: {e}")
            return {
                'success': False,
                'error': f'Unexpected error: {e}'
            }

    def close(
        self,
        pr_number: int,
        comment: str
    ) -> Dict[str, Any]:
        """Pull Requestをクローズ

        Args:
            pr_number: PR番号
            comment: クローズコメント

        Returns:
            Dict[str, Any]:
                - success: bool
                - error: Optional[str]

        Example:
            >>> result = client.close(123, "Closing due to...")
        """
        try:
            pr = self.repository.get_pull(pr_number)

            # コメントを投稿
            pr.create_issue_comment(comment)

            # PRをクローズ
            pr.edit(state='closed')
            logger.info(f"Closed PR #{pr_number}")

            return {
                'success': True,
                'error': None
            }

        except GithubException as e:
            error_message = f"GitHub API error: {e.status} - {e.data.get('message', 'Unknown error')}"
            logger.error(f"Failed to close PR: {error_message}")

            return {
                'success': False,
                'error': error_message
            }

        except Exception as e:
            logger.error(f"Unexpected error closing PR: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_number_from_issue(
        self,
        issue_number: int
    ) -> Optional[int]:
        """Issue番号から関連するPR番号を取得

        Args:
            issue_number: Issue番号

        Returns:
            Optional[int]: PR番号（見つからない場合は None）

        Example:
            >>> pr_num = client.get_number_from_issue(376)
            >>> if pr_num:
            ...     print(f"Related PR: #{pr_num}")
        """
        try:
            # Issueを取得
            issue = self.repository.get_issue(issue_number)

            # Issueのタイムライン情報からPRを検索
            timeline = issue.get_timeline()
            for event in timeline:
                if event.event == 'cross-referenced' and hasattr(event.source, 'issue'):
                    # PRが見つかった場合
                    source_issue = event.source.issue
                    if hasattr(source_issue, 'pull_request') and source_issue.pull_request:
                        logger.debug(f"Found PR #{source_issue.number} from timeline")
                        return source_issue.number

            # ブランチ名からPRを検索
            branch_name = f"ai-workflow/issue-{issue_number}"
            owner = self.repository.owner.login
            full_head = f"{owner}:{branch_name}"

            pulls = self.repository.get_pulls(
                state='all',
                head=full_head,
                base='main'
            )

            for pr in pulls:
                logger.debug(f"Found PR #{pr.number} from branch search")
                return pr.number

            # 見つからない場合
            logger.warning(f"PR not found for issue #{issue_number}")
            return None

        except Exception as e:
            logger.warning(f"Failed to get PR number: {e}")
            return None

    def generate_body_template(
        self,
        issue_number: int,
        branch_name: str
    ) -> str:
        """PR本文テンプレートを生成

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

        Example:
            >>> body = client.generate_body_template(376, 'ai-workflow/issue-376')
        """
        # テンプレートファイルのパスを取得
        template_path = Path(__file__).parent.parent.parent / 'templates' / 'pr_body_template.md'

        # テンプレートを読み込み
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()

            # プレースホルダーを置換
            return template.format(issue_number=issue_number, branch_name=branch_name)
        except FileNotFoundError:
            logger.warning(f"Template file not found: {template_path}, using default template")
            # デフォルトテンプレートを返す
            return self._get_default_template(issue_number, branch_name)
        except Exception as e:
            logger.error(f"Error reading template: {e}")
            return self._get_default_template(issue_number, branch_name)

    def generate_body_detailed(
        self,
        issue_number: int,
        branch_name: str,
        extracted_info: Dict[str, Any]
    ) -> str:
        """詳細版PR本文を生成

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

        Example:
            >>> info = {'summary': '...', 'implementation_details': '...'}
            >>> body = client.generate_body_detailed(376, 'ai-workflow/issue-376', info)
        """
        # テンプレートファイルのパスを取得
        template_path = Path(__file__).parent.parent.parent / 'templates' / 'pr_body_detailed_template.md'

        try:
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
            logger.error(f"Template file not found: {template_path}")
            raise FileNotFoundError(f"Template file not found: {template_path}")

        except KeyError as e:
            logger.error(f"Missing placeholder in template: {e}")
            raise KeyError(f"Missing placeholder in template: {e}")

    def _get_default_template(self, issue_number: int, branch_name: str) -> str:
        """デフォルトのPR本文テンプレートを返す

        Args:
            issue_number: Issue番号
            branch_name: ブランチ名

        Returns:
            str: デフォルトPR本文
        """
        return f"""# AI Workflow - Issue #{issue_number}

Closes #{issue_number}

## ワークフロー進捗

- [x] Phase 0: 初期化
- [ ] Phase 1: 要件定義
- [ ] Phase 2: 設計
- [ ] Phase 3: テストシナリオ
- [ ] Phase 4: 実装
- [ ] Phase 5: テスト実装
- [ ] Phase 6: テスト実行
- [ ] Phase 7: ドキュメント

## 成果物

すべての成果物は `.ai-workflow/issue-{issue_number}/` ディレクトリに格納されています。

## ブランチ

`{branch_name}`

---
*AI駆動開発自動化ワークフロー (Claude Agent SDK)*
"""

    def close_client(self):
        """GitHub APIクライアントをクローズ"""
        # PyGitHubはクローズ不要
        pass
