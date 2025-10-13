"""Error Handler - エラーハンドリングの共通化モジュール

このモジュールは、プロジェクト全体で統一されたエラーハンドリングを提供します。

機能:
    - カスタム例外クラスの定義
    - エラーメッセージの統一
    - エラーリカバリー処理の標準化
    - エラーログの自動記録

使用例:
    >>> from common.error_handler import GitOperationError
    >>> raise GitOperationError("ブランチ作成に失敗しました", details={'branch': 'feature/test'})
"""

from typing import Dict, Any, Optional


class WorkflowError(Exception):
    """ワークフローエラーの基底クラス

    すべてのカスタム例外はこのクラスを継承します。

    Attributes:
        message: エラーメッセージ
        details: エラー詳細情報（辞書）
        original_exception: 元の例外（存在する場合）
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """初期化

        Args:
            message: エラーメッセージ
            details: エラー詳細情報
            original_exception: 元の例外
        """
        self.message = message
        self.details = details or {}
        self.original_exception = original_exception
        super().__init__(message)

    def __str__(self) -> str:
        """文字列表現"""
        result = self.message

        if self.details:
            details_str = ', '.join(f"{k}={v}" for k, v in self.details.items())
            result += f" (Details: {details_str})"

        if self.original_exception:
            result += f" (Caused by: {self.original_exception})"

        return result


class GitOperationError(WorkflowError):
    """Git操作エラー

    Git操作（ブランチ作成、コミット、プッシュ等）で発生したエラー。
    """
    pass


class GitBranchError(GitOperationError):
    """Gitブランチ操作エラー

    ブランチ作成、切り替え等で発生したエラー。
    """
    pass


class GitCommitError(GitOperationError):
    """Gitコミット操作エラー

    コミット作成で発生したエラー。
    """
    pass


class GitPushError(GitOperationError):
    """Gitプッシュ操作エラー

    リモートへのプッシュで発生したエラー。
    """
    pass


class GitHubAPIError(WorkflowError):
    """GitHub API エラー

    GitHub API呼び出しで発生したエラー。
    """
    pass


class ClaudeAPIError(WorkflowError):
    """Claude API エラー

    Claude API呼び出しで発生したエラー。
    """
    pass


class PhaseExecutionError(WorkflowError):
    """フェーズ実行エラー

    フェーズ実行中に発生したエラー。
    """
    pass


class ValidationError(WorkflowError):
    """バリデーションエラー

    入力値や設定の検証で発生したエラー。
    """
    pass


class DependencyError(WorkflowError):
    """依存関係エラー

    フェーズ間の依存関係チェックで発生したエラー。
    """
    pass


class MetadataError(WorkflowError):
    """メタデータエラー

    metadata.jsonの読み込み・書き込みで発生したエラー。
    """
    pass


class ErrorHandler:
    """エラーハンドリングユーティリティクラス

    エラーメッセージの生成、ログ記録等の共通処理を提供します。
    """

    @staticmethod
    def format_error_message(
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """エラーメッセージをフォーマット

        Args:
            error: 例外オブジェクト
            context: コンテキスト情報

        Returns:
            str: フォーマットされたエラーメッセージ

        Example:
            >>> error = GitBranchError("ブランチ作成失敗", details={'branch': 'test'})
            >>> msg = ErrorHandler.format_error_message(error, {'phase': 'planning'})
        """
        lines = []

        # エラータイプ
        lines.append(f"Error Type: {error.__class__.__name__}")

        # エラーメッセージ
        lines.append(f"Message: {str(error)}")

        # コンテキスト情報
        if context:
            lines.append("Context:")
            for key, value in context.items():
                lines.append(f"  {key}: {value}")

        # 詳細情報（WorkflowErrorの場合）
        if isinstance(error, WorkflowError) and error.details:
            lines.append("Details:")
            for key, value in error.details.items():
                lines.append(f"  {key}: {value}")

        # 元の例外（WorkflowErrorの場合）
        if isinstance(error, WorkflowError) and error.original_exception:
            lines.append(f"Original Exception: {error.original_exception}")

        return "\n".join(lines)

    @staticmethod
    def wrap_exception(
        original_exception: Exception,
        message: str,
        error_class: type = WorkflowError,
        details: Optional[Dict[str, Any]] = None
    ) -> WorkflowError:
        """例外をカスタム例外でラップ

        Args:
            original_exception: 元の例外
            message: エラーメッセージ
            error_class: カスタム例外クラス
            details: エラー詳細情報

        Returns:
            WorkflowError: ラップされた例外

        Example:
            >>> try:
            ...     # Git操作
            ... except GitCommandError as e:
            ...     raise ErrorHandler.wrap_exception(
            ...         e, "ブランチ作成に失敗しました",
            ...         GitBranchError, {'branch': 'test'}
            ...     )
        """
        return error_class(
            message=message,
            details=details,
            original_exception=original_exception
        )
