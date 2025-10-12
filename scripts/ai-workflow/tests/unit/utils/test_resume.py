"""ResumeManagerのUnitテスト

このテストファイルは、Phase 3のテストシナリオ（test-scenario.md）に基づいて作成されています。
テストケース番号は、テストシナリオ文書の番号に対応しています。
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from core.metadata_manager import MetadataManager
from core.workflow_state import WorkflowState
from utils.resume import ResumeManager


class TestResumeManagerInit:
    """ResumeManager.__init__()のテスト"""

    def test_init_success(self, tmp_path):
        """
        UT-RM-INIT-001: 正常系 - 初期化成功

        検証項目:
        - ResumeManagerが正しく初期化されること
        - metadata_managerが設定されること
        - phasesが正しいフェーズリストを持つこと
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='[FEATURE] AIワークフロー実行時のレジューム機能実装'
        )
        metadata_manager = MetadataManager(metadata_path)

        # Act
        resume_manager = ResumeManager(metadata_manager)

        # Assert
        assert resume_manager.metadata_manager == metadata_manager
        assert resume_manager.phases == [
            'requirements',
            'design',
            'test_scenario',
            'implementation',
            'test_implementation',
            'testing',
            'documentation',
            'report'
        ]


class TestResumeManagerCanResume:
    """ResumeManager.can_resume()のテスト"""

    def test_can_resume_with_failed_phase(self, tmp_path):
        """
        UT-RM-RESUME-001: 正常系 - メタデータ存在、未完了フェーズあり

        検証項目:
        - メタデータが存在し未完了フェーズがある場合にTrueを返すこと
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='Test Issue'
        )
        metadata_manager = MetadataManager(metadata_path)

        # Phase 1-4を完了、Phase 5を失敗、Phase 6-8をpendingに設定
        for phase in ['requirements', 'design', 'test_scenario', 'implementation']:
            metadata_manager.update_phase_status(phase, 'completed')
        metadata_manager.update_phase_status('test_implementation', 'failed')

        resume_manager = ResumeManager(metadata_manager)

        # Act
        result = resume_manager.can_resume()

        # Assert
        assert result is True

    def test_can_resume_metadata_not_exists(self, tmp_path):
        """
        UT-RM-RESUME-002: 正常系 - メタデータ不存在

        検証項目:
        - メタデータファイルが存在しない場合にFalseを返すこと
        """
        # Arrange
        metadata_path = tmp_path / 'nonexistent' / 'metadata.json'
        metadata_manager = MagicMock(spec=MetadataManager)
        metadata_manager.metadata_path = metadata_path
        metadata_manager.metadata_path.exists = MagicMock(return_value=False)

        resume_manager = ResumeManager(metadata_manager)

        # Act
        result = resume_manager.can_resume()

        # Assert
        assert result is False

    def test_can_resume_all_completed(self, tmp_path):
        """
        UT-RM-RESUME-003: 正常系 - 全フェーズ完了

        検証項目:
        - 全フェーズが完了している場合にFalseを返すこと
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='Test Issue'
        )
        metadata_manager = MetadataManager(metadata_path)

        # 全フェーズを完了に設定
        for phase in ['requirements', 'design', 'test_scenario', 'implementation',
                      'test_implementation', 'testing', 'documentation', 'report']:
            metadata_manager.update_phase_status(phase, 'completed')

        resume_manager = ResumeManager(metadata_manager)

        # Act
        result = resume_manager.can_resume()

        # Assert
        assert result is False

    def test_can_resume_all_pending(self, tmp_path):
        """
        UT-RM-RESUME-004: 正常系 - 全フェーズpending

        検証項目:
        - 全フェーズがpendingの場合にFalseを返すこと（新規ワークフロー）
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='Test Issue'
        )
        metadata_manager = MetadataManager(metadata_path)

        # デフォルトではすべてpending
        resume_manager = ResumeManager(metadata_manager)

        # Act
        result = resume_manager.can_resume()

        # Assert
        assert result is False


class TestResumeManagerIsCompleted:
    """ResumeManager.is_completed()のテスト"""

    def test_is_completed_all_phases_completed(self, tmp_path):
        """
        UT-RM-COMPLETE-001: 正常系 - 全フェーズ完了

        検証項目:
        - 全フェーズが完了している場合にTrueを返すこと
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='Test Issue'
        )
        metadata_manager = MetadataManager(metadata_path)

        # 全フェーズを完了に設定
        for phase in ['requirements', 'design', 'test_scenario', 'implementation',
                      'test_implementation', 'testing', 'documentation', 'report']:
            metadata_manager.update_phase_status(phase, 'completed')

        resume_manager = ResumeManager(metadata_manager)

        # Act
        result = resume_manager.is_completed()

        # Assert
        assert result is True

    def test_is_completed_with_pending_phase(self, tmp_path):
        """
        UT-RM-COMPLETE-002: 正常系 - 未完了フェーズあり

        検証項目:
        - 未完了フェーズがある場合にFalseを返すこと
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='Test Issue'
        )
        metadata_manager = MetadataManager(metadata_path)

        # Phase 1-7を完了、Phase 8をpendingに設定
        for phase in ['requirements', 'design', 'test_scenario', 'implementation',
                      'test_implementation', 'testing', 'documentation']:
            metadata_manager.update_phase_status(phase, 'completed')

        resume_manager = ResumeManager(metadata_manager)

        # Act
        result = resume_manager.is_completed()

        # Assert
        assert result is False

    def test_is_completed_with_failed_phase(self, tmp_path):
        """
        UT-RM-COMPLETE-003: 正常系 - 失敗フェーズあり

        検証項目:
        - 失敗フェーズがある場合にFalseを返すこと
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='Test Issue'
        )
        metadata_manager = MetadataManager(metadata_path)

        # Phase 1-4を完了、Phase 5を失敗に設定
        for phase in ['requirements', 'design', 'test_scenario', 'implementation']:
            metadata_manager.update_phase_status(phase, 'completed')
        metadata_manager.update_phase_status('test_implementation', 'failed')

        resume_manager = ResumeManager(metadata_manager)

        # Act
        result = resume_manager.is_completed()

        # Assert
        assert result is False


