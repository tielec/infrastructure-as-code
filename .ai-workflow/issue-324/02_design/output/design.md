# 詳細設計書 - Issue #324

## 0. Planning Documentの確認

Planning Phase（Phase 0）で作成された計画書を確認しました。以下の重要事項を踏まえて詳細設計を実施します：

### 開発戦略の概要（Planning Documentより）
- **複雑度**: 中程度
- **見積もり工数**: 8時間
- **リスクレベル**: 低
- **Planning Documentで決定済みの戦略**:
  - 実装戦略: CREATE（新規ファイル作成）
  - テスト戦略: UNIT_INTEGRATION（ユニット + 統合テスト）
  - テストコード戦略: CREATE_TEST（新規テストファイル作成）

### 既に対応済みの項目（Planning Documentより）
- ✅ プロンプトファイル作成済み（`prompts/test_implementation/*.txt`）
- ✅ metadata.json構造対応済み（`workflow_state.py:80-86`）
- ✅ Jenkins DSL対応済み（存在する場合）
- ✅ BasePhaseのPHASE_NUMBERSマッピングに'test_implementation': '05'を追加済み

---

## 1. アーキテクチャ設計

### 1.1 システム全体図

```
┌─────────────────────────────────────────────────────────┐
│           AIワークフロー 8フェーズシステム                 │
└─────────────────────────────────────────────────────────┘
                         ↓
    ┌──────────────────────────────────────────┐
    │  Phase 0: planning（計画）                │
    └──────────────────────────────────────────┘
                         ↓
    ┌──────────────────────────────────────────┐
    │  Phase 1: requirements（要件定義）         │
    └──────────────────────────────────────────┘
                         ↓
    ┌──────────────────────────────────────────┐
    │  Phase 2: design（設計）                  │
    │  - 実装戦略・テスト戦略決定                │
    └──────────────────────────────────────────┘
                         ↓
    ┌──────────────────────────────────────────┐
    │  Phase 3: test_scenario（テストシナリオ）  │
    └──────────────────────────────────────────┘
                         ↓
    ┌──────────────────────────────────────────┐
    │  Phase 4: implementation（実装）           │
    │  - 責務: 実コードのみ                      │
    │  - テストコード実装は禁止                  │
    └──────────────────────────────────────────┘
                         ↓
    ┌──────────────────────────────────────────┐
    │  Phase 5: test_implementation（新規）      │
    │  - 責務: テストコードのみ                  │
    │  - 実コード修正は禁止                      │
    └──────────────────────────────────────────┘
                         ↓
    ┌──────────────────────────────────────────┐
    │  Phase 6: testing（テスト実行）            │
    │  - Phase番号変更: 5→6                     │
    └──────────────────────────────────────────┘
                         ↓
    ┌──────────────────────────────────────────┐
    │  Phase 7: documentation（ドキュメント）    │
    │  - Phase番号変更: 6→7                     │
    └──────────────────────────────────────────┘
                         ↓
    ┌──────────────────────────────────────────┐
    │  Phase 8: report（レポート）               │
    │  - Phase番号変更: 7→8                     │
    └──────────────────────────────────────────┘
```

### 1.2 TestImplementationPhaseコンポーネント設計

```
┌─────────────────────────────────────────────────────────┐
│           TestImplementationPhase クラス                  │
├─────────────────────────────────────────────────────────┤
│  継承: BasePhase                                         │
│                                                          │
│  [フィールド]                                             │
│  - phase_name: 'test_implementation'                    │
│  - prompts_dir: prompts/test_implementation/            │
│  - output_dir: .ai-workflow/issue-XXX/05_test_implementation/output/ │
│  - execute_dir: .ai-workflow/issue-XXX/05_test_implementation/execute/ │
│  - review_dir: .ai-workflow/issue-XXX/05_test_implementation/review/ │
│  - revise_dir: .ai-workflow/issue-XXX/05_test_implementation/revise/ │
│                                                          │
│  [メソッド]                                               │
│  + __init__(*args, **kwargs)                            │
│  + execute() -> Dict[str, Any]                          │
│  + review() -> Dict[str, Any]                           │
│  + revise(review_feedback: str) -> Dict[str, Any]       │
└─────────────────────────────────────────────────────────┘
                         ↓ 使用
┌─────────────────────────────────────────────────────────┐
│                  依存コンポーネント                        │
├─────────────────────────────────────────────────────────┤
│  - BasePhase: 基底クラス                                 │
│  - MetadataManager: メタデータ管理                       │
│  - ClaudeAgentClient: Claude API連携                    │
│  - GitHubClient: GitHub API連携                         │
│  - GitManager: Git操作                                  │
└─────────────────────────────────────────────────────────┘
```

### 1.3 データフロー

