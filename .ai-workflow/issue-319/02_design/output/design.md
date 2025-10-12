# 詳細設計書 - Issue #319

## 0. ドキュメントメタデータ

| 項目 | 内容 |
|------|------|
| Issue番号 | #319 |
| タイトル | [FEATURE] AIワークフロー: フェーズ依存関係の柔軟化と選択的実行機能 |
| 作成日 | 2025-10-12 |
| バージョン | 1.0 |
| ステータス | Draft |

---

## 1. アーキテクチャ設計

### 1.1 システム全体図

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Interface (main.py)                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  execute コマンド                                      │  │
│  │  - --phase {phase_name}                              │  │
│  │  - --skip-dependency-check                           │  │
│  │  - --ignore-dependencies                             │  │
│  │  - --preset {preset_name}                            │  │
│  │  - --requirements-doc {path} (将来拡張)              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Dependency Validator (新規モジュール)            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  validate_phase_dependencies(phase, metadata)        │  │
│  │    → PHASE_DEPENDENCIES 定義を参照                    │  │
│  │    → MetadataManager でステータス確認                 │  │
│  │    → DependencyError 発生 or True 返却               │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   BasePhase.run() 統合                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. フェーズ開始前に依存関係チェック                    │  │
│  │  2. スキップフラグ考慮                                 │  │
│  │  3. 違反時の挙動制御                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   MetadataManager                            │
│  - フェーズステータス取得                                     │
│  - 依存関係違反ログ記録                                       │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 コンポーネント間の関係

```
┌───────────────┐
│   main.py     │
│  (CLI層)      │
└───────┬───────┘
        │ calls
        ↓
┌───────────────────────┐
│ DependencyValidator   │ ←─────┐
│  (新規モジュール)      │       │ uses
└───────┬───────────────┘       │
        │ uses                  │
        ↓                       │
┌───────────────┐      ┌────────────────┐
│  BasePhase    │─────→│ MetadataManager│
│   (既存)      │ uses │   (既存)       │
└───────────────┘      └────────────────┘
```

### 1.3 データフロー

```
User Input (CLI)
    ↓
Phase Name + Issue Number + Flags
    ↓
Dependency Check?
    ├── Yes → validate_phase_dependencies()
    │           ↓
    │       Check MetadataManager
    │           ↓
    │       Dependencies Met?
    │           ├── Yes → Execute Phase
    │           └── No  → DependencyError (or Warning)
    │
    └── No (--skip-dependency-check) → Execute Phase
```

---

## 2. 実装戦略判断

### 実装戦略: EXTEND

**判断根拠**:
- **既存ファイルへの影響が大きい**: `main.py`のCLIオプション拡張、`BasePhase.run()`への依存関係チェック統合が必要
- **新規モジュールの作成**: `utils/dependency_validator.py`を新規作成するが、既存の`main.py`や`BasePhase`との統合が主目的
- **既存機能の拡張**: 既存のフェーズ実行フローに依存関係チェックを追加する形で実装
- **既存テストの修正が必要**: 依存関係チェックが追加されるため、既存のE2Eテストやintegrationテストの修正が必要

**理由の詳細**:
1. 既存の`main.py`の`execute`コマンドに3つの新規オプションを追加（`--skip-dependency-check`, `--ignore-dependencies`, `--preset`）
2. 既存の`BasePhase.run()`メソッドに依存関係チェックロジックを統合
3. 新規モジュール`utils/dependency_validator.py`を作成し、`PHASE_DEPENDENCIES`定義と検証関数を実装
4. 既存のメタデータスキーマ（`metadata.json`）に依存関係違反ログフィールドを追加（非破壊的な拡張）

---

## 3. テスト戦略判断

### テスト戦略: UNIT_INTEGRATION

**判断根拠**:
- **機能の複雑度**: 依存関係チェックはビジネスロジックが中心で、Unit テストで十分カバー可能
- **Integration テストの必要性**: CLIからの実行フロー、MetadataManagerとの連携、BasePhaseとの統合をテストする必要がある
- **BDD の不要性**: ユーザーストーリーよりも技術的な依存関係検証が主眼であり、Gherkin 形式のシナリオテストは過剰
- **既存テストとの整合性**: 既存のUnit テスト（`tests/unit/`）とIntegration テスト（`tests/integration/`）の構造に合わせる

**テスト内訳**:
1. **Unit テスト**:
   - `test_dependency_validator.py`: 依存関係チェックロジックの単体テスト
   - `test_main.py` 拡張: CLIオプションのパース検証
   - `test_base_phase.py` 拡張: 依存関係チェック統合の単体テスト

2. **Integration テスト**:
   - `test_dependency_check_integration.py`: フェーズ実行時の依存関係チェック動作確認
   - `test_cli_dependency_flags.py`: CLIフラグによる動作変更の確認
   - 既存のE2Eテストの修正: 依存関係チェックを考慮した実行フロー

---

## 4. テストコード戦略判断

### テストコード戦略: BOTH_TEST

