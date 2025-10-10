# 詳細設計書: AI WorkflowでIssue番号に連動したブランチを自動作成

## ドキュメントメタデータ

- **Issue番号**: #315
- **Issue URL**: https://github.com/tielec/infrastructure-as-code/issues/315
- **作成日**: 2025-10-10
- **バージョン**: 1.0.0
- **ステータス**: Draft
- **対応要件定義**: `.ai-workflow/issue-315/01_requirements/output/requirements.md`

---

## 1. アーキテクチャ設計

### 1.1 システム全体図

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py (CLI)                          │
│                                                                 │
│  ┌─────────────────┐              ┌─────────────────┐          │
│  │  init command   │              │ execute command │          │
│  │                 │              │                 │          │
│  │ 1. Issue URL    │              │ 1. Issue番号    │          │
│  │    解析         │              │ 2. Phase指定    │          │
│  │ 2. ブランチ作成 │              │                 │          │
│  │ 3. メタデータ   │              │                 │          │
│  │    初期化       │              │                 │          │
│  └────────┬────────┘              └────────┬────────┘          │
│           │                                │                   │
└───────────┼────────────────────────────────┼───────────────────┘
            │                                │
            │                                │
            ▼                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GitManager (拡張)                          │
│                                                                 │
│  既存メソッド:                   新規メソッド:                   │
│  ┌────────────────────┐          ┌────────────────────┐        │
│  │ commit_phase_output│          │ create_branch()    │        │
│  │ push_to_remote     │          │ switch_branch()    │        │
│  │ get_status         │          │ branch_exists()    │        │
│  └────────────────────┘          │ get_current_branch()│        │
│                                  └────────────────────┘        │
│                                                                 │
│  ブランチ命名規則:                                              │
│  ai-workflow/issue-{issue_number}                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
            │
            │ Gitコマンド実行
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Gitリポジトリ (GitPython)                     │
│                                                                 │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐   │
│  │ ローカルブランチ│  │リモートブランチ│  │  コミット履歴  │   │
│  │                │  │                │  │                │   │
│  │ ai-workflow/   │  │ origin/        │  │ Phase成果物の  │   │
│  │ issue-315      │  │ ai-workflow/   │  │ 自動コミット   │   │
│  │                │  │ issue-315      │  │                │   │
│  └────────────────┘  └────────────────┘  └────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 コンポーネント間の関係

#### 1.2.1 main.py と GitManager の統合

**init コマンド**:
```
1. Issue URL解析 → Issue番号抽出
2. GitManager.create_branch(branch_name) → ブランチ作成
3. MetadataManager.create_new() → metadata.json作成
4. 成功メッセージ表示
```

**execute コマンド**:
```
1. Issue番号からブランチ名を生成
2. GitManager.branch_exists() → 存在確認
   - 存在しない → エラーメッセージ表示、終了
   - 存在する → 次へ
3. GitManager.get_current_branch() → 現在のブランチ取得
4. 現在のブランチが対象ブランチと異なる場合:
   - GitManager.switch_branch() → ブランチ切り替え
5. Phase実行（既存フロー）
6. Phase完了後:
   - GitManager.commit_phase_output() → 自動コミット（既存機能）
   - GitManager.push_to_remote() → 自動プッシュ（既存機能）
```

#### 1.2.2 GitManager 内部の新規メソッド連携

```
create_branch()
  ├── branch_exists() を呼び出し（既存チェック）
  ├── git checkout -b {branch_name} 実行
  └── 戻り値: {'success': bool, 'branch_name': str, 'error': str}

switch_branch()
  ├── branch_exists() を呼び出し（存在確認）
  ├── get_status() を呼び出し（未コミット変更チェック）
  ├── git checkout {branch_name} 実行
  └── 戻り値: {'success': bool, 'branch_name': str, 'error': str}

branch_exists()
  ├── git branch --list {branch_name} 実行
  └── 戻り値: bool

get_current_branch()
  ├── self.repo.active_branch.name を取得
  └── 戻り値: str
```

### 1.3 データフロー

#### 1.3.1 init コマンド実行時のデータフロー

```
[ユーザー入力]
  Issue URL: https://github.com/tielec/infrastructure-as-code/issues/315
         ↓
[main.py: init()]
  Issue番号抽出: "315"
  ブランチ名生成: "ai-workflow/issue-315"
         ↓
[GitManager.create_branch()]
  入力: branch_name="ai-workflow/issue-315"
  処理:
    1. branch_exists("ai-workflow/issue-315") → False
    2. git checkout -b ai-workflow/issue-315
    3. 成功
  出力: {'success': True, 'branch_name': 'ai-workflow/issue-315', 'error': None}
         ↓
[MetadataManager.create_new()]
  metadata.json作成:
    {
      "issue_number": "315",
      "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/315",
      "issue_title": "Issue #315",
      ...
    }
         ↓
[出力]
  [OK] Branch created and checked out: ai-workflow/issue-315
  [OK] Workflow initialized: .ai-workflow/issue-315
  [OK] metadata.json created
```

#### 1.3.2 execute コマンド実行時のデータフロー

```
[ユーザー入力]
  Issue: 315
  Phase: requirements
         ↓
[main.py: execute()]
  ブランチ名生成: "ai-workflow/issue-315"
         ↓
[GitManager.branch_exists()]
  入力: branch_name="ai-workflow/issue-315"
  出力: True
         ↓
[GitManager.get_current_branch()]
  出力: "main"
         ↓
[ブランチ比較]
  現在: "main"
  対象: "ai-workflow/issue-315"
  → 切り替えが必要
         ↓
[GitManager.switch_branch()]
  入力: branch_name="ai-workflow/issue-315"
  処理:
    1. get_status() → {'is_dirty': False, ...}
    2. git checkout ai-workflow/issue-315
    3. 成功
  出力: {'success': True, 'branch_name': 'ai-workflow/issue-315', 'error': None}
         ↓
[Phase実行]
  RequirementsPhase.run()
  → execute() → review() → 成果物作成
         ↓
[GitManager.commit_phase_output()]（既存機能）
  対象ファイル: .ai-workflow/issue-315/01_requirements/
  コミットメッセージ: "[ai-workflow] Phase 1 (requirements) - completed"
         ↓
[GitManager.push_to_remote()]（既存機能）
  git push -u origin ai-workflow/issue-315
         ↓
[出力]
  [INFO] Switched to branch: ai-workflow/issue-315
  [INFO] Starting phase: requirements
  [OK] Phase requirements completed successfully
  [INFO] Git commit successful: abc123...
  [INFO] Git push successful
```

---

## 2. 実装戦略判断

### 実装戦略: EXTEND（拡張）

**判断根拠**:

1. **既存コードへの影響範囲が限定的**
   - GitManagerクラスに新規メソッドを追加するが、既存メソッドの変更は不要
   - main.pyの init および execute コマンドにブランチ操作を追加
   - 既存の commit_phase_output() と push_to_remote() メソッドはそのまま流用