```
[Phase 3: test_scenario]
   test-scenario.md
         ↓ 参照
[Phase 4: implementation]
   implementation.md
         ↓ 両方参照
┌──────────────────────────────┐
│ Phase 5: test_implementation │
├──────────────────────────────┤
│ execute():                   │
│  1. test_scenario.mdを読込   │
│  2. implementation.mdを読込  │
│  3. テストコード生成プロンプト│
│  4. Claude Agent SDK実行     │
│  5. test-implementation.md生成│
└──────────────────────────────┘
         ↓
┌──────────────────────────────┐
│ review():                    │
│  1. test-implementation.md読込│
│  2. 設計書・テストシナリオ読込│
│  3. レビュープロンプト        │
│  4. PASS/FAIL判定            │
└──────────────────────────────┘
         ↓ FAIL時
┌──────────────────────────────┐
│ revise():                    │
│  1. レビューフィードバック受取│
│  2. 修正プロンプト            │
│  3. Claude Agent SDK実行     │
│  4. test-implementation.md更新│
└──────────────────────────────┘
         ↓ 成功
[Phase 6: testing]
   テストコードを実行
```

---

## 2. 実装戦略判断

### 実装戦略: **CREATE**

**判断根拠**:

1. **新規ファイル作成が主目的**:
   - `scripts/ai-workflow/phases/test_implementation.py`を新規作成（約300行）
   - 既存の`ImplementationPhase`クラス（implementation.py）をテンプレートとして活用
   - BasePhaseを継承した標準的なフェーズ実装パターンを踏襲

2. **既存ファイルへの修正は軽微**:
   - `scripts/ai-workflow/main.py`: phase_classesディクショナリに1行追加のみ
   - `scripts/ai-workflow/phases/__init__.py`: インポートとエクスポート追加のみ
   - `scripts/ai-workflow/phases/report.py`: コメント内のPhase番号更新のみ（7→8）

3. **既存機能との統合度**:
   - 既存のワークフローに新フェーズを挿入する形式
   - BasePhaseのインターフェースに完全準拠
   - 既存フェーズのロジックは一切変更しない

4. **Planning Documentとの整合性**:
   - Planning Phase（Phase 0）で既に「CREATE」戦略が決定済み
   - 設計フェーズでの判断を踏襲する

**結論**: 新規ファイル作成が中心で、既存コードへの影響が最小限のため、**CREATE戦略**が適切。

---

## 3. テスト戦略判断

### テスト戦略: **UNIT_INTEGRATION**

**判断根拠**:

1. **ユニットテストが必要な理由**:
   - TestImplementationPhaseクラスの各メソッド（execute, review, revise）の個別動作確認
   - モックを使用してClaudeクライアント、GitHubクライアントの動作を分離
   - ファイルパス解決、プロンプト生成ロジックの単体検証
   - 既存のPhaseクラス（PlanningPhase、ImplementationPhaseなど）と同じパターン

2. **統合テストが必要な理由**:
   - Phase 4（implementation）→ Phase 5（test_implementation）→ Phase 6（testing）の連携確認
   - metadata.jsonの更新が正しく行われるか
   - Git auto-commit動作が正常に機能するか
   - 実際のワークフロー全体（Phase 0〜8）での動作確認

3. **BDDテスト不要の理由**:
   - エンドユーザー向け機能ではなく、内部フレームワークの拡張
   - ユーザーストーリーは存在しない（開発者向けツール）
   - 既存のPhasesにもBDDテストは存在しない

4. **Planning Documentとの整合性**:
   - Planning Phase（Phase 0）で既に「UNIT_INTEGRATION」戦略が決定済み
   - 設計フェーズでの判断を踏襲する

**結論**: クラスメソッドの個別検証（UNIT）と全体ワークフローの検証（INTEGRATION）の両方が必要なため、**UNIT_INTEGRATION戦略**が適切。

---

## 4. テストコード戦略判断

### テストコード戦略: **CREATE_TEST**

**判断根拠**:

1. **新規テストファイル作成が必要**:
   - `tests/unit/phases/test_test_implementation.py`を新規作成（約200行）
   - 既存テストファイル（`test_planning.py`、`test_implementation.py`など）には含まれない

2. **既存テストファイルの拡張は不適切**:
   - TestImplementationPhaseは独立した新しいフェーズ
   - 既存のtest_implementation.pyとは別のテスト対象
   - テストケースが異なる（テストコード生成の検証 vs 実コード生成の検証）

3. **参考実装の活用**:
   - `tests/unit/phases/test_planning.py`と同様のテスト構造
   - 既存のモックパターンを再利用
   - BasePhaseのテストパターンを踏襲

4. **Planning Documentとの整合性**:
   - Planning Phase（Phase 0）で既に「CREATE_TEST」戦略が決定済み
   - 設計フェーズでの判断を踏襲する

