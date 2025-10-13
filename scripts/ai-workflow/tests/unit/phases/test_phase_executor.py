"""
Unit tests for phases/base/phase_executor.py

Test Scenarios:
- UT-PE-001: PhaseExecutor.run() - 1回目でPASS
- UT-PE-002: PhaseExecutor.run() - リトライ後PASS
- UT-PE-003: PhaseExecutor.run() - 最大リトライ到達
- UT-PE-004: PhaseExecutor.run() - 依存関係チェック失敗
- UT-PE-005: PhaseExecutor._auto_commit_and_push() - 正常系
"""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from phases.base.phase_executor import PhaseExecutor


class TestPhaseExecutor:
    """PhaseExecutor クラスのユニットテスト"""

    def test_run_succeeds_on_first_pass(self):
        """UT-PE-001: 1回目の実行でPASSした場合に正常終了することを確認"""
        # Given: フェーズが初期化済み、1回目でPASS
        mock_phase = Mock()
        mock_phase.phase_name = 'planning'
        mock_phase.execute.return_value = {'success': True, 'output': 'planning.md'}
        mock_phase.review.return_value = {
            'result': 'PASS',
            'feedback': 'Good work',
            'suggestions': []
        }

        mock_metadata = Mock()
        mock_issue_client = Mock()
        mock_git_commit = Mock()
        mock_validator = Mock()
        mock_validator.validate_dependencies.return_value = {'valid': True, 'error': None}
        mock_reporter = Mock()

        executor = PhaseExecutor(
            phase=mock_phase,
            metadata_manager=mock_metadata,
            issue_client=mock_issue_client,
            git_commit=mock_git_commit,
            validator=mock_validator,
            reporter=mock_reporter
        )

        # When: run()を実行
        result = executor.run()

        # Then: 成功が返され、execute()とreview()が1回ずつ呼ばれる
        assert result['success'] is True
        assert result['review_result'] == 'PASS'
        assert result['error'] is None

        mock_phase.execute.assert_called_once()
        mock_phase.review.assert_called_once()
        mock_metadata.update_phase_status.assert_called()
        mock_reporter.post_progress.assert_called()
        mock_reporter.post_review.assert_called()

    def test_run_succeeds_after_retry(self):
        """UT-PE-002: 1回目がFAIL、2回目でPASSした場合に正常終了することを確認"""
        # Given: 1回目はFAIL、2回目はPASS
        mock_phase = Mock()
        mock_phase.phase_name = 'planning'
        mock_phase.execute.return_value = {'success': True, 'output': 'planning.md'}
        mock_phase.revise.return_value = {'success': True, 'output': 'planning.md'}

        # 1回目はFAIL、2回目はPASS
        mock_phase.review.side_effect = [
            {'result': 'FAIL', 'feedback': 'Needs improvement', 'suggestions': []},
            {'result': 'PASS', 'feedback': 'Good work', 'suggestions': []}
        ]

        mock_metadata = Mock()
        mock_issue_client = Mock()
        mock_git_commit = Mock()
        mock_validator = Mock()
        mock_validator.validate_dependencies.return_value = {'valid': True, 'error': None}
        mock_reporter = Mock()

        executor = PhaseExecutor(
            phase=mock_phase,
            metadata_manager=mock_metadata,
            issue_client=mock_issue_client,
            git_commit=mock_git_commit,
            validator=mock_validator,
            reporter=mock_reporter
        )

        # When: run()を実行
        result = executor.run()

        # Then: 成功が返され、execute()が1回、revise()が1回呼ばれる
        assert result['success'] is True
        assert result['review_result'] == 'PASS'
        assert result['error'] is None

        mock_phase.execute.assert_called_once()
        mock_phase.revise.assert_called_once()
        assert mock_phase.review.call_count == 2

    def test_run_fails_after_max_retries(self):
        """UT-PE-003: 最大リトライ回数に到達した場合に失敗することを確認"""
        # Given: 常にFAILを返すフェーズ
        mock_phase = Mock()
        mock_phase.phase_name = 'planning'
        mock_phase.execute.return_value = {'success': True, 'output': 'planning.md'}
        mock_phase.revise.return_value = {'success': True, 'output': 'planning.md'}
        mock_phase.review.return_value = {
            'result': 'FAIL',
            'feedback': 'Quality gates not met',
            'suggestions': []
        }

        mock_metadata = Mock()
        mock_issue_client = Mock()
        mock_git_commit = Mock()
        mock_validator = Mock()
        mock_validator.validate_dependencies.return_value = {'valid': True, 'error': None}
        mock_reporter = Mock()

        executor = PhaseExecutor(
            phase=mock_phase,
            metadata_manager=mock_metadata,
            issue_client=mock_issue_client,
            git_commit=mock_git_commit,
            validator=mock_validator,
            reporter=mock_reporter
        )

        # When: run()を実行
        result = executor.run()

        # Then: 失敗が返され、3回試行される
        assert result['success'] is False
        assert result['review_result'] == 'FAIL'
        assert result['error'] == 'Max retries reached'

        mock_phase.execute.assert_called_once()
        assert mock_phase.revise.call_count == 2  # 2回目と3回目でrevise()
        assert mock_phase.review.call_count == 3  # 3回全てでreview()

    def test_run_fails_dependency_check(self):
        """UT-PE-004: 依存関係チェックが失敗した場合に実行されないことを確認"""
        # Given: 依存関係チェックが失敗
        mock_phase = Mock()
        mock_phase.phase_name = 'requirements'

        mock_metadata = Mock()
        mock_issue_client = Mock()
        mock_git_commit = Mock()
        mock_validator = Mock()
        mock_validator.validate_dependencies.return_value = {
            'valid': False,
            'error': 'Dependency check failed: Phase planning not completed'
        }
        mock_reporter = Mock()

        executor = PhaseExecutor(
            phase=mock_phase,
            metadata_manager=mock_metadata,
            issue_client=mock_issue_client,
            git_commit=mock_git_commit,
            validator=mock_validator,
            reporter=mock_reporter,
            skip_dependency_check=False
        )

        # When: run()を実行
        result = executor.run()

        # Then: 失敗が返され、execute()は呼ばれない
        assert result['success'] is False
        assert result['review_result'] is None
        assert 'Dependency check failed' in result['error']

        mock_phase.execute.assert_not_called()
        mock_phase.review.assert_not_called()

    def test_auto_commit_and_push_succeeds(self):
        """UT-PE-005: Git自動commit & pushが正常に動作することを確認"""
        # Given: Git操作が成功するモック
        mock_phase = Mock()
        mock_phase.phase_name = 'planning'

        mock_metadata = Mock()
        mock_metadata.data = {'issue_number': 376}

        mock_git_commit = Mock()
        mock_git_commit.commit_phase_output.return_value = {
            'success': True,
            'commit_hash': '1a2b3c4',
            'files_committed': ['.ai-workflow/issue-376/00_planning/output/planning.md'],
            'error': None
        }
        mock_git_commit.push_to_remote.return_value = {
            'success': True,
            'retries': 0,
            'error': None
        }

        mock_issue_client = Mock()
        mock_validator = Mock()
        mock_reporter = Mock()

        executor = PhaseExecutor(
            phase=mock_phase,
            metadata_manager=mock_metadata,
            issue_client=mock_issue_client,
            git_commit=mock_git_commit,
            validator=mock_validator,
            reporter=mock_reporter
        )

        # When: _auto_commit_and_push()を実行
        executor._auto_commit_and_push(status='completed', review_result='PASS')

        # Then: commit()とpush()が呼ばれる
        mock_git_commit.commit_phase_output.assert_called_once_with(
            phase_name='planning',
            issue_number=376,
            status='completed',
            review_result='PASS'
        )
        mock_git_commit.push_to_remote.assert_called_once()

    def test_run_skips_dependency_check_when_flag_set(self):
        """skip_dependency_check=Trueの場合、依存関係チェックがスキップされることを確認"""
        # Given: skip_dependency_check=True
        mock_phase = Mock()
        mock_phase.phase_name = 'requirements'
        mock_phase.execute.return_value = {'success': True, 'output': 'requirements.md'}
        mock_phase.review.return_value = {
            'result': 'PASS',
            'feedback': 'Good',
            'suggestions': []
        }

        mock_metadata = Mock()
        mock_issue_client = Mock()
        mock_git_commit = Mock()
        mock_validator = Mock()
        mock_reporter = Mock()

        executor = PhaseExecutor(
            phase=mock_phase,
            metadata_manager=mock_metadata,
            issue_client=mock_issue_client,
            git_commit=mock_git_commit,
            validator=mock_validator,
            reporter=mock_reporter,
            skip_dependency_check=True  # スキップフラグ
        )

        # When: run()を実行
        result = executor.run()

        # Then: 成功し、validate_dependencies()は呼ばれない
        assert result['success'] is True
        mock_validator.validate_dependencies.assert_not_called()
        mock_phase.execute.assert_called_once()


