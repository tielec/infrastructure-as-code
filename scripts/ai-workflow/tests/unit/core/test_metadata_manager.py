"""MetadataManagerのUnitテスト"""
import pytest
from pathlib import Path
from core.metadata_manager import MetadataManager
from core.workflow_state import WorkflowState


class TestMetadataManager:
    """MetadataManagerクラスのUnitテスト"""

    def test_init(self, tmp_path):
        """
        初期化のテスト

        検証項目:
        - 正しく初期化されるか
        - workflow_dirが正しく設定されるか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )

        # Act
        manager = MetadataManager(metadata_path)

        # Assert
        assert manager.metadata_path == metadata_path
        assert manager.workflow_dir == metadata_path.parent
        assert manager.data is not None

    def test_data_property(self, tmp_path):
        """
        dataプロパティのテスト

        検証項目:
        - dataプロパティで生データを取得できるか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )
        manager = MetadataManager(metadata_path)

        # Act
        data = manager.data

        # Assert
        assert data['issue_number'] == '304'
        assert data['workflow_version'] == '1.0.0'

    def test_update_phase_status(self, tmp_path):
        """
        フェーズステータス更新のテスト

        検証項目:
        - MetadataManager経由でステータス更新できるか
        - 自動的に保存されるか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )
        manager = MetadataManager(metadata_path)

        # Act
        manager.update_phase_status('requirements', 'in_progress')

        # Assert
        assert manager.data['phases']['requirements']['status'] == 'in_progress'
        assert manager.data['phases']['requirements']['started_at'] is not None

        # ファイルから再読み込みして確認（自動保存の確認）
        loaded_manager = MetadataManager(metadata_path)
        assert loaded_manager.data['phases']['requirements']['status'] == 'in_progress'

    def test_update_phase_status_with_output_file(self, tmp_path):
        """
        フェーズステータス更新（出力ファイル指定）のテスト

        検証項目:
        - output_fileが記録されるか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )
        manager = MetadataManager(metadata_path)

        # Act
        manager.update_phase_status(
            'requirements',
            'completed',
            output_file='requirements.md'
        )

        # Assert
        assert 'output_files' in manager.data['phases']['requirements']
        assert 'requirements.md' in manager.data['phases']['requirements']['output_files']

    def test_add_cost(self, tmp_path):
        """
        コストトラッキングのテスト

        検証項目:
        - 入力トークン数、出力トークン数、コストが累積されるか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )
        manager = MetadataManager(metadata_path)

        # Act
        manager.add_cost(input_tokens=1000, output_tokens=500, cost_usd=0.05)
        manager.add_cost(input_tokens=2000, output_tokens=1000, cost_usd=0.10)

        # Assert
        assert manager.data['cost_tracking']['total_input_tokens'] == 3000
        assert manager.data['cost_tracking']['total_output_tokens'] == 1500
        assert manager.data['cost_tracking']['total_cost_usd'] == 0.15

        # ファイルから再読み込みして確認（自動保存の確認）
        loaded_manager = MetadataManager(metadata_path)
        assert loaded_manager.data['cost_tracking']['total_input_tokens'] == 3000
        assert loaded_manager.data['cost_tracking']['total_output_tokens'] == 1500
        assert abs(loaded_manager.data['cost_tracking']['total_cost_usd'] - 0.15) < 0.0001

    def test_get_phase_status(self, tmp_path):
        """
        フェーズステータス取得のテスト

        検証項目:
        - 正しいステータスを取得できるか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )
        manager = MetadataManager(metadata_path)

        # Act & Assert
        assert manager.get_phase_status('requirements') == 'pending'

        manager.update_phase_status('requirements', 'in_progress')
        assert manager.get_phase_status('requirements') == 'in_progress'

    def test_set_design_decision(self, tmp_path):
        """
        設計判断記録のテスト

        検証項目:
        - implementation_strategy, test_strategy, test_code_strategyが設定できるか
        - 自動的に保存されるか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )
        manager = MetadataManager(metadata_path)

        # Act
        manager.set_design_decision('implementation_strategy', 'EXTEND')
        manager.set_design_decision('test_strategy', 'UNIT_BDD')
        manager.set_design_decision('test_code_strategy', 'BOTH_TEST')

        # Assert
        assert manager.data['design_decisions']['implementation_strategy'] == 'EXTEND'
        assert manager.data['design_decisions']['test_strategy'] == 'UNIT_BDD'
        assert manager.data['design_decisions']['test_code_strategy'] == 'BOTH_TEST'

        # ファイルから再読み込みして確認（自動保存の確認）
        loaded_manager = MetadataManager(metadata_path)
        assert loaded_manager.data['design_decisions']['implementation_strategy'] == 'EXTEND'
        assert loaded_manager.data['design_decisions']['test_strategy'] == 'UNIT_BDD'
        assert loaded_manager.data['design_decisions']['test_code_strategy'] == 'BOTH_TEST'

    def test_increment_retry_count(self, tmp_path):
        """
        リトライカウント増加のテスト

        検証項目:
        - カウントが正しく増加するか
        - 自動的に保存されるか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )
        manager = MetadataManager(metadata_path)

        # Act
        count1 = manager.increment_retry_count('requirements')
        count2 = manager.increment_retry_count('requirements')

        # Assert
        assert count1 == 1
        assert count2 == 2
        assert manager.data['phases']['requirements']['retry_count'] == 2

        # ファイルから再読み込みして確認（自動保存の確認）
        loaded_manager = MetadataManager(metadata_path)
        assert loaded_manager.data['phases']['requirements']['retry_count'] == 2

    def test_save(self, tmp_path):
        """
        明示的な保存のテスト

        検証項目:
        - save()メソッドで保存できるか
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )
        manager = MetadataManager(metadata_path)

        # Act
        manager.data['test_field'] = 'test_value'
        manager.save()

        # Assert
        loaded_manager = MetadataManager(metadata_path)
        assert loaded_manager.data['test_field'] == 'test_value'

    def test_clear_removes_metadata_and_directory(self, tmp_path):
        """
        UT-MM-CLEAR-001: 正常系 - メタデータファイル削除

        検証項目:
        - メタデータファイルが正しく削除されること
        - ワークフローディレクトリが正しく削除されること
        """
        # Arrange
        metadata_path = tmp_path / 'test_workflow' / 'metadata.json'
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='Test Issue'
        )
        manager = MetadataManager(metadata_path)

        # メタデータファイルが存在することを確認
        assert metadata_path.exists()
        assert metadata_path.parent.exists()

        # Act
        manager.clear()

        # Assert
        assert not metadata_path.exists()
        assert not metadata_path.parent.exists()

    def test_clear_handles_nonexistent_files(self, tmp_path):
        """
        UT-MM-CLEAR-002: 正常系 - ファイル不存在時のエラーなし

        検証項目:
        - メタデータファイルが存在しない場合でもエラーが発生しないこと
        """
        # Arrange
        metadata_path = tmp_path / 'nonexistent_workflow' / 'metadata.json'
        manager = MetadataManager.__new__(MetadataManager)
        manager.metadata_path = metadata_path
        manager.workflow_dir = metadata_path.parent

        # ファイルが存在しないことを確認
        assert not metadata_path.exists()
        assert not metadata_path.parent.exists()

        # Act & Assert - エラーが発生しないことを確認
        try:
            manager.clear()
        except Exception as e:
            pytest.fail(f"clear() should not raise exception for nonexistent files: {e}")

    def test_clear_handles_permission_error(self, tmp_path):
        """
        UT-MM-CLEAR-003: 異常系 - 権限エラー

        検証項目:
        - 削除権限がない場合に適切にエラーが発生すること
        """
        # Arrange
        metadata_path = tmp_path / 'readonly_workflow' / 'metadata.json'
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='360',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/360',
            issue_title='Test Issue'
        )

        # ファイルを読み取り専用にする
        import os
        os.chmod(metadata_path, 0o444)
        os.chmod(metadata_path.parent, 0o555)

        manager = MetadataManager(metadata_path)

        # Act & Assert
        try:
            with pytest.raises(PermissionError):
                manager.clear()
        finally:
            # クリーンアップ: 権限を戻して削除
            try:
                os.chmod(metadata_path, 0o644)
                os.chmod(metadata_path.parent, 0o755)
                if metadata_path.exists():
                    metadata_path.unlink()
                if metadata_path.parent.exists():
                    metadata_path.parent.rmdir()
            except:
                pass  # クリーンアップのエラーは無視