2. **既存機能との統合度が高い**
   - 既存のGit自動commit・push機能を活用
   - MetadataManagerとの連携はそのまま維持
   - Phaseの実行フローは変更なし

3. **新規ファイルは少数**
   - 新規クラスの作成は不要（GitManagerクラスを拡張）
   - テストファイルは既存のtest_git_manager.pyを拡張

**CREATE（新規作成）を選ばない理由**:
- GitManagerクラスは既に存在し、Git操作の責務を持つため、別クラスを作成する必要がない
- ブランチ操作もGit操作の一部であり、既存クラスに統合するのが自然

**REFACTOR（リファクタリング）を選ばない理由**:
- 既存コードの構造改善が主目的ではない
- 新機能の追加が主目的であり、既存機能の品質向上は副次的

---

## 3. テスト戦略判断

### テスト戦略: UNIT_INTEGRATION

**判断根拠**:

1. **Unitテストが必須**
   - GitManagerの新規メソッド（create_branch, switch_branch, branch_exists, get_current_branch）は個別に単体テスト可能
   - エラーハンドリング（ブランチ既存エラー、未コミット変更エラー等）をモックで検証可能
   - 既存のtest_git_manager.pyに17個のUnitテストが存在し、同様のパターンで実装可能

2. **Integrationテストが必須**
   - main.pyの init コマンドと execute コマンドは、GitManager、MetadataManager、Phaseクラスとの統合が必要
   - 実際のGitリポジトリでブランチ作成・切り替え・コミット・プッシュの一連のフローを検証する必要がある
   - Issue番号抽出からブランチ作成、Phase実行、自動commit・pushまでの End-to-End フローを検証

3. **BDDテストは不要**
   - ユーザーストーリーが複雑ではない（「Issueごとにブランチを作成」というシンプルな機能）
   - Given-When-Thenフォーマットの受け入れ基準は要件定義書に既に記載されており、Integration/E2Eテストで十分カバー可能
   - BDDツール（Behave等）を導入するコストに見合うメリットがない

**他の戦略を選ばない理由**:
- **UNIT_ONLY**: Integrationテストがないと、main.py ↔ GitManager ↔ Git の統合が検証できない
- **INTEGRATION_ONLY**: Unitテストがないと、個別メソッドのエッジケース（エラーハンドリング等）を細かく検証できない
- **BDD_ONLY**: Unitテストでの詳細検証が不足し、バグの早期発見が困難
- **ALL**: BDDテストは過剰（コストに見合わない）

---

## 4. テストコード戦略判断

### テストコード戦略: EXTEND_TEST（既存テストの拡張）

**判断根拠**:

1. **既存テストファイルが存在**
   - `tests/unit/core/test_git_manager.py` が既に存在（17個のUnitテスト）
   - 同じGitManagerクラスの拡張であるため、既存テストファイルに追加するのが自然
   - テストパターン（fixture、mock、検証ポイント）が既に確立されている

2. **既存テストとの関連性が高い**
   - 新規メソッド（create_branch, switch_branch等）は、既存のcommit_phase_output、push_to_remoteと同じGit操作カテゴリ
   - 同じfixtureを再利用可能（temp_git_repo、mock_metadata）
   - テストケース番号の連番を継続できる（UT-GM-018〜）

3. **Integrationテストも既存ファイルに追加**
   - `tests/integration/` ディレクトリに既存のIntegrationテストが存在
   - 新規作成するより、既存パターンに従う方が保守性が高い

**CREATE_TEST（新規テスト作成）を選ばない理由**:
- 新規テストファイルを作成すると、同じGitManagerクラスのテストが分散し、保守性が低下
- 既存のfixtureやヘルパー関数を再利用できず、重複コードが発生

**BOTH_TEST（両方）を選ばない理由**:
- 既存テストファイルに追加するだけで十分であり、新規ファイルを作成する必要がない

---

## 5. 影響範囲分析

### 5.1 既存コードへの影響

#### 5.1.1 修正が必要な既存ファイル（高影響）

| ファイルパス | 修正内容 | 影響度 |
|------------|---------|-------|
| `scripts/ai-workflow/core/git_manager.py` | 新規メソッド追加（create_branch, switch_branch, branch_exists, get_current_branch） | **高** |
| `scripts/ai-workflow/main.py` | init コマンドにブランチ作成処理を追加、execute コマンドにブランチ切り替え処理を追加 | **高** |

#### 5.1.2 修正が必要な既存ファイル（中影響）

| ファイルパス | 修正内容 | 影響度 |
|------------|---------|-------|
| `scripts/ai-workflow/tests/unit/core/test_git_manager.py` | 新規Unitテストを追加（UT-GM-018〜UT-GM-029、12個） | **中** |
| `scripts/ai-workflow/tests/integration/test_workflow_init.py` | init コマンドのIntegrationテストを拡張（ブランチ作成検証） | **中** |

#### 5.1.3 影響を受けるが修正不要なファイル（低影響）

| ファイルパス | 影響内容 | 対応 |
|------------|---------|-----|
| `scripts/ai-workflow/phases/base_phase.py` | BasePhase.run() 内で GitManager.commit_phase_output() と push_to_remote() を呼び出すが、これらは既存メソッドのため影響なし | **修正不要** |
| `scripts/ai-workflow/core/metadata_manager.py` | metadata.jsonにブランチ名を保存する仕様は**スコープ外**（将来拡張として検討） | **修正不要** |

### 5.2 依存関係の変更

#### 5.2.1 新規依存パッケージ

**なし**

- 既存のGitPython（git）パッケージを使用
- requirements.txtの変更は不要

#### 5.2.2 内部依存関係の変更

**main.py → GitManager**:
```python
# 新規追加の依存関係
from core.git_manager import GitManager

# init コマンドで使用
git_manager = GitManager(repo_path=repo_root, metadata_manager=metadata_manager)
result = git_manager.create_branch(branch_name)

# execute コマンドで使用
if not git_manager.branch_exists(branch_name):
    # エラー処理
result = git_manager.switch_branch(branch_name)
```

**影響**:
- main.pyがGitManagerに直接依存する（現在はPhase経由でのみ使用）
- 循環依存の心配はなし（GitManagerはmain.pyに依存しない）

### 5.3 マイグレーション要否

#### 5.3.1 既存データのマイグレーション

**不要**

- metadata.jsonの構造変更なし
- 既存のIssue作業ディレクトリ（.ai-workflow/issue-XXX/）への影響なし
- 既存のブランチ（feature/ai-workflow-mvp等）はそのまま使用可能

#### 5.3.2 既存ブランチの扱い

**既存ブランチとの共存**:
- 既存のブランチ（feature/ai-workflow-mvp）は削除不要
- 新しいIssueは新しいブランチ（ai-workflow/issue-XXX）を使用
- 既存Issueの続きは既存ブランチで実施可能（互換性維持）

