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


class TestMetadataManagerEvaluationExtensions:
    """Issue #362: Evaluation Phase 用のMetadataManager拡張機能のテスト"""

    def test_rollback_to_phase_implementation(self, tmp_path):
        """
        TC-MM-001: rollback_to_phase() - Phase 4への巻き戻し（正常系）

        Given: Phase 1-8がすべてcompletedである
        When: rollback_to_phase('implementation')が呼ばれる
        Then: Phase 4-8がpendingにリセットされる
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='362',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/362',
            issue_title='Test Issue #362'
        )
        manager = MetadataManager(metadata_path)

        # Phase 1-8をcompletedに設定
        for phase_name in ['requirements', 'design', 'test_scenario', 'implementation',
                           'test_implementation', 'testing', 'documentation', 'report']:
            manager.update_phase_status(phase_name, 'completed')

        # Act
        result = manager.rollback_to_phase('implementation')

        # Assert
        assert result['success'] is True
        assert 'backup_path' in result
        assert Path(result['backup_path']).exists()

        # Phase 4-8がpendingにリセットされている
        assert manager.get_phase_status('implementation') == 'pending'
        assert manager.get_phase_status('test_implementation') == 'pending'
        assert manager.get_phase_status('testing') == 'pending'
        assert manager.get_phase_status('documentation') == 'pending'
        assert manager.get_phase_status('report') == 'pending'

        # Phase 1-3はcompletedのまま
        assert manager.get_phase_status('requirements') == 'completed'
        assert manager.get_phase_status('design') == 'completed'
        assert manager.get_phase_status('test_scenario') == 'completed'

    def test_rollback_to_phase_requirements(self, tmp_path):
        """
        TC-MM-002: rollback_to_phase() - Phase 1への巻き戻し

        Given: Phase 1-8がすべてcompletedである
        When: rollback_to_phase('requirements')が呼ばれる
        Then: Phase 1-8すべてがpendingにリセットされる
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='362',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/362',
            issue_title='Test Issue #362'
        )
        manager = MetadataManager(metadata_path)

        # Phase 1-8をcompletedに設定
        for phase_name in ['requirements', 'design', 'test_scenario', 'implementation',
                           'test_implementation', 'testing', 'documentation', 'report']:
            manager.update_phase_status(phase_name, 'completed')

        # Act
        result = manager.rollback_to_phase('requirements')

        # Assert
        assert result['success'] is True

        # すべてのフェーズがpendingにリセットされている
        for phase_name in ['requirements', 'design', 'test_scenario', 'implementation',
                           'test_implementation', 'testing', 'documentation', 'report']:
            assert manager.get_phase_status(phase_name) == 'pending'

    def test_rollback_to_phase_invalid_phase(self, tmp_path):
        """
        TC-MM-003: rollback_to_phase() - 不正なフェーズ名（異常系）

        Given: 不正なフェーズ名を指定する
        When: rollback_to_phase('invalid_phase')が呼ばれる
        Then: エラーが返される
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='362',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/362',
            issue_title='Test Issue #362'
        )
        manager = MetadataManager(metadata_path)

        # Act
        result = manager.rollback_to_phase('invalid_phase')

        # Assert
        assert result['success'] is False
        assert 'error' in result

    def test_get_all_phases_status(self, tmp_path):
        """
        TC-MM-004: get_all_phases_status() - 全フェーズステータス取得

        Given: Phase 1-3がcompleted、Phase 4がin_progress、Phase 5-8がpending
        When: get_all_phases_status()が呼ばれる
        Then: すべてのフェーズのステータスが返される
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='362',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/362',
            issue_title='Test Issue #362'
        )
        manager = MetadataManager(metadata_path)

        # Phase 1-3をcompleted、Phase 4をin_progressに設定
        manager.update_phase_status('requirements', 'completed')
        manager.update_phase_status('design', 'completed')
        manager.update_phase_status('test_scenario', 'completed')
        manager.update_phase_status('implementation', 'in_progress')

        # Act
        result = manager.get_all_phases_status()

        # Assert
        assert isinstance(result, dict)
        assert result['requirements'] == 'completed'
        assert result['design'] == 'completed'
        assert result['test_scenario'] == 'completed'
        assert result['implementation'] == 'in_progress'
        assert result['test_implementation'] == 'pending'
        assert result['testing'] == 'pending'

    def test_backup_metadata(self, tmp_path):
        """
        TC-MM-005: backup_metadata() - メタデータバックアップ作成

        Given: metadata.jsonが存在する
        When: backup_metadata()が呼ばれる
        Then: タイムスタンプ付きバックアップファイルが作成される
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='362',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/362',
            issue_title='Test Issue #362'
        )
        manager = MetadataManager(metadata_path)

        # Act
        backup_path = manager.backup_metadata()

        # Assert
        assert backup_path is not None
        assert Path(backup_path).exists()
        assert 'metadata.json.backup_' in backup_path
        assert Path(backup_path).parent == tmp_path

    def test_set_evaluation_decision_pass(self, tmp_path):
        """
        TC-MM-006: set_evaluation_decision() - PASS判定の記録

        Given: Evaluation Phaseが実行された
        When: set_evaluation_decision('PASS', ...)が呼ばれる
        Then: metadata.jsonにPASS判定が記録される
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='362',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/362',
            issue_title='Test Issue #362'
        )
        manager = MetadataManager(metadata_path)

        # Act
        manager.set_evaluation_decision(
            decision='PASS',
            failed_phase=None,
            remaining_tasks=[],
            created_issue_url=None,
            abort_reason=None
        )

        # Assert
        assert 'evaluation' in manager.data['phases']
        assert manager.data['phases']['evaluation']['decision'] == 'PASS'
        assert manager.data['phases']['evaluation']['failed_phase'] is None
        assert manager.data['phases']['evaluation']['remaining_tasks'] == []

    def test_set_evaluation_decision_pass_with_issues(self, tmp_path):
        """
        TC-MM-007: set_evaluation_decision() - PASS_WITH_ISSUES判定の記録

        Given: Evaluation Phaseで残タスクが発見された
        When: set_evaluation_decision('PASS_WITH_ISSUES', ...)が呼ばれる
        Then: 残タスクとIssue URLが記録される
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='362',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/362',
            issue_title='Test Issue #362'
        )
        manager = MetadataManager(metadata_path)

        # Act
        remaining_tasks = [
            {'task': 'Performance optimization', 'phase': 'implementation', 'priority': 'Medium'},
            {'task': 'Additional tests', 'phase': 'testing', 'priority': 'Low'}
        ]
        manager.set_evaluation_decision(
            decision='PASS_WITH_ISSUES',
            failed_phase=None,
            remaining_tasks=remaining_tasks,
            created_issue_url='https://github.com/tielec/infrastructure-as-code/issues/363',
            abort_reason=None
        )

        # Assert
        assert manager.data['phases']['evaluation']['decision'] == 'PASS_WITH_ISSUES'
        assert len(manager.data['phases']['evaluation']['remaining_tasks']) == 2
        assert manager.data['phases']['evaluation']['created_issue_url'] == 'https://github.com/tielec/infrastructure-as-code/issues/363'

    def test_set_evaluation_decision_fail_phase_x(self, tmp_path):
        """
        TC-MM-008: set_evaluation_decision() - FAIL_PHASE_X判定の記録

        Given: Evaluation PhaseでPhase 4に問題が発見された
        When: set_evaluation_decision('FAIL_PHASE_4', ...)が呼ばれる
        Then: failed_phaseが記録される
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='362',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/362',
            issue_title='Test Issue #362'
        )
        manager = MetadataManager(metadata_path)

        # Act
        manager.set_evaluation_decision(
            decision='FAIL_PHASE_4',
            failed_phase='implementation',
            remaining_tasks=[],
            created_issue_url=None,
            abort_reason=None
        )

        # Assert
        assert manager.data['phases']['evaluation']['decision'] == 'FAIL_PHASE_4'
        assert manager.data['phases']['evaluation']['failed_phase'] == 'implementation'

    def test_set_evaluation_decision_abort(self, tmp_path):
        """
        TC-MM-009: set_evaluation_decision() - ABORT判定の記録

        Given: Evaluation Phaseで致命的な問題が発見された
        When: set_evaluation_decision('ABORT', ...)が呼ばれる
        Then: abort_reasonが記録される
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='362',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/362',
            issue_title='Test Issue #362'
        )
        manager = MetadataManager(metadata_path)

        # Act
        manager.set_evaluation_decision(
            decision='ABORT',
            failed_phase=None,
            remaining_tasks=[],
            created_issue_url=None,
            abort_reason='Fundamental architectural flaw discovered'
        )

        # Assert
        assert manager.data['phases']['evaluation']['decision'] == 'ABORT'
        assert manager.data['phases']['evaluation']['abort_reason'] == 'Fundamental architectural flaw discovered'