**判断根拠**:
- **既存テストファイルの拡張**: `tests/unit/test_main.py`, `tests/unit/phases/test_base_phase.py` に依存関係チェック関連のテストケースを追加
- **新規テストファイルの作成**: `tests/unit/utils/test_dependency_validator.py`, `tests/integration/test_dependency_check_integration.py` を新規作成
- **既存E2Eテストの修正**: `tests/e2e/test_phase*.py` で依存関係チェックがスキップされるよう修正（Phase 0完了状態の確保）

**詳細**:
1. **既存テスト拡張**:
   - `test_main.py`: CLIオプションのパースとバリデーション
   - `test_base_phase.py`: `run()`メソッドでの依存関係チェック呼び出し

2. **新規テスト作成**:
   - `test_dependency_validator.py`: 依存関係検証ロジックの網羅的テスト
   - `test_dependency_check_integration.py`: 実際のフェーズ実行における依存関係チェック動作

3. **既存テスト修正**:
   - E2Eテスト: Phase 1実行前にmetadata.jsonを操作し、依存フェーズを`completed`に設定

---

## 5. 影響範囲分析

### 5.1 既存コードへの影響

#### 高影響 (High Impact)
- **`main.py`**: CLIオプション追加、個別フェーズ実行ロジックへの依存関係チェック統合
- **`phases/base_phase.py`**: `run()`メソッドに依存関係チェックを統合
- **E2Eテスト全般**: 依存関係チェックを考慮したテストデータ準備が必要

#### 中影響 (Medium Impact)
- **`core/metadata_manager.py`**: 依存関係違反ログ記録メソッドの追加（オプション）
- **既存のIntegrationテスト**: 一部のテストで依存関係チェックの挙動を考慮

#### 低影響 (Low Impact)
- **`core/workflow_state.py`**: メタデータスキーマへの非破壊的なフィールド追加（将来拡張用）
- **既存のUnitテスト**: 依存関係チェックが無効な状態でのテストは影響なし

### 5.2 依存関係の変更

#### 新規追加
- `utils/dependency_validator.py` → `core/metadata_manager.py`
- `phases/base_phase.py` → `utils/dependency_validator.py`
- `main.py` → `utils/dependency_validator.py`

#### 変更なし
- 既存のモジュール間依存関係は変更なし

### 5.3 マイグレーション要否

**マイグレーション不要**

理由:
- 既存の`metadata.json`スキーマに非破壊的なフィールド追加のみ
- 既存のワークフローは依存関係チェックが自動的にスキップされる（すべてのフェーズが順次実行される前提）
- 後方互換性を維持

---

## 6. 変更・追加ファイルリスト

### 6.1 新規作成ファイル

```
scripts/ai-workflow/
├── utils/
│   └── dependency_validator.py          # 依存関係検証モジュール（新規）
│
└── tests/
    ├── unit/
    │   └── utils/
    │       └── test_dependency_validator.py   # Unitテスト（新規）
    └── integration/
        └── test_dependency_check_integration.py  # Integrationテスト（新規）
```

### 6.2 修正が必要な既存ファイル

```
scripts/ai-workflow/
├── main.py                              # CLIオプション追加、フェーズ実行ロジック修正
├── phases/
│   └── base_phase.py                    # run()メソッドに依存関係チェック統合
├── core/
│   └── metadata_manager.py              # （オプション）依存関係違反ログメソッド追加
│
└── tests/
    ├── unit/
    │   ├── test_main.py                 # CLIオプションのテストケース追加
    │   └── phases/
    │       └── test_base_phase.py       # 依存関係チェックのテストケース追加
    ├── integration/
    │   └── test_phase_separation.py     # 依存関係チェック考慮のテスト修正
    └── e2e/
        ├── test_phase0.py               # 依存関係考慮（必要に応じて）
        ├── test_phase1.py               # 依存関係考慮
        ├── test_phase2.py               # 依存関係考慮
        ├── test_phase3.py               # 依存関係考慮
        ├── test_phase4.py               # 依存関係考慮
        ├── test_phase5.py               # 依存関係考慮
        ├── test_phase6.py               # 依存関係考慮
        └── test_phase_all.py            # 依存関係考慮
```

### 6.3 削除が必要なファイル

**なし**

---

## 7. 詳細設計

### 7.1 新規モジュール: `utils/dependency_validator.py`

#### 7.1.1 PHASE_DEPENDENCIES 定義

```python
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
```

#### 7.1.2 設計上の重要なポイント

1. **DependencyErrorカスタム例外**:
   - 未完了フェーズの情報を保持
   - 明確なエラーメッセージを生成

2. **validate_phase_dependencies()関数**:
   - `skip_check`と`ignore_violations`の2つのモードをサポート
   - MetadataManagerを通じてフェーズステータスを取得
   - 詳細なログ出力（INFO/WARNING）

3. **ユーティリティ関数**:
   - `get_phase_dependencies()`: テストやデバッグ用
   - `get_all_phase_dependencies()`: ドキュメント生成や可視化用

---

### 7.2 既存モジュール修正: `main.py`

#### 7.2.1 CLIオプション追加

