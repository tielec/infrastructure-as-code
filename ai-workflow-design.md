# AI駆動開発自動化ワークフロー 詳細設計書

**文書バージョン**: 1.0.0
**作成日**: 2025-10-07
**前フェーズ**: 要件定義書 v1.2.0

---

## 1. 実装戦略判断

### 1.1 実装戦略: CREATE（新規作成）

**判断根拠**:
- 既存の `scripts/` ディレクトリにはPythonスクリプトが存在しない（シェルスクリプトのみ）
- このAI Workflowは全く新しい機能で、既存コードとの依存関係がない
- `jenkins/jobs/pipeline/docs-generator/` に類似のPython実装パターンが存在し、参考にできる
- 独立した機能として新規作成することで、既存システムへの影響をゼロに抑えられる

### 1.2 テスト戦略: INTEGRATION_BDD（IntegrationテストとBDDテスト）

**判断根拠**:
- **BDDテスト必要性（最優先）**:
  - エンドユーザー（開発者）の視点で、ワークフロー全体の動作を検証
  - 「GitHub IssueからPR作成まで」というユーザーストーリーをGherkin形式で記述
  - 非技術者（プロダクトマネージャー等）でも理解できるシナリオ
  - ビジネス要件（6フェーズのワークフロー）との対応が明確
  - ユーザーにとっての価値（自動化による開発効率化）を検証

- **Integrationテスト必要性**:
  - BDDシナリオを技術的に実装するための統合テスト
  - 6フェーズの連携動作を検証（Phase 1 → Phase 2 → ... → Phase 6）
  - レビュー不合格時のリトライフローの検証
  - Git操作とmetadata.json更新の整合性検証
  - Claude APIとの実際の通信テスト（モック使用）

- **Unitテストは実装時に必要に応じて追加**:
  - Phase 4（実装）で、複雑なロジックが発生した場合に追加
  - 当初はBDD + Integrationテストで十分

### 1.3 テストコード戦略: CREATE_TEST（新規作成）

**判断根拠**:
- 既存のテストコードが存在しない（新規プロジェクト）
- 全てのテストケースを新規に作成する必要がある
- ただし、既存の `jenkins/jobs/pipeline/docs-generator/` のテストパターンは参考にする

---

## 2. アーキテクチャ設計

### 2.1 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│                     GitHub Issue                        │
│                  (開発者が作成)                          │
└────────────────────┬────────────────────────────────────┘
                     │ Issue URL
                     ↓
┌─────────────────────────────────────────────────────────┐
│                   Jenkins Job                           │
│            (AI-Workflow/orchestrator)                    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │         Jenkinsfile (Pipeline)                 │    │
│  │  - Stage管理（可視化）                         │    │
│  │  - パラメータ受取                              │    │
│  │  - Pythonスクリプト呼び出し                    │    │
│  └──────────────┬─────────────────────────────────┘    │
└─────────────────┼──────────────────────────────────────┘
                  │
                  ↓ Python実行
┌─────────────────────────────────────────────────────────┐
│             scripts/ai-workflow/                        │
│              (Pythonスクリプト)                          │
│                                                          │
│  ┌─────────────────────────────────────────────┐       │
│  │ main.py (CLI)                                │       │
│  │  - init: ワークフロー初期化                  │       │
│  │  - execute: フェーズ実行                     │       │
│  │  - review: レビュー実行                      │       │
│  │  - status: 状態確認                          │       │
│  └──────────┬──────────────────────────────────┘       │
│             │                                            │
│  ┌──────────┴──────────────────────────────────┐       │
│  │ core/                                        │       │
│  │  - claude_client.py: Claude API通信         │       │
│  │  - git_operations.py: Git操作               │       │
│  │  - workflow_state.py: 状態管理              │       │
│  │  - context_manager.py: コンテキスト管理     │       │
│  └──────────┬──────────────────────────────────┘       │
│             │                                            │
│  ┌──────────┴──────────────────────────────────┐       │
│  │ phases/                                      │       │
│  │  - requirements.py: Phase 1実行             │       │
│  │  - design.py: Phase 2実行                   │       │
│  │  - test_scenario.py: Phase 3実行            │       │
│  │  - implementation.py: Phase 4実行           │       │
│  │  - testing.py: Phase 5実行                  │       │
│  │  - documentation.py: Phase 6実行            │       │
│  └──────────┬──────────────────────────────────┘       │
│             │                                            │
│  ┌──────────┴──────────────────────────────────┐       │
│  │ reviewers/                                   │       │
│  │  - critical_thinking.py: レビューエンジン   │       │
│  │    - ブロッカー判定                          │       │
│  │    - クオリティゲートチェック                │       │
│  │    - PASS/PASS_WITH_SUGGESTIONS/FAIL判定    │       │
│  └──────────────────────────────────────────────┘       │
└───────────┬─────────────────────────────────────────────┘
            │
            ↓ API呼び出し
