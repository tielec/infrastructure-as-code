"""WorkflowController - ワークフロー制御クラス

このモジュールは、AI駆動ワークフロー全体の制御を担当します。

機能:
    - ワークフロー初期化（メタデータ作成、ブランチ作成）
    - 単一フェーズの実行制御
    - 全フェーズの順次実行制御
    - エラーハンドリング
    - 依存関係チェック

使用例:
    >>> from core.workflow_controller import WorkflowController
    >>> controller = WorkflowController(
    ...     repo_root=Path('.'),
    ...     config_manager=config_manager,
    ...     # ... 他の依存オブジェクト
    ... )
    >>> result = controller.initialize(issue_number=380, issue_url='https://...')
    >>> if result['success']:
    ...     result = controller.execute_phase('planning')
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from core.metadata_manager import MetadataManager
from core.config_manager import ConfigManager
from core.git.repository import GitRepository
from core.git.branch import GitBranch
from core.git.commit import GitCommit
from core.github.issue_client import IssueClient
from core.github.pr_client import PRClient
from core.github.comment_client import CommentClient
from core.claude_agent_client import ClaudeAgentClient
from phases.base.phase_executor import PhaseExecutor
from common.error_handler import (
    MetadataError, GitOperationError, GitHubAPIError,
    ClaudeAPIError, WorkflowError
)
from common.logger import Logger


class WorkflowController:
    """ワークフロー制御クラス

    責務:
        - ワークフロー初期化（メタデータ作成、ブランチ作成）
        - 単一フェーズの実行制御
        - 全フェーズの順次実行制御
        - エラーハンドリング
        - 依存関係チェック
    """

    # フェーズ実行順序の定義
    PHASE_ORDER = [
        'planning',
        'requirements',
        'design',
        'test_scenario',
        'implementation',
        'test_implementation',
        'testing',
        'documentation',
        'report',
        'evaluation'
    ]

    def __init__(
        self,
        repo_root: Path,
        config_manager: ConfigManager,
        metadata_manager: MetadataManager,
        git_repository: GitRepository,
        git_branch: GitBranch,
        git_commit: GitCommit,
        issue_client: IssueClient,
        pr_client: PRClient,
        comment_client: CommentClient,
        claude_client: ClaudeAgentClient
    ):
        """初期化

        Args:
            repo_root: リポジトリルートパス
            config_manager: ConfigManagerインスタンス
            metadata_manager: MetadataManagerインスタンス
            git_repository: GitRepositoryインスタンス
            git_branch: GitBranchインスタンス
            git_commit: GitCommitインスタンス
            issue_client: IssueClientインスタンス
            pr_client: PRClientインスタンス
            comment_client: CommentClientインスタンス
            claude_client: ClaudeAgentClientインスタンス
        """
        self.repo_root = repo_root
        self.config = config_manager
        self.metadata = metadata_manager
        self.git_repo = git_repository
        self.git_branch = git_branch
        self.git_commit = git_commit
        self.issue_client = issue_client
        self.pr_client = pr_client
        self.comment_client = comment_client
        self.claude_client = claude_client
        self.logger = Logger.get_logger(__name__)

    def initialize(self, issue_number: int, issue_url: str) -> Dict[str, Any]:
        """ワークフロー初期化

        処理内容:
            1. GitHub Issue情報を取得
            2. メタデータファイル作成
            3. 作業ブランチ作成
            4. 初期状態を記録

        Args:
            issue_number: Issue番号
            issue_url: Issue URL

        Returns:
            Dict[str, Any]: 初期化結果
                - success: bool
                - branch_name: str
                - metadata_path: str
                - error: Optional[str]

        Raises:
            GitHubAPIError: GitHub API呼び出し失敗
            GitOperationError: Git操作失敗
            MetadataError: メタデータ作成失敗
        """
        try:
            self.logger.info(f'Initializing workflow for Issue #{issue_number}')

            # 1. GitHub Issue情報を取得
            issue_info = self.issue_client.get_info(issue_number)

            # 2. メタデータファイル作成
            self.metadata.create_new(
                issue_number=issue_number,
                issue_url=issue_url,
                issue_title=issue_info.get('title', 'Untitled')
            )

            # 3. 作業ブランチ作成
            branch_name = f'ai-workflow/issue-{issue_number}'
            self.git_branch.create_and_checkout(branch_name)

            # 4. 初期状態を記録
            self.metadata.save()

            self.logger.info(f'Workflow initialized successfully: {branch_name}')

            return {
                'success': True,
                'branch_name': branch_name,
                'metadata_path': str(self.metadata.metadata_path),
                'error': None
            }

        except GitHubAPIError as e:
            self.logger.error(f'GitHub API error during initialization: {e}')
            return {'success': False, 'error': str(e)}
        except GitOperationError as e:
            self.logger.error(f'Git error during initialization: {e}')
            return {'success': False, 'error': str(e)}
        except MetadataError as e:
            self.logger.error(f'Metadata error during initialization: {e}')
            return {'success': False, 'error': str(e)}
        except Exception as e:
            self.logger.error(f'Unexpected error during initialization: {e}')
            return {'success': False, 'error': str(e)}

    def execute_phase(
        self,
        phase_name: str,
        skip_dependency_check: bool = False,
        ignore_dependencies: bool = False
    ) -> Dict[str, Any]:
        """単一フェーズを実行

        処理内容:
            1. フェーズ名の検証
            2. 依存関係チェック（オプション）
            3. PhaseExecutorを使用してフェーズを実行
            4. 実行結果をメタデータに記録
            5. エラーハンドリング

        Args:
            phase_name: フェーズ名
            skip_dependency_check: 依存関係チェックをスキップ（デフォルト: False）
            ignore_dependencies: 依存関係違反を警告のみで許可（デフォルト: False）

        Returns:
            Dict[str, Any]: 実行結果
                - success: bool
                - phase: str
                - review_result: str (PASS/PASS_WITH_SUGGESTIONS/FAIL)
                - error: Optional[str]

        Raises:
            WorkflowError: フェーズ実行失敗
        """
        try:
            self.logger.info(f'Executing phase: {phase_name}')

            # 1. フェーズ名の検証
            if phase_name not in self.PHASE_ORDER:
                raise WorkflowError(f'Unknown phase: {phase_name}')

            # 2. PhaseExecutorを使用してフェーズを実行
            executor = PhaseExecutor.create(
                phase_name=phase_name,
                working_dir=self.repo_root,
                metadata_manager=self.metadata,
                claude_client=self.claude_client,
                issue_client=self.issue_client,
                git_commit=self.git_commit,
                skip_dependency_check=skip_dependency_check,
                ignore_dependencies=ignore_dependencies
            )

            result = executor.run()

            # 3. 実行結果を返す（メタデータはPhaseExecutor内で更新済み）
            self.logger.info(f'Phase {phase_name} completed: {result["review_result"]}')

            return {
                'success': result['success'],
                'phase': phase_name,
                'review_result': result.get('review_result'),
                'error': result.get('error')
            }

        except WorkflowError as e:
            self.logger.error(f'Workflow error in phase {phase_name}: {e}')
            return {'success': False, 'phase': phase_name, 'error': str(e)}
        except Exception as e:
            self.logger.error(f'Unexpected error in phase {phase_name}: {e}')
            return {'success': False, 'phase': phase_name, 'error': str(e)}

    def execute_all_phases(
        self,
        start_from: Optional[str] = None,
        skip_dependency_check: bool = False,
        ignore_dependencies: bool = False
    ) -> Dict[str, Any]:
        """全フェーズを順次実行

        処理内容:
            1. フェーズ実行順序に従って順次実行
            2. 各フェーズの依存関係チェック
            3. フェーズ失敗時はエラーハンドリング
            4. 進捗状況のリアルタイム表示

        Args:
            start_from: 開始フェーズ（指定がない場合は最初から）
            skip_dependency_check: 依存関係チェックをスキップ
            ignore_dependencies: 依存関係違反を警告のみで許可

        Returns:
            Dict[str, Any]: 実行結果サマリー
                - success: bool - 全フェーズが成功したか
                - completed_phases: List[str] - 完了したフェーズ一覧
                - failed_phase: Optional[str] - 失敗したフェーズ
                - error: Optional[str] - エラーメッセージ
                - total_duration: float - 総実行時間（秒）
        """
        import time
        start_time = time.time()
        completed_phases = []
        failed_phase = None
        error = None

        try:
            self.logger.info('Starting full workflow execution')

            # 開始フェーズのインデックスを取得
            start_index = 0
            if start_from:
                if start_from in self.PHASE_ORDER:
                    start_index = self.PHASE_ORDER.index(start_from)
                else:
                    raise WorkflowError(f'Unknown start phase: {start_from}')

            for i, phase in enumerate(self.PHASE_ORDER[start_index:], start_index + 1):
                self.logger.info(f'Progress: [{i}/{len(self.PHASE_ORDER)}] Phase: {phase}')

                # フェーズ実行
                result = self.execute_phase(
                    phase,
                    skip_dependency_check=skip_dependency_check,
                    ignore_dependencies=ignore_dependencies
                )

                if result['success']:
                    completed_phases.append(phase)
                else:
                    # フェーズ失敗 → 停止
                    failed_phase = phase
                    error = result.get('error', 'Unknown error')
                    self.logger.error(f'Phase {phase} failed. Stopping workflow.')
                    break

            total_duration = time.time() - start_time
            success = (failed_phase is None)

            self.logger.info(f'Workflow execution completed: success={success}')

            return {
                'success': success,
                'completed_phases': completed_phases,
                'failed_phase': failed_phase,
                'error': error,
                'total_duration': total_duration
            }

        except Exception as e:
            total_duration = time.time() - start_time
            self.logger.error(f'Unexpected error during full workflow execution: {e}')
            return {
                'success': False,
                'completed_phases': completed_phases,
                'failed_phase': failed_phase or 'unknown',
                'error': str(e),
                'total_duration': total_duration
            }

    def get_workflow_status(self) -> Dict[str, Any]:
        """ワークフローの現在の状態を取得

        Returns:
            Dict[str, Any]: ワークフロー状態
                - issue_number: int
                - branch_name: str
                - phases: Dict[str, Dict[str, Any]] - 各フェーズの状態
        """
        try:
            return {
                'issue_number': self.metadata.data.get('issue_number'),
                'branch_name': self.metadata.data.get('branch_name'),
                'phases': self.metadata.data.get('phases', {})
            }
        except Exception as e:
            self.logger.error(f'Failed to get workflow status: {e}')
            return {
                'issue_number': None,
                'branch_name': None,
                'phases': {}
            }
