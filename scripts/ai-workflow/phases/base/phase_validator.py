"""Phase Validator - フェーズ検証ロジック

このモジュールは、フェーズの依存関係検証とレビュー結果のパース処理を提供します。

機能:
    - フェーズ依存関係の検証
    - レビュー結果メッセージのパース
    - 依存関係違反の警告/エラー処理

使用例:
    >>> validator = PhaseValidator(metadata_manager)
    >>> result = validator.validate_dependencies('design')
    >>> if not result['valid']:
    ...     print(f"依存関係エラー: {result['error']}")
"""

from typing import Dict, Any, List
from core.metadata_manager import MetadataManager
from common.logger import Logger


class PhaseValidator:
    """フェーズ検証クラス

    フェーズの依存関係検証とレビュー結果のパース処理を提供します。

    Attributes:
        metadata: メタデータマネージャー
        logger: ロガーインスタンス
    """

    # フェーズ依存関係定義
    PHASE_DEPENDENCIES = {
        'planning': [],
        'requirements': ['planning'],
        'design': ['requirements'],
        'test_scenario': ['design'],
        'implementation': ['design'],
        'test_implementation': ['implementation'],
        'testing': ['test_implementation'],
        'documentation': ['testing'],
        'report': ['documentation'],
        'evaluation': ['report']
    }

    def __init__(self, metadata_manager: MetadataManager):
        """初期化

        Args:
            metadata_manager: メタデータマネージャー
        """
        self.metadata = metadata_manager
        self.logger = Logger.get_logger(__name__)

    def validate_dependencies(
        self,
        phase_name: str,
        ignore_violations: bool = False
    ) -> Dict[str, Any]:
        """依存関係を検証

        指定されたフェーズが実行可能かどうかを、依存する前提フェーズの
        完了状況に基づいて検証します。

        Args:
            phase_name: フェーズ名（例: 'design', 'implementation'）
            ignore_violations: 依存関係違反を警告のみで許可（デフォルト: False）

        Returns:
            Dict[str, Any]: 検証結果
                - valid: bool - 検証結果（True: 実行可能、False: 実行不可）
                - error: Optional[str] - エラーメッセージ（実行不可の場合）
                - warning: Optional[str] - 警告メッセージ（ignore_violationsがTrueの場合）
                - missing_phases: List[str] - 未完了の依存フェーズリスト

        Example:
            >>> result = validator.validate_dependencies('design')
            >>> if result['valid']:
            ...     print("実行可能")
            >>> else:
            ...     print(f"実行不可: {result['error']}")
        """
        dependencies = self.PHASE_DEPENDENCIES.get(phase_name, [])

        # 依存関係がない場合は常にOK
        if not dependencies:
            return {
                'valid': True,
                'error': None,
                'warning': None,
                'missing_phases': []
            }

        # 依存フェーズのステータスをチェック
        missing_phases = []
        phases_status = self.metadata.get_all_phases_status()

        for dep_phase in dependencies:
            status = phases_status.get(dep_phase, 'pending')
            if status != 'completed':
                missing_phases.append(dep_phase)

        if missing_phases:
            error_msg = (
                f"Phase '{phase_name}' requires completion of: "
                f"{', '.join(missing_phases)}"
            )

            if ignore_violations:
                # 警告のみで実行継続
                self.logger.warning(error_msg)
                return {
                    'valid': True,
                    'error': None,
                    'warning': error_msg,
                    'missing_phases': missing_phases
                }
            else:
                # エラーで実行停止
                self.logger.error(error_msg)
                return {
                    'valid': False,
                    'error': error_msg,
                    'warning': None,
                    'missing_phases': missing_phases
                }

        return {
            'valid': True,
            'error': None,
            'warning': None,
            'missing_phases': []
        }

    def parse_review_result(self, messages: List[str]) -> Dict[str, Any]:
        """レビュー結果メッセージから判定とフィードバックを抽出

        Claude Agent SDKからのレスポンスメッセージを解析し、
        レビュー判定、フィードバック、改善提案を抽出します。

        Args:
            messages: Claude Agent SDKからのレスポンスメッセージリスト

        Returns:
            Dict[str, Any]: レビュー結果
                - result: str - レビュー判定（PASS/PASS_WITH_SUGGESTIONS/FAIL）
                - feedback: str - フィードバックメッセージ
                - suggestions: List[str] - 改善提案リスト

        Note:
            実際のパース処理はContentParserに委譲します。

        Example:
            >>> messages = ['レビュー結果: PASS', 'フィードバック: 良好です']
            >>> result = validator.parse_review_result(messages)
            >>> print(result['result'])  # 'PASS'
        """
        # ContentParserに委譲
        from core.content_parser import ContentParser
        parser = ContentParser()
        return parser.parse_review_result(messages)

    def get_required_phases(self, phase_name: str) -> List[str]:
        """フェーズの依存関係リストを取得

        Args:
            phase_name: フェーズ名

        Returns:
            List[str]: 依存するフェーズ名のリスト

        Example:
            >>> required = validator.get_required_phases('design')
            >>> print(required)  # ['requirements']
        """
        return self.PHASE_DEPENDENCIES.get(phase_name, [])

    def is_phase_executable(self, phase_name: str) -> bool:
        """フェーズが実行可能かどうかを判定

        Args:
            phase_name: フェーズ名

        Returns:
            bool: 実行可能な場合True

        Example:
            >>> if validator.is_phase_executable('design'):
            ...     print("実行可能")
        """
        result = self.validate_dependencies(phase_name, ignore_violations=False)
        return result['valid']