```python
@cli.command()
@click.option('--phase', required=True,
              type=click.Choice(['all', 'planning', 'requirements', 'design', 'test_scenario',
                                'implementation', 'test_implementation', 'testing',
                                'documentation', 'report', 'evaluation']))
@click.option('--issue', required=True, help='Issue number')
@click.option('--git-user', help='Git commit user name')
@click.option('--git-email', help='Git commit user email')
@click.option('--force-reset', is_flag=True, default=False,
              help='Clear metadata and restart from Phase 1')
# ━━━ 新規追加: 依存関係チェックフラグ ━━━
@click.option('--skip-dependency-check', is_flag=True, default=False,
              help='Skip dependency check and force phase execution')
@click.option('--ignore-dependencies', is_flag=True, default=False,
              help='Show warnings for dependency violations but continue execution')
@click.option('--preset', type=click.Choice(['requirements-only', 'design-phase',
                                              'implementation-phase', 'full-workflow']),
              help='Execute predefined phase preset')
# ━━━ 新規追加ここまで ━━━
def execute(phase: str, issue: str, git_user: str = None, git_email: str = None,
            force_reset: bool = False,
            skip_dependency_check: bool = False,  # 新規パラメータ
            ignore_dependencies: bool = False,     # 新規パラメータ
            preset: str = None):                   # 新規パラメータ
    """フェーズ実行"""

    # ━━━ 新規追加: オプション排他性チェック ━━━
    if preset and phase != 'all':
        click.echo('[ERROR] --preset and --phase cannot be used together. Please use only one.')
        sys.exit(1)

    if skip_dependency_check and ignore_dependencies:
        click.echo('[ERROR] --skip-dependency-check and --ignore-dependencies are mutually exclusive.')
        sys.exit(1)
    # ━━━ 新規追加ここまで ━━━

    # ━━━ 新規追加: プリセット処理 ━━━
    if preset:
        # プリセットに応じてphaseを上書き
        preset_mapping = {
            'requirements-only': 'requirements',
            'design-phase': 'design',           # Phase 1-2を実行（execute_phases_from）
            'implementation-phase': 'implementation',  # Phase 1-4を実行
            'full-workflow': 'all'
        }
        phase = preset_mapping[preset]
        click.echo(f'[INFO] Using preset: {preset} (executing phase: {phase})')
    # ━━━ 新規追加ここまで ━━━

    # ... 既存のコード ...

    # ━━━ 新規追加: 個別フェーズ実行時の依存関係チェック ━━━
    # (phase != 'all' の場合)
    if phase != 'all':
        from utils.dependency_validator import validate_phase_dependencies, DependencyError

        try:
            # 依存関係チェック
            validate_phase_dependencies(
                phase_name=phase,
                metadata=metadata_manager,
                skip_check=skip_dependency_check,
                ignore_violations=ignore_dependencies
            )
        except DependencyError as e:
            # 依存関係違反
            click.echo(f'[ERROR] {e.message}')
            click.echo('[INFO] Hint: Use --skip-dependency-check to bypass this check.')
            click.echo('[INFO] Hint: Use --ignore-dependencies to show warnings only.')
            sys.exit(1)
        except Exception as e:
            # その他のエラー
            click.echo(f'[ERROR] Dependency check failed: {e}')
            sys.exit(1)
    # ━━━ 新規追加ここまで ━━━

    # ... 既存のフェーズ実行コード ...
```

#### 7.2.2 プリセット実行の詳細設計

**プリセットマッピング**:
- `requirements-only`: Phase 1のみ実行
- `design-phase`: Phase 1-2を実行（`execute_phases_from('requirements', ...)`を呼び出し、Phase 2で停止）
- `implementation-phase`: Phase 1-4を実行（同様に`execute_phases_from('requirements', ...)`を呼び出し、Phase 4で停止）
- `full-workflow`: 全フェーズ実行（既存の`phase='all'`と同じ）

**注意**: プリセット実行時は依存関係チェックが自動的に有効（順次実行のため問題なし）

---

### 7.3 既存モジュール修正: `phases/base_phase.py`

#### 7.3.1 run()メソッドへの依存関係チェック統合

```python
def run(self) -> bool:
    """
    フェーズを実行してレビュー（リトライ機能付き）

    Returns:
        bool: 成功/失敗

    Notes:
        0. ━━━ 新規追加: 依存関係チェック ━━━
        1. フェーズステータスをin_progressに更新
        2. GitHubに進捗報告
        3. リトライループ（MAX_RETRIES=3）:
           - attempt=1: execute()を実行
           - attempt>=2: review() → revise()を実行
        4. 各試行の成功時、最終レビューへ進む
        5. 最大リトライ到達時は失敗終了
        6. Git自動commit & push（成功・失敗問わず実行）
    """
    MAX_RETRIES = 3

    git_manager = None
    final_status = 'failed'
    review_result = None

    try:
        # ━━━ 新規追加: 依存関係チェック ━━━
        from utils.dependency_validator import validate_phase_dependencies, DependencyError

        # CLIで指定されたフラグをメタデータから取得（将来拡張用）
        # 現時点では、main.pyでCLI実行前にチェック済みのため、ここでは再チェックしない
        # ただし、BasePhase.run()が直接呼ばれる場合（テスト等）に備えて防御的にチェック
        try:
            # デフォルトでは依存関係チェックを実施（CLIでスキップされていない限り）
            # メタデータに skip_dependency_check フラグが記録されているか確認
            skip_check = self.metadata.data.get('skip_dependency_check', False)
            ignore_violations = self.metadata.data.get('ignore_dependencies', False)

            validate_phase_dependencies(
                phase_name=self.phase_name,
                metadata=self.metadata,
                skip_check=skip_check,
                ignore_violations=ignore_violations
            )
        except DependencyError as e:
            # 依存関係違反
            print(f"[ERROR] {e.message}")
            self.update_phase_status(status='failed')
            self.post_progress(
                status='failed',
                details=f'Dependency check failed: {e.message}'
            )
            return False
        # ━━━ 新規追加ここまで ━━━

        # GitManagerを初期化
        from core.git_manager import GitManager
        git_manager = GitManager(
            repo_path=self.working_dir.parent.parent,  # リポジトリルート
            metadata_manager=self.metadata
        )

        # ... 既存のコード ...
```

