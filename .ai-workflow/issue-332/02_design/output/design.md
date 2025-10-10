# 詳細設計書: Planning PhaseのJenkins統合とプロンプト修正

**Issue番号**: #332
**タイトル**: [FEATURE] Planning PhaseのJenkins統合とプロンプト修正
**作成日**: 2025-10-10
**バージョン**: 1.0.0

---

## 1. アーキテクチャ設計

### 1.1 システム全体図

```
┌─────────────────────────────────────────────────────────────────┐
│                    Jenkins Job (ai_workflow_orchestrator)         │
│                                                                   │
│  START_PHASE Parameter: ['planning', 'requirements', ...]        │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Planning     │──│ Requirements │──│ Design       │──...      │
│  │ Phase (新規) │  │ Phase        │  │ Phase        │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                   │                │                    │
└─────────┼───────────────────┼────────────────┼───────────────────┘
          │                   │                │
          ▼                   ▼                ▼
  ┌───────────────────────────────────────────────────────┐
  │         Python Phase Classes (phases/*.py)            │
  │                                                         │
  │  planning.py  requirements.py  design.py  ...         │
  │       │              │              │                  │
  │       └──────────────┴──────────────┘                 │
  │                      │                                 │
  │                      ▼                                 │
  │         BasePhase._get_planning_document_path()       │
  │                  (新規ヘルパー)                        │
  └───────────────────────────────────────────────────────┘
                         │
                         ▼
          ┌─────────────────────────────────┐
          │ Planning Document (planning.md) │
          │ .ai-workflow/issue-{N}/         │
          │   00_planning/output/           │
          └─────────────────────────────────┘
```

### 1.2 コンポーネント間の関係

```
[Jenkins DSL]
   ├─ START_PHASEパラメータに 'planning' を追加
   └─ デフォルト値を 'planning' に変更

[Jenkinsfile]
   ├─ Planning Phaseステージを追加（Requirements Phaseの前）
   └─ `python main.py execute --phase planning --issue ${ISSUE_NUMBER}`

[BasePhase (base_phase.py)]
   └─ _get_planning_document_path(issue_number) メソッドを追加
        ├─ Planning Documentのパスを構築
        ├─ 存在確認
        └─ @{relative_path} 形式またはwarningメッセージを返却

[各Phase (requirements.py, design.py, ...)]
   ├─ execute()メソッドで _get_planning_document_path() を呼び出し
   ├─ プロンプトテンプレートに {planning_document_path} プレースホルダーを埋め込み
   └─ revise()メソッドにも同様の処理を追加

[Prompts (prompts/*/execute.txt)]
   ├─ 「入力情報」セクションにPlanning Document参照を追加
   └─ タスク本文でPlanning Documentの確認を指示
```

### 1.3 データフロー

```
1. Jenkins Job起動（START_PHASE=planning）
     │
     ▼
2. Planning Phase実行
     ├─ Issue情報を取得
     ├─ planning.mdを生成
     └─ metadata.jsonに戦略判断を保存
     │
     ▼
3. Requirements Phase実行
     ├─ _get_planning_document_path(issue_number) 呼び出し
     ├─ planning.mdのパスを取得（@{path}形式）
     ├─ プロンプトテンプレートに埋め込み
     └─ Claude Agent SDKに渡す
     │
     ▼
4. Claude Agent SDK
     ├─ @{path}記法でplanning.mdを読み取り
     ├─ Planning Documentの内容を参照して要件定義書を作成
     └─ requirements.mdを生成
     │
     ▼
5. 以降のPhaseも同様（Design, Test Scenario, Implementation, ...）
```

---

## 2. 実装戦略: EXTEND

### 実装戦略の判断根拠

**判断根拠**:
- **既存システムへの統合**: Planning Phase (`phases/planning.py`) は既に実装済みだが、Jenkinsジョブからの実行とプロンプト参照機能が未実装
- **既存パターンの踏襲**: Requirements Phase以降の既存Phaseクラスとプロンプト構造をそのまま拡張する形式
- **共通ヘルパーメソッドの追加**: BasePhaseクラスに新しいヘルパーメソッドを追加し、全Phaseで再利用
- **複数ファイルの修正**: Jenkinsfile、Job DSL、7つのPhaseクラス、7つのプロンプトファイルを修正
- **新規作成は最小限**: 完全に新しいファイルの作成は不要（既存の修正のみ）

この要件は既存のAI Workflowシステムの拡張であり、**EXTEND（拡張）** が最も適切です。

---

## 3. テスト戦略: INTEGRATION_ONLY

### テスト戦略の判断根拠

**判断根拠**:
- **複数コンポーネント間の統合**: Jenkins → Python → Claude Agent SDK → Planning Document参照という複数コンポーネント間の連携
- **E2Eワークフローの検証**: Planning Phase → Requirements Phase → Design Phaseという一連のワークフローの動作確認が必要
- **ファイル生成とパス参照の検証**: Planning Documentが正しく生成され、後続Phaseで正しく参照されることの確認
- **Unitテストの必要性は低い**: `_get_planning_document_path()` は単純なファイルパス構築とチェックのみ（Unitテストで得られる価値は限定的）
- **BDDは不要**: ユーザーストーリーよりもシステム間の統合動作確認が主目的

**テスト戦略: INTEGRATION_ONLY** が最適です。具体的には以下のテストを実施：
1. Planning Phase単独実行テスト
2. Planning Phase → Requirements Phase連携テスト
3. Planning Documentが存在しない場合の挙動テスト（警告表示）
4. 全Phase（Phase 0-7）のE2Eテスト

---

## 4. テストコード戦略: CREATE_TEST