┌─────────────────────────────────────────────────────────┐
│                  Claude API (Sonnet 4.5)                │
│  - テキスト生成・分析                                    │
│  - Function Calling（ツール実行）                        │
└───────────┬─────────────────────────────────────────────┘
            │
            ↓ 成果物保存
┌─────────────────────────────────────────────────────────┐
│            Git Repository (Feature Branch)              │
│  .ai-workflow/issue-{番号}/                             │
│    ├─ metadata.json                                     │
│    ├─ 01-requirements.md                                │
│    ├─ 02-design.md                                      │
│    └─ ...                                               │
└─────────────────────────────────────────────────────────┘
```

### 2.2 レビュワー指摘への回答

#### 2.2.1 Phase 4実装方法の技術選定（必須）

**選択: Option A - Claude API + Function Calling + Pythonツール実装**

```python
# Phase 4での実装方法概要
class ImplementationPhase:
    def execute(self, context):
        # 1. 設計書からファイルリストを取得
        files_to_change = context.design_decisions['files_to_change']

        # 2. Claudeに実装依頼（Function Callingで）
        tools = [
            {"name": "read_file", "implementation": self.read_file},
            {"name": "write_file", "implementation": self.write_file},
            {"name": "edit_file", "implementation": self.edit_file},
            {"name": "run_tests", "implementation": self.run_tests}
        ]

        # 3. ClaudeがFunction Callingでツールを呼び出す
        response = self.claude_client.chat_with_tools(
            messages=self.build_implementation_prompt(context),
            tools=tools
        )

        # 4. Claudeの指示に従ってPython側でファイル操作
        for tool_call in response.tool_calls:
            result = self.execute_tool(tool_call)
            # 結果をClaudeにフィードバック
```

**技術詳細**:
- **Claude API Messages API** を使用
- **Function Calling機能**で以下のツールを提供:
  - `read_file(path)`: ファイル読み込み
  - `write_file(path, content)`: ファイル書き込み
  - `edit_file(path, old_content, new_content)`: ファイル編集
  - `list_files(pattern)`: ファイル検索
  - `run_command(command)`: コマンド実行（テスト等）
  - `search_code(pattern)`: コード検索

**メリット**:
- Claude APIの正式機能を使用（安定）
- Python側でファイル操作を完全制御（セキュリティ）
- エラーハンドリングが容易
- ローカルでのデバッグが可能
- Jenkins以外（GitHub Actions等）への移植も容易

#### 2.2.2 Claude APIコスト管理戦略（推奨）

**実装する対策**:

1. **トークン使用量の追跡**:
```python
class ClaudeClient:
    def __init__(self):
        self.token_usage = {
            'input_tokens': 0,
            'output_tokens': 0,
            'total_cost': 0.0
        }

    def track_usage(self, response):
        self.token_usage['input_tokens'] += response.usage.input_tokens
        self.token_usage['output_tokens'] += response.usage.output_tokens
        # Sonnet 4.5の料金: $3/1M input, $15/1M output
        cost = (response.usage.input_tokens * 3 / 1_000_000 +
                response.usage.output_tokens * 15 / 1_000_000)
        self.token_usage['total_cost'] += cost
```

2. **予算制限の設定**:
```yaml
# config.yaml
cost_limits:
  per_phase_max_tokens: 100000  # フェーズあたり10万トークン
  per_workflow_max_cost: 5.0    # ワークフローあたり$5上限
  warning_threshold: 0.8        # 80%で警告