#### 7.3.2 設計上の注意点

1. **二重チェック防止**:
   - `main.py`でCLI実行前にチェック済み
   - `BasePhase.run()`では防御的に再チェック（テスト等で直接呼ばれる場合）

2. **メタデータからのフラグ取得**:
   - 将来拡張: メタデータに`skip_dependency_check`フラグを記録
   - 現時点では、CLIフラグのみ使用（メタデータ記録は将来拡張）

3. **エラーハンドリング**:
   - DependencyError発生時、フェーズステータスを`failed`に更新
   - GitHubにエラーメッセージを投稿

---

### 7.4 既存モジュール修正（オプション）: `core/metadata_manager.py`

#### 7.4.1 依存関係違反ログ記録メソッド追加（将来拡張用）

```python
def log_dependency_violation(
    self,
    phase_name: str,
    missing_phases: List[str],
    action: str  # 'skipped', 'ignored', 'failed'
):
    """
    依存関係違反をメタデータに記録（将来拡張用）

    Args:
        phase_name: 実行しようとしたフェーズ名
        missing_phases: 未完了の依存フェーズリスト
        action: 実行された動作（skipped/ignored/failed）
    """
    if 'dependency_violations' not in self._state.data:
        self._state.data['dependency_violations'] = []

    from datetime import datetime

    violation = {
        'phase': phase_name,
        'missing_phases': missing_phases,
        'action': action,
        'timestamp': datetime.now().isoformat()
    }

    self._state.data['dependency_violations'].append(violation)
    self._state.save()
```

**注意**: このメソッドは将来拡張用であり、Phase 1実装では使用しない。Issue #319の後続Issueで実装予定。

---

### 7.5 データ構造設計

#### 7.5.1 metadata.json スキーマ拡張（将来拡張用）

```json
{
  "workflow_version": "1.0.0",
  "issue_number": "319",
  "skip_dependency_check": false,  // 新規フィールド（将来拡張用）
  "ignore_dependencies": false,     // 新規フィールド（将来拡張用）
  "dependency_violations": [        // 新規フィールド（将来拡張用）
    {
      "phase": "design",
      "missing_phases": ["requirements"],
      "action": "ignored",
      "timestamp": "2025-10-12T10:30:00"
    }
  ],
  "phases": {
    "requirements": {
      "status": "completed",
      // ... 既存フィールド ...
    },
    // ...
  }
}
```

**注意**: Phase 1実装では、メタデータへのフラグ記録は実装しない。CLIフラグのみ使用。

---

### 7.6 インターフェース設計

#### 7.6.1 `validate_phase_dependencies()` 関数

```python
def validate_phase_dependencies(
    phase_name: str,
    metadata: MetadataManager,
    skip_check: bool = False,
    ignore_violations: bool = False
) -> bool:
    """
    フェーズ依存関係を検証

    Parameters
    ----------
    phase_name : str
        実行しようとしているフェーズ名
    metadata : MetadataManager
        MetadataManagerインスタンス
    skip_check : bool, default=False
        依存関係チェックをスキップするか（--skip-dependency-check）
    ignore_violations : bool, default=False
        依存関係違反時も警告のみ表示して継続するか（--ignore-dependencies）

    Returns
    -------
    bool
        依存関係が満たされている場合True

    Raises
    ------
    DependencyError
        依存関係が満たされていない場合（ignore_violations=Falseの時）
    ValueError
        未知のフェーズ名が指定された場合

    Examples
    --------
    >>> metadata = MetadataManager(Path('metadata.json'))
    >>> validate_phase_dependencies('design', metadata)
    True

    >>> validate_phase_dependencies('design', metadata, skip_check=True)
    [WARNING] Dependency check skipped. Proceeding without validation.
    True

    >>> validate_phase_dependencies('design', metadata, ignore_violations=True)
    [WARNING] Dependency violation: Phase 'requirements' is not completed. Continuing anyway.
    True
    """
```

#### 7.6.2 DependencyError 例外

```python
class DependencyError(Exception):
    """依存関係違反エラー

    Attributes
    ----------
    phase_name : str
        実行しようとしているフェーズ名
    missing_phases : List[str]
        未完了の依存フェーズリスト
    message : str
        エラーメッセージ
    """
```

---

## 8. セキュリティ考慮事項