### テストコード戦略の判断根拠

**判断根拠**:
- **既存テストファイルの不在**: 現在、AI Workflowには統合テストが存在しない（今回新規作成）
- **新機能の検証**: Planning Phase統合という新機能のテストは既存テストに追加する対象ではない
- **独立したテストケース**: 既存のPhaseとは異なる、Planning Phaseの独自動作テストが必要
- **E2Eテストの新規作成**: 全Phaseを通したワークフローテストを新規作成

**テストコード戦略: CREATE_TEST** が適切です。新規テストファイルを作成します。

---

## 5. 影響範囲分析

### 5.1 既存コードへの影響

| コンポーネント | 影響の種類 | 影響度 |
|--------------|----------|-------|
| **Jenkins Job DSL** | 修正（パラメータ追加） | 低 |
| **Jenkinsfile** | 追加（新規ステージ） | 中 |
| **BasePhase** | 追加（ヘルパーメソッド） | 低 |
| **Requirements Phase** | 修正（プロンプト埋め込みロジック） | 中 |
| **Design Phase** | 修正（プロンプト埋め込みロジック） | 中 |
| **Test Scenario Phase** | 修正（プロンプト埋め込みロジック） | 中 |
| **Implementation Phase** | 修正（プロンプト埋め込みロジック） | 中 |
| **Testing Phase** | 修正（プロンプト埋め込みロジック） | 中 |
| **Documentation Phase** | 修正（プロンプト埋め込みロジック） | 中 |
| **Report Phase** | 修正（プロンプト埋め込みロジック） | 中 |
| **Prompts** | 追加（Planning Document参照セクション） | 低 |
| **Planning Phase** | 影響なし（既存実装を使用） | なし |

### 5.2 依存関係の変更

**新規依存関係**:
- 各Phase（Requirements以降）が Planning Phase の成果物（planning.md）に依存

**依存関係図**:
```
Planning Phase (Phase 0)
    │
    ├─ planning.md を生成
    │
    ▼
Requirements Phase (Phase 1)
    ├─ planning.md を参照（オプション）
    │
    ▼
Design Phase (Phase 2)
    ├─ requirements.md を参照（既存）
    ├─ planning.md を参照（新規、オプション）
    │
    ▼
... 以降のPhaseも同様
```

**注意**: Planning Documentが存在しない場合でも、各Phaseは正常に実行される（後方互換性を維持）。

### 5.3 マイグレーション要否

**マイグレーション不要**: 既存のIssueワークフローには影響なし。

**理由**:
- Planning Documentが存在しない場合でも、各Phaseは警告ログを出力するのみで正常実行
- 既存のIssue（Planning Phaseを実行していないIssue）でも後続Phaseは問題なく動作
- Planning Phaseはオプション扱い（推奨だが必須ではない）

---

## 6. 変更・追加ファイルリスト

### 6.1 新規作成ファイル

なし（既存ファイルの修正のみ）

### 6.2 修正が必要な既存ファイル

#### Jenkins関連（2ファイル）
1. `jenkins/jobs/dsl/ai-workflow/ai_workflow_orchestrator.groovy`
   - START_PHASEパラメータに `'planning'` を追加
   - デフォルト値を `'planning'` に変更

2. `jenkins/jobs/pipeline/ai-workflow/ai-workflow-orchestrator/Jenkinsfile`
   - Planning Phaseステージを追加（Requirements Phaseの前）

#### Python Phase Classes（8ファイル）
3. `scripts/ai-workflow/phases/base_phase.py`
   - `_get_planning_document_path(issue_number)` メソッドを追加

4. `scripts/ai-workflow/phases/requirements.py`
   - `execute()` メソッドにPlanning Document参照ロジックを追加
   - `revise()` メソッドにPlanning Document参照ロジックを追加

5. `scripts/ai-workflow/phases/design.py`
   - `execute()` メソッドにPlanning Document参照ロジックを追加
   - `revise()` メソッドにPlanning Document参照ロジックを追加

6. `scripts/ai-workflow/phases/test_scenario.py`
   - `execute()` メソッドにPlanning Document参照ロジックを追加
   - `revise()` メソッドにPlanning Document参照ロジックを追加

7. `scripts/ai-workflow/phases/implementation.py`
   - `execute()` メソッドにPlanning Document参照ロジックを追加
   - `revise()` メソッドにPlanning Document参照ロジックを追加

8. `scripts/ai-workflow/phases/testing.py`
   - `execute()` メソッドにPlanning Document参照ロジックを追加
   - `revise()` メソッドにPlanning Document参照ロジックを追加

9. `scripts/ai-workflow/phases/documentation.py`
   - `execute()` メソッドにPlanning Document参照ロジックを追加
   - `revise()` メソッドにPlanning Document参照ロジックを追加

10. `scripts/ai-workflow/phases/report.py`
    - `execute()` メソッドにPlanning Document参照ロジックを追加
    - `revise()` メソッドにPlanning Document参照ロジックを追加

#### Prompts（7ファイル）
11. `scripts/ai-workflow/prompts/requirements/execute.txt`
    - 「入力情報」セクションにPlanning Document参照を追加

12. `scripts/ai-workflow/prompts/design/execute.txt`
    - 「入力情報」セクションにPlanning Document参照を追加

13. `scripts/ai-workflow/prompts/test_scenario/execute.txt`
    - 「入力情報」セクションにPlanning Document参照を追加

14. `scripts/ai-workflow/prompts/implementation/execute.txt`
    - 「入力情報」セクションにPlanning Document参照を追加

