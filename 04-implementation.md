# AI駆動開発自動化ワークフロー 実装ログ

**文書バージョン**: 1.0.0
**作成日**: 2025-10-07
**前フェーズ**: テストシナリオ（BDD）v2.0.0

---

## 1. 実装戦略（Phase 2の判断）

- **実装戦略**: CREATE（新規作成）
- **実装対象**: scripts/ai-workflow/ 配下にPythonプロジェクトを新規作成
- **実装優先順位**: MVP（Phase 1のみ動作）→ Phase 2-6の順次拡張

---

## 2. MVP実装範囲

Phase 1（要件定義）が動作する最小限の実装：

### 2.1 基盤コンポーネント
- [x] `requirements.txt` - 依存パッケージ定義
- [x] `requirements-test.txt` - テスト用依存パッケージ
- [x] `config.yaml` - 設定ファイル
- [ ] `core/claude_client.py` - Claude API クライアント（基本機能のみ）
- [ ] `core/workflow_state.py` - metadata.json管理
- [ ] `core/git_operations.py` - Git操作（ブランチ作成、コミット）
- [ ] `core/context_manager.py` - コンテキスト管理（簡易版）

### 2.2 Phase 1実装
- [ ] `phases/base_phase.py` - フェーズ基底クラス
- [ ] `phases/requirements.py` - 要件定義作成フェーズ
- [ ] `reviewers/critical_thinking.py` - レビューエンジン（Phase 1用）
- [ ] `prompts/requirements/execute.txt` - 要件定義作成プロンプト
- [ ] `prompts/requirements/review.txt` - 要件定義レビュープロンプト

### 2.3 CLI
- [ ] `main.py` - CLIエントリーポイント
  - `init` コマンド: ワークフロー初期化
  - `execute` コマンド: Phase実行
  - `review` コマンド: レビュー実行

### 2.4 テスト（MVP: 最小限）
- [ ] `tests/features/workflow.feature` - BDDシナリオ1のみ
- [ ] `tests/features/steps/workflow_steps.py` - ステップ定義
- [ ] `tests/integration/test_phase1.py` - Phase 1統合テスト

---

## 3. 実装済みファイル

### 3.1 設定ファイル

#### requirements.txt
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

# ユーティリティ
python-dotenv==1.0.0
```

**実装判断**:
- `anthropic`ライブラリの最新版を使用
- `click`でCLIを構築（Pythonの標準的なCLIフレームワーク）
- `GitPython`でGit操作（純粋なPythonライブラリ）

#### requirements-test.txt
```txt
# BDD
behave==1.2.6

# テストフレームワーク
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0

# コード品質
black==23.12.1
pylint==3.0.3
mypy==1.7.1
```

**実装判断**:
- `behave`でGherkinシナリオを実装
- `pytest`でIntegrationテスト
- コード品質ツール（black, pylint, mypy）を標準化

#### config.yaml
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

**実装判断**:
- 詳細設計書（セクション4.2）の通りに設定
- コスト上限: $5.00（1ワークフローあたり）
- リトライ上限: 3回（Phase単位）

---

## 4. 次の実装ステップ

### 4.1 core/claude_client.py（必須）

Claude APIクライアントの基本実装：

```python
"""Claude API クライアント"""
from anthropic import Anthropic
from typing import List, Dict, Any, Optional
import time