### 8.1 認証・認可

**影響なし**: 本機能は依存関係チェックのみであり、認証・認可には影響しない。

### 8.2 データ保護

**影響なし**: メタデータへの追加情報は非機密情報（フェーズ名、ステータス）のみ。

### 8.3 セキュリティリスクと対策

#### リスク1: 依存関係スキップによる不整合

**リスク内容**:
- `--skip-dependency-check`フラグを使用して依存関係をスキップした場合、前フェーズの成果物が存在しないためエラーが発生する可能性

**対策**:
- CLIで明確な警告メッセージを表示
- フェーズ実行時にファイル存在チェックを実施（既存の実装）
- ドキュメントにリスクを明記

#### リスク2: 無効なフェーズ名の指定

**リスク内容**:
- 未知のフェーズ名を指定した場合、ValueError発生

**対策**:
- `validate_phase_dependencies()`でフェーズ名のバリデーションを実施
- Clickの`Choice`型制約でCLI入力を制限

#### リスク3: メタデータ破損

**リスク内容**:
- 依存関係違反ログが大量に蓄積された場合、metadata.jsonが肥大化

**対策**:
- Phase 1実装では違反ログを記録しない（将来拡張用）
- 将来実装時にはログローテーション機能を追加

---

## 9. 非機能要件への対応

### 9.1 パフォーマンス（NFR-1.1, NFR-1.2）

#### NFR-1.1: 依存関係チェックの実行時間は100ms以内

**対応**:
- メタデータの読み取りは既存の`MetadataManager`を使用（メモリ内データ）
- 依存関係チェックはO(N)の単純なループ（N=依存フェーズ数、最大5）
- 実測では10ms以下を想定

**実装のポイント**:
```python
# 効率的な実装
required_phases = PHASE_DEPENDENCIES[phase_name]  # O(1)
for required_phase in required_phases:            # O(N)
    status = metadata.get_phase_status(required_phase)  # O(1)
```

#### NFR-1.2: メタデータの読み取り回数を最小化

**対応**:
- `MetadataManager`は既にメモリ内にデータを保持
- `get_phase_status()`はディクショナリアクセスのみ（ファイルI/Oなし）

### 9.2 保守性（NFR-2.1, NFR-2.2, NFR-2.3）

#### NFR-2.1: フェーズ依存関係は一箇所で管理

**対応**:
- `PHASE_DEPENDENCIES`定数を`utils/dependency_validator.py`で一元管理
- 変更時は1箇所の修正で完結

#### NFR-2.2: 新規フェーズの追加時、既存コードの変更を最小限に

**対応**:
- 新規フェーズ追加時は`PHASE_DEPENDENCIES`に1行追加するのみ
- `validate_phase_dependencies()`は汎用的な実装で変更不要

#### NFR-2.3: ドキュメントに依存関係図とプリセット一覧を記載

**対応**:
- `README.md`に以下を追加:
  - フェーズ依存関係図（Mermaid形式）
  - プリセット一覧（表形式）
  - 使用例

### 9.3 可用性・信頼性（NFR-3.1, NFR-3.2）

#### NFR-3.1: 依存関係チェック失敗時、メタデータが破損しない

**対応**:
- 依存関係チェックは読み取り専用操作（メタデータ変更なし）
- エラー時は`sys.exit(1)`で即座に終了（メタデータ保存前）

#### NFR-3.2: 外部ドキュメント指定時、ファイルコピーが失敗してもロールバック

**対応**:
- Phase 2実装（`--requirements-doc`オプション）で対応
- Phase 1実装範囲外

### 9.4 ユーザビリティ（NFR-4.1, NFR-4.2, NFR-4.3）

#### NFR-4.1: エラーメッセージは具体的で解決方法を提示

**対応**:
```
[ERROR] Dependency check failed: Phase 'requirements' must be completed before 'design'
[INFO] Hint: Use --skip-dependency-check to bypass this check.
[INFO] Hint: Use --ignore-dependencies to show warnings only.
```

#### NFR-4.2: CLIヘルプに全オプションとプリセットが表示

**対応**:
- `click.option(help=...)`に詳細な説明を記載
- `python main.py execute --help`で表示

#### NFR-4.3: 警告メッセージは `[WARNING]` プレフィックスで統一

**対応**:
```python
print(f"[WARNING] Dependency check skipped. Proceeding without validation.")
print(f"[WARNING] Dependency violation: Phase 'requirements' is not completed. Continuing anyway.")
```

---

## 10. 実装の順序

### Phase 1: コア機能実装（優先度: 高）

1. **`utils/dependency_validator.py` 新規作成**:
   - `PHASE_DEPENDENCIES` 定数定義
   - `DependencyError` クラス実装
   - `validate_phase_dependencies()` 関数実装
   - ユーティリティ関数（`get_phase_dependencies()`, `get_all_phase_dependencies()`）

2. **Unitテスト作成**:
   - `tests/unit/utils/test_dependency_validator.py` 新規作成
   - 依存関係チェックロジックの網羅的テスト

3. **`main.py` 修正**:
   - CLIオプション追加（`--skip-dependency-check`, `--ignore-dependencies`, `--preset`）
   - 個別フェーズ実行時の依存関係チェック統合
   - オプション排他性チェック