15. `scripts/ai-workflow/prompts/testing/execute.txt`
    - 「入力情報」セクションにPlanning Document参照を追加

16. `scripts/ai-workflow/prompts/documentation/execute.txt`
    - 「入力情報」セクションにPlanning Document参照を追加

17. `scripts/ai-workflow/prompts/report/execute.txt`
    - 「入力情報」セクションにPlanning Document参照を追加

#### ドキュメント（2ファイル）
18. `jenkins/README.md`
    - ai_workflow_orchestratorジョブの説明にPlanning Phaseを追加
    - START_PHASEパラメータの説明を更新

19. `scripts/ai-workflow/README.md`
    - Phase 0（Planning）の説明を追加
    - 各PhaseでのPlanning Document参照方法を記載

### 6.3 削除が必要なファイル

なし

---

## 7. 詳細設計

### 7.1 BasePhaseクラスの拡張

#### 7.1.1 新規メソッド: `_get_planning_document_path()`

**ファイル**: `scripts/ai-workflow/phases/base_phase.py`

**実装位置**: 既存のヘルパーメソッド（`load_prompt()`, `update_phase_status()` など）の近く

**シグネチャ**:
```python
def _get_planning_document_path(self, issue_number: int) -> str:
    """
    Planning Phase成果物のパスを取得

    Args:
        issue_number: Issue番号

    Returns:
        str: Planning Documentのパス（@{relative_path}形式）または警告メッセージ

    Notes:
        - Planning Documentのパス: .ai-workflow/issue-{number}/00_planning/output/planning.md
        - 存在する場合: working_dirからの相対パスを取得し、@{rel_path}形式で返す
        - 存在しない場合: "Planning Phaseは実行されていません"を返す
    """
```

**実装詳細**:
```python
def _get_planning_document_path(self, issue_number: int) -> str:
    """
    Planning Phase成果物のパスを取得

    Args:
        issue_number: Issue番号

    Returns:
        str: Planning Documentのパス（@{relative_path}形式）または警告メッセージ
    """
    # Planning Documentのパスを構築
    # .ai-workflow/issue-{number}/00_planning/output/planning.md
    planning_dir = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '00_planning' / 'output'
    planning_file = planning_dir / 'planning.md'

    # ファイル存在確認
    if not planning_file.exists():
        print(f"[WARNING] Planning Phase成果物が見つかりません: {planning_file}")
        return "Planning Phaseは実行されていません"

    # working_dirからの相対パスを取得
    try:
        rel_path = planning_file.relative_to(self.claude.working_dir)
        planning_path_str = f'@{rel_path}'
        print(f"[INFO] Planning Document参照: {planning_path_str}")
        return planning_path_str
    except ValueError:
        # 相対パスが取得できない場合（異なるドライブなど）
        print(f"[WARNING] Planning Documentの相対パスが取得できません: {planning_file}")
        return "Planning Phaseは実行されていません"
```

**エラーハンドリング**:
- ファイルが存在しない場合: 警告ログを出力し、`"Planning Phaseは実行されていません"` を返却
- 相対パスが取得できない場合: 警告ログを出力し、`"Planning Phaseは実行されていません"` を返却
- Phase実行自体は失敗させない（後方互換性を維持）

### 7.2 各Phaseクラスの修正

#### 7.2.1 Requirements Phase (`requirements.py`)

**修正対象メソッド**: `execute()`, `revise()`

**execute()メソッドの修正**:

**修正前**（現在の実装、行25-60）:
```python
def execute(self) -> Dict[str, Any]:
    try:
        # Issue情報を取得
        issue_number = int(self.metadata.data['issue_number'])
        issue_info = self.github.get_issue_info(issue_number)

        # Issue情報をフォーマット
        issue_info_text = self._format_issue_info(issue_info)

        # 実行プロンプトを読み込み
        execute_prompt_template = self.load_prompt('execute')

        # Issue情報をプロンプトに埋め込み
        execute_prompt = execute_prompt_template.replace(
            '{issue_info}',
            issue_info_text
        ).replace(
            '{issue_number}',
            str(issue_number)
        )

        # Claude Agent SDKでタスクを実行
        messages = self.execute_with_claude(
            prompt=execute_prompt,
            max_turns=30,
            log_prefix='execute'
        )
        # ... 以降の処理
```

**修正後**:
```python
def execute(self) -> Dict[str, Any]:
    try:
        # Issue情報を取得
        issue_number = int(self.metadata.data['issue_number'])
        issue_info = self.github.get_issue_info(issue_number)

        # Issue情報をフォーマット
        issue_info_text = self._format_issue_info(issue_info)

        # Planning Phase成果物のパス取得（新規追加）
        planning_path_str = self._get_planning_document_path(issue_number)

        # 実行プロンプトを読み込み
        execute_prompt_template = self.load_prompt('execute')

        # プロンプトに情報を埋め込み（planning_document_pathを追加）
        execute_prompt = execute_prompt_template.replace(
            '{planning_document_path}',
            planning_path_str
        ).replace(
            '{issue_info}',
            issue_info_text
        ).replace(
            '{issue_number}',
            str(issue_number)
        )

        # Claude Agent SDKでタスクを実行
        messages = self.execute_with_claude(
            prompt=execute_prompt,
            max_turns=30,
            log_prefix='execute'
        )
        # ... 以降の処理
```

**変更点**:
1. `_get_planning_document_path(issue_number)` の呼び出しを追加
2. プロンプトテンプレートで `{planning_document_path}` を `planning_path_str` で置換

**revise()メソッドの修正**:

同様に、`revise()` メソッドにも Planning Document参照ロジックを追加します。

