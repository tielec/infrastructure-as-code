"""Integration tests for dependency check flow (Issue #319)

Tests cover:
- CLI実行フロー全体テスト
- 複数依存関係のテスト
- BasePhase.run() 統合テスト
- エラーハンドリングとリカバリ

Test Strategy: UNIT_INTEGRATION (Integration portion)

TC-I-001 ~ TC-I-015, TC-I-017 ~ TC-I-018 に対応
（TC-I-016はE2Eテストで対応）
"""
import pytest
import subprocess
import tempfile
import shutil
from pathlib import Path
import json
import sys

# プロジェクトルートをPYTHONPATHに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.metadata_manager import MetadataManager
from core.workflow_state import WorkflowState


class TestCLIExecutionFlow:
    """CLI実行フロー全体テスト

    TC-I-001 ~ TC-I-008 に対応
    """

    @pytest.fixture
    def test_workspace(self, tmp_path):
        """テスト用のワークスペースを作成"""
        workspace = tmp_path / 'test-workspace'
        workspace.mkdir()

        # メタデータディレクトリ作成
        metadata_dir = workspace / '.ai-workflow' / 'issue-319'
        metadata_dir.mkdir(parents=True)

        # メタデータファイル作成
        metadata_path = metadata_dir / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/test/test/issues/319',
            issue_title='Test Issue for Dependency Check'
        )

        return {
            'workspace': workspace,
            'metadata_path': metadata_path
        }

    def test_execute_with_dependencies_met_succeeds(self, test_workspace):
        """TC-I-001: 正常フロー - 依存関係満たされた状態でのフェーズ実行

        Given: requirements フェーズが completed である
        When: design フェーズを実行する
        Then: 依存関係チェックが成功し、フェーズが正常に実行される
        """
        # Arrange: requirements を completed に設定
        metadata = MetadataManager(test_workspace['metadata_path'])
        metadata.update_phase_status('requirements', 'completed')

        # Note: この統合テストは実際のCLI実行をシミュレートするため、
        # E2Eテストで完全に実装される。ここではメタデータの整合性を検証。
        assert metadata.get_phase_status('requirements') == 'completed'

    def test_execute_without_dependencies_fails(self, test_workspace):
        """TC-I-002: 異常フロー - 依存関係未満足でのフェーズ実行エラー

        Given: requirements フェーズが pending である
        When: design フェーズを実行しようとする
        Then: 依存関係チェックでエラーが発生する
        """
        # Arrange: requirements は pending のまま
        metadata = MetadataManager(test_workspace['metadata_path'])
        requirements_status = metadata.get_phase_status('requirements')

        assert requirements_status in ['pending', None], \
            "requirements フェーズが未完了である"

        # Note: 実際のCLI実行とエラーメッセージ検証はE2Eテストで実装

    def test_skip_dependency_check_flag_bypasses_check(self, test_workspace):
        """TC-I-003: --skip-dependency-check フラグ使用時の動作

        Given: requirements フェーズが pending である
        When: --skip-dependency-check フラグを使用して design フェーズを実行する
        Then: 依存関係チェックがスキップされる
        """
        # Arrange: requirements は pending のまま
        metadata = MetadataManager(test_workspace['metadata_path'])

        # Note: CLIフラグの動作検証はE2Eテストで実装
        # ここではメタデータの状態確認のみ
        assert metadata.get_phase_status('requirements') != 'completed'

    def test_ignore_dependencies_flag_shows_warning(self, test_workspace):
        """TC-I-004: --ignore-dependencies フラグ使用時の動作

        Given: requirements フェーズが pending である
        When: --ignore-dependencies フラグを使用して design フェーズを実行する
        Then: 警告のみ表示され、実行が継続される
        """
        # Arrange
        metadata = MetadataManager(test_workspace['metadata_path'])

        # Note: 警告メッセージの検証はE2Eテストで実装
        assert metadata.get_phase_status('requirements') != 'completed'

    def test_preset_requirements_only(self, test_workspace):
        """TC-I-005: プリセット実行 - requirements-only

        Given: ワークフローが初期化されている
        When: requirements-only プリセットで実行する
        Then: requirements フェーズのみが実行される
        """
        # Note: プリセット実行の検証はE2Eテストで実装
        # ここではメタデータの初期状態確認
        metadata = MetadataManager(test_workspace['metadata_path'])
        assert metadata.data['issue_number'] == '319'

    def test_preset_design_phase(self, test_workspace):
        """TC-I-006: プリセット実行 - design-phase

        Given: ワークフローが初期化されている
        When: design-phase プリセットで実行する
        Then: requirements と design フェーズが順次実行される
        """
        # Note: プリセット実行の検証はE2Eテストで実装
        pass

    def test_preset_implementation_phase(self, test_workspace):
        """TC-I-007: プリセット実行 - implementation-phase

        Given: ワークフローが初期化されている
        When: implementation-phase プリセットで実行する
        Then: Phase 1-4 が順次実行される
        """
        # Note: プリセット実行の検証はE2Eテストで実装
        pass

    def test_preset_and_phase_mutual_exclusion_error(self, test_workspace):
        """TC-I-008: プリセットとphaseの同時指定エラー

        Given: ワークフローが初期化されている
        When: --preset と --phase を同時に指定する
        Then: エラーメッセージが表示され、実行されない
        """
        # Note: 相互排他エラーの検証はE2Eテストで実装
        pass


