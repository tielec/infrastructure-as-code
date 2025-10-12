# 詳細設計書 - Issue #360

## プロジェクト情報

- **Issue番号**: #360
- **タイトル**: [FEATURE] AIワークフロー実行時のレジューム機能実装
- **状態**: open
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/360
- **ラベル**: enhancement
- **作成日**: 2025-10-12

---

## 0. Planning/Requirements Documentの確認

### 開発計画の概要

**Planning Document**: `.ai-workflow/issue-360/00_planning/output/planning.md`

- **実装戦略**: EXTEND（既存コードの拡張）
- **テスト戦略**: UNIT_INTEGRATION（ユニット + 統合テスト）
- **テストコード戦略**: CREATE_TEST（新規テストファイル作成）
- **見積もり工数**: 約12時間
- **リスク**: 中程度

**Requirements Document**: `.ai-workflow/issue-360/01_requirements/output/requirements.md`

主要な機能要件:
- FR-01: デフォルトでの自動レジューム機能
- FR-02: 強制リセットフラグ（`--force-reset`）
- FR-03: レジューム開始フェーズの優先順位決定
- FR-04: エッジケースの処理
- FR-05: レジューム状態のログ出力
- FR-06: `MetadataManager.clear()`メソッドの実装

---

## 1. 既存コードベース分析結果

### 1.1 影響範囲の特定

**新規作成ファイル**:
- `scripts/ai-workflow/utils/resume.py`: レジューム機能を管理するResumeManagerクラス

**修正が必要な既存ファイル**:
- `scripts/ai-workflow/main.py`: `execute()`コマンドへのレジューム機能統合、`--force-reset`フラグ追加
- `scripts/ai-workflow/core/metadata_manager.py`: `clear()`メソッド追加

**テストファイル（新規作成）**:
- `scripts/ai-workflow/tests/unit/utils/test_resume.py`: ResumeManagerのユニットテスト
- `scripts/ai-workflow/tests/integration/test_resume_integration.py`: レジューム機能の統合テスト

**ドキュメントファイル（更新）**:
- `scripts/ai-workflow/README.md`: レジューム機能の使用方法を追加

### 1.2 既存パターンの調査結果

**メタデータ管理パターン**:
- `WorkflowState`クラス: metadata.jsonの低レベルアクセス（core/workflow_state.py）
- `MetadataManager`クラス: WorkflowStateのラッパー、フェーズ実装で使いやすいインターフェース提供（core/metadata_manager.py）
- フェーズステータス: `PhaseStatus` Enum（pending/in_progress/completed/failed）

**既存のフェーズ実行パターン**:
- `main.py:execute_all_phases()`: 全フェーズを順次実行（Phase 1-8）
- `main.py:_execute_single_phase()`: 個別フェーズを実行
- 各フェーズは独立したクラス（phases/配下）

**テストパターン**:
- ユニットテスト: `tests/unit/core/`, `tests/unit/phases/`
- 統合テスト: `tests/integration/`
- テストディレクトリ構造が明確に分離されている

### 1.3 依存関係の分析

**ResumeManagerの依存**:
- `core.workflow_state.WorkflowState`: メタデータの読み書き
- `core.metadata_manager.MetadataManager`: メタデータマネージャー（ResumeManagerの初期化に必要）
- Python標準ライブラリのみ使用（外部依存なし）

**main.pyの依存**:
- 新規作成する`utils.resume.ResumeManager`をインポート
- 既存の`execute_all_phases()`関数にレジューム判定ロジックを追加

---

## 2. 実装戦略の判断

### 実装戦略: **EXTEND**

**判断根拠**:

1. **新規モジュールの作成**:
   - `scripts/ai-workflow/utils/resume.py`を新規作成してResumeManagerクラスを実装
   - 関心の分離: レジューム機能を独立したモジュールとして管理

2. **既存コードの拡張**:
   - `main.py`: `execute()`コマンドに`--force-reset`フラグ追加、`execute_all_phases()`関数にレジューム判定ロジックを追加
   - `metadata_manager.py`: `clear()`メソッドを追加（メタデータ削除機能）

3. **既存アーキテクチャの維持**:
   - メタデータJSON構造は変更なし（後方互換性を完全に維持）
   - フェーズ実行ロジックは変更なし
   - 既存の`WorkflowState`/`MetadataManager`クラスを活用

4. **後方互換性の維持**:
   - 既存の`--phase all`は自動レジュームがデフォルトになるが、`--force-reset`で従来の動作（最初から実行）も可能
   - メタデータ構造の変更がないため、既存のmetadata.jsonファイルとの互換性を維持

**結論**: 新規モジュール作成と既存コード拡張が中心のため、**EXTEND**が最適。

---

## 3. テスト戦略の判断

### テスト戦略: **UNIT_INTEGRATION**

**判断根拠**:

