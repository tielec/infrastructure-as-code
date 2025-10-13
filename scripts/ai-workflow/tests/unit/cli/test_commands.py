"""
Unit tests for CLI Commands

Test Strategy: UNIT_INTEGRATION
Phase: 5 (Test Implementation)
Issue: #380
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from click.testing import CliRunner

from cli.commands import cli, init, execute, status, resume


class TestCLIInitCommand:
    """Test CLI init command"""

    def test_cli_init_command_正常系(self):
        """
        Test: init command executes successfully
        Given: Valid issue URL
        When: init command is executed
        Then: Workflow is initialized successfully
        """
        # Given
        runner = CliRunner()
        issue_url = 'https://github.com/tielec/infrastructure-as-code/issues/380'

        # Mock WorkflowController
        with patch('cli.commands._initialize_workflow_controller') as mock_init:
            mock_controller = Mock()
            mock_controller.initialize.return_value = {
                'success': True,
                'branch_name': 'ai-workflow/issue-380',
                'metadata_path': '.ai-workflow/issue-380/metadata.json'
            }
            mock_init.return_value = mock_controller

            # When
            result = runner.invoke(cli, ['init', '--issue-url', issue_url])

            # Then
            assert result.exit_code == 0
            assert '[OK]' in result.output
            assert 'Issue #380' in result.output
            mock_controller.initialize.assert_called_once()

    def test_cli_init_command_invalid_url_異常系(self):
        """
        Test: init command fails with invalid URL
        Given: Invalid Issue URL format
        When: init command is executed
        Then: Error message is displayed
        """
        # Given
        runner = CliRunner()
        invalid_url = 'invalid-url'

        # When
        result = runner.invoke(cli, ['init', '--issue-url', invalid_url])

        # Then
        assert result.exit_code == 1
        assert '[ERROR]' in result.output
        assert 'Invalid Issue URL' in result.output

    def test_cli_init_command_workflow_initialization_failure(self):
        """
        Test: init command handles initialization failure
        Given: WorkflowController.initialize() returns failure
        When: init command is executed
        Then: Error is displayed
        """
        # Given
        runner = CliRunner()
        issue_url = 'https://github.com/tielec/infrastructure-as-code/issues/380'

        with patch('cli.commands._initialize_workflow_controller') as mock_init:
            mock_controller = Mock()
            mock_controller.initialize.return_value = {
                'success': False,
                'error': 'GitHub API error'
            }
            mock_init.return_value = mock_controller

            # When
            result = runner.invoke(cli, ['init', '--issue-url', issue_url])

            # Then
            assert result.exit_code == 1
            assert '[ERROR]' in result.output
            assert 'GitHub API error' in result.output


class TestCLIExecuteCommand:
    """Test CLI execute command"""

    def test_cli_execute_command_single_phase_正常系(self):
        """
        Test: execute command runs single phase successfully
        Given: Valid issue number and phase name
        When: execute command is executed
        Then: Phase executes successfully
        """
        # Given
        runner = CliRunner()
        issue = '380'
        phase = 'planning'

        with patch('cli.commands._initialize_workflow_controller') as mock_init:
            mock_controller = Mock()
            mock_controller.execute_phase.return_value = {
                'success': True,
                'phase': 'planning',
                'review_result': 'PASS'
            }
            mock_init.return_value = mock_controller

            # When
            result = runner.invoke(cli, ['execute', '--issue', issue, '--phase', phase])

            # Then
            assert result.exit_code == 0
            assert '[OK]' in result.output
            assert 'planning' in result.output
            mock_controller.execute_phase.assert_called_once_with(
                'planning',
                skip_dependency_check=False,
                ignore_dependencies=False
            )

    def test_cli_execute_command_all_phases_正常系(self):
        """
        Test: execute command runs all phases successfully
        Given: phase='all'
        When: execute command is executed
        Then: All phases execute successfully
        """
        # Given
        runner = CliRunner()
        issue = '380'
        phase = 'all'

        with patch('cli.commands._initialize_workflow_controller') as mock_init:
            mock_controller = Mock()
            mock_controller.execute_all_phases.return_value = {
                'success': True,
                'completed_phases': ['planning', 'requirements'],
                'failed_phase': None
            }
            mock_init.return_value = mock_controller

            # When
            result = runner.invoke(cli, ['execute', '--issue', issue, '--phase', phase])

            # Then
            assert result.exit_code == 0
            assert '[OK]' in result.output
            mock_controller.execute_all_phases.assert_called_once()

    def test_cli_execute_command_failure_異常系(self):
        """
        Test: execute command handles phase failure
        Given: Phase execution fails
        When: execute command is executed
        Then: Error message is displayed
        """
        # Given
        runner = CliRunner()
        issue = '380'
        phase = 'planning'

        with patch('cli.commands._initialize_workflow_controller') as mock_init:
            mock_controller = Mock()
            mock_controller.execute_phase.return_value = {
                'success': False,
                'error': 'Test error message'
            }
            mock_init.return_value = mock_controller

            # When
            result = runner.invoke(cli, ['execute', '--issue', issue, '--phase', phase])

            # Then
            assert result.exit_code == 1
            assert '[ERROR]' in result.output
            assert 'Test error message' in result.output

    def test_cli_execute_command_with_skip_dependency_check(self):
        """
        Test: execute command with --skip-dependency-check flag
        Given: --skip-dependency-check flag is provided
        When: execute command is executed
        Then: skip_dependency_check=True is passed
        """
        # Given
        runner = CliRunner()
        issue = '380'
        phase = 'planning'

        with patch('cli.commands._initialize_workflow_controller') as mock_init:
            mock_controller = Mock()
            mock_controller.execute_phase.return_value = {
                'success': True,
                'phase': 'planning',
                'review_result': 'PASS'
            }
            mock_init.return_value = mock_controller

            # When
            result = runner.invoke(cli, [
                'execute',
                '--issue', issue,
                '--phase', phase,
                '--skip-dependency-check'
            ])

            # Then
            assert result.exit_code == 0
            mock_controller.execute_phase.assert_called_once_with(
                'planning',
                skip_dependency_check=True,
                ignore_dependencies=False
            )

    def test_cli_execute_command_with_ignore_dependencies(self):
        """
        Test: execute command with --ignore-dependencies flag
        Given: --ignore-dependencies flag is provided
        When: execute command is executed
        Then: ignore_dependencies=True is passed
        """
        # Given
        runner = CliRunner()
        issue = '380'
        phase = 'planning'

        with patch('cli.commands._initialize_workflow_controller') as mock_init:
            mock_controller = Mock()
            mock_controller.execute_phase.return_value = {
                'success': True,
                'phase': 'planning',
                'review_result': 'PASS'
            }
            mock_init.return_value = mock_controller

            # When
            result = runner.invoke(cli, [
                'execute',
                '--issue', issue,
                '--phase', phase,
                '--ignore-dependencies'
            ])

            # Then
            assert result.exit_code == 0
            mock_controller.execute_phase.assert_called_once_with(
                'planning',
                skip_dependency_check=False,
                ignore_dependencies=True
            )


class TestCLIStatusCommand:
    """Test CLI status command"""

    def test_cli_status_command_正常系(self):
        """
        Test: status command displays workflow status
        Given: Metadata contains workflow state
        When: status command is executed
        Then: Status is displayed correctly
        """
        # Given
        runner = CliRunner()
        issue = '380'

        with patch('cli.commands._initialize_workflow_controller') as mock_init:
            mock_controller = Mock()
            mock_controller.get_workflow_status.return_value = {
                'issue_number': 380,
                'branch_name': 'ai-workflow/issue-380',
                'phases': {
                    'planning': {'status': 'completed', 'review_result': 'PASS'},
                    'requirements': {'status': 'in_progress'}
                }
            }
            mock_init.return_value = mock_controller

            # When
            result = runner.invoke(cli, ['status', '--issue', issue])

            # Then
            assert result.exit_code == 0
            assert 'Workflow Status' in result.output
            assert 'Issue #380' in result.output
            assert 'ai-workflow/issue-380' in result.output
            assert 'planning' in result.output
            mock_controller.get_workflow_status.assert_called_once()

    def test_cli_status_command_metadata_not_found(self):
        """
        Test: status command handles metadata not found
        Given: Metadata file doesn't exist
        When: status command is executed
        Then: Error message is displayed
        """
        # Given
        runner = CliRunner()
        issue = '380'

        with patch('cli.commands._initialize_workflow_controller') as mock_init:
            mock_init.side_effect = FileNotFoundError('Metadata not found')

            # When
            result = runner.invoke(cli, ['status', '--issue', issue])

            # Then
            assert result.exit_code == 1
            assert '[ERROR]' in result.output or 'Metadata not found' in result.output


class TestCLIResumeCommand:
    """Test CLI resume command"""

    def test_cli_resume_command_正常系(self):
        """
        Test: resume command resumes workflow
        Given: Workflow was previously interrupted
        When: resume command is executed
        Then: Workflow resumes from last completed phase
        """
        # Given
        runner = CliRunner()
        issue = '380'

        with patch('cli.commands._initialize_workflow_controller') as mock_init:
            mock_controller = Mock()
            mock_controller.get_workflow_status.return_value = {
                'phases': {
                    'planning': {'status': 'completed'},
                    'requirements': {'status': 'failed'}
                }
            }
            mock_controller.execute_all_phases.return_value = {
                'success': True,
                'completed_phases': ['requirements', 'design'],
                'failed_phase': None
            }
            mock_init.return_value = mock_controller

            # When
            result = runner.invoke(cli, ['resume', '--issue', issue])

            # Then
            assert result.exit_code == 0
            assert '[OK]' in result.output
            mock_controller.execute_all_phases.assert_called_once()

    def test_cli_resume_command_with_skip_dependency_check(self):
        """
        Test: resume command with --skip-dependency-check flag
        Given: --skip-dependency-check flag is provided
        When: resume command is executed
        Then: skip_dependency_check=True is passed
        """
        # Given
        runner = CliRunner()
        issue = '380'

        with patch('cli.commands._initialize_workflow_controller') as mock_init:
            mock_controller = Mock()
            mock_controller.get_workflow_status.return_value = {
                'phases': {
                    'planning': {'status': 'completed'}
                }
            }
            mock_controller.execute_all_phases.return_value = {
                'success': True,
                'completed_phases': ['requirements'],
                'failed_phase': None
            }
            mock_init.return_value = mock_controller

            # When
            result = runner.invoke(cli, [
                'resume',
                '--issue', issue,
                '--skip-dependency-check'
            ])

            # Then
            assert result.exit_code == 0
            mock_controller.execute_all_phases.assert_called_once()
            call_kwargs = mock_controller.execute_all_phases.call_args[1]
            assert call_kwargs.get('skip_dependency_check') is True


class TestCLICommandsIntegration:
    """Integration tests for CLI commands"""

    def test_cli_help_command(self):
        """
        Test: CLI help command displays usage
        Given: CLI is invoked with --help
        When: Command is executed
        Then: Help text is displayed
        """
        # Given
        runner = CliRunner()

        # When
        result = runner.invoke(cli, ['--help'])

        # Then
        assert result.exit_code == 0
        assert 'init' in result.output
        assert 'execute' in result.output
        assert 'status' in result.output
        assert 'resume' in result.output

    def test_cli_init_help_command(self):
        """
        Test: init command help displays correct options
        Given: init --help is invoked
        When: Command is executed
        Then: Help text shows --issue-url option
        """
        # Given
        runner = CliRunner()

        # When
        result = runner.invoke(cli, ['init', '--help'])

        # Then
        assert result.exit_code == 0
        assert '--issue-url' in result.output

    def test_cli_execute_help_command(self):
        """
        Test: execute command help displays correct options
        Given: execute --help is invoked
        When: Command is executed
        Then: Help text shows --issue and --phase options
        """
        # Given
        runner = CliRunner()

        # When
        result = runner.invoke(cli, ['execute', '--help'])

        # Then
        assert result.exit_code == 0
        assert '--issue' in result.output
        assert '--phase' in result.output


class TestCLIWorkflowControllerInitialization:
    """Test _initialize_workflow_controller helper function"""

    @patch('cli.commands.ConfigManager')
    @patch('cli.commands.MetadataManager')
    @patch('cli.commands.GitRepository')
    @patch('cli.commands.WorkflowController')
    def test_initialize_workflow_controller_creates_all_dependencies(
        self,
        mock_workflow_controller,
        mock_git_repo,
        mock_metadata,
        mock_config
    ):
        """
        Test: _initialize_workflow_controller creates all dependencies
        Given: Valid issue_number
        When: _initialize_workflow_controller() is called
        Then: All dependencies are created and WorkflowController is instantiated
        """
        # Given
        from cli.commands import _initialize_workflow_controller

        issue_number = 380

        # Mock all dependency constructors
        mock_config_instance = Mock()
        mock_config_instance.load_config.return_value = {
            'working_dir': '.',
            'github_token': 'test-token'
        }
        mock_config.return_value = mock_config_instance

        # When
        with patch('cli.commands.Path'):
            with patch('cli.commands.GitBranch'):
                with patch('cli.commands.GitCommit'):
                    with patch('cli.commands.IssueClient'):
                        with patch('cli.commands.PRClient'):
                            with patch('cli.commands.CommentClient'):
                                with patch('cli.commands.ClaudeAgentClient'):
                                    result = _initialize_workflow_controller(issue_number)

        # Then
        assert result is not None
        mock_workflow_controller.assert_called_once()