**結論**: 新規Phase実装のため、既存テストファイルには含まれず、**CREATE_TEST戦略**が適切。

---

## 5. 影響範囲分析

### 5.1 既存コードへの影響

#### 軽微な修正が必要なファイル

**1. `scripts/ai-workflow/main.py` (line 159-168)**
```python
# 修正前
phase_classes = {
    'planning': PlanningPhase,
    'requirements': RequirementsPhase,
    'design': DesignPhase,
    'test_scenario': TestScenarioPhase,
    'implementation': ImplementationPhase,
    'testing': TestingPhase,
    'documentation': DocumentationPhase,
    'report': ReportPhase
}

# 修正後
phase_classes = {
    'planning': PlanningPhase,
    'requirements': RequirementsPhase,
    'design': DesignPhase,
    'test_scenario': TestScenarioPhase,
    'implementation': ImplementationPhase,
    'test_implementation': TestImplementationPhase,  # 追加
    'testing': TestingPhase,
    'documentation': DocumentationPhase,
    'report': ReportPhase
}
```

**影響**: phase選択肢に'test_implementation'が追加されるのみ。既存フェーズの動作に影響なし。

**2. `scripts/ai-workflow/main.py` (line 96)**
```python
# 修正前
@click.option('--phase', required=True,
              type=click.Choice(['planning', 'requirements', 'design', 'test_scenario',
                                'implementation', 'testing', 'documentation', 'report']))

# 修正後
@click.option('--phase', required=True,
              type=click.Choice(['planning', 'requirements', 'design', 'test_scenario',
                                'implementation', 'test_implementation', 'testing',
                                'documentation', 'report']))
```

**影響**: CLIでtest_implementationが選択可能になるのみ。既存コマンドに影響なし。

**3. `scripts/ai-workflow/main.py` (line 11-18)**
```python
# 修正前
from phases.planning import PlanningPhase
from phases.requirements import RequirementsPhase
from phases.design import DesignPhase
from phases.test_scenario import TestScenarioPhase
from phases.implementation import ImplementationPhase
from phases.testing import TestingPhase
from phases.documentation import DocumentationPhase
from phases.report import ReportPhase

# 修正後
from phases.planning import PlanningPhase
from phases.requirements import RequirementsPhase
from phases.design import DesignPhase
from phases.test_scenario import TestScenarioPhase
from phases.implementation import ImplementationPhase
from phases.test_implementation import TestImplementationPhase  # 追加
from phases.testing import TestingPhase
from phases.documentation import DocumentationPhase
from phases.report import ReportPhase
```

**影響**: インポート追加のみ。既存のインポートに影響なし。

**4. `scripts/ai-workflow/phases/__init__.py`**
```python
# 修正前
"""AI Workflow フェーズ管理パッケージ

各フェーズの実装とベースクラスを提供
"""
from .base_phase import BasePhase

__all__ = ['BasePhase']

# 修正後
"""AI Workflow フェーズ管理パッケージ

各フェーズの実装とベースクラスを提供
"""
from .base_phase import BasePhase
from .test_implementation import TestImplementationPhase  # 追加

__all__ = ['BasePhase', 'TestImplementationPhase']  # 追加
```

**影響**: エクスポート追加のみ。既存のエクスポートに影響なし。

**5. `scripts/ai-workflow/phases/report.py` (コメントのみ)**
```python
# 修正前（複数箇所）
"""Phase 7: レポートフェーズ

# 修正後（複数箇所）
"""Phase 8: レポートフェーズ
```

**影響**: コメント・ログ出力のPhase番号のみ変更。ロジックに影響なし。

#### 修正不要なファイル（既に対応済み）

- ✅ `scripts/ai-workflow/phases/base_phase.py:23-33`: PHASE_NUMBERSに'test_implementation': '05'が既に追加済み
- ✅ `scripts/ai-workflow/core/workflow_state.py:80-86`: metadata.json構造にtest_implementationが既に定義済み
- ✅ `scripts/ai-workflow/prompts/test_implementation/*.txt`: プロンプトファイルが既に作成済み

### 5.2 依存関係の変更

#### 新規依存

**なし**

既存のBasePhase、ClaudeAgentClient、GitHubClient、GitManagerを使用するため、新規依存関係は発生しない。

#### 既存依存の変更

**なし**

既存のクラス・モジュールのインターフェースは一切変更しない。

### 5.3 マイグレーション要否

#### データベーススキーマ変更

**不要**

metadata.jsonの構造は既にWorkflowState.create_new()で対応済み（workflow_state.py:80-86）。

#### 設定ファイル変更

**不要**

既存の設定ファイルに変更は不要。

#### 後方互換性

**完全互換**

- 既存の7フェーズワークフロー（planning→requirements→design→test_scenario→implementation→testing→documentation→report）は引き続き動作
- 新しい8フェーズワークフロー（test_implementationを含む）はオプトイン方式
- CLIパラメータでtest_implementationをスキップすることも可能