1. **ユニットテストの必要性**:
   - `ResumeManager`クラスの各メソッド（`can_resume()`, `get_resume_phase()`, `is_completed()`等）のロジック検証が必要
   - メタデータ状態の判定ロジック（failed/in_progress/pending）の正確性検証
   - エッジケース（メタデータ破損、不存在等）の網羅的なテスト

2. **統合テストの必要性**:
   - `main.py execute --phase all`との統合動作確認
   - メタデータの読み込み → レジューム判定 → フェーズ実行の一連のフロー検証
   - `--force-reset`フラグの動作確認
   - 実際のmetadata.jsonファイルを使用した動作確認

3. **BDDテスト不要の理由**:
   - エンドユーザー向けのユーザーストーリーではなく、CLI内部機能のため
   - 要件定義書にユーザーストーリー形式の記載がない
   - ユニットテストと統合テストで十分にカバー可能

**結論**: ロジック検証（ユニット）とCLI統合動作確認（統合）の両方が必要なため、**UNIT_INTEGRATION**が最適。

---

## 4. テストコード戦略の判断

### テストコード戦略: **CREATE_TEST**

**判断根拠**:

1. **新規テストファイル作成の理由**:
   - `ResumeManager`は新規クラスのため、既存テストファイルとの関連性が低い
   - 新規テストファイル作成:
     - `tests/unit/utils/test_resume.py`: ResumeManagerクラスのユニットテスト
     - `tests/integration/test_resume_integration.py`: レジューム機能の統合テスト

2. **既存テスト拡張不要の理由**:
   - `tests/unit/test_main.py`: 既存の`execute()`コマンドのテストだが、レジューム機能は別の関心事
   - `tests/unit/core/test_metadata_manager.py`: MetadataManagerの基本機能のテストであり、`clear()`メソッドは新規機能
   - ただし、`clear()`メソッドのテストは`test_metadata_manager.py`に追加することも検討（テストファイルの一貫性のため）

3. **テストの分離**:
   - レジューム機能は独立した機能のため、テストも独立させる
   - テストファイルの可読性と保守性が向上

**結論**: 新規機能のため、新規テストファイルを作成する**CREATE_TEST**が最適。ただし、`MetadataManager.clear()`のテストは既存の`test_metadata_manager.py`に追加する。

---

## 5. アーキテクチャ設計

### 5.1 システム全体図

```
┌─────────────────────────────────────────────────────────┐
│                    CLI (main.py)                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │ execute --phase all [--force-reset]              │   │
│  └──────────────┬───────────────────────────────────┘   │
│                 │                                         │
│                 ↓                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ レジューム判定ロジック                            │   │
│  │ ・ResumeManager.can_resume()                    │   │
│  │ ・ResumeManager.get_resume_phase()              │   │
│  └──────────────┬───────────────────────────────────┘   │
│                 │                                         │
│                 ↓                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ execute_all_phases() / run_phases_from()         │   │
│  └──────────────┬───────────────────────────────────┘   │
└─────────────────┼───────────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────────────┐
│         新規モジュール: utils/resume.py                 │
│  ┌──────────────────────────────────────────────────┐   │
│  │ ResumeManager                                    │   │
│  │ ・can_resume()                                   │   │
│  │ ・get_resume_phase()                             │   │
│  │ ・is_completed()                                 │   │
│  │ ・get_status_summary()                           │   │
│  │ ・reset()                                        │   │
│  └──────────────┬───────────────────────────────────┘   │
└─────────────────┼───────────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────────────┐
│      既存モジュール: core/metadata_manager.py           │
│  ┌──────────────────────────────────────────────────┐   │
│  │ MetadataManager (拡張)                           │   │
│  │ ・clear() ← 新規追加                             │   │
│  └──────────────┬───────────────────────────────────┘   │
└─────────────────┼───────────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────────────┐
│      既存モジュール: core/workflow_state.py             │
│  ┌──────────────────────────────────────────────────┐   │
│  │ WorkflowState                                    │   │
│  │ ・data['phases'][phase_name]['status']          │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 5.2 データフロー

```
1. ユーザーが `python main.py execute --issue 360 --phase all` を実行

2. main.py: メタデータ読み込み
   ↓
   MetadataManager(metadata_path) 初期化

3. main.py: ResumeManager 初期化
   ↓
   ResumeManager(metadata_manager)

4. main.py: --force-reset チェック
   ↓
   if --force-reset:
       ResumeManager.reset()
       execute_all_phases()  # Phase 1から実行
   else:
       レジューム判定 (ステップ5へ)

5. main.py: レジューム判定
   ↓
   if ResumeManager.can_resume():
       resume_phase = ResumeManager.get_resume_phase()
       if resume_phase is None:
           # 全フェーズ完了済み
           ログ表示して終了
       else:
           # レジューム実行
           status = ResumeManager.get_status_summary()
           ログ表示
           run_phases_from(resume_phase)  # レジューム開始フェーズから実行
   else:
       execute_all_phases()  # Phase 1から新規実行

