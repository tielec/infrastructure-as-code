"""
Unit tests for phases/base/phase_validator.py

Test Scenarios:
- UT-PV-001: PhaseValidator.validate_dependencies() - 依存満たす
- UT-PV-002: PhaseValidator.validate_dependencies() - 依存未満足
- UT-PV-003: PhaseValidator.validate_dependencies() - 違反を無視
- UT-PV-004: PhaseValidator._parse_review_result() - PASS
"""
import pytest
from unittest.mock import Mock
from phases.base.phase_validator import PhaseValidator


class TestPhaseValidator:
    """PhaseValidator クラスのユニットテスト"""

    def test_validate_dependencies_succeeds_when_dependencies_met(self):
        """UT-PV-001: 依存関係が満たされている場合にTrueが返されることを確認"""
        # Given: 依存フェーズが全てcompletedのメタデータマネージャー
        mock_metadata = Mock()
        mock_metadata.get_phase_status.side_effect = lambda phase: {
            'planning': 'completed',
            'requirements': 'pending'
        }.get(phase, 'pending')

        validator = PhaseValidator(mock_metadata)

        # When: requirementsフェーズの依存関係を検証（planningに依存）
        result = validator.validate_dependencies(
            phase_name='requirements',
            ignore_violations=False
        )

        # Then: 依存関係が満たされている
        assert result['valid'] is True
        assert result['error'] is None

    def test_validate_dependencies_fails_when_dependencies_not_met(self):
        """UT-PV-002: 依存関係が満たされていない場合にFalseが返されることを確認"""
        # Given: 依存フェーズが未完了のメタデータマネージャー
        mock_metadata = Mock()
        mock_metadata.get_phase_status.side_effect = lambda phase: {
            'planning': 'pending',  # 未完了
            'requirements': 'pending',
            'design': 'pending'
        }.get(phase, 'pending')

        validator = PhaseValidator(mock_metadata)

        # When: designフェーズの依存関係を検証（requirementsに依存、planningは間接依存）
        result = validator.validate_dependencies(
            phase_name='design',
            ignore_violations=False
        )

        # Then: 依存関係が満たされていない
        assert result['valid'] is False
        assert result['error'] is not None
        assert 'Phase requirements not completed' in result['error']

    def test_validate_dependencies_ignores_violations_when_flag_set(self):
        """UT-PV-003: ignore_violations=Trueの場合に警告のみで通過することを確認"""
        # Given: 依存フェーズが未完了のメタデータマネージャー
        mock_metadata = Mock()
        mock_metadata.get_phase_status.side_effect = lambda phase: 'pending'

        validator = PhaseValidator(mock_metadata)

        # When: ignore_violations=Trueで依存関係を検証
        result = validator.validate_dependencies(
            phase_name='design',
            ignore_violations=True
        )

        # Then: 警告のみで通過
        assert result['valid'] is True
        assert result['error'] is None

    def test_parse_review_result_parses_pass_correctly(self):
        """UT-PV-004: レビュー結果が正しくパースされることを確認"""
        # Given: PASSレビュー結果のメッセージ
        mock_metadata = Mock()
        validator = PhaseValidator(mock_metadata)

        messages = [
            "Result: PASS",
            "Feedback: Good work",
            "The implementation meets all requirements."
        ]

        # When: レビュー結果をパース
        result = validator.parse_review_result(messages)

        # Then: 正しくパースされる
        assert result['result'] == 'PASS'
        assert 'Good work' in result['feedback']
        assert isinstance(result['suggestions'], list)

    def test_planning_phase_has_no_dependencies(self):
        """planningフェーズが依存関係なしで検証を通過することを確認"""
        # Given: メタデータマネージャー
        mock_metadata = Mock()

        validator = PhaseValidator(mock_metadata)

        # When: planningフェーズの依存関係を検証
        result = validator.validate_dependencies(
            phase_name='planning',
            ignore_violations=False
        )

        # Then: 依存関係なしで成功
        assert result['valid'] is True