```

3. **コスト超過時の動作**:
- 警告: ログ出力 + 継続
- 上限達成: 処理停止 + 人間エスカレーション

4. **コンテキスト最適化**:
- 大規模ファイルは要約してから送信
- 前フェーズの成果物は必要部分のみ抽出
- プロンプトの簡潔化

#### 2.2.3 既存コードベース分析手法（推奨）

**Phase 2での分析戦略**:

```python
class DesignPhase:
    def analyze_codebase(self, issue_content):
        """既存コードベースを段階的に分析"""

        # Step 1: Issueから関連ファイルパターンを推測
        keywords = self.extract_keywords(issue_content)

        # Step 2: ファイル検索（Glob）
        relevant_files = self.search_files(keywords)

        # Step 3: トークン制限を考慮して優先度付け
        prioritized_files = self.prioritize_files(relevant_files)

        # Step 4: 上位ファイルのみClaudeに送信（最大20ファイル or 50k tokens）
        analysis_context = self.build_analysis_context(prioritized_files)

        # Step 5: Claudeに分析依頼
        return self.claude_client.analyze_codebase(analysis_context)
```

**具体的手法**:
1. **キーワード抽出**: Issueタイトル・本文から技術用語抽出
2. **ファイル検索**: Glob/Grepで関連ファイル特定
3. **優先度付け**:
   - 変更頻度が高いファイル
   - Issueのキーワードが多く含まれるファイル
   - インポート関係が深いファイル
4. **トークン制限**: 最大50k tokens（Sonnet 4.5の入力制限200kの1/4）
5. **要約送信**: ファイル全体ではなく、関数シグネチャ+docstring程度

#### 2.2.4 Phase 5テスト失敗時のフロー（推奨）

**選択: Option A（Phase 4に戻る）**

```
Phase 5: Testing
  ├─ テスト実行
  ├─ 結果分析
  │
  ├─ 成功 → Phase 6へ
  │
  └─ 失敗
      ├─ Phase 5のリトライカウント+1
      ├─ Phase 4に戻る（実装修正）
      │   └─ Phase 4のリトライカウント+1
      └─ Phase 4でリトライ上限（3回）到達
          └─ 人間エスカレーション
```

**ルール**:
- Phase 5でテスト失敗 → Phase 4に戻って修正
- Phase 4 + Phase 5のループは最大3回
- 3回ループしても失敗 → エスカレーション
- metadata.jsonに `test_failure_count` を記録

---

## 3. システムコンポーネント設計

### 3.1 コアモジュール

#### 3.1.1 claude_client.py

```python
"""Claude API クライアント"""
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from typing import List, Dict, Any, Optional

class ClaudeClient:
    """Claude API通信クライアント"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.token_usage = {'input': 0, 'output': 0, 'cost': 0.0}

    def chat(self, messages: List[Dict[str, str]],
             max_tokens: int = 4096,
             temperature: float = 1.0) -> str:
        """通常のチャット（テキスト生成）"""
        pass

    def chat_with_tools(self, messages: List[Dict[str, str]],
                       tools: List[Dict[str, Any]],
                       max_tokens: int = 4096) -> Any:
        """Function Calling付きチャット"""
        pass

    def track_cost(self, response: Any) -> None:
        """コスト追跡"""
        pass
```

#### 3.1.2 git_operations.py

```python
"""Git操作ヘルパー"""
import git
from pathlib import Path
from typing import Optional

class GitOperations:
    """Git操作を管理"""

    def __init__(self, repo_path: str):
        self.repo = git.Repo(repo_path)

    def create_feature_branch(self, issue_number: str, title: str) -> str:
        """フィーチャーブランチ作成"""
        pass

    def commit(self, message: str, files: List[str]) -> None:
        """変更をコミット"""
        pass

    def create_workflow_structure(self, issue_number: str) -> Path:
        """.ai-workflow/issue-{番号}/ ディレクトリ作成"""
        pass
```

#### 3.1.3 workflow_state.py

```python
"""ワークフロー状態管理"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum

class PhaseStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class WorkflowState:
    """metadata.jsonの読み書き"""

    def __init__(self, metadata_path: Path):
        self.metadata_path = metadata_path
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        """metadata.json読み込み"""
        pass

    def save(self) -> None:
        """metadata.json保存"""
        pass

    def update_phase_status(self, phase: str, status: PhaseStatus) -> None:
        """フェーズ状態更新"""
        pass

    def set_design_decision(self, key: str, value: str) -> None:
        """設計判断を記録"""
        pass

    def increment_retry_count(self, phase: str) -> int:
        """リトライカウント増加"""
        pass