---

## 6. 変更・追加ファイルリスト

### 6.1 新規作成ファイル

1. **`scripts/ai-workflow/phases/test_implementation.py`**
   - 説明: TestImplementationPhaseクラス実装
   - 予想行数: 約300行
   - テンプレート: `scripts/ai-workflow/phases/implementation.py`

### 6.2 修正が必要な既存ファイル

1. **`scripts/ai-workflow/main.py`**
   - 説明: インポート追加、phase_classesディクショナリにtest_implementation追加、CLI選択肢追加
   - 修正箇所: line 11-18（インポート）, line 96（CLI選択肢）, line 159-168（phase_classes）
   - 修正行数: 約3行追加

2. **`scripts/ai-workflow/phases/__init__.py`**
   - 説明: TestImplementationPhaseのインポートとエクスポート
   - 修正箇所: 全体（インポート追加、__all__更新）
   - 修正行数: 約2行追加

3. **`scripts/ai-workflow/phases/report.py`**
   - 説明: Phase番号を7→8に更新（コメントとログのみ）
   - 修正箇所: 複数（コメント・ログ文字列）
   - 修正行数: 約5箇所

### 6.3 削除が必要なファイル

**なし**

---

## 7. 詳細設計

### 7.1 TestImplementationPhaseクラス設計

#### クラス定義

```python
"""Phase 5: テストコード実装フェーズ

Phase 3で作成されたテストシナリオとPhase 4で実装された実コードを基に、
テストコードのみを実装する。実コードの修正は行わない。
"""
import re
from pathlib import Path
from typing import Dict, Any, List
from .base_phase import BasePhase


class TestImplementationPhase(BasePhase):
    """テストコード実装フェーズ"""

    def __init__(self, *args, **kwargs):
        """初期化"""
        super().__init__(
            phase_name='test_implementation',
            *args,
            **kwargs
        )

    def execute(self) -> Dict[str, Any]:
        """
        テストコード実装フェーズを実行

        Returns:
            Dict[str, Any]: 実行結果
                - success: bool
                - output: str - test-implementation.mdのパス
                - error: Optional[str]
        """
        # 実装詳細は後述

    def review(self) -> Dict[str, Any]:
        """
        テストコード実装をレビュー

        Returns:
            Dict[str, Any]: レビュー結果
                - result: str - PASS/PASS_WITH_SUGGESTIONS/FAIL
                - feedback: str
                - suggestions: List[str]
        """
        # 実装詳細は後述

    def revise(self, review_feedback: str) -> Dict[str, Any]:
        """
        レビュー結果を元にテストコードを修正

        Args:
            review_feedback: レビュー結果のフィードバック

        Returns:
            Dict[str, Any]: 修正結果
                - success: bool
                - output: str - test-implementation.mdのパス
                - error: Optional[str]
        """
        # 実装詳細は後述
```

#### メソッド詳細設計

##### 7.1.1 execute()メソッド

**目的**: テストシナリオと実装を基に、テストコードを生成する

