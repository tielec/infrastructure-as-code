"""レジューム機能 - ワークフローの再開管理

AIワークフロー実行時のレジューム機能を提供します。
メタデータの状態を分析し、失敗したフェーズから自動的に再開する機能を実装しています。
"""
from pathlib import Path
from typing import Optional, Dict, List
from core.metadata_manager import MetadataManager


class ResumeManager:
    """ワークフローのレジューム機能を管理するクラス

    メタデータJSONの状態を分析し、以下の機能を提供します：
    - レジューム可能性の判定
    - レジューム開始フェーズの決定
    - 全フェーズ完了状態の確認
    - ステータスサマリーの取得
    - メタデータのリセット
    """

    def __init__(self, metadata_manager: MetadataManager):
        """ResumeManagerの初期化

        Args:
            metadata_manager: MetadataManagerインスタンス
        """
        self.metadata_manager = metadata_manager

        # フェーズリスト（Phase 1-8の順序）
        # Planning（Phase 0）は含まない（README.mdの記載に従う）
        self.phases = [
            'requirements',
            'design',
            'test_scenario',
            'implementation',
            'test_implementation',
            'testing',
            'documentation',
            'report'
        ]

    def can_resume(self) -> bool:
        """レジューム可能かチェック

        以下の条件を満たす場合にレジューム可能と判定：
        - メタデータファイルが存在する
        - 少なくとも1つのフェーズがcompleted/failed/in_progressである
        - 全フェーズが完了していない

        Returns:
            bool: レジューム可能な場合True
        """
        # メタデータファイルが存在しない場合
        if not self.metadata_manager.metadata_path.exists():
            return False

        # 全フェーズが完了している場合はレジューム不要
        if self.is_completed():
            return False

        # 少なくとも1つのフェーズがcompleted/failed/in_progressの場合
        phases_data = self.metadata_manager.data['phases']
        for phase in self.phases:
            status = phases_data[phase]['status']
            if status in ['completed', 'failed', 'in_progress']:
                return True

        # すべてpendingの場合はレジューム不要（新規ワークフロー）
        return False

    def is_completed(self) -> bool:
        """全フェーズが完了しているかチェック

        Returns:
            bool: 全フェーズが完了している場合True
        """
        phases_data = self.metadata_manager.data['phases']

        for phase in self.phases:
            status = phases_data[phase]['status']
            if status != 'completed':
                return False

        return True

    def get_resume_phase(self) -> Optional[str]:
        """レジューム開始フェーズを取得

        優先順位に従ってレジューム開始フェーズを決定：
        1. failedフェーズ: 最初に失敗したフェーズから再開
        2. in_progressフェーズ: 異常終了したフェーズから再開
        3. pendingフェーズ: 最初の未実行フェーズから再開
        4. 全フェーズcompleted: None（完了済み）

        Returns:
            Optional[str]: レジューム開始フェーズ名、完了済みの場合はNone
        """
        # 全フェーズ完了チェック
        if self.is_completed():
            return None

        phases_data = self.metadata_manager.data['phases']

        # 優先順位1: failedフェーズ
        for phase in self.phases:
            if phases_data[phase]['status'] == 'failed':
                return phase

        # 優先順位2: in_progressフェーズ
        for phase in self.phases:
            if phases_data[phase]['status'] == 'in_progress':
                return phase

        # 優先順位3: pendingフェーズ
        for phase in self.phases:
            if phases_data[phase]['status'] == 'pending':
                return phase

        # すべてcompletedの場合（is_completed()でチェック済みのため到達しない）
        return None

    def get_status_summary(self) -> Dict[str, List[str]]:
        """各フェーズのステータスサマリーを取得

        ログ出力用に各ステータスのフェーズリストを取得します。

        Returns:
            Dict[str, List[str]]: ステータスごとのフェーズリスト
                {
                    'completed': ['requirements', 'design', ...],
                    'failed': ['test_implementation'],
                    'in_progress': [],
                    'pending': ['testing', 'documentation', ...]
                }
        """
        return {
            'completed': self._get_phases_by_status('completed'),
            'failed': self._get_phases_by_status('failed'),
            'in_progress': self._get_phases_by_status('in_progress'),
            'pending': self._get_phases_by_status('pending')
        }

    def reset(self) -> None:
        """メタデータをクリアして最初からやり直し

        MetadataManager.clear()を呼び出してメタデータとワークフロー
        ディレクトリを削除します。

        Note:
            破壊的操作のため、呼び出し元で--force-resetフラグの
            チェックが必須です。
        """
        self.metadata_manager.clear()

    def _get_phases_by_status(self, status: str) -> List[str]:
        """指定ステータスのフェーズリストを取得

        Args:
            status: フェーズステータス（completed/failed/in_progress/pending）

        Returns:
            List[str]: フェーズ名リスト
        """
        phases_data = self.metadata_manager.data['phases']
        return [
            phase for phase in self.phases
            if phases_data[phase]['status'] == status
        ]
