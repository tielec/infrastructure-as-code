# AI駆動開発自動化ワークフロー アーキテクチャ

**バージョン**: 1.0.0
**最終更新**: 2025-10-07

---

## 1. システム概要

AI駆動開発自動化ワークフローは、GitHub IssueからPR作成まで、Claude AIによる自動開発を実現するシステムです。

### 1.1 システムの目的

- **開発プロセスの自動化**: プロジェクト計画→要件定義→設計→実装→テストを自動実行
- **事前計画の自動化**: Phase 0で実装戦略・テスト戦略を事前決定し、後続フェーズの負荷を軽減
- **品質の担保**: 各フェーズでAIレビューを実施し、品質ゲートを設定
- **コスト管理**: API利用料金を追跡し、予算内で実行
- **トレーサビリティ**: すべての成果物とメタデータをGit管理

### 1.2 システムの特徴

- **9フェーズワークフロー**: Phase 0（プロジェクト計画） → Phase 1（要件定義） → Phase 2（詳細設計） → Phase 3（テストシナリオ） → Phase 4（実装） → Phase 5（テストコード実装） → Phase 6（テスト実行） → Phase 7（ドキュメント） → Phase 8（レポート）
- **Phase 0（Planning）**: プロジェクトマネージャとして機能
  - 実装戦略・テスト戦略の事前決定により、Phase 2の負荷を軽減
  - Issue複雑度分析、タスク分割、依存関係特定
  - 各フェーズの見積もり、リスク評価と軽減策の策定
  - planning.mdとmetadata.jsonへの戦略保存
- **AI批判的思考レビュー**: 各フェーズ完了後にAIがレビュー（PASS/PASS_WITH_SUGGESTIONS/FAIL）
- **統一リトライ機能**: execute()失敗時も自動的にreview() → revise()を実行し、最大3回までリトライ
- **BDD準拠**: ユーザー行動視点のテストシナリオ（Gherkin形式）

---

## 2. アーキテクチャ設計思想

### 2.1 設計原則

1. **モジュラー設計**: フェーズごとに独立したモジュール、疎結合
2. **状態管理の一元化**: metadata.jsonで全状態を管理
3. **冪等性**: 同じ操作を複数回実行しても安全
4. **テスタビリティ**: BDD/Unitテスト可能な設計
5. **拡張性**: 新しいフェーズやレビューアルゴリズムの追加が容易

### 2.2 品質哲学

**「80点で十分」の思想**:
- 完璧を求めず、実用的な品質で前進
- PASS_WITH_SUGGESTIONSで改善提案を記録しつつ進行
- FAILはブロッカーのみ、非ブロッカーは提案として処理

---

## 3. システムアーキテクチャ

### 3.1 全体構成図