**修正前**（現在の実装、行176-256）:
```python
def revise(self, review_feedback: str) -> Dict[str, Any]:
    try:
        # Issue情報を取得
        issue_number = int(self.metadata.data['issue_number'])
        issue_info = self.github.get_issue_info(issue_number)

        # Issue情報をフォーマット
        issue_info_text = self._format_issue_info(issue_info)

        # 元の要件定義書を読み込み
        requirements_file = self.output_dir / 'requirements.md'

        if not requirements_file.exists():
            return {
                'success': False,
                'output': None,
                'error': 'requirements.mdが存在しません。'
            }

        # 修正プロンプトを読み込み
        revise_prompt_template = self.load_prompt('revise')

        # working_dirからの相対パスを使用
        rel_path = requirements_file.relative_to(self.claude.working_dir)

        # プロンプトに情報を埋め込み
        revise_prompt = revise_prompt_template.replace(
            '{requirements_document_path}',
            f'@{rel_path}'
        ).replace(
            '{review_feedback}',
            review_feedback
        ).replace(
            '{issue_info}',
            issue_info_text
        ).replace(
            '{issue_number}',
            str(issue_number)
        )
        # ... 以降の処理
```

**修正後**:
```python
def revise(self, review_feedback: str) -> Dict[str, Any]:
    try:
        # Issue情報を取得
        issue_number = int(self.metadata.data['issue_number'])
        issue_info = self.github.get_issue_info(issue_number)

        # Issue情報をフォーマット
        issue_info_text = self._format_issue_info(issue_info)

        # Planning Phase成果物のパス取得（新規追加）
        planning_path_str = self._get_planning_document_path(issue_number)

        # 元の要件定義書を読み込み
        requirements_file = self.output_dir / 'requirements.md'

        if not requirements_file.exists():
            return {
                'success': False,
                'output': None,
                'error': 'requirements.mdが存在しません。'
            }

        # 修正プロンプトを読み込み
        revise_prompt_template = self.load_prompt('revise')

        # working_dirからの相対パスを使用
        rel_path = requirements_file.relative_to(self.claude.working_dir)

        # プロンプトに情報を埋め込み（planning_document_pathを追加）
        revise_prompt = revise_prompt_template.replace(
            '{planning_document_path}',
            planning_path_str
        ).replace(
            '{requirements_document_path}',
            f'@{rel_path}'
        ).replace(
            '{review_feedback}',
            review_feedback
        ).replace(
            '{issue_info}',
            issue_info_text
        ).replace(
            '{issue_number}',
            str(issue_number)
        )
        # ... 以降の処理
```

**変更点**:
1. `_get_planning_document_path(issue_number)` の呼び出しを追加
2. プロンプトテンプレートで `{planning_document_path}` を `planning_path_str` で置換

#### 7.2.2 Design Phase以降

**対象クラス**:
- `design.py`
- `test_scenario.py`
- `implementation.py`
- `testing.py`
- `documentation.py`
- `report.py`

**修正内容**: Requirements Phaseと同様の修正を全て適用

**修正箇所**:
1. `execute()` メソッド: Planning Document参照ロジックを追加
2. `revise()` メソッド: Planning Document参照ロジックを追加（実装されている場合のみ）

**注意**: 各Phaseごとにプロンプトテンプレートの変数名が異なる（`{requirements_document_path}`, `{design_document_path}` など）ため、適切な変数名を使用すること。

### 7.3 プロンプトテンプレートの修正

#### 7.3.1 Requirements Phase Prompt (`prompts/requirements/execute.txt`)

**修正箇所**: 冒頭の「Issue情報」セクションの前に「入力情報」セクションを追加

**修正前**（現在の実装、行1-10）:
```markdown
# 要件定義フェーズ - 実行プロンプト

## タスク概要

GitHubのIssue情報から詳細な要件定義書を作成してください。

## Issue情報

{issue_info}
```

**修正後**:
```markdown
# 要件定義フェーズ - 実行プロンプト

## タスク概要

GitHubのIssue情報から詳細な要件定義書を作成してください。

## 入力情報

### Planning Phase成果物
- Planning Document: {planning_document_path}

**注意**: Planning Phaseが実行されている場合、開発計画（実装戦略、テスト戦略、リスク、スケジュール）を必ず確認してください。

### GitHub Issue情報
- Issue URL: {issue_url}
- Issue Title: {issue_title}
- Issue Body: {issue_body}

以下はIssue詳細です：

{issue_info}
```

**追加内容**:
1. 「入力情報」セクションを新規追加
2. Planning Document参照（`{planning_document_path}` プレースホルダー）
3. Planning Documentの確認指示

**タスク本文への追加**（行11-13付近に追加）:
```markdown
## 要件定義書の構成

以下のセクションを含む要件定義書を作成してください：

### 0. Planning Documentの確認（Planning Phaseが実行されている場合）
- 開発計画の全体像を把握
- スコープ、技術選定、リスク、スケジュールを確認
- Planning Documentで策定された戦略を踏まえて要件定義を実施

### 1. 概要
- Issue本文の「## 概要」セクションを要約
- 背景と目的を明確に記述
- ビジネス価値・技術的価値を説明
...
```

#### 7.3.2 Design Phase以降のPrompts

**対象ファイル**:
- `prompts/design/execute.txt`
- `prompts/test_scenario/execute.txt`
- `prompts/implementation/execute.txt`
- `prompts/testing/execute.txt`
- `prompts/documentation/execute.txt`
- `prompts/report/execute.txt`

**修正内容**: Requirements Phaseと同様の修正を全て適用