6. フェーズ実行
   ↓
   _execute_single_phase(phase, ...)
```

### 5.3 コンポーネント間の関係

**依存関係**:
```
main.py
  → ResumeManager (新規)
    → MetadataManager (既存)
      → WorkflowState (既存)
        → metadata.json
```

**責務分担**:
- `main.py`: CLI、フェーズ実行制御、レジューム判定の呼び出し
- `ResumeManager`: レジューム可否判定、レジューム開始フェーズ決定、ステータスサマリー生成
- `MetadataManager`: メタデータの読み書き、フェーズステータス更新、メタデータクリア
- `WorkflowState`: metadata.jsonの低レベルアクセス

---

## 6. 詳細設計

### 6.1 ResumeManagerクラス設計

#### 6.1.1 クラス図

```python
class ResumeManager:
    """ワークフローのレジューム機能を管理"""

    # 属性
    metadata_manager: MetadataManager
    phases: List[str]  # フェーズリスト（Phase 1-8の順序）

    # メソッド
    def __init__(self, metadata_manager: MetadataManager) -> None
    def can_resume(self) -> bool
    def is_completed(self) -> bool
    def get_resume_phase(self) -> Optional[str]
    def get_status_summary(self) -> Dict[str, List[str]]
    def reset(self) -> None
    def _get_phases_by_status(self, status: str) -> List[str]
```

#### 6.1.2 メソッド詳細設計

##### `__init__(self, metadata_manager: MetadataManager)`

**責務**: ResumeManagerの初期化

**引数**:
- `metadata_manager`: MetadataManagerインスタンス

**処理フロー**:
```python
def __init__(self, metadata_manager: MetadataManager):
    """
    ResumeManagerの初期化

    Args:
        metadata_manager: MetadataManagerインスタンス
    """
    self.metadata_manager = metadata_manager
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
```

**注意事項**:
- `phases`リストは`main.py:execute_all_phases()`と同じ順序を保つ
- planningフェーズは含めない（README.mdの記載に従う）

---

##### `can_resume(self) -> bool`

**責務**: レジューム可能かチェック

**戻り値**:
- `True`: レジューム可能
- `False`: レジューム不可（新規ワークフローとして実行）

**処理フロー**:
```python
def can_resume(self) -> bool:
    """
    レジューム可能かチェック

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
```

**エッジケース処理**:
- メタデータ不存在: `False`を返す（新規ワークフロー）
- メタデータ破損: 呼び出し元でtry-exceptハンドリング（後述）

---

##### `is_completed(self) -> bool`

**責務**: 全フェーズが完了しているかチェック

**戻り値**:
- `True`: 全フェーズ完了
- `False`: 未完了フェーズあり

**処理フロー**:
```python
def is_completed(self) -> bool:
    """
    全フェーズが完了しているかチェック

    Returns:
        bool: 全フェーズが完了している場合True
    """
    phases_data = self.metadata_manager.data['phases']

    for phase in self.phases:
        status = phases_data[phase]['status']
        if status != 'completed':
            return False

    return True
```

---

##### `get_resume_phase(self) -> Optional[str]`

**責務**: レジューム開始フェーズを決定

**戻り値**:
- `str`: レジューム開始フェーズ名
- `None`: レジューム不要（全フェーズ完了）

**処理フロー**:
```python
def get_resume_phase(self) -> Optional[str]:
    """
    レジューム開始フェーズを取得

    優先順位:
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
```

**設計判断**:
- 最初に見つかったフェーズから再開（順序保証）
- failedを最優先（失敗したフェーズからやり直す）

---

##### `get_status_summary(self) -> Dict[str, List[str]]`

**責務**: 各フェーズのステータスサマリーを取得（ログ出力用）

**戻り値**:
```python
{
    'completed': ['requirements', 'design', ...],
    'failed': ['test_implementation'],
    'in_progress': [],
    'pending': ['testing', 'documentation', ...]
}
```

**処理フロー**:
```python
def get_status_summary(self) -> Dict[str, List[str]]:
    """
    各フェーズのステータスサマリーを取得

    Returns:
        Dict[str, List[str]]: ステータスごとのフェーズリスト
    """
    return {
        'completed': self._get_phases_by_status('completed'),
        'failed': self._get_phases_by_status('failed'),
        'in_progress': self._get_phases_by_status('in_progress'),
        'pending': self._get_phases_by_status('pending')
    }

def _get_phases_by_status(self, status: str) -> List[str]:
    """
    指定ステータスのフェーズリストを取得

    Args:
        status: フェーズステータス

    Returns:
        List[str]: フェーズ名リスト
    """
    phases_data = self.metadata_manager.data['phases']
    return [
        phase for phase in self.phases
        if phases_data[phase]['status'] == status
    ]
```

---

##### `reset(self) -> None`

**責務**: メタデータとワークフローディレクトリを削除

**処理フロー**:
```python
def reset(self) -> None:
    """
    メタデータをクリアして最初からやり直し

    Note:
        MetadataManager.clear()を呼び出す
    """
    self.metadata_manager.clear()