**処理フロー**:
```python
def execute(self) -> Dict[str, Any]:
    try:
        # 1. Issue情報を取得
        issue_number = int(self.metadata.data['issue_number'])

        # 2. 要件定義書、設計書、テストシナリオ、実装ログを読み込み
        requirements_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '01_requirements' / 'output' / 'requirements.md'
        design_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '02_design' / 'output' / 'design.md'
        test_scenario_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '03_test_scenario' / 'output' / 'test-scenario.md'
        implementation_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '04_implementation' / 'output' / 'implementation.md'

        # 3. ファイル存在確認
        for file in [requirements_file, design_file, test_scenario_file, implementation_file]:
            if not file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': f'必要なファイルが見つかりません: {file}'
                }

        # 4. テスト戦略を取得（Phase 2で決定済み）
        test_strategy = self.metadata.data['design_decisions'].get('test_strategy')
        test_code_strategy = self.metadata.data['design_decisions'].get('test_code_strategy')

        if not test_strategy or not test_code_strategy:
            return {
                'success': False,
                'output': None,
                'error': 'テスト戦略が設計フェーズで決定されていません。Phase 2を先に実行してください。'
            }

        # 5. Planning Phase成果物のパス取得
        planning_path_str = self._get_planning_document_path(issue_number)

        # 6. 実行プロンプトを読み込み
        execute_prompt_template = self.load_prompt('execute')

        # 7. working_dirからの相対パスを使用
        rel_path_requirements = requirements_file.relative_to(self.claude.working_dir)
        rel_path_design = design_file.relative_to(self.claude.working_dir)
        rel_path_test_scenario = test_scenario_file.relative_to(self.claude.working_dir)
        rel_path_implementation = implementation_file.relative_to(self.claude.working_dir)

        # 8. プロンプトに情報を埋め込み
        execute_prompt = execute_prompt_template.replace(
            '{planning_document_path}',
            planning_path_str
        ).replace(
            '{requirements_document_path}',
            f'@{rel_path_requirements}'
        ).replace(
            '{design_document_path}',
            f'@{rel_path_design}'
        ).replace(
            '{test_scenario_document_path}',
            f'@{rel_path_test_scenario}'
        ).replace(
            '{implementation_document_path}',
            f'@{rel_path_implementation}'
        ).replace(
            '{test_strategy}',
            test_strategy
        ).replace(
            '{test_code_strategy}',
            test_code_strategy
        ).replace(
            '{issue_number}',
            str(issue_number)
        )

        # 9. Claude Agent SDKでタスクを実行
        # テスト実装フェーズは時間がかかる可能性があるため、max_turnsを多めに
        messages = self.execute_with_claude(
            prompt=execute_prompt,
            max_turns=50,
            log_prefix='execute'
        )

        # 10. test-implementation.mdのパスを取得
        output_file = self.output_dir / 'test-implementation.md'

        if not output_file.exists():
            return {
                'success': False,
                'output': None,
                'error': f'test-implementation.mdが生成されませんでした: {output_file}'
            }

        # 11. GitHub Issueに成果物を投稿
        try:
            output_content = output_file.read_text(encoding='utf-8')
            self.post_output(
                output_content=output_content,
                title="テストコード実装ログ"
            )
        except Exception as e:
            print(f"[WARNING] 成果物のGitHub投稿に失敗しました: {e}")

        return {
            'success': True,
            'output': str(output_file),
            'error': None
        }

    except Exception as e:
        # ステータス更新: 失敗
        self.metadata.update_phase_status('test_implementation', 'failed')

        return {
            'success': False,
            'output': None,
            'error': str(e)
        }
```

**エラーハンドリング**:
- ファイル存在確認（requirements.md、design.md、test-scenario.md、implementation.md）
- テスト戦略未定義チェック
- Claude Agent SDK実行エラー
- 出力ファイル生成確認

##### 7.1.2 review()メソッド

**目的**: 生成されたテストコードが要件・設計・テストシナリオに準拠しているかレビューする

**処理フロー**:
```python
def review(self) -> Dict[str, Any]:
    try:
        # 1. test-implementation.mdを読み込み
        test_implementation_file = self.output_dir / 'test-implementation.md'

        if not test_implementation_file.exists():
            return {
                'result': 'FAIL',
                'feedback': 'test-implementation.mdが存在しません。',
                'suggestions': ['execute()を実行してtest-implementation.mdを生成してください。']
            }

        # 2. 設計書、テストシナリオ、実装ログのパス
        issue_number = int(self.metadata.data['issue_number'])
        design_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '02_design' / 'output' / 'design.md'
        test_scenario_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '03_test_scenario' / 'output' / 'test-scenario.md'
        implementation_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '04_implementation' / 'output' / 'implementation.md'

        # 3. テスト戦略を取得
        test_strategy = self.metadata.data['design_decisions'].get('test_strategy', 'UNKNOWN')
        test_code_strategy = self.metadata.data['design_decisions'].get('test_code_strategy', 'UNKNOWN')

        # 4. レビュープロンプトを読み込み
        review_prompt_template = self.load_prompt('review')

        # 5. working_dirからの相対パスを使用
        rel_path_test_implementation = test_implementation_file.relative_to(self.claude.working_dir)
        rel_path_design = design_file.relative_to(self.claude.working_dir)
        rel_path_test_scenario = test_scenario_file.relative_to(self.claude.working_dir)
        rel_path_implementation = implementation_file.relative_to(self.claude.working_dir)

        # 6. プロンプトに情報を埋め込み
        review_prompt = review_prompt_template.replace(
            '{test_implementation_document_path}',
            f'@{rel_path_test_implementation}'
        ).replace(
            '{design_document_path}',
            f'@{rel_path_design}'
        ).replace(
            '{test_scenario_document_path}',
            f'@{rel_path_test_scenario}'
        ).replace(
            '{implementation_document_path}',
            f'@{rel_path_implementation}'
        ).replace(
            '{test_strategy}',
            test_strategy
        ).replace(
            '{test_code_strategy}',
            test_code_strategy
        )

        # 7. Claude Agent SDKでレビューを実行
        messages = self.execute_with_claude(
            prompt=review_prompt,
            max_turns=30,
            log_prefix='review'
        )

        # 8. レビュー結果をパース
        review_result = self._parse_review_result(messages)

        # 9. レビュー結果をファイルに保存
        review_file = self.review_dir / 'result.md'
        review_file.write_text(review_result['feedback'], encoding='utf-8')
        print(f"[INFO] レビュー結果を保存: {review_file}")

        return review_result

    except Exception as e:
        return {
            'result': 'FAIL',
            'feedback': f'レビュー中にエラーが発生しました: {str(e)}',
            'suggestions': []
        }
```

