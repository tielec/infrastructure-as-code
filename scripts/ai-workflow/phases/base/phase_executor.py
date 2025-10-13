"""Phase Executor - フェーズ実行制御

このモジュールは、フェーズの実行制御、リトライ、依存関係チェック、
Git自動commit/pushなどの機能を提供します。

機能:
    - フェーズの実行制御（execute → review → revise）
    - 依存関係の検証
    - リトライ機能（最大3回）
    - Git自動commit & push
    - 進捗・レビュー結果のGitHub報告

使用例:
    >>> executor = PhaseExecutor.create(
    ...     phase_name='planning',
    ...     metadata_manager=metadata_manager,
    ...     claude_client=claude_client,
    ...     issue_client=issue_client,
    ...     git_commit=git_commit
    ... )
    >>> result = executor.run()
    >>> if result['success']:
    ...     print("フェーズ完了")
"""

import importlib
from pathlib import Path
from typing import Dict, Any, Optional
from core.metadata_manager import MetadataManager
from core.claude_agent_client import ClaudeAgentClient
from core.github.issue_client import IssueClient
from core.git.commit import GitCommit
from phases.base.abstract_phase import AbstractPhase
from phases.base.phase_validator import PhaseValidator
from phases.base.phase_reporter import PhaseReporter
from common.logger import Logger