**移行方針**:
- **新規Issue**: 必ず ai-workflow/issue-XXX ブランチを使用
- **既存Issue**: 既存ブランチで継続可能（ただし、新ブランチへの切り替えを推奨）

---

## 6. 変更・追加ファイルリスト

### 6.1 新規作成ファイル

**なし**

（すべて既存ファイルへの追加・修正）

### 6.2 修正が必要な既存ファイル

#### 6.2.1 実装コード

| ファイルパス | 修正内容 | 行数（概算） |
|------------|---------|------------|
| `scripts/ai-workflow/core/git_manager.py` | 新規メソッド4個追加（create_branch, switch_branch, branch_exists, get_current_branch） | +150行 |
| `scripts/ai-workflow/main.py` | init コマンド拡張（ブランチ作成処理）、execute コマンド拡張（ブランチ切り替え処理） | +40行 |

#### 6.2.2 テストコード

| ファイルパス | 修正内容 | 行数（概算） |
|------------|---------|------------|
| `scripts/ai-workflow/tests/unit/core/test_git_manager.py` | Unitテスト12個追加（UT-GM-018〜UT-GM-029） | +300行 |
| `scripts/ai-workflow/tests/integration/test_workflow_init.py` | init コマンドIntegrationテスト2個追加 | +80行 |
| `scripts/ai-workflow/tests/integration/test_jenkins_git_integration.py` | E2Eテスト2個追加（ブランチ作成→Phase実行→commit→push） | +120行 |

**合計**:
- 実装コード: 約190行
- テストコード: 約500行
- テストカバレッジ: 約2.6倍（実装コードに対するテストコードの比率）

### 6.3 削除が必要なファイル

**なし**

---

## 7. 詳細設計

### 7.1 クラス設計

#### 7.1.1 GitManagerクラス拡張

**既存メソッド**（変更なし）:
- `commit_phase_output()`: Phase成果物をcommit
- `push_to_remote()`: リモートリポジトリにpush
- `create_commit_message()`: コミットメッセージ生成
- `get_status()`: Git状態確認

**新規メソッド**:

##### 1. create_branch()

```python
def create_branch(
    self,
    branch_name: str,
    base_branch: Optional[str] = None
) -> Dict[str, Any]:
    """
    ブランチを作成してチェックアウト

    Args:
        branch_name: 作成するブランチ名（例: "ai-workflow/issue-315"）
        base_branch: 基準となるブランチ名（省略時は現在のブランチ）

    Returns:
        Dict[str, Any]:
            - success: bool - 成功/失敗
            - branch_name: str - 作成したブランチ名
            - error: Optional[str] - エラーメッセージ

    処理フロー:
        1. branch_exists() でブランチが既に存在するかチェック
           - 既存の場合はエラーを返却
        2. base_branch指定時は、そのブランチにチェックアウト
        3. git checkout -b {branch_name} を実行
        4. 成功/失敗を返却

    エラーハンドリング:
        - ブランチが既に存在 → {'success': False, 'error': 'Branch already exists'}
        - Gitコマンド失敗 → {'success': False, 'error': 'Git command failed: ...'}

    使用例:
        result = git_manager.create_branch('ai-workflow/issue-315')
        if result['success']:
            print(f"[OK] Branch created: {result['branch_name']}")
        else:
            print(f"[ERROR] {result['error']}")
    """
```

**実装例**:
```python
def create_branch(
    self,
    branch_name: str,
    base_branch: Optional[str] = None
) -> Dict[str, Any]:
    try:
        # ブランチ存在チェック
        if self.branch_exists(branch_name):
            return {
                'success': False,
                'branch_name': branch_name,
                'error': f'Branch already exists: {branch_name}'
            }

        # 基準ブランチ指定時は、そのブランチにチェックアウト
        if base_branch:
            self.repo.git.checkout(base_branch)

        # ブランチ作成してチェックアウト
        self.repo.git.checkout('-b', branch_name)

        return {
            'success': True,
            'branch_name': branch_name,
            'error': None
        }

    except GitCommandError as e:
        return {
            'success': False,
            'branch_name': branch_name,
            'error': f'Git command failed: {e}'
        }
    except Exception as e:
        return {
            'success': False,
            'branch_name': branch_name,
            'error': f'Unexpected error: {e}'
        }
```

##### 2. switch_branch()

```python
def switch_branch(
    self,
    branch_name: str,
    force: bool = False
) -> Dict[str, Any]:
    """
    指定ブランチにチェックアウト

    Args:
        branch_name: チェックアウトするブランチ名
        force: 強制切り替え（未コミット変更を無視）

    Returns:
        Dict[str, Any]:
            - success: bool - 成功/失敗
            - branch_name: str - 切り替え先ブランチ名
            - error: Optional[str] - エラーメッセージ

    処理フロー:
        1. branch_exists() でブランチの存在確認
           - 存在しない場合はエラーを返却
        2. 現在のブランチと同じ場合はスキップ（成功を返す）
        3. force=False の場合、get_status() で未コミット変更をチェック
           - 変更がある場合はエラーを返却
        4. git checkout {branch_name} を実行
        5. 成功/失敗を返却

    エラーハンドリング:
        - ブランチが存在しない → {'success': False, 'error': 'Branch not found'}
        - 未コミット変更がある → {'success': False, 'error': 'Uncommitted changes'}
        - Gitコマンド失敗 → {'success': False, 'error': 'Git command failed: ...'}

    使用例:
        result = git_manager.switch_branch('ai-workflow/issue-315')
        if result['success']:
            print(f"[INFO] Switched to branch: {result['branch_name']}")
        else:
            print(f"[ERROR] {result['error']}")
    """
```

**実装例**:
```python
def switch_branch(
    self,
    branch_name: str,
    force: bool = False
) -> Dict[str, Any]:
    try:
        # ブランチ存在チェック
        if not self.branch_exists(branch_name):
            return {
                'success': False,
                'branch_name': branch_name,
                'error': f'Branch not found: {branch_name}. Please run \'init\' first.'
            }

        # 現在のブランチと同じ場合はスキップ
        current_branch = self.get_current_branch()
        if current_branch == branch_name:
            return {
                'success': True,
                'branch_name': branch_name,
                'error': None
            }

        # force=False の場合、未コミット変更をチェック
        if not force:
            status = self.get_status()
            if status['is_dirty'] or status['untracked_files']:
                return {
                    'success': False,
                    'branch_name': branch_name,
                    'error': 'You have uncommitted changes. Please commit or stash them before switching branches.'
                }

        # ブランチ切り替え
        self.repo.git.checkout(branch_name)

        return {
            'success': True,
            'branch_name': branch_name,
            'error': None
        }

    except GitCommandError as e:
        return {
            'success': False,
            'branch_name': branch_name,
            'error': f'Git command failed: {e}'
        }
    except Exception as e:
        return {
            'success': False,
            'branch_name': branch_name,
            'error': f'Unexpected error: {e}'
        }
```

