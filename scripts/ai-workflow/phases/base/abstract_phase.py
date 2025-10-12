"""Abstract Phase - フェーズ抽象基底クラス

このモジュールは、すべてのフェーズクラスが継承する抽象基底クラスを提供します。

機能:
    - フェーズの基本構造定義
    - execute(), review() の抽象メソッド
    - プロンプトファイル読み込み機能
    - ディレクトリ管理

使用例:
    >>> class MyPhase(AbstractPhase):
    ...     def execute(self) -> Dict[str, Any]:
    ...         # 実装
    ...         pass
    ...
    ...     def review(self) -> Dict[str, Any]:
    ...         # 実装
    ...         pass
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
from core.metadata_manager import MetadataManager
from core.claude_agent_client import ClaudeAgentClient
from core.content_parser import ContentParser


class AbstractPhase(ABC):
    """フェーズ抽象基底クラス

    すべてのフェーズクラスはこのクラスを継承する必要があります。

    Attributes:
        phase_name: フェーズ名
        working_dir: 作業ディレクトリ
        metadata: メタデータマネージャー
        claude: Claude Agent SDKクライアント
        content_parser: コンテンツパーサー
        phase_dir: フェーズディレクトリ
        output_dir: 出力ディレクトリ
        execute_dir: 実行用ディレクトリ
        review_dir: レビュー用ディレクトリ
        revise_dir: 修正用ディレクトリ
    """

    # フェーズ番号マッピング
    PHASE_NUMBERS = {
        'planning': '00',
        'requirements': '01',
        'design': '02',
        'test_scenario': '03',
        'implementation': '04',
        'test_implementation': '05',
        'testing': '06',
        'documentation': '07',
        'report': '08',
        'evaluation': '09'
    }

    def __init__(
        self,
        phase_name: str,
        working_dir: Path,
        metadata_manager: MetadataManager,
        claude_client: ClaudeAgentClient
    ):
        """初期化

        Args:
            phase_name: フェーズ名（例: 'planning', 'requirements'）
            working_dir: 作業ディレクトリ（リポジトリルート）
            metadata_manager: メタデータマネージャー
            claude_client: Claude Agent SDKクライアント
        """
        self.phase_name = phase_name
        self.working_dir = working_dir
        self.metadata = metadata_manager
        self.claude = claude_client
        self.content_parser = ContentParser()

        # ディレクトリパス設定
        phase_number = self.PHASE_NUMBERS.get(phase_name, '00')
        self.phase_dir = self.metadata.workflow_dir / f'{phase_number}_{phase_name}'
        self.output_dir = self.phase_dir / 'output'
        self.execute_dir = self.phase_dir / 'execute'
        self.review_dir = self.phase_dir / 'review'
        self.revise_dir = self.phase_dir / 'revise'

        # ディレクトリ作成
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.execute_dir.mkdir(parents=True, exist_ok=True)
        self.review_dir.mkdir(parents=True, exist_ok=True)
        self.revise_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def execute(self) -> Dict[str, Any]:
        """フェーズを実行

        サブクラスで実装必須のメソッド。
        フェーズの主要処理を実行し、結果を返します。

        Returns:
            Dict[str, Any]: 実行結果
                - success: bool - 実行が成功したかどうか
                - output: Any - 実行結果の出力
                - error: Optional[str] - エラーメッセージ（失敗時）

        Raises:
            NotImplementedError: サブクラスで実装されていない場合
        """
        raise NotImplementedError("execute() must be implemented by subclass")

    @abstractmethod
    def review(self) -> Dict[str, Any]:
        """フェーズをレビュー

        サブクラスで実装必須のメソッド。
        実行結果をレビューし、品質評価を返します。

        Returns:
            Dict[str, Any]: レビュー結果
                - result: str - レビュー判定（PASS/PASS_WITH_SUGGESTIONS/FAIL）
                - feedback: str - フィードバックメッセージ
                - suggestions: List[str] - 改善提案リスト

        Raises:
            NotImplementedError: サブクラスで実装されていない場合
        """
        raise NotImplementedError("review() must be implemented by subclass")

    def load_prompt(self, prompt_type: str) -> str:
        """プロンプトファイルを読み込み

        指定されたプロンプトタイプのファイルを読み込みます。

        Args:
            prompt_type: プロンプトタイプ（execute, review, revise）

        Returns:
            str: プロンプトテキスト

        Raises:
            FileNotFoundError: プロンプトファイルが存在しない場合

        Example:
            >>> prompt = self.load_prompt('execute')
        """
        prompts_dir = self.working_dir / 'prompts' / self.phase_name
        prompt_file = prompts_dir / f'{prompt_type}.txt'

        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        return prompt_file.read_text(encoding='utf-8')

    def get_phase_number(self) -> str:
        """フェーズ番号を取得

        Returns:
            str: フェーズ番号（例: '00', '01'）
        """
        return self.PHASE_NUMBERS.get(self.phase_name, '00')