**レビュー観点**:
- テストシナリオに基づいたテストケースが実装されているか
- 実コードが変更されていないか（Phase 5の責務違反チェック）
- テストコードの品質（カバレッジ、エッジケース、命名規則）
- 設計書のテスト戦略に準拠しているか

##### 7.1.3 revise()メソッド

**目的**: レビューフィードバックに基づいてテストコードを修正する

**処理フロー**:
```python
def revise(self, review_feedback: str) -> Dict[str, Any]:
    try:
        # 1. 元のテスト実装ログを読み込み
        test_implementation_file = self.output_dir / 'test-implementation.md'

        if not test_implementation_file.exists():
            return {
                'success': False,
                'output': None,
                'error': 'test-implementation.mdが存在しません。'
            }

        # 2. 設計書、テストシナリオ、実装ログのパス
        issue_number = int(self.metadata.data['issue_number'])
        design_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '02_design' / 'output' / 'design.md'
        test_scenario_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '03_test_scenario' / 'output' / 'test-scenario.md'
        implementation_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '04_implementation' / 'output' / 'implementation.md'

        # 3. テスト戦略を取得
        test_strategy = self.metadata.data['design_decisions'].get('test_strategy', 'UNKNOWN')
        test_code_strategy = self.metadata.data['design_decisions'].get('test_code_strategy', 'UNKNOWN')

        # 4. 修正プロンプトを読み込み
        revise_prompt_template = self.load_prompt('revise')

        # 5. working_dirからの相対パスを使用
        rel_path_test_implementation = test_implementation_file.relative_to(self.claude.working_dir)
        rel_path_design = design_file.relative_to(self.claude.working_dir)
        rel_path_test_scenario = test_scenario_file.relative_to(self.claude.working_dir)
        rel_path_implementation = implementation_file.relative_to(self.claude.working_dir)

        # 6. プロンプトに情報を埋め込み
        revise_prompt = revise_prompt_template.replace(
            '{test_implementation_document_path}',
            f'@{rel_path_test_implementation}'
        ).replace(
            '{review_feedback}',
            review_feedback
        ).replace(
            '{design_document_path}',
            f'@{rel_path_design}'
        ).replace(
            '{test_scenario_document_path}',
            f'@{rel_path_test_scenario}'
        ).replace(
            '{implementation_document_path}',
            f'@{rel_path_implementation}'
        ).replace(
            '{test_strategy}',
            test_strategy
        ).replace(
            '{test_code_strategy}',
            test_code_strategy
        ).replace(
            '{issue_number}',
            str(issue_number)
        )

        # 7. Claude Agent SDKでタスクを実行
        messages = self.execute_with_claude(
            prompt=revise_prompt,
            max_turns=50,
            log_prefix='revise'
        )

        # 8. test-implementation.mdのパスを取得
        output_file = self.output_dir / 'test-implementation.md'

        if not output_file.exists():
            return {
                'success': False,
                'output': None,
                'error': '修正されたtest-implementation.mdが生成されませんでした。'
            }

        return {
            'success': True,
            'output': str(output_file),
            'error': None
        }

    except Exception as e:
        return {
            'success': False,
            'output': None,
            'error': str(e)
        }
```

**修正方針**:
- レビューフィードバックに基づいてテストコードのみを修正
- 実コードは一切変更しない
- テストシナリオとの整合性を保つ

### 7.2 データ構造設計

#### 7.2.1 metadata.json構造（test_implementation部分）

```json
{
  "phases": {
    "test_implementation": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    }
  }
}
```

**既に対応済み**: `workflow_state.py:80-86`で定義済み

#### 7.2.2 成果物ファイル構造

```
.ai-workflow/issue-324/05_test_implementation/
├── output/
│   └── test-implementation.md          # テストコード実装ログ
├── execute/
│   ├── prompt_1.txt                    # 実行プロンプト
│   ├── agent_log_1.md                  # 整形済みログ
│   └── agent_log_raw_1.txt             # 生ログ
├── review/
│   ├── prompt_1.txt                    # レビュープロンプト
│   ├── agent_log_1.md                  # 整形済みログ
│   ├── agent_log_raw_1.txt             # 生ログ
│   └── result.md                       # レビュー結果
└── revise/
    ├── prompt_1.txt                    # 修正プロンプト
    ├── agent_log_1.md                  # 整形済みログ
    └── agent_log_raw_1.txt             # 生ログ
```

### 7.3 インターフェース設計

#### 7.3.1 BasePhaseインターフェース

TestImplementationPhaseはBasePhaseのインターフェースに完全準拠：

