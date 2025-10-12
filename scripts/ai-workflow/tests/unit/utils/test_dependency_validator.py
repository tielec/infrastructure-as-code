"""Unit tests for dependency_validator.py

Tests cover:
- PHASE_DEPENDENCIES definition validation
- DependencyError exception behavior
- validate_phase_dependencies() function logic
- Utility functions (get_phase_dependencies, get_all_phase_dependencies)

Test Strategy: UNIT_INTEGRATION (Unit portion)
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from utils.dependency_validator import (
    PHASE_DEPENDENCIES,
    DependencyError,
    validate_phase_dependencies,
    get_phase_dependencies,
    get_all_phase_dependencies
)
from core.metadata_manager import MetadataManager
from core.workflow_state import WorkflowState


class TestPhaseDependenciesDefinition:
    """PHASE_DEPENDENCIES 定数の構造検証

    TC-U-001 ~ TC-U-005 に対応
    """

    def test_phase_dependencies_structure(self):
        """TC-U-001: PHASE_DEPENDENCIES 構造検証

        Given: PHASE_DEPENDENCIES 定数が存在する
        When: 構造を確認する
        Then: dict型で、すべてのフェーズ名がキーとして存在し、値がlist型である
        """
        # Assert structure
        assert isinstance(PHASE_DEPENDENCIES, dict)

        # Assert all expected phases exist
        expected_phases = [
            'planning', 'requirements', 'design', 'test_scenario',
            'implementation', 'test_implementation', 'testing',
            'documentation', 'report', 'evaluation'
        ]
        for phase in expected_phases:
            assert phase in PHASE_DEPENDENCIES, f"Phase '{phase}' not found"
            assert isinstance(PHASE_DEPENDENCIES[phase], list), \
                f"Phase '{phase}' dependencies must be a list"

    def test_requirements_has_no_dependencies(self):
        """TC-U-002: requirements フェーズの依存関係検証

        Given: PHASE_DEPENDENCIES が定義されている
        When: requirements フェーズの依存関係を確認する
        Then: 空リスト [] である
        """
        assert PHASE_DEPENDENCIES['requirements'] == []

    def test_design_depends_on_requirements(self):
        """TC-U-003: design フェーズの依存関係検証

        Given: PHASE_DEPENDENCIES が定義されている
        When: design フェーズの依存関係を確認する
        Then: ['requirements'] である
        """
        assert PHASE_DEPENDENCIES['design'] == ['requirements']

    def test_implementation_depends_on_requirements_design_test_scenario(self):
        """TC-U-004: implementation フェーズの依存関係検証

        Given: PHASE_DEPENDENCIES が定義されている
        When: implementation フェーズの依存関係を確認する
        Then: requirements, design, test_scenario が含まれる
        """
        expected_deps = {'requirements', 'design', 'test_scenario'}
        actual_deps = set(PHASE_DEPENDENCIES['implementation'])
        assert actual_deps == expected_deps

    def test_report_phase_dependencies(self):
        """TC-U-005: report フェーズの依存関係検証

        Given: PHASE_DEPENDENCIES が定義されている
        When: report フェーズの依存関係を確認する
        Then: requirements, design, implementation, testing, documentation が含まれる
        """
        expected_deps = {'requirements', 'design', 'implementation', 'testing', 'documentation'}
        actual_deps = set(PHASE_DEPENDENCIES['report'])
        assert actual_deps == expected_deps


class TestDependencyError:
    """DependencyError カスタム例外のテスト

    TC-U-006 ~ TC-U-008 に対応
    """

    def test_dependency_error_single_phase(self):
        """TC-U-006: DependencyError - 単一フェーズ未完了

        Given: 単一フェーズの依存関係違反がある
        When: DependencyError を生成する
        Then: 適切なエラーメッセージが生成される
        """
        error = DependencyError(
            phase_name='design',
            missing_phases=['requirements']
        )

        assert error.phase_name == 'design'
        assert error.missing_phases == ['requirements']
        assert "Phase 'requirements' must be completed before 'design'" in error.message
        assert "Phase 'requirements' must be completed before 'design'" in str(error)

    def test_dependency_error_multiple_phases(self):
        """TC-U-007: DependencyError - 複数フェーズ未完了

        Given: 複数フェーズの依存関係違反がある
        When: DependencyError を生成する
        Then: 複数フェーズを含む適切なエラーメッセージが生成される
        """
        error = DependencyError(
            phase_name='implementation',
            missing_phases=['requirements', 'design']
        )

        assert error.phase_name == 'implementation'
        assert error.missing_phases == ['requirements', 'design']
        assert "Phases 'requirements', 'design' must be completed before 'implementation'" in error.message

    def test_dependency_error_custom_message(self):
        """TC-U-008: DependencyError - カスタムメッセージ

        Given: カスタムエラーメッセージを指定する
        When: DependencyError を生成する
        Then: カスタムメッセージが設定される
        """
        custom_msg = 'Custom error message'
        error = DependencyError(
            phase_name='design',
            missing_phases=['requirements'],
            message=custom_msg
        )

        assert error.message == custom_msg


class TestValidatePhaseDependencies:
    """validate_phase_dependencies() 関数のテスト

    TC-U-009 ~ TC-U-016 に対応
    """

    @pytest.fixture
    def temp_metadata(self, tmp_path):
        """テスト用のメタデータを作成"""
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/test/test/issues/319',
            issue_title='Test Issue'
        )
        return MetadataManager(metadata_path)

    def test_validate_no_dependencies_succeeds(self, temp_metadata, capsys):
        """TC-U-009: 依存関係なしのフェーズ（正常系）

        Given: requirements フェーズを実行しようとする
        When: 依存関係チェックを実行する
        Then: 検証成功し、適切なログが表示される
        """
        result = validate_phase_dependencies('requirements', temp_metadata)

        assert result is True
        captured = capsys.readouterr()
        assert "[INFO] Phase 'requirements' has no dependencies. Proceeding." in captured.out

    def test_validate_dependencies_met_succeeds(self, temp_metadata, capsys):
        """TC-U-010: 依存関係満たされている（正常系）

        Given: requirements フェーズが completed である
        When: design フェーズの依存関係チェックを実行する
        Then: 検証成功し、適切なログが表示される
        """
        temp_metadata.update_phase_status('requirements', 'completed')

        result = validate_phase_dependencies('design', temp_metadata)

        assert result is True
        captured = capsys.readouterr()
        assert "[INFO] Dependency check passed for phase 'design'." in captured.out

    def test_validate_dependencies_not_met_raises_error(self, temp_metadata):
        """TC-U-011: 依存関係違反（異常系）

        Given: requirements フェーズが pending である
        When: design フェーズの依存関係チェックを実行する
        Then: DependencyError が発生する
        """
        # requirements は pending のまま

        with pytest.raises(DependencyError) as exc_info:
            validate_phase_dependencies('design', temp_metadata)

        assert 'requirements' in str(exc_info.value)
        assert 'design' in str(exc_info.value)
        assert exc_info.value.missing_phases == ['requirements']

    def test_validate_multiple_dependencies_partial_not_met(self, temp_metadata):
        """TC-U-012: 複数依存関係の一部未完了（異常系）

        Given: requirements は completed、design は pending である
        When: test_scenario フェーズの依存関係チェックを実行する
        Then: DependencyError が発生し、design が未完了として報告される
        """
        temp_metadata.update_phase_status('requirements', 'completed')
        # design は pending のまま

        with pytest.raises(DependencyError) as exc_info:
            validate_phase_dependencies('test_scenario', temp_metadata)

        assert exc_info.value.missing_phases == ['design']

    def test_validate_skip_check_bypasses_validation(self, temp_metadata, capsys):
        """TC-U-013: skip_check フラグ有効（正常系）

        Given: requirements フェーズが pending である
        When: skip_check=True で design フェーズの依存関係チェックを実行する
        Then: 検証がスキップされ、警告が表示される
        """
        # requirements は pending のまま

        result = validate_phase_dependencies('design', temp_metadata, skip_check=True)

        assert result is True
        captured = capsys.readouterr()
        assert "[WARNING] Dependency check skipped. Proceeding without validation." in captured.out

    def test_validate_ignore_violations_shows_warning(self, temp_metadata, capsys):
        """TC-U-014: ignore_violations フラグ有効（警告モード）

        Given: requirements フェーズが pending である
        When: ignore_violations=True で design フェーズの依存関係チェックを実行する
        Then: 警告のみ表示され、検証は成功する
        """
        # requirements は pending のまま

        result = validate_phase_dependencies('design', temp_metadata, ignore_violations=True)

        assert result is True
        captured = capsys.readouterr()
        assert "[WARNING] Dependency violation: Phase 'requirements' is not completed." in captured.out
        assert "Continuing anyway." in captured.out

    def test_validate_unknown_phase_raises_value_error(self, temp_metadata):
        """TC-U-015: 未知のフェーズ名（異常系）

        Given: 存在しないフェーズ名を指定する
        When: 依存関係チェックを実行する
        Then: ValueError が発生する
        """
        with pytest.raises(ValueError) as exc_info:
            validate_phase_dependencies('unknown_phase', temp_metadata)

        assert "Unknown phase: 'unknown_phase'" in str(exc_info.value)

    def test_validate_all_dependencies_not_met(self, temp_metadata):
        """TC-U-016: 複数依存関係すべて未完了（異常系）

        Given: requirements, design, test_scenario すべてが pending である
        When: implementation フェーズの依存関係チェックを実行する
        Then: DependencyError が発生し、すべての依存フェーズが報告される
        """
        # すべて pending のまま

        with pytest.raises(DependencyError) as exc_info:
            validate_phase_dependencies('implementation', temp_metadata)

        expected_missing = {'requirements', 'design', 'test_scenario'}
        actual_missing = set(exc_info.value.missing_phases)
        assert actual_missing == expected_missing


class TestUtilityFunctions:
    """ユーティリティ関数のテスト

    TC-U-017 ~ TC-U-019 に対応
    """

    def test_get_phase_dependencies_returns_correct_list(self):
        """TC-U-017: get_phase_dependencies() - 正常系

        Given: フェーズ名を指定する
        When: get_phase_dependencies() を呼び出す
        Then: 正しい依存関係リストが返される
        """
        deps = get_phase_dependencies('design')

        assert deps == ['requirements']
        # Verify it's a copy, not the original
        assert deps is not PHASE_DEPENDENCIES['design']

    def test_get_phase_dependencies_unknown_phase_raises_error(self):
        """TC-U-018: get_phase_dependencies() - 未知のフェーズ

        Given: 存在しないフェーズ名を指定する
        When: get_phase_dependencies() を呼び出す
        Then: ValueError が発生する
        """
        with pytest.raises(ValueError) as exc_info:
            get_phase_dependencies('unknown_phase')

        assert "Unknown phase" in str(exc_info.value)

    def test_get_all_phase_dependencies_returns_full_dict(self):
        """TC-U-019: get_all_phase_dependencies() - 正常系

        Given: 何も指定しない
        When: get_all_phase_dependencies() を呼び出す
        Then: すべてのフェーズ依存関係定義が返される
        """
        all_deps = get_all_phase_dependencies()

        assert isinstance(all_deps, dict)
        assert 'requirements' in all_deps
        assert 'design' in all_deps
        assert 'implementation' in all_deps
        # Verify it's a copy, not the original
        assert all_deps is not PHASE_DEPENDENCIES


class TestValidatePhaseDependenciesIgnoreViolationsMultiple:
    """ignore_violations フラグでの複数フェーズ違反のテスト"""

    @pytest.fixture
    def temp_metadata(self, tmp_path):
        """テスト用のメタデータを作成"""
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/test/test/issues/319',
            issue_title='Test Issue'
        )
        return MetadataManager(metadata_path)

    def test_ignore_violations_multiple_phases(self, temp_metadata, capsys):
        """複数フェーズ違反時の ignore_violations 動作

        Given: requirements, design が pending である
        When: ignore_violations=True で implementation フェーズの依存関係チェックを実行する
        Then: 複数フェーズの警告が表示され、検証は成功する
        """
        # test_scenario は completed に設定
        temp_metadata.update_phase_status('test_scenario', 'completed')
        # requirements, design は pending のまま

        result = validate_phase_dependencies('implementation', temp_metadata, ignore_violations=True)

        assert result is True
        captured = capsys.readouterr()
        assert "[WARNING] Dependency violation:" in captured.out
        assert "are not completed" in captured.out
        assert "Continuing anyway." in captured.out