```

**注意事項**:
- 実際の削除処理は`MetadataManager.clear()`に委譲
- 破壊的操作のため、呼び出し元（main.py）で`--force-reset`フラグのチェックが必須

---

### 6.2 MetadataManager.clear()メソッド設計

#### 6.2.1 メソッド詳細

**責務**: メタデータファイルとワークフローディレクトリを削除

**引数**: なし

**戻り値**: なし

**処理フロー**:
```python
def clear(self) -> None:
    """
    メタデータとワークフローディレクトリをクリア

    Note:
        - metadata.jsonファイルを削除
        - ワークフローディレクトリ全体を削除
        - 削除前にログで警告を表示
        - 削除対象が存在しない場合はスキップ（エラーなし）
    """
    import shutil

    # メタデータファイル削除
    if self.metadata_path.exists():
        import click
        click.echo(f"[INFO] Clearing metadata: {self.metadata_path}")
        self.metadata_path.unlink()

    # ワークフローディレクトリ削除
    if self.workflow_dir.exists():
        import click
        click.echo(f"[INFO] Removing workflow directory: {self.workflow_dir}")
        shutil.rmtree(self.workflow_dir)
        click.echo(f"[OK] Workflow directory removed successfully")
```

**セキュリティ考慮事項**:
- 削除対象が`.ai-workflow/issue-XXX`ディレクトリ配下であることを確認（誤削除防止）
- パス検証を追加することを検討（実装フェーズで判断）

**エラーハンドリング**:
- ファイル不存在: エラーなし（スキップ）
- 権限エラー: 例外発生（呼び出し元でハンドリング）

---

### 6.3 main.pyの修正設計

#### 6.3.1 `--force-reset`フラグの追加

**修正箇所**: `execute()`コマンドの引数定義

```python
@cli.command()
@click.option('--phase', required=True,
              type=click.Choice(['all', 'planning', 'requirements', 'design', 'test_scenario',
                                'implementation', 'test_implementation', 'testing',
                                'documentation', 'report']))
@click.option('--issue', required=True, help='Issue number')
@click.option('--git-user', help='Git commit user name')
@click.option('--git-email', help='Git commit user email')
@click.option('--force-reset', is_flag=True, default=False,
              help='Clear metadata and restart from Phase 1')  # ← 新規追加
def execute(phase: str, issue: str, git_user: str = None, git_email: str = None,
            force_reset: bool = False):  # ← 引数追加
    """フェーズ実行"""
    # ... 既存コード ...
```

#### 6.3.2 `execute_all_phases()`関数へのレジューム判定の追加

**修正箇所**: `execute()`コマンドの`--phase all`処理部分

**修正前**（main.py:581-606行目）:
```python
if phase == 'all':
    click.echo('[INFO] Starting all phases execution')
    try:
        result = execute_all_phases(
            issue=issue,
            repo_root=repo_root,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )
        # ... 既存コード ...
```

**修正後**:
```python
if phase == 'all':
    click.echo('[INFO] Starting all phases execution')

    # ━━━ 新規追加: レジューム判定 ━━━
    from utils.resume import ResumeManager
    resume_manager = ResumeManager(metadata_manager)

    # --force-reset フラグチェック
    if force_reset:
        click.echo('[INFO] --force-reset specified. Restarting from Phase 1...')
        resume_manager.reset()

        # 新規ワークフローとして実行
        try:
            result = execute_all_phases(
                issue=issue,
                repo_root=repo_root,
                metadata_manager=metadata_manager,
                claude_client=claude_client,
                github_client=github_client
            )
            # ... 既存の結果処理 ...
        except Exception as e:
            # ... 既存のエラーハンドリング ...

    # レジューム可能性チェック
    elif resume_manager.can_resume():
        resume_phase = resume_manager.get_resume_phase()

        if resume_phase is None:
            # 全フェーズ完了済み
            click.echo('[INFO] All phases are already completed.')
            click.echo('[INFO] To re-run, use --force-reset flag.')
            sys.exit(0)

        # レジューム実行
        status = resume_manager.get_status_summary()
        click.echo('[INFO] Existing workflow detected.')
        click.echo(f"[INFO] Completed phases: {', '.join(status['completed'])}")
        if status['failed']:
            click.echo(f"[INFO] Failed phases: {', '.join(status['failed'])}")
        if status['in_progress']:
            click.echo(f"[INFO] In-progress phases: {', '.join(status['in_progress'])}")
        click.echo(f"[INFO] Resuming from phase: {resume_phase}")

        # レジューム開始フェーズから実行
        try:
            result = execute_phases_from(
                start_phase=resume_phase,
                issue=issue,
                repo_root=repo_root,
                metadata_manager=metadata_manager,
                claude_client=claude_client,
                github_client=github_client
            )
            # ... 既存の結果処理 ...
        except Exception as e:
            # ... 既存のエラーハンドリング ...

    else:
        # 新規ワークフロー（メタデータ不存在 or 全フェーズpending）
        click.echo('[INFO] Starting new workflow.')
        try:
            result = execute_all_phases(
                issue=issue,
                repo_root=repo_root,
                metadata_manager=metadata_manager,
                claude_client=claude_client,
                github_client=github_client
            )
            # ... 既存の結果処理 ...
        except Exception as e:
            # ... 既存のエラーハンドリング ...
    # ━━━ 新規追加ここまで ━━━
