"""フェーズ依存関係検証モジュール

各フェーズの依存関係を定義し、実行前に依存フェーズが完了しているかを検証する。
"""
from typing import List, Dict, Optional
from core.metadata_manager import MetadataManager


# フェーズ依存関係定義
PHASE_DEPENDENCIES: Dict[str, List[str]] = {
    'planning': [],  # Phase 0: 依存なし
    'requirements': [],  # Phase 1: 依存なし
    'design': ['requirements'],  # Phase 2: Phase 1が必要
    'test_scenario': ['requirements', 'design'],  # Phase 3: Phase 1, 2が必要
    'implementation': ['requirements', 'design', 'test_scenario'],  # Phase 4
    'test_implementation': ['implementation'],  # Phase 5: Phase 4が必要
    'testing': ['implementation', 'test_implementation'],  # Phase 6
    'documentation': ['implementation'],  # Phase 7: Phase 4が必要
    'report': ['requirements', 'design', 'implementation', 'testing', 'documentation'],  # Phase 8
    'evaluation': ['report']  # Phase 9: Phase 8が必要
}


class DependencyError(Exception):
    """依存関係違反エラー"""

    def __init__(self, phase_name: str, missing_phases: List[str], message: str = None):
        """
        初期化

        Args:
            phase_name: 実行しようとしているフェーズ名
            missing_phases: 未完了の依存フェーズリスト
            message: カスタムエラーメッセージ（省略可）
        """
        self.phase_name = phase_name
        self.missing_phases = missing_phases

        if message:
            self.message = message
        else:
            if len(missing_phases) == 1:
                self.message = (
                    f"Dependency check failed: Phase '{missing_phases[0]}' must be completed "
                    f"before '{phase_name}'"
                )
            else:
                phases_str = "', '".join(missing_phases)
                self.message = (
                    f"Dependency check failed: Phases '{phases_str}' must be completed "
                    f"before '{phase_name}'"
                )

        super().__init__(self.message)


def validate_phase_dependencies(
    phase_name: str,
    metadata: MetadataManager,
    skip_check: bool = False,
    ignore_violations: bool = False
) -> bool:
    """
    フェーズ依存関係を検証

    Args:
        phase_name: 実行しようとしているフェーズ名
        metadata: MetadataManagerインスタンス
        skip_check: 依存関係チェックをスキップするか（--skip-dependency-check）
        ignore_violations: 依存関係違反時も警告のみ表示して継続するか（--ignore-dependencies）

    Returns:
        bool: 依存関係が満たされている場合True

    Raises:
        DependencyError: 依存関係が満たされていない場合（ignore_violations=Falseの時）
        ValueError: 未知のフェーズ名が指定された場合
    """
    # スキップフラグが有効な場合は即座にTrue返却
    if skip_check:
        print(f"[WARNING] Dependency check skipped. Proceeding without validation.")
        return True

    # フェーズ名のバリデーション
    if phase_name not in PHASE_DEPENDENCIES:
        raise ValueError(f"Unknown phase: '{phase_name}'")

    # 依存フェーズリストを取得
    required_phases = PHASE_DEPENDENCIES[phase_name]

    # 依存フェーズがない場合は即座にTrue返却
    if not required_phases:
        print(f"[INFO] Phase '{phase_name}' has no dependencies. Proceeding.")
        return True

    # 未完了の依存フェーズをチェック
    missing_phases: List[str] = []
    for required_phase in required_phases:
        status = metadata.get_phase_status(required_phase)
        if status != 'completed':
            missing_phases.append(required_phase)

    # 依存関係が満たされている場合
    if not missing_phases:
        print(f"[INFO] Dependency check passed for phase '{phase_name}'.")
        return True

    # 依存関係違反が発生
    if ignore_violations:
        # 警告のみ表示して継続
        if len(missing_phases) == 1:
            print(
                f"[WARNING] Dependency violation: Phase '{missing_phases[0]}' is not completed. "
                f"Continuing anyway."
            )
        else:
            phases_str = "', '".join(missing_phases)
            print(
                f"[WARNING] Dependency violation: Phases '{phases_str}' are not completed. "
                f"Continuing anyway."
            )
        return True
    else:
        # 例外を発生
        raise DependencyError(phase_name=phase_name, missing_phases=missing_phases)


def get_phase_dependencies(phase_name: str) -> List[str]:
    """
    指定フェーズの依存フェーズリストを取得

    Args:
        phase_name: フェーズ名

    Returns:
        List[str]: 依存フェーズ名のリスト

    Raises:
        ValueError: 未知のフェーズ名が指定された場合
    """
    if phase_name not in PHASE_DEPENDENCIES:
        raise ValueError(f"Unknown phase: '{phase_name}'")

    return PHASE_DEPENDENCIES[phase_name].copy()


def get_all_phase_dependencies() -> Dict[str, List[str]]:
    """
    全フェーズの依存関係定義を取得

    Returns:
        Dict[str, List[str]]: フェーズ名 → 依存フェーズリストの辞書
    """
    return PHASE_DEPENDENCIES.copy()