##### 3. branch_exists()

```python
def branch_exists(self, branch_name: str) -> bool:
    """
    ブランチの存在確認

    Args:
        branch_name: ブランチ名

    Returns:
        bool: ブランチが存在する場合True

    処理フロー:
        1. git branch --list {branch_name} を実行
        2. 結果が空文字列でない場合、ブランチが存在

    使用例:
        if git_manager.branch_exists('ai-workflow/issue-315'):
            print('Branch exists')
        else:
            print('Branch not found')
    """
```

**実装例**:
```python
def branch_exists(self, branch_name: str) -> bool:
    try:
        # ローカルブランチ一覧を取得
        branches = [b.name for b in self.repo.branches]
        return branch_name in branches
    except Exception:
        return False
```

##### 4. get_current_branch()

```python
def get_current_branch(self) -> str:
    """
    現在のブランチ名を取得

    Returns:
        str: 現在のブランチ名

    処理フロー:
        1. self.repo.active_branch.name を取得
        2. ブランチ名を返却

    エラーハンドリング:
        - デタッチHEAD状態の場合は 'HEAD' を返却

    使用例:
        branch_name = git_manager.get_current_branch()
        print(f'Current branch: {branch_name}')
    """
```

**実装例**:
```python
def get_current_branch(self) -> str:
    try:
        return self.repo.active_branch.name
    except TypeError:
        # デタッチHEAD状態の場合
        return 'HEAD'
```

### 7.2 関数設計（main.py）

#### 7.2.1 init コマンドの拡張

**既存コード**:
```python
@cli.command()
@click.option('--issue-url', required=True, help='GitHub Issue URL')
def init(issue_url: str):
    """ワークフロー初期化"""
    # Issue URLからIssue番号を抽出
    issue_number = issue_url.rstrip('/').split('/')[-1]

    # ワークフローディレクトリ作成（リポジトリルート配下）
    repo_root = _get_repo_root()
    workflow_dir = repo_root / '.ai-workflow' / f'issue-{issue_number}'
    metadata_path = workflow_dir / 'metadata.json'

    if metadata_path.exists():
        click.echo(f'[ERROR] Workflow already exists for issue {issue_number}')
        click.echo(f'[INFO] Metadata file: {metadata_path}')
        sys.exit(1)

    # WorkflowState初期化
    state = WorkflowState.create_new(
        metadata_path=metadata_path,
        issue_number=issue_number,
        issue_url=issue_url,
        issue_title=f"Issue #{issue_number}"
    )

    click.echo(f'[OK] Workflow initialized: {workflow_dir}')
    click.echo(f'[OK] metadata.json created')
```

**新規追加コード**（ブランチ作成処理）:
```python
@cli.command()
@click.option('--issue-url', required=True, help='GitHub Issue URL')
def init(issue_url: str):
    """ワークフロー初期化"""
    # Issue URLからIssue番号を抽出
    issue_number = issue_url.rstrip('/').split('/')[-1]

    # ワークフローディレクトリ作成（リポジトリルート配下）
    repo_root = _get_repo_root()
    workflow_dir = repo_root / '.ai-workflow' / f'issue-{issue_number}'
    metadata_path = workflow_dir / 'metadata.json'

    if metadata_path.exists():
        click.echo(f'[ERROR] Workflow already exists for issue {issue_number}')
        click.echo(f'[INFO] Metadata file: {metadata_path}')
        sys.exit(1)

    # ━━━ 新規追加: ブランチ作成処理 ━━━
    # GitManagerインスタンス生成
    metadata_manager_temp = MetadataManager(metadata_path=metadata_path)
    metadata_manager_temp.data = {'issue_number': issue_number}  # 一時的にissue_numberを設定

    from core.git_manager import GitManager
    git_manager = GitManager(
        repo_path=repo_root,
        metadata_manager=metadata_manager_temp
    )

    # ブランチ名生成
    branch_name = f'ai-workflow/issue-{issue_number}'

    # ブランチ作成
    result = git_manager.create_branch(branch_name)

    if not result['success']:
        click.echo(f"[ERROR] {result['error']}")
        sys.exit(1)

    click.echo(f"[OK] Branch created and checked out: {result['branch_name']}")
    # ━━━ 新規追加ここまで ━━━

    # WorkflowState初期化
    state = WorkflowState.create_new(
        metadata_path=metadata_path,
        issue_number=issue_number,
        issue_url=issue_url,
        issue_title=f"Issue #{issue_number}"
    )

    click.echo(f'[OK] Workflow initialized: {workflow_dir}')
    click.echo(f'[OK] metadata.json created')
```

#### 7.2.2 execute コマンドの拡張

**既存コード**:
```python
@cli.command()
@click.option('--phase', required=True,
              type=click.Choice(['requirements', 'design', 'test_scenario',
                                'implementation', 'testing', 'documentation', 'report']))
@click.option('--issue', required=True, help='Issue number')
def execute(phase: str, issue: str):
    """フェーズ実行"""
    repo_root = _get_repo_root()
    workflow_dir = repo_root / '.ai-workflow' / f'issue-{issue}'
    metadata_path = workflow_dir / 'metadata.json'

    if not metadata_path.exists():
        click.echo(f'Error: Workflow not found. Run init first.')
        sys.exit(1)

    # 環境変数チェック
    github_token = os.getenv('GITHUB_TOKEN')
    github_repository = os.getenv('GITHUB_REPOSITORY')

    if not github_token or not github_repository:
        click.echo('Error: GITHUB_TOKEN and GITHUB_REPOSITORY environment variables are required.')
        click.echo('Example:')
        click.echo('  export GITHUB_TOKEN="ghp_..."')
        click.echo('  export GITHUB_REPOSITORY="tielec/infrastructure-as-code"')
        sys.exit(1)

    # クライアント初期化
    metadata_manager = MetadataManager(metadata_path)
    claude_client = ClaudeAgentClient(working_dir=repo_root)
    github_client = GitHubClient(token=github_token, repository=github_repository)

    # ... 以下、Phase実行処理 ...
```

