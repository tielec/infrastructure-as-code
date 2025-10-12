"""phase_dependencies機能の統合テスト

このファイルは依存関係チェック機能の統合テストを実装します。
テストシナリオ: .ai-workflow/issue-319/03_test_scenario/output/test-scenario.md

テスト対象:
- フェーズ実行時の依存関係チェック統合
- プリセット機能統合
- 外部ドキュメント指定機能統合
- 後方互換性
- エラーハンドリング統合
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from core.workflow_state import WorkflowState
from core.metadata_manager import MetadataManager
from core.phase_dependencies import (
    validate_phase_dependencies,
    PHASE_PRESETS
)


class TestDependencyCheckIntegration:
    """依存関係チェック統合テスト"""

    def test_dependency_check_success(self, tmp_path):
        """
        IT-001: フェーズ実行時の依存関係チェック - 正常系

        Given: すべての依存フェーズがcompletedである
        When: implementationフェーズの依存関係チェックを実行する
        Then: バリデーションが成功し、valid=Trueが返される
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/319',
            issue_title='Test Issue #319'
        )

        # 依存フェーズをcompleted状態にする
        state.update_phase_status('planning', 'completed')
        state.update_phase_status('requirements', 'completed')
        state.update_phase_status('design', 'completed')
        state.update_phase_status('test_scenario', 'completed')

        manager = MetadataManager(metadata_path)

        # Act
        result = validate_phase_dependencies(
            phase_name='implementation',
            metadata_manager=manager,
            skip_check=False,
            ignore_violations=False
        )

        # Assert
        assert result['valid'] is True
        assert 'error' not in result

    def test_dependency_check_failure(self, tmp_path):
        """
        IT-002: フェーズ実行時の依存関係チェック - 異常系（依存フェーズ未完了）

        Given: 依存フェーズ（requirements）がpendingである
        When: implementationフェーズの依存関係チェックを実行する
        Then: バリデーションが失敗し、エラーメッセージが返される
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/319',
            issue_title='Test Issue #319'
        )

        # planningのみcompleted、他はpending
        state.update_phase_status('planning', 'completed')
        # requirements, design, test_scenarioはpending

        manager = MetadataManager(metadata_path)

        # Act
        result = validate_phase_dependencies(
            phase_name='implementation',
            metadata_manager=manager,
            skip_check=False,
            ignore_violations=False
        )

        # Assert
        assert result['valid'] is False
        assert 'error' in result
        assert 'requirements' in result['error']
        assert 'missing_phases' in result
        assert 'requirements' in result['missing_phases']

    def test_skip_dependency_check_flag(self, tmp_path):
        """
        IT-003: --skip-dependency-check フラグの動作確認

        Given: 依存フェーズが未完了である
        When: skip_check=Trueで依存関係チェックを実行する
        Then: 依存関係に関わらずvalid=Trueが返される
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/319',
            issue_title='Test Issue #319'
        )

        # すべてのフェーズがpending（依存関係を満たしていない）
        manager = MetadataManager(metadata_path)

        # Act
        result = validate_phase_dependencies(
            phase_name='implementation',
            metadata_manager=manager,
            skip_check=True,  # スキップフラグを有効化
            ignore_violations=False
        )

        # Assert
        assert result['valid'] is True
        # エラーや警告が含まれていないことを確認
        assert 'error' not in result
        assert 'warning' not in result

    def test_ignore_dependencies_flag(self, tmp_path):
        """
        IT-004: --ignore-dependencies フラグの動作確認

        Given: 依存フェーズが未完了である
        When: ignore_violations=Trueで依存関係チェックを実行する
        Then: 警告が返されるがvalid=False、ignored=Trueである
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/319',
            issue_title='Test Issue #319'
        )

        # planningのみcompleted
        state.update_phase_status('planning', 'completed')

        manager = MetadataManager(metadata_path)

        # Act
        result = validate_phase_dependencies(
            phase_name='implementation',
            metadata_manager=manager,
            skip_check=False,
            ignore_violations=True  # 違反を無視
        )

        # Assert
        assert result['valid'] is False
        assert result.get('ignored') is True
        assert 'warning' in result
        # 未完了フェーズが警告に含まれることを確認
        assert 'requirements' in result['warning']
        assert 'design' in result['warning']
        assert 'test_scenario' in result['warning']


class TestPresetFunctionality:
    """プリセット機能統合テスト"""

    def test_preset_requirements_only(self):
        """
        IT-005: プリセット実行 - requirements-only

        Given: PHASE_PRESETS['requirements-only']
        When: プリセットを取得する
        Then: ['requirements']が返される
        """
        # Act
        phases = PHASE_PRESETS['requirements-only']

        # Assert
        assert phases == ['requirements']
        assert len(phases) == 1

    def test_preset_design_phase(self):
        """
        IT-006: プリセット実行 - design-phase

        Given: PHASE_PRESETS['design-phase']
        When: プリセットを取得する
        Then: ['requirements', 'design']が返される
        """
        # Act
        phases = PHASE_PRESETS['design-phase']

        # Assert
        assert phases == ['requirements', 'design']
        assert len(phases) == 2

    def test_preset_implementation_phase(self):
        """
        IT-007: プリセット実行 - implementation-phase

        Given: PHASE_PRESETS['implementation-phase']
        When: プリセットを取得する
        Then: 4つのフェーズが返される
        """
        # Act
        phases = PHASE_PRESETS['implementation-phase']

        # Assert
        expected = ['requirements', 'design', 'test_scenario', 'implementation']
        assert phases == expected
        assert len(phases) == 4

    def test_preset_full_workflow(self):
        """
        プリセット実行 - full-workflow

        Given: PHASE_PRESETS['full-workflow']
        When: プリセットを取得する
        Then: すべてのフェーズが返される
        """
        # Act
        phases = PHASE_PRESETS['full-workflow']

        # Assert
        assert 'planning' in phases
        assert 'requirements' in phases
        assert 'evaluation' in phases
        assert len(phases) == 10  # すべてのフェーズ


class TestExternalDocumentIntegration:
    """外部ドキュメント指定機能統合テスト"""

    def test_external_document_valid_markdown(self, tmp_path):
        """
        IT-009: 外部ドキュメント指定 - 正常なMarkdownファイル

        Given: 正常なMarkdownファイルが存在する
        When: 外部ドキュメントとして指定する
        Then: バリデーションが成功する
        """
        # Arrange
        from core.phase_dependencies import validate_external_document

        # 外部要件定義書を作成
        external_doc = tmp_path / 'external_requirements.md'
        external_doc.write_text("""# External Requirements