```
┌─────────────────────────────────────────────────────────────────┐
│                         Jenkins Job                              │
│  (AI Workflow Orchestrator)                                      │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Jenkinsfile (パイプライン定義)                           │  │
│  │  - GitHub Issue URLを受け取る                             │  │
│  │  - Pythonスクリプトを呼び出す                             │  │
│  │  - 各フェーズの成功/失敗を監視                            │  │
│  └────────────┬─────────────────────────────────────────────┘  │
│               │                                                   │
└───────────────┼───────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Python ワークフローエンジン                     │
│                   (scripts/ai-workflow/)                         │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  main.py (CLIエントリーポイント)                          │  │
│  │  - init: ワークフロー初期化                               │  │
│  │  - execute: フェーズ実行                                  │  │
│  │  - review: レビュー実行                                   │  │
│  └────────────┬─────────────────────────────────────────────┘  │
│               │                                                   │
│  ┌────────────▼─────────────────────────────────────────────┐  │
│  │  core/ (コアモジュール)                                   │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │ workflow_state.py: metadata.json管理               │ │  │
│  │  │ - create_new(): ワークフロー初期化                 │ │  │
│  │  │ - save(): 状態保存                                 │ │  │
│  │  │ - update_phase_status(): フェーズ更新              │ │  │
│  │  │ - increment_retry_count(): リトライ管理            │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │ claude_client.py: Claude API通信（未実装）         │ │  │
│  │  │ - chat(): テキスト生成                             │ │  │
│  │  │ - track_cost(): コスト追跡                         │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │ git_operations.py: Git操作（未実装）               │ │  │
│  │  │ - create_branch(): ブランチ作成                    │ │  │
│  │  │ - commit(): コミット                               │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  phases/ (フェーズ実装)                                    │  │
│  │  - base_phase.py: フェーズ基底クラス                      │  │
│  │  - planning.py: Phase 0（プロジェクト計画）              │  │
│  │    - Issue分析、実装戦略・テスト戦略決定                 │  │
│  │    - タスク分割、見積もり、リスク評価                     │  │
│  │  - requirements.py: Phase 1（要件定義）                  │  │
│  │  - design.py: Phase 2（詳細設計）                        │  │
│  │    - Phase 0の戦略を参照し、設計に専念                   │  │
│  │  - test_scenario.py: Phase 3（テストシナリオ）           │  │
│  │  - implementation.py: Phase 4（実装）                    │  │
│  │    - 実コードのみを実装                                  │  │
│  │  - test_implementation.py: Phase 5（テストコード実装）   │  │
│  │    - テストコードのみを実装                              │  │
│  │  - testing.py: Phase 6（テスト実行）                     │  │
│  │  - documentation.py: Phase 7（ドキュメント作成）         │  │
│  │  - report.py: Phase 8（レポート）                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  reviewers/ (レビューエンジン・未実装)                    │  │
│  │  - critical_thinking.py: 批判的思考レビュー               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   外部システム連携                                │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ Claude API   │  │ GitHub API   │  │ Git Repository       │ │
│  │ - Sonnet 4.5 │  │ - Issue取得  │  │ - feature/issue-XXX  │ │
│  │ - 計画生成   │  │ - PR作成     │  │ - .ai-workflow/      │ │
│  │ - 要件生成   │  │              │  │   - metadata.json    │ │
│  │ - レビュー   │  │              │  │   - 00-planning          │ │
│  └──────────────┘  └──────────────┘  │   - 01-requirements      │ │
│                                       │   - 02-design            │ │
│                                       │   - 03-test-scenario     │ │
│                                       │   - 04-implementation    │ │
│                                       │   - 05-test-implementation│ │
│                                       │   - 06-testing           │ │
│                                       │   - 07-documentation     │ │
│                                       │   - 08-report            │ │
│                                       └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 レイヤー構成

| レイヤー | 役割 | 主要コンポーネント |
|----------|------|-------------------|
| **オーケストレーション層** | ジョブ管理、パイプライン制御 | Jenkins Jenkinsfile |
| **CLI層** | ユーザーインターフェース | main.py |
| **ビジネスロジック層** | フェーズ実行、レビュー | phases/, reviewers/ |
| **コア層** | 状態管理、API通信、Git操作 | core/ |
| **外部連携層** | API通信、Git操作 | Claude API, GitHub API |

---

## 4. データフロー

### 4.1 ワークフロー初期化フロー

```
[ユーザー]
    │
    │ python main.py init --issue-url <URL>
    ▼
[main.py:init()]
    │
    │ 1. Issue URLからIssue番号を抽出
    │ 2. .ai-workflow/issue-{number}/ ディレクトリ作成
    ▼
[WorkflowState.create_new()]
    │
    │ 3. 初期データ構造を生成
    │    - issue_number, issue_url, issue_title
    │    - workflow_version: "1.0.0"
    │    - current_phase: "planning"（Phase 0から開始）
    │    - 9フェーズをpendingで初期化
    │    - cost_tracking初期化
    │    - created_at, updated_at設定
    │
    │ 4. metadata.jsonに書き込み
    ▼
[ファイルシステム]
    │
    └── .ai-workflow/issue-{number}/metadata.json