4. **`phases/base_phase.py` 修正**:
   - `run()`メソッドに依存関係チェック統合（防御的チェック）

5. **Unitテスト拡張**:
   - `tests/unit/test_main.py` 修正: CLIオプションのテストケース追加
   - `tests/unit/phases/test_base_phase.py` 修正: 依存関係チェックのテストケース追加

### Phase 2: 統合テスト（優先度: 高）

6. **Integrationテスト作成**:
   - `tests/integration/test_dependency_check_integration.py` 新規作成
   - フェーズ実行時の依存関係チェック動作確認

7. **既存E2Eテスト修正**:
   - `tests/e2e/test_phase*.py` 修正: 依存関係チェックを考慮したテストデータ準備

### Phase 3: ドキュメント更新（優先度: 中）

8. **README.md 更新**:
   - 使用例追加
   - プリセット一覧追加
   - フェーズ依存関係図追加

9. **CLAUDE.md 更新**:
   - 開発ワークフローへの依存関係チェックの影響を記載

### Phase 4: 将来拡張準備（優先度: 低）

10. **`core/metadata_manager.py` 拡張**:
    - `log_dependency_violation()` メソッド追加（実装のみ、使用しない）

11. **外部ドキュメント指定機能**:
    - Phase 2実装として後続Issueで実装（`--requirements-doc`オプション）

---

## 11. テスト計画

### 11.1 Unitテスト

#### `tests/unit/utils/test_dependency_validator.py`

```python
"""依存関係検証モジュールのUnitテスト"""
import pytest
from pathlib import Path
from utils.dependency_validator import (
    PHASE_DEPENDENCIES,
    DependencyError,
    validate_phase_dependencies,
    get_phase_dependencies,
    get_all_phase_dependencies
)
from core.metadata_manager import MetadataManager
from core.workflow_state import WorkflowState


class TestPhaseDependenciesDefinition:
    """PHASE_DEPENDENCIES 定義のテスト"""

    def test_phase_dependencies_structure(self):
        """依存関係定義の構造が正しいか"""
        assert isinstance(PHASE_DEPENDENCIES, dict)
        assert 'requirements' in PHASE_DEPENDENCIES
        assert 'design' in PHASE_DEPENDENCIES
        assert 'implementation' in PHASE_DEPENDENCIES

    def test_requirements_has_no_dependencies(self):
        """requirements フェーズは依存関係なし"""
        assert PHASE_DEPENDENCIES['requirements'] == []

    def test_design_depends_on_requirements(self):
        """design フェーズは requirements に依存"""
        assert PHASE_DEPENDENCIES['design'] == ['requirements']

    def test_implementation_depends_on_requirements_design_test_scenario(self):
        """implementation フェーズは requirements, design, test_scenario に依存"""
        assert set(PHASE_DEPENDENCIES['implementation']) == {
            'requirements', 'design', 'test_scenario'
        }


class TestDependencyError:
    """DependencyError クラスのテスト"""

    def test_dependency_error_single_phase(self):
        """単一フェーズの依存関係違反"""
        error = DependencyError(
            phase_name='design',
            missing_phases=['requirements']
        )
        assert error.phase_name == 'design'
        assert error.missing_phases == ['requirements']
        assert "Phase 'requirements' must be completed before 'design'" in str(error)

    def test_dependency_error_multiple_phases(self):
        """複数フェーズの依存関係違反"""
        error = DependencyError(
            phase_name='implementation',
            missing_phases=['requirements', 'design']
        )
        assert len(error.missing_phases) == 2
        assert "Phases 'requirements', 'design' must be completed before 'implementation'" in str(error)


class TestValidatePhaseDependencies:
    """validate_phase_dependencies 関数のテスト"""

    def test_validate_success_no_dependencies(self, tmp_path):
        """依存関係なしのフェーズ（requirements）は常に成功"""
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/test/test/issues/319',
            issue_title='Test'
        )
        metadata = MetadataManager(metadata_path)

        # Act
        result = validate_phase_dependencies('requirements', metadata)

        # Assert
        assert result is True

    def test_validate_success_dependencies_met(self, tmp_path):
        """依存関係が満たされている場合は成功"""
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/test/test/issues/319',
            issue_title='Test'
        )
        metadata = MetadataManager(metadata_path)
        metadata.update_phase_status('requirements', 'completed')

        # Act
        result = validate_phase_dependencies('design', metadata)

        # Assert
        assert result is True

    def test_validate_failure_dependency_not_met(self, tmp_path):
        """依存関係が満たされていない場合は DependencyError"""
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/test/test/issues/319',
            issue_title='Test'
        )
        metadata = MetadataManager(metadata_path)
        # requirements フェーズは pending のまま

        # Act & Assert
        with pytest.raises(DependencyError) as exc_info:
            validate_phase_dependencies('design', metadata)

        assert 'requirements' in str(exc_info.value)
        assert 'design' in str(exc_info.value)

    def test_validate_skip_check(self, tmp_path):
        """skip_check=True の場合は依存関係チェックをスキップ"""
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/test/test/issues/319',
            issue_title='Test'
        )
        metadata = MetadataManager(metadata_path)
        # requirements フェーズは pending のまま

        # Act
        result = validate_phase_dependencies('design', metadata, skip_check=True)

        # Assert
        assert result is True  # スキップされるため成功

    def test_validate_ignore_violations(self, tmp_path):
        """ignore_violations=True の場合は警告のみ表示して継続"""
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/test/test/issues/319',
            issue_title='Test'
        )
        metadata = MetadataManager(metadata_path)
        # requirements フェーズは pending のまま

        # Act
        result = validate_phase_dependencies('design', metadata, ignore_violations=True)

        # Assert
        assert result is True  # 警告のみで成功

    def test_validate_unknown_phase(self, tmp_path):
        """未知のフェーズ名は ValueError"""
        # Arrange
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='319',
            issue_url='https://github.com/test/test/issues/319',
            issue_title='Test'
        )
        metadata = MetadataManager(metadata_path)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            validate_phase_dependencies('unknown_phase', metadata)

        assert 'Unknown phase' in str(exc_info.value)


class TestUtilityFunctions:
    """ユーティリティ関数のテスト"""

    def test_get_phase_dependencies(self):
        """get_phase_dependencies 関数のテスト"""
        deps = get_phase_dependencies('design')
        assert deps == ['requirements']

    def test_get_all_phase_dependencies(self):
        """get_all_phase_dependencies 関数のテスト"""
        all_deps = get_all_phase_dependencies()
        assert isinstance(all_deps, dict)
        assert 'requirements' in all_deps
        assert 'design' in all_deps
```

