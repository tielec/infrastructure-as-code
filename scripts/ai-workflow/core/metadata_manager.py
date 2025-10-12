"""メタデータ管理 - WorkflowStateのラッパー

Phase実装で使いやすいインターフェースを提供
"""
from pathlib import Path
from typing import Optional
from .workflow_state import WorkflowState, PhaseStatus


class MetadataManager:
    """メタデータ管理クラス"""

    def __init__(self, metadata_path: Path):
        """
        初期化

        Args:
            metadata_path: metadata.jsonのパス
        """
        self.metadata_path = metadata_path
        self.workflow_dir = metadata_path.parent
        self._state = WorkflowState(metadata_path)

    @property
    def data(self):
        """メタデータの生データ"""
        return self._state.data

    def save(self):
        """メタデータを保存"""
        self._state.save()

    def update_phase_status(
        self,
        phase_name: str,
        status: str,
        output_file: Optional[str] = None,
        review_result: Optional[str] = None
    ):
        """
        フェーズステータスを更新

        Args:
            phase_name: フェーズ名
            status: ステータス（pending/in_progress/completed/failed）
            output_file: 出力ファイル名（省略可）
            review_result: レビュー結果（PASS/PASS_WITH_SUGGESTIONS/FAIL）
        """
        # ステータス文字列からEnumに変換
        status_enum = PhaseStatus(status)
        self._state.update_phase_status(phase_name, status_enum)

        # 出力ファイルを記録
        if output_file:
            if 'output_files' not in self._state.data['phases'][phase_name]:
                self._state.data['phases'][phase_name]['output_files'] = []
            self._state.data['phases'][phase_name]['output_files'].append(output_file)

        # レビュー結果を記録
        if review_result:
            self._state.data['phases'][phase_name]['review_result'] = review_result

        # 保存
        self._state.save()

    def add_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float
    ):
        """
        コストトラッキングを更新

        Args:
            input_tokens: 入力トークン数
            output_tokens: 出力トークン数
            cost_usd: コスト（USD）
        """
        self._state.data['cost_tracking']['total_input_tokens'] += input_tokens
        self._state.data['cost_tracking']['total_output_tokens'] += output_tokens
        self._state.data['cost_tracking']['total_cost_usd'] += cost_usd

        # 保存
        self._state.save()

    def get_phase_status(self, phase_name: str) -> str:
        """
        フェーズステータスを取得

        Args:
            phase_name: フェーズ名

        Returns:
            str: ステータス
        """
        return self._state.get_phase_status(phase_name)

    def set_design_decision(self, key: str, value: str):
        """
        設計判断を記録

        Args:
            key: 設計判断のキー
            value: 設計判断の値
        """
        self._state.set_design_decision(key, value)
        self._state.save()

    def increment_retry_count(self, phase_name: str) -> int:
        """
        リトライカウントを増加

        Args:
            phase_name: フェーズ名

        Returns:
            int: 新しいリトライカウント
        """
        count = self._state.increment_retry_count(phase_name)
        self._state.save()
        return count

    def clear(self) -> None:
        """
        メタデータとワークフローディレクトリをクリア

        破壊的操作のため、--force-resetフラグが明示的に指定された
        場合のみ呼び出してください。

        Note:
            - metadata.jsonファイルを削除
            - ワークフローディレクトリ全体を削除
            - 削除前にログで警告を表示
            - 削除対象が存在しない場合はスキップ（エラーなし）
        """
        import shutil
        import click

        try:
            # メタデータファイル削除
            if self.metadata_path.exists():
                click.echo(f"[INFO] Clearing metadata: {self.metadata_path}")
                self.metadata_path.unlink()

            # ワークフローディレクトリ削除
            if self.workflow_dir.exists():
                click.echo(f"[INFO] Removing workflow directory: {self.workflow_dir}")
                shutil.rmtree(self.workflow_dir)
                click.echo(f"[OK] Workflow directory removed successfully")

        except PermissionError as e:
            click.echo(f"[ERROR] Permission denied: {e}")
            raise
        except OSError as e:
            click.echo(f"[ERROR] Failed to remove directory: {e}")
            raise