## Functional Requirements
- FR-001: User authentication
- FR-002: Data validation

## Non-Functional Requirements
- NFR-001: Response time < 1s
""")

        # Act
        result = validate_external_document(str(external_doc))

        # Assert
        assert result['valid'] is True
        assert 'absolute_path' in result
        assert Path(result['absolute_path']).exists()

    def test_external_document_metadata_recording(self, tmp_path):
        """
        IT-009 (拡張): 外部ドキュメント指定時のメタデータ記録

        Given: 外部ドキュメントが指定される
        When: メタデータに記録する
        Then: metadata.jsonにexternal_documentsフィールドが追加される
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/319',
            issue_title='Test Issue #319'
        )

        external_doc = tmp_path / 'external_requirements.md'
        external_doc.write_text("# Requirements")

        manager = MetadataManager(metadata_path)

        # Act: 外部ドキュメント情報を記録
        if 'external_documents' not in manager.data:
            manager.data['external_documents'] = {}
        manager.data['external_documents']['requirements'] = str(external_doc)
        manager.save()

        # Assert
        loaded_manager = MetadataManager(metadata_path)
        assert 'external_documents' in loaded_manager.data
        assert 'requirements' in loaded_manager.data['external_documents']
        assert str(external_doc) in loaded_manager.data['external_documents']['requirements']

    def test_multiple_external_documents(self, tmp_path):
        """
        IT-010: 外部ドキュメント指定 - 複数ドキュメント

        Given: 複数の外部ドキュメントが指定される
        When: メタデータに記録する
        Then: すべてのドキュメント情報が記録される
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/319',
            issue_title='Test Issue #319'
        )

        # 複数の外部ドキュメントを作成
        req_doc = tmp_path / 'external_requirements.md'
        req_doc.write_text("# Requirements")

        design_doc = tmp_path / 'external_design.md'
        design_doc.write_text("# Design")

        manager = MetadataManager(metadata_path)

        # Act: 複数の外部ドキュメント情報を記録
        if 'external_documents' not in manager.data:
            manager.data['external_documents'] = {}
        manager.data['external_documents']['requirements'] = str(req_doc)
        manager.data['external_documents']['design'] = str(design_doc)
        manager.save()

        # Assert
        loaded_manager = MetadataManager(metadata_path)
        assert 'external_documents' in loaded_manager.data
        assert 'requirements' in loaded_manager.data['external_documents']
        assert 'design' in loaded_manager.data['external_documents']


class TestBackwardCompatibility:
    """後方互換性テスト"""

    def test_existing_workflow_phase_all(self, tmp_path):
        """
        IT-012: 既存ワークフロー - --phase all

        Given: すべてのフェーズが定義されている
        When: 全フェーズのステータスを確認する
        Then: すべてのフェーズが存在する
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/319',
            issue_title='Test Issue #319'
        )

        # Act
        manager = MetadataManager(metadata_path)
        all_phases = manager.get_all_phases_status()

        # Assert: すべてのフェーズが存在する
        expected_phases = [
            'planning', 'requirements', 'design', 'test_scenario',
            'implementation', 'test_implementation', 'testing',
            'documentation', 'report', 'evaluation'
        ]

        for phase in expected_phases:
            assert phase in all_phases, f"Phase '{phase}' should exist"

    def test_single_phase_execution_with_dependencies(self, tmp_path):
        """
        IT-013: 既存ワークフロー - 単一フェーズ実行

        Given: 依存フェーズがすべて完了している
        When: implementationフェーズの依存関係チェックを実行する
        Then: valid=Trueが返される
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/319',
            issue_title='Test Issue #319'
        )

        # 依存フェーズをすべて完了
        state.update_phase_status('planning', 'completed')
        state.update_phase_status('requirements', 'completed')
        state.update_phase_status('design', 'completed')
        state.update_phase_status('test_scenario', 'completed')

        manager = MetadataManager(metadata_path)

        # Act
        result = validate_phase_dependencies(
            phase_name='implementation',
            metadata_manager=manager
        )

        # Assert
        assert result['valid'] is True


class TestErrorHandling:
    """エラーハンドリング統合テスト"""

    def test_error_message_clarity_dependency_violation(self, tmp_path):
        """
        IT-014: エラーメッセージの明確性 - 依存関係違反

        Given: 依存フェーズが未完了である
        When: validate_phase_dependencies()を呼び出す
        Then: 明確なエラーメッセージが返される
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/319',
            issue_title='Test Issue #319'
        )

        # planningのみcompleted
        state.update_phase_status('planning', 'completed')

        manager = MetadataManager(metadata_path)

        # Act
        result = validate_phase_dependencies(
            phase_name='implementation',
            metadata_manager=manager,
            skip_check=False,
            ignore_violations=False
        )

        # Assert
        assert result['valid'] is False
        assert 'error' in result
        # エラーメッセージが明確であることを確認
        error_msg = result['error']
        assert 'must be completed' in error_msg
        assert 'before' in error_msg
        assert 'requirements' in error_msg  # 未完了フェーズ名が含まれる

    def test_validation_with_repo_root_security(self, tmp_path):
        """
        IT-011: 外部ドキュメント指定 - バリデーションエラー（セキュリティ）

        Given: リポジトリ外のファイルパスが指定される
        When: validate_external_document()をrepo_root付きで呼び出す
        Then: セキュリティエラーが返される
        """
        # Arrange
        from core.phase_dependencies import validate_external_document

        repo_root = tmp_path / 'repo'
        repo_root.mkdir()

        # リポジトリ外にファイルを作成
        outside_file = tmp_path / 'outside.md'
        outside_file.write_text("# Outside file")

        # Act
        result = validate_external_document(str(outside_file), repo_root=repo_root)

        # Assert
        assert result['valid'] is False
        assert 'error' in result
        assert 'within the repository' in result['error']


