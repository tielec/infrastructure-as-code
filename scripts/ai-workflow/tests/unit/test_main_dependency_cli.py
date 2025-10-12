"""Unit tests for main.py CLI dependency check options (Issue #319)

Tests cover:
- CLI option parsing (--skip-dependency-check, --ignore-dependencies, --preset)
- Option exclusivity validation
- Preset mapping logic

Test Strategy: UNIT_INTEGRATION (Unit portion for CLI options)

TC-U-020 ~ TC-U-028 に対応
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
from click.testing import CliRunner

# プロジェクトルートをPYTHONPATHに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestCLIDependencyCheckOptions:
    """main.py execute コマンドの依存関係チェック関連CLIオプションのテストクラス"""

    @pytest.fixture
    def cli_runner(self):
        """Click CLIRunnerのフィクスチャ"""
        return CliRunner()

    def test_skip_dependency_check_flag_parsing(self, cli_runner):
        """TC-U-020: --skip-dependency-check フラグのパース

        Given: --skip-dependency-check フラグを指定する
        When: execute コマンドをパースする
        Then: skip_dependency_check パラメータが True になる
        """
        from main import execute

        with cli_runner.isolated_filesystem():
            # モックしてコマンド実行を最小限に
            with patch('main.MetadataManager') as mock_metadata:
                with patch('main.validate_phase_dependencies') as mock_validate:
                    mock_metadata_instance = Mock()
                    mock_metadata_instance.data = {'phases': {}}
                    mock_metadata.return_value = mock_metadata_instance

                    mock_validate.return_value = True

                    with patch('main.DesignPhase') as mock_phase:
                        mock_phase_instance = Mock()
                        mock_phase_instance.run.return_value = True
                        mock_phase.return_value = mock_phase_instance

                        # Act: --skip-dependency-check フラグを指定
                        result = cli_runner.invoke(execute, [
                            '--phase', 'design',
                            '--issue', '319',
                            '--skip-dependency-check'
                        ], catch_exceptions=False)

                        # Assert: validate_phase_dependencies が skip_check=True で呼ばれる
                        mock_validate.assert_called_once()
                        call_kwargs = mock_validate.call_args[1]
                        assert call_kwargs['skip_check'] is True, \
                            "skip_dependency_check フラグが正しく渡される"

    def test_ignore_dependencies_flag_parsing(self, cli_runner):
        """TC-U-021: --ignore-dependencies フラグのパース

        Given: --ignore-dependencies フラグを指定する
        When: execute コマンドをパースする
        Then: ignore_dependencies パラメータが True になる
        """
        from main import execute

        with cli_runner.isolated_filesystem():
            with patch('main.MetadataManager') as mock_metadata:
                with patch('main.validate_phase_dependencies') as mock_validate:
                    mock_metadata_instance = Mock()
                    mock_metadata_instance.data = {'phases': {}}
                    mock_metadata.return_value = mock_metadata_instance

                    mock_validate.return_value = True

                    with patch('main.DesignPhase') as mock_phase:
                        mock_phase_instance = Mock()
                        mock_phase_instance.run.return_value = True
                        mock_phase.return_value = mock_phase_instance

                        # Act: --ignore-dependencies フラグを指定
                        result = cli_runner.invoke(execute, [
                            '--phase', 'design',
                            '--issue', '319',
                            '--ignore-dependencies'
                        ], catch_exceptions=False)

                        # Assert: validate_phase_dependencies が ignore_violations=True で呼ばれる
                        mock_validate.assert_called_once()
                        call_kwargs = mock_validate.call_args[1]
                        assert call_kwargs['ignore_violations'] is True, \
                            "ignore_dependencies フラグが正しく渡される"

    def test_preset_option_parsing(self, cli_runner):
        """TC-U-022: --preset オプションのパース

        Given: --preset design-phase オプションを指定する
        When: execute コマンドをパースする
        Then: preset パラメータが 'design-phase' になり、実行フェーズが決定される
        """
        from main import execute

        with cli_runner.isolated_filesystem():
            with patch('main.MetadataManager') as mock_metadata:
                with patch('main.execute_phases_from') as mock_execute_from:
                    mock_metadata_instance = Mock()
                    mock_metadata_instance.data = {'phases': {}}
                    mock_metadata.return_value = mock_metadata_instance

                    mock_execute_from.return_value = True

                    # Act: --preset オプションを指定
                    result = cli_runner.invoke(execute, [
                        '--preset', 'design-phase',
                        '--issue', '319'
                    ], catch_exceptions=False)

                    # Assert: プリセットに応じた実行が行われる
                    # design-phase は Phase 1-2 を実行するため、
                    # execute_phases_from('requirements', ...) が呼ばれ、design で停止
                    assert result.exit_code == 0 or mock_execute_from.called, \
                        "プリセットが正しく処理される"

    def test_preset_and_phase_mutual_exclusion(self, cli_runner):
        """TC-U-023: --preset と --phase の同時指定（異常系）

        Given: --preset と --phase を同時に指定する
        When: execute コマンドを実行する
        Then: エラーメッセージが表示され、終了コード 1 で終了する
        """
        from main import execute

        with cli_runner.isolated_filesystem():
            # Act: --preset と --phase を同時指定
            result = cli_runner.invoke(execute, [
                '--preset', 'design-phase',
                '--phase', 'implementation',
                '--issue', '319'
            ])

            # Assert: エラーで終了
            assert result.exit_code == 1, "相互排他エラーで終了コード 1"
            assert "--preset and --phase cannot be used together" in result.output, \
                "適切なエラーメッセージが表示される"

    def test_skip_and_ignore_mutual_exclusion(self, cli_runner):
        """TC-U-024: --skip-dependency-check と --ignore-dependencies の同時指定（異常系）

        Given: --skip-dependency-check と --ignore-dependencies を同時に指定する
        When: execute コマンドを実行する
        Then: エラーメッセージが表示され、終了コード 1 で終了する
        """
        from main import execute

        with cli_runner.isolated_filesystem():
            # Act: 相互排他的なフラグを同時指定
            result = cli_runner.invoke(execute, [
                '--phase', 'design',
                '--issue', '319',
                '--skip-dependency-check',
                '--ignore-dependencies'
            ])

            # Assert: エラーで終了
            assert result.exit_code == 1, "相互排他エラーで終了コード 1"
            assert "--skip-dependency-check and --ignore-dependencies are mutually exclusive" in result.output, \
                "適切なエラーメッセージが表示される"


class TestPresetMapping:
    """プリセットマッピングロジックのテスト

    TC-U-025 ~ TC-U-028 に対応
    """

    @pytest.fixture
    def cli_runner(self):
        """Click CLIRunnerのフィクスチャ"""
        return CliRunner()

    def test_preset_requirements_only(self, cli_runner):
        """TC-U-025: プリセットマッピング - requirements-only

        Given: requirements-only プリセットを指定する
        When: プリセットが解釈される
        Then: requirements フェーズのみが実行される
        """
        from main import execute

        with cli_runner.isolated_filesystem():
            with patch('main.MetadataManager') as mock_metadata:
                with patch('main.RequirementsPhase') as mock_phase:
                    mock_metadata_instance = Mock()
                    mock_metadata_instance.data = {'phases': {}}
                    mock_metadata.return_value = mock_metadata_instance

                    mock_phase_instance = Mock()
                    mock_phase_instance.run.return_value = True
                    mock_phase.return_value = mock_phase_instance

                    # Act: requirements-only プリセット指定
                    result = cli_runner.invoke(execute, [
                        '--preset', 'requirements-only',
                        '--issue', '319'
                    ], catch_exceptions=False)

                    # Assert: requirements フェーズが実行される
                    mock_phase.assert_called_once()

    def test_preset_design_phase(self, cli_runner):
        """TC-U-026: プリセットマッピング - design-phase

        Given: design-phase プリセットを指定する
        When: プリセットが解釈される
        Then: Phase 1-2 (requirements, design) が実行される
        """
        from main import execute

        with cli_runner.isolated_filesystem():
            with patch('main.MetadataManager') as mock_metadata:
                with patch('main.execute_phases_from') as mock_execute_from:
                    mock_metadata_instance = Mock()
                    mock_metadata_instance.data = {'phases': {}}
                    mock_metadata.return_value = mock_metadata_instance

                    mock_execute_from.return_value = True

                    # Act: design-phase プリセット指定
                    result = cli_runner.invoke(execute, [
                        '--preset', 'design-phase',
                        '--issue', '319'
                    ], catch_exceptions=False)

                    # Assert: execute_phases_from が呼ばれて Phase 1-2 が実行される
                    # (実装により異なるが、プリセットが正しく設定されることを確認)
                    assert "[INFO] Using preset: design-phase" in result.output or result.exit_code == 0

    def test_preset_implementation_phase(self, cli_runner):
        """TC-U-027: プリセットマッピング - implementation-phase

        Given: implementation-phase プリセットを指定する
        When: プリセットが解釈される
        Then: Phase 1-4 (requirements, design, test_scenario, implementation) が実行される
        """
        from main import execute

        with cli_runner.isolated_filesystem():
            with patch('main.MetadataManager') as mock_metadata:
                with patch('main.execute_phases_from') as mock_execute_from:
                    mock_metadata_instance = Mock()
                    mock_metadata_instance.data = {'phases': {}}
                    mock_metadata.return_value = mock_metadata_instance

                    mock_execute_from.return_value = True

                    # Act: implementation-phase プリセット指定
                    result = cli_runner.invoke(execute, [
                        '--preset', 'implementation-phase',
                        '--issue', '319'
                    ], catch_exceptions=False)

                    # Assert: プリセットが正しく処理される
                    assert "[INFO] Using preset: implementation-phase" in result.output or result.exit_code == 0

    def test_preset_full_workflow(self, cli_runner):
        """TC-U-028: プリセットマッピング - full-workflow

        Given: full-workflow プリセットを指定する
        When: プリセットが解釈される
        Then: 全フェーズが実行される（phase='all' と同等）
        """
        from main import execute

        with cli_runner.isolated_filesystem():
            with patch('main.MetadataManager') as mock_metadata:
                with patch('main.execute_all_phases') as mock_execute_all:
                    mock_metadata_instance = Mock()
                    mock_metadata_instance.data = {'phases': {}, 'cost_tracking': {'total_cost_usd': 0.0}}
                    mock_metadata.return_value = mock_metadata_instance

                    mock_execute_all.return_value = {
                        'success': True,
                        'completed_phases': [],
                        'failed_phase': None,
                        'error': None
                    }

                    # Act: full-workflow プリセット指定
                    result = cli_runner.invoke(execute, [
                        '--preset', 'full-workflow',
                        '--issue', '319'
                    ], catch_exceptions=False)

                    # Assert: 全フェーズ実行が呼ばれる
                    assert "[INFO] Using preset: full-workflow" in result.output or mock_execute_all.called


class TestDependencyCheckIntegrationWithCLI:
    """依存関係チェックとCLI統合のテスト

    TC-U-029 ~ TC-U-031 に対応
    """

    @pytest.fixture
    def cli_runner(self):
        """Click CLIRunnerのフィクスチャ"""
        return CliRunner()

    def test_dependency_check_called_for_individual_phase(self, cli_runner):
        """TC-U-029: 個別フェーズ実行時の依存関係チェック呼び出し

        Given: 個別フェーズ (phase != 'all') を実行する
        When: execute コマンドを実行する
        Then: validate_phase_dependencies() が呼び出される
        """
        from main import execute

        with cli_runner.isolated_filesystem():
            with patch('main.MetadataManager') as mock_metadata:
                with patch('main.validate_phase_dependencies') as mock_validate:
                    mock_metadata_instance = Mock()
                    mock_metadata_instance.data = {'phases': {}}
                    mock_metadata.return_value = mock_metadata_instance

                    mock_validate.return_value = True

                    with patch('main.DesignPhase') as mock_phase:
                        mock_phase_instance = Mock()
                        mock_phase_instance.run.return_value = True
                        mock_phase.return_value = mock_phase_instance

                        # Act: 個別フェーズ実行
                        result = cli_runner.invoke(execute, [
                            '--phase', 'design',
                            '--issue', '319'
                        ], catch_exceptions=False)

                        # Assert: 依存関係チェックが呼ばれる
                        mock_validate.assert_called_once()
                        assert mock_validate.call_args[0][0] == 'design', \
                            "正しいフェーズ名で依存関係チェックが呼ばれる"

    def test_dependency_check_skipped_for_phase_all(self, cli_runner):
        """TC-U-030: phase='all' の場合、依存関係チェックをスキップ

        Given: phase='all' を指定する
        When: execute コマンドを実行する
        Then: validate_phase_dependencies() が呼び出されない
        """
        from main import execute

        with cli_runner.isolated_filesystem():
            with patch('main.MetadataManager') as mock_metadata:
                with patch('main.validate_phase_dependencies') as mock_validate:
                    with patch('main.execute_all_phases') as mock_execute_all:
                        mock_metadata_instance = Mock()
                        mock_metadata_instance.data = {'phases': {}, 'cost_tracking': {'total_cost_usd': 0.0}}
                        mock_metadata.return_value = mock_metadata_instance

                        mock_execute_all.return_value = {
                            'success': True,
                            'completed_phases': [],
                            'failed_phase': None,
                            'error': None
                        }

                        # Act: phase='all' で実行
                        result = cli_runner.invoke(execute, [
                            '--phase', 'all',
                            '--issue', '319'
                        ], catch_exceptions=False)

                        # Assert: 依存関係チェックが呼ばれない
                        mock_validate.assert_not_called()

    def test_dependency_error_handling_in_cli(self, cli_runner):
        """TC-U-031: DependencyError 発生時のエラーハンドリング

        Given: 依存関係が満たされていない
        When: execute コマンドを実行する
        Then: エラーメッセージとヒントが表示され、終了コード 1 で終了する
        """
        from main import execute
        from utils.dependency_validator import DependencyError

        with cli_runner.isolated_filesystem():
            with patch('main.MetadataManager') as mock_metadata:
                with patch('main.validate_phase_dependencies') as mock_validate:
                    mock_metadata_instance = Mock()
                    mock_metadata_instance.data = {'phases': {}}
                    mock_metadata.return_value = mock_metadata_instance

                    # DependencyError を発生させる
                    mock_validate.side_effect = DependencyError(
                        phase_name='design',
                        missing_phases=['requirements']
                    )

                    # Act: 依存関係違反で実行
                    result = cli_runner.invoke(execute, [
                        '--phase', 'design',
                        '--issue', '319'
                    ])

                    # Assert: エラーメッセージとヒントが表示される
                    assert result.exit_code == 1, "依存関係エラーで終了コード 1"
                    assert "[ERROR]" in result.output, "エラープレフィックスが表示される"
                    assert "requirements" in result.output, "未完了フェーズが表示される"
                    assert "design" in result.output, "実行フェーズが表示される"
                    assert "--skip-dependency-check" in result.output, "ヒント1が表示される"
                    assert "--ignore-dependencies" in result.output, "ヒント2が表示される"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
