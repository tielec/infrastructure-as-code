"""Integration Test: 後方互換性（既存ワークフロー Phase 1-7の動作保証）を検証

Issue #324の受け入れ基準を検証：
- AC-004: 既存のワークフロー（Phase 1-7）は引き続き動作する
- NFR-001: 後方互換性の保証
"""
import pytest
import json
from pathlib import Path
from datetime import datetime
from core.workflow_state import WorkflowState


class TestMetadataMigration:
    """metadata.jsonマイグレーションのテスト"""

    def test_migrate_old_metadata_to_new_schema(self, tmp_path):
        """AC-004: Phase 1-7構成のmetadata.jsonが正しくPhase 0-8構成にマイグレーションされる

        テストの意図:
        - 古いスキーマ（Phase 1-7）のmetadata.jsonをロードする
        - WorkflowState.migrate()が自動実行される
        - 'planning'フェーズが追加される
        - 'test_implementation'フェーズが追加される
        - 既存フェーズのデータ（status、started_at、completed_at等）が保持される
        - フェーズの順序が正しい
        """
        # Given: Phase 1-7構成のmetadata.jsonを作成
        metadata_path = tmp_path / 'metadata.json'
        old_metadata = {
            "issue_number": "324",
            "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/324",
            "issue_title": "[FEATURE] 実装フェーズとテストコード実装フェーズの分離",
            "phases": {
                "requirements": {
                    "status": "completed",
                    "started_at": "2025-01-01T00:00:00Z",
                    "completed_at": "2025-01-01T01:00:00Z",
                    "retry_count": 0
                },
                "design": {
                    "status": "completed",
                    "started_at": "2025-01-01T01:00:00Z",
                    "completed_at": "2025-01-01T02:00:00Z",
                    "retry_count": 0
                },
                "test_scenario": {
                    "status": "completed",
                    "started_at": "2025-01-01T02:00:00Z",
                    "completed_at": "2025-01-01T03:00:00Z",
                    "retry_count": 0
                },
                "implementation": {
                    "status": "completed",
                    "started_at": "2025-01-01T03:00:00Z",
                    "completed_at": "2025-01-01T04:00:00Z",
                    "retry_count": 0
                },
                "testing": {
                    "status": "pending",
                    "retry_count": 0
                },
                "documentation": {
                    "status": "pending",
                    "retry_count": 0
                },
                "report": {
                    "status": "pending",
                    "retry_count": 0
                }
            },
            "design_decisions": {
                "implementation_strategy": "EXTEND",
                "test_strategy": "INTEGRATION_BDD",
                "test_code_strategy": "CREATE_TEST"
            },
            "cost_tracking": {
                "total_input_tokens": 150000,
                "total_output_tokens": 50000,
                "total_cost_usd": 2.5
            },
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T04:00:00Z"
        }
        metadata_path.write_text(json.dumps(old_metadata, indent=2, ensure_ascii=False))

        # When: WorkflowStateをロード（マイグレーション自動実行）
        state = WorkflowState(metadata_path)
        migrated = state.migrate()

        # Then: マイグレーションが実行された
        assert migrated is True, "Migration should have been executed"

        # Then: planningフェーズが追加された
        assert 'planning' in state.data['phases'], "planning phase should be added"
        assert state.data['phases']['planning']['status'] == 'pending', \
            "planning phase status should be 'pending'"

        # Then: test_implementationフェーズが追加された
        assert 'test_implementation' in state.data['phases'], \
            "test_implementation phase should be added"
        assert state.data['phases']['test_implementation']['status'] == 'pending', \
            "test_implementation phase status should be 'pending'"

        # Then: 既存フェーズのデータが保持された
        assert state.data['phases']['requirements']['status'] == 'completed', \
            "requirements status should be preserved"
        assert state.data['phases']['requirements']['started_at'] == "2025-01-01T00:00:00Z", \
            "requirements started_at should be preserved"
        assert state.data['phases']['requirements']['completed_at'] == "2025-01-01T01:00:00Z", \
            "requirements completed_at should be preserved"

        assert state.data['phases']['design']['status'] == 'completed', \
            "design status should be preserved"
        assert state.data['phases']['design']['started_at'] == "2025-01-01T01:00:00Z", \
            "design started_at should be preserved"

        # Then: フェーズの順序が正しい
        expected_order = [
            'planning', 'requirements', 'design', 'test_scenario',
            'implementation', 'test_implementation', 'testing',
            'documentation', 'report'
        ]
        actual_order = list(state.data['phases'].keys())
        assert actual_order == expected_order, \
            f"Phase order mismatch: expected {expected_order}, got {actual_order}"

    def test_migrate_preserves_phase_status(self, tmp_path):
        """既存フェーズのステータス（completed、failed等）が保持される

        テストの意図:
        - マイグレーション後も既存フェーズのステータスが変わらない
        - completed、failed、in_progressなどのステータスが正しく保持される
        """
        # Given: 様々なステータスを持つ古いmetadata.json
        metadata_path = tmp_path / 'metadata.json'
        old_metadata = {
            "issue_number": "324",
            "issue_url": "https://github.com/test/repo/issues/324",
            "issue_title": "Test",
            "phases": {
                "requirements": {
                    "status": "completed",
                    "started_at": "2025-01-01T00:00:00Z",
                    "completed_at": "2025-01-01T01:00:00Z",
                    "retry_count": 0
                },
                "design": {
                    "status": "failed",
                    "started_at": "2025-01-01T01:00:00Z",
                    "failed_at": "2025-01-01T01:30:00Z",
                    "retry_count": 2
                },
                "test_scenario": {
                    "status": "pending",
                    "retry_count": 0
                },
                "implementation": {
                    "status": "pending",
                    "retry_count": 0
                },
                "testing": {
                    "status": "pending",
                    "retry_count": 0
                },
                "documentation": {
                    "status": "pending",
                    "retry_count": 0
                },
                "report": {
                    "status": "pending",
                    "retry_count": 0
                }
            },
            "design_decisions": {
                "implementation_strategy": None,
                "test_strategy": None,
                "test_code_strategy": None
            },
            "cost_tracking": {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost_usd": 0.0
            },
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z"
        }
        metadata_path.write_text(json.dumps(old_metadata, indent=2, ensure_ascii=False))

        # When: マイグレーション実行
        state = WorkflowState(metadata_path)
        state.migrate()

        # Then: 既存フェーズのステータスが保持される
        assert state.data['phases']['requirements']['status'] == 'completed', \
            "requirements status should remain 'completed'"
        assert state.data['phases']['design']['status'] == 'failed', \
            "design status should remain 'failed'"
        assert state.data['phases']['design']['retry_count'] == 2, \
            "design retry_count should be preserved"

    def test_migrate_preserves_design_decisions(self, tmp_path):
        """design_decisionsが保持される

        テストの意図:
        - マイグレーション後もdesign_decisions（実装戦略、テスト戦略等）が保持される
        """
        # Given: design_decisionsを持つ古いmetadata.json
        metadata_path = tmp_path / 'metadata.json'
        old_metadata = {
            "issue_number": "324",
            "issue_url": "https://github.com/test/repo/issues/324",
            "issue_title": "Test",
            "phases": {
                "requirements": {"status": "completed", "retry_count": 0},
                "design": {"status": "completed", "retry_count": 0},
                "test_scenario": {"status": "pending", "retry_count": 0},
                "implementation": {"status": "pending", "retry_count": 0},
                "testing": {"status": "pending", "retry_count": 0},
                "documentation": {"status": "pending", "retry_count": 0},
                "report": {"status": "pending", "retry_count": 0}
            },
            "design_decisions": {
                "implementation_strategy": "EXTEND",
                "test_strategy": "INTEGRATION_BDD",
                "test_code_strategy": "CREATE_TEST"
            },
            "cost_tracking": {
                "total_input_tokens": 10000,
                "total_output_tokens": 5000,
                "total_cost_usd": 1.5
            },
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z"
        }
        metadata_path.write_text(json.dumps(old_metadata, indent=2, ensure_ascii=False))

        # When: マイグレーション実行
        state = WorkflowState(metadata_path)
        state.migrate()

        # Then: design_decisionsが保持される
        assert state.data['design_decisions']['implementation_strategy'] == 'EXTEND', \
            "implementation_strategy should be preserved"
        assert state.data['design_decisions']['test_strategy'] == 'INTEGRATION_BDD', \
            "test_strategy should be preserved"
        assert state.data['design_decisions']['test_code_strategy'] == 'CREATE_TEST', \
            "test_code_strategy should be preserved"

    def test_migrate_preserves_cost_tracking(self, tmp_path):
        """cost_trackingが保持される

        テストの意図:
        - マイグレーション後もコスト追跡情報が保持される
        """
        # Given: cost_trackingを持つ古いmetadata.json
        metadata_path = tmp_path / 'metadata.json'
        old_metadata = {
            "issue_number": "324",
            "issue_url": "https://github.com/test/repo/issues/324",
            "issue_title": "Test",
            "phases": {
                "requirements": {"status": "completed", "retry_count": 0},
                "design": {"status": "completed", "retry_count": 0},
                "test_scenario": {"status": "pending", "retry_count": 0},
                "implementation": {"status": "pending", "retry_count": 0},
                "testing": {"status": "pending", "retry_count": 0},
                "documentation": {"status": "pending", "retry_count": 0},
                "report": {"status": "pending", "retry_count": 0}
            },
            "design_decisions": {
                "implementation_strategy": None,
                "test_strategy": None,
                "test_code_strategy": None
            },
            "cost_tracking": {
                "total_input_tokens": 150000,
                "total_output_tokens": 50000,
                "total_cost_usd": 2.5
            },
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z"
        }
        metadata_path.write_text(json.dumps(old_metadata, indent=2, ensure_ascii=False))

        # When: マイグレーション実行
        state = WorkflowState(metadata_path)
        state.migrate()

        # Then: cost_trackingが保持される
        assert state.data['cost_tracking']['total_input_tokens'] == 150000, \
            "total_input_tokens should be preserved"
        assert state.data['cost_tracking']['total_output_tokens'] == 50000, \
            "total_output_tokens should be preserved"
        assert state.data['cost_tracking']['total_cost_usd'] == 2.5, \
            "total_cost_usd should be preserved"

    def test_no_migration_for_new_schema(self, tmp_path):
        """既にPhase 0-8構成の場合、マイグレーションが実行されない

        テストの意図:
        - 最新スキーマのmetadata.jsonの場合、migrate()がFalseを返す
        - データが変更されない
        """
        # Given: Phase 0-8構成のmetadata.json（最新スキーマ）
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='324',
            issue_url='https://github.com/test/repo/issues/324',
            issue_title='Test'
        )

        # データをコピー（変更検知用）
        original_data = json.loads(json.dumps(state.data))

        # When: マイグレーション実行
        migrated = state.migrate()

        # Then: マイグレーションが実行されない
        assert migrated is False, "Migration should not be executed for new schema"

        # Then: データが変更されていない
        assert state.data['phases'] == original_data['phases'], \
            "Phases should not be changed"

    def test_migrate_idempotent(self, tmp_path):
        """マイグレーションが冪等である（複数回実行しても結果が同じ）

        テストの意図:
        - 同じmetadata.jsonに対してmigrate()を複数回実行しても結果が同じ
        - 2回目以降のmigrate()はFalseを返す（変更なし）
        """
        # Given: Phase 1-7構成のmetadata.json
        metadata_path = tmp_path / 'metadata.json'
        old_metadata = {
            "issue_number": "324",
            "issue_url": "https://github.com/test/repo/issues/324",
            "issue_title": "Test",
            "phases": {
                "requirements": {"status": "completed", "retry_count": 0},
                "design": {"status": "completed", "retry_count": 0},
                "test_scenario": {"status": "pending", "retry_count": 0},
                "implementation": {"status": "pending", "retry_count": 0},
                "testing": {"status": "pending", "retry_count": 0},
                "documentation": {"status": "pending", "retry_count": 0},
                "report": {"status": "pending", "retry_count": 0}
            },
            "design_decisions": {
                "implementation_strategy": None,
                "test_strategy": None,
                "test_code_strategy": None
            },
            "cost_tracking": {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost_usd": 0.0
            },
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z"
        }
        metadata_path.write_text(json.dumps(old_metadata, indent=2, ensure_ascii=False))

        # When: 1回目のマイグレーション
        state = WorkflowState(metadata_path)
        migrated1 = state.migrate()
        data_after_first_migration = json.loads(json.dumps(state.data))

        # When: 2回目のマイグレーション
        migrated2 = state.migrate()
        data_after_second_migration = json.loads(json.dumps(state.data))

        # Then: 1回目はTrue、2回目はFalse
        assert migrated1 is True, "First migration should return True"
        assert migrated2 is False, "Second migration should return False"

        # Then: データが同じ
        assert data_after_first_migration == data_after_second_migration, \
            "Data should be the same after multiple migrations"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
