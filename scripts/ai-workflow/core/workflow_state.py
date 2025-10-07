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
        initial_data = {
            "issue_number": issue_number,
            "issue_url": issue_url,
            "issue_title": issue_title,
            "workflow_version": "1.0.0",
            "current_phase": "requirements",
            "design_decisions": {
                "implementation_strategy": None,
                "test_strategy": None,
                "test_code_strategy": None
            },
            "cost_tracking": {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost_usd": 0.0
            },
            "phases": {
                "requirements": {
                    "status": "pending",
                    "retry_count": 0,
                    "started_at": None,
                    "completed_at": None,
                    "review_result": None
                },
                "design": {
                    "status": "pending",
                    "retry_count": 0,
                    "started_at": None,
                    "completed_at": None,
                    "review_result": None
                },
                "test_scenario": {
                    "status": "pending",
                    "retry_count": 0,
                    "started_at": None,
                    "completed_at": None,
                    "review_result": None
                },
                "implementation": {
                    "status": "pending",
                    "retry_count": 0,
                    "started_at": None,
                    "completed_at": None,
                    "review_result": None
                },
                "testing": {
                    "status": "pending",
                    "retry_count": 0,
                    "started_at": None,
                    "completed_at": None,
                    "review_result": None
                },
                "documentation": {
                    "status": "pending",
                    "retry_count": 0,
                    "started_at": None,
                    "completed_at": None,
                    "review_result": None
                }
            },
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }

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
