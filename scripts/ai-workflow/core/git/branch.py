"""Git Branch - ブランチ管理クラス

このモジュールは、Gitブランチに関する操作を提供します。

機能:
    - ブランチ作成
    - ブランチ切り替え
    - ブランチ存在確認
    - 現在のブランチ名取得

使用例:
    >>> from git import Repo
    >>> from core.git.branch import GitBranch
    >>>
    >>> repo = Repo('/path/to/repo')
    >>> branch = GitBranch(repo)
    >>> result = branch.create('feature/test')
    >>> if result['success']:
    ...     print(f"Branch created: {result['branch_name']}")
"""

from typing import Dict, Any, Optional
from git import Repo, GitCommandError
from common.logger import Logger
from common.error_handler import GitBranchError


logger = Logger.get_logger(__name__)


class GitBranch:
    """Gitブランチ管理クラス

    ブランチの作成、切り替え、存在確認等を提供します。

    Attributes:
        repo: GitPythonのRepoオブジェクト
    """

    def __init__(self, repo: Repo):
        """初期化

        Args:
            repo: GitPythonのRepoオブジェクト
        """
        self.repo = repo
        logger.debug("GitBranch initialized")

    def create(
        self,
        branch_name: str,
        base_branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """ブランチを作成してチェックアウト

        Args:
            branch_name: 作成するブランチ名（例: "ai-workflow/issue-315"）
            base_branch: 基準となるブランチ名（省略時は現在のブランチ）

        Returns:
            Dict[str, Any]:
                - success: bool - 成功/失敗
                - branch_name: str - 作成したブランチ名
                - error: Optional[str] - エラーメッセージ

        処理フロー:
            1. exists() でブランチが既に存在するかチェック
               - 既存の場合はチェックアウトまたはリセット
            2. base_branch指定時は、そのブランチにチェックアウト
            3. git checkout -b {branch_name} を実行
            4. 成功/失敗を返却

        エラーハンドリング:
            - Gitコマンド失敗 → {'success': False, 'error': 'Git command failed: ...'}

        Example:
            >>> result = branch.create('ai-workflow/issue-376')
            >>> if not result['success']:
            ...     print(f"Error: {result['error']}")
        """
        try:
            # ブランチ存在チェック
            if self.exists(branch_name):
                logger.info(f"Branch {branch_name} already exists")

                # ローカルブランチが存在するか確認
                local_branches = [ref.name for ref in self.repo.branches]
                local_exists = branch_name in local_branches

                if local_exists:
                    # ローカルブランチが存在する場合はリモートブランチで完全に置き換え
                    logger.info(f"Checking out existing local branch: {branch_name}")
                    current_branch = self.get_current()
                    if current_branch != branch_name:
                        self.repo.git.checkout(branch_name)

                    # リモートから最新を取得してローカルを完全に置き換え
                    try:
                        logger.info(f"Fetching and resetting to remote: origin/{branch_name}")
                        self.repo.git.fetch('origin', branch_name)
                        self.repo.git.reset('--hard', f'origin/{branch_name}')
                        logger.info(f"Successfully reset to origin/{branch_name}")
                    except Exception as e:
                        logger.warning(f"Could not reset to remote: {e}")

                    return {
                        'success': True,
                        'branch_name': branch_name,
                        'error': None
                    }
                else:
                    # リモートのみ存在する場合はチェックアウト
                    logger.info(f"Remote branch exists, checking out: {branch_name}")
                    self.repo.git.checkout(branch_name)
                    return {
                        'success': True,
                        'branch_name': branch_name,
                        'error': None
                    }

            # 基準ブランチ指定時は、そのブランチにチェックアウト
            if base_branch:
                self.repo.git.checkout(base_branch)
                logger.debug(f"Checked out base branch: {base_branch}")

            # ブランチ作成してチェックアウト
            self.repo.git.checkout('-b', branch_name)
            logger.info(f"Created and checked out branch: {branch_name}")

            return {
                'success': True,
                'branch_name': branch_name,
                'error': None
            }

        except GitCommandError as e:
            logger.error(f"Failed to create branch {branch_name}: {e}")
            return {
                'success': False,
                'branch_name': branch_name,
                'error': f'Git command failed: {e}'
            }
        except Exception as e:
            logger.error(f"Unexpected error creating branch {branch_name}: {e}")
            return {
                'success': False,
                'branch_name': branch_name,
                'error': f'Unexpected error: {e}'
            }

    def switch(
        self,
        branch_name: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """指定ブランチにチェックアウト（リモートブランチにも対応）

        Args:
            branch_name: チェックアウトするブランチ名
            force: 強制切り替え（未コミット変更を無視）

        Returns:
            Dict[str, Any]:
                - success: bool - 成功/失敗
                - branch_name: str - 切り替え先ブランチ名
                - error: Optional[str] - エラーメッセージ

        処理フロー:
            1. exists() でブランチの存在確認（ローカル + リモート）
               - 存在しない場合はエラーを返却
            2. 現在のブランチと同じ場合はスキップ（成功を返す）
            3. force=False の場合、未コミット変更をチェック
               - 変更がある場合はエラーを返却
            4. ローカルブランチが存在しない場合、リモートブランチから作成
               - git checkout -b {branch_name} origin/{branch_name}
            5. ローカルブランチが存在する場合、通常のチェックアウト
               - git checkout {branch_name}
            6. 成功/失敗を返却

        エラーハンドリング:
            - ブランチが存在しない → {'success': False, 'error': 'Branch not found'}
            - 未コミット変更がある → {'success': False, 'error': 'Uncommitted changes'}
            - Gitコマンド失敗 → {'success': False, 'error': 'Git command failed: ...'}

        Example:
            >>> result = branch.switch('main')
            >>> if result['success']:
            ...     print(f"Switched to {result['branch_name']}")
        """
        try:
            # ブランチ存在チェック（ローカル + リモート）
            if not self.exists(branch_name, check_remote=True):
                return {
                    'success': False,
                    'branch_name': branch_name,
                    'error': f'Branch not found: {branch_name}. Please run \'init\' first.'
                }

            # 現在のブランチと同じ場合はスキップ
            current_branch = self.get_current()
            if current_branch == branch_name:
                logger.debug(f"Already on branch: {branch_name}")
                return {
                    'success': True,
                    'branch_name': branch_name,
                    'error': None
                }

            # force=False の場合、未コミット変更をチェック
            if not force:
                is_dirty = self.repo.is_dirty()
                has_untracked = len(self.repo.untracked_files) > 0
                if is_dirty or has_untracked:
                    return {
                        'success': False,
                        'branch_name': branch_name,
                        'error': 'You have uncommitted changes. Please commit or stash them before switching branches.'
                    }

            # ローカルブランチ存在確認
            local_branch_exists = self.exists(branch_name, check_remote=False)

            if not local_branch_exists:
                # ローカルブランチが存在しない場合、リモートブランチから作成
                # git checkout -b {branch_name} origin/{branch_name}
                self.repo.git.checkout('-b', branch_name, f'origin/{branch_name}')
                logger.info(f"Created local branch '{branch_name}' from 'origin/{branch_name}'")
            else:
                # ローカルブランチが存在する場合、通常のチェックアウト
                self.repo.git.checkout(branch_name)
                logger.info(f"Switched to branch: {branch_name}")

            return {
                'success': True,
                'branch_name': branch_name,
                'error': None
            }

        except GitCommandError as e:
            logger.error(f"Failed to switch to branch {branch_name}: {e}")
            return {
                'success': False,
                'branch_name': branch_name,
                'error': f'Git command failed: {e}'
            }
        except Exception as e:
            logger.error(f"Unexpected error switching to branch {branch_name}: {e}")
            return {
                'success': False,
                'branch_name': branch_name,
                'error': f'Unexpected error: {e}'
            }

    def exists(self, branch_name: str, check_remote: bool = True) -> bool:
        """ブランチの存在確認（ローカル + リモート）

        Args:
            branch_name: ブランチ名
            check_remote: リモートブランチもチェックするか（デフォルト: True）

        Returns:
            bool: ブランチが存在する場合True

        処理フロー:
            1. ローカルブランチ一覧をチェック
            2. check_remote=True の場合、リモートブランチもチェック
               - origin/{branch_name} の存在を確認

        Example:
            >>> if branch.exists('feature/test'):
            ...     print("Branch exists")
        """
        try:
            # ローカルブランチ一覧を取得
            branches = [b.name for b in self.repo.branches]
            if branch_name in branches:
                return True

            # リモートブランチもチェック
            if check_remote:
                try:
                    remote_branches = [ref.name for ref in self.repo.remote('origin').refs]
                    # origin/{branch_name} の形式でチェック
                    if f'origin/{branch_name}' in remote_branches:
                        return True
                except Exception:
                    pass

            return False
        except Exception:
            return False

    def get_current(self) -> str:
        """現在のブランチ名を取得

        Returns:
            str: 現在のブランチ名

        処理フロー:
            1. self.repo.active_branch.name を取得
            2. ブランチ名を返却

        エラーハンドリング:
            - デタッチHEAD状態の場合は 'HEAD' を返却

        Example:
            >>> current = branch.get_current()
            >>> print(f"Current branch: {current}")
        """
        try:
            return self.repo.active_branch.name
        except TypeError:
            # デタッチHEAD状態の場合
            logger.warning("Repository is in detached HEAD state")
            return 'HEAD'