**注意**: 各Phaseごとに既存のドキュメント参照（`{requirements_document_path}`, `{design_document_path}` など）があるため、Planning Document参照を追加する際は既存の参照を保持すること。

**Design Phaseの例**（`prompts/design/execute.txt`）:

**修正前**:
```markdown
## 入力情報

### 要件定義書
{requirements_document_path}

### GitHub Issue情報
{issue_info}
```

**修正後**:
```markdown
## 入力情報

### Planning Phase成果物
- Planning Document: {planning_document_path}

**注意**: Planning Phaseが実行されている場合、開発計画（実装戦略、テスト戦略、リスク、スケジュール）を必ず確認してください。

### 要件定義書
{requirements_document_path}

### GitHub Issue情報
{issue_info}
```

### 7.4 Jenkins統合

#### 7.4.1 Job DSL修正 (`ai_workflow_orchestrator.groovy`)

**ファイル**: `jenkins/jobs/dsl/ai-workflow/ai_workflow_orchestrator.groovy`

**修正箇所**: 行53（START_PHASEパラメータ定義）

**修正前**:
```groovy
choiceParam('START_PHASE', ['requirements', 'design', 'test_scenario', 'implementation', 'testing', 'documentation', 'report'], '''
開始フェーズ

ワークフローを開始するフェーズを指定します。
途中からジョブを再開する場合に使用します。

デフォルト: requirements（最初から実行）
        '''.stripIndent().trim())
```

**修正後**:
```groovy
choiceParam('START_PHASE', ['planning', 'requirements', 'design', 'test_scenario', 'implementation', 'testing', 'documentation', 'report'], '''
開始フェーズ

ワークフローを開始するフェーズを指定します。
途中からジョブを再開する場合に使用します。

デフォルト: planning（最初から実行）
        '''.stripIndent().trim())
```

**変更点**:
1. `'planning'` を選択肢の先頭に追加
2. 説明文のデフォルト値を `planning` に変更

#### 7.4.2 Jenkinsfile修正 (`Jenkinsfile`)

**ファイル**: `jenkins/jobs/pipeline/ai-workflow/ai-workflow-orchestrator/Jenkinsfile`

**修正箇所**: Requirements Phaseステージ（行159）の前に Planning Phaseステージを追加

**追加内容**:
```groovy
stage('Phase 0: Planning') {
    when {
        expression {
            def phaseOrder = ['planning', 'requirements', 'design', 'test_scenario', 'implementation', 'testing', 'documentation', 'report']
            def startIndex = phaseOrder.indexOf(params.START_PHASE)
            def currentIndex = phaseOrder.indexOf('planning')
            return currentIndex >= startIndex
        }
    }
    steps {
        script {
            echo "========================================="
            echo "Stage: Phase 0 - Planning"
            echo "========================================="

            dir(env.WORKFLOW_DIR) {
                if (params.DRY_RUN) {
                    echo "[DRY RUN] Phase 0実行をスキップ"
                } else {
                    // Phase実行（execute + review統合）
                    sh """
                        python main.py execute \
                            --phase planning \
                            --issue ${env.ISSUE_NUMBER}
                    """
                }
            }
        }
    }
}
```

**追加位置**: 既存の `stage('Phase 1: Requirements')` の直前（行159の前）

**既存ステージの修正**: すべてのPhaseステージの `phaseOrder` 配列に `'planning'` を追加

**修正例**（Requirements Phaseステージ）:
```groovy
when {
    expression {
        def phaseOrder = ['planning', 'requirements', 'design', 'test_scenario', 'implementation', 'testing', 'documentation', 'report']
        def startIndex = phaseOrder.indexOf(params.START_PHASE)
        def currentIndex = phaseOrder.indexOf('requirements')
        return currentIndex >= startIndex
    }
}
```

**注意**: Design Phase, Test Scenario Phase, Implementation Phase, Testing Phase, Documentation Phase, Report Phaseの各ステージも同様に `phaseOrder` 配列を修正すること。

---

## 8. セキュリティ考慮事項

### 8.1 認証・認可

- **Planning Documentへのアクセス**: ファイルシステムベースのアクセス（既存のPhase成果物と同様）
- **追加の認証不要**: 既存のJenkins認証・GitHub Token認証で対応可能

### 8.2 データ保護

- **Planning Documentの内容**: 機密情報を含む可能性があるため、リポジトリのアクセス権限管理を継続
- **パス情報の漏洩防止**: ログ出力時にファイルパスを出力するが、既存の実装と同様の扱い（問題なし）

### 8.3 セキュリティリスクと対策

| リスク | 対策 |
|------|------|
| **パストラバーサル攻撃** | `issue_number` は整数型に変換しているため、ディレクトリトラバーサルは不可 |
| **ファイル存在確認の悪用** | Planning Documentの存在確認は内部処理のみ、外部APIでの公開なし |
| **Claude Agent SDKへの不正パス注入** | `@{relative_path}` 形式のみを使用、既存の実装と同様のセキュリティレベル |

**結論**: 既存のセキュリティレベルを維持しており、追加のリスクは極めて低い。

---

## 9. 非機能要件への対応

### 9.1 パフォーマンス

| 要件 | 対応策 | 目標値 |
|------|-------|-------|
| **NFR-1.1**: Planning Phase追加によるJenkinsジョブ実行時間の増加は5分以内 | Planning PhaseはClaude Agent SDKの呼び出しのみ、複雑な処理なし | 3-5分（見積もり） |
| **NFR-1.2**: `_get_planning_document_path()` の実行時間は100ms以内 | ファイル存在確認と相対パス取得のみ（O(1)） | 10ms以下（実測想定） |
| **NFR-1.3**: 各Phaseのexecute()メソッドでのプロンプト生成時間の増加は10ms以内 | 文字列置換処理のみ追加（O(n)、nは小さい） | 5ms以下（実測想定） |