```

#### 3.1.4 context_manager.py

```python
"""コンテキスト管理（前フェーズからの情報引き継ぎ）"""
from pathlib import Path
from typing import Dict, Any, List

class ContextManager:
    """フェーズ間のコンテキスト管理"""

    def __init__(self, workflow_dir: Path, state: WorkflowState):
        self.workflow_dir = workflow_dir
        self.state = state

    def get_context_for_phase(self, phase: str) -> Dict[str, Any]:
        """指定フェーズに必要なコンテキストを構築"""
        pass

    def load_previous_artifacts(self, phases: List[str]) -> Dict[str, str]:
        """前フェーズの成果物を読み込み"""
        pass

    def get_review_feedback(self, phase: str, retry: int) -> Optional[str]:
        """レビューフィードバックを取得"""
        pass
```

### 3.2 フェーズモジュール

#### 3.2.1 base_phase.py

```python
"""フェーズ基底クラス"""
from abc import ABC, abstractmethod
from typing import Dict, Any

class BasePhase(ABC):
    """全フェーズの基底クラス"""

    def __init__(self, claude_client: ClaudeClient,
                 context_manager: ContextManager,
                 workflow_state: WorkflowState):
        self.claude = claude_client
        self.context = context_manager
        self.state = workflow_state

    @abstractmethod
    def execute(self, retry_count: int = 0) -> Dict[str, Any]:
        """フェーズ実行（サブクラスで実装）"""
        pass

    def save_artifact(self, filename: str, content: str) -> None:
        """成果物を保存"""
        pass

    def load_prompt_template(self, template_name: str) -> str:
        """プロンプトテンプレート読み込み"""
        pass
```

#### 3.2.2 requirements.py (Phase 1)

```python
"""Phase 1: 要件定義"""
from .base_phase import BasePhase

class RequirementsPhase(BasePhase):
    """要件定義フェーズ"""

    def execute(self, retry_count: int = 0) -> Dict[str, Any]:
        # 1. Issueコンテンツ取得
        issue_content = self.context.get_issue_content()

        # 2. プロンプト構築
        prompt = self.build_prompt(issue_content, retry_count)

        # 3. Claude API呼び出し
        requirements = self.claude.chat(prompt)

        # 4. 成果物保存
        self.save_artifact('01-requirements.md', requirements)

        return {'status': 'completed', 'artifact': requirements}
```

#### 3.2.3 design.py (Phase 2)

```python
"""Phase 2: 詳細設計"""
from .base_phase import BasePhase

class DesignPhase(BasePhase):
    """詳細設計フェーズ（戦略判断を含む）"""

    def execute(self, retry_count: int = 0) -> Dict[str, Any]:
        # 1. 要件定義取得
        requirements = self.context.load_previous_artifacts(['requirements'])

        # 2. 既存コードベース分析
        codebase_analysis = self.analyze_codebase()

        # 3. 設計書作成 + 戦略判断
        design_doc = self.generate_design(requirements, codebase_analysis)

        # 4. 戦略判断を抽出してmetadata.jsonに保存
        decisions = self.extract_decisions(design_doc)
        for key, value in decisions.items():
            self.state.set_design_decision(key, value)

        # 5. 成果物保存
        self.save_artifact('02-design.md', design_doc)

        return {'status': 'completed', 'decisions': decisions}

    def analyze_codebase(self) -> str:
        """既存コードベース分析（トークン制限考慮）"""
        pass
```

#### 3.2.4 implementation.py (Phase 4)

```python
"""Phase 4: 実装"""
from .base_phase import BasePhase