```

### 4.2 フェーズ実行フロー（v1.6.0実装済み）

```
[Jenkins]
    │
    │ Jenkinsfileがpython main.py executeを呼び出し
    ▼
[main.py:execute()]
    │
    │ 1. metadata.jsonを読み込み
    │ 2. current_phaseを確認
    ▼
[BasePhase.run()]
    │
    │ 3. 【v1.6.0追加】統一リトライループ開始（MAX_RETRIES=3）
    │ 4. フェーズステータスをIN_PROGRESSに更新
    ▼
[リトライループ（attempt 1~3）]
    │
    │ 5. [ATTEMPT N/3]ログ出力
    │ 6. attempt == 1: execute()実行
    │    attempt >= 2: review() → revise()実行
    ▼
[phases/requirements.py:execute()]
    │
    │ 7. GitHub APIでIssue内容を取得
    │ 8. プロンプトテンプレートを読み込み
    │ 9. Claude APIで要件定義を生成
    │ 10. コスト追跡（input/output tokens）
    ▼
[BasePhase リトライ判定]
    │
    │ 11. execute()成功 → 最終レビューへ
    │ 12. execute()失敗 → attempt >= 2でreview() → revise()
    │ 13. 最大リトライ到達 → フェーズ失敗
    ▼
[最終レビュー（成功時のみ）]
    │
    │ 14. review()実行
    │ 15. レビュー結果判定（PASS/PASS_WITH_SUGGESTIONS/FAIL）
    │ 16. レビュー結果をGitHub Issueコメント投稿
    ▼
[WorkflowState]
    │
    │ 17. review_resultを保存
    │ 18. 成果物を01-requirements/output/requirements.mdに保存
    │ 19. 【v1.4.0追加】BasePhase.post_output()で成果物をGitHub Issueコメント投稿
    │ 20. フェーズステータスをCOMPLETEDに更新
    ▼
[finally: Git自動commit & push]
    │
    │ 21. 成功・失敗問わずGitコミット・プッシュ
    ▼
[metadata.json]
```

### 4.3 データ永続化

**metadata.json 構造**:

```json
{
  "issue_number": "123",
  "issue_url": "https://github.com/.../issues/123",
  "issue_title": "新機能の追加",
  "workflow_version": "1.0.0",
  "current_phase": "requirements",
  "design_decisions": {
    "implementation_strategy": "CREATE",
    "test_strategy": "INTEGRATION_BDD",
    "test_code_strategy": null
  },
  "cost_tracking": {
    "total_input_tokens": 12345,
    "total_output_tokens": 6789,
    "total_cost_usd": 0.45
  },
  "phases": {
    "planning": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-10T09:00:00.000Z",
      "completed_at": "2025-10-10T09:05:23.456Z",
      "review_result": "PASS"
    },
    "requirements": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-10T09:06:00.000Z",
      "completed_at": "2025-10-10T09:11:23.456Z",
      "review_result": "PASS_WITH_SUGGESTIONS"
    },
    "design": {
      "status": "in_progress",
      "retry_count": 0,
      "started_at": "2025-10-10T09:12:00.000Z",
      "completed_at": null,
      "review_result": null
    },
    "test_scenario": { "status": "pending", ... },
    "implementation": { "status": "pending", ... },
    "testing": { "status": "pending", ... },
    "documentation": { "status": "pending", ... }
  },
  "created_at": "2025-10-07T10:00:00.000Z",
  "updated_at": "2025-10-07T10:05:30.000Z"
}
```

---

## 5. コンポーネント詳細

### 5.1 WorkflowState（core/workflow_state.py）

**責務**: metadata.jsonの読み書き、ワークフロー状態管理

**主要メソッド**:

```python
class WorkflowState:
    @classmethod
    def create_new(cls, metadata_path: Path, issue_number: str,
                   issue_url: str, issue_title: str) -> 'WorkflowState':
        """新規ワークフロー作成"""
        # 初期データ構造を生成しJSONに書き込み

    def save(self) -> None:
        """metadata.jsonを保存"""
        # updated_atを更新してJSON書き込み

    def update_phase_status(self, phase: str, status: PhaseStatus) -> None:
        """フェーズステータスを更新"""
        # IN_PROGRESS: started_at設定
        # COMPLETED/FAILED: completed_at設定

    def increment_retry_count(self, phase: str) -> int:
        """リトライカウントを増加（上限3回）"""
        # 上限チェック、カウント増加

    def set_design_decision(self, key: str, value: str) -> None:
        """設計判断を記録"""
        # Phase 0での実装戦略などを保存（Phase 2でも使用可能）

    def get_phase_status(self, phase: str) -> str:
        """フェーズステータスを取得"""