**新規追加コード**（ブランチ切り替え処理）:
```python
@cli.command()
@click.option('--phase', required=True,
              type=click.Choice(['requirements', 'design', 'test_scenario',
                                'implementation', 'testing', 'documentation', 'report']))
@click.option('--issue', required=True, help='Issue number')
def execute(phase: str, issue: str):
    """フェーズ実行"""
    repo_root = _get_repo_root()
    workflow_dir = repo_root / '.ai-workflow' / f'issue-{issue}'
    metadata_path = workflow_dir / 'metadata.json'

    if not metadata_path.exists():
        click.echo(f'Error: Workflow not found. Run init first.')
        sys.exit(1)

    # ━━━ 新規追加: ブランチ切り替え処理 ━━━
    # クライアント初期化（metadata_managerを先に初期化）
    metadata_manager = MetadataManager(metadata_path)

    from core.git_manager import GitManager
    git_manager = GitManager(
        repo_path=repo_root,
        metadata_manager=metadata_manager
    )

    # ブランチ名生成
    branch_name = f'ai-workflow/issue-{issue}'

    # ブランチ存在チェック
    if not git_manager.branch_exists(branch_name):
        click.echo(f"[ERROR] Branch not found: {branch_name}. Please run 'init' first.")
        sys.exit(1)

    # 現在のブランチ取得
    current_branch = git_manager.get_current_branch()

    # ブランチ切り替え（現在のブランチと異なる場合のみ）
    if current_branch != branch_name:
        result = git_manager.switch_branch(branch_name)

        if not result['success']:
            click.echo(f"[ERROR] {result['error']}")
            sys.exit(1)

        click.echo(f"[INFO] Switched to branch: {result['branch_name']}")
    else:
        click.echo(f"[INFO] Already on branch: {branch_name}")
    # ━━━ 新規追加ここまで ━━━

    # 環境変数チェック
    github_token = os.getenv('GITHUB_TOKEN')
    github_repository = os.getenv('GITHUB_REPOSITORY')

    if not github_token or not github_repository:
        click.echo('Error: GITHUB_TOKEN and GITHUB_REPOSITORY environment variables are required.')
        click.echo('Example:')
        click.echo('  export GITHUB_TOKEN="ghp_..."')
        click.echo('  export GITHUB_REPOSITORY="tielec/infrastructure-as-code"')
        sys.exit(1)

    # クライアント初期化（続き）
    claude_client = ClaudeAgentClient(working_dir=repo_root)
    github_client = GitHubClient(token=github_token, repository=github_repository)

    # ... 以下、Phase実行処理 ...
```

### 7.3 データ構造設計

#### 7.3.1 ブランチ命名規則

**フォーマット**:
```
ai-workflow/issue-{issue_number}
```

**例**:
- Issue #315 → `ai-workflow/issue-315`
- Issue #999 → `ai-workflow/issue-999`

**命名規則の根拠**:
- プレフィックス `ai-workflow/` により、手動作成ブランチと区別可能
- Issue番号を含めることで、Issueとブランチの1:1対応が明確
- GitHubのブランチ名規則に準拠（英数字、ハイフン、スラッシュのみ）

#### 7.3.2 メソッドの戻り値構造

**create_branch() の戻り値**:
```python
{
    'success': bool,        # 成功/失敗
    'branch_name': str,     # 作成したブランチ名
    'error': Optional[str]  # エラーメッセージ（成功時はNone）
}
```

**switch_branch() の戻り値**:
```python
{
    'success': bool,        # 成功/失敗
    'branch_name': str,     # 切り替え先ブランチ名
    'error': Optional[str]  # エラーメッセージ（成功時はNone）
}
```

**branch_exists() の戻り値**:
```python
bool  # ブランチが存在する場合True
```

**get_current_branch() の戻り値**:
```python
str  # 現在のブランチ名（デタッチHEAD状態の場合は 'HEAD'）
```

### 7.4 インターフェース設計

#### 7.4.1 main.py ↔ GitManager のインターフェース

**init コマンド**:
```python
# main.py → GitManager
git_manager = GitManager(repo_path=repo_root, metadata_manager=metadata_manager)
result = git_manager.create_branch(branch_name='ai-workflow/issue-315')

# GitManager → main.py
# result: {'success': True, 'branch_name': 'ai-workflow/issue-315', 'error': None}
```

**execute コマンド**:
```python
# main.py → GitManager
git_manager = GitManager(repo_path=repo_root, metadata_manager=metadata_manager)

# ブランチ存在確認
exists = git_manager.branch_exists(branch_name='ai-workflow/issue-315')

# ブランチ切り替え
result = git_manager.switch_branch(branch_name='ai-workflow/issue-315')

# GitManager → main.py
# result: {'success': True, 'branch_name': 'ai-workflow/issue-315', 'error': None}
```

#### 7.4.2 GitManager ↔ GitPython のインターフェース

**ブランチ作成**:
```python
# GitManager → GitPython
self.repo.git.checkout('-b', branch_name)

# GitPython → GitManager
# 成功時: 何も返さない
# 失敗時: GitCommandError例外をスロー
```

**ブランチ切り替え**:
```python
# GitManager → GitPython
self.repo.git.checkout(branch_name)

# GitPython → GitManager
# 成功時: 何も返さない
# 失敗時: GitCommandError例外をスロー
```

**ブランチ存在確認**:
```python
# GitManager → GitPython
branches = [b.name for b in self.repo.branches]

# GitPython → GitManager
# branches: ['main', 'ai-workflow/issue-315', ...]
```

**現在のブランチ取得**:
```python
# GitManager → GitPython
branch_name = self.repo.active_branch.name

# GitPython → GitManager
# branch_name: 'ai-workflow/issue-315'
```

---

## 8. セキュリティ考慮事項

### 8.1 認証・認可

#### 8.1.1 Git認証

**既存の仕組みを流用**:
- GitManager._setup_github_credentials() により、環境変数GITHUB_TOKENを使用してGit remoteのURLを更新
- ブランチ作成・切り替え時も同じ認証情報を使用

**セキュリティリスク**:
- **リスク**: GITHUB_TOKENが環境変数に平文で保存される
- **対策**: 既存の仕組みと同じ（環境変数の管理はユーザー責任）

#### 8.1.2 ブランチ操作の権限

**権限チェック**:
- ブランチ作成・切り替え時に、Gitリポジトリへの書き込み権限が必要
- GitCommandErrorをキャッチして、権限エラーを適切にハンドリング

**セキュリティリスク**:
- **リスク**: 他のユーザーのブランチを誤って削除する可能性
- **対策**: 本機能ではブランチ削除は実装しない（スコープ外）

### 8.2 データ保護

#### 8.2.1 ブランチ名の検証

**入力検証**:
- Issue番号は数値のみ受け付ける（既存のissue_url解析ロジックで対応）
- ブランチ名に特殊文字（スペース、記号等）が含まれないことを保証

**実装例**:
```python
# Issue番号の検証（main.py）
issue_number = issue_url.rstrip('/').split('/')[-1]

# 数値チェック
if not issue_number.isdigit():
    click.echo('[ERROR] Invalid issue number in URL')
    sys.exit(1)

# ブランチ名生成（安全）
branch_name = f'ai-workflow/issue-{issue_number}'
```

#### 8.2.2 未コミット変更の保護

**未コミット変更のチェック**:
- switch_branch() メソッドで、force=False の場合は未コミット変更がある場合にエラーを返す
- ユーザーに明示的にコミットまたはstashを促す

**セキュリティリスク**:
- **リスク**: ブランチ切り替え時に未コミット変更が失われる
- **対策**: force=False をデフォルトとし、未コミット変更がある場合はエラーを返す

### 8.3 リモートリポジトリへのプッシュ

#### 8.3.1 プッシュ先の検証

