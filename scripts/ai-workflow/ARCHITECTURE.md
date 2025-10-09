# AI駆動開発自動化ワークフロー アーキテクチャ

**バージョン**: 1.0.0
**最終更新**: 2025-10-07

---

## 1. システム概要

AI駆動開発自動化ワークフローは、GitHub IssueからPR作成まで、Claude AIによる自動開発を実現するシステムです。

### 1.1 システムの目的

- **開発プロセスの自動化**: 要件定義→設計→実装→テストを自動実行
- **品質の担保**: 各フェーズでAIレビューを実施し、品質ゲートを設定
- **コスト管理**: API利用料金を追跡し、予算内で実行
- **トレーサビリティ**: すべての成果物とメタデータをGit管理

### 1.2 システムの特徴

- **6フェーズワークフロー**: 要件定義 → 詳細設計 → テストシナリオ → 実装 → テスト → ドキュメント
- **AI批判的思考レビュー**: 各フェーズ完了後にAIがレビュー（PASS/PASS_WITH_SUGGESTIONS/FAIL）
- **リトライ機能**: FAIL時は最大3回まで自動リトライ
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
│  │  phases/ (フェーズ実装・未実装)                           │  │
│  │  - base_phase.py: フェーズ基底クラス                      │  │
│  │  - requirements.py: 要件定義                              │  │
│  │  - design.py: 詳細設計                                    │  │
│  │  - test_scenario.py: テストシナリオ                       │  │
│  │  - implementation.py: 実装                                │  │
│  │  - testing.py: テスト実行                                 │  │
│  │  - documentation.py: ドキュメント作成                     │  │
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
│  │ - 要件生成   │  │ - PR作成     │  │ - .ai-workflow/      │ │
│  │ - レビュー   │  │              │  │   - metadata.json    │ │
│  └──────────────┘  └──────────────┘  │   - 01-requirements  │ │
│                                       │   - 02-design        │ │
│                                       │   - 03-test-scenario │ │
│                                       │   - 04-implementation│ │
│                                       │   - 05-testing       │ │
│                                       │   - 06-documentation │ │
│                                       └──────────────────────┘ │
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
    │    - current_phase: "requirements"
    │    - 6フェーズをpendingで初期化
    │    - cost_tracking初期化
    │    - created_at, updated_at設定
    │
    │ 4. metadata.jsonに書き込み
    ▼
[ファイルシステム]
    │
    └── .ai-workflow/issue-{number}/metadata.json
```

### 4.2 フェーズ実行フロー（将来実装）

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
[phases/requirements.py]
    │
    │ 3. GitHub APIでIssue内容を取得
    │ 4. プロンプトテンプレートを読み込み
    │ 5. Claude APIで要件定義を生成
    ▼
[ClaudeClient]
    │
    │ 6. Claude API呼び出し（messages.create）
    │ 7. コスト追跡（input/output tokens）
    ▼
[WorkflowState]
    │
    │ 8. フェーズステータスをIN_PROGRESSに更新
    │ 9. 成果物を01-requirements.mdに保存
    │ 10. Gitコミット
    │ 11. フェーズステータスをCOMPLETEDに更新
    ▼
[main.py:review()]
    │
    │ 12. レビュープロンプトを生成
    │ 13. Claude APIでレビュー実行
    ▼
[CriticalThinkingReviewer]
    │
    │ 14. レビュー結果判定（PASS/PASS_WITH_SUGGESTIONS/FAIL）
    │ 15. 01-requirements-review.mdに保存
    ▼
[WorkflowState]
    │
    │ 16. review_resultを保存
    │ 17. PASSなら次フェーズへ
    │ 18. FAILならretry_count増加→再実行
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
    "requirements": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-07T10:00:00.000Z",
      "completed_at": "2025-10-07T10:05:23.456Z",
      "review_result": "PASS_WITH_SUGGESTIONS"
    },
    "design": {
      "status": "in_progress",
      "retry_count": 0,
      "started_at": "2025-10-07T10:05:30.000Z",
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
        # Phase 2での実装戦略などを保存

    def get_phase_status(self, phase: str) -> str:
        """フェーズステータスを取得"""
```

**設計判断**:
- Enum（PhaseStatus）で型安全性を確保
- ISO 8601形式のタイムスタンプ（UTC）
- ensure_ascii=Falseで日本語対応
- parents=True, exist_ok=Trueで堅牢なディレクトリ作成

### 5.2 ClaudeClient（core/claude_client.py）・未実装

**責務**: Claude API通信、コスト追跡

**設計方針**:
- Anthropic Python SDKを使用
- 指数バックオフリトライ（1秒, 2秒, 4秒）
- トークン数とコストの追跡
- Sonnet 4.5料金: $3/1M input, $15/1M output

### 5.3 BasePhase（phases/base_phase.py）・未実装

**責務**: フェーズ実行の基底クラス

**インターフェース**:
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
```

### 5.4 CriticalThinkingReviewer（reviewers/critical_thinking.py）・未実装

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
| Phase 1実行（要件定義） | < 60秒 | 未実装 |
| 全6フェーズ完了 | < 10分 | 未実装 |

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

### 8.2 BDDシナリオ

**実装済み**:
- シナリオ1: ワークフロー初期化とメタデータ作成（6ステップ）

**将来追加予定**:
- シナリオ2-7（ai-workflow-test-scenario.md v2.0.0参照）

---

## 9. 今後の拡張計画

詳細は [ROADMAP.md](ROADMAP.md) を参照。

**優先順位**:
1. **Phase 1実装**: Claude API統合、要件定義自動生成
2. **Git操作**: ブランチ作成、コミット、PR作成
3. **Phase 2-6実装**: 詳細設計→ドキュメント
4. **レビューエンジン**: 批判的思考アルゴリズム
5. **Jenkins統合**: Jenkinsfileパイプライン実装

---

## 10. 参考文献

- [Anthropic Claude API Documentation](https://docs.anthropic.com/)
- [GitHub REST API](https://docs.github.com/rest)
- [Behave Documentation](https://behave.readthedocs.io/)
- [Click Documentation](https://click.palletsprojects.com/)

---

**バージョン**: 1.0.0 (MVP)
**最終更新**: 2025-10-07