class TestMetadataIntegration:
    """メタデータ統合テスト"""

    def test_get_all_phases_status_integration(self, tmp_path):
        """
        メタデータ統合 - get_all_phases_status()の動作確認

        Given: 複数のフェーズステータスが設定されている
        When: get_all_phases_status()を呼び出す
        Then: すべてのフェーズのステータスが返される
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/319',
            issue_title='Test Issue #319'
        )

        # Phase 1-3をcompleted、Phase 4をin_progressに設定
        state.update_phase_status('planning', 'completed')
        state.update_phase_status('requirements', 'completed')
        state.update_phase_status('design', 'completed')
        state.update_phase_status('test_scenario', 'completed')
        state.update_phase_status('implementation', 'in_progress')

        manager = MetadataManager(metadata_path)

        # Act
        result = manager.get_all_phases_status()

        # Assert
        assert isinstance(result, dict)
        assert result['planning'] == 'completed'
        assert result['requirements'] == 'completed'
        assert result['design'] == 'completed'
        assert result['test_scenario'] == 'completed'
        assert result['implementation'] == 'in_progress'
        assert result['test_implementation'] == 'pending'


class TestDependencyValidationEdgeCases:
    """依存関係検証のエッジケーステスト"""

    def test_planning_phase_no_dependencies(self, tmp_path):
        """
        エッジケース: planningフェーズは依存関係がない

        Given: metadata.jsonが初期状態（すべてpending）
        When: planningフェーズの依存関係チェックを実行する
        Then: 常にvalid=Trueが返される
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/319',
            issue_title='Test Issue #319'
        )

        manager = MetadataManager(metadata_path)

        # Act
        result = validate_phase_dependencies(
            phase_name='planning',
            metadata_manager=manager
        )

        # Assert
        assert result['valid'] is True

    def test_evaluation_phase_multiple_dependencies(self, tmp_path):
        """
        エッジケース: evaluationフェーズは最終フェーズで多数の依存関係を持つ

        Given: すべての依存フェーズがcompletedである
        When: evaluationフェーズの依存関係チェックを実行する
        Then: valid=Trueが返される
        """
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/319',
            issue_title='Test Issue #319'
        )

        # reportフェーズまでcompleted
        for phase in ['planning', 'requirements', 'design', 'test_scenario',
                      'implementation', 'test_implementation', 'testing',
                      'documentation', 'report']:
            state.update_phase_status(phase, 'completed')

        manager = MetadataManager(metadata_path)

        # Act
        result = validate_phase_dependencies(
            phase_name='evaluation',
            metadata_manager=manager
        )

        # Assert
        assert result['valid'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