```python
class BasePhase(ABC):
    @abstractmethod
    def execute(self) -> Dict[str, Any]:
        """
        Returns:
            Dict[str, Any]: 実行結果
                - success: bool - 成功/失敗
                - output: Any - 実行結果の出力
                - error: Optional[str] - エラーメッセージ
        """
        pass

    @abstractmethod
    def review(self) -> Dict[str, Any]:
        """
        Returns:
            Dict[str, Any]: レビュー結果
                - result: str - PASS/PASS_WITH_SUGGESTIONS/FAIL
                - feedback: str - フィードバック
                - suggestions: List[str] - 改善提案一覧
        """
        pass
```

#### 7.3.2 プロンプトファイルインターフェース

**既に作成済み**:
- `prompts/test_implementation/execute.txt`: テストコード実装プロンプト
- `prompts/test_implementation/review.txt`: テストコードレビュープロンプト
- `prompts/test_implementation/revise.txt`: テストコード修正プロンプト

**プレースホルダー**（execute.txtの例）:
- `{planning_document_path}`: Planning Document参照（オプション）
- `{requirements_document_path}`: 要件定義書参照
- `{design_document_path}`: 設計書参照
- `{test_scenario_document_path}`: テストシナリオ参照
- `{implementation_document_path}`: 実装ログ参照
- `{test_strategy}`: テスト戦略（UNIT_INTEGRATION等）
- `{test_code_strategy}`: テストコード戦略（CREATE_TEST等）
- `{issue_number}`: Issue番号

---

## 8. セキュリティ考慮事項

### 8.1 認証・認可

**該当なし**

TestImplementationPhaseは既存のClaudeAgentClient、GitHubClientを使用するため、新たな認証・認可機構は不要。

### 8.2 データ保護

**機密情報の取り扱い**:
- テストコードに機密情報（APIキー、パスワード等）を含めないようプロンプトで指示
- レビューフェーズで機密情報の有無をチェック

**ログ保護**:
- 実行ログ（agent_log_*.md）にはClaudeのレスポンスが含まれる
- Gitリポジトリにコミットされるため、機密情報を含めないよう注意

### 8.3 セキュリティリスクと対策

| リスク | 影響度 | 確率 | 対策 |
|--------|--------|------|------|
| テストコードに機密情報が含まれる | 高 | 低 | プロンプトで明示的に禁止、レビューでチェック |
| 実コードの意図しない変更 | 中 | 低 | プロンプトで禁止、レビューで変更検出 |
| 不正なテストコードの生成 | 中 | 低 | レビューフェーズでコード品質チェック |

---

## 9. 非機能要件への対応

### 9.1 パフォーマンス（NFR-002）

**目標**:
- Phase 5の実行時間: 約2時間以内（Phase 5見積もりより）
- オーバーヘッド: Phase追加による追加時間は5分以内

**対策**:
- Claude Agent SDKの`max_turns=50`で十分な試行回数を確保
- プロンプトを簡潔にしてトークン数を削減
- ファイルI/O最適化（Path.read_text()の効率的な使用）

**計測方法**:
- metadata.jsonのstart_time、end_timeで実行時間を記録
- BasePhase.run()でフェーズ全体の実行時間を計測

### 9.2 スケーラビリティ

**考慮点**:
- テストファイル数が増加してもフェーズ実行時間が線形に増加しない設計
- Claude Agent SDKのコンテキスト上限（200,000トークン）を考慮

**対策**:
- テストシナリオを参照する際、必要な部分のみを抽出
- 実装ログも同様に必要な部分のみを参照

### 9.3 保守性

**設計方針**:
- ImplementationPhaseと同様の構造を踏襲（一貫性）
- コメントを日本語で記述（CLAUDE.mdより）
- エラーメッセージを明確にする

**コーディング規約**:
- PEP 8準拠
- 型ヒント使用（Python 3.8+）
- docstring記述（Googleスタイル）

---

## 10. 実装の順序

以下の順序で実装することを推奨します：

### Phase 1: 準備作業（30分）
1. `scripts/ai-workflow/phases/test_implementation.py`を新規作成
2. `scripts/ai-workflow/phases/implementation.py`をテンプレートとしてコピー
3. クラス名を`TestImplementationPhase`に変更
4. `phase_name='test_implementation'`に変更

### Phase 2: execute()メソッド実装（1時間）
1. Issue情報取得ロジック実装
2. ファイル存在確認ロジック実装
3. テスト戦略取得ロジック実装
4. プロンプト生成ロジック実装
5. Claude Agent SDK実行ロジック実装
6. 成果物保存・投稿ロジック実装

### Phase 3: review()メソッド実装（30分）
1. test-implementation.md読み込みロジック実装
2. レビュープロンプト生成ロジック実装
3. Claude Agent SDK実行ロジック実装
4. レビュー結果パースロジック実装