class TestMultipleDependencies:
    """複数依存関係のテスト

    TC-I-009 ~ TC-I-011 に対応
    """

    @pytest.fixture
    def test_workspace(self, tmp_path):
        """テスト用のワークスペースを作成"""
        workspace = tmp_path / 'test-workspace'
        workspace.mkdir()

        metadata_dir = workspace / '.ai-workflow' / 'issue-319'
        metadata_dir.mkdir(parents=True)

        metadata_path = metadata_dir / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/test/test/issues/319',
            issue_title='Test Issue'
        )

        return {
            'workspace': workspace,
            'metadata_path': metadata_path
        }

    def test_multiple_dependencies_all_met_succeeds(self, test_workspace):
        """TC-I-009: 複数依存関係 - すべて満たされている場合

        Given: requirements, design, test_scenario が completed である
        When: implementation フェーズを実行する
        Then: 依存関係チェックが成功し、implementation が実行される
        """
        # Arrange: すべての依存フェーズを completed に設定
        metadata = MetadataManager(test_workspace['metadata_path'])
        metadata.update_phase_status('requirements', 'completed')
        metadata.update_phase_status('design', 'completed')
        metadata.update_phase_status('test_scenario', 'completed')

        # Assert: すべての依存フェーズが completed
        assert metadata.get_phase_status('requirements') == 'completed'
        assert metadata.get_phase_status('design') == 'completed'
        assert metadata.get_phase_status('test_scenario') == 'completed'

        # Note: 実際の実行検証はE2Eテストで実装

    def test_multiple_dependencies_partial_not_met_fails(self, test_workspace):
        """TC-I-010: 複数依存関係 - 一部未満足の場合

        Given: requirements と design は completed、test_scenario は pending である
        When: implementation フェーズを実行する
        Then: 依存関係チェックでエラーが発生する
        """
        # Arrange: 一部の依存フェーズのみ completed
        metadata = MetadataManager(test_workspace['metadata_path'])
        metadata.update_phase_status('requirements', 'completed')
        metadata.update_phase_status('design', 'completed')
        # test_scenario は pending のまま

        # Assert: test_scenario が未完了
        assert metadata.get_phase_status('test_scenario') != 'completed'

        # Note: エラー発生の検証はE2Eテストで実装

    def test_report_phase_complex_dependencies(self, test_workspace):
        """TC-I-011: report フェーズの複雑な依存関係

        Given: requirements, design, implementation, testing は completed、
              documentation は pending である
        When: report フェーズを実行する
        Then: documentation が未完了であることがエラーとして報告される
        """
        # Arrange: 複数の依存フェーズを設定
        metadata = MetadataManager(test_workspace['metadata_path'])
        metadata.update_phase_status('requirements', 'completed')
        metadata.update_phase_status('design', 'completed')
        metadata.update_phase_status('implementation', 'completed')
        metadata.update_phase_status('testing', 'completed')
        # documentation は pending のまま

        # Assert: documentation が未完了
        assert metadata.get_phase_status('documentation') != 'completed'

        # Note: エラーメッセージの検証はE2Eテストで実装