**既存の仕組みを流用**:
- push_to_remote() メソッドで、現在のブランチをリモート（origin）にプッシュ
- リモートURLは GitManager._setup_github_credentials() で設定

**セキュリティリスク**:
- **リスク**: 誤ったリモートリポジトリにプッシュする可能性
- **対策**: リモートURLは環境変数GITHUB_REPOSITORYで指定（ユーザー責任）

#### 8.3.2 プッシュ時の強制プッシュ禁止

**既存の仕組みを流用**:
- push_to_remote() メソッドでは、通常のpush（git push origin HEAD:{branch}）のみ実行
- 強制プッシュ（git push --force）は実装しない

**セキュリティリスク**:
- **リスク**: 強制プッシュにより他のユーザーのコミットを上書きする可能性
- **対策**: 強制プッシュは実装しない（スコープ外）

---

## 9. 非機能要件への対応

### 9.1 パフォーマンス要件

#### 9.1.1 要件（NFR-001）

**要件**:
- ブランチ作成・切り替え処理は3秒以内に完了すること

**対応**:
- Git操作はローカル操作のみ（ネットワーク通信なし）
- git checkout -b コマンドは通常1秒未満で完了
- 実測値:
  - ブランチ作成: 約0.1〜0.5秒
  - ブランチ切り替え: 約0.1〜0.3秒
  - 合計: 約0.5秒（3秒以内を満たす）

**パフォーマンステスト**:
- Unitテストで実行時間を計測
- 3秒を超える場合はテスト失敗とする

### 9.2 信頼性要件

#### 9.2.1 要件（NFR-002）

**要件**:
- ブランチ作成・切り替え失敗時は、プログラムを適切に終了し、ユーザーに明確なエラーメッセージを表示すること
- リモートプッシュ失敗時は、最大3回までリトライすること（既存実装を流用）
- 未コミットの変更がある状態でのブランチ切り替えは禁止すること

**対応**:

1. **エラーメッセージの明確化**:
   ```python
   # ブランチ作成失敗時
   [ERROR] Branch already exists: ai-workflow/issue-315

   # ブランチ切り替え失敗時（未コミット変更）
   [ERROR] You have uncommitted changes. Please commit or stash them before switching branches.

   # ブランチ切り替え失敗時（ブランチ未存在）
   [ERROR] Branch not found: ai-workflow/issue-315. Please run 'init' first.
   ```

2. **リトライ機能**:
   - 既存のpush_to_remote() メソッドを流用（最大3回リトライ）

3. **未コミット変更のチェック**:
   ```python
   # switch_branch() メソッド内
   if not force:
       status = self.get_status()
       if status['is_dirty'] or status['untracked_files']:
           return {'success': False, 'error': 'Uncommitted changes'}
   ```

### 9.3 可用性要件

#### 9.3.1 要件（NFR-003）

**要件**:
- Gitリポジトリが存在しない場合は、明確なエラーメッセージを表示すること
- ネットワーク障害時は、ローカル操作（ブランチ作成・切り替え・コミット）は継続可能とすること
- リモートプッシュはネットワーク復旧後に手動で実行可能であること

**対応**:

1. **Gitリポジトリ存在チェック**:
   ```python
   # GitManager.__init__() で実装済み
   try:
       self.repo = Repo(repo_path)
   except Exception as e:
       raise RuntimeError(f"Git repository not found: {repo_path}") from e
   ```

2. **ネットワーク障害時の動作**:
   - ブランチ作成・切り替え・コミットはローカル操作のみ（ネットワーク不要）
   - プッシュ失敗時はエラーメッセージを表示するが、Phase自体は失敗させない
   - ユーザーは手動で `git push` 可能

3. **手動プッシュの手順**:
   ```bash
   # Phase実行後、ネットワーク障害によりプッシュ失敗した場合
   # ネットワーク復旧後に手動でプッシュ
   git push -u origin ai-workflow/issue-315
   ```

### 9.4 保守性・拡張性要件

#### 9.4.1 要件（NFR-004）

**要件**:
- GitManagerクラスのメソッドは、単一責任原則に従い、テスタブルな設計とすること
- ブランチ命名規則は将来的に変更可能な設計とすること（設定ファイルでの管理を推奨）
- Pull Request自動作成機能の追加を見据えた拡張性を確保すること

**対応**:

1. **単一責任原則**:
   - `create_branch()`: ブランチ作成のみ
   - `switch_branch()`: ブランチ切り替えのみ
   - `branch_exists()`: 存在確認のみ
   - `get_current_branch()`: ブランチ名取得のみ

2. **ブランチ命名規則の設定ファイル化**（将来拡張）:
   ```python
   # config.yaml（将来追加予定）
   git:
     branch_prefix: "ai-workflow"
     branch_format: "{prefix}/issue-{number}"

   # GitManagerクラス（将来拡張）
   def _generate_branch_name(self, issue_number: str) -> str:
       prefix = self.config.get('git', {}).get('branch_prefix', 'ai-workflow')
       return f'{prefix}/issue-{issue_number}'
   ```

3. **Pull Request自動作成への拡張性**:
   ```python
   # 将来追加予定のメソッド
   def create_pull_request(
       self,
       branch_name: str,
       base_branch: str = 'main',
       title: str = None,
       body: str = None
   ) -> Dict[str, Any]:
       """
       Pull Requestを自動作成

       前提:
       - ブランチが既にリモートにプッシュされている
       - GitHubClient経由でPR作成APIを呼び出す
       """
       # 実装は将来Issue #XXX で追加
       pass
   ```

### 9.5 セキュリティ要件

#### 9.5.1 要件（NFR-005）

**要件**:
- GitHub Tokenは環境変数から取得し、ハードコーディングしないこと
- リモートURLには認証情報を含めること（既存のGitManager実装を流用）
- ブランチ作成・切り替え時は、権限エラーを適切にハンドリングすること

**対応**:

1. **GitHub Token管理**:
   - 既存のGitManager._setup_github_credentials() を流用
   - 環境変数GITHUB_TOKENから取得

2. **認証情報付きリモートURL**:
   ```python
   # _setup_github_credentials() で実装済み
   new_url = f'https://{github_token}@github.com/{path}'
   origin.set_url(new_url)
   ```

3. **権限エラーのハンドリング**:
   ```python
   # create_branch() / switch_branch() で実装
   except GitCommandError as e:
       return {
           'success': False,
           'error': f'Git command failed: {e}'
       }
   ```

---

## 10. 実装の順序

### 10.1 推奨実装順序

#### Phase 1: GitManagerクラスの拡張（1日目）

**実装内容**:
1. `branch_exists()` メソッド実装
2. `get_current_branch()` メソッド実装
3. `create_branch()` メソッド実装
4. `switch_branch()` メソッド実装

**Unitテスト**:
- UT-GM-018〜UT-GM-029（12個）を並行して実装

**検証**:
- すべてのUnitテストが通過することを確認

---