### Phase 4: revise()メソッド実装（30分）
1. レビューフィードバック処理ロジック実装
2. 修正プロンプト生成ロジック実装
3. Claude Agent SDK実行ロジック実装
4. 修正結果保存ロジック実装

### Phase 5: main.py修正（10分）
1. TestImplementationPhaseのインポート追加
2. phase_classesディクショナリに追加
3. CLI選択肢に追加

### Phase 6: phases/__init__.py修正（5分）
1. TestImplementationPhaseのインポート追加
2. __all__に追加

### Phase 7: report.py修正（5分）
1. コメントのPhase番号を7→8に更新
2. ログ出力のPhase番号を7→8に更新

### Phase 8: 統合テスト（1時間）
1. Phase 0〜8の全フェーズを実行
2. metadata.jsonの更新確認
3. Git auto-commit動作確認

---

## 11. テスト設計概要

### 11.1 ユニットテスト設計

**テストファイル**: `tests/unit/phases/test_test_implementation.py`

**テストケース**:
1. `test_init()`: 初期化テスト
2. `test_execute_success()`: execute()正常系テスト
3. `test_execute_missing_files()`: execute()ファイル不在エラーテスト
4. `test_execute_missing_test_strategy()`: execute()テスト戦略未定義エラーテスト
5. `test_review_success_pass()`: review()正常系（PASS）テスト
6. `test_review_success_fail()`: review()正常系（FAIL）テスト
7. `test_review_missing_output()`: review()出力ファイル不在エラーテスト
8. `test_revise_success()`: revise()正常系テスト
9. `test_revise_missing_output()`: revise()出力ファイル不在エラーテスト

**モック対象**:
- ClaudeAgentClient.execute_task_sync()
- GitHubClient.post_comment()
- MetadataManager.update_phase_status()
- Path.exists()
- Path.read_text()

### 11.2 統合テスト設計

**テストシナリオ**: Phase 4→5→6の連携確認

**検証項目**:
1. Phase 4完了後、Phase 5が実行可能
2. Phase 5でtest-implementation.mdが生成される
3. Phase 5でmetadata.jsonが更新される
4. Phase 5でGit commitが実行される
5. Phase 6がPhase 5の成果物を参照できる

---

## 12. 品質ゲート確認

設計書が以下の品質ゲートを満たしているか確認します：

- [x] **実装戦略の判断根拠が明記されている**: セクション2で「CREATE」戦略の判断根拠を4項目記載
- [x] **テスト戦略の判断根拠が明記されている**: セクション3で「UNIT_INTEGRATION」戦略の判断根拠を4項目記載
- [x] **テストコード戦略の判断根拠が明記されている**: セクション4で「CREATE_TEST」戦略の判断根拠を4項目記載
- [x] **既存コードへの影響範囲が分析されている**: セクション5で軽微な修正箇所を5ファイル特定、修正不要ファイルを3項目記載
- [x] **変更が必要なファイルがリストアップされている**: セクション6で新規作成1ファイル、修正3ファイル、削除0ファイルをリストアップ
- [x] **設計が実装可能である**: セクション7で具体的なクラス設計、メソッド実装フロー、データ構造を記載

**結論**: 全ての品質ゲートを満たしています。

---

## 13. 付録

### 13.1 用語集

| 用語 | 説明 |
|------|------|
| TestImplementationPhase | Phase 5のテストコード実装を担当するクラス |
| BasePhase | 全フェーズの基底クラス。execute()、review()、revise()を定義 |
| test-implementation.md | Phase 5の成果物（テストコード実装ログ） |
| test_strategy | テスト戦略（UNIT_INTEGRATION等） |
| test_code_strategy | テストコード戦略（CREATE_TEST等） |
| metadata.json | ワークフローの状態管理ファイル |
| PHASE_NUMBERS | BasePhaseのフェーズ番号マッピング辞書 |

### 13.2 参考ドキュメント

- **Planning Document**: `.ai-workflow/issue-324/00_planning/output/planning.md`
- **Requirements Document**: `.ai-workflow/issue-324/01_requirements/output/requirements.md`
- **CLAUDE.md**: プロジェクトの全体方針とコーディングガイドライン
- **ARCHITECTURE.md**: アーキテクチャ設計思想
- **README.md**: プロジェクト概要と使用方法

### 13.3 実装参考ファイル

- **BasePhase**: `scripts/ai-workflow/phases/base_phase.py`
- **ImplementationPhase**: `scripts/ai-workflow/phases/implementation.py`（テンプレート）
- **TestingPhase**: `scripts/ai-workflow/phases/testing.py`（類似フェーズ）
- **WorkflowState**: `scripts/ai-workflow/core/workflow_state.py`

---

**作成日**: 2025-10-11
**Issue番号**: #324
**Phase**: Phase 2 (design)
**バージョン**: 1.0