class ImplementationPhase(BasePhase):
    """実装フェーズ（Function Calling使用）"""

    def execute(self, retry_count: int = 0) -> Dict[str, Any]:
        # 1. 設計書とテストシナリオ取得
        context = self.context.get_context_for_phase('implementation')

        # 2. 実装戦略に基づいて動作変更
        strategy = self.state.data['design_decisions']['implementation_strategy']

        # 3. ツール定義
        tools = self.define_tools()

        # 4. Claude API呼び出し（Function Calling）
        implementation_log = self.execute_with_tools(context, tools)

        # 5. 成果物保存
        self.save_artifact('04-implementation.md', implementation_log)

        return {'status': 'completed', 'files_changed': self.files_changed}

    def define_tools(self) -> List[Dict]:
        """実装用ツール定義"""
        return [
            {
                "name": "read_file",
                "description": "ファイルの内容を読み込む",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "ファイルパス"}
                    }
                }
            },
            # ... 他のツール
        ]
```

### 3.3 レビューモジュール

#### 3.3.1 critical_thinking.py

```python
"""クリティカルシンキングレビューエンジン"""
from enum import Enum
from typing import Dict, List, Any

class ReviewResult(Enum):
    PASS = "PASS"
    PASS_WITH_SUGGESTIONS = "PASS_WITH_SUGGESTIONS"
    FAIL = "FAIL"

class CriticalThinkingReviewer:
    """レビューエンジン"""

    def __init__(self, claude_client: ClaudeClient):
        self.claude = claude_client

    def review(self, phase: str, artifact: str, context: Dict) -> Dict[str, Any]:
        """成果物をレビュー"""
        # 1. レビュープロンプト構築
        prompt = self.build_review_prompt(phase, artifact, context)

        # 2. Claude API呼び出し
        review_text = self.claude.chat(prompt)

        # 3. レビュー結果をパース
        result = self.parse_review_result(review_text)

        return result

    def parse_review_result(self, review_text: str) -> Dict[str, Any]:
        """レビュー結果を構造化"""
        # 判定: PASS / PASS_WITH_SUGGESTIONS / FAIL
        # ブロッカー: List[str]
        # 改善提案: List[str]
        # クオリティゲート評価: Dict[str, bool]
        pass

    def build_review_prompt(self, phase: str, artifact: str,
                           context: Dict) -> List[Dict]:
        """レビュープロンプト構築"""
        # Phase固有のクオリティゲートを含める
        quality_gates = self.get_quality_gates(phase)

        prompt = f"""
あなたは経験豊富なシニアエンジニアです。以下の成果物をレビューしてください。

# クオリティゲート（最低基準）
{quality_gates}

# レビュー姿勢
- 完璧ではなく「十分」を目指す（80点で合格）
- ブロッカーと改善提案を明確に区別
- プロジェクトを前に進めることが最優先

# 成果物
{artifact}

# 前フェーズのコンテキスト
{context}

# 出力フォーマット
## 判定: PASS / PASS_WITH_SUGGESTIONS / FAIL

## ブロッカー（FAIL判定の場合のみ）
- [ブロッカー1]

## 改善提案（任意）
- [提案1]

## クオリティゲート評価
- [ ] 項目1: 合格/不合格
"""
        return prompt
```

---

## 4. データ構造設計

### 4.1 metadata.json 完全版

```json
{
  "issue_number": "123",
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/123",
  "issue_title": "新機能追加",
  "issue_body": "Issue本文（最初の500文字）",
  "workflow_version": "1.0.0",
  "current_phase": "requirements",
  "branch_name": "feature/issue-123-new-feature",

  "design_decisions": {
    "implementation_strategy": null,
    "test_strategy": null,
    "test_code_strategy": null
  },

  "cost_tracking": {
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_cost_usd": 0.0,
    "per_phase_cost": {}
  },

  "phases": {
    "requirements": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-07T10:00:00Z",
      "completed_at": "2025-10-07T10:05:00Z",
      "review_result": "PASS",
      "review_feedback": null,
      "tokens_used": {"input": 5000, "output": 3000}
    },
    "design": {
      "status": "in_progress",
      "retry_count": 0,
      "started_at": "2025-10-07T10:05:00Z",
      "completed_at": null,
      "review_result": null,
      "review_feedback": null,
      "tokens_used": null,
      "decisions": {
        "implementation_strategy": "EXTEND",
        "test_strategy": "BOTH",
        "test_code_strategy": "CREATE_TEST"
      }
    },
    "test_scenario": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null,
      "review_feedback": null,
      "tokens_used": null,
      "applied_test_strategy": null
    },
    "implementation": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null,
      "review_feedback": null,
      "tokens_used": null,
      "applied_implementation_strategy": null,
      "files_changed": []
    },
    "testing": {
      "status": "pending",
      "retry_count": 0,
      "test_failure_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null,
      "review_feedback": null,
      "tokens_used": null,
      "test_results": null
    },
    "documentation": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null,
      "review_feedback": null,
      "tokens_used": null
    }
  },

  "created_at": "2025-10-07T10:00:00Z",
  "updated_at": "2025-10-07T10:05:00Z"
}
```

### 4.2 config.yaml

```yaml
# Claude API設定
claude:
  model: "claude-sonnet-4-5-20250929"
  max_tokens_per_request: 4096
  temperature: 1.0
  timeout: 120

