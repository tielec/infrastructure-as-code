"""フェーズ依存関係管理モジュール

各フェーズの依存関係を定義し、実行前に依存関係をチェックする機能を提供します。

主要機能:
- PHASE_DEPENDENCIES: フェーズ依存関係の定義
- PHASE_PRESETS: プリセット実行モードの定義
- validate_phase_dependencies(): 依存関係検証
- detect_circular_dependencies(): 循環参照検出
- validate_external_document(): 外部ドキュメント検証
"""
from pathlib import Path
from typing import Dict, List, Any, Optional


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# フェーズ依存関係定義
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PHASE_DEPENDENCIES: Dict[str, List[str]] = {
    'planning': [],  # 依存なし
    'requirements': ['planning'],
    'design': ['requirements'],
    'test_scenario': ['requirements', 'design'],
    'implementation': ['requirements', 'design', 'test_scenario'],
    'test_implementation': ['implementation'],
    'testing': ['test_implementation'],
    'documentation': ['implementation'],
    'report': ['requirements', 'design', 'implementation', 'testing', 'documentation'],
    'evaluation': ['report']
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# プリセット定義
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PHASE_PRESETS: Dict[str, List[str]] = {
    'requirements-only': ['requirements'],
    'design-phase': ['requirements', 'design'],
    'implementation-phase': ['requirements', 'design', 'test_scenario', 'implementation'],
    'full-workflow': [
        'planning', 'requirements', 'design', 'test_scenario',
        'implementation', 'test_implementation', 'testing',
        'documentation', 'report', 'evaluation'
    ]
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 依存関係検証関数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def validate_phase_dependencies(
    phase_name: str,
    metadata_manager,
    skip_check: bool = False,
    ignore_violations: bool = False
) -> Dict[str, Any]:
    """
    フェーズ実行前に依存関係をチェック

    Args:
        phase_name: フェーズ名（例: 'implementation'）
        metadata_manager: MetadataManagerインスタンス
        skip_check: 依存関係チェックをスキップするか（--skip-dependency-check）
        ignore_violations: 依存関係違反を警告のみで許可するか（--ignore-dependencies）

    Returns:
        Dict[str, Any]: 検証結果
            - valid: bool - 依存関係が満たされているか
            - error: Optional[str] - エラーメッセージ（valid=False の場合）
            - warning: Optional[str] - 警告メッセージ（ignored=True の場合）
            - ignored: bool - 依存関係違反が無視されたか
            - missing_phases: List[str] - 未完了の依存フェーズ一覧

    Raises:
        ValueError: phase_name が不正な場合

    Example:
        >>> result = validate_phase_dependencies('implementation', metadata_manager)
        >>> if not result['valid']:
        ...     print(result['error'])
        Phase 'requirements' must be completed before 'implementation'
    """
    # フェーズ名のバリデーション
    if phase_name not in PHASE_DEPENDENCIES:
        raise ValueError(f"Invalid phase name: {phase_name}")

    # skip_check=True の場合は即座にリターン
    if skip_check:
        return {'valid': True}

    # 依存フェーズリストを取得
    required_phases = PHASE_DEPENDENCIES.get(phase_name, [])

    # 依存関係がない場合（planningフェーズ）
    if not required_phases:
        return {'valid': True}

    # 全フェーズのステータスを取得
    phases_status = metadata_manager.get_all_phases_status()

    # 未完了の依存フェーズをチェック
    missing_phases = []
    for required_phase in required_phases:
        status = phases_status.get(required_phase)
        if status != 'completed':
            missing_phases.append(required_phase)
            # 早期リターン最適化（ignore_violationsがFalseの場合）
            if not ignore_violations:
                return {
                    'valid': False,
                    'error': f"Phase '{required_phase}' must be completed before '{phase_name}'",
                    'missing_phases': [required_phase]
                }

    # すべてチェック完了
    if missing_phases and ignore_violations:
        return {
            'valid': False,
            'ignored': True,
            'warning': f"Dependency violations ignored: {', '.join(missing_phases)}",
            'missing_phases': missing_phases
        }

    return {'valid': True}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 循環参照検出関数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detect_circular_dependencies() -> List[List[str]]:
    """
    PHASE_DEPENDENCIES 内の循環参照を検出

    Returns:
        List[List[str]]: 循環参照のリスト（例: [['A', 'B', 'A']]）
                         循環参照が存在しない場合は空リスト

    Algorithm:
        DFS (Depth-First Search) を使用して循環を検出

    Example:
        >>> cycles = detect_circular_dependencies()
        >>> if cycles:
        ...     print(f"Circular dependencies detected: {cycles}")
    """
    def dfs(node: str, visited: set, rec_stack: list, path: list) -> List[List[str]]:
        """DFSで循環参照を検出"""
        visited.add(node)
        rec_stack.append(node)
        path.append(node)
        cycles = []

        dependencies = PHASE_DEPENDENCIES.get(node, [])
        for dep in dependencies:
            if dep not in visited:
                # 未訪問ノードを訪問
                cycles.extend(dfs(dep, visited, rec_stack, path))
            elif dep in rec_stack:
                # 循環検出
                cycle_start_index = rec_stack.index(dep)
                cycle = rec_stack[cycle_start_index:] + [dep]
                cycles.append(cycle)

        # バックトラック
        rec_stack.pop()
        path.pop()
        return cycles

    visited = set()
    all_cycles = []

    # すべてのノードを訪問
    for phase in PHASE_DEPENDENCIES:
        if phase not in visited:
            all_cycles.extend(dfs(phase, visited, [], []))

    return all_cycles


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 外部ドキュメント検証関数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def validate_external_document(file_path: str, repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    外部ドキュメントファイルのバリデーション

    Args:
        file_path: ファイルパス（相対パスまたは絶対パス）
        repo_root: リポジトリルートパス（省略可、指定しない場合は相対パスベース）

    Returns:
        Dict[str, Any]: バリデーション結果
            - valid: bool
            - error: Optional[str]
            - absolute_path: str - 絶対パス

    Validation rules:
        - ファイルが存在すること
        - 読み込み可能な形式（.md, .txt）
        - ファイルサイズが10MB以下
        - リポジトリ内のファイル（相対パスで指定）

    Example:
        >>> result = validate_external_document('path/to/requirements.md')
        >>> if not result['valid']:
        ...     print(result['error'])
    """
    try:
        # Pathオブジェクトに変換
        file = Path(file_path)

        # ファイルの存在確認
        if not file.exists():
            return {
                'valid': False,
                'error': f'File not found: {file_path}'
            }

        # 絶対パスに変換
        abs_path = file.resolve()

        # ファイル拡張子のチェック（.md, .txt のみ許可）
        if abs_path.suffix not in ['.md', '.txt']:
            return {
                'valid': False,
                'error': f'Invalid file format: {abs_path.suffix}. Only .md and .txt are allowed'
            }

        # ファイルサイズのチェック（10MB以下）
        file_size_mb = abs_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 10.0:
            return {
                'valid': False,
                'error': f'File size exceeds 10MB limit (actual: {file_size_mb:.1f}MB)'
            }

        # リポジトリ内のファイルかチェック（セキュリティ）
        if repo_root:
            repo_root_resolved = repo_root.resolve()
            try:
                abs_path.relative_to(repo_root_resolved)
            except ValueError:
                return {
                    'valid': False,
                    'error': 'File must be within the repository'
                }

        return {
            'valid': True,
            'absolute_path': str(abs_path)
        }

    except PermissionError:
        return {
            'valid': False,
            'error': f'Permission denied: {file_path}'
        }
    except Exception as e:
        return {
            'valid': False,
            'error': f'Unexpected error: {str(e)}'
        }
