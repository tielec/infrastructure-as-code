"""
Unit tests for WorkflowController

Test Strategy: UNIT_INTEGRATION
Phase: 5 (Test Implementation)
Issue: #380
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

from core.workflow_controller import WorkflowController
from common.error_handler import (
    MetadataError, GitOperationError, GitHubAPIError,
    ClaudeAPIError, WorkflowError
)


class TestWorkflowControllerInit:
    """Test WorkflowController initialization"""

    def test_workflow_controller_init_正常系(self):
        """
        Test: WorkflowController initialization (normal case)
        Given: All required dependencies
        When: WorkflowController is initialized
        Then: Instance is created with correct attributes
        """
        # Given - Create mock dependencies
        repo_root = Path('/tmp/test-repo')
        config_manager = Mock()
        metadata_manager = Mock()
        git_repository = Mock()
        git_branch = Mock()
        git_commit = Mock()
        issue_client = Mock()
        pr_client = Mock()
        comment_client = Mock()
        claude_client = Mock()

        # When
        controller = WorkflowController(
            repo_root=repo_root,
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

        # Then
        assert controller.repo_root == repo_root
        assert controller.config == config_manager
        assert controller.metadata == metadata_manager
        assert controller.git_repo == git_repository
        assert controller.git_branch == git_branch
        assert controller.issue_client == issue_client
        assert controller.PHASE_ORDER == [
            'planning', 'requirements', 'design', 'test_scenario',
            'implementation', 'test_implementation', 'testing',
            'documentation', 'report', 'evaluation'
        ]


class TestWorkflowControllerInitialize:
    """Test WorkflowController.initialize() method"""

    def test_initialize_workflow_正常系(self):
        """
        Test: Workflow initialization succeeds
        Given: Valid issue_number and issue_url
        When: initialize() is called
        Then: Workflow is initialized successfully
        """
        # Given
        issue_number = 380
        issue_url = 'https://github.com/tielec/infrastructure-as-code/issues/380'

        # Mock dependencies
        metadata_manager = Mock()
        git_branch = Mock()
        issue_client = Mock()
        issue_client.get_issue_info.return_value = {
            'title': '[TASK] Issue #376の続き - Application/CLI層の実装',
            'state': 'open'
        }

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
        result = controller.initialize(issue_number, issue_url)

        # Then
        assert result['success'] is True
        assert result['branch_name'] == 'ai-workflow/issue-380'
        assert 'metadata_path' in result
        assert result['error'] is None

        # Verify method calls
        issue_client.get_issue_info.assert_called_once_with(issue_number)
        metadata_manager.create_new.assert_called_once()
        git_branch.create_and_checkout.assert_called_once_with('ai-workflow/issue-380')
        metadata_manager.save.assert_called_once()

    def test_initialize_workflow_github_api_error_異常系(self):
        """
        Test: GitHub API error during initialization
        Given: issue_client.get_issue_info() raises GitHubAPIError
        When: initialize() is called
        Then: Error is handled gracefully
        """
        # Given
        issue_number = 999
        issue_url = 'https://github.com/tielec/infrastructure-as-code/issues/999'

        issue_client = Mock()
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
        result = controller.initialize(issue_number, issue_url)

        # Then
        assert result['success'] is False
        assert 'Issue not found' in result['error']

    def test_initialize_workflow_git_error_異常系(self):
        """
        Test: Git error during branch creation
        Given: git_branch.create_and_checkout() raises GitOperationError
        When: initialize() is called
        Then: Error is handled gracefully
        """
        # Given
        issue_number = 380
        issue_url = 'https://github.com/test/repo/issues/380'

        issue_client = Mock()
        issue_client.get_issue_info.return_value = {'title': 'Test', 'state': 'open'}

        git_branch = Mock()
        git_branch.create_and_checkout.side_effect = GitOperationError('Branch already exists')

        controller = WorkflowController(
            repo_root=Path('/tmp/test'),
            config_manager=Mock(),
            metadata_manager=Mock(),
            git_repository=Mock(),
            git_branch=git_branch,
            git_commit=Mock(),
            issue_client=issue_client,
            pr_client=Mock(),
            comment_client=Mock(),
            claude_client=Mock()
        )

        # When
        result = controller.initialize(issue_number, issue_url)

        # Then
        assert result['success'] is False
        assert 'Branch already exists' in result['error']


class TestWorkflowControllerExecutePhase:
    """Test WorkflowController.execute_phase() method"""

    def test_execute_phase_正常系(self):
        """
        Test: Single phase execution succeeds
        Given: Valid phase_name
        When: execute_phase() is called
        Then: Phase executes successfully
        """
        # Given
        phase_name = 'planning'

        metadata_manager = Mock()
        phase_executor = Mock()
        phase_executor.run.return_value = {
            'success': True,
            'review_result': 'PASS',
            'output_file': '.ai-workflow/issue-380/00_planning/output/planning.md'
        }

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
        controller.phase_executor = phase_executor

        # When
        result = controller.execute_phase(phase_name)

        # Then
        assert result['success'] is True
        assert result['phase'] == 'planning'
        assert result['review_result'] == 'PASS'

        # Verify method calls
        phase_executor.run.assert_called_once()
        metadata_manager.update_phase_status.assert_called_once()
        metadata_manager.save.assert_called_once()

    def test_execute_phase_unknown_phase_異常系(self):
        """
        Test: Unknown phase name raises error
        Given: Invalid phase_name
        When: execute_phase() is called
        Then: WorkflowError is returned
        """
        # Given
        phase_name = 'unknown_phase'

        controller = WorkflowController(
            repo_root=Path('/tmp/test'),
            config_manager=Mock(),
            metadata_manager=Mock(),
            git_repository=Mock(),
            git_branch=Mock(),
            git_commit=Mock(),
            issue_client=Mock(),
            pr_client=Mock(),
            comment_client=Mock(),
            claude_client=Mock()
        )

        # When
        result = controller.execute_phase(phase_name)

        # Then
        assert result['success'] is False
        assert 'Unknown phase' in result['error']

    def test_execute_phase_failure_異常系(self):
        """
        Test: Phase execution fails
        Given: phase_executor.run() returns failure
        When: execute_phase() is called
        Then: Failure is handled gracefully
        """
        # Given
        phase_name = 'planning'

        metadata_manager = Mock()
        phase_executor = Mock()
        phase_executor.run.return_value = {
            'success': False,
            'error': 'Test error'
        }

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
        controller.phase_executor = phase_executor

        # When
        result = controller.execute_phase(phase_name)

        # Then
        assert result['success'] is False
        assert 'error' in result


class TestWorkflowControllerExecuteAllPhases:
    """Test WorkflowController.execute_all_phases() method"""

    def test_execute_all_phases_正常系(self):
        """
        Test: All phases execute successfully
        Given: All phases succeed
        When: execute_all_phases() is called
        Then: All phases complete successfully
        """
        # Given
        phase_executor = Mock()
        phase_executor.run.return_value = {
            'success': True,
            'review_result': 'PASS',
            'output_file': 'test.md'
        }

        controller = WorkflowController(
            repo_root=Path('/tmp/test'),
            config_manager=Mock(),
            metadata_manager=Mock(),
            git_repository=Mock(),
            git_branch=Mock(),
            git_commit=Mock(),
            issue_client=Mock(),
            pr_client=Mock(),
            comment_client=Mock(),
            claude_client=Mock()
        )
        controller.phase_executor = phase_executor

        # When
        result = controller.execute_all_phases()

        # Then
        assert result['success'] is True
        assert len(result['completed_phases']) == 10
        assert result['failed_phase'] is None
        assert 'total_duration' in result

    def test_execute_all_phases_failure_異常系(self):
        """
        Test: Execution stops when a phase fails
        Given: Second phase (requirements) fails
        When: execute_all_phases() is called
        Then: Execution stops after first phase
        """
        # Given
        phase_executor = Mock()

        def phase_side_effect(phase_name, *args, **kwargs):
            if phase_name == 'planning':
                return {
                    'success': True,
                    'review_result': 'PASS',
                    'output_file': 'planning.md'
                }
            else:
                return {
                    'success': False,
                    'error': 'Requirements failed'
                }

        phase_executor.run.side_effect = phase_side_effect

        controller = WorkflowController(
            repo_root=Path('/tmp/test'),
            config_manager=Mock(),
            metadata_manager=Mock(),
            git_repository=Mock(),
            git_branch=Mock(),
            git_commit=Mock(),
            issue_client=Mock(),
            pr_client=Mock(),
            comment_client=Mock(),
            claude_client=Mock()
        )
        controller.phase_executor = phase_executor

        # When
        result = controller.execute_all_phases()

        # Then
        assert result['success'] is False
        assert len(result['completed_phases']) == 1
        assert result['completed_phases'][0] == 'planning'
        assert result['failed_phase'] == 'requirements'
        assert 'Requirements failed' in result['error']

    def test_execute_all_phases_start_from(self):
        """
        Test: Start execution from specific phase
        Given: start_from='requirements'
        When: execute_all_phases(start_from='requirements') is called
        Then: Execution starts from requirements phase
        """
        # Given
        phase_executor = Mock()
        phase_executor.run.return_value = {
            'success': True,
            'review_result': 'PASS',
            'output_file': 'test.md'
        }

        controller = WorkflowController(
            repo_root=Path('/tmp/test'),
            config_manager=Mock(),
            metadata_manager=Mock(),
            git_repository=Mock(),
            git_branch=Mock(),
            git_commit=Mock(),
            issue_client=Mock(),
            pr_client=Mock(),
            comment_client=Mock(),
            claude_client=Mock()
        )
        controller.phase_executor = phase_executor

        # When
        result = controller.execute_all_phases(start_from='requirements')

        # Then
        assert result['success'] is True
        assert 'planning' not in result['completed_phases']
        assert 'requirements' in result['completed_phases']
        assert len(result['completed_phases']) == 9  # All except planning


class TestWorkflowControllerGetWorkflowStatus:
    """Test WorkflowController.get_workflow_status() method"""

    def test_get_workflow_status_正常系(self):
        """
        Test: Get workflow status successfully
        Given: Metadata contains workflow state
        When: get_workflow_status() is called
        Then: Current workflow status is returned
        """
        # Given
        metadata_manager = Mock()
        metadata_manager.data = {
            'issue_number': 380,
            'branch_name': 'ai-workflow/issue-380',
            'phases': {
                'planning': {'status': 'completed'},
                'requirements': {'status': 'in_progress'}
            }
        }

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
        result = controller.get_workflow_status()

        # Then
        assert result['issue_number'] == 380
        assert result['branch_name'] == 'ai-workflow/issue-380'
        assert result['phases']['planning']['status'] == 'completed'
        assert result['phases']['requirements']['status'] == 'in_progress'


class TestWorkflowControllerDependencyInjection:
    """Test dependency injection pattern"""

    def test_all_dependencies_injected(self):
        """
        Test: All dependencies are properly injected
        Given: All dependencies provided to constructor
        When: WorkflowController is created
        Then: All dependencies are accessible
        """
        # Given
        repo_root = Path('/tmp/test')
        config_manager = Mock()
        metadata_manager = Mock()
        git_repository = Mock()
        git_branch = Mock()
        git_commit = Mock()
        issue_client = Mock()
        pr_client = Mock()
        comment_client = Mock()
        claude_client = Mock()

        # When
        controller = WorkflowController(
            repo_root=repo_root,
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

        # Then - Verify all dependencies are injected
        assert controller.repo_root is repo_root
        assert controller.config is config_manager
        assert controller.metadata is metadata_manager
        assert controller.git_repo is git_repository
        assert controller.git_branch is git_branch
        assert controller.git_commit is git_commit
        assert controller.issue_client is issue_client
        assert controller.pr_client is pr_client
        assert controller.comment_client is comment_client
        assert controller.claude_client is claude_client


class TestWorkflowControllerErrorHandling:
    """Test error handling across different scenarios"""

    def test_error_handling_metadata_error(self):
        """
        Test: MetadataError is handled gracefully
        Given: metadata_manager.save() raises MetadataError
        When: execute_phase() is called
        Then: Error is caught and returned
        """
        # Given
        metadata_manager = Mock()
        metadata_manager.save.side_effect = MetadataError('Failed to save metadata')

        phase_executor = Mock()
        phase_executor.run.return_value = {
            'success': True,
            'review_result': 'PASS',
            'output_file': 'test.md'
        }

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
        controller.phase_executor = phase_executor

        # When
        result = controller.execute_phase('planning')

        # Then
        assert result['success'] is False
        assert 'Failed to save metadata' in result['error']