```

**設計判断**:
- Enum（PhaseStatus）で型安全性を確保
- ISO 8601形式のタイムスタンプ（UTC）
- ensure_ascii=Falseで日本語対応
- parents=True, exist_ok=Trueで堅牢なディレクトリ作成

### 5.2 ClaudeClient（core/claude_client.py）・実装済み

**責務**: Claude API通信、コスト追跡

**設計方針**:
- Anthropic Python SDKを使用
- 指数バックオフリトライ（1秒, 2秒, 4秒）
- トークン数とコストの追跡
- Sonnet 4.5料金: $3/1M input, $15/1M output

### 5.3 BasePhase（phases/base_phase.py）・実装済み

**責務**: フェーズ実行の基底クラス

**主要メソッド**:
```python
class BasePhase(ABC):
    @abstractmethod
    def execute(self, retry_count: int = 0) -> Dict[str, Any]:
        """フェーズ実行"""
        pass

    @abstractmethod
    def review(self) -> Dict[str, Any]:
        """レビュー実行"""
        pass

    def post_output(self, output_content: str, title: Optional[str] = None):
        """GitHub Issueに成果物を投稿（v1.4.0で追加）"""
        # GitHubClient経由でIssueコメントとして成果物を投稿
        # 失敗時でもワークフローは継続（WARNING表示）

    def _get_next_sequence_number(self, target_dir: Path) -> int:
        """対象ディレクトリ内の既存ログファイルから次の連番を取得（v1.5.0で追加）"""
        # agent_log_*.md パターンのファイルを検索
        # 正規表現で連番を抽出し、最大値+1を返す
        # ファイルが存在しない場合は1を返す

    def _save_execution_logs(self, prompt: str, messages: List[str], log_prefix: str = ''):
        """プロンプトとエージェントログを保存（連番付き、v1.5.0で拡張）"""
        # 連番を自動決定してログファイルに付与
        # agent_log_{N}.md, agent_log_raw_{N}.txt, prompt_{N}.txt