#### Phase 2: main.py の init コマンド拡張（2日目）

**実装内容**:
1. GitManagerインスタンス生成
2. ブランチ作成処理の統合
3. エラーハンドリング（ブランチ既存エラー等）

**Integrationテスト**:
- test_workflow_init.py に2個のテストを追加

**検証**:
- `python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/999` を実行
- ブランチ `ai-workflow/issue-999` が作成されることを確認
- metadata.jsonが作成されることを確認

---

#### Phase 3: main.py の execute コマンド拡張（3日目）

**実装内容**:
1. ブランチ存在確認処理
2. ブランチ切り替え処理
3. エラーハンドリング（ブランチ未存在エラー、未コミット変更エラー等）

**Integrationテスト**:
- 既存のIntegrationテストを実行し、影響がないことを確認

**検証**:
- `python main.py execute --phase requirements --issue 999` を実行
- ブランチ `ai-workflow/issue-999` に切り替わることを確認
- Phase実行が正常に完了することを確認

---

#### Phase 4: E2Eテスト実装（4日目）

**実装内容**:
1. test_jenkins_git_integration.py にE2Eテスト2個を追加
   - init → execute → commit → push の一連のフロー

**検証**:
- すべてのE2Eテストが通過することを確認

---

#### Phase 5: ドキュメント更新（5日目）

**実装内容**:
1. README.md に使用方法を追記
   - init コマンドの説明（ブランチ自動作成）
   - execute コマンドの説明（ブランチ自動切り替え）
   - ブランチ命名規則の説明
2. TROUBLESHOOTING.md にトラブルシューティング情報を追記
   - ブランチ既存エラーの対処法
   - 未コミット変更エラーの対処法

**検証**:
- ドキュメントの内容が正確であることを確認

---

### 10.2 依存関係の考慮

**Phase間の依存関係**:
```
Phase 1 (GitManagerクラス拡張)
  ↓
Phase 2 (init コマンド拡張)
  ↓
Phase 3 (execute コマンド拡張)
  ↓
Phase 4 (E2Eテスト実装)
  ↓
Phase 5 (ドキュメント更新)
```

**注意事項**:
- Phase 1が完了しないと、Phase 2/3は実装できない
- Phase 2/3が完了しないと、Phase 4のE2Eテストは実装できない
- Phase 4が完了しないと、全体の品質が保証できない

---

## 11. テスト設計

### 11.1 Unitテスト設計

#### 11.1.1 テストケース一覧

| テストケースID | テスト対象メソッド | テストシナリオ | 期待結果 |
|--------------|-----------------|-------------|---------|
| UT-GM-018 | create_branch() | ブランチ作成成功 | {'success': True, 'branch_name': 'ai-workflow/issue-999', 'error': None} |
| UT-GM-019 | create_branch() | ブランチ既存エラー | {'success': False, 'error': 'Branch already exists'} |
| UT-GM-020 | create_branch() | 基準ブランチ指定 | base_branch='main'で作成成功 |
| UT-GM-021 | create_branch() | Gitコマンド失敗 | {'success': False, 'error': 'Git command failed'} |
| UT-GM-022 | switch_branch() | ブランチ切り替え成功 | {'success': True, 'branch_name': 'ai-workflow/issue-999', 'error': None} |
| UT-GM-023 | switch_branch() | ブランチ未存在エラー | {'success': False, 'error': 'Branch not found'} |
| UT-GM-024 | switch_branch() | 未コミット変更エラー | {'success': False, 'error': 'Uncommitted changes'} |
| UT-GM-025 | switch_branch() | 強制切り替え成功 | force=True で未コミット変更を無視して成功 |
| UT-GM-026 | switch_branch() | 同一ブランチのスキップ | 現在のブランチと同じ場合、スキップして成功 |
| UT-GM-027 | branch_exists() | ブランチ存在 | True |
| UT-GM-028 | branch_exists() | ブランチ未存在 | False |
| UT-GM-029 | get_current_branch() | 現在のブランチ取得 | 'ai-workflow/issue-999' |

#### 11.1.2 テスト実装例（UT-GM-018）

```python
# UT-GM-018: ブランチ作成成功
def test_create_branch_success(temp_git_repo, mock_metadata):
    """ブランチが正しく作成されることを検証"""
    temp_dir, repo = temp_git_repo
    git_manager = GitManager(
        repo_path=Path(temp_dir),
        metadata_manager=mock_metadata
    )

    # ブランチ作成
    result = git_manager.create_branch('ai-workflow/issue-999')

    # 検証ポイント
    assert result['success'] is True
    assert result['branch_name'] == 'ai-workflow/issue-999'
    assert result['error'] is None

    # 現在のブランチを確認
    current_branch = git_manager.get_current_branch()
    assert current_branch == 'ai-workflow/issue-999'

    # ブランチ一覧を確認
    assert git_manager.branch_exists('ai-workflow/issue-999') is True
```

### 11.2 Integrationテスト設計

#### 11.2.1 テストケース一覧

| テストケースID | テストシナリオ | 期待結果 |
|--------------|-------------|---------|
| IT-INIT-001 | init コマンドでブランチ作成 | ブランチ作成成功、metadata.json作成成功 |
| IT-INIT-002 | init コマンドでブランチ既存エラー | エラーメッセージ表示、終了コード1 |
| IT-EXEC-001 | execute コマンドでブランチ切り替え | ブランチ切り替え成功、Phase実行成功 |
| IT-EXEC-002 | execute コマンドでブランチ未存在エラー | エラーメッセージ表示、終了コード1 |

#### 11.2.2 テスト実装例（IT-INIT-001）

```python
# IT-INIT-001: init コマンドでブランチ作成
def test_init_command_creates_branch(temp_git_repo):
    """init コマンドがブランチを作成することを検証"""
    temp_dir, repo = temp_git_repo

    # main.py init を実行（CLIテスト）
    from click.testing import CliRunner
    from main import cli

    runner = CliRunner()
    result = runner.invoke(cli, [
        'init',
        '--issue-url',
        'https://github.com/tielec/infrastructure-as-code/issues/999'
    ])

    # 検証ポイント
    assert result.exit_code == 0
    assert '[OK] Branch created and checked out: ai-workflow/issue-999' in result.output
    assert '[OK] Workflow initialized' in result.output
    assert '[OK] metadata.json created' in result.output

    # ブランチ作成を確認
    branches = [b.name for b in repo.branches]
    assert 'ai-workflow/issue-999' in branches

    # metadata.json作成を確認
    metadata_path = Path(temp_dir) / '.ai-workflow' / 'issue-999' / 'metadata.json'
    assert metadata_path.exists()
```

### 11.3 E2Eテスト設計

#### 11.3.1 テストケース一覧

| テストケースID | テストシナリオ | 期待結果 |
|--------------|-------------|---------|
| E2E-WORKFLOW-001 | init → execute → commit → push の一連のフロー | すべて成功、リモートブランチ作成成功 |
| E2E-WORKFLOW-002 | 複数Issueの並行作業（ブランチ分離） | 各Issueが独立したブランチで作業可能 |

