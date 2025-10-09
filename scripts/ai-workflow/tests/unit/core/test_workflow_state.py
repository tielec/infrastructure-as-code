"""WorkflowStateのUnitテスト"""
import json
import pytest
from pathlib import Path
from datetime import datetime
from core.workflow_state import WorkflowState, PhaseStatus


class TestWorkflowState:
    """WorkflowStateクラスのUnitテスト"""

    def test_create_new(self, tmp_path):
        """
        新規ワークフロー作成のテスト

        検証項目:
        - metadata.jsonが存在しない状態で作成
        - すべてのフィールドが存在するか
        - タイムスタンプがISO 8601形式か
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        issue_number = '304'
        issue_url = 'https://github.com/tielec/infrastructure-as-code/issues/304'
        issue_title = 'Test Issue #304'

        # Act
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number=issue_number,
            issue_url=issue_url,
            issue_title=issue_title
        )

        # Assert
        assert metadata_path.exists()
        assert state.data['issue_number'] == issue_number
        assert state.data['issue_url'] == issue_url
        assert state.data['issue_title'] == issue_title
        assert state.data['workflow_version'] == '1.0.0'
        assert state.data['current_phase'] == 'requirements'

        # タイムスタンプがISO 8601形式か確認
        created_at = state.data['created_at']
        updated_at = state.data['updated_at']
        assert created_at.endswith('Z')
        assert updated_at.endswith('Z')

        # タイムスタンプをパース可能か確認
        datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        datetime.fromisoformat(updated_at.replace('Z', '+00:00'))

        # すべてのフェーズが存在し、ステータスがpendingであるか
        phases = ['requirements', 'design', 'test_scenario',
                  'implementation', 'testing', 'documentation']
        for phase in phases:
            assert phase in state.data['phases']
            assert state.data['phases'][phase]['status'] == 'pending'
            assert state.data['phases'][phase]['retry_count'] == 0
            assert state.data['phases'][phase]['started_at'] is None
            assert state.data['phases'][phase]['completed_at'] is None
            assert state.data['phases'][phase]['review_result'] is None

    def test_load(self, tmp_path):
        """
        metadata.json読み込みのテスト

        検証項目:
        - 正しいJSON構造を読み込めるか
        - UTF-8エンコーディングで読み込めるか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )

        # Act
        loaded_state = WorkflowState(metadata_path)

        # Assert
        assert loaded_state.data['issue_number'] == '304'
        assert loaded_state.data['workflow_version'] == '1.0.0'

    def test_load_file_not_found(self, tmp_path):
        """
        metadata.jsonが存在しない場合のエラーテスト

        検証項目:
        - FileNotFoundErrorが発生するか
        """
        # Arrange
        metadata_path = tmp_path / 'non_existent.json'

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            WorkflowState(metadata_path)

    def test_save(self, tmp_path):
        """
        metadata.json保存のテスト

        検証項目:
        - updated_atが更新されるか
        - UTF-8エンコーディングで保存されるか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )
        initial_updated_at = state.data['updated_at']

        # Act
        # 少し待機してタイムスタンプが変わることを確認
        import time
        time.sleep(0.1)
        state.data['test_field'] = 'test_value'
        state.save()

        # Assert
        assert state.data['updated_at'] != initial_updated_at

        # ファイルから再読み込みして確認
        with open(metadata_path, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        assert loaded_data['test_field'] == 'test_value'

    def test_save_with_japanese(self, tmp_path):
        """
        日本語を含むデータの保存テスト

        検証項目:
        - UTF-8エンコーディングで保存されるか
        - ensure_ascii=Falseが適用されているか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        issue_title = '[TASK] AI駆動開発自動化ワークフローMVP v1.0.0実装'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title=issue_title
        )

        # Act
        state.save()

        # Assert
        with open(metadata_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # 日本語がそのまま保存されているか（\uXXXXでエスケープされていないか）
            assert 'AI駆動開発' in content

    def test_update_phase_status_to_in_progress(self, tmp_path):
        """
        フェーズステータス更新（pending → in_progress）のテスト

        検証項目:
        - started_atが記録されるか
        - current_phaseが更新されるか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )

        # Act
        state.update_phase_status('requirements', PhaseStatus.IN_PROGRESS)

        # Assert
        assert state.data['phases']['requirements']['status'] == 'in_progress'
        assert state.data['phases']['requirements']['started_at'] is not None
        assert state.data['phases']['requirements']['started_at'].endswith('Z')
        assert state.data['current_phase'] == 'requirements'

    def test_update_phase_status_to_completed(self, tmp_path):
        """
        フェーズステータス更新（in_progress → completed）のテスト

        検証項目:
        - completed_atが記録されるか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )
        state.update_phase_status('requirements', PhaseStatus.IN_PROGRESS)

        # Act
        state.update_phase_status('requirements', PhaseStatus.COMPLETED)

        # Assert
        assert state.data['phases']['requirements']['status'] == 'completed'
        assert state.data['phases']['requirements']['completed_at'] is not None
        assert state.data['phases']['requirements']['completed_at'].endswith('Z')

    def test_update_phase_status_to_failed(self, tmp_path):
        """
        フェーズステータス更新（in_progress → failed）のテスト

        検証項目:
        - completed_atが記録されるか（failedでも記録される）
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )
        state.update_phase_status('requirements', PhaseStatus.IN_PROGRESS)

        # Act
        state.update_phase_status('requirements', PhaseStatus.FAILED)

        # Assert
        assert state.data['phases']['requirements']['status'] == 'failed'
        assert state.data['phases']['requirements']['completed_at'] is not None

    def test_update_phase_status_unknown_phase(self, tmp_path):
        """
        不正なフェーズ名のエラーテスト

        検証項目:
        - ValueErrorが発生するか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )

        # Act & Assert
        with pytest.raises(ValueError, match='Unknown phase'):
            state.update_phase_status('invalid_phase', PhaseStatus.IN_PROGRESS)

    def test_increment_retry_count(self, tmp_path):
        """
        リトライカウント増加のテスト

        検証項目:
        - カウントが正しく増加するか
        - 上限3回まで増加するか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )

        # Act & Assert
        count1 = state.increment_retry_count('requirements')
        assert count1 == 1
        assert state.data['phases']['requirements']['retry_count'] == 1

        count2 = state.increment_retry_count('requirements')
        assert count2 == 2
        assert state.data['phases']['requirements']['retry_count'] == 2

        count3 = state.increment_retry_count('requirements')
        assert count3 == 3
        assert state.data['phases']['requirements']['retry_count'] == 3

    def test_increment_retry_count_exceeds_max(self, tmp_path):
        """
        リトライカウント上限超過のエラーテスト

        検証項目:
        - 3回を超えると例外が発生するか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )
        state.increment_retry_count('requirements')
        state.increment_retry_count('requirements')
        state.increment_retry_count('requirements')

        # Act & Assert
        with pytest.raises(Exception, match='Max retry count exceeded'):
            state.increment_retry_count('requirements')

    def test_set_design_decision(self, tmp_path):
        """
        設計判断記録のテスト

        検証項目:
        - design_decisionsが正しく更新されるか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )

        # Act
        state.set_design_decision('implementation_strategy', 'EXTEND')
        state.set_design_decision('test_strategy', 'UNIT_BDD')
        state.set_design_decision('test_code_strategy', 'BOTH_TEST')

        # Assert
        assert state.data['design_decisions']['implementation_strategy'] == 'EXTEND'
        assert state.data['design_decisions']['test_strategy'] == 'UNIT_BDD'
        assert state.data['design_decisions']['test_code_strategy'] == 'BOTH_TEST'

    def test_set_design_decision_unknown_key(self, tmp_path):
        """
        不正な設計判断キーのエラーテスト

        検証項目:
        - ValueErrorが発生するか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )

        # Act & Assert
        with pytest.raises(ValueError, match='Unknown design decision key'):
            state.set_design_decision('invalid_key', 'value')

    def test_get_phase_status(self, tmp_path):
        """
        フェーズステータス取得のテスト

        検証項目:
        - 正しいステータスを取得できるか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )

        # Act & Assert
        assert state.get_phase_status('requirements') == 'pending'

        state.update_phase_status('requirements', PhaseStatus.IN_PROGRESS)
        assert state.get_phase_status('requirements') == 'in_progress'

        state.update_phase_status('requirements', PhaseStatus.COMPLETED)
        assert state.get_phase_status('requirements') == 'completed'