```

**v1.4.0での変更**:
- `post_output()`メソッドを追加し、全フェーズで成果物をGitHub Issueに自動投稿
- エラーハンドリング強化：投稿失敗時でもワークフローを継続

**v1.5.0での変更（Issue #317）**:
- `_get_next_sequence_number()`メソッドを追加し、ログファイルの連番を自動管理
- `_save_execution_logs()`を拡張し、リトライ時に過去のログを保持
- ログファイル名: `agent_log_1.md` → `agent_log_2.md` → `agent_log_3.md`...
- 成果物ファイル（`output/`配下）は従来通り上書き

**v1.6.0での変更（Issue #331）**:
- `run()`メソッドのリトライループロジックを全面修正
- execute()とrevise()を統一リトライループに統合
- execute()失敗時も自動的にreview() → revise()を実行
- 試行回数の可視化：`[ATTEMPT N/3]`形式でログ出力
- 一時的なエラー（ネットワーク障害、API制限等）からの自動回復が可能

### 5.4 GitManager（core/git_manager.py）

**責務**: Git操作の管理、Phase完了後の自動commit & push

**主要メソッド**:

```python
class GitManager:
    def __init__(self, repo_path: Path, metadata_manager: MetadataManager,
                 config: Optional[Dict] = None):
        """初期化"""

    def commit_phase_output(self, phase_name: str, status: str,
                            review_result: Optional[str] = None) -> Dict[str, Any]:
        """Phase成果物をcommit"""
        # 1. Issue番号を取得
        # 2. 変更ファイルを収集（untracked + modified + staged）
        # 3. _filter_phase_files()でフィルタリング
        # 4. git add {files}
        # 5. create_commit_message()でメッセージ生成
        # 6. git commit
        # 戻り値: {'success': bool, 'commit_hash': str, 'files_committed': List[str], 'error': str}

    def push_to_remote(self, max_retries: int = 3,
                      retry_delay: float = 2.0) -> Dict[str, Any]:
        """リモートリポジトリにpush"""
        # 1. 現在のブランチを取得
        # 2. git push origin HEAD:{branch}
        # 3. ネットワークエラー時はリトライ（最大max_retries回）
        # 4. 権限エラー時はリトライせず即座に失敗
        # 戻り値: {'success': bool, 'retries': int, 'error': str}

    def create_commit_message(self, phase_name: str, status: str,
                             review_result: Optional[str] = None) -> str:
        """コミットメッセージ生成"""
        # フォーマット:
        # [ai-workflow] Phase X (phase_name) - status
        #
        # Issue: #XXX
        # Phase: X (phase_name)
        # Status: completed/failed
        # Review: PASS/PASS_WITH_SUGGESTIONS/FAIL/N/A
        #
        # Auto-generated by AI Workflow

    def _filter_phase_files(self, files: List[str], issue_number: int) -> List[str]:
        """Phaseファイルのフィルタリング"""
        # Include: .ai-workflow/issue-XXX/*（対象Issue）
        # Include: プロジェクト本体ファイル（.ai-workflow/以外）
        # Exclude: .ai-workflow/issue-YYY/*（他のIssue）
        # Exclude: *@tmp/*（Jenkins一時ディレクトリ）

    def _setup_github_credentials(self) -> None:
        """GitHub Token認証設定"""
        # 環境変数GITHUB_TOKENを使用してremote URLを更新
        # https://github.com/owner/repo.git → https://{token}@github.com/owner/repo.git

    def _is_retriable_error(self, error: Exception) -> bool:
        """リトライ可能エラー判定"""
        # リトライ可能: timeout, connection refused, network is unreachable
        # リトライ不可: permission denied, authentication failed