```

#### 6.3.3 `execute_phases_from()`ヘルパー関数の追加

**新規追加**: レジューム開始フェーズから実行する関数

```python
def execute_phases_from(
    start_phase: str,
    issue: str,
    repo_root: Path,
    metadata_manager: MetadataManager,
    claude_client: ClaudeAgentClient,
    github_client: GitHubClient
) -> Dict[str, Any]:
    """
    指定フェーズから全フェーズを順次実行（レジューム用）

    Args:
        start_phase: 開始フェーズ名
        issue: Issue番号（文字列）
        repo_root: リポジトリルートパス
        metadata_manager: メタデータマネージャー
        claude_client: Claude Agent SDKクライアント
        github_client: GitHub APIクライアント

    Returns:
        Dict[str, Any]: 実行結果サマリー（execute_all_phases()と同じ形式）
    """
    # フェーズリスト定義
    all_phases = [
        'requirements',
        'design',
        'test_scenario',
        'implementation',
        'test_implementation',
        'testing',
        'documentation',
        'report'
    ]

    # 開始フェーズのインデックス取得
    if start_phase not in all_phases:
        raise ValueError(f"Unknown phase: {start_phase}")

    start_index = all_phases.index(start_phase)
    phases = all_phases[start_index:]  # 開始フェーズから最後まで

    # execute_all_phases()と同じ処理（フェーズリストのみ異なる）
    results = {}
    start_time = time.time()
    total_phases = len(phases)

    # ヘッダー表示
    click.echo(f"\n{'='*60}")
    click.echo(f"AI Workflow Resume Execution - Issue #{issue}")
    click.echo(f"Starting from: {start_phase}")
    click.echo(f"{'='*60}\n")

    # フェーズループ（execute_all_phases()と同じロジック）
    for i, phase in enumerate(phases, 1):
        # ... 既存のexecute_all_phases()と同じ処理 ...
        # （省略）

    # 成功サマリー生成
    return _generate_success_summary(
        phases=phases,
        results=results,
        start_time=start_time,
        metadata_manager=metadata_manager
    )
```

---

### 6.4 エラーハンドリング設計

#### 6.4.1 メタデータ破損時の処理

**発生箇所**: `ResumeManager.can_resume()`呼び出し時

**処理方針**:
```python
# main.py execute() コマンド内

try:
    from utils.resume import ResumeManager
    resume_manager = ResumeManager(metadata_manager)

    if resume_manager.can_resume():
        # ... レジューム処理 ...
    else:
        # ... 新規ワークフロー処理 ...

except json.JSONDecodeError as e:
    # メタデータJSON破損
    click.echo('[WARNING] metadata.json is corrupted. Starting as new workflow.')
    click.echo(f'[DEBUG] Error: {e}')

    # 新規ワークフローとして実行
    result = execute_all_phases(...)