# コスト制限
cost_limits:
  per_phase_max_tokens: 100000
  per_workflow_max_cost_usd: 5.0
  warning_threshold: 0.8

# リトライ設定
retry:
  max_attempts: 3
  backoff_multiplier: 2
  initial_delay_seconds: 1

# コードベース分析設定
codebase_analysis:
  max_files: 20
  max_tokens: 50000
  file_size_limit_kb: 100

# テスト実行設定
testing:
  timeout_seconds: 600
  failure_max_retries: 3

# Git設定
git:
  branch_prefix: "feature/issue-"
  commit_message_template: "[AI-Workflow][Phase {phase}] {phase_name}: {status}"
  workflow_dir: ".ai-workflow"

# GitHub設定
github:
  api_url: "https://api.github.com"
  timeout: 30
```

---

## 5. ファイル・ディレクトリ構造

### 5.1 新規作成ファイル一覧

```
scripts/ai-workflow/
├── main.py                         # CLIエントリーポイント
├── requirements.txt                # 依存パッケージ
├── config.yaml                     # 設定ファイル
├── README.md                       # 使用方法
├── .env.example                    # 環境変数サンプル
│
├── core/
│   ├── __init__.py
│   ├── claude_client.py           # Claude APIクライアント
│   ├── git_operations.py          # Git操作
│   ├── workflow_state.py          # ワークフロー状態管理
│   └── context_manager.py         # コンテキスト管理
│
├── phases/
│   ├── __init__.py
│   ├── base_phase.py              # フェーズ基底クラス
│   ├── requirements.py            # Phase 1
│   ├── design.py                  # Phase 2
│   ├── test_scenario.py           # Phase 3
│   ├── implementation.py          # Phase 4
│   ├── testing.py                 # Phase 5
│   └── documentation.py           # Phase 6
│
├── reviewers/
│   ├── __init__.py
│   ├── base_reviewer.py           # レビュー基底クラス
│   └── critical_thinking.py       # クリティカルシンキングレビュー
│
├── prompts/
│   ├── requirements/
│   │   ├── execute.txt            # 要件定義作成プロンプト
│   │   └── review.txt             # 要件定義レビュープロンプト
│   ├── design/
│   │   ├── execute.txt
│   │   └── review.txt
│   ├── test_scenario/
│   │   ├── execute.txt
│   │   └── review.txt
│   ├── implementation/
│   │   ├── execute.txt
│   │   └── review.txt
│   ├── testing/
│   │   ├── execute.txt
│   │   └── review.txt
│   ├── documentation/
│   │   ├── execute.txt
│   │   └── review.txt
│   └── common/
│       ├── quality_gates.txt      # クオリティゲート定義
│       └── review_guidelines.txt  # レビューガイドライン
│
├── utils/
│   ├── __init__.py
│   ├── file_utils.py              # ファイル操作ユーティリティ
│   ├── logger.py                  # ロギング
│   ├── github_client.py           # GitHub API
│   └── cost_tracker.py            # コスト追跡
│
└── tests/
    ├── __init__.py
    ├── conftest.py                # pytestフィクスチャ
    ├── unit/
    │   ├── test_claude_client.py
    │   ├── test_workflow_state.py
    │   ├── test_phases.py
    │   └── test_reviewers.py
    └── integration/
        ├── test_phase_flow.py     # フェーズ連携テスト
        ├── test_retry_logic.py    # リトライテスト
        └── test_end_to_end.py     # E2Eテスト（モック使用）
