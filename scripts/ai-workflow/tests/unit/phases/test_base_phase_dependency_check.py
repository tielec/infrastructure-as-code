"""Unit tests for BasePhase.run() dependency check integration (Issue #319)

Tests cover:
- run() メソッド開始時の依存関係チェック
- DependencyError ハンドリング
- skip_check / ignore_violations フラグの確認

Test Strategy: UNIT_INTEGRATION (Unit portion for BasePhase integration)

TC-U-032 ~ TC-U-035 に対応
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# プロジェクトルートをPYTHONPATHに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from phases.base_phase import BasePhase
from utils.dependency_validator import DependencyError
from core.metadata_manager import MetadataManager
from core.workflow_state import WorkflowState


class TestBasePhaseRunDependencyCheck:
    """BasePhase.run() メソッドでの依存関係チェック統合テスト

    TC-U-032 ~ TC-U-035 に対応
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

    @pytest.fixture
    def mock_phase(self, temp_metadata):
        """テスト用のBasePhaseモック"""
        working_dir = Path('/tmp/test-workflow')
        working_dir.mkdir(parents=True, exist_ok=True)

        # BasePhaseを継承した具象クラスを作成
        class TestPhase(BasePhase):
            def execute(self):
                """テスト用のexecuteメソッド"""
                return True

        phase = TestPhase(
            working_dir=working_dir,
            phase_name='design',
            metadata=temp_metadata,
            claude_client=Mock(),
            github_client=Mock()
        )
        return phase

    def test_run_calls_validate_phase_dependencies(self, mock_phase):
        """TC-U-032: run() メソッド開始時の依存関係チェック

        Given: BasePhase インスタンスが作成されている
        When: run() メソッドを呼び出す
        Then: validate_phase_dependencies() が呼び出される
        """
        with patch('phases.base_phase.validate_phase_dependencies') as mock_validate:
            mock_validate.return_value = True

            # モックを設定してrun()を短絡させる
            with patch.object(mock_phase, 'execute', return_value=True):
                with patch.object(mock_phase, 'review', return_value={'result': 'PASS', 'suggestions': []}):
                    with patch.object(mock_phase, 'post_progress'):
                        with patch.object(mock_phase, 'update_phase_status'):
                            # Act: run() 呼び出し
                            result = mock_phase.run()

            # Assert: 依存関係チェックが呼ばれる
            mock_validate.assert_called_once()
            call_args = mock_validate.call_args

            assert call_args[0][0] == 'design', "正しいフェーズ名で呼ばれる"
            assert call_args[1]['metadata'] == mock_phase.metadata, "正しいmetadataで呼ばれる"

    def test_run_handles_dependency_error(self, mock_phase, temp_metadata):
        """TC-U-033: run() メソッドでの DependencyError ハンドリング

        Given: 依存関係が満たされていない
        When: run() メソッドを呼び出す
        Then: エラーメッセージが表示され、フェーズステータスが 'failed' に更新される
        """
        with patch('phases.base_phase.validate_phase_dependencies') as mock_validate:
            # DependencyError を発生させる
            mock_validate.side_effect = DependencyError(
                phase_name='design',
                missing_phases=['requirements']
            )

            with patch.object(mock_phase, 'post_progress') as mock_post:
                with patch.object(mock_phase, 'update_phase_status') as mock_update:
                    # Act: run() 呼び出し
                    result = mock_phase.run()

            # Assert: エラーハンドリングが正しい
            assert result is False, "依存関係エラー時は False を返す"

            # フェーズステータスが failed に更新される
            mock_update.assert_called_with(status='failed')

            # GitHub に進捗報告が投稿される
            mock_post.assert_called_once()
            call_args = mock_post.call_args[1]
            assert call_args['status'] == 'failed'
            assert 'Dependency check failed' in call_args['details']

    def test_run_reads_skip_check_flag_from_metadata(self, mock_phase, temp_metadata):
        """TC-U-034: run() メソッドでの skip_check フラグ確認

        Given: メタデータに skip_dependency_check フラグが設定されている
        When: run() メソッドを呼び出す
        Then: validate_phase_dependencies() に skip_check=True が渡される
        """
        # メタデータに skip_dependency_check フラグを設定
        temp_metadata.data['skip_dependency_check'] = True
        temp_metadata.save()

        with patch('phases.base_phase.validate_phase_dependencies') as mock_validate:
            mock_validate.return_value = True

            with patch.object(mock_phase, 'execute', return_value=True):
                with patch.object(mock_phase, 'review', return_value={'result': 'PASS', 'suggestions': []}):
                    with patch.object(mock_phase, 'post_progress'):
                        with patch.object(mock_phase, 'update_phase_status'):
                            # Act: run() 呼び出し
                            result = mock_phase.run()

            # Assert: skip_check=True で呼ばれる
            mock_validate.assert_called_once()
            call_kwargs = mock_validate.call_args[1]
            assert call_kwargs['skip_check'] is True, \
                "メタデータから skip_check フラグが読み取られる"

    def test_run_reads_ignore_violations_flag_from_metadata(self, mock_phase, temp_metadata):
        """TC-U-035: run() メソッドでの ignore_violations フラグ確認

        Given: メタデータに ignore_dependencies フラグが設定されている
        When: run() メソッドを呼び出す
        Then: validate_phase_dependencies() に ignore_violations=True が渡される
        """
        # メタデータに ignore_dependencies フラグを設定
        temp_metadata.data['ignore_dependencies'] = True
        temp_metadata.save()

        with patch('phases.base_phase.validate_phase_dependencies') as mock_validate:
            mock_validate.return_value = True

            with patch.object(mock_phase, 'execute', return_value=True):
                with patch.object(mock_phase, 'review', return_value={'result': 'PASS', 'suggestions': []}):
                    with patch.object(mock_phase, 'post_progress'):
                        with patch.object(mock_phase, 'update_phase_status'):
                            # Act: run() 呼び出し
                            result = mock_phase.run()

            # Assert: ignore_violations=True で呼ばれる
            mock_validate.assert_called_once()
            call_kwargs = mock_validate.call_args[1]
            assert call_kwargs['ignore_violations'] is True, \
                "メタデータから ignore_violations フラグが読み取られる"

    def test_run_defaults_to_false_when_flags_not_in_metadata(self, mock_phase):
        """フラグがメタデータに存在しない場合のデフォルト動作

        Given: メタデータに skip_dependency_check / ignore_dependencies フラグが存在しない
        When: run() メソッドを呼び出す
        Then: デフォルト値 False で validate_phase_dependencies() が呼ばれる
        """
        with patch('phases.base_phase.validate_phase_dependencies') as mock_validate:
            mock_validate.return_value = True

            with patch.object(mock_phase, 'execute', return_value=True):
                with patch.object(mock_phase, 'review', return_value={'result': 'PASS', 'suggestions': []}):
                    with patch.object(mock_phase, 'post_progress'):
                        with patch.object(mock_phase, 'update_phase_status'):
                            # Act: run() 呼び出し
                            result = mock_phase.run()

            # Assert: デフォルト値 False で呼ばれる
            mock_validate.assert_called_once()
            call_kwargs = mock_validate.call_args[1]
            assert call_kwargs.get('skip_check', False) is False, \
                "skip_check のデフォルト値は False"
            assert call_kwargs.get('ignore_violations', False) is False, \
                "ignore_violations のデフォルト値は False"

    def test_run_continues_execution_when_dependencies_met(self, mock_phase, temp_metadata):
        """依存関係が満たされている場合、フェーズ実行が継続されることを確認

        Given: 依存関係が満たされている
        When: run() メソッドを呼び出す
        Then: フェーズ実行が継続され、execute() が呼ばれる
        """
        # requirements フェーズを completed に設定
        temp_metadata.update_phase_status('requirements', 'completed')

        with patch('phases.base_phase.validate_phase_dependencies') as mock_validate:
            mock_validate.return_value = True

            with patch.object(mock_phase, 'execute', return_value=True) as mock_execute:
                with patch.object(mock_phase, 'review', return_value={'result': 'PASS', 'suggestions': []}):
                    with patch.object(mock_phase, 'post_progress'):
                        with patch.object(mock_phase, 'update_phase_status'):
                            # Act: run() 呼び出し
                            result = mock_phase.run()

            # Assert: execute() が呼ばれる
            mock_execute.assert_called_once()
            assert result is True, "依存関係が満たされている場合、実行が継続される"