#### テストカバレッジ目標

- **ライン カバレッジ**: 90%以上
- **ブランチ カバレッジ**: 85%以上

---

### 11.2 Integrationテスト

#### `tests/integration/test_dependency_check_integration.py`

```python
"""依存関係チェック統合テスト"""
import pytest
import subprocess
from pathlib import Path


class TestDependencyCheckIntegration:
    """依存関係チェックの統合テスト"""

    def test_execute_design_without_requirements_fails(self, tmp_path, setup_test_repo):
        """requirements 未完了で design を実行すると失敗"""
        # Arrange: 新規ワークフロー初期化
        result = subprocess.run(
            ['python', 'main.py', 'init', '--issue-url', 'https://github.com/test/test/issues/319'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

        # Act: design フェーズを実行（requirements が pending のまま）
        result = subprocess.run(
            ['python', 'main.py', 'execute', '--phase', 'design', '--issue', '319'],
            capture_output=True,
            text=True
        )

        # Assert: エラーで終了
        assert result.returncode == 1
        assert 'Dependency check failed' in result.stdout
        assert 'requirements' in result.stdout

    def test_execute_design_with_skip_dependency_check_succeeds(self, tmp_path, setup_test_repo):
        """--skip-dependency-check を指定すると依存関係チェックをスキップ"""
        # Arrange: 新規ワークフロー初期化
        subprocess.run(['python', 'main.py', 'init', '--issue-url', 'https://github.com/test/test/issues/319'])

        # Act: --skip-dependency-check を指定して design フェーズを実行
        result = subprocess.run(
            ['python', 'main.py', 'execute', '--phase', 'design', '--issue', '319', '--skip-dependency-check'],
            capture_output=True,
            text=True
        )

        # Assert: 警告が表示されるが実行される
        assert 'Dependency check skipped' in result.stdout
        # 注意: 実際にはファイル不在等で失敗する可能性があるため、ここではチェックスキップのみ確認

    def test_execute_design_with_ignore_dependencies_shows_warning(self, tmp_path, setup_test_repo):
        """--ignore-dependencies を指定すると警告のみ表示"""
        # Arrange
        subprocess.run(['python', 'main.py', 'init', '--issue-url', 'https://github.com/test/test/issues/319'])

        # Act
        result = subprocess.run(
            ['python', 'main.py', 'execute', '--phase', 'design', '--issue', '319', '--ignore-dependencies'],
            capture_output=True,
            text=True
        )

        # Assert
        assert 'Dependency violation' in result.stdout
        assert 'WARNING' in result.stdout
```

---

### 11.3 既存E2Eテスト修正

#### 修正が必要なテストファイル

- `tests/e2e/test_phase1.py`
- `tests/e2e/test_phase2.py`
- `tests/e2e/test_phase3.py`
- `tests/e2e/test_phase4.py`
- `tests/e2e/test_phase5.py`
- `tests/e2e/test_phase6.py`
- `tests/e2e/test_phase_all.py`

#### 修正方針

**Phase 1実行前に依存フェーズを完了状態に設定**:

```python
def test_phase1_requirements(self, test_env):
    """Phase 1 (requirements) の実行テスト"""
    # Arrange: Phase 0 (planning) を completed に設定（依存関係チェック対応）
    metadata = MetadataManager(test_env['metadata_path'])
    # Phase 1 は dependencies: [] のため、実際には不要
    # ただし、将来の拡張を考慮して明示的に設定

    # Act: Phase 1 実行
    result = subprocess.run(
        ['python', 'main.py', 'execute', '--phase', 'requirements', '--issue', test_env['issue_number']],
        capture_output=True,
        text=True,
        timeout=300
    )

    # Assert
    assert result.returncode == 0
```