class PhaseExecutor:
    """フェーズ実行制御クラス

    フェーズの実行、レビュー、リトライを制御します。

    Attributes:
        MAX_RETRIES: 最大リトライ回数（3回）
        phase: フェーズインスタンス
        metadata: メタデータマネージャー
        issue_client: Issue操作クライアント
        git_commit: Gitコミット操作
        validator: フェーズバリデーター
        reporter: フェーズレポーター
        skip_dependency_check: 依存関係チェックをスキップするフラグ
        ignore_dependencies: 依存関係違反を警告のみで許可するフラグ
        logger: ロガーインスタンス
    """

    MAX_RETRIES = 3

    def __init__(
        self,
        phase: AbstractPhase,
        metadata_manager: MetadataManager,
        issue_client: IssueClient,
        git_commit: GitCommit,
        validator: PhaseValidator,
        reporter: PhaseReporter,
        skip_dependency_check: bool = False,
        ignore_dependencies: bool = False
    ):
        """初期化

        Args:
            phase: フェーズインスタンス
            metadata_manager: メタデータマネージャー
            issue_client: Issue操作クライアント
            git_commit: Gitコミット操作
            validator: フェーズバリデーター
            reporter: フェーズレポーター
            skip_dependency_check: 依存関係チェックをスキップ（デフォルト: False）
            ignore_dependencies: 依存関係違反を警告のみで許可（デフォルト: False）
        """
        self.phase = phase
        self.metadata = metadata_manager
        self.issue_client = issue_client
        self.git_commit = git_commit
        self.validator = validator
        self.reporter = reporter
        self.skip_dependency_check = skip_dependency_check
        self.ignore_dependencies = ignore_dependencies
        self.logger = Logger.get_logger(__name__)

    @classmethod
    def create(
        cls,
        phase_name: str,
        working_dir: Path,
        metadata_manager: MetadataManager,
        claude_client: ClaudeAgentClient,
        issue_client: IssueClient,
        git_commit: GitCommit,
        skip_dependency_check: bool = False,
        ignore_dependencies: bool = False
    ) -> 'PhaseExecutor':
        """PhaseExecutorインスタンスを生成（ファクトリーメソッド）

        Args:
            phase_name: フェーズ名（例: 'planning', 'requirements'）
            working_dir: 作業ディレクトリ（リポジトリルート）
            metadata_manager: メタデータマネージャー
            claude_client: Claude Agent SDKクライアント
            issue_client: Issue操作クライアント
            git_commit: Gitコミット操作
            skip_dependency_check: 依存関係チェックをスキップ
            ignore_dependencies: 依存関係違反を警告のみで許可

        Returns:
            PhaseExecutor: 初期化されたインスタンス

        Raises:
            ImportError: フェーズクラスのインポートに失敗した場合
            AttributeError: フェーズクラスが存在しない場合
        """
        # フェーズクラスマッピング
        phase_class_map = {
            'planning': ('phases.planning', 'PlanningPhase'),
            'requirements': ('phases.requirements', 'RequirementsPhase'),
            'design': ('phases.design', 'DesignPhase'),
            'test_scenario': ('phases.test_scenario', 'TestScenarioPhase'),
            'implementation': ('phases.implementation', 'ImplementationPhase'),
            'test_implementation': ('phases.test_implementation', 'TestImplementationPhase'),
            'testing': ('phases.testing', 'TestingPhase'),
            'documentation': ('phases.documentation', 'DocumentationPhase'),
            'report': ('phases.report', 'ReportPhase'),
            'evaluation': ('phases.evaluation', 'EvaluationPhase')
        }

        # フェーズクラスを動的にインポート
        if phase_name not in phase_class_map:
            raise ValueError(f"Unknown phase: {phase_name}")

        module_name, class_name = phase_class_map[phase_name]
        module = importlib.import_module(module_name)
        phase_class = getattr(module, class_name)

        # フェーズインスタンス生成
        phase_instance = phase_class(
            phase_name=phase_name,
            working_dir=working_dir,
            metadata_manager=metadata_manager,
            claude_client=claude_client
        )

        # CommentClientを生成（環境変数から自動取得）
        from core.github.comment_client import CommentClient
        import os
        comment_client = CommentClient(
            token=os.getenv('GITHUB_TOKEN'),
            repository=os.getenv('GITHUB_REPOSITORY')
        )

        # Validator, Reporter生成
        validator = PhaseValidator(metadata_manager)
        reporter = PhaseReporter(issue_client, comment_client, metadata_manager)

        return cls(
            phase=phase_instance,
            metadata_manager=metadata_manager,
            issue_client=issue_client,
            git_commit=git_commit,
            validator=validator,
            reporter=reporter,
            skip_dependency_check=skip_dependency_check,
            ignore_dependencies=ignore_dependencies
        )

    def run(self) -> Dict[str, Any]:
        """フェーズを実行してレビュー（リトライ機能付き）

        処理フロー:
            1. 依存関係チェック
            2. フェーズ開始（メタデータ更新、進捗報告）
            3. リトライループ（最大3回）:
               - execute() または revise() 実行
               - review() 実行
               - レビュー結果を投稿
               - PASS/PASS_WITH_SUGGESTIONS なら成功
               - FAILなら次回リトライ
            4. 成功/失敗に応じてメタデータ更新、Git commit & push

        Returns:
            Dict[str, Any]: 実行結果
                - success: bool - 実行が成功したかどうか
                - review_result: Optional[str] - レビュー判定（PASS/PASS_WITH_SUGGESTIONS/FAIL）
                - error: Optional[str] - エラーメッセージ（失敗時）
        """
        # 依存関係チェック
        if not self.skip_dependency_check:
            validation_result = self.validator.validate_dependencies(
                phase_name=self.phase.phase_name,
                ignore_violations=self.ignore_dependencies
            )

            if not validation_result['valid']:
                self.logger.error(f"Dependency check failed: {validation_result['error']}")
                return {
                    'success': False,
                    'review_result': None,
                    'error': validation_result['error']
                }

        # フェーズ開始
        self.metadata.update_phase_status(
            phase_name=self.phase.phase_name,
            status='in_progress'
        )
        self.reporter.post_progress(
            phase_name=self.phase.phase_name,
            status='in_progress',
            details=f'{self.phase.phase_name}フェーズを開始しました。'
        )

        # リトライループ
        feedback = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            self.logger.info(f"Attempt {attempt}/{self.MAX_RETRIES}: {self.phase.phase_name}")

            # 実行
            if attempt == 1:
                result = self.phase.execute()
            else:
                # 2回目以降はrevise()（存在する場合）
                if hasattr(self.phase, 'revise'):
                    result = self.phase.revise(review_feedback=feedback)
                else:
                    # revise()がない場合は再度execute()
                    result = self.phase.execute()

            if not result.get('success', False):
                self.logger.error(f"Phase execution failed: {result.get('error')}")
                # 実行失敗時は次のリトライへ
                continue

            # レビュー
            review_result = self.phase.review()
            result_str = review_result.get('result', 'FAIL')
            feedback = review_result.get('feedback')

            # レビュー結果を投稿
            self.reporter.post_review(
                phase_name=self.phase.phase_name,
                result=result_str,
                feedback=feedback,
                suggestions=review_result.get('suggestions', [])
            )

            if result_str in ['PASS', 'PASS_WITH_SUGGESTIONS']:
                # 成功
                self.metadata.update_phase_status(
                    phase_name=self.phase.phase_name,
                    status='completed',
                    review_result=result_str
                )
                self.reporter.post_progress(
                    phase_name=self.phase.phase_name,
                    status='completed',
                    details=f'{self.phase.phase_name}フェーズが完了しました。'
                )

                # Git commit & push
                self._auto_commit_and_push(status='completed', review_result=result_str)

                return {
                    'success': True,
                    'review_result': result_str,
                    'error': None
                }

            # FAIL の場合は次のリトライへ
            self.logger.warning(
                f"Review result: {result_str}. "
                f"Retrying ({attempt}/{self.MAX_RETRIES})..."
            )

        # 最大リトライ到達
        self.metadata.update_phase_status(
            phase_name=self.phase.phase_name,
            status='failed'
        )
        self.reporter.post_progress(
            phase_name=self.phase.phase_name,
            status='failed',
            details=f'最大リトライ回数({self.MAX_RETRIES})に到達しました'
        )

        # Git commit & push（失敗時も実行）
        self._auto_commit_and_push(status='failed', review_result='FAIL')

        return {
            'success': False,
            'review_result': 'FAIL',
            'error': 'Max retries reached'
        }

    def _auto_commit_and_push(
        self,
        status: str,
        review_result: Optional[str]
    ):
        """Git自動commit & push

        Args:
            status: フェーズステータス（completed, failed）
            review_result: レビュー結果（PASS, PASS_WITH_SUGGESTIONS, FAIL）
        """
        try:
            # Commit
            issue_number = int(self.metadata.data['issue_number'])
            commit_result = self.git_commit.commit_phase_output(
                phase_name=self.phase.phase_name,
                issue_number=issue_number,
                status=status,
                review_result=review_result
            )

            if not commit_result.get('success'):
                self.logger.warning(f"Git commit failed: {commit_result.get('error')}")
                return

            # Push
            push_result = self.git_commit.push_to_remote()

            if not push_result.get('success'):
                self.logger.error(f"Git push failed: {push_result.get('error')}")
            else:
                self.logger.info("Git commit & push successful")

        except Exception as e:
            self.logger.error(f"Git auto-commit & push failed: {e}")
