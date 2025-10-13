"""Git Commit - コミット操作クラス

このモジュールは、Gitコミットに関する操作を提供します。

機能:
    - フェーズ成果物のコミット
    - リモートへのプッシュ
    - コミットメッセージの生成
    - Git設定の確認

使用例:
    >>> from git import Repo
    >>> from core.git.commit import GitCommit
    >>> from core.metadata_manager import MetadataManager
    >>>
    >>> repo = Repo('/path/to/repo')
    >>> metadata = MetadataManager(...)
    >>> commit = GitCommit(repo, metadata)
    >>> result = commit.commit_phase_output('requirements', 'completed')
"""

import os
import time
from typing import Dict, Any, Optional, List
from git import Repo, GitCommandError
from common.logger import Logger
from common.error_handler import GitCommitError, GitPushError
from common.retry import retry


logger = Logger.get_logger(__name__)


class GitCommit:
    """Gitコミット操作クラス

    コミット作成、プッシュ、コミットメッセージ生成等を提供します。

    Attributes:
        repo: GitPythonのRepoオブジェクト
        metadata_manager: メタデータマネージャー
    """

    def __init__(self, repo: Repo, metadata_manager):
        """初期化

        Args:
            repo: GitPythonのRepoオブジェクト
            metadata_manager: MetadataManagerインスタンス
        """
        self.repo = repo
        self.metadata = metadata_manager

        # GitHub Token設定（環境変数から）
        self._setup_github_credentials()

        logger.debug("GitCommit initialized")

    def commit_phase_output(
        self,
        phase_name: str,
        status: str,
        target_files: List[str],
        review_result: Optional[str] = None
    ) -> Dict[str, Any]:
        """Phase成果物をcommit

        Args:
            phase_name: フェーズ名（requirements, design, etc.）
            status: ステータス（completed/failed）
            target_files: コミット対象ファイル一覧
            review_result: レビュー結果（PASS/PASS_WITH_SUGGESTIONS/FAIL）

        Returns:
            Dict[str, Any]:
                - success: bool - 成功/失敗
                - commit_hash: Optional[str] - コミットハッシュ
                - files_committed: List[str] - コミットされたファイル一覧
                - error: Optional[str] - エラーメッセージ

        処理フロー:
            1. 対象ファイルが0件の場合はスキップ
            2. git add {target_files}
            3. create_commit_message()でメッセージ生成
            4. git commit -m "{message}"
            5. 結果を返却

        エラーハンドリング:
            - コミット対象ファイルが0件 → スキップ（エラーではない）
            - git commitに失敗 → エラー（リトライなし）

        Example:
            >>> result = commit.commit_phase_output(
            ...     'requirements', 'completed', ['file1.py', 'file2.py']
            ... )
        """
        try:
            if not target_files:
                # コミット対象ファイルが0件
                logger.info("No files to commit, skipping")
                return {
                    'success': True,
                    'commit_hash': None,
                    'files_committed': [],
                    'error': None
                }

            # git add
            self.repo.index.add(target_files)
            logger.debug(f"Added {len(target_files)} files to staging area")

            # Git設定（user.name、user.emailが未設定の場合に設定）
            self._ensure_git_config()

            # コミットメッセージ生成
            commit_message = self.create_commit_message(
                phase_name=phase_name,
                status=status,
                review_result=review_result
            )

            # git commit
            commit = self.repo.index.commit(commit_message)
            logger.info(f"Created commit: {commit.hexsha}")

            return {
                'success': True,
                'commit_hash': commit.hexsha,
                'files_committed': target_files,
                'error': None
            }

        except GitCommandError as e:
            logger.error(f"Git commit failed: {e}")
            return {
                'success': False,
                'commit_hash': None,
                'files_committed': [],
                'error': f'Git commit failed: {e}'
            }
        except Exception as e:
            logger.error(f"Unexpected error during commit: {e}")
            return {
                'success': False,
                'commit_hash': None,
                'files_committed': [],
                'error': f'Unexpected error: {e}'
            }

    def push_to_remote(
        self,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ) -> Dict[str, Any]:
        """リモートリポジトリにpush

        Args:
            max_retries: 最大リトライ回数（デフォルト: 3）
            retry_delay: リトライ間隔（秒、デフォルト: 2.0）

        Returns:
            Dict[str, Any]:
                - success: bool - 成功/失敗
                - retries: int - 実際のリトライ回数
                - error: Optional[str] - エラーメッセージ

        処理フロー:
            1. 現在のブランチを取得
            2. git push origin {branch}を実行
            3. 失敗時はリトライ（最大max_retries回）
            4. 結果を返却

        エラーハンドリング:
            - ネットワークエラー → リトライ
            - 権限エラー → エラー（リトライしない）
            - リモートブランチが存在しない → エラー（リトライしない）

        Example:
            >>> result = commit.push_to_remote()
            >>> if not result['success']:
            ...     print(f"Push failed: {result['error']}")
        """
        retries = 0

        while retries <= max_retries:
            try:
                # 現在のブランチを取得
                current_branch = self.repo.active_branch.name
                logger.debug(f"Attempting to push branch: {current_branch}")

                # リモートURL確認
                origin = self.repo.remote(name='origin')
                origin_url = origin.url
                # トークンを隠して表示
                safe_url = origin_url.replace(
                    os.getenv('GITHUB_TOKEN', ''), '***TOKEN***'
                ) if os.getenv('GITHUB_TOKEN') else origin_url
                logger.debug(f"Remote URL: {safe_url}")

                # git push origin HEAD
                logger.debug(f"Executing: git push origin HEAD:{current_branch}")
                push_info = origin.push(refspec=f'HEAD:{current_branch}')

                # push結果を詳細ログ
                logger.debug(f"Push result count: {len(push_info)}")
                for info in push_info:
                    logger.debug(f"Push info - flags: {info.flags}, summary: {info.summary}")
                    if info.flags & info.ERROR:
                        logger.error("Push failed with error flag")
                        return {
                            'success': False,
                            'retries': retries,
                            'error': f'Push error: {info.summary}'
                        }

                logger.info("Git push successful")
                return {
                    'success': True,
                    'retries': retries,
                    'error': None
                }

            except GitCommandError as e:
                error_message = str(e)
                logger.error(f"GitCommandError during push: {error_message}")

                # リトライ可能なエラーかチェック
                if not self._is_retriable_error(e):
                    # リトライ不可能なエラー（権限エラー等）
                    logger.error("Non-retriable error detected")
                    return {
                        'success': False,
                        'retries': retries,
                        'error': f'Permission or configuration error: {error_message}'
                    }

                # リトライ可能なエラー
                if retries >= max_retries:
                    # 最大リトライ回数に達した
                    logger.error("Max retries reached")
                    return {
                        'success': False,
                        'retries': retries,
                        'error': f'Max retries exceeded: {error_message}'
                    }

                # リトライ
                retries += 1
                logger.warning(
                    f"Git push failed. Retrying ({retries}/{max_retries})... "
                    f"Error: {error_message}"
                )
                time.sleep(retry_delay)

            except Exception as e:
                # その他のエラー
                logger.error(f"Unexpected error during push: {e}", exc_info=True)
                return {
                    'success': False,
                    'retries': retries,
                    'error': f'Unexpected error: {e}'
                }

        # ループを抜けた場合（通常は到達しない）
        logger.error("Unexpected loop exit")
        return {
            'success': False,
            'retries': retries,
            'error': 'Unexpected loop exit'
        }

    def create_commit_message(
        self,
        phase_name: str,
        status: str,
        review_result: Optional[str] = None
    ) -> str:
        """コミットメッセージを生成

        Args:
            phase_name: フェーズ名
            status: ステータス（completed/failed）
            review_result: レビュー結果（省略可）

        Returns:
            str: コミットメッセージ

        フォーマット:
            [ai-workflow] Phase X (phase_name) - status

            Issue: #XXX
            Phase: X (phase_name)
            Status: completed/failed
            Review: PASS/PASS_WITH_SUGGESTIONS/FAIL/N/A

            Auto-generated by AI Workflow

        例:
            [ai-workflow] Phase 1 (requirements) - completed

            Issue: #305
            Phase: 1 (requirements)
            Status: completed
            Review: PASS

            Auto-generated by AI Workflow

        Example:
            >>> message = commit.create_commit_message('requirements', 'completed', 'PASS')
        """
        from phases.base_phase import BasePhase

        # フェーズ番号を取得
        phase_number_str = BasePhase.PHASE_NUMBERS.get(phase_name, '00')
        phase_number = int(phase_number_str)  # ゼロパディングを除去（"01" → 1）

        # Issue番号を取得
        issue_number = self.metadata.data.get('issue_number', 'Unknown')

        # レビュー結果（未実施の場合はN/A）
        review = review_result or 'N/A'

        # コミットメッセージ作成
        message_parts = [
            f"[ai-workflow] Phase {phase_number} ({phase_name}) - {status}",
            "",
            f"Issue: #{issue_number}",
            f"Phase: {phase_number} ({phase_name})",
            f"Status: {status}",
            f"Review: {review}",
            "",
            "Auto-generated by AI Workflow"
        ]

        return '\n'.join(message_parts)

    def _ensure_git_config(self) -> None:
        """Git設定を確認し、未設定の場合は環境変数から設定

        環境変数の優先順位:
            1. GIT_COMMIT_USER_NAME / GIT_COMMIT_USER_EMAIL（最優先、新規）
            2. GIT_AUTHOR_NAME / GIT_AUTHOR_EMAIL（互換性のため継続サポート）
            3. デフォルト値（'AI Workflow' / 'ai-workflow@tielec.local'）

        バリデーション:
            - ユーザー名: 1-100文字
            - メールアドレス: '@'の存在確認（RFC 5322準拠の厳密チェックは不要）

        ログ出力:
            - [INFO] Git設定完了: user.name=..., user.email=...
            - [WARN] バリデーションエラー時の警告

        処理フロー:
            1. 現在のuser.name、user.emailを取得
            2. 未設定の場合、環境変数から優先順位で取得
            3. バリデーション実施（エラー時は警告ログ、デフォルト値使用）
            4. git config --local user.name/user.emailで設定
            5. ログ出力
        """
        try:
            # 現在の設定を取得
            config_reader = self.repo.config_reader()

            # user.nameをチェック
            try:
                user_name = config_reader.get_value('user', 'name')
            except Exception:
                user_name = None

            # user.emailをチェック
            try:
                user_email = config_reader.get_value('user', 'email')
            except Exception:
                user_email = None

            # 未設定の場合、環境変数またはデフォルト値を使用
            # 優先順位: GIT_COMMIT_USER_NAME > GIT_AUTHOR_NAME > デフォルト
            if not user_name:
                user_name = (
                    os.environ.get('GIT_COMMIT_USER_NAME') or
                    os.environ.get('GIT_AUTHOR_NAME') or
                    'AI Workflow'
                )

            # 優先順位: GIT_COMMIT_USER_EMAIL > GIT_AUTHOR_EMAIL > デフォルト
            if not user_email:
                user_email = (
                    os.environ.get('GIT_COMMIT_USER_EMAIL') or
                    os.environ.get('GIT_AUTHOR_EMAIL') or
                    'ai-workflow@tielec.local'
                )

            # バリデーション: ユーザー名長さチェック（1-100文字）
            if len(user_name) < 1 or len(user_name) > 100:
                logger.warning(
                    f"User name length is invalid ({len(user_name)} chars), using default"
                )
                user_name = 'AI Workflow'

            # バリデーション: メールアドレス形式チェック（基本的な'@'の存在確認のみ）
            if '@' not in user_email:
                logger.warning(f"Invalid email format: {user_email}, using default")
                user_email = 'ai-workflow@tielec.local'

            # config_writerで設定（ローカルリポジトリのみ）
            with self.repo.config_writer() as config_writer:
                config_writer.set_value('user', 'name', user_name)
                config_writer.set_value('user', 'email', user_email)

            logger.info(f"Git設定完了: user.name={user_name}, user.email={user_email}")

        except Exception as e:
            logger.warning(f"Git設定に失敗しましたが、コミットは続行します: {e}")

    def _is_retriable_error(self, error: Exception) -> bool:
        """リトライ可能なエラーかどうか判定

        Args:
            error: 例外オブジェクト

        Returns:
            bool: リトライ可能ならTrue

        リトライ可能なエラー:
            - ネットワークタイムアウト
            - 一時的な接続エラー

        リトライ不可能なエラー:
            - 認証エラー
            - 権限エラー
            - リモートブランチ不存在
        """
        error_message = str(error).lower()

        # リトライ不可能なエラーキーワード
        non_retriable_keywords = [
            'permission denied',
            'authentication failed',
            'could not read from remote repository',
            'does not appear to be a git repository',
            'fatal: unable to access'
        ]

        for keyword in non_retriable_keywords:
            if keyword in error_message:
                return False

        # リトライ可能なエラーキーワード
        retriable_keywords = [
            'timeout',
            'connection refused',
            'network is unreachable',
            'temporary failure'
        ]

        for keyword in retriable_keywords:
            if keyword in error_message:
                return True

        # デフォルトはリトライ可能（ネットワークエラーの可能性）
        return True

    def _setup_github_credentials(self) -> None:
        """GitHub Token認証の設定

        環境変数GITHUB_TOKENを使用してGit remoteのURLを更新

        処理フロー:
            1. 環境変数GITHUB_TOKENを取得
            2. originリモートの現在のURLを取得
            3. HTTPS URLの場合、認証情報付きURLに変換
            4. リモートURLを更新

        注意:
            - GITHUB_TOKENが未設定の場合は警告を出力して続行
            - HTTPS URL以外（SSH等）の場合は変換しない
        """
        github_token = os.getenv('GITHUB_TOKEN')
        if not github_token:
            logger.warning("GITHUB_TOKEN not found in environment variables")
            return

        try:
            origin = self.repo.remote(name='origin')
            current_url = origin.url

            # HTTPS URLの場合のみ変換
            if current_url.startswith('https://github.com/'):
                # https://github.com/owner/repo.git → owner/repo.git
                path = current_url.replace('https://github.com/', '')
                # 認証情報付きURLに変換
                new_url = f'https://{github_token}@github.com/{path}'
                origin.set_url(new_url)
                logger.info("Git remote URL configured with GitHub token authentication")
            else:
                logger.info(
                    f"Git remote URL is not HTTPS, skipping token configuration: {current_url}"
                )

        except Exception as e:
            logger.warning(f"Failed to setup GitHub credentials: {e}")