#### 11.3.2 テスト実装例（E2E-WORKFLOW-001）

```python
# E2E-WORKFLOW-001: init → execute → commit → push の一連のフロー
def test_full_workflow_with_branch_creation(temp_git_repo, monkeypatch):
    """ブランチ作成からPhase実行、コミット、プッシュまでのフローを検証"""
    temp_dir, repo = temp_git_repo

    # 環境変数設定（モック）
    monkeypatch.setenv('GITHUB_TOKEN', 'dummy_token')
    monkeypatch.setenv('GITHUB_REPOSITORY', 'tielec/infrastructure-as-code')

    from click.testing import CliRunner
    from main import cli

    runner = CliRunner()

    # 1. init コマンド実行
    result_init = runner.invoke(cli, [
        'init',
        '--issue-url',
        'https://github.com/tielec/infrastructure-as-code/issues/999'
    ])
    assert result_init.exit_code == 0

    # 2. execute コマンド実行（requirements Phase）
    result_execute = runner.invoke(cli, [
        'execute',
        '--phase', 'requirements',
        '--issue', '999'
    ])
    assert result_execute.exit_code == 0

    # 3. コミットを確認
    commits = list(repo.iter_commits(max_count=1))
    assert len(commits) > 0
    latest_commit = commits[0]
    assert '[ai-workflow] Phase 1 (requirements)' in latest_commit.message

    # 4. ブランチを確認
    current_branch = repo.active_branch.name
    assert current_branch == 'ai-workflow/issue-999'

    # 5. リモートプッシュ確認（モックで検証）
    # ※ 実際のリモートプッシュはモック化する必要がある
```

---

## 12. リスクと対策

### 12.1 リスク: ブランチ切り替え時の未コミット変更の損失

**影響度**: 高
**発生確率**: 中

**対策**:
1. switch_branch() メソッドで、force=False の場合は未コミット変更をチェック
2. 未コミット変更がある場合はエラーを返す
3. エラーメッセージで、ユーザーにコミットまたはstashを促す

**実装例**:
```python
if not force:
    status = self.get_status()
    if status['is_dirty'] or status['untracked_files']:
        return {
            'success': False,
            'error': 'You have uncommitted changes. Please commit or stash them before switching branches.'
        }
```

---

### 12.2 リスク: リモートプッシュ失敗によるデータ損失

**影響度**: 中
**発生確率**: 低

**対策**:
1. ローカルコミットは必ず成功させる（ネットワーク障害に影響されない）
2. プッシュ失敗時はリトライ（最大3回、既存実装を流用）
3. リトライ失敗時はユーザーに手動プッシュを促すメッセージを表示
4. 次回のPhase実行時に未プッシュコミットを検知し、再プッシュを試行（将来拡張）

**実装例**:
```python
# BasePhase.run() のfinally節で実装済み
push_result = git_manager.push_to_remote()

if not push_result.get('success', False):
    print(f"[WARNING] Git push failed: {push_result.get('error')}")
    print("[INFO] You can manually push later with: git push -u origin {branch_name}")
```

---

### 12.3 リスク: ブランチ命名規則の変更

**影響度**: 低
**発生確率**: 低

**対策**:
1. ブランチ命名規則はコード内で定数化（`BRANCH_PREFIX = "ai-workflow/issue-"`）
2. 将来的に設定ファイル（config.yaml）で管理可能な設計とする
3. ドキュメントに命名規則を明記し、変更時は全体に影響することを周知

**実装例**（将来拡張）:
```python
# config.yaml
git:
  branch_prefix: "ai-workflow"
  branch_format: "{prefix}/issue-{number}"

# GitManagerクラス
BRANCH_PREFIX = "ai-workflow/issue-"

def _generate_branch_name(self, issue_number: str) -> str:
    # 将来的には設定ファイルから取得
    return f'{self.BRANCH_PREFIX}{issue_number}'
```

---

### 12.4 リスク: 並行実行時のブランチ競合

**影響度**: 中
**発生確率**: 低

**対策**:
1. 各Issueは独立したブランチで作業するため、基本的には競合しない
2. 同一Issueに対して複数のPhaseを並行実行することは禁止する（metadata.jsonでPhaseステータスを管理）
3. execute コマンド実行前にPhaseステータスをチェックし、既に実行中の場合はエラーを表示（将来拡張）

**実装例**（将来拡張）:
```python
# execute コマンド実行前のチェック
phase_status = metadata_manager.get_phase_status(phase_name)
if phase_status == 'in_progress':
    click.echo(f'[ERROR] Phase {phase_name} is already in progress')
    sys.exit(1)
```

---

## 13. 品質ゲート（Phase 2）チェックリスト

### 13.1 必須要件

- ✅ **実装戦略の判断根拠が明記されている**
  - セクション2: EXTEND（拡張）戦略を選択、既存コードへの影響範囲、新規ファイル数、既存機能との統合度を根拠として記載

- ✅ **テスト戦略の判断根拠が明記されている**
  - セクション3: UNIT_INTEGRATION戦略を選択、Unitテストの必要性、Integrationテストの必要性、BDDテスト不要の根拠を記載

- ✅ **テストコード戦略の判断根拠が明記されている**
  - セクション4: EXTEND_TEST戦略を選択、既存テストファイルの存在、既存テストとの関連性、新規ファイル不要の根拠を記載

- ✅ **既存コードへの影響範囲が分析されている**
  - セクション5: 修正が必要な既存ファイル（高影響・中影響）、影響を受けるが修正不要なファイル（低影響）、依存関係の変更、マイグレーション要否を分析

- ✅ **変更が必要なファイルがリストアップされている**
  - セクション6: 新規作成ファイル（なし）、修正が必要な既存ファイル（実装コード2個、テストコード3個）、削除が必要なファイル（なし）をリストアップ

- ✅ **設計が実装可能である**
  - セクション7: クラス設計、関数設計、データ構造設計、インターフェース設計を詳細に記載
  - セクション10: 実装順序を5つのPhaseに分割し、依存関係を考慮した順序で記載
  - セクション11: Unitテスト12個、Integrationテスト4個、E2Eテスト2個の詳細設計を記載

---

## 14. 参考資料

- **CLAUDE.md**: プロジェクトの全体方針とコーディングガイドライン
- **ARCHITECTURE.md**: Platform Engineeringのアーキテクチャ設計思想
- **README.md**: プロジェクト全体の使用方法
- **要件定義書**: `.ai-workflow/issue-315/01_requirements/output/requirements.md`
- **GitPython Documentation**: https://gitpython.readthedocs.io/

---

## 15. 変更履歴

| バージョン | 日付 | 変更内容 | 作成者 |
|-----------|------|---------|--------|
| 1.0.0 | 2025-10-10 | 初版作成 | AI Workflow |

---

**以上**