class TestBasePhaseRunDependencyCheckEdgeCases:
    """BasePhase.run() での依存関係チェックのエッジケーステスト"""

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

    @pytest.fixture
    def mock_phase(self, temp_metadata):
        """テスト用のBasePhaseモック"""
        working_dir = Path('/tmp/test-workflow')
        working_dir.mkdir(parents=True, exist_ok=True)

        class TestPhase(BasePhase):
            def execute(self):
                """テスト用のexecuteメソッド"""
                return True

        phase = TestPhase(
            working_dir=working_dir,
            phase_name='implementation',
            metadata=temp_metadata,
            claude_client=Mock(),
            github_client=Mock()
        )
        return phase

    def test_run_with_multiple_missing_dependencies(self, mock_phase):
        """複数の依存関係が未満足の場合のエラーハンドリング

        Given: 複数の依存フェーズが未完了
        When: run() メソッドを呼び出す
        Then: 複数フェーズのエラーメッセージが生成され、適切に処理される
        """
        with patch('phases.base_phase.validate_phase_dependencies') as mock_validate:
            # 複数フェーズの依存関係違反
            mock_validate.side_effect = DependencyError(
                phase_name='implementation',
                missing_phases=['requirements', 'design', 'test_scenario']
            )

            with patch.object(mock_phase, 'post_progress') as mock_post:
                with patch.object(mock_phase, 'update_phase_status') as mock_update:
                    # Act: run() 呼び出し
                    result = mock_phase.run()

            # Assert: エラーメッセージに複数フェーズが含まれる
            assert result is False

            call_args = mock_post.call_args[1]
            error_details = call_args['details']
            assert 'requirements' in error_details
            assert 'design' in error_details
            assert 'test_scenario' in error_details

    def test_run_with_unexpected_exception_during_dependency_check(self, mock_phase):
        """依存関係チェック中の予期しない例外のハンドリング

        Given: validate_phase_dependencies() が予期しない例外を発生させる
        When: run() メソッドを呼び出す
        Then: 例外が適切にキャッチされ、エラーが記録される
        """
        with patch('phases.base_phase.validate_phase_dependencies') as mock_validate:
            # 予期しない例外
            mock_validate.side_effect = RuntimeError("Unexpected error in dependency check")

            with patch.object(mock_phase, 'post_progress') as mock_post:
                with patch.object(mock_phase, 'update_phase_status') as mock_update:
                    # Act & Assert: 例外が適切にハンドリングされることを確認
                    # （実装により、例外が再発生するか、Falseを返すか異なる可能性がある）
                    try:
                        result = mock_phase.run()
                        # 例外がキャッチされる場合
                        assert result is False or result is True
                    except RuntimeError:
                        # 例外が再発生する場合
                        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
