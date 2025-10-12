"""
Unit tests for common/error_handler.py

Test Scenarios:
- カスタム例外クラスの動作確認
- エラーメッセージの整形確認
- ErrorHandler クラスの機能確認
"""
import pytest
from common.error_handler import (
    WorkflowError,
    GitOperationError,
    GitBranchError,
    GitCommitError,
    GitPushError,
    GitHubAPIError,
    ClaudeAPIError,
    PhaseExecutionError,
    ValidationError,
    DependencyError,
    MetadataError,
    ErrorHandler
)


class TestWorkflowError:
    """WorkflowError 基底例外クラスのテスト"""

    def test_workflow_error_basic(self):
        """基本的な例外の作成と表示"""
        # Given: エラーメッセージ
        message = "Test error message"

        # When: WorkflowErrorを作成
        error = WorkflowError(message)

        # Then: エラーメッセージが正しく設定される
        assert str(error) == message
        assert error.message == message
        assert error.details is None
        assert error.original_exception is None

    def test_workflow_error_with_details(self):
        """詳細情報を持つ例外"""
        # Given: エラーメッセージと詳細情報
        message = "Test error"
        details = {"key": "value", "number": 123}

        # When: WorkflowErrorを作成
        error = WorkflowError(message, details=details)

        # Then: 詳細情報が設定される
        assert error.message == message
        assert error.details == details

    def test_workflow_error_with_original_exception(self):
        """元の例外を保持する例外"""
        # Given: 元の例外
        original = ValueError("Original error")

        # When: WorkflowErrorを作成
        error = WorkflowError("Wrapped error", original_exception=original)

        # Then: 元の例外が保持される
        assert error.original_exception is original
        assert isinstance(error.original_exception, ValueError)


class TestGitErrors:
    """Git関連例外クラスのテスト"""

    def test_git_operation_error(self):
        """GitOperationError の作成"""
        # Given: エラーメッセージ
        message = "Git operation failed"

        # When: GitOperationErrorを作成
        error = GitOperationError(message)

        # Then: WorkflowErrorを継承している
        assert isinstance(error, WorkflowError)
        assert str(error) == message

    def test_git_branch_error(self):
        """GitBranchError の作成"""
        # Given: エラーメッセージと詳細情報
        message = "Branch creation failed"
        details = {"branch": "feature-branch"}

        # When: GitBranchErrorを作成
        error = GitBranchError(message, details=details)

        # Then: 正しく設定される
        assert isinstance(error, GitOperationError)
        assert error.details["branch"] == "feature-branch"

    def test_git_commit_error(self):
        """GitCommitError の作成"""
        # Given: エラーメッセージ
        message = "Commit failed"

        # When: GitCommitErrorを作成
        error = GitCommitError(message)

        # Then: 正しく設定される
        assert isinstance(error, GitOperationError)
        assert str(error) == message

    def test_git_push_error(self):
        """GitPushError の作成"""
        # Given: エラーメッセージ
        message = "Push failed"

        # When: GitPushErrorを作成
        error = GitPushError(message)

        # Then: 正しく設定される
        assert isinstance(error, GitOperationError)
        assert str(error) == message


class TestGitHubAPIError:
    """GitHubAPIError 例外クラスのテスト"""

    def test_github_api_error_basic(self):
        """GitHubAPIError の基本動作"""
        # Given: エラーメッセージ
        message = "GitHub API request failed"

        # When: GitHubAPIErrorを作成
        error = GitHubAPIError(message)

        # Then: 正しく設定される
        assert isinstance(error, WorkflowError)
        assert str(error) == message

    def test_github_api_error_with_details(self):
        """GitHubAPIError に詳細情報を設定"""
        # Given: エラーメッセージと詳細情報
        message = "API rate limit exceeded"
        details = {"rate_limit": 5000, "remaining": 0}

        # When: GitHubAPIErrorを作成
        error = GitHubAPIError(message, details=details)

        # Then: 詳細情報が設定される
        assert error.details["rate_limit"] == 5000
        assert error.details["remaining"] == 0