**結論**: すべての非機能要件を満たす見込み。

### 9.2 スケーラビリティ

- **複数Issueの同時実行**: Issue番号ごとに独立したディレクトリ構造のため、スケーラビリティに影響なし
- **Planning Documentのファイルサイズ**: Markdownテキストファイル（数KB～数十KB想定）、パフォーマンスへの影響は無視できる

### 9.3 保守性

- **コードの再利用**: `_get_planning_document_path()` ヘルパーメソッドにより、重複コードを削減（DRY原則）
- **拡張性**: 新しいPhaseを追加する際も、BasePhaseのヘルパーメソッドを再利用可能
- **プロンプトの統一**: 全Phaseで統一されたPlanning Document参照フォーマットを使用

---

## 10. 実装の順序

### 10.1 推奨実装順序

**Phase 1: 基盤整備（1日目）**
1. BasePhaseヘルパーメソッドの実装（`_get_planning_document_path()`）
   - 実装: 30分
   - ローカルテスト: 30分
2. Jenkinsfile修正（Planning Phaseステージ追加）
   - 実装: 30分
3. Job DSL修正（START_PHASEパラメータ更新）
   - 実装: 15分
4. シードジョブ実行とJenkins動作確認
   - 実行: 15分

**Phase 2: Requirements Phase統合（1日目午後）**
5. Requirements Phase プロンプト修正（`execute.txt`）
   - 実装: 30分
6. Requirements Phase クラス修正（`requirements.py`）
   - `execute()` メソッド: 30分
   - `revise()` メソッド: 30分
7. テスト実行（Planning → Requirements連携）
   - 実行: 30分

**Phase 3: 残りPhaseの統合（2日目）**
8. Design Phase プロンプト修正（`execute.txt`）
   - 実装: 30分
9. Design Phase クラス修正（`design.py`）
   - 実装: 30分
10. Test Scenario Phase プロンプト修正（`execute.txt`）
    - 実装: 30分
11. Test Scenario Phase クラス修正（`test_scenario.py`）
    - 実装: 30分
12. Implementation Phase プロンプト修正（`execute.txt`）
    - 実装: 30分
13. Implementation Phase クラス修正（`implementation.py`）
    - 実装: 30分
14. Testing Phase プロンプト修正（`execute.txt`）
    - 実装: 30分
15. Testing Phase クラス修正（`testing.py`）
    - 実装: 30分
16. Documentation Phase プロンプト修正（`execute.txt`）
    - 実装: 30分
17. Documentation Phase クラス修正（`documentation.py`）
    - 実装: 30分
18. Report Phase プロンプト修正（`execute.txt`）
    - 実装: 30分
19. Report Phase クラス修正（`report.py`）
    - 実装: 30分

**Phase 4: ドキュメント更新とE2Eテスト（3日目）**
20. `jenkins/README.md` 更新
    - 実装: 30分
21. `scripts/ai-workflow/README.md` 更新
    - 実装: 30分
22. E2Eテスト実行（Planning → Report全Phase）
    - 実行: 2-3時間
23. バグ修正とリトライ
    - 実行: 1-2時間

**合計見積もり**: 3日間

### 10.2 依存関係の考慮

**必須の順序**:
1. BasePhaseヘルパーメソッド → 各Phaseクラス修正
2. Jenkinsfile修正 + Job DSL修正 → シードジョブ実行
3. プロンプト修正 → Phaseクラス修正（プレースホルダーが必要）

**並行可能な作業**:
- 各Phaseのプロンプト修正（Requirements, Design, Test Scenario, ...）
- 各Phaseのクラス修正（Requirements, Design, Test Scenario, ...）

**クリティカルパス**:
```
BasePhaseヘルパー実装
    ↓
Jenkins統合（Jenkinsfile + Job DSL）
    ↓
Requirements Phase統合（プロンプト + クラス）
    ↓
Design Phase統合（プロンプト + クラス）
    ↓
... 以降のPhase統合
    ↓
E2Eテスト
```

---

## 11. リスクと軽減策

### リスク1: Planning Documentが存在しない場合のエラーハンドリング不足

**影響度**: 中
**発生確率**: 中

**軽減策**:
- `_get_planning_document_path()` で存在チェックを実施
- 存在しない場合でもエラー終了せず、警告ログを出力して継続
- プロンプトに「Planning Phaseは実行されていません」と明示
- **実装済み**: BasePhaseヘルパーメソッドで対応済み

**テスト計画**:
- Planning Documentが存在しない状態で各Phaseを実行し、正常動作を確認

### リスク2: プロンプト修正の漏れ（7ファイル）

**影響度**: 高
**発生確率**: 低

**軽減策**:
- チェックリストを作成し、全7Phaseのプロンプト修正を確認
- 統一されたテンプレートを使用して、コピー&ペーストで修正
- 実装フェーズでレビュー時に全ファイルを確認
- **実装時**: Grepコマンドで `{planning_document_path}` プレースホルダーの存在を確認

**チェックリスト**:
- [ ] `prompts/requirements/execute.txt`
- [ ] `prompts/design/execute.txt`
- [ ] `prompts/test_scenario/execute.txt`
- [ ] `prompts/implementation/execute.txt`
- [ ] `prompts/testing/execute.txt`
- [ ] `prompts/documentation/execute.txt`
- [ ] `prompts/report/execute.txt`

### リスク3: Jenkinsジョブの既存パイプライン破壊