```

**設計判断**:
- GitPythonライブラリを使用
- finally句で確実に実行（BasePhase.run()と統合）
- ファイルフィルタリングで他Issueへの影響を防止
- リトライロジックでネットワークエラーに対応

**シーケンス図：Git自動commit & push**

```
BasePhase.run()
    ├─ execute()
    ├─ review()
    └─ finally:
         ├─ GitManager.commit_phase_output()
         │    ├─ 変更ファイル収集
         │    ├─ _filter_phase_files()
         │    │    ├─ Include: .ai-workflow/issue-XXX/*
         │    │    └─ Exclude: issue-YYY/*, @tmp/*
         │    ├─ git add
         │    ├─ create_commit_message()
         │    └─ git commit
         │
         └─ GitManager.push_to_remote()
              ├─ git push origin HEAD:{branch}
              ├─ Retry on network errors (max 3)
              └─ No retry on permission errors
```

**エラーハンドリング**:
1. **ネットワークエラー**: 自動リトライ（最大3回、2秒間隔）
2. **権限エラー**: リトライせず即座にエラー返却
3. **Phase失敗時**: 失敗時もcommit実行（トラブルシューティング用）

### 5.5 CriticalThinkingReviewer（reviewers/critical_thinking.py）

**責務**: AI批判的思考レビュー

**レビュー判定基準**:
- **PASS**: すべて合格、次フェーズへ進行可能
- **PASS_WITH_SUGGESTIONS**: 非ブロッカーの改善提案あり、次フェーズへ進行可能
- **FAIL**: ブロッカーあり、リトライ必要

---

## 6. セキュリティとエラーハンドリング

### 6.1 認証情報管理

- **Claude API Key**: 環境変数 `CLAUDE_API_KEY`
- **GitHub Token**: 環境変数 `GITHUB_TOKEN`
- **ハードコーディング禁止**: すべて環境変数またはSSM Parameter Storeで管理

### 6.2 エラーハンドリング戦略

1. **API通信エラー**: 指数バックオフで最大3回リトライ
2. **コスト超過**: $5.00上限到達時にワークフロー停止
3. **リトライ上限**: 同一フェーズで3回FAIL時にワークフロー停止
4. **ファイルI/Oエラー**: 例外を明確なメッセージでユーザーに通知

### 6.3 並行実行制御

**現状（MVP）**:
- 単一ワークフロー前提（排他制御なし）
- 異なるIssue番号は別ディレクトリで並行実行可能

**将来**:
- 同一Issue内での並行実行にはファイルロック実装を検討

---

## 7. パフォーマンスとスケーラビリティ

### 7.1 パフォーマンス目標

| 項目 | 目標値 | 実測値（MVP） |
|------|--------|--------------|
| ワークフロー初期化 | < 1秒 | 未計測 |
| metadata.json読み込み | < 100ms | 未計測 |
| Phase 0実行（プロジェクト計画） | < 3分 | 実装済み |
| Phase 1実行（要件定義） | < 60秒 | 実装済み |
| 全7フェーズ完了 | < 15分 | 未実装 |

### 7.2 スケーラビリティ

**水平スケール**:
- Issue番号ごとに独立したディレクトリ → 複数Issue並行処理可能
- Jenkinsで複数ジョブ同時実行可能

**垂直スケール**:
- Claude API制限: RPM=50, TPM=40,000（Sonnet 4.5）
- 1ワークフローあたり10万トークン上限で制御

---

## 8. テスト戦略

### 8.1 テストピラミッド

```
        ┌──────────────┐
        │  E2E (BDD)   │  ← behave（Gherkin）
        │  1 scenario  │
        └──────────────┘
       ┌────────────────┐
       │  Integration   │  ← pytest（未実装）
       │  (未実装)       │
       └────────────────┘
     ┌──────────────────┐
     │  Unit Tests      │  ← pytest（未実装）
     │  (未実装)         │
     └──────────────────┘
```

**MVP（v1.0.0）**: BDDテスト1シナリオのみ実装
**v1.2.0**: Phase 2 E2Eテストを追加

### 8.2 BDDシナリオ

**実装済み**:
- シナリオ1: ワークフロー初期化とメタデータ作成（6ステップ）

**E2Eテスト**:
- test_phase1.py: Phase 1（要件定義）のE2Eテスト
- test_phase2.py: Phase 2（詳細設計）のE2Eテスト

**将来追加予定**:
- シナリオ2-7（ai-workflow-test-scenario.md v2.0.0参照）

---

## 9. 今後の拡張計画

詳細は [ROADMAP.md](ROADMAP.md) を参照。

**優先順位**:
1. ~~**Phase 1実装**: Claude API統合、要件定義自動生成~~ ✅ 完了（v1.1.0）
2. ~~**Phase 2実装**: 詳細設計、設計判断機能~~ ✅ 完了（v1.2.0）
3. ~~**Phase 0実装**: プロジェクト計画、実装戦略の事前決定~~ ✅ 完了（v1.5.0）
4. **PR自動作成**: GitHub PR作成機能
5. **コスト最適化**: プロンプトキャッシュ活用
6. **レビュー基準のカスタマイズ**: プロジェクト固有の品質基準設定

---

## 10. 参考文献

- [Anthropic Claude API Documentation](https://docs.anthropic.com/)
- [GitHub REST API](https://docs.github.com/rest)
- [Behave Documentation](https://behave.readthedocs.io/)
- [Click Documentation](https://click.palletsprojects.com/)

---

**バージョン**: 1.5.0
**最終更新**: 2025-10-10
**Phase 0実装**: Issue #313で追加（プロジェクトマネージャ役割）
