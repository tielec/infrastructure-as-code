"""Git操作を管理するクラス

Phase完了後の成果物を自動的にcommit & pushする機能を提供
- commit_phase_output(): Phase成果物をcommit
- push_to_remote(): リモートリポジトリにpush
- create_commit_message(): コミットメッセージ生成
- get_status(): Git状態確認
"""
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from git import Repo, GitCommandError
from core.metadata_manager import MetadataManager


class GitManager:
    """Git操作マネージャー"""

    def __init__(
        self,
        repo_path: Path,
        metadata_manager: MetadataManager,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初期化

        Args:
            repo_path: Gitリポジトリのルートパス
            metadata_manager: メタデータマネージャー
            config: 設定（省略時はconfig.yamlから読み込み）
        """
        self.repo_path = repo_path
        self.metadata = metadata_manager
        self.config = config or {}

        # Gitリポジトリを開く
        try:
            self.repo = Repo(repo_path)
        except Exception as e:
            raise RuntimeError(f"Git repository not found: {repo_path}") from e

        # GitHub Token設定（環境変数から）
        self._setup_github_credentials()

    def commit_phase_output(
        self,
        phase_name: str,
        status: str,
        review_result: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Phase成果物をcommit

        Args:
            phase_name: フェーズ名（requirements, design, etc.）
            status: ステータス（completed/failed）
            review_result: レビュー結果（PASS/PASS_WITH_SUGGESTIONS/FAIL）

        Returns:
            Dict[str, Any]:
                - success: bool - 成功/失敗
                - commit_hash: Optional[str] - コミットハッシュ
                - files_committed: List[str] - コミットされたファイル一覧
                - error: Optional[str] - エラーメッセージ

        処理フロー:
            1. git statusで変更ファイルを確認
            2. .ai-workflow/issue-XXX/ 配下のファイルをフィルタリング
            3. 対象ファイルが0件の場合はスキップ
            4. git add .ai-workflow/issue-XXX/
            5. create_commit_message()でメッセージ生成
            6. git commit -m "{message}"
            7. 結果を返却

        エラーハンドリング:
            - Gitリポジトリが存在しない → エラー
            - コミット対象ファイルが0件 → スキップ（エラーではない）
            - git commitに失敗 → エラー（リトライなし）
        """
        try:
            # Issue番号を取得
            issue_number = self.metadata.data.get('issue_number')
            if not issue_number:
                return {
                    'success': False,
                    'commit_hash': None,
                    'files_committed': [],
                    'error': 'Issue number not found in metadata'
                }

            # 変更ファイルを取得
            changed_files = []

            # 未追跡ファイル
            untracked_files = self.repo.untracked_files
            changed_files.extend(untracked_files)

            # 変更ファイル（tracked）
            modified_files = [item.a_path for item in self.repo.index.diff(None)]
            changed_files.extend(modified_files)

            # ステージングエリアの変更ファイル
            staged_files = [item.a_path for item in self.repo.index.diff('HEAD')]
            changed_files.extend(staged_files)

            # 重複を除去
            changed_files = list(set(changed_files))

            # .ai-workflow/issue-XXX/ 配下のファイルのみフィルタリング
            target_files = self._filter_phase_files(changed_files, issue_number)

            if not target_files:
                # コミット対象ファイルが0件
                return {
                    'success': True,
                    'commit_hash': None,
                    'files_committed': [],
                    'error': None
                }

            # git add
            self.repo.index.add(target_files)

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

            return {
                'success': True,
                'commit_hash': commit.hexsha,
                'files_committed': target_files,
                'error': None
            }

        except GitCommandError as e:
            return {
                'success': False,
                'commit_hash': None,
                'files_committed': [],
                'error': f'Git commit failed: {e}'
            }
        except Exception as e:
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
        """
        リモートリポジトリにpush

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
        """
        retries = 0

        while retries <= max_retries:
            try:
                # 現在のブランチを取得
                current_branch = self.repo.active_branch.name

                # git push origin HEAD
                origin = self.repo.remote(name='origin')
                origin.push(refspec=f'HEAD:{current_branch}')

                return {
                    'success': True,
                    'retries': retries,
                    'error': None
                }

            except GitCommandError as e:
                error_message = str(e)

                # リトライ可能なエラーかチェック
                if not self._is_retriable_error(e):
                    # リトライ不可能なエラー（権限エラー等）
                    return {
                        'success': False,
                        'retries': retries,
                        'error': f'Permission or configuration error: {error_message}'
                    }

                # リトライ可能なエラー
                if retries >= max_retries:
                    # 最大リトライ回数に達した
                    return {
                        'success': False,
                        'retries': retries,
                        'error': f'Max retries exceeded: {error_message}'
                    }

                # リトライ
                retries += 1
                print(f"[INFO] Git push failed. Retrying ({retries}/{max_retries})... Error: {error_message}")
                time.sleep(retry_delay)

            except Exception as e:
                # その他のエラー
                return {
                    'success': False,
                    'retries': retries,
                    'error': f'Unexpected error: {e}'
                }

        # ループを抜けた場合（通常は到達しない）
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
        """
        コミットメッセージを生成

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

    def get_status(self) -> Dict[str, Any]:
        """
        Git状態確認

        Returns:
            Dict[str, Any]:
                - branch: str - 現在のブランチ名
                - is_dirty: bool - 未コミットの変更があるか
                - untracked_files: List[str] - 未追跡ファイル一覧
                - modified_files: List[str] - 変更ファイル一覧
        """
        return {
            'branch': self.repo.active_branch.name,
            'is_dirty': self.repo.is_dirty(),
            'untracked_files': self.repo.untracked_files,
            'modified_files': [item.a_path for item in self.repo.index.diff(None)]
        }

    def _filter_phase_files(
        self,
        files: List[str],
        issue_number: int
    ) -> List[str]:
        """
        Phaseに関連するファイルのみフィルタリング

        コミット対象:
        - .ai-workflow/issue-XXX/ 配下のすべてのファイル（必須）
        - プロジェクト本体で変更されたファイル（.ai-workflow/以外）

        除外対象:
        - .ai-workflow/issue-YYY/ 配下のファイル（他のIssue）
        - Jenkins一時ディレクトリ（*@tmp/）

        Args:
            files: ファイルパス一覧
            issue_number: Issue番号

        Returns:
            List[str]: フィルタリング後のファイル一覧
        """
        target_prefix = f".ai-workflow/issue-{issue_number}/"
        result = []

        for f in files:
            # 0. Jenkins一時ディレクトリは常に除外（@tmpを含むパス）
            if '@tmp' in f:
                continue
            # 1. 対象Issue配下のファイルは必ず含める
            if f.startswith(target_prefix):
                result.append(f)
            # 2. .ai-workflowディレクトリ配下だが対象Issue以外のファイルは除外
            elif f.startswith(".ai-workflow/"):
                continue
            # 3. プロジェクト本体のファイルは含める
            else:
                result.append(f)

        return result

    def _ensure_git_config(self) -> None:
        """
        Git設定を確認し、未設定の場合は環境変数から設定

        環境変数:
            - GIT_AUTHOR_NAME: コミットユーザー名（デフォルト: AI Workflow）
            - GIT_AUTHOR_EMAIL: コミットユーザーメール（デフォルト: ai-workflow@tielec.local）

        処理フロー:
            1. 現在のuser.name、user.emailを取得
            2. 未設定の場合、環境変数から取得
            3. 環境変数も未設定の場合、デフォルト値を使用
            4. git config --local user.name/user.emailで設定
        """
        import os

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
            if not user_name:
                user_name = os.environ.get('GIT_AUTHOR_NAME', 'AI Workflow')

            if not user_email:
                user_email = os.environ.get('GIT_AUTHOR_EMAIL', 'ai-workflow@tielec.local')

            # config_writerで設定
            with self.repo.config_writer() as config_writer:
                config_writer.set_value('user', 'name', user_name)
                config_writer.set_value('user', 'email', user_email)

            print(f"[INFO] Git設定完了: user.name={user_name}, user.email={user_email}")

        except Exception as e:
            print(f"[WARN] Git設定に失敗しましたが、コミットは続行します: {e}")

    def _is_retriable_error(self, error: Exception) -> bool:
        """
        リトライ可能なエラーかどうか判定

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
        """
        GitHub Token認証の設定

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
            print("[WARNING] GITHUB_TOKEN not found in environment variables")
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
                print(f"[INFO] Git remote URL configured with GitHub token authentication")
            else:
                print(f"[INFO] Git remote URL is not HTTPS, skipping token configuration: {current_url}")

        except Exception as e:
            print(f"[WARNING] Failed to setup GitHub credentials: {e}")