**Phase 2実行前に Phase 1 を completed に設定**:

```python
def test_phase2_design(self, test_env):
    """Phase 2 (design) の実行テスト"""
    # Arrange: Phase 1 (requirements) を completed に設定
    metadata = MetadataManager(test_env['metadata_path'])
    metadata.update_phase_status('requirements', 'completed')

    # Act: Phase 2 実行
    result = subprocess.run(
        ['python', 'main.py', 'execute', '--phase', 'design', '--issue', test_env['issue_number']],
        capture_output=True,
        text=True,
        timeout=300
    )

    # Assert
    assert result.returncode == 0
```

---

## 12. 制約事項の遵守

### TC-1: 既存のメタデータスキーマとの互換性

**対応**:
- 新規フィールド（`skip_dependency_check`, `ignore_dependencies`, `dependency_violations`）は将来拡張用
- Phase 1実装では使用しないため、後方互換性を維持

### TC-2: 既存のフェーズクラスのインターフェース変更なし

**対応**:
- `BasePhase.run()`メソッドのシグネチャ変更なし
- 内部で依存関係チェックを呼び出すのみ

### TC-3: Python 3.8以上で動作

**対応**:
- 型ヒント（`Dict[str, List[str]]`）はPython 3.8対応
- `pathlib.Path`、`subprocess`はPython 3.8で利用可能

### TC-4: 既存のテストケースが破損しない

**対応**:
- E2Eテストは依存フェーズを`completed`に設定することで対応
- Unitテストは既存のテストケースに影響なし（新規テストケース追加のみ）

---

## 13. リスク分析

### リスク1: E2Eテストの修正漏れ

**リスク内容**:
- E2Eテスト修正時に一部のテストファイルで依存フェーズ設定を忘れ、テストが失敗する

**対策**:
- すべてのE2Eテストファイルを網羅的に確認
- CIパイプラインでテスト実行し、失敗を検出

**影響度**: 中
**発生確率**: 中

### リスク2: 依存関係定義の誤り

**リスク内容**:
- `PHASE_DEPENDENCIES`定義が実際のフェーズ依存関係と異なる

**対策**:
- 要件定義書の依存関係表と照合
- レビュー時に依存関係図を確認

**影響度**: 高
**発生確率**: 低

### リスク3: パフォーマンス劣化

**リスク内容**:
- 依存関係チェックにより実行時間が増加

**対策**:
- 依存関係チェックは10ms以下のオーバーヘッドのみ
- パフォーマンステスト実施

**影響度**: 低
**発生確率**: 低

---

## 14. 将来拡張

### Phase 2実装予定

1. **外部ドキュメント指定機能**:
   - `--requirements-doc`, `--design-doc`, `--test-scenario-doc`オプション
   - ファイル存在チェック、バリデーション、コピー処理

2. **プリセット実行の停止フェーズ指定**:
   - 現在はフェーズ指定のみ（Phase 1-Xすべて実行）
   - 将来は特定フェーズで停止するオプション追加

3. **依存関係違反ログの記録と可視化**:
   - `metadata.json`への違反ログ記録
   - レポートフェーズでの違反ログ可視化

### Phase 3実装候補

1. **フェーズ依存関係のYAML設定ファイル化**:
   - `PHASE_DEPENDENCIES`をYAMLファイルで管理
   - カスタムフェーズの追加が容易

2. **依存関係の可視化ツール**:
   - Mermaid/Graphvizによる依存関係図の自動生成

3. **ドライラン機能**:
   - `--dry-run`フラグで依存関係チェックのみ実行

---

## 15. まとめ

### 15.1 設計の要点

1. **EXTEND戦略**: 既存の`main.py`と`BasePhase`を拡張し、新規モジュール`dependency_validator.py`を統合
2. **UNIT_INTEGRATION テスト**: 依存関係検証ロジックのUnit テストと、フェーズ実行フローのIntegration テスト
3. **BOTH_TEST**: 既存テストの拡張と新規テストの作成を組み合わせ

### 15.2 品質ゲートの確認

- [x] **実装戦略の判断根拠が明記されている**: セクション2で詳細に記載
- [x] **テスト戦略の判断根拠が明記されている**: セクション3で詳細に記載
- [x] **既存コードへの影響範囲が分析されている**: セクション5で高・中・低に分類して分析
- [x] **変更が必要なファイルがリストアップされている**: セクション6で新規作成・修正・削除を明記
- [x] **設計が実装可能である**: セクション7で具体的なコード例と実装手順を提示

### 15.3 次のステップ

1. **設計レビュー**: 本設計書のクリティカルシンキングレビュー実施
2. **実装開始**: Phase 1 コア機能実装（セクション10の順序に従う）
3. **テスト実施**: Unit テスト、Integration テスト、E2Eテストの順に実施
4. **ドキュメント更新**: README.md、CLAUDE.mdの更新

---

## 変更履歴

| バージョン | 日付 | 変更内容 | 作成者 |
|----------|------|---------|--------|
| 1.0 | 2025-10-12 | 初版作成 | Claude (AI Workflow) |
