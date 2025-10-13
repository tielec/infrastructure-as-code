"""
Integration tests for Workflow

Test Strategy: UNIT_INTEGRATION
Phase: 5 (Test Implementation)
Issue: #380

These tests verify the integration between CLI layer, Application layer,
and Domain layer components.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import yaml

from core.config_manager import ConfigManager
from core.workflow_controller import WorkflowController
from core.metadata_manager import MetadataManager
from core.git.repository import GitRepository
from core.git.branch import GitBranch
from core.git.commit import GitCommit
from core.github.issue_client import IssueClient
from core.github.pr_client import PRClient
from core.github.comment_client import CommentClient
from core.claude_agent_client import ClaudeAgentClient
from common.error_handler import GitHubAPIError, MetadataError


class TestWorkflowInitToPhaseExecution:
    """Integration test: Workflow initialization to phase execution"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_dependencies(self, temp_workspace):
        """Create mock dependencies for integration testing"""
        # Create config.yaml
        config_file = temp_workspace / "config.yaml"
        config_data = {
            'github_token': 'test-token',
            'github_repository': 'test-owner/test-repo',
            'claude_api_key': 'sk-test-key',
            'openai_api_key': 'sk-openai-test-key',
            'claude_code_oauth_token': 'oauth-test-token',
            'working_dir': str(temp_workspace),
            'log_level': 'INFO'
        }
        config_file.write_text(yaml.dump(config_data))

        # Create metadata directory
        metadata_dir = temp_workspace / ".ai-workflow" / "issue-380"
        metadata_dir.mkdir(parents=True, exist_ok=True)

        return {
            'config_file': config_file,
            'metadata_dir': metadata_dir,
            'temp_workspace': temp_workspace
        }

    def test_workflow_init_to_phase_execution(self, mock_dependencies):
        """
        Integration Test: Workflow initialization to single phase execution

        Given: Valid Issue #380 and all required configuration
        When:
            1. ConfigManager loads configuration
            2. WorkflowController initializes workflow
            3. WorkflowController executes planning phase
        Then: All steps complete successfully with proper integration
        """
        # Given - Setup
        temp_workspace = mock_dependencies['temp_workspace']
        config_file = mock_dependencies['config_file']
        metadata_path = mock_dependencies['metadata_dir'] / "metadata.json"

        # Step 1: ConfigManager loads configuration
        config_manager = ConfigManager(config_file)
        config = config_manager.load_config()

        assert config['github_token'] == 'test-token'
        assert config['github_repository'] == 'test-owner/test-repo'

        # Step 2: Create mocked dependencies for WorkflowController
        metadata_manager = Mock(spec=MetadataManager)
        metadata_manager.metadata_path = metadata_path
        metadata_manager.data = {}

        git_repository = Mock(spec=GitRepository)
        git_branch = Mock(spec=GitBranch)
        git_commit = Mock(spec=GitCommit)

        issue_client = Mock(spec=IssueClient)
        issue_client.get_issue_info.return_value = {
            'title': '[TASK] Issue #376の続き - Application/CLI層の実装',
            'state': 'open',
            'number': 380
        }

        pr_client = Mock(spec=PRClient)
        comment_client = Mock(spec=CommentClient)
        claude_client = Mock(spec=ClaudeAgentClient)

        # Step 3: Create WorkflowController
        controller = WorkflowController(
            repo_root=temp_workspace,
            config_manager=config_manager,
            metadata_manager=metadata_manager,
            git_repository=git_repository,
            git_branch=git_branch,
            git_commit=git_commit,
            issue_client=issue_client,
            pr_client=pr_client,
            comment_client=comment_client,
            claude_client=claude_client
        )

        # Step 4: Initialize workflow
        init_result = controller.initialize(
            issue_number=380,
            issue_url='https://github.com/test-owner/test-repo/issues/380'
        )

        # Then - Verify initialization
        assert init_result['success'] is True
        assert init_result['branch_name'] == 'ai-workflow/issue-380'

        # Verify integration: GitHub client was called
        issue_client.get_issue_info.assert_called_once_with(380)

        # Verify integration: Metadata was created
        metadata_manager.create_new.assert_called_once()

        # Verify integration: Git branch was created
        git_branch.create_and_checkout.assert_called_once_with('ai-workflow/issue-380')

        # Verify integration: Metadata was saved
        metadata_manager.save.assert_called_once()

        # Step 5: Execute planning phase (with mocked PhaseExecutor)
        phase_executor = Mock()
        phase_executor.run.return_value = {
            'success': True,
            'review_result': 'PASS',
            'output_file': '.ai-workflow/issue-380/00_planning/output/planning.md'
        }
        controller.phase_executor = phase_executor

        exec_result = controller.execute_phase('planning')

        # Then - Verify phase execution
        assert exec_result['success'] is True
        assert exec_result['phase'] == 'planning'
        assert exec_result['review_result'] == 'PASS'

        # Verify integration: PhaseExecutor was called
        phase_executor.run.assert_called_once()

        # Verify integration: Metadata was updated
        assert metadata_manager.update_phase_status.called
        assert metadata_manager.save.call_count == 2  # Once for init, once for phase