class TestClaudeAPIError:
    """ClaudeAPIError 例外クラスのテスト"""

    def test_claude_api_error(self):
        """ClaudeAPIError の基本動作"""
        # Given: エラーメッセージ
        message = "Claude API request failed"

        # When: ClaudeAPIErrorを作成
        error = ClaudeAPIError(message)

        # Then: 正しく設定される
        assert isinstance(error, WorkflowError)
        assert str(error) == message


class TestPhaseErrors:
    """Phase関連例外クラスのテスト"""

    def test_phase_execution_error(self):
        """PhaseExecutionError の作成"""
        # Given: エラーメッセージ
        message = "Phase execution failed"

        # When: PhaseExecutionErrorを作成
        error = PhaseExecutionError(message)

        # Then: 正しく設定される
        assert isinstance(error, WorkflowError)
        assert str(error) == message

    def test_validation_error(self):
        """ValidationError の作成"""
        # Given: エラーメッセージ
        message = "Validation failed"

        # When: ValidationErrorを作成
        error = ValidationError(message)

        # Then: 正しく設定される
        assert isinstance(error, WorkflowError)
        assert str(error) == message

    def test_dependency_error(self):
        """DependencyError の作成"""
        # Given: エラーメッセージと詳細情報
        message = "Dependency check failed"
        details = {"missing_phases": ["planning", "requirements"]}

        # When: DependencyErrorを作成
        error = DependencyError(message, details=details)

        # Then: 正しく設定される
        assert isinstance(error, WorkflowError)
        assert error.details["missing_phases"] == ["planning", "requirements"]

    def test_metadata_error(self):
        """MetadataError の作成"""
        # Given: エラーメッセージ
        message = "Metadata operation failed"

        # When: MetadataErrorを作成
        error = MetadataError(message)

        # Then: 正しく設定される
        assert isinstance(error, WorkflowError)
        assert str(error) == message


class TestErrorHandler:
    """ErrorHandler クラスのテスト"""

    def test_wrap_exception_basic(self):
        """基本的な例外のラップ"""
        # Given: 元の例外
        original_error = ValueError("Original error")

        # When: ErrorHandlerでラップ
        wrapped = ErrorHandler.wrap_exception(
            exception=original_error,
            error_class=WorkflowError,
            message="Wrapped error"
        )

        # Then: 正しくラップされる
        assert isinstance(wrapped, WorkflowError)
        assert wrapped.message == "Wrapped error"
        assert wrapped.original_exception is original_error

    def test_wrap_exception_with_details(self):
        """詳細情報付きで例外をラップ"""
        # Given: 元の例外と詳細情報
        original_error = RuntimeError("Runtime error")
        details = {"context": "test_context", "phase": "planning"}

        # When: ErrorHandlerでラップ
        wrapped = ErrorHandler.wrap_exception(
            exception=original_error,
            error_class=PhaseExecutionError,
            message="Phase failed",
            details=details
        )

        # Then: 正しくラップされる
        assert isinstance(wrapped, PhaseExecutionError)
        assert wrapped.details == details

    def test_format_error_message_basic(self):
        """基本的なエラーメッセージのフォーマット"""
        # Given: WorkflowError
        error = WorkflowError("Test error")

        # When: エラーメッセージをフォーマット
        formatted = ErrorHandler.format_error_message(error)

        # Then: フォーマットされたメッセージが返される
        assert "WorkflowError" in formatted
        assert "Test error" in formatted

    def test_format_error_message_with_details(self):
        """詳細情報付きエラーメッセージのフォーマット"""
        # Given: 詳細情報付きWorkflowError
        error = GitBranchError(
            "Branch creation failed",
            details={"branch": "feature-branch"}
        )

        # When: エラーメッセージをフォーマット
        formatted = ErrorHandler.format_error_message(error)

        # Then: 詳細情報も含まれる
        assert "GitBranchError" in formatted
        assert "Branch creation failed" in formatted
        assert "branch" in formatted
        assert "feature-branch" in formatted