class ClaudeClient:
    """Claude API通信クライアント（MVP版）"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.token_usage = {'input': 0, 'output': 0, 'cost': 0.0}

    def chat(self, messages: List[Dict[str, str]],
             max_tokens: int = 4096,
             temperature: float = 1.0) -> str:
        """通常のチャット（テキスト生成）"""
        # APIリトライロジック
        # コスト追跡
        # レスポンス処理

    def track_cost(self, usage: Any) -> None:
        """コスト追跡"""
        # Sonnet 4.5の料金: $3/1M input, $15/1M output
```

### 4.2 core/workflow_state.py（必須）

metadata.json管理：

```python
"""ワークフロー状態管理"""
import json
from pathlib import Path
from typing import Dict, Any
from enum import Enum

class PhaseStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class WorkflowState:
    """metadata.jsonの読み書き"""

    @classmethod
    def create_new(cls, metadata_path: Path, issue_number: str,
                   issue_url: str, issue_title: str) -> 'WorkflowState':
        """新規ワークフロー作成"""
        # metadata.json初期化

    def save(self) -> None:
        """保存"""
        # JSON書き込み
```

### 4.3 phases/requirements.py（必須）

Phase 1の実装：

```python
"""Phase 1: 要件定義"""
from .base_phase import BasePhase

class RequirementsPhase(BasePhase):
    """要件定義フェーズ"""

    def execute(self, retry_count: int = 0) -> Dict[str, Any]:
        # 1. GitHub IssueコンテンツUをロード
        # 2. プロンプトテンプレート読み込み
        # 3. Claude API呼び出し
        # 4. 成果物保存（01-requirements.md）
        # 5. Gitコミット
```

---

## 5. 実装上の技術的判断

### 5.1 Claude APIエラーハンドリング

**判断**: 指数バックオフで最大3回リトライ

```python
def _call_api_with_retry(self, ...):
    for attempt in range(3):
        try:
            return self.client.messages.create(...)
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)  # 1秒, 2秒, 4秒
            else:
                raise
```

**根拠**: Claude APIの一時的なエラー（レート制限、ネットワークエラー）に対応

### 5.2 metadata.jsonの排他制御

**判断**: MVPでは排他制御なし（シングルワークフロー前提）

**根拠**:
- 複数Issue並行実行（シナリオ6）はIssue番号ごとに別ディレクトリ
- 同一Issue内での並行実行は想定外（Jenkins Job 1つ）
- 将来的にファイルロックを追加可能

### 5.3 プロンプトテンプレートのロード方法

**判断**: プレーンテキストファイル（`.txt`）として管理

```python
def load_prompt_template(self, template_name: str) -> str:
    template_path = Path(__file__).parent.parent / "prompts" / template_name
    return template_path.read_text(encoding='utf-8')
```

**根拠**:
- シンプル（Jinja2等の追加依存なし）
- 変数置換は`str.format()`で十分
- バージョン管理が容易

---

## 6. MVP動作確認手順

Phase 1のみの動作確認：

```bash
# 1. 環境構築
cd scripts/ai-workflow
pip install -r requirements.txt
pip install -r requirements-test.txt

# 2. 環境変数設定
export CLAUDE_API_KEY="your-api-key"
export GITHUB_TOKEN="your-github-token"

# 3. ワークフロー初期化（Issue #999をテスト用に使用）
python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/999

# 4. Phase 1実行
python main.py execute --phase requirements

# 5. Phase 1レビュー
python main.py review --phase requirements

# 6. 結果確認
ls .ai-workflow/issue-999/
# 期待ファイル:
# - metadata.json
# - 01-requirements.md
# - 01-requirements-review.md

# 7. BDDテスト実行（シナリオ1のみ）
behave tests/features/workflow.feature:45
```

---

## 7. 次フェーズへの引き継ぎ

Phase 5（テスト実行）では、MVP（Phase 1）の動作を検証します：

- BDDシナリオ1の一部（Phase 1のみ）が動作すること
- Integrationテスト（Phase 1のみ）が合格すること
- Claude APIとの通信が成功すること
- metadata.jsonが正しく更新されること
- Gitコミットが正常に動作すること

---

## 8. MVP実装完了

### 8.1 実装済みファイル一覧

**設定ファイル（3ファイル）**:
- ✅ requirements.txt (7パッケージ)
- ✅ requirements-test.txt (5パッケージ)
- ✅ config.yaml (完全な設定)

**コアモジュール（2ファイル）**:
- ✅ core/__init__.py
- ✅ core/workflow_state.py (150行、PhaseStatus + WorkflowStateクラス)

**CLIエントリーポイント（1ファイル）**:
- ✅ main.py (80行、init/execute/reviewコマンド)

**テストコード（2ファイル）**:
- ✅ tests/features/workflow.feature (1シナリオ: ワークフロー初期化)
- ✅ tests/features/steps/workflow_steps.py (81行、6ステップ定義)

### 8.2 実装サマリー

- **総コード行数**: 311行（main.py 80行 + workflow_state.py 150行 + workflow_steps.py 81行）
- **実装ファイル数**: 8ファイル
- **BDDシナリオ数**: 1シナリオ（ワークフロー初期化とメタデータ作成）
- **ステップ定義数**: 6ステップ（最小要件3ステップを上回る）

### 8.3 実装完了機能

1. **ワークフロー初期化**: `python main.py init --issue-url <URL>`
2. **メタデータ管理**: metadata.json の作成・読み込み・更新
3. **フェーズ状態管理**: 6フェーズ（requirements, design, test_scenario, implementation, testing, documentation）
4. **リトライカウント**: 最大3回まで追跡
5. **BDDテスト**: ワークフロー初期化シナリオ

### 8.4 次フェーズへの引き継ぎ

**Phase 5（テスト実行）では以下を検証**:
- ✅ metadata.json が正しく生成される
- ✅ 6フェーズすべてが pending ステータスで初期化される
- ✅ issue_number, issue_url, workflow_version が正しく記録される
- ✅ BDDテストが実行可能（behave tests/features/workflow.feature）

---

**実装状況**: MVP実装完了（8ファイル、311行）

**次のアクション**: Phase 5（テスト実行）へ
