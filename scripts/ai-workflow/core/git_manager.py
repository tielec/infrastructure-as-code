"""Git操作を管理するクラス

Phase完了後の成果物を自動的にcommit & pushする機能を提供
- commit_phase_output(): Phase成果物をcommit
- push_to_remote(): リモートリポジトリにpush
- create_commit_message(): コミットメッセージ生成
- get_status(): Git状態確認
"""
import os
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from git import Repo, GitCommandError
from core.metadata_manager import MetadataManager

logger = logging.getLogger(__name__)


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

            # フェーズ固有の成果物ディレクトリを追加スキャン
            phase_specific_files = self._get_phase_specific_files(phase_name)
            target_files.extend(phase_specific_files)

            # 重複除去
            target_files = list(set(target_files))

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
                print(f"[DEBUG] Attempting to push branch: {current_branch}")

                # リモートURL確認
                origin = self.repo.remote(name='origin')
                origin_url = origin.url
                # トークンを隠して表示
                safe_url = origin_url.replace(os.getenv('GITHUB_TOKEN', ''), '***TOKEN***') if os.getenv('GITHUB_TOKEN') else origin_url
                print(f"[DEBUG] Remote URL: {safe_url}")

                # git push origin HEAD
                print(f"[DEBUG] Executing: git push origin HEAD:{current_branch}")
                push_info = origin.push(refspec=f'HEAD:{current_branch}')

                # push結果を詳細ログ
                print(f"[DEBUG] Push result count: {len(push_info)}")
                for info in push_info:
                    print(f"[DEBUG] Push info - flags: {info.flags}, summary: {info.summary}")
                    if info.flags & info.ERROR:
                        print(f"[ERROR] Push failed with error flag")
                        return {
                            'success': False,
                            'retries': retries,
                            'error': f'Push error: {info.summary}'
                        }

                print(f"[INFO] Git push successful")
                return {
                    'success': True,
                    'retries': retries,
                    'error': None
                }

            except GitCommandError as e:
                error_message = str(e)
                print(f"[ERROR] GitCommandError during push: {error_message}")

                # リトライ可能なエラーかチェック
                if not self._is_retriable_error(e):
                    # リトライ不可能なエラー（権限エラー等）
                    print(f"[ERROR] Non-retriable error detected")
                    return {
                        'success': False,
                        'retries': retries,
                        'error': f'Permission or configuration error: {error_message}'
                    }

                # リトライ可能なエラー
                if retries >= max_retries:
                    # 最大リトライ回数に達した
                    print(f"[ERROR] Max retries reached")
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
                print(f"[ERROR] Unexpected error during push: {e}")
                import traceback
                traceback.print_exc()
                return {
                    'success': False,
                    'retries': retries,
                    'error': f'Unexpected error: {e}'
                }

        # ループを抜けた場合（通常は到達しない）
        print(f"[ERROR] Unexpected loop exit")
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

    def _get_phase_specific_files(self, phase_name: str) -> List[str]:
        """
        フェーズ固有の成果物ディレクトリから未追跡・変更ファイルを取得

        各フェーズで作成される成果物の配置場所：
        - implementation: scripts/, pulumi/, ansible/, jenkins/ など
        - test_implementation: tests/, scripts/ai-workflow/tests/ など
        - documentation: *.md ファイル

        Args:
            phase_name: フェーズ名

        Returns:
            List[str]: フェーズ固有のファイル一覧
        """
        phase_files = []

        if phase_name == 'implementation':
            # implementation phaseで作成される可能性のあるディレクトリ
            target_dirs = ['scripts', 'pulumi', 'ansible', 'jenkins']
            phase_files.extend(self._scan_directories(target_dirs))

        elif phase_name == 'test_implementation':
            # test_implementation phaseで作成されるテストファイル
            # リポジトリ全体から test_*.py などのパターンを検索
            test_patterns = [
                'test_*.py', '*_test.py',           # Python
                '*.test.js', '*.spec.js',           # JavaScript
                '*.test.ts', '*.spec.ts',           # TypeScript
                '*_test.go',                        # Go
                'Test*.java', '*Test.java',         # Java
                'test_*.sh',                        # Shell
            ]
            phase_files.extend(self._scan_by_patterns(test_patterns))

        elif phase_name == 'documentation':
            # documentation phaseで更新される可能性のあるドキュメント
            doc_patterns = ['*.md', '*.MD']
            phase_files.extend(self._scan_by_patterns(doc_patterns))

        return phase_files

    def _scan_directories(self, directories: List[str]) -> List[str]:
        """
        指定ディレクトリ配下の未追跡・変更ファイルを取得

        Args:
            directories: スキャン対象ディレクトリ一覧

        Returns:
            List[str]: 見つかったファイル一覧
        """
        from pathlib import Path

        result = []
        repo_root = Path(self.repo_path)

        # 未追跡ファイル
        untracked_files = set(self.repo.untracked_files)

        # 変更ファイル
        modified_files = set(item.a_path for item in self.repo.index.diff(None))

        # ステージングエリアの変更ファイル
        staged_files = set(item.a_path for item in self.repo.index.diff('HEAD'))

        all_changed_files = untracked_files | modified_files | staged_files

        for directory in directories:
            dir_path = repo_root / directory
            if not dir_path.exists():
                continue

            # ディレクトリ配下のファイルをチェック
            for file_path in all_changed_files:
                if file_path.startswith(f"{directory}/"):
                    # Jenkins一時ディレクトリは除外
                    if '@tmp' not in file_path:
                        result.append(file_path)

        return result

    def _scan_by_patterns(self, patterns: List[str]) -> List[str]:
        """
        パターンマッチングで未追跡・変更ファイルを取得

        Args:
            patterns: ファイルパターン一覧（例: ['*.md', 'test_*.py']）

        Returns:
            List[str]: 見つかったファイル一覧
        """
        import fnmatch

        result = []

        # 未追跡ファイル
        untracked_files = set(self.repo.untracked_files)

        # 変更ファイル
        modified_files = set(item.a_path for item in self.repo.index.diff(None))

        # ステージングエリアの変更ファイル
        staged_files = set(item.a_path for item in self.repo.index.diff('HEAD'))

        all_changed_files = untracked_files | modified_files | staged_files

        for file_path in all_changed_files:
            # Jenkins一時ディレクトリは除外
            if '@tmp' in file_path:
                continue

            # パターンマッチング
            for pattern in patterns:
                if fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(file_path, f"**/{pattern}"):
                    result.append(file_path)
                    break  # 一度マッチしたら次のファイルへ

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

    def create_branch(
        self,
        branch_name: str,
        base_branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ブランチを作成してチェックアウト

        Args:
            branch_name: 作成するブランチ名（例: "ai-workflow/issue-315"）
            base_branch: 基準となるブランチ名（省略時は現在のブランチ）

        Returns:
            Dict[str, Any]:
                - success: bool - 成功/失敗
                - branch_name: str - 作成したブランチ名
                - error: Optional[str] - エラーメッセージ

        処理フロー:
            1. branch_exists() でブランチが既に存在するかチェック
               - 既存の場合はエラーを返却
            2. base_branch指定時は、そのブランチにチェックアウト
            3. git checkout -b {branch_name} を実行
            4. 成功/失敗を返却

        エラーハンドリング:
            - ブランチが既に存在 → {'success': False, 'error': 'Branch already exists'}
            - Gitコマンド失敗 → {'success': False, 'error': 'Git command failed: ...'}
        """
        try:
            # ブランチ存在チェック
            if self.branch_exists(branch_name):
                print(f"Branch {branch_name} already exists")

                # ローカルブランチが存在するか確認
                local_branches = [ref.name for ref in self.repo.branches]
                local_exists = branch_name in local_branches

                if local_exists:
                    # ローカルブランチが存在する場合はリモートブランチで完全に置き換え
                    print(f"Checking out existing local branch: {branch_name}")
                    current_branch = self.get_current_branch()
                    if current_branch != branch_name:
                        self.repo.git.checkout(branch_name)

                    # リモートから最新を取得してローカルを完全に置き換え
                    try:
                        print(f"Fetching and resetting to remote: origin/{branch_name}")
                        self.repo.git.fetch('origin', branch_name)
                        self.repo.git.reset('--hard', f'origin/{branch_name}')
                        print(f"Successfully reset to origin/{branch_name}")
                    except Exception as e:
                        print(f"Warning: Could not reset to remote: {e}")

                    return {
                        'success': True,
                        'branch_name': branch_name,
                        'error': None
                    }
                else:
                    # リモートのみ存在する場合はチェックアウト
                    print(f"Remote branch exists, checking out: {branch_name}")
                    self.repo.git.checkout(branch_name)
                    return {
                        'success': True,
                        'branch_name': branch_name,
                        'error': None
                    }

            # 基準ブランチ指定時は、そのブランチにチェックアウト
            if base_branch:
                self.repo.git.checkout(base_branch)

            # ブランチ作成してチェックアウト
            self.repo.git.checkout('-b', branch_name)

            return {
                'success': True,
                'branch_name': branch_name,
                'error': None
            }

        except GitCommandError as e:
            return {
                'success': False,
                'branch_name': branch_name,
                'error': f'Git command failed: {e}'
            }
        except Exception as e:
            return {
                'success': False,
                'branch_name': branch_name,
                'error': f'Unexpected error: {e}'
            }

    def switch_branch(
        self,
        branch_name: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        指定ブランチにチェックアウト（リモートブランチにも対応）

        Args:
            branch_name: チェックアウトするブランチ名
            force: 強制切り替え（未コミット変更を無視）

        Returns:
            Dict[str, Any]:
                - success: bool - 成功/失敗
                - branch_name: str - 切り替え先ブランチ名
                - error: Optional[str] - エラーメッセージ

        処理フロー:
            1. branch_exists() でブランチの存在確認（ローカル + リモート）
               - 存在しない場合はエラーを返却
            2. 現在のブランチと同じ場合はスキップ（成功を返す）
            3. force=False の場合、get_status() で未コミット変更をチェック
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
        """
        try:
            # ブランチ存在チェック（ローカル + リモート）
            if not self.branch_exists(branch_name, check_remote=True):
                return {
                    'success': False,
                    'branch_name': branch_name,
                    'error': f'Branch not found: {branch_name}. Please run \'init\' first.'
                }

            # 現在のブランチと同じ場合はスキップ
            current_branch = self.get_current_branch()
            if current_branch == branch_name:
                return {
                    'success': True,
                    'branch_name': branch_name,
                    'error': None
                }

            # force=False の場合、未コミット変更をチェック
            if not force:
                status = self.get_status()
                if status['is_dirty'] or status['untracked_files']:
                    return {
                        'success': False,
                        'branch_name': branch_name,
                        'error': 'You have uncommitted changes. Please commit or stash them before switching branches.'
                    }

            # ローカルブランチ存在確認
            local_branch_exists = self.branch_exists(branch_name, check_remote=False)

            if not local_branch_exists:
                # ローカルブランチが存在しない場合、リモートブランチから作成
                # git checkout -b {branch_name} origin/{branch_name}
                self.repo.git.checkout('-b', branch_name, f'origin/{branch_name}')
                print(f"[INFO] Created local branch '{branch_name}' from 'origin/{branch_name}'")
            else:
                # ローカルブランチが存在する場合、通常のチェックアウト
                self.repo.git.checkout(branch_name)

            return {
                'success': True,
                'branch_name': branch_name,
                'error': None
            }

        except GitCommandError as e:
            return {
                'success': False,
                'branch_name': branch_name,
                'error': f'Git command failed: {e}'
            }
        except Exception as e:
            return {
                'success': False,
                'branch_name': branch_name,
                'error': f'Unexpected error: {e}'
            }

    def branch_exists(self, branch_name: str, check_remote: bool = True) -> bool:
        """
        ブランチの存在確認（ローカル + リモート）

        Args:
            branch_name: ブランチ名
            check_remote: リモートブランチもチェックするか（デフォルト: True）

        Returns:
            bool: ブランチが存在する場合True

        処理フロー:
            1. ローカルブランチ一覧をチェック
            2. check_remote=True の場合、リモートブランチもチェック
               - origin/{branch_name} の存在を確認
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

    def get_current_branch(self) -> str:
        """
        現在のブランチ名を取得

        Returns:
            str: 現在のブランチ名

        処理フロー:
            1. self.repo.active_branch.name を取得
            2. ブランチ名を返却

        エラーハンドリング:
            - デタッチHEAD状態の場合は 'HEAD' を返却
        """
        try:
            return self.repo.active_branch.name
        except TypeError:
            # デタッチHEAD状態の場合
            return 'HEAD'

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
