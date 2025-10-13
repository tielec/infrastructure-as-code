"""メタデータ管理 - WorkflowStateのラッパー

Phase実装で使いやすいインターフェースを提供
"""
from pathlib import Path
from typing import Optional, Dict, Any, List
from .workflow_state import WorkflowState, PhaseStatus
from common.error_handler import MetadataError
from common.logger import Logger


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
        self.logger = Logger.get_logger(__name__)

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
                self.logger.info(f"Clearing metadata: {self.metadata_path}")
                click.echo(f"[INFO] Clearing metadata: {self.metadata_path}")
                self.metadata_path.unlink()

            # ワークフローディレクトリ削除
            if self.workflow_dir.exists():
                self.logger.info(f"Removing workflow directory: {self.workflow_dir}")
                click.echo(f"[INFO] Removing workflow directory: {self.workflow_dir}")
                shutil.rmtree(self.workflow_dir)
                self.logger.info("Workflow directory removed successfully")
                click.echo(f"[OK] Workflow directory removed successfully")

        except PermissionError as e:
            error_msg = f"Permission denied: {e}"
            self.logger.error(error_msg)
            click.echo(f"[ERROR] {error_msg}")
            raise
        except OSError as e:
            error_msg = f"Failed to remove directory: {e}"
            self.logger.error(error_msg)
            click.echo(f"[ERROR] {error_msg}")
            raise

    def rollback_to_phase(self, phase_name: str) -> Dict[str, Any]:
        """
        指定フェーズにメタデータを巻き戻し

        Args:
            phase_name: 巻き戻し先フェーズ名（例: 'implementation'）

        Returns:
            Dict[str, Any]:
                - success: bool
                - backup_path: str - バックアップファイルパス
                - rolled_back_phases: List[str] - 巻き戻されたフェーズ一覧
                - error: Optional[str]
        """
        from datetime import datetime
        import shutil

        try:
            # フェーズ名のバリデーション
            all_phases = list(self._state.data['phases'].keys())
            if phase_name not in all_phases:
                error_msg = f'Invalid phase name: {phase_name}'
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

            # バックアップ作成
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = str(self.metadata_path.parent / f'metadata.json.backup_{timestamp}')
            shutil.copy(str(self.metadata_path), backup_path)
            self.logger.info(f"メタデータバックアップ作成: {backup_path}")

            # 巻き戻し先フェーズのインデックスを取得
            start_index = all_phases.index(phase_name)
            rolled_back_phases = all_phases[start_index:]

            # Phase X 以降のフェーズステータスを pending に変更
            for phase in rolled_back_phases:
                self._state.data['phases'][phase]['status'] = 'pending'
                self._state.data['phases'][phase]['started_at'] = None
                self._state.data['phases'][phase]['completed_at'] = None
                self._state.data['phases'][phase]['review_result'] = None
                self._state.data['phases'][phase]['retry_count'] = 0

            # 保存
            self._state.save()

            self.logger.info(f"メタデータを {phase_name} フェーズに巻き戻しました")
            self.logger.info(f"巻き戻されたフェーズ: {', '.join(rolled_back_phases)}")

            return {
                'success': True,
                'backup_path': backup_path,
                'rolled_back_phases': rolled_back_phases,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'backup_path': None,
                'rolled_back_phases': [],
                'error': str(e)
            }

    def get_all_phases_status(self) -> Dict[str, str]:
        """
        全フェーズのステータスを取得

        Returns:
            Dict[str, str]: フェーズ名 → ステータス
        """
        return {
            phase_name: phase_data['status']
            for phase_name, phase_data in self._state.data['phases'].items()
        }

    def backup_metadata(self) -> str:
        """
        metadata.json のバックアップを作成

        Returns:
            str: バックアップファイルパス
        """
        from datetime import datetime
        import shutil

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = str(self.metadata_path.parent / f'metadata.json.backup_{timestamp}')
        shutil.copy(str(self.metadata_path), backup_path)
        self.logger.info(f"メタデータバックアップ作成: {backup_path}")

        return backup_path

    def set_evaluation_decision(
        self,
        decision: str,
        failed_phase: Optional[str] = None,
        remaining_tasks: Optional[List[Dict]] = None,
        created_issue_url: Optional[str] = None,
        abort_reason: Optional[str] = None
    ):
        """
        評価判定結果を metadata.json に記録

        Args:
            decision: 判定タイプ（PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT）
            failed_phase: FAIL_PHASE_X の場合のフェーズ名
            remaining_tasks: PASS_WITH_ISSUES の場合の残タスクリスト
            created_issue_url: PASS_WITH_ISSUES の場合の作成されたIssue URL
            abort_reason: ABORT の場合の中止理由
        """
        if 'evaluation' not in self._state.data['phases']:
            error_msg = "Evaluation phase not found in metadata"
            self.logger.error(error_msg)
            raise MetadataError(error_msg)

        self._state.data['phases']['evaluation']['decision'] = decision

        if failed_phase:
            self._state.data['phases']['evaluation']['failed_phase'] = failed_phase

        if remaining_tasks:
            self._state.data['phases']['evaluation']['remaining_tasks'] = remaining_tasks

        if created_issue_url:
            self._state.data['phases']['evaluation']['created_issue_url'] = created_issue_url

        if abort_reason:
            self._state.data['phases']['evaluation']['abort_reason'] = abort_reason

        self._state.save()

    def save_progress_comment_id(
        self,
        comment_id: int,
        comment_url: str
    ) -> None:
        """
        進捗コメントIDをメタデータに保存

        Args:
            comment_id: GitHub コメントID
            comment_url: GitHub コメントURL

        処理フロー:
            1. self._state.data に 'github_integration' セクションを追加（存在しない場合）
            2. 'progress_comment_id' と 'progress_comment_url' を保存
            3. self._state.save() で保存
        """
        # github_integrationセクションが存在しない場合は作成
        if 'github_integration' not in self._state.data:
            self._state.data['github_integration'] = {}

        # コメントIDとURLを保存
        self._state.data['github_integration']['progress_comment_id'] = comment_id
        self._state.data['github_integration']['progress_comment_url'] = comment_url

        # 保存
        self._state.save()

    def get_progress_comment_id(self) -> Optional[int]:
        """
        進捗コメントIDをメタデータから取得

        Returns:
            Optional[int]: コメントID（存在しない場合はNone）

        処理フロー:
            1. self._state.data['github_integration']の存在確認
            2. 存在する場合: 'progress_comment_id' を返却
            3. 存在しない場合: None を返却
        """
        # github_integrationセクションの存在確認
        if 'github_integration' not in self._state.data:
            return None

        # progress_comment_idを返却（存在しない場合はNone）
        return self._state.data['github_integration'].get('progress_comment_id')