**影響度**: 高
**発生確率**: 低

**軽減策**:
- Job DSLファイルとJenkinsfileのバックアップを取得
- 開発ブランチで十分にテストした後、mainブランチにマージ
- ロールバック手順を事前に準備
- **実装時**: DRY_RUNモードでJenkinsジョブをテスト実行

**ロールバック手順**:
1. Gitで変更をrevert
2. シードジョブを再実行
3. Jenkinsジョブが元の状態に戻ることを確認

### リスク4: Claude Agent SDKの@記法の誤用

**影響度**: 中
**発生確率**: 低

**軽減策**:
- Planning Phaseクラス（`planning.py`）の既存実装を参考にする
- `working_dir` からの相対パスを正しく取得する
- テストでファイルが正しく読み込まれるか確認
- **実装済み**: BasePhaseヘルパーメソッドで `relative_to()` を使用

**テスト計画**:
- Planning Documentが正しく読み込まれることを確認（Claude Agent SDKのログで検証）

---

## 12. テスト計画

### 12.1 統合テスト

#### テストケース1: Planning Phase単独実行テスト

**目的**: Planning Phaseが単独で正常に実行されることを確認

**手順**:
1. Jenkinsジョブを実行（START_PHASE=planning, ISSUE_URL=テスト用Issue）
2. Planning Phaseステージが実行されることを確認
3. `.ai-workflow/issue-{N}/00_planning/output/planning.md` が生成されることを確認
4. metadata.jsonに戦略判断が保存されることを確認

**期待結果**:
- Planning Phaseステージが成功
- planning.mdが生成される
- metadata.jsonに `design_decisions` が保存される

#### テストケース2: Planning Phase → Requirements Phase連携テスト

**目的**: Planning Phaseの成果物を Requirements Phaseが正しく参照することを確認

**手順**:
1. Jenkinsジョブを実行（START_PHASE=planning, ISSUE_URL=テスト用Issue）
2. Planning PhaseとRequirements Phaseが順次実行されることを確認
3. Requirements Phaseのログで Planning Documentのパスが出力されることを確認
4. Requirements Phaseの成果物（requirements.md）にPlanning Documentの内容が反映されていることを確認

**期待結果**:
- Requirements Phaseで `[INFO] Planning Document参照: @.ai-workflow/issue-{N}/00_planning/output/planning.md` のログが出力される
- requirements.mdにPlanning Documentの戦略が反映される

#### テストケース3: Planning Documentが存在しない場合のテスト

**目的**: Planning Documentが存在しない場合でも、各Phaseが正常に実行されることを確認

**手順**:
1. Jenkinsジョブを実行（START_PHASE=requirements, ISSUE_URL=テスト用Issue）
2. Planning Phaseをスキップ（Requirements Phaseから開始）
3. Requirements Phaseのログで警告メッセージが出力されることを確認
4. Requirements Phaseが正常に完了することを確認

**期待結果**:
- Requirements Phaseで `[WARNING] Planning Phase成果物が見つかりません` のログが出力される
- プロンプトに `Planning Phaseは実行されていません` が埋め込まれる
- Requirements Phaseは正常に完了する（エラー終了しない）

#### テストケース4: 全Phase（Phase 0-7）のE2Eテスト

**目的**: Planning Phase → Report Phaseまでの全ワークフローが正常に動作することを確認

**手順**:
1. Jenkinsジョブを実行（START_PHASE=planning, ISSUE_URL=テスト用Issue）
2. 全Phaseが順次実行されることを確認
3. 各Phaseでそれぞれの成果物が生成されることを確認
4. 各PhaseのログでPlanning Documentのパスが出力されることを確認

**期待結果**:
- 全Phaseが成功
- 全Phaseでplanning.mdが参照される
- 各Phaseの成果物にPlanning Documentの内容が反映される

### 12.2 テスト環境

- **Jenkins環境**: dev環境
- **テスト用Issue**: #332（本Issue）または新規テスト用Issue
- **ブランチ**: `ai-workflow/issue-332`（本Issue対応ブランチ）

### 12.3 テスト実行タイミング

- **Phase 2完了後**: テストケース1, 2, 3を実行
- **Phase 3完了後**: テストケース4を実行（全Phase統合テスト）

---

## 13. ドキュメント更新

### 13.1 jenkins/README.md

**追加セクション**: 「AI Workflow Orchestrator」ジョブの説明

**追加内容**:
```markdown
### Planning Phaseの実行

Planning Phaseは、Issue複雑度分析、実装戦略・テスト戦略の事前決定、タスク分割、依存関係特定、リスク評価を行う重要なフェーズです。

**実行方法**:
```bash
# Jenkinsジョブで以下のパラメータを指定
START_PHASE: planning
ISSUE_URL: https://github.com/tielec/infrastructure-as-code/issues/332
```

**成果物**:
- Planning Document: `.ai-workflow/issue-{N}/00_planning/output/planning.md`

**注意事項**:
- Planning Phaseの成果物は、後続の全Phase（Requirements, Design, Test Scenario, Implementation, Testing, Documentation, Report）で参照されます
- Planning Phaseをスキップした場合でも、後続Phaseは正常に実行されます（警告ログのみ出力）
```

### 13.2 scripts/ai-workflow/README.md

**追加セクション**: 「Phase 0: Planning」の説明