except Exception as e:
    # その他のエラー
    click.echo(f'[ERROR] {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

#### 6.4.2 `clear()`メソッドのエラーハンドリング

**発生しうるエラー**:
- `PermissionError`: 削除権限なし
- `OSError`: ディレクトリ削除失敗

**処理方針**:
```python
# MetadataManager.clear()

def clear(self) -> None:
    """メタデータとワークフローディレクトリをクリア"""
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
```

---

## 7. データ構造設計

### 7.1 metadata.jsonの構造（既存、変更なし）

```json
{
  "issue_number": "360",
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/360",
  "issue_title": "[FEATURE] AIワークフロー実行時のレジューム機能実装",
  "workflow_version": "1.0.0",
  "current_phase": "design",
  "design_decisions": {
    "implementation_strategy": "EXTEND",
    "test_strategy": "UNIT_INTEGRATION",
    "test_code_strategy": "CREATE_TEST"
  },
  "cost_tracking": {
    "total_input_tokens": 50000,
    "total_output_tokens": 10000,
    "total_cost_usd": 1.5
  },
  "phases": {
    "planning": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T10:00:00Z",
      "completed_at": "2025-10-12T10:30:00Z",
      "review_result": "PASS"
    },
    "requirements": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T10:30:00Z",
      "completed_at": "2025-10-12T11:00:00Z",
      "review_result": "PASS"
    },
    "design": {
      "status": "in_progress",
      "retry_count": 0,
      "started_at": "2025-10-12T11:00:00Z",
      "completed_at": null,
      "review_result": null
    },
    "test_scenario": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    },
    "implementation": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    },
    "test_implementation": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    },
    "testing": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    },
    "documentation": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    },
    "report": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    }
  },
  "created_at": "2025-10-12T10:00:00Z",
  "updated_at": "2025-10-12T11:00:00Z"
}
```

**設計判断**: 既存構造を変更しない（後方互換性維持）

---

### 7.2 ResumeManager内部データ構造

**フェーズリスト**:
```python
self.phases = [
    'requirements',       # Phase 1
    'design',             # Phase 2
    'test_scenario',      # Phase 3
    'implementation',     # Phase 4
    'test_implementation',# Phase 5
    'testing',            # Phase 6
    'documentation',      # Phase 7
    'report'              # Phase 8
]
```

**ステータスサマリー**:
```python
{
    'completed': ['requirements', 'design'],
    'failed': ['test_implementation'],
    'in_progress': [],
    'pending': ['testing', 'documentation', 'report']
}
```

---

## 8. 影響範囲分析

### 8.1 既存コードへの影響

| ファイルパス | 変更内容 | 影響度 | 備考 |
|------------|---------|--------|------|
| `scripts/ai-workflow/utils/resume.py` | **新規作成** | 新規 | ResumeManager実装 |
| `scripts/ai-workflow/main.py` | `execute()`コマンドに`--force-reset`引数追加、レジューム判定ロジック追加 | 中 | 既存の`--phase all`動作が変わる（自動レジューム） |
| `scripts/ai-workflow/core/metadata_manager.py` | `clear()`メソッド追加 | 小 | 新規メソッド追加のみ |
| `scripts/ai-workflow/README.md` | レジューム機能のドキュメント追加 | 小 | ドキュメント更新 |

### 8.2 変更が不要なファイル

- `scripts/ai-workflow/core/workflow_state.py`: メタデータ構造は変更なし、既存APIのみ使用
- `scripts/ai-workflow/core/claude_agent_client.py`: フェーズ実行ロジックは変更なし
- `scripts/ai-workflow/core/github_client.py`: GitHub API連携は変更なし
- 各Phaseファイル（`phases/*.py`）: フェーズ実装は変更なし

### 8.3 依存関係の変更

**新規依存の追加**: なし
- Python標準ライブラリと既存モジュール（`MetadataManager`, `WorkflowState`）のみ使用

**既存依存の変更**: なし

### 8.4 マイグレーション要否

**不要**

**理由**:
- メタデータJSON構造の変更なし
- 既存の`metadata.json`ファイルとの互換性を完全に維持
- 既存ワークフローへの影響なし（レジューム機能は`--phase all`実行時のみ動作）

---

## 9. セキュリティ考慮事項

### 9.1 破壊的操作の防止

**`--force-reset`フラグの使用**:
- ユーザーが明示的に指定しない限り、メタデータは削除されない
- ログで警告メッセージを表示

**`clear()`メソッドの安全性**:
- 削除対象が`.ai-workflow/issue-XXX`ディレクトリ配下であることを確認
- パス検証を追加することを検討（実装フェーズで判断）

### 9.2 データ保護

**メタデータ保護**:
- 削除前にログで警告を表示
- 削除対象ファイル/ディレクトリが存在しない場合はスキップ（エラーなし）

### 9.3 認証・認可

**該当なし**: ローカルファイル操作のみ

---

## 10. 非機能要件への対応

### 10.1 パフォーマンス（NFR-01）

**要件**: レジューム判定処理の追加オーバーヘッドは1秒未満

**対応**:
- メタデータ読み込みは既存処理で実施済み（追加コストなし）
- レジューム判定ロジックはシンプルなループ処理のみ（O(n)、n=8フェーズ）
- 複雑な計算なし

**計測方法**:
- Phase 6（テスト実行）でパフォーマンス測定を実施
- `time`コマンドで`--phase all`の起動時間を計測

### 10.2 信頼性（NFR-02）

**要件**: メタデータ読み込みエラーやファイルシステムエラーが発生しても、システムが適切に動作

**対応**:
- メタデータJSON破損時: `try-except`で捕捉、新規ワークフローとして継続実行
- ファイルI/Oエラー時: 適切なエラーメッセージを表示
- 例外処理により予期しない終了を防止

### 10.3 保守性（NFR-03）

**要件**: レジューム機能は`ResumeManager`クラスとして独立して実装

**対応**:
- `ResumeManager`クラスは`utils/resume.py`に配置（関心の分離）
- 既存の`WorkflowState`クラスを活用し、重複実装を避ける
- `main.py`の変更は最小限（レジューム判定ロジックの呼び出しのみ）
- コードコメントを適切に記載（各メソッドの目的、引数、戻り値）

### 10.4 後方互換性（NFR-04）

**要件**: 既存のワークフローに影響を与えず、既存の`metadata.json`ファイルと互換性を維持

**対応**:
- メタデータJSON構造の変更なし
- 既存の`metadata.json`ファイルをそのまま読み込み可能
- `--phase all`のデフォルト動作が変わることをREADME.mdで明記

### 10.5 セキュリティ（NFR-05）

**要件**: `clear()`メソッドの破壊的操作によるデータ損失を防止

**対応**:
- `--force-reset`フラグを明示的に指定した場合のみ`clear()`を実行
- 削除実行前にログで警告メッセージを表示
- 削除対象が意図しないディレクトリでないことを検証（パス検証）

---

## 11. 実装の順序

### 11.1 推奨実装順序

**Phase 4（実装）での推奨順序**:

1. **`scripts/ai-workflow/utils/resume.py`の新規作成**（1.5h）
   - ResumeManagerクラスの骨格作成
   - `__init__()`メソッド実装
   - `can_resume()`メソッド実装
   - `is_completed()`メソッド実装
   - `get_resume_phase()`メソッド実装
   - `get_status_summary()`メソッド実装
   - `reset()`メソッド実装
   - `_get_phases_by_status()`ヘルパーメソッド実装

2. **`scripts/ai-workflow/core/metadata_manager.py`の拡張**（0.5h）
   - `clear()`メソッドの実装
   - エラーハンドリングの追加

3. **`scripts/ai-workflow/main.py`の拡張**（1h）
   - `--force-reset`引数の追加
   - `execute_phases_from()`ヘルパー関数の実装
   - `execute()`コマンドへのレジューム機能統合
   - レジューム状態のログ出力
   - エラーハンドリングの追加

### 11.2 依存関係の考慮

**実装順序の理由**:
1. `resume.py`（独立したモジュール）→ 依存なし、先に実装可能
2. `metadata_manager.py`（`resume.py`から呼ばれる）→ `resume.py`と並行実装可能
3. `main.py`（`resume.py`と`metadata_manager.py`を使用）→ 最後に実装

---

## 12. 変更・追加ファイルリスト

### 12.1 新規作成ファイル

| ファイルパス | 説明 |
|------------|------|
| `scripts/ai-workflow/utils/resume.py` | ResumeManagerクラス実装 |
| `scripts/ai-workflow/tests/unit/utils/test_resume.py` | ResumeManagerのユニットテスト |
| `scripts/ai-workflow/tests/integration/test_resume_integration.py` | レジューム機能の統合テスト |

### 12.2 修正が必要な既存ファイル

| ファイルパス | 変更内容 |
|------------|---------|
| `scripts/ai-workflow/main.py` | `--force-reset`引数追加、レジューム判定ロジック追加、`execute_phases_from()`関数追加 |
| `scripts/ai-workflow/core/metadata_manager.py` | `clear()`メソッド追加 |
| `scripts/ai-workflow/tests/unit/core/test_metadata_manager.py` | `clear()`メソッドのテストケース追加 |
| `scripts/ai-workflow/README.md` | レジューム機能のドキュメント追加 |

### 12.3 削除が必要なファイル

**なし**

---

## 13. テストシナリオ概要（Phase 3で詳細化）

### 13.1 ユニットテスト

**テストファイル**: `tests/unit/utils/test_resume.py`

**テスト対象**:
- `ResumeManager.__init__()`: 初期化が正しく行われるか
- `ResumeManager.can_resume()`: 各シナリオで正しく判定されるか
  - メタデータ不存在 → False
  - 全フェーズpending → False
  - 1フェーズでもcompleted/failed/in_progress → True
  - 全フェーズcompleted → False
- `ResumeManager.is_completed()`: 全フェーズ完了判定が正しいか
- `ResumeManager.get_resume_phase()`: 優先順位に従って正しいフェーズが返されるか
  - failed最優先
  - in_progress次点
  - pending最後
  - 全completed → None
- `ResumeManager.get_status_summary()`: 正しいサマリーが返されるか
- `ResumeManager.reset()`: `MetadataManager.clear()`が呼ばれるか（モック使用）

**テストファイル**: `tests/unit/core/test_metadata_manager.py`（既存ファイルに追加）

**テスト対象**:
- `MetadataManager.clear()`: メタデータファイルとディレクトリが削除されるか

### 13.2 統合テスト

**テストファイル**: `tests/integration/test_resume_integration.py`

**テスト対象**:
- `--phase all`実行時の自動レジューム動作確認
  - Phase 5失敗 → 再実行時にPhase 5から再開
  - Phase 3失敗 → 再実行時にPhase 3から再開
- `--force-reset`フラグの動作確認
  - メタデータクリア → Phase 1から実行
- 全フェーズ完了時の動作確認
  - 完了メッセージ表示 → 実行終了
- エッジケース
  - メタデータ不存在 → 新規ワークフローとして実行
  - メタデータ破損 → 警告表示 → 新規ワークフローとして実行

---

## 14. ドキュメント更新計画

### 14.1 README.md更新内容

**追加セクション**: レジューム機能

```markdown
## レジューム機能

AIワークフローは、`--phase all`実行中に途中のフェーズで失敗した場合、自動的に失敗したフェーズから再開するレジューム機能をサポートしています。

### デフォルト動作: 自動レジューム

`--phase all`実行時は**常に自動レジューム**を行います。

```bash
# デフォルトで自動レジューム
python scripts/ai-workflow/main.py execute --issue 360 --phase all

# 出力例：
# [INFO] Existing workflow detected.
# [INFO] Completed phases: requirements, design, test_scenario, implementation
# [INFO] Failed phases: test_implementation
# [INFO] Resuming from phase: test_implementation
```

### 強制リセット: --force-reset

最初から実行したい場合は`--force-reset`フラグを使用します。

```bash
# メタデータをクリアして最初から実行
python scripts/ai-workflow/main.py execute --issue 360 --phase all --force-reset

# 出力例：
# [INFO] --force-reset specified. Restarting from Phase 1...
# [INFO] Clearing metadata: .ai-workflow/issue-360/metadata.json
# [INFO] Removing workflow directory: .ai-workflow/issue-360
# [OK] Workflow directory removed successfully
# [INFO] Starting new workflow.
```

### レジューム開始フェーズの決定

以下の優先順位でレジューム開始フェーズを決定します：

1. **failedフェーズ**: 最初に失敗したフェーズから再開
2. **in_progressフェーズ**: 異常終了したフェーズから再開
3. **pendingフェーズ**: 最初の未実行フェーズから再開
4. **全フェーズcompleted**: 既に完了済みメッセージを表示して終了

### 全フェーズ完了時の動作

全フェーズが既に完了している場合は、完了メッセージを表示して終了します。

```bash
python scripts/ai-workflow/main.py execute --issue 360 --phase all

# 出力例：
# [INFO] All phases are already completed.
# [INFO] To re-run, use --force-reset flag.
```

### エッジケース

#### メタデータ不存在

メタデータファイルが存在しない場合は、新規ワークフローとして実行します。

```bash
# .ai-workflow/issue-360/metadata.json が存在しない場合
python scripts/ai-workflow/main.py execute --issue 360 --phase all

# 出力例：
# [INFO] Starting new workflow.
```

#### メタデータ破損

メタデータファイルが破損している場合は、警告を表示して新規ワークフローとして実行します。

```bash
# metadata.json が破損している場合
python scripts/ai-workflow/main.py execute --issue 360 --phase all

# 出力例：
# [WARNING] metadata.json is corrupted. Starting as new workflow.
# [INFO] Starting new workflow.
```
```

---

## 15. 品質ゲートチェックリスト

本設計書は、Phase 2の品質ゲート（必須要件）を満たしています：

- [x] **実装戦略の判断根拠が明記されている**: セクション2で**EXTEND**を選択し、判断根拠を4点記載
- [x] **テスト戦略の判断根拠が明記されている**: セクション3で**UNIT_INTEGRATION**を選択し、判断根拠を3点記載
- [x] **テストコード戦略の判断根拠が明記されている**: セクション4で**CREATE_TEST**を選択し、判断根拠を3点記載
- [x] **既存コードへの影響範囲が分析されている**: セクション8で影響範囲を詳細に分析（変更ファイル、変更不要ファイル、依存関係、マイグレーション要否）
- [x] **変更が必要なファイルがリストアップされている**: セクション12で新規作成ファイル、修正ファイル、削除ファイルをリスト化
- [x] **設計が実装可能である**:
  - セクション6でクラス設計、メソッド詳細設計、処理フロー、エラーハンドリングを具体的に記載
  - セクション11で実装順序と依存関係を明記
  - コードスニペットを多用し、実装イメージを明確化

---

## 16. まとめ

### 16.1 設計のポイント

1. **関心の分離**: レジューム機能を`ResumeManager`クラスとして独立したモジュールに実装
2. **既存資産の活用**: `WorkflowState`, `MetadataManager`を活用し、重複実装を避ける
3. **後方互換性の維持**: メタデータJSON構造は変更せず、既存ワークフローとの互換性を保つ
4. **ユーザビリティ向上**: デフォルトで自動レジューム、`--force-reset`で従来の動作も可能
5. **エラーハンドリングの徹底**: メタデータ破損、ファイルI/Oエラーに適切に対応

### 16.2 次のステップ

**Phase 3（テストシナリオ）**:
- セクション13の概要を元に、詳細なテストケースを作成
- エッジケースの網羅的な洗い出し
- テストデータの準備

**Phase 4（実装）**:
- セクション11の実装順序に従って実装
- セクション6の詳細設計に基づいてコーディング

**Phase 5（テストコード実装）**:
- Phase 3で作成したテストシナリオに基づいてテストコードを実装

---

**作成日**: 2025-10-12
**作成者**: Claude AI (Phase 2: Design)
**レビュー状態**: 未レビュー
**承認者**: -
**承認日**: -