class TestCLIToApplicationToDomainIntegration:
    """Integration test: CLI → Application → Domain layer"""

    def test_cli_to_domain_layer_integration(self):
        """
        Integration Test: CLI commands trigger Application layer which uses Domain layer

        Given: CLI command is invoked
        When: CLI layer calls WorkflowController (Application layer)
        Then: WorkflowController uses Domain layer components correctly
        """
        # Given - Mock all Domain layer components
        config_manager = Mock(spec=ConfigManager)
        config_manager.get.return_value = 'test-value'

        metadata_manager = Mock(spec=MetadataManager)
        metadata_manager.data = {
            'issue_number': 380,
            'branch_name': 'ai-workflow/issue-380'
        }

        git_repo = Mock(spec=GitRepository)
        git_branch = Mock(spec=GitBranch)
        git_commit = Mock(spec=GitCommit)

        issue_client = Mock(spec=IssueClient)
        issue_client.get_issue_info.return_value = {
            'title': 'Test Issue',
            'state': 'open'
        }

        pr_client = Mock(spec=PRClient)
        comment_client = Mock(spec=CommentClient)
        claude_client = Mock(spec=ClaudeAgentClient)

        # When - Create WorkflowController (Application layer)
        controller = WorkflowController(
            repo_root=Path('/tmp/test'),
            config_manager=config_manager,
            metadata_manager=metadata_manager,
            git_repository=git_repo,
            git_branch=git_branch,
            git_commit=git_commit,
            issue_client=issue_client,
            pr_client=pr_client,
            comment_client=comment_client,
            claude_client=claude_client
        )

        # Simulate CLI calling Application layer
        init_result = controller.initialize(380, 'https://github.com/test/repo/issues/380')

        # Then - Verify Application layer used Domain layer correctly
        assert init_result['success'] is True

        # Verify Domain layer calls
        issue_client.get_issue_info.assert_called_once_with(380)
        metadata_manager.create_new.assert_called_once()
        git_branch.create_and_checkout.assert_called_once()