**追加内容**:
```markdown
## Phase 0: Planning

### 概要

Planning Phaseは、プロジェクトマネージャ役として実装戦略・テスト戦略を事前決定し、Issue複雑度分析・タスク分割・依存関係特定・リスク評価を行う重要なフェーズです。

### 成果物

- **Planning Document** (`planning.md`): 開発計画書
  - Issue複雑度分析
  - 実装タスクの洗い出しと分割
  - タスク間依存関係
  - 各フェーズの見積もり
  - リスク評価とリスク軽減策
  - 実装戦略・テスト戦略の事前決定

### 後続Phaseでの参照

Planning Documentは、後続の全Phase（Phase 1-7）で参照されます。各Phaseのプロンプトに以下のセクションが追加されています：

```markdown
## 入力情報

### Planning Phase成果物
- Planning Document: @.ai-workflow/issue-{N}/00_planning/output/planning.md

**注意**: Planning Phaseが実行されている場合、開発計画（実装戦略、テスト戦略、リスク、スケジュール）を必ず確認してください。
```

### Planning Phaseのスキップ

Planning Phaseをスキップした場合（START_PHASE=requirements以降で実行した場合）でも、後続Phaseは正常に実行されます。この場合、プロンプトには以下のメッセージが埋め込まれます：

```
Planning Document: Planning Phaseは実行されていません
```

### 推奨ワークフロー

Planning Phaseから開始することを強く推奨します。Planning Phaseで策定された開発計画に基づいて、後続Phaseが一貫性のある作業を実施できます。

```bash
# 推奨: Planning Phaseから開始
START_PHASE=planning

# 非推奨: Planning Phaseをスキップ
START_PHASE=requirements
```
```

---

## 14. 成功基準

### 14.1 機能要件の成功基準

| 要件 | 成功基準 | 検証方法 |
|------|---------|---------|
| **FR-1**: JenkinsジョブへのPlanning Phase統合 | Planning PhaseがSTART_PHASEパラメータで選択可能、デフォルト値がplanning | Job DSL画面で確認、Jenkinsジョブ実行 |
| **FR-2**: BasePhaseヘルパーメソッドの追加 | `_get_planning_document_path()`が正しく動作、存在する場合は@{path}形式、存在しない場合は警告メッセージ | ユニットテスト、統合テスト |
| **FR-3**: 各Phaseプロンプトの修正 | 全7Phaseのexecute.txtにPlanning Document参照セクションが追加 | ファイル内容確認、Grepコマンド |
| **FR-4**: 各PhaseクラスのPlanning Document参照ロジック追加 | 全7Phaseのexecute()とrevise()メソッドでPlanning Document参照ロジックが動作 | 統合テスト、ログ確認 |
| **FR-5**: ドキュメント更新 | jenkins/README.mdとscripts/ai-workflow/README.mdにPlanning Phaseの説明が追加 | ドキュメント確認 |

### 14.2 非機能要件の成功基準

| 要件 | 成功基準 | 検証方法 |
|------|---------|---------|
| **NFR-1.1**: Planning Phase追加によるJenkinsジョブ実行時間の増加は5分以内 | Planning Phase実行時間が3-5分 | Jenkinsジョブログでの実行時間確認 |
| **NFR-1.2**: `_get_planning_document_path()`の実行時間は100ms以内 | メソッド実行時間が10ms以下 | パフォーマンス計測 |
| **NFR-1.3**: プロンプト生成時間の増加は10ms以内 | 文字列置換処理の追加によるオーバーヘッドが5ms以下 | パフォーマンス計測 |
| **NFR-2.1**: Planning Documentが存在しない場合でも各Phaseは正常に実行 | Planning Documentが存在しない場合でもエラー終了せず、警告ログのみ出力 | 統合テスト |
| **NFR-3.1**: 新しいPhaseを追加する際、BasePhaseのヘルパーメソッドを再利用可能 | ヘルパーメソッドがBasePhaseに実装され、継承可能 | コード確認 |

---

## 15. 品質ゲート（Phase 2）

本設計書は、以下の品質ゲートを満たしています：

- ✅ **実装戦略の判断根拠が明記されている**: セクション2で明記（EXTEND戦略、理由を明確に記載）
- ✅ **テスト戦略の判断根拠が明記されている**: セクション3で明記（INTEGRATION_ONLY戦略、理由を明確に記載）
- ✅ **テストコード戦略の判断根拠が明記されている**: セクション4で明記（CREATE_TEST戦略、理由を明確に記載）
- ✅ **既存コードへの影響範囲が分析されている**: セクション5で詳細に分析（19ファイルの修正対象をリストアップ）
- ✅ **変更が必要なファイルがリストアップされている**: セクション6で全ファイルをリストアップ（新規作成0ファイル、修正19ファイル、削除0ファイル）
- ✅ **設計が実装可能である**: セクション7で詳細な実装方法を記載（コードサンプル、修正前後の比較、具体的な実装箇所）

---

## 16. 参考情報

### 16.1 関連Issue

- **Issue #313**: Planning Phase実装（既存実装）
- **Issue #305**: AI Workflowの全Phase E2Eテスト

### 16.2 関連ドキュメント

- `CLAUDE.md`: プロジェクトの全体方針とコーディングガイドライン
- `scripts/ai-workflow/README.md`: AI Workflowの概要と使用方法
- `scripts/ai-workflow/ARCHITECTURE.md`: AI Workflowのアーキテクチャ設計思想
- `jenkins/README.md`: Jenkinsジョブの使用方法
- `jenkins/CONTRIBUTION.md`: Jenkins開発のベストプラクティス

### 16.3 技術仕様

- **Claude Agent SDK**: `@{path}` 記法でファイル参照
- **Python**: 3.11以上
- **Job DSL**: Groovy DSL
- **Jenkinsfile**: Declarative Pipeline

---

**承認者**: （レビュー後に記入）
**承認日**: （レビュー後に記入）