```

### 5.2 Jenkins関連ファイル

```
jenkins/jobs/
├── dsl/admin/
│   └── ai_workflow_orchestrator_job.groovy  # Job DSL定義
│
└── pipeline/admin/ai-workflow/
    └── Jenkinsfile                          # パイプライン定義
```

---

## 6. Jenkins Job設計

### 6.1 Job DSL (ai_workflow_orchestrator_job.groovy)

```groovy
pipelineJob('Admin_Jobs/ai-workflow-orchestrator') {
    description('AI駆動開発自動化ワークフロー - GitHub IssueからPR作成まで自動化')

    parameters {
        string {
            name('ISSUE_URL')
            description('GitHub Issue URL')
            trim(true)
        }

        choice {
            name('START_PHASE')
            choices(['requirements', 'design', 'test_scenario', 'implementation', 'testing', 'documentation'])
            description('開始フェーズ（デフォルト: requirements）')
        }

        booleanParam {
            name('DRY_RUN')
            defaultValue(false)
            description('ドライラン実行（実際のAPI呼び出しなし）')
        }
    }

    definition {
        cpsScm {
            scm {
                git {
                    remote {
                        url('${GIT_REPO_URL}')
                        credentials('github-app-token')
                    }
                    branch('*/main')
                }
            }
            scriptPath('jenkins/jobs/pipeline/admin/ai-workflow/Jenkinsfile')
        }
    }

    triggers {
        // 手動実行のみ（将来的にwebhook追加可能）
    }
}
```

### 6.2 Jenkinsfile

```groovy
@Library('jenkins-shared-library') _

pipeline {
    agent any

    environment {
        CLAUDE_API_KEY = credentials('claude-api-key')
        GITHUB_TOKEN = credentials('github-app-token')
        PYTHON_SCRIPT = 'scripts/ai-workflow/main.py'
        WORKFLOW_DIR = '.ai-workflow'
    }

    stages {
        stage('Initialize') {
            steps {
                script {
                    echo "=== AI Workflow Orchestrator ==="
                    echo "Issue URL: ${params.ISSUE_URL}"
                    echo "Start Phase: ${params.START_PHASE}"

                    sh """
                        python ${PYTHON_SCRIPT} init \
                            --issue-url ${params.ISSUE_URL} \
                            --start-phase ${params.START_PHASE}
                    """
                }
            }
        }

        stage('Phase 1: Requirements') {
            when {
                expression { shouldRunPhase('requirements') }
            }
            steps {
                script {
                    executePhase('requirements')
                }
            }
        }

        stage('Phase 1: Review') {
            when {
                expression { shouldRunPhase('requirements') }
            }
            steps {
                script {
                    reviewPhase('requirements')
                }
            }
        }

        stage('Phase 2: Design') {
            when {
                expression { shouldRunPhase('design') }
            }
            steps {
                script {
                    executePhase('design')
                }
            }
        }

        stage('Phase 2: Review') {
            when {
                expression { shouldRunPhase('design') }
            }
            steps {
                script {
                    reviewPhase('design')
                }
            }
        }

        // Phase 3-6も同様

        stage('Finalize') {
            steps {
                script {
                    sh """
                        python ${PYTHON_SCRIPT} finalize \
                            --create-pr
                    """
                }
            }
        }
    }

    post {
        success {
            echo "AI Workflow completed successfully!"
            sh "python ${PYTHON_SCRIPT} notify --status success"
        }
        failure {
            echo "AI Workflow failed"
            sh "python ${PYTHON_SCRIPT} notify --status failure"
        }
    }
}

def shouldRunPhase(phase) {
    // metadata.jsonから実行判断
    def status = sh(
        script: "python ${PYTHON_SCRIPT} status --phase ${phase}",
        returnStdout: true
    ).trim()
    return status == 'pending' || status == 'in_progress'
}

def executePhase(phase) {
    retry(3) {
        sh """
            python ${PYTHON_SCRIPT} execute \
                --phase ${phase} \
                --api-key ${CLAUDE_API_KEY} \
                --github-token ${GITHUB_TOKEN}
        """
    }
}