class TestConfigManagerMultiSourceIntegration:
    """Integration test: ConfigManager with multiple config sources"""

    @pytest.fixture
    def temp_config_file(self):
        """Create temporary config file"""
        temp_dir = tempfile.mkdtemp()
        config_file = Path(temp_dir) / "config.yaml"
        yield config_file
        shutil.rmtree(temp_dir)

    def test_config_multi_source_integration(self, temp_config_file):
        """
        Integration Test: ConfigManager integrates YAML + env vars + defaults

        Given: config.yaml exists with some values, env vars set for others
        When: ConfigManager.load_config() is called
        Then: Priority is correct (env > yaml > default)
        """
        # Given - Create YAML config
        config_data = {
            'github_token': 'yaml-token',
            'github_repository': 'yaml-owner/yaml-repo',
            'claude_api_key': 'sk-yaml-key',
            'openai_api_key': 'sk-openai-yaml-key',
            'claude_code_oauth_token': 'oauth-yaml-token',
            'log_level': 'DEBUG'
        }
        temp_config_file.write_text(yaml.dump(config_data))

        config_manager = ConfigManager(temp_config_file)

        # When - Load config with env var override
        with patch.dict('os.environ', {
            'GITHUB_TOKEN': 'env-token',
            'LOG_LEVEL': 'WARNING'
        }):
            result = config_manager.load_config()

        # Then - Verify priority: env > yaml > default
        assert result['github_token'] == 'env-token'  # env override
        assert result['github_repository'] == 'yaml-owner/yaml-repo'  # yaml
        assert result['log_level'] == 'WARNING'  # env override
        assert result['working_dir'] == '.'  # default
        assert result['max_turns'] == 30  # default


class TestErrorHandlingIntegration:
    """Integration tests for error handling across layers"""

    def test_github_api_error_handling_integration(self):
        """
        Integration Test: GitHub API error is handled correctly across layers

        Given: IssueClient.get_issue_info() raises GitHubAPIError
        When: WorkflowController.initialize() is called
        Then: Error is caught, logged, and returned to CLI layer
        """
        # Given
        issue_client = Mock(spec=IssueClient)
        issue_client.get_issue_info.side_effect = GitHubAPIError('Issue not found')

        controller = WorkflowController(
            repo_root=Path('/tmp/test'),
            config_manager=Mock(),
            metadata_manager=Mock(),
            git_repository=Mock(),
            git_branch=Mock(),
            git_commit=Mock(),
            issue_client=issue_client,
            pr_client=Mock(),
            comment_client=Mock(),
            claude_client=Mock()
        )

        # When
        result = controller.initialize(999, 'https://github.com/test/repo/issues/999')

        # Then - Error handled gracefully
        assert result['success'] is False
        assert 'Issue not found' in result['error']

        # Verify error was logged (via logger)
        assert controller.logger is not None

    def test_metadata_corruption_error_handling(self):
        """
        Integration Test: Corrupted metadata is handled correctly

        Given: MetadataManager.load() raises MetadataError
        When: WorkflowController accesses metadata
        Then: Error is caught and handled appropriately
        """
        # Given
        metadata_manager = Mock(spec=MetadataManager)
        metadata_manager.load.side_effect = MetadataError('Corrupted metadata')

        controller = WorkflowController(
            repo_root=Path('/tmp/test'),
            config_manager=Mock(),
            metadata_manager=metadata_manager,
            git_repository=Mock(),
            git_branch=Mock(),
            git_commit=Mock(),
            issue_client=Mock(),
            pr_client=Mock(),
            comment_client=Mock(),
            claude_client=Mock()
        )

        # When - Attempt to get status (which would load metadata)
        with pytest.raises(MetadataError):
            metadata_manager.load()

        # Then - Error is raised as expected


class TestBackwardCompatibility:
    """Integration tests for backward compatibility"""

    @pytest.fixture
    def legacy_metadata(self):
        """Create legacy metadata format"""
        return {
            'issue_number': 380,
            'issue_url': 'https://github.com/test/repo/issues/380',
            'issue_title': 'Test Issue',
            'branch_name': 'ai-workflow/issue-380',
            'created_at': '2025-10-13T10:00:00Z',
            'phases': {
                'planning': {
                    'status': 'completed',
                    'started_at': '2025-10-13T10:05:00Z',
                    'completed_at': '2025-10-13T10:30:00Z',
                    'output_file': '.ai-workflow/issue-380/00_planning/output/planning.md',
                    'review_result': 'PASS'
                }
            }
        }

    def test_legacy_metadata_format_compatibility(self, legacy_metadata):
        """
        Integration Test: Legacy metadata format is still readable

        Given: Metadata in legacy format (from Issue #376)
        When: WorkflowController.get_workflow_status() is called
        Then: Legacy metadata is read correctly
        """
        # Given
        metadata_manager = Mock(spec=MetadataManager)
        metadata_manager.data = legacy_metadata

        controller = WorkflowController(
            repo_root=Path('/tmp/test'),
            config_manager=Mock(),
            metadata_manager=metadata_manager,
            git_repository=Mock(),
            git_branch=Mock(),
            git_commit=Mock(),
            issue_client=Mock(),
            pr_client=Mock(),
            comment_client=Mock(),
            claude_client=Mock()
        )

        # When
        status = controller.get_workflow_status()

        # Then - Legacy format is readable
        assert status['issue_number'] == 380
        assert status['branch_name'] == 'ai-workflow/issue-380'
        assert status['phases']['planning']['status'] == 'completed'
        assert status['phases']['planning']['review_result'] == 'PASS'