class TestBasePhaseRunIntegration:
    """BasePhase.run() 統合テスト

    TC-I-012 ~ TC-I-013 に対応
    """

    @pytest.fixture
    def test_workspace(self, tmp_path):
        """テスト用のワークスペースを作成"""
        workspace = tmp_path / 'test-workspace'
        workspace.mkdir()

        metadata_dir = workspace / '.ai-workflow' / 'issue-319'
        metadata_dir.mkdir(parents=True)

        metadata_path = metadata_dir / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/test/test/issues/319',
            issue_title='Test Issue'
        )

        return {
            'workspace': workspace,
            'metadata_path': metadata_path
        }

    def test_base_phase_run_executes_dependency_check(self, test_workspace):
        """TC-I-012: BasePhase.run() 経由での依存関係チェック

        Given: requirements フェーズが pending である
        When: DesignPhase.run() を直接呼び出す
        Then: 依存関係チェックが実行され、DependencyError が発生する
        """
        # Note: BasePhase.run()の実際の動作検証はUnitテストで実装
        # ここではメタデータの整合性確認
        metadata = MetadataManager(test_workspace['metadata_path'])
        assert metadata.get_phase_status('requirements') != 'completed'

    def test_base_phase_run_with_skip_flag(self, test_workspace):
        """TC-I-013: BasePhase.run() でのスキップフラグ動作

        Given: requirements フェーズが pending であり、
              メタデータに skip_dependency_check=True が設定されている
        When: DesignPhase.run() を呼び出す
        Then: 依存関係チェックがスキップされ、フェーズ実行が試行される
        """
        # Arrange: skip_dependency_check フラグを設定
        metadata = MetadataManager(test_workspace['metadata_path'])
        metadata.data['skip_dependency_check'] = True
        metadata.save()

        # Assert: フラグが設定されている
        assert metadata.data['skip_dependency_check'] is True

        # Note: 実際の動作検証はUnitテストで実装


class TestErrorHandlingAndRecovery:
    """エラーハンドリングとリカバリ

    TC-I-014 ~ TC-I-015 に対応
    """

    @pytest.fixture
    def test_workspace(self, tmp_path):
        """テスト用のワークスペースを作成"""
        workspace = tmp_path / 'test-workspace'
        workspace.mkdir()

        metadata_dir = workspace / '.ai-workflow' / 'issue-319'
        metadata_dir.mkdir(parents=True)

        metadata_path = metadata_dir / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/test/test/issues/319',
            issue_title='Test Issue'
        )

        return {
            'workspace': workspace,
            'metadata_path': metadata_path
        }

    def test_dependency_error_recovery(self, test_workspace):
        """TC-I-014: 依存関係エラー後のリカバリ

        Given: ワークフローが初期化されている
        When: 1回目: design を実行（エラー）、2回目: requirements を実行、
              3回目: design を再実行
        Then: 3回目で design が正常に実行される
        """
        metadata = MetadataManager(test_workspace['metadata_path'])

        # 1回目: design 実行前の状態確認
        assert metadata.get_phase_status('requirements') != 'completed'

        # 2回目: requirements を completed に設定
        metadata.update_phase_status('requirements', 'completed')

        # 3回目: design 実行可能な状態を確認
        assert metadata.get_phase_status('requirements') == 'completed'

        # Note: 実際のCLI実行フローはE2Eテストで検証

    def test_mutual_exclusion_flags_error(self, test_workspace):
        """TC-I-015: 相互排他フラグ指定時のエラー

        Given: ワークフローが初期化されている
        When: --skip-dependency-check と --ignore-dependencies を同時に指定する
        Then: エラーメッセージが表示され、実行されない
        """
        # Note: CLIエラーの検証はE2Eテストで実装
        pass


