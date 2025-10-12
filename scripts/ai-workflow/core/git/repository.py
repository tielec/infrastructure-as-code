"""Git Repository - リポジトリ操作クラス

このモジュールは、Gitリポジトリに関する操作を提供します。

機能:
    - リポジトリルートの取得
    - リポジトリステータスの確認
    - 変更ファイルの取得
    - フェーズ固有ファイルのフィルタリング

使用例:
    >>> from pathlib import Path
    >>> from core.git.repository import GitRepository
    >>>
    >>> repo = GitRepository(Path('/path/to/repo'))
    >>> status = repo.get_status()
    >>> print(f"Current branch: {status['branch']}")
"""

from pathlib import Path
from typing import Dict, Any, List
from git import Repo, GitCommandError
from common.logger import Logger
from common.error_handler import GitOperationError


logger = Logger.get_logger(__name__)


class GitRepository:
    """Gitリポジトリ操作クラス

    リポジトリの状態確認、変更ファイルの取得等を提供します。

    Attributes:
        repo_path: リポジトリのルートパス
        repo: GitPythonのRepoオブジェクト
    """

    def __init__(self, repo_path: Path):
        """初期化

        Args:
            repo_path: Gitリポジトリのルートパス

        Raises:
            GitOperationError: Gitリポジトリが見つからない場合
        """
        self.repo_path = repo_path

        try:
            self.repo = Repo(repo_path)
        except Exception as e:
            raise GitOperationError(
                f"Git repository not found: {repo_path}",
                details={'path': str(repo_path)},
                original_exception=e
            )

        logger.debug(f"GitRepository initialized: {repo_path}")

    def get_root(self) -> Path:
        """リポジトリのルートパスを取得

        Returns:
            Path: リポジトリのルートパス
        """
        return self.repo_path

    def get_status(self) -> Dict[str, Any]:
        """Git状態確認

        Returns:
            Dict[str, Any]:
                - branch: str - 現在のブランチ名
                - is_dirty: bool - 未コミットの変更があるか
                - untracked_files: List[str] - 未追跡ファイル一覧
                - modified_files: List[str] - 変更ファイル一覧
                - staged_files: List[str] - ステージング済みファイル一覧

        Example:
            >>> status = repo.get_status()
            >>> if status['is_dirty']:
            ...     print("Uncommitted changes detected")
        """
        try:
            # ステージング済みファイル
            staged_files = [item.a_path for item in self.repo.index.diff('HEAD')]

            return {
                'branch': self.repo.active_branch.name,
                'is_dirty': self.repo.is_dirty(),
                'untracked_files': self.repo.untracked_files,
                'modified_files': [item.a_path for item in self.repo.index.diff(None)],
                'staged_files': staged_files
            }
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            raise GitOperationError(
                "Failed to get Git status",
                original_exception=e
            )

    def get_changed_files(self) -> List[str]:
        """すべての変更ファイルを取得

        未追跡、変更、ステージング済みファイルをすべて取得します。

        Returns:
            List[str]: 変更ファイルのパス一覧（重複なし）

        Example:
            >>> files = repo.get_changed_files()
            >>> print(f"{len(files)} files changed")
        """
        try:
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
            return list(set(changed_files))

        except Exception as e:
            logger.error(f"Failed to get changed files: {e}")
            raise GitOperationError(
                "Failed to get changed files",
                original_exception=e
            )

    def filter_phase_files(
        self,
        files: List[str],
        issue_number: int
    ) -> List[str]:
        """Phaseに関連するファイルのみフィルタリング

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

        Example:
            >>> files = repo.get_changed_files()
            >>> target_files = repo.filter_phase_files(files, 376)
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

        logger.debug(f"Filtered {len(result)} files for issue-{issue_number}")
        return result

    def get_phase_specific_files(self, phase_name: str) -> List[str]:
        """フェーズ固有の成果物ディレクトリから未追跡・変更ファイルを取得

        各フェーズで作成される成果物の配置場所：
        - implementation: scripts/, pulumi/, ansible/, jenkins/ など
        - test_implementation: tests/, scripts/ai-workflow/tests/ など
        - documentation: *.md ファイル

        Args:
            phase_name: フェーズ名

        Returns:
            List[str]: フェーズ固有のファイル一覧

        Example:
            >>> files = repo.get_phase_specific_files('implementation')
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

        logger.debug(f"Found {len(phase_files)} phase-specific files for {phase_name}")
        return phase_files

    def _scan_directories(self, directories: List[str]) -> List[str]:
        """指定ディレクトリ配下の未追跡・変更ファイルを取得

        Args:
            directories: スキャン対象ディレクトリ一覧

        Returns:
            List[str]: 見つかったファイル一覧
        """
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
        """パターンマッチングで未追跡・変更ファイルを取得

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