class TestResumeManagerGetResumePhase:
    """ResumeManager.get_resume_phase()のテスト"""

    def test_get_resume_phase_from_failed(self, tmp_path):
        """
        UT-RM-PHASE-001: 正常系 - failedフェーズから再開

        検証項目:
        - failedフェーズが最優先でレジューム開始フェーズとして返されること
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='Test Issue'
        )
        metadata_manager = MetadataManager(metadata_path)

        # Phase 1-4を完了、Phase 5を失敗、Phase 6-8をpendingに設定
        for phase in ['requirements', 'design', 'test_scenario', 'implementation']:
            metadata_manager.update_phase_status(phase, 'completed')
        metadata_manager.update_phase_status('test_implementation', 'failed')

        resume_manager = ResumeManager(metadata_manager)

        # Act
        result = resume_manager.get_resume_phase()

        # Assert
        assert result == 'test_implementation'

    def test_get_resume_phase_multiple_failed_first_priority(self, tmp_path):
        """
        UT-RM-PHASE-002: 正常系 - 複数failedフェーズ、最初から再開

        検証項目:
        - 複数のfailedフェーズがある場合、最初の失敗フェーズから再開すること
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='Test Issue'
        )
        metadata_manager = MetadataManager(metadata_path)

        # Phase 1-2を完了、Phase 3を失敗、Phase 4を完了、Phase 5を失敗
        for phase in ['requirements', 'design']:
            metadata_manager.update_phase_status(phase, 'completed')
        metadata_manager.update_phase_status('test_scenario', 'failed')
        metadata_manager.update_phase_status('implementation', 'completed')
        metadata_manager.update_phase_status('test_implementation', 'failed')

        resume_manager = ResumeManager(metadata_manager)

        # Act
        result = resume_manager.get_resume_phase()

        # Assert
        assert result == 'test_scenario'  # 最初のfailedフェーズ

    def test_get_resume_phase_from_in_progress(self, tmp_path):
        """
        UT-RM-PHASE-003: 正常系 - in_progressフェーズから再開

        検証項目:
        - failedフェーズがなく、in_progressフェーズがある場合にそこから再開すること
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='Test Issue'
        )
        metadata_manager = MetadataManager(metadata_path)

        # Phase 1-4を完了、Phase 5をin_progressに設定
        for phase in ['requirements', 'design', 'test_scenario', 'implementation']:
            metadata_manager.update_phase_status(phase, 'completed')
        metadata_manager.update_phase_status('test_implementation', 'in_progress')

        resume_manager = ResumeManager(metadata_manager)

        # Act
        result = resume_manager.get_resume_phase()

        # Assert
        assert result == 'test_implementation'

    def test_get_resume_phase_from_pending(self, tmp_path):
        """
        UT-RM-PHASE-004: 正常系 - pendingフェーズから再開

        検証項目:
        - failed/in_progressフェーズがなく、pendingフェーズがある場合にそこから再開すること
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='Test Issue'
        )
        metadata_manager = MetadataManager(metadata_path)

        # Phase 1-5を完了、Phase 6-8をpendingに設定
        for phase in ['requirements', 'design', 'test_scenario', 'implementation',
                      'test_implementation']:
            metadata_manager.update_phase_status(phase, 'completed')

        resume_manager = ResumeManager(metadata_manager)

        # Act
        result = resume_manager.get_resume_phase()

        # Assert
        assert result == 'testing'  # 最初のpendingフェーズ

    def test_get_resume_phase_all_completed_returns_none(self, tmp_path):
        """
        UT-RM-PHASE-005: 正常系 - 全フェーズ完了、Noneを返す

        検証項目:
        - 全フェーズが完了している場合にNoneを返すこと
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='Test Issue'
        )
        metadata_manager = MetadataManager(metadata_path)

        # 全フェーズを完了に設定
        for phase in ['requirements', 'design', 'test_scenario', 'implementation',
                      'test_implementation', 'testing', 'documentation', 'report']:
            metadata_manager.update_phase_status(phase, 'completed')

        resume_manager = ResumeManager(metadata_manager)

        # Act
        result = resume_manager.get_resume_phase()

        # Assert
        assert result is None

    def test_get_resume_phase_failed_priority_over_in_progress(self, tmp_path):
        """
        UT-RM-PHASE-006: エッジケース - failed優先度確認

        検証項目:
        - failedフェーズがin_progressより優先されること
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='Test Issue'
        )
        metadata_manager = MetadataManager(metadata_path)

        # Phase 1-2を完了、Phase 3をin_progress、Phase 4を完了、Phase 5を失敗
        for phase in ['requirements', 'design']:
            metadata_manager.update_phase_status(phase, 'completed')
        metadata_manager.update_phase_status('test_scenario', 'in_progress')
        metadata_manager.update_phase_status('implementation', 'completed')
        metadata_manager.update_phase_status('test_implementation', 'failed')

        resume_manager = ResumeManager(metadata_manager)

        # Act
        result = resume_manager.get_resume_phase()

        # Assert
        assert result == 'test_implementation'  # failedが優先