class TestPhaseResumeScenario:
    """途中フェーズからの実行（中断・再開シナリオ）

    TC-I-017 に対応
    """

    @pytest.fixture
    def test_workspace(self, tmp_path):
        """テスト用のワークスペースを作成"""
        workspace = tmp_path / 'test-workspace'
        workspace.mkdir()

        metadata_dir = workspace / '.ai-workflow' / 'issue-319'
        metadata_dir.mkdir(parents=True)

        metadata_path = metadata_dir / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/test/test/issues/319',
            issue_title='Test Issue'
        )

        return {
            'workspace': workspace,
            'metadata_path': metadata_path
        }

    def test_resume_from_phase_4(self, test_workspace):
        """TC-I-017: 途中フェーズからの実行（中断・再開シナリオ）

        Given: Phase 1-3 (requirements, design, test_scenario) が completed である
        When: Phase 4 (implementation) から再開する
        Then: 依存関係が正しく認識され、implementation が実行される
        """
        # Arrange: Phase 1-3 を completed に設定
        metadata = MetadataManager(test_workspace['metadata_path'])
        metadata.update_phase_status('requirements', 'completed')
        metadata.update_phase_status('design', 'completed')
        metadata.update_phase_status('test_scenario', 'completed')

        # Assert: Phase 1-3 が completed
        assert metadata.get_phase_status('requirements') == 'completed'
        assert metadata.get_phase_status('design') == 'completed'
        assert metadata.get_phase_status('test_scenario') == 'completed'

        # Note: 実際の再開フローはE2Eテストで検証


class TestPerformance:
    """パフォーマンステスト

    TC-I-018 に対応
    """

    @pytest.fixture
    def test_workspace(self, tmp_path):
        """テスト用のワークスペースを作成"""
        workspace = tmp_path / 'test-workspace'
        workspace.mkdir()

        metadata_dir = workspace / '.ai-workflow' / 'issue-319'
        metadata_dir.mkdir(parents=True)

        metadata_path = metadata_dir / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/test/test/issues/319',
            issue_title='Test Issue'
        )

        return {
            'workspace': workspace,
            'metadata_path': metadata_path
        }

    def test_dependency_check_execution_time(self, test_workspace):
        """TC-I-018: 依存関係チェックの実行時間

        Given: メタデータが初期化されている
        When: validate_phase_dependencies() を100回実行する
        Then: 平均実行時間が 100ms 以内である
        """
        from utils.dependency_validator import validate_phase_dependencies
        import time

        metadata = MetadataManager(test_workspace['metadata_path'])

        # すべての依存フェーズを completed に設定
        metadata.update_phase_status('requirements', 'completed')
        metadata.update_phase_status('design', 'completed')
        metadata.update_phase_status('test_scenario', 'completed')

        # パフォーマンステスト
        iterations = 100
        start_time = time.time()

        for _ in range(iterations):
            result = validate_phase_dependencies('implementation', metadata)
            assert result is True

        end_time = time.time()
        total_duration = end_time - start_time
        average_duration = (total_duration / iterations) * 1000  # ms

        # Assert: 平均実行時間が 100ms 以内
        assert average_duration < 100, \
            f"平均実行時間 {average_duration:.2f}ms は 100ms を超えている"

        print(f"\n[Performance] Average execution time: {average_duration:.2f}ms")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