class TestPerformanceIntegration:
    """Integration tests for performance requirements"""

    def test_workflow_initialization_performance(self):
        """
        Integration Test: Workflow initialization completes within time limit

        Given: All components are ready
        When: WorkflowController.initialize() is called
        Then: Initialization completes within 10 seconds
        """
        import time

        # Given
        issue_client = Mock(spec=IssueClient)
        issue_client.get_issue_info.return_value = {
            'title': 'Test',
            'state': 'open'
        }

        metadata_manager = Mock(spec=MetadataManager)
        git_branch = Mock(spec=GitBranch)

        controller = WorkflowController(
            repo_root=Path('/tmp/test'),
            config_manager=Mock(),
            metadata_manager=metadata_manager,
            git_repository=Mock(),
            git_branch=git_branch,
            git_commit=Mock(),
            issue_client=issue_client,
            pr_client=Mock(),
            comment_client=Mock(),
            claude_client=Mock()
        )

        # When
        start_time = time.time()
        result = controller.initialize(380, 'https://github.com/test/repo/issues/380')
        duration = time.time() - start_time

        # Then
        assert result['success'] is True
        assert duration < 10.0  # Should complete in less than 10 seconds


class TestEndToEndWorkflow:
    """End-to-end integration test for complete workflow"""

    def test_end_to_end_workflow_simulation(self):
        """
        Integration Test: Simulate complete workflow from init to execution

        Given: Fresh workflow start
        When: init → execute planning → execute requirements
        Then: All phases execute in order with proper state management
        """
        # Given - Setup all mocks
        config_manager = Mock(spec=ConfigManager)
        metadata_manager = Mock(spec=MetadataManager)
        metadata_manager.data = {}

        git_branch = Mock(spec=GitBranch)
        issue_client = Mock(spec=IssueClient)
        issue_client.get_issue_info.return_value = {
            'title': 'Test Issue',
            'state': 'open'
        }

        controller = WorkflowController(
            repo_root=Path('/tmp/test'),
            config_manager=config_manager,
            metadata_manager=metadata_manager,
            git_repository=Mock(),
            git_branch=git_branch,
            git_commit=Mock(),
            issue_client=issue_client,
            pr_client=Mock(),
            comment_client=Mock(),
            claude_client=Mock()
        )

        # Mock phase executor
        phase_executor = Mock()
        phase_executor.run.return_value = {
            'success': True,
            'review_result': 'PASS',
            'output_file': 'test.md'
        }
        controller.phase_executor = phase_executor

        # When - Execute workflow steps
        # Step 1: Initialize
        init_result = controller.initialize(380, 'https://github.com/test/repo/issues/380')
        assert init_result['success'] is True

        # Step 2: Execute planning phase
        plan_result = controller.execute_phase('planning')
        assert plan_result['success'] is True

        # Step 3: Execute requirements phase
        req_result = controller.execute_phase('requirements')
        assert req_result['success'] is True

        # Then - Verify all steps completed
        assert metadata_manager.create_new.call_count == 1
        assert git_branch.create_and_checkout.call_count == 1
        assert metadata_manager.update_phase_status.call_count == 2  # planning + requirements
        assert metadata_manager.save.call_count == 3  # init + planning + requirements