class TestResumeManagerGetStatusSummary:
    """ResumeManager.get_status_summary()のテスト"""

    def test_get_status_summary_mixed_statuses(self, tmp_path):
        """
        UT-RM-SUMMARY-001: 正常系 - ステータスサマリー取得

        検証項目:
        - 各ステータスのフェーズリストが正しく取得できること
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='Test Issue'
        )
        metadata_manager = MetadataManager(metadata_path)

        # 各フェーズのステータスを設定
        for phase in ['requirements', 'design', 'test_scenario', 'implementation']:
            metadata_manager.update_phase_status(phase, 'completed')
        metadata_manager.update_phase_status('test_implementation', 'failed')
        metadata_manager.update_phase_status('testing', 'in_progress')
        # documentation, reportはpending

        resume_manager = ResumeManager(metadata_manager)

        # Act
        result = resume_manager.get_status_summary()

        # Assert
        assert result['completed'] == ['requirements', 'design', 'test_scenario', 'implementation']
        assert result['failed'] == ['test_implementation']
        assert result['in_progress'] == ['testing']
        assert result['pending'] == ['documentation', 'report']

    def test_get_status_summary_all_completed(self, tmp_path):
        """
        UT-RM-SUMMARY-002: 正常系 - 全フェーズ完了時のサマリー

        検証項目:
        - 全フェーズが完了している場合のサマリーが正しいこと
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='Test Issue'
        )
        metadata_manager = MetadataManager(metadata_path)

        # 全フェーズを完了に設定
        for phase in ['requirements', 'design', 'test_scenario', 'implementation',
                      'test_implementation', 'testing', 'documentation', 'report']:
            metadata_manager.update_phase_status(phase, 'completed')

        resume_manager = ResumeManager(metadata_manager)

        # Act
        result = resume_manager.get_status_summary()

        # Assert
        assert result['completed'] == ['requirements', 'design', 'test_scenario', 'implementation',
                                       'test_implementation', 'testing', 'documentation', 'report']
        assert result['failed'] == []
        assert result['in_progress'] == []
        assert result['pending'] == []

    def test_get_status_summary_all_pending(self, tmp_path):
        """
        UT-RM-SUMMARY-003: 正常系 - 全フェーズpending時のサマリー

        検証項目:
        - 全フェーズがpendingの場合のサマリーが正しいこと
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='Test Issue'
        )
        metadata_manager = MetadataManager(metadata_path)

        # デフォルトではすべてpending
        resume_manager = ResumeManager(metadata_manager)

        # Act
        result = resume_manager.get_status_summary()

        # Assert
        assert result['completed'] == []
        assert result['failed'] == []
        assert result['in_progress'] == []
        assert result['pending'] == ['requirements', 'design', 'test_scenario', 'implementation',
                                     'test_implementation', 'testing', 'documentation', 'report']


class TestResumeManagerReset:
    """ResumeManager.reset()のテスト"""

    def test_reset_calls_metadata_manager_clear(self):
        """
        UT-RM-RESET-001: 正常系 - resetがMetadataManager.clear()を呼ぶ

        検証項目:
        - reset()がMetadataManager.clear()を正しく呼び出すこと
        """
        # Arrange
        metadata_manager_mock = MagicMock(spec=MetadataManager)
        resume_manager = ResumeManager(metadata_manager_mock)

        # Act
        resume_manager.reset()

        # Assert
        metadata_manager_mock.clear.assert_called_once()


class TestResumeManagerGetPhasesByStatus:
    """ResumeManager._get_phases_by_status()のテスト"""

    def test_get_phases_by_status_filters_correctly(self, tmp_path):
        """
        UT-RM-FILTER-001: 正常系 - ステータス別フェーズ取得

        検証項目:
        - 指定したステータスのフェーズリストが正しく取得できること
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='Test Issue'
        )
        metadata_manager = MetadataManager(metadata_path)

        # 各フェーズのステータスを設定
        metadata_manager.update_phase_status('requirements', 'completed')
        metadata_manager.update_phase_status('design', 'completed')
        metadata_manager.update_phase_status('test_scenario', 'failed')
        # implementation, test_implementationはpending
        metadata_manager.update_phase_status('testing', 'in_progress')
        # documentation, reportはpending

        resume_manager = ResumeManager(metadata_manager)

        # Act & Assert
        assert resume_manager._get_phases_by_status('completed') == ['requirements', 'design']
        assert resume_manager._get_phases_by_status('failed') == ['test_scenario']
        assert resume_manager._get_phases_by_status('in_progress') == ['testing']
        assert resume_manager._get_phases_by_status('pending') == [
            'implementation', 'test_implementation', 'documentation', 'report'
        ]