def reviewPhase(phase) {
    def reviewResult = sh(
        script: """
            python ${PYTHON_SCRIPT} review \
                --phase ${phase} \
                --api-key ${CLAUDE_API_KEY}
        """,
        returnStdout: true
    ).trim()

    if (reviewResult == 'FAIL') {
        error("Phase ${phase} review failed")
    }
}
```

---

## 7. 依存ライブラリ (requirements.txt)

```txt
# Claude API
anthropic==0.37.0

# CLI
click==8.1.7

# Git操作
GitPython==3.1.40

# YAML設定
PyYAML==6.0.1

# GitHub API
PyGithub==2.1.1
requests==2.31.0

# テスト
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0

# コード品質
black==23.12.1
pylint==3.0.3
mypy==1.7.1

# ユーティリティ
python-dotenv==1.0.0
```

---

## 8. 実装優先順位

### Phase 1実装（MVP: Minimum Viable Product）

**目標**: Phase 1（要件定義）の完全動作

1. **基盤実装** (Week 1-2):
   - `core/claude_client.py` - 基本的なチャット機能
   - `core/workflow_state.py` - metadata.json管理
   - `core/git_operations.py` - ブランチ作成、コミット
   - `main.py` - `init`コマンド実装

2. **Phase 1実装** (Week 2):
   - `phases/requirements.py`
   - `prompts/requirements/execute.txt`
   - 動作確認（手動テスト）

3. **Phase 1レビュー実装** (Week 3):
   - `reviewers/critical_thinking.py` - 基本レビュー
   - `prompts/requirements/review.txt`
   - クオリティゲート判定ロジック

4. **Jenkins統合** (Week 3):
   - `jenkins/jobs/dsl/admin/ai_workflow_orchestrator_job.groovy`
   - `jenkins/jobs/pipeline/admin/ai-workflow/Jenkinsfile`
   - Phase 1のみ実行できることを確認

### Phase 2実装（拡張）

**Phase 2-6を順次実装**

5. **Phase 2-3実装** (Week 4-5):
   - Phase 2: 設計 + 戦略判断
   - Phase 3: テストシナリオ

6. **Phase 4実装** (Week 5-6):
   - Function Calling実装
   - ツール定義・実行

7. **Phase 5-6実装** (Week 7):
   - Phase 5: テスト実行 + Phase 4へのフィードバックループ
   - Phase 6: ドキュメント作成

8. **テスト実装** (Week 8):
   - Unitテスト
   - Integrationテスト

---

## 9. セキュリティ考慮事項

### 9.1 認証情報管理

- **Claude API Key**: Jenkins Credentials Plugin経由（環境変数）
- **GitHub Token**: Jenkins Credentials Plugin経由（環境変数）
- `.env`ファイル: ローカルテスト用（`.gitignore`に追加）

### 9.2 生成コードの安全性

- Phase 4実装時、危険なコマンド実行を防止:
  ```python
  BLACKLIST_COMMANDS = ['rm -rf /', 'sudo', 'chmod 777']
  ```

- サンドボックス環境での実行（将来対応）

### 9.3 API呼び出し制限

- レート制限の遵守
- コスト上限の強制

---

## 10. モニタリング・ロギング

### 10.1 ログ出力

```python
# utils/logger.py
import logging

class WorkflowLogger:
    def __init__(self, phase: str, issue_number: str):
        self.logger = logging.getLogger(f'ai-workflow.{phase}')
        self.phase = phase
        self.issue = issue_number

    def info(self, message: str):
        self.logger.info(f"[{self.issue}][{self.phase}] {message}")

    def error(self, message: str):
        self.logger.error(f"[{self.issue}][{self.phase}] {message}")
```

### 10.2 メトリクス収集

- トークン使用量
- フェーズ実行時間
- リトライ回数
- コスト

---

## 11. 成功基準（Phase 2固有）

- [x] 実装戦略が明確に判断されている（CREATE）
- [x] テスト戦略が明確に判断されている（BOTH）
- [x] テストコード戦略が明確に判断されている（CREATE_TEST）
- [x] 既存コードへの影響範囲が分析されている（影響なし）
- [x] 変更・追加が必要なファイルがリストアップされている（セクション5.1参照）
- [x] 設計が実装可能である（技術選定完了）
- [x] レビュワーの指摘に対する回答が明記されている（セクション2.2参照）

---

**次フェーズ**: Phase 3（テストシナリオ作成）
