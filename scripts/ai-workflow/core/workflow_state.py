"""ワークフロー状態管理 - metadata.json の読み書き"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime


class PhaseStatus(Enum):
    """フェーズステータス"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowState:
    """metadata.json の読み書きを管理"""

    def __init__(self, metadata_path: Path):
        self.metadata_path = metadata_path
        self.data = self._load()

    @classmethod
    def create_new(cls, metadata_path: Path, issue_number: str,
                   issue_url: str, issue_title: str) -> 'WorkflowState':
        """新規ワークフローを作成"""
        # テンプレートファイルを読み込み
        template_path = Path(__file__).parent.parent / 'metadata.json.template'
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        initial_data = json.loads(template_path.read_text(encoding='utf-8'))

        # パラメータを設定
        initial_data['issue_number'] = issue_number
        initial_data['issue_url'] = issue_url
        initial_data['issue_title'] = issue_title
        initial_data['created_at'] = datetime.utcnow().isoformat() + "Z"
        initial_data['updated_at'] = datetime.utcnow().isoformat() + "Z"

        # ディレクトリ作成
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        # JSON書き込み
        metadata_path.write_text(json.dumps(initial_data, indent=2, ensure_ascii=False))

        return cls(metadata_path)

    def _load(self) -> Dict[str, Any]:
        """metadata.json を読み込み"""
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"metadata.json not found: {self.metadata_path}")

        return json.loads(self.metadata_path.read_text(encoding='utf-8'))

    def save(self) -> None:
        """metadata.json を保存"""
        self.data['updated_at'] = datetime.utcnow().isoformat() + "Z"
        self.metadata_path.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

    def update_phase_status(self, phase: str, status: PhaseStatus) -> None:
        """フェーズのステータスを更新"""
        if phase not in self.data['phases']:
            raise ValueError(f"Unknown phase: {phase}")

        self.data['phases'][phase]['status'] = status.value

        if status == PhaseStatus.IN_PROGRESS:
            self.data['phases'][phase]['started_at'] = datetime.utcnow().isoformat() + "Z"
        elif status in (PhaseStatus.COMPLETED, PhaseStatus.FAILED):
            self.data['phases'][phase]['completed_at'] = datetime.utcnow().isoformat() + "Z"

        self.data['current_phase'] = phase

    def increment_retry_count(self, phase: str) -> int:
        """リトライカウントを増加（上限3回）"""
        if phase not in self.data['phases']:
            raise ValueError(f"Unknown phase: {phase}")

        current_count = self.data['phases'][phase]['retry_count']
        if current_count >= 3:
            raise Exception(f"Max retry count exceeded for phase: {phase}")

        self.data['phases'][phase]['retry_count'] = current_count + 1
        return current_count + 1

    def set_design_decision(self, key: str, value: str) -> None:
        """設計判断を記録"""
        if key not in self.data['design_decisions']:
            raise ValueError(f"Unknown design decision key: {key}")

        self.data['design_decisions'][key] = value

    def get_phase_status(self, phase: str) -> str:
        """フェーズのステータスを取得"""
        return self.data['phases'][phase]['status']

    def migrate(self) -> bool:
        """metadata.jsonを最新のスキーマにマイグレーション

        Returns:
            bool: マイグレーションを実行した場合True
        """
        migrated = False

        # テンプレートファイルを読み込み
        template_path = self.metadata_path.parent.parent.parent.parent / 'scripts' / 'ai-workflow' / 'metadata.json.template'
        if not template_path.exists():
            print(f"[WARNING] Template file not found: {template_path}")
            return False

        template = json.loads(template_path.read_text(encoding='utf-8'))

        # 欠けているフェーズをチェック
        missing_phases = []
        for phase_name in template['phases'].keys():
            if phase_name not in self.data['phases']:
                print(f"[INFO] Migrating metadata.json: Adding {phase_name} phase")
                missing_phases.append(phase_name)
                migrated = True

        # フェーズを正しい順序で再構築
        if missing_phases:
            new_phases = {}
            for phase_name in template['phases'].keys():
                if phase_name in self.data['phases']:
                    # 既存のフェーズデータを保持
                    new_phases[phase_name] = self.data['phases'][phase_name]
                else:
                    # 新しいフェーズをテンプレートから追加
                    new_phases[phase_name] = template['phases'][phase_name].copy()
            self.data['phases'] = new_phases

        # design_decisionsの構造チェック
        if 'design_decisions' not in self.data:
            print("[INFO] Migrating metadata.json: Adding design_decisions")
            self.data['design_decisions'] = template['design_decisions'].copy()
            migrated = True
        else:
            # 各キーの存在チェック
            for key in template['design_decisions'].keys():
                if key not in self.data['design_decisions']:
                    print(f"[INFO] Migrating metadata.json: Adding design_decisions.{key}")
                    self.data['design_decisions'][key] = None
                    migrated = True

        # cost_trackingの構造チェック
        if 'cost_tracking' not in self.data:
            print("[INFO] Migrating metadata.json: Adding cost_tracking")
            self.data['cost_tracking'] = template['cost_tracking'].copy()
            migrated = True

        # workflow_versionの追加
        if 'workflow_version' not in self.data:
            print("[INFO] Migrating metadata.json: Adding workflow_version")
            self.data['workflow_version'] = template['workflow_version']
            migrated = True

        if migrated:
            self.save()
            print(f"[OK] metadata.json migrated successfully")

        return migrated