class TestPhaseExecutorCreate:
    """PhaseExecutor.create() ファクトリーメソッドのテスト"""

    @patch('phases.base.phase_executor.importlib.import_module')
    def test_create_imports_phase_class_correctly(self, mock_import):
        """create()がフェーズクラスを正しくインポートすることを確認"""
        # Given: モックされたフェーズクラス
        mock_module = Mock()
        mock_phase_class = Mock()
        mock_module.PlanningPhase = mock_phase_class
        mock_import.return_value = mock_module

        mock_phase_instance = Mock()
        mock_phase_instance.phase_name = 'planning'
        mock_phase_class.return_value = mock_phase_instance

        mock_metadata = Mock()
        mock_claude = Mock()

        # IssueClientのモック（github属性とrepository属性を持つ）
        mock_issue_client = Mock()
        mock_issue_client.github = Mock()
        mock_issue_client.repository.full_name = 'tielec/infrastructure-as-code'

        mock_git_commit = Mock()

        # When: create()を呼び出し
        executor = PhaseExecutor.create(
            phase_name='planning',
            working_dir=Path('/tmp/repo'),
            metadata_manager=mock_metadata,
            claude_client=mock_claude,
            issue_client=mock_issue_client,
            git_commit=mock_git_commit
        )

        # Then: 正しくインポートされる
        mock_import.assert_called_once_with('phases.planning')
        assert isinstance(executor, PhaseExecutor)
        assert executor.phase == mock_phase_instance

    def test_create_raises_error_for_unknown_phase(self):
        """create()が未知のフェーズ名でエラーを発生させることを確認"""
        # Given: 無効なフェーズ名
        mock_metadata = Mock()
        mock_claude = Mock()
        mock_issue_client = Mock()
        mock_git_commit = Mock()

        # When/Then: ValueErrorが発生
        with pytest.raises(ValueError, match="Unknown phase"):
            PhaseExecutor.create(
                phase_name='invalid_phase',
                working_dir=Path('/tmp/repo'),
                metadata_manager=mock_metadata,
                claude_client=mock_claude,
                issue_client=mock_issue_client,
                git_commit=mock_git_commit
            )
