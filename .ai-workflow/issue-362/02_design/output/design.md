# 詳細設計書 - Issue #362

## 📋 プロジェクト情報

- **Issue番号**: #362
- **Issue タイトル**: [FEATURE] Project Evaluation フェーズの追加
- **Issue URL**: https://github.com/tielec/infrastructure-as-code/issues/362
- **作成日**: 2025-10-12
- **Planning Document**: `.ai-workflow/issue-362/00_planning/output/planning.md`
- **Requirements Document**: `.ai-workflow/issue-362/01_requirements/output/requirements.md`

---

## 0. Planning & Requirements Document の確認

### 開発計画の全体像（Planning Phase）

Planning Phase（Phase 0）にて以下の戦略が策定されています：

- **実装戦略**: CREATE（新規フェーズクラスの作成）
- **テスト戦略**: ALL（ユニット + インテグレーション + BDD）
- **テストコード戦略**: CREATE_TEST（新規テストファイルの作成）
- **見積もり工数**: 約18時間
- **リスクレベル**: 高

### 要件定義の確認（Requirements Phase）

要件定義書（Phase 1）にて以下の機能要件が定義されています：

- **FR-001**: プロジェクト全体の評価実行
- **FR-002**: 判定タイプの決定（PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT）
- **FR-003**: 残タスクの抽出
- **FR-004**: GitHub Issue の自動作成
- **FR-005**: メタデータの巻き戻し
- **FR-006**: 再実行の実行
- **FR-007**: ワークフローのクローズ

---

## 1. アーキテクチャ設計

### 1.1 システム全体図

```
┌──────────────────────────────────────────────────────────┐
│                     AI Workflow                          │
│                                                          │
│  Phase 0 → Phase 1 → ... → Phase 8 → Phase 9           │
│  (Planning)  (Requirements)   (Report)  (Evaluation)    │
└──────────────────────────────────────────────────────────┘
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │ EvaluationPhase │
                                    └─────────────────┘
                                              │
                 ┌────────────────────────────┼────────────────────────────┐
                 │                            │                            │
                 ▼                            ▼                            ▼
        ┌────────────────┐         ┌────────────────┐          ┌────────────────┐
        │ execute()      │         │ review()       │          │ Decision Logic │
        │ - プロジェクト   │         │ - 評価レビュー  │          │ - PASS         │
        │   全体評価      │         │ - 品質ゲート    │          │ - PASS_WITH... │
        │ - 成果物読込    │         │   チェック     │          │ - FAIL_PHASE_X │
        │ - 評価実行      │         └────────────────┘          │ - ABORT        │
        └────────────────┘                                     └────────────────┘
                 │                                                      │
                 └──────────────────────────────────────────────────────┘
                                         │
                      ┌──────────────────┼──────────────────┐
                      │                  │                  │
                      ▼                  ▼                  ▼
            ┌─────────────────┐ ┌───────────────┐ ┌───────────────┐
            │ Issue Creation  │ │ Metadata      │ │ Workflow      │
            │ - 残タスク抽出   │ │ Rollback      │ │ Closure       │
            │ - Issue自動作成 │ │ - Phase巻戻   │ │ - PR/Issue    │
            │ - ラベル付与    │ │ - 再実行準備  │ │   クローズ    │
            └─────────────────┘ └───────────────┘ └───────────────┘
```

### 1.2 コンポーネント間の関係

```
EvaluationPhase (extends BasePhase)
    │
    ├─ uses → ClaudeAgentClient（評価実行）
    ├─ uses → GitHubClient（Issue作成、PR/Issueクローズ）
    ├─ uses → MetadataManager（メタデータ管理）
    └─ uses → ContentParser（レビュー結果パース）

MetadataManager
    │
    ├─ uses → WorkflowState（状態管理）
    └─ new methods:
        ├─ rollback_to_phase(phase_name)
        ├─ get_all_phases_status()
        └─ backup_metadata()

GitHubClient
    │
    └─ new methods:
        ├─ create_issue_from_evaluation(...)
        ├─ close_issue_with_reason(...)
        └─ close_pull_request(...)
```

### 1.3 データフロー

```
1. execute() フロー:
   Phase 1-8 成果物
        ↓
   EvaluationPhase.execute()
        ↓
   Claude Agent SDK（評価実行）
        ↓
   evaluation_report.md 生成
        ↓
   判定タイプ決定

2. PASS_WITH_ISSUES フロー:
   evaluation_report.md
        ↓
   残タスク抽出
        ↓
   GitHubClient.create_issue_from_evaluation()
        ↓
   新しいIssue作成
        ↓
   metadata.json 更新（created_issue_url）

3. FAIL_PHASE_X フロー:
   判定結果（FAIL_PHASE_4）
        ↓
   MetadataManager.rollback_to_phase('implementation')
        ↓
   Phase 4-8 のステータスを pending に変更
        ↓
   metadata.json.backup_{timestamp} 作成
        ↓
   Phase 4 から再実行可能

4. ABORT フロー:
   判定結果（ABORT）
        ↓
   GitHubClient.close_issue_with_reason()
        ↓
   GitHubClient.close_pull_request()
        ↓
   metadata.json 更新（abort_reason）
        ↓
   ワークフロー停止
```

---

## 2. 実装戦略判断

### 実装戦略: **CREATE**

**判断根拠**:

1. **新規フェーズクラスの作成**:
   - `scripts/ai-workflow/phases/evaluation.py` を新規作成
   - 既存の Phase 0-8 とは独立した新しいフェーズ
   - `BasePhase` を継承し、既存の設計パターンを踏襲

2. **新規プロンプトファイルの作成**:
   - `scripts/ai-workflow/prompts/evaluation/execute.txt`
   - `scripts/ai-workflow/prompts/evaluation/review.txt`
   - `scripts/ai-workflow/prompts/evaluation/revise.txt`（オプション）

3. **既存コードの拡張**:
   - `main.py`: `phase_classes` に `'evaluation': EvaluationPhase` を追加
   - `base_phase.py`: `PHASE_NUMBERS` に `'evaluation': '09'` を追加
   - `metadata_manager.py`: 新規メソッド追加（`rollback_to_phase()` など）
   - `github_client.py`: 新規メソッド追加（Issue作成、クローズ処理）
   - `workflow_state.py`: メタデータマイグレーション処理追加

4. **テンプレートファイルの更新**:
   - `metadata.json.template`: `evaluation` フィールド追加

**結論**: 新規フェーズの追加であり、既存の Phase 0-8 には影響を与えない。一部既存コードの拡張が必要だが、主要な実装は新規作成となるため、**CREATE** 戦略が最適。

---

## 3. テスト戦略判断

### テスト戦略: **ALL**

**判断根拠**:

1. **ユニットテスト必要性（高）**:
   - `EvaluationPhase` クラスの各メソッドのロジック検証が必須
   - 判定アルゴリズム（`_determine_decision()`）の正確性検証
   - 残タスク抽出ロジック（`_extract_remaining_tasks()`）のテスト
   - メタデータ巻き戻し処理（`MetadataManager.rollback_to_phase()`）の動作確認

2. **インテグレーションテスト必要性（高）**:
   - Phase 1-8 の成果物を実際に読み込み、評価フローを検証
   - GitHub API 連携（Issue作成、PR/Issueクローズ）の動作確認
   - メタデータの整合性検証（巻き戻し後の状態確認）
   - エンドツーエンドの評価フロー検証

3. **BDDテスト必要性（高）**:
   - プロジェクトマネージャー視点のユーザーストーリー検証
   - 「プロジェクトが合格と判定される」シナリオ
   - 「残タスクが新Issueとして作成される」シナリオ
   - 「特定フェーズから再実行される」シナリオ
   - 「プロジェクトが中止される」シナリオ

4. **リスクレベルが高い**:
   - Planning Phase でリスクレベル「高」と評価されている
   - 判定ロジックの誤りは重大な影響を与える
   - GitHub API連携の失敗はワークフロー全体に影響

**結論**: 大規模な変更であり、複数のコンポーネントが連携する複雑な機能のため、すべてのテストレベル（ユニット、インテグレーション、BDD）を実施する **ALL** が必須。

---

## 4. テストコード戦略判断

### テストコード戦略: **CREATE_TEST**

**判断根拠**:

1. **新規テストファイル作成が必要**:
   - `tests/unit/phases/test_evaluation.py`: EvaluationPhase のユニットテスト
   - `tests/integration/test_evaluation_integration.py`: 評価フローの統合テスト
   - `tests/bdd/features/evaluation.feature`: BDDシナリオ
   - `tests/bdd/steps/test_evaluation_steps.py`: BDDステップ実装

2. **既存テストとの独立性**:
   - 既存の Phase 0-8 のテストは独立しており、Evaluation フェーズの影響を受けない
   - 新規フェーズのため、既存テストファイルを拡張する必要はない

3. **新規コンポーネントのテスト**:
   - `MetadataManager` の新規メソッド（`rollback_to_phase()` など）のテスト
   - `GitHubClient` の新規メソッド（`create_issue_from_evaluation()` など）のテスト
   - これらは既存テストファイルに追加する形で実装

**結論**: 新規フェーズのため、新規テストファイルを作成する **CREATE_TEST** が最適。ただし、`MetadataManager` と `GitHubClient` の新規メソッドについては、既存のユニットテストファイル（`test_metadata_manager.py`、`test_github_client.py`）に追加する。

---

## 5. 影響範囲分析

### 5.1 既存コードへの影響

#### 変更が必要なファイル

| ファイルパス | 変更内容 | 影響度 | 理由 |
|------------|---------|--------|------|
| `scripts/ai-workflow/phases/evaluation.py` | **新規作成** | 新規 | EvaluationPhase クラス実装 |
| `scripts/ai-workflow/prompts/evaluation/execute.txt` | **新規作成** | 新規 | 評価実行プロンプト |
| `scripts/ai-workflow/prompts/evaluation/review.txt` | **新規作成** | 新規 | 評価レビュープロンプト |
| `scripts/ai-workflow/prompts/evaluation/revise.txt` | **新規作成** | 新規 | 評価修正プロンプト（オプション） |
| `scripts/ai-workflow/main.py` | phase_classes に 'evaluation' 追加 | 小 | Phase 9 を実行可能にするため |
| `scripts/ai-workflow/phases/base_phase.py` | PHASE_NUMBERS に 'evaluation': '09' 追加 | 小 | フェーズ番号マッピング |
| `scripts/ai-workflow/core/metadata_manager.py` | 新規メソッド追加（rollback_to_phase など） | 中 | メタデータ巻き戻し機能 |
| `scripts/ai-workflow/core/workflow_state.py` | migrate() メソッド更新 | 中 | evaluation フィールドのマイグレーション |
| `scripts/ai-workflow/core/github_client.py` | 新規メソッド追加（Issue作成、クローズ処理） | 中 | GitHub API 連携機能拡張 |
| `scripts/ai-workflow/metadata.json.template` | evaluation フィールド追加 | 小 | メタデータテンプレート更新 |

#### 変更が不要なファイル

- `scripts/ai-workflow/phases/planning.py`: Phase 0 は変更不要
- `scripts/ai-workflow/phases/requirements.py`: Phase 1 は変更不要
- `scripts/ai-workflow/phases/design.py`: Phase 2 は変更不要
- `scripts/ai-workflow/phases/test_scenario.py`: Phase 3 は変更不要
- `scripts/ai-workflow/phases/implementation.py`: Phase 4 は変更不要
- `scripts/ai-workflow/phases/test_implementation.py`: Phase 5 は変更不要
- `scripts/ai-workflow/phases/testing.py`: Phase 6 は変更不要
- `scripts/ai-workflow/phases/documentation.py`: Phase 7 は変更不要
- `scripts/ai-workflow/phases/report.py`: Phase 8 は変更不要
- `scripts/ai-workflow/core/claude_agent_client.py`: Claude Agent SDK連携は変更不要
- `scripts/ai-workflow/core/content_parser.py`: コンテンツパーサーは変更不要
- `scripts/ai-workflow/core/git_manager.py`: Git操作は変更不要

### 5.2 依存関係の変更

**新規依存の追加**: なし
- 既存のPython標準ライブラリと既存モジュール（`GitHubClient`、`MetadataManager` など）のみ使用

**既存依存の変更**: なし

### 5.3 マイグレーション要否

**必要**

**理由**:
- メタデータJSON構造に `evaluation` フィールドを追加
- 既存の `metadata.json` ファイルには `evaluation` フィールドが存在しない
- `WorkflowState.migrate()` メソッドで自動マイグレーション実装が必要

**マイグレーション内容**:

```json
{
  "phases": {
    "evaluation": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null,
      "decision": null,
      "failed_phase": null,
      "remaining_tasks": [],
      "created_issue_url": null,
      "abort_reason": null
    }
  }
}
```

**マイグレーション実装**:

`WorkflowState.migrate()` メソッドに以下のロジックを追加：

```python
# evaluationフェーズの追加チェック
if 'evaluation' not in self.data['phases']:
    print("[INFO] Migrating metadata.json: Adding evaluation phase")
    self.data['phases']['evaluation'] = template['phases']['evaluation'].copy()
    migrated = True
```

---

## 6. 変更・追加ファイルリスト

### 6.1 新規作成ファイル

**フェーズ実装**:
- `scripts/ai-workflow/phases/evaluation.py`

**プロンプトファイル**:
- `scripts/ai-workflow/prompts/evaluation/execute.txt`
- `scripts/ai-workflow/prompts/evaluation/review.txt`
- `scripts/ai-workflow/prompts/evaluation/revise.txt`（オプション）

**テストファイル**:
- `tests/unit/phases/test_evaluation.py`
- `tests/integration/test_evaluation_integration.py`
- `tests/bdd/features/evaluation.feature`
- `tests/bdd/steps/test_evaluation_steps.py`

### 6.2 修正が必要な既存ファイル

**コアファイル**:
- `scripts/ai-workflow/main.py`（phase_classes に evaluation 追加）
- `scripts/ai-workflow/phases/base_phase.py`（PHASE_NUMBERS に evaluation 追加）
- `scripts/ai-workflow/core/metadata_manager.py`（新規メソッド追加）
- `scripts/ai-workflow/core/workflow_state.py`（migrate() 更新）
- `scripts/ai-workflow/core/github_client.py`（新規メソッド追加）
- `scripts/ai-workflow/metadata.json.template`（evaluation フィールド追加）

**テストファイル（既存テストに追加）**:
- `tests/unit/core/test_metadata_manager.py`（rollback_to_phase() のテスト追加）
- `tests/unit/core/test_github_client.py`（Issue作成メソッドのテスト追加）

### 6.3 削除が必要なファイル

なし

---

## 7. 詳細設計

### 7.1 EvaluationPhase クラス設計

#### クラス図

```
BasePhase
    │
    └── EvaluationPhase
         │
         ├── execute(): Dict[str, Any]
         ├── review(): Dict[str, Any]
         ├── revise(review_feedback: str): Dict[str, Any]
         │
         ├── _get_all_phase_outputs(issue_number: int): Dict[str, Path]
         ├── _determine_decision(evaluation_content: str): Dict[str, Any]
         ├── _extract_remaining_tasks(evaluation_content: str): List[Dict[str, Any]]
         ├── _handle_pass_with_issues(remaining_tasks: List[Dict]): Dict[str, Any]
         ├── _handle_fail_phase_x(failed_phase: str): Dict[str, Any]
         └── _handle_abort(abort_reason: str): Dict[str, Any]
```

#### メソッドシグネチャ

```python
class EvaluationPhase(BasePhase):
    """Phase 9: プロジェクト評価フェーズ"""

    def __init__(self, *args, **kwargs):
        """初期化"""
        super().__init__(phase_name='evaluation', *args, **kwargs)

    def execute(self) -> Dict[str, Any]:
        """
        プロジェクト全体を評価

        Returns:
            Dict[str, Any]:
                - success: bool
                - output: str - evaluation_report.md のパス
                - decision: str - PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT
                - error: Optional[str]

        処理フロー:
            1. Phase 1-8 の成果物を読み込み
            2. 評価プロンプトを生成
            3. Claude Agent SDK で評価実行
            4. evaluation_report.md 生成
            5. 判定タイプ決定
            6. 判定に応じた処理実行
        """

    def review(self) -> Dict[str, Any]:
        """
        評価結果をレビュー

        Returns:
            Dict[str, Any]:
                - result: str - PASS/PASS_WITH_SUGGESTIONS/FAIL
                - feedback: str
                - suggestions: List[str]

        処理フロー:
            1. evaluation_report.md を読み込み
            2. レビュープロンプトを生成
            3. Claude Agent SDK でレビュー実行
            4. レビュー結果をパース
        """

    def revise(self, review_feedback: str) -> Dict[str, Any]:
        """
        レビュー結果を元に評価を修正

        Args:
            review_feedback: レビュー結果のフィードバック

        Returns:
            Dict[str, Any]:
                - success: bool
                - output: str
                - error: Optional[str]

        処理フロー:
            1. 元の evaluation_report.md を読み込み
            2. 修正プロンプトを生成
            3. Claude Agent SDK で修正実行
            4. evaluation_report.md 更新
        """

    def _get_all_phase_outputs(self, issue_number: int) -> Dict[str, Path]:
        """
        Phase 0-8 の全成果物パスを取得

        Args:
            issue_number: Issue番号

        Returns:
            Dict[str, Path]: フェーズ名 → 成果物パス

        成果物パス:
            - planning: 00_planning/output/planning.md
            - requirements: 01_requirements/output/requirements.md
            - design: 02_design/output/design.md
            - test_scenario: 03_test_scenario/output/test-scenario.md
            - implementation: 04_implementation/output/implementation.md
            - test_implementation: 05_test_implementation/output/test-implementation.md
            - testing: 06_testing/output/test-result.md
            - documentation: 07_documentation/output/documentation-update-log.md
            - report: 08_report/output/report.md
        """

    def _determine_decision(self, evaluation_content: str) -> Dict[str, Any]:
        """
        評価内容から判定タイプを決定

        Args:
            evaluation_content: evaluation_report.md の内容

        Returns:
            Dict[str, Any]:
                - decision: str - PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT
                - failed_phase: Optional[str] - FAIL_PHASE_X の場合のフェーズ名
                - abort_reason: Optional[str] - ABORT の場合の理由

        判定ロジック:
            1. evaluation_report.md から判定結果を抽出
            2. キーワードベースの判定（"PASS", "PASS_WITH_ISSUES", "FAIL_PHASE_", "ABORT"）
            3. ContentParser を使用して構造化データを抽出
        """

    def _extract_remaining_tasks(self, evaluation_content: str) -> List[Dict[str, Any]]:
        """
        評価内容から残タスクを抽出

        Args:
            evaluation_content: evaluation_report.md の内容

        Returns:
            List[Dict[str, Any]]: 残タスクリスト
                - task: str - タスク内容
                - phase: str - 発見されたフェーズ
                - priority: str - 優先度（高/中/低）

        抽出ロジック:
            1. evaluation_report.md の "残タスク" セクションを抽出
            2. チェックボックス項目（- [ ]）を抽出
            3. 優先度キーワードを検出（"優先度: 高" など）
        """

    def _handle_pass_with_issues(self, remaining_tasks: List[Dict]) -> Dict[str, Any]:
        """
        PASS_WITH_ISSUES 判定時の処理

        Args:
            remaining_tasks: 残タスクリスト

        Returns:
            Dict[str, Any]:
                - success: bool
                - created_issue_url: Optional[str]
                - error: Optional[str]

        処理フロー:
            1. 残タスクを Issue 本文に整形
            2. GitHubClient.create_issue_from_evaluation() 呼び出し
            3. metadata.json に created_issue_url を記録
            4. ワークフロー完了
        """

    def _handle_fail_phase_x(self, failed_phase: str) -> Dict[str, Any]:
        """
        FAIL_PHASE_X 判定時の処理

        Args:
            failed_phase: 失敗したフェーズ名

        Returns:
            Dict[str, Any]:
                - success: bool
                - error: Optional[str]

        処理フロー:
            1. MetadataManager.rollback_to_phase(failed_phase) 呼び出し
            2. Phase X 以降のステータスを pending に変更
            3. metadata.json.backup_{timestamp} 作成
            4. 評価レポートに巻き戻し理由を記録
        """

    def _handle_abort(self, abort_reason: str) -> Dict[str, Any]:
        """
        ABORT 判定時の処理

        Args:
            abort_reason: 中止理由

        Returns:
            Dict[str, Any]:
                - success: bool
                - error: Optional[str]

        処理フロー:
            1. GitHubClient.close_issue_with_reason() 呼び出し
            2. GitHubClient.close_pull_request() 呼び出し
            3. metadata.json に abort_reason を記録
            4. ワークフロー停止
        """
```

### 7.2 MetadataManager 拡張設計

#### 新規メソッド

```python
class MetadataManager:
    """メタデータ管理クラス（拡張）"""

    def rollback_to_phase(self, phase_name: str) -> Dict[str, Any]:
        """
        指定フェーズにメタデータを巻き戻し

        Args:
            phase_name: 巻き戻し先フェーズ名（例: 'implementation'）

        Returns:
            Dict[str, Any]:
                - success: bool
                - backup_path: str - バックアップファイルパス
                - rolled_back_phases: List[str] - 巻き戻されたフェーズ一覧
                - error: Optional[str]

        処理フロー:
            1. metadata.json のバックアップ作成（metadata.json.backup_{timestamp}）
            2. phase_name 以降のフェーズのステータスを pending に変更
            3. started_at, completed_at, review_result を null に設定
            4. retry_count を 0 に設定
            5. metadata.json を保存
            6. Phase X 以降の成果物ディレクトリを _backup_{timestamp} に移動（オプション）

        エラーハンドリング:
            - 不正なフェーズ名 → ValueError
            - バックアップ作成失敗 → IOError
        """

    def get_all_phases_status(self) -> Dict[str, str]:
        """
        全フェーズのステータスを取得

        Returns:
            Dict[str, str]: フェーズ名 → ステータス

        例:
            {
                'planning': 'completed',
                'requirements': 'completed',
                'design': 'completed',
                ...
                'evaluation': 'pending'
            }
        """

    def backup_metadata(self) -> str:
        """
        metadata.json のバックアップを作成

        Returns:
            str: バックアップファイルパス

        バックアップ命名:
            metadata.json.backup_{timestamp}
            例: metadata.json.backup_20251012_143022
        """

    def set_evaluation_decision(
        self,
        decision: str,
        failed_phase: Optional[str] = None,
        remaining_tasks: Optional[List[Dict]] = None,
        created_issue_url: Optional[str] = None,
        abort_reason: Optional[str] = None
    ):
        """
        評価判定結果を metadata.json に記録

        Args:
            decision: 判定タイプ（PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT）
            failed_phase: FAIL_PHASE_X の場合のフェーズ名
            remaining_tasks: PASS_WITH_ISSUES の場合の残タスクリスト
            created_issue_url: PASS_WITH_ISSUES の場合の作成されたIssue URL
            abort_reason: ABORT の場合の中止理由

        更新内容:
            metadata.json['phases']['evaluation']['decision'] = decision
            metadata.json['phases']['evaluation']['failed_phase'] = failed_phase
            metadata.json['phases']['evaluation']['remaining_tasks'] = remaining_tasks
            metadata.json['phases']['evaluation']['created_issue_url'] = created_issue_url
            metadata.json['phases']['evaluation']['abort_reason'] = abort_reason
        """
```

### 7.3 GitHubClient 拡張設計

#### 新規メソッド

```python
class GitHubClient:
    """GitHub API クライアント（拡張）"""

    def create_issue_from_evaluation(
        self,
        issue_number: int,
        remaining_tasks: List[Dict[str, Any]],
        evaluation_report_path: str
    ) -> Dict[str, Any]:
        """
        評価結果から新しい Issue を作成

        Args:
            issue_number: 元の Issue 番号
            remaining_tasks: 残タスクリスト
                - task: str - タスク内容
                - phase: str - 発見されたフェーズ
                - priority: str - 優先度（高/中/低）
            evaluation_report_path: 評価レポートのパス

        Returns:
            Dict[str, Any]:
                - success: bool
                - issue_url: Optional[str]
                - issue_number: Optional[int]
                - error: Optional[str]

        Issue テンプレート:
            タイトル: [FOLLOW-UP] Issue #{元のIssue番号} - 残タスク
            本文:
                ## 概要
                AI Workflow Issue #{元のIssue番号} の実装完了後に発見された残タスクです。

                ## 残タスク一覧

                - [ ] タスク1（Phase X で発見、優先度: 高）
                - [ ] タスク2（Phase Y で発見、優先度: 中）
                - [ ] タスク3（Phase Z で発見、優先度: 低）

                ## 関連

                - 元Issue: #{元のIssue番号}
                - 元PR: #{元のPR番号}
                - Evaluation Report: {evaluation_report_path}

                ---
                *自動生成: AI Workflow Phase 9 (Evaluation)*

            ラベル: enhancement, ai-workflow-follow-up
            Assignee: なし

        エラーハンドリング:
            - API 制限超過時: ログに記録し、エラーを返却（ワークフローは継続）
            - ネットワークエラー時: 最大3回リトライ
            - 失敗時: 評価レポートに「手動 Issue 作成が必要」と記載
        """

    def close_issue_with_reason(
        self,
        issue_number: int,
        reason: str
    ) -> Dict[str, Any]:
        """
        Issue をクローズ理由付きでクローズ

        Args:
            issue_number: Issue番号
            reason: クローズ理由

        Returns:
            Dict[str, Any]:
                - success: bool
                - error: Optional[str]

        コメントテンプレート:
            ## ⚠️ ワークフロー中止

            プロジェクト評価の結果、致命的な問題が発見されたため、ワークフローを中止します。

            ### 中止理由

            {reason}

            ### 発見された問題

            {evaluation_report.md から抽出}

            ### 推奨アクション

            - アーキテクチャの再設計
            - スコープの見直し
            - 技術選定の再検討

            ---
            *AI Workflow Phase 9 (Evaluation) - ABORT*

        処理フロー:
            1. コメントを投稿
            2. Issue を closed 状態に変更
        """

    def close_pull_request(
        self,
        pr_number: int,
        comment: str
    ) -> Dict[str, Any]:
        """
        Pull Request をクローズ

        Args:
            pr_number: PR番号
            comment: クローズコメント

        Returns:
            Dict[str, Any]:
                - success: bool
                - error: Optional[str]

        処理フロー:
            1. コメントを投稿
            2. PR を closed 状態に変更
        """

    def get_pull_request_number(
        self,
        issue_number: int
    ) -> Optional[int]:
        """
        Issue番号から関連するPR番号を取得

        Args:
            issue_number: Issue番号

        Returns:
            Optional[int]: PR番号（見つからない場合は None）

        処理フロー:
            1. Issue のコメントから PR リンクを検索
            2. PRブランチ名（ai-workflow/issue-{number}）から PR を検索
        """
```

### 7.4 データ構造設計

#### metadata.json 拡張

```json
{
  "issue_number": "362",
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/362",
  "issue_title": "[FEATURE] Project Evaluation フェーズの追加",
  "workflow_version": "2.0",
  "created_at": "2025-10-12T10:00:00Z",
  "updated_at": "2025-10-12T18:00:00Z",
  "current_phase": "evaluation",
  "phases": {
    "planning": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T10:00:00Z",
      "completed_at": "2025-10-12T11:00:00Z",
      "review_result": "N/A"
    },
    "requirements": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T11:00:00Z",
      "completed_at": "2025-10-12T12:00:00Z",
      "review_result": "PASS"
    },
    "design": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T12:00:00Z",
      "completed_at": "2025-10-12T13:00:00Z",
      "review_result": "PASS_WITH_SUGGESTIONS"
    },
    "test_scenario": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T13:00:00Z",
      "completed_at": "2025-10-12T14:00:00Z",
      "review_result": "PASS"
    },
    "implementation": {
      "status": "completed",
      "retry_count": 1,
      "started_at": "2025-10-12T14:00:00Z",
      "completed_at": "2025-10-12T15:30:00Z",
      "review_result": "PASS"
    },
    "test_implementation": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T15:30:00Z",
      "completed_at": "2025-10-12T16:00:00Z",
      "review_result": "PASS"
    },
    "testing": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T16:00:00Z",
      "completed_at": "2025-10-12T16:30:00Z",
      "review_result": "PASS_WITH_SUGGESTIONS"
    },
    "documentation": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T16:30:00Z",
      "completed_at": "2025-10-12T17:00:00Z",
      "review_result": "PASS"
    },
    "report": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T17:00:00Z",
      "completed_at": "2025-10-12T17:30:00Z",
      "review_result": "PASS"
    },
    "evaluation": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T17:30:00Z",
      "completed_at": "2025-10-12T18:00:00Z",
      "review_result": "PASS",
      "decision": "PASS_WITH_ISSUES",
      "failed_phase": null,
      "remaining_tasks": [
        {
          "task": "パフォーマンス最適化",
          "phase": "implementation",
          "priority": "中"
        },
        {
          "task": "追加テストケースの作成",
          "phase": "testing",
          "priority": "低"
        }
      ],
      "created_issue_url": "https://github.com/tielec/infrastructure-as-code/issues/363",
      "abort_reason": null
    }
  },
  "design_decisions": {
    "implementation_strategy": "CREATE",
    "test_strategy": "ALL",
    "test_code_strategy": "CREATE_TEST"
  },
  "cost_tracking": {
    "total_input_tokens": 150000,
    "total_output_tokens": 50000,
    "total_cost_usd": 12.5
  }
}
```

#### 判定タイプ定義

```python
class EvaluationDecision(Enum):
    """評価判定タイプ"""
    PASS = "PASS"
    PASS_WITH_ISSUES = "PASS_WITH_ISSUES"
    FAIL_PHASE_PLANNING = "FAIL_PHASE_PLANNING"
    FAIL_PHASE_REQUIREMENTS = "FAIL_PHASE_REQUIREMENTS"
    FAIL_PHASE_DESIGN = "FAIL_PHASE_DESIGN"
    FAIL_PHASE_TEST_SCENARIO = "FAIL_PHASE_TEST_SCENARIO"
    FAIL_PHASE_IMPLEMENTATION = "FAIL_PHASE_IMPLEMENTATION"
    FAIL_PHASE_TEST_IMPLEMENTATION = "FAIL_PHASE_TEST_IMPLEMENTATION"
    FAIL_PHASE_TESTING = "FAIL_PHASE_TESTING"
    FAIL_PHASE_DOCUMENTATION = "FAIL_PHASE_DOCUMENTATION"
    FAIL_PHASE_REPORT = "FAIL_PHASE_REPORT"
    ABORT = "ABORT"
```

### 7.5 インターフェース設計

#### Claude Agent SDK プロンプト構造

**execute.txt プロンプト構造**:

```
# プロジェクト評価フェーズ - 実行プロンプト

## タスク概要
Phase 1-8 の全成果物を評価し、プロジェクト全体の判定を行ってください。

## 入力情報

### Phase 0-8 成果物
- Planning Document: @{planning_document_path}
- Requirements Document: @{requirements_document_path}
- Design Document: @{design_document_path}
- Test Scenario Document: @{test_scenario_document_path}
- Implementation Document: @{implementation_document_path}
- Test Implementation Document: @{test_implementation_document_path}
- Test Result Document: @{test_result_document_path}
- Documentation Update Log: @{documentation_update_log_path}
- Report Document: @{report_document_path}

### GitHub Issue情報
## Issue情報
{issue_info}

## 評価観点

### 1. 完全性チェック
- すべての成果物が存在し、必要な情報が記載されているか
- 各フェーズの品質ゲートを満たしているか

### 2. 一貫性チェック
- フェーズ間で矛盾や不整合がないか
- Requirements → Design → Implementation → Testing のトレーサビリティ

### 3. 品質チェック
- 各成果物が品質ゲートを満たしているか
- レビュー結果が PASS または PASS_WITH_SUGGESTIONS か

### 4. 残タスクチェック
- 未完了タスクや改善提案が残っていないか
- ブロッカー（次フェーズに進めない問題）が存在しないか

## 判定基準

### PASS（合格）
- すべてのフェーズが completed 状態
- すべてのレビュー結果が PASS または PASS_WITH_SUGGESTIONS
- 致命的な問題（ブロッカー）が存在しない
- 残タスクがゼロ、または軽微な改善提案のみ

### PASS_WITH_ISSUES（条件付き合格）
- すべてのフェーズが completed 状態
- 基本要件は満たしているが、残タスクまたは改善提案が存在
- 残タスクは非ブロッカー（将来の改善として扱える）

### FAIL_PHASE_X（特定フェーズ不合格）
- Phase X の成果物に重大な問題がある
- Phase X のレビュー結果が FAIL
- Phase X から再実行することで問題が解決可能

### ABORT（中止）
- 致命的な問題が発見され、プロジェクト継続が不可能
- 例: アーキテクチャの根本的な欠陥、技術選定ミス

## 出力形式

評価レポートは `.ai-workflow/issue-{issue_number}/09_evaluation/output/evaluation_report.md` として保存してください。

Markdown形式で以下のセクションを含めてください：

### 必須セクション
1. 評価サマリー
2. 判定結果（PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT）
3. 判定理由
4. 各フェーズの評価結果（表形式）
5. 完全性チェック結果
6. 一貫性チェック結果
7. 品質チェック結果
8. 残タスク一覧（PASS_WITH_ISSUES の場合）
9. 再実行推奨フェーズ（FAIL_PHASE_X の場合）
10. 中止理由（ABORT の場合）

## 実装開始

上記を踏まえ、プロジェクト評価を実行してください。
```

**review.txt プロンプト構造**:

```
# プロジェクト評価フェーズ - レビュープロンプト

## タスク概要
作成された評価レポートをレビューし、品質ゲートを満たしているか確認してください。

## 入力情報

### 評価レポート
@{evaluation_report_path}

### Phase 0-8 成果物（参照用）
- Requirements Document: @{requirements_document_path}
- Design Document: @{design_document_path}
...（省略）

## レビュー観点

### 1. 判定の妥当性
- 判定タイプ（PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT）が適切か
- 判定理由が具体的かつ論理的か

### 2. 評価の網羅性
- すべての評価観点（完全性、一貫性、品質、残タスク）がカバーされているか
- 各フェーズの評価結果が明記されているか

### 3. 残タスクの妥当性
- PASS_WITH_ISSUES の場合、残タスクが適切に抽出されているか
- 優先度が正しく設定されているか

### 4. 品質ゲートチェック
- [ ] 判定タイプが明記されている
- [ ] 判定理由が具体的である（200文字以上）
- [ ] 各フェーズの評価結果が表形式で記載されている
- [ ] PASS_WITH_ISSUES の場合、残タスクが1個以上記載されている
- [ ] FAIL_PHASE_X の場合、失敗フェーズが明記されている
- [ ] ABORT の場合、中止理由が明記されている

## 出力形式

レビュー結果は以下の形式で出力してください：

**判定**: PASS / PASS_WITH_SUGGESTIONS / FAIL

**フィードバック**:
（具体的なフィードバック内容）

**改善提案**:
- 提案1
- 提案2

## 実装開始

上記を踏まえ、評価レポートをレビューしてください。
```

---

## 8. セキュリティ考慮事項

### 8.1 認証・認可

**GitHub API認証**:
- 環境変数 `GITHUB_TOKEN` を使用
- Token スコープ: `repo`（Issue作成、PR/Issueクローズに必要）
- Token のハードコーディング禁止

**メタデータアクセス制御**:
- metadata.json のバックアップファイルに機密情報が含まれないよう注意
- バックアップファイルのパーミッション: 600（所有者のみ読み書き可能）

### 8.2 データ保護

**メタデータバックアップ**:
- metadata.json の巻き戻し前に必ずバックアップを作成
- バックアップファイル名: `metadata.json.backup_{timestamp}`
- バックアップファイルは `.ai-workflow/issue-{number}/` ディレクトリに保存

**成果物の保護**:
- Phase X 以降の成果物ディレクトリを削除しない（履歴として残す）
- 成果物ディレクトリ名に `_backup_{timestamp}` サフィックスを追加して移動

### 8.3 セキュリティリスクと対策

**リスク1: GitHub Token漏洩**

- **リスク内容**: GitHub Token が漏洩すると、リポジトリへの不正アクセスが可能になる
- **対策**:
  - Token は環境変数で管理
  - ログに Token を出力しない
  - Token のスコープを最小限に設定（`repo` のみ）

**リスク2: メタデータ破損**

- **リスク内容**: metadata.json の巻き戻し処理が失敗し、メタデータが破損する
- **対策**:
  - 巻き戻し前に必ずバックアップを作成
  - 巻き戻し処理をトランザクション的に実装（失敗時はロールバック）
  - バックアップファイルから復元可能

**リスク3: Issue作成スパム**

- **リスク内容**: 誤った判定により、大量の Issue が作成される
- **対策**:
  - PASS_WITH_ISSUES 判定時のみ Issue を作成
  - 残タスクが0個の場合は Issue を作成しない
  - Issue作成前に確認ログを出力

---

## 9. 非機能要件への対応

### 9.1 パフォーマンス

**NFR-001: 評価レポート生成時間（5分以内）**

- **対策**:
  - Phase 1-8 の成果物を並列読み込み（`concurrent.futures.ThreadPoolExecutor`）
  - Claude Agent SDK の max_turns を 30 に設定（過度に長い評価を防止）
  - 評価プロンプトを最適化（不要な情報を削減）

**NFR-002: GitHub API レート制限の考慮**

- **対策**:
  - Issue 作成は最大1回（PASS_WITH_ISSUES 時のみ）
  - API 呼び出し前にレート制限をチェック（`github.get_rate_limit()`）
  - レート制限超過時は待機（exponential backoff）
  - レート制限残数をログに記録

**実装例**:

```python
def _check_rate_limit(self):
    """GitHub API レート制限をチェック"""
    rate_limit = self.github.github.get_rate_limit()
    remaining = rate_limit.core.remaining

    if remaining < 10:
        reset_time = rate_limit.core.reset
        wait_seconds = (reset_time - datetime.now()).total_seconds()
        print(f"[WARNING] GitHub API rate limit low: {remaining} remaining")
        print(f"[INFO] Waiting {wait_seconds}s until reset...")
        time.sleep(wait_seconds + 1)
```

### 9.2 信頼性

**NFR-003: エラーハンドリング**

- **対策**:
  - すべての外部API呼び出しに try-except ブロックを実装
  - GitHub API エラー: ログに記録し、ワークフロー継続（PASS扱い）
  - Claude Agent SDK エラー: リトライ（最大3回）、失敗時は FAIL
  - ファイルシステムエラー: 例外を raise、ワークフロー停止

**NFR-004: データ整合性の保証**

- **対策**:
  - メタデータの巻き戻し時にデータ整合性を保証
  - 巻き戻し前のバックアップ作成
  - 巻き戻し失敗時のロールバック
  - 成果物ファイルの保護（削除しない）

**実装例**:

```python
def rollback_to_phase(self, phase_name: str) -> Dict[str, Any]:
    """メタデータを指定フェーズに巻き戻し"""
    try:
        # バックアップ作成
        backup_path = self.backup_metadata()

        # 巻き戻し処理
        # ...（巻き戻しロジック）

        # 成功
        return {'success': True, 'backup_path': backup_path}

    except Exception as e:
        # ロールバック（バックアップから復元）
        if backup_path and Path(backup_path).exists():
            shutil.copy(backup_path, self.metadata_path)
            print(f"[INFO] Rolled back to backup: {backup_path}")

        return {'success': False, 'error': str(e)}
```

### 9.3 保守性

**NFR-005: ログ出力**

- **対策**:
  - すべての重要な処理にログ出力を実装
  - ログレベル:
    - INFO: 評価開始、判定結果、Issue作成、巻き戻し実行
    - WARNING: API失敗（リトライ可能）、レート制限接近
    - ERROR: API失敗（リトライ不可）、巻き戻し失敗、ファイルI/Oエラー
  - ログ保存先:
    - `.ai-workflow/issue-{number}/09_evaluation/execute/agent_log_{N}.md`
    - `.ai-workflow/issue-{number}/09_evaluation/execute/agent_log_raw_{N}.txt`

**NFR-006: コーディング規約準拠**

- **対策**:
  - PEP 8 コーディング規約に準拠
  - `flake8` による静的解析
  - 例外:
    - 行長: 最大120文字（プロンプト文字列のみ）

**実装例**:

```python
import logging

# ロガー設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ログハンドラー
handler = logging.FileHandler(self.phase_dir / 'evaluation.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# ログ出力
logger.info("Evaluation phase started")
logger.warning(f"GitHub API rate limit low: {remaining} remaining")
logger.error(f"Failed to create issue: {error}")
```

---

## 10. 実装の順序

### 10.1 推奨実装順序

**Phase 4（実装）**:

1. **メタデータ構造拡張**（優先度: 最高）
   - `metadata.json.template` に `evaluation` フィールドを追加
   - `WorkflowState.migrate()` メソッドを更新

2. **基本インフラ実装**（優先度: 高）
   - `base_phase.py`: `PHASE_NUMBERS` に `'evaluation': '09'` を追加
   - `main.py`: `phase_classes` に `'evaluation': EvaluationPhase` を追加

3. **MetadataManager 拡張**（優先度: 高）
   - `rollback_to_phase()` メソッド実装
   - `get_all_phases_status()` メソッド実装
   - `backup_metadata()` メソッド実装
   - `set_evaluation_decision()` メソッド実装

4. **GitHubClient 拡張**（優先度: 高）
   - `create_issue_from_evaluation()` メソッド実装
   - `close_issue_with_reason()` メソッド実装
   - `close_pull_request()` メソッド実装
   - `get_pull_request_number()` メソッド実装

5. **EvaluationPhase 基本実装**（優先度: 高）
   - クラス定義と初期化
   - `_get_all_phase_outputs()` メソッド実装

6. **evaluate実行ロジック実装**（優先度: 高）
   - `execute()` メソッド実装
   - プロンプトファイル作成（`execute.txt`）

7. **判定ロジック実装**（優先度: 高）
   - `_determine_decision()` メソッド実装
   - `_extract_remaining_tasks()` メソッド実装

8. **判定別処理実装**（優先度: 高）
   - `_handle_pass_with_issues()` メソッド実装
   - `_handle_fail_phase_x()` メソッド実装
   - `_handle_abort()` メソッド実装

9. **レビュー・修正ロジック実装**（優先度: 中）
   - `review()` メソッド実装
   - `revise()` メソッド実装
   - プロンプトファイル作成（`review.txt`, `revise.txt`）

### 10.2 依存関係の考慮

**必須の前提条件**:
1. メタデータ構造拡張 → すべての実装の基盤
2. MetadataManager 拡張 → EvaluationPhase の実装に必要
3. GitHubClient 拡張 → EvaluationPhase の実装に必要

**推奨実装順序の理由**:
- メタデータ構造拡張を最初に実装することで、後続の実装がスムーズになる
- MetadataManager と GitHubClient の拡張を先に実装することで、EvaluationPhase の実装時に依存関係を解決できる
- EvaluationPhase は基本実装（execute）から始め、段階的に機能を追加していく

**並列実行可能なタスク**:
- MetadataManager 拡張と GitHubClient 拡張は並列実行可能
- プロンプトファイルの作成は並列実行可能

### 10.3 ブロッキングポイント

**ブロッカー1: メタデータ構造拡張**
- すべての実装がメタデータ構造に依存
- 先に完了させる必要がある

**ブロッカー2: MetadataManager と GitHubClient の拡張**
- EvaluationPhase の実装に必須
- 先に完了させる必要がある

**ブロッカー3: execute() メソッド実装**
- review() と revise() の実装に必須
- 先に完了させる必要がある

---

## 11. 品質ゲート確認

本設計書は、Phase 2 の品質ゲートを満たしていることを確認します：

- [x] **実装戦略の判断根拠が明記されている**: セクション2で CREATE 戦略の判断根拠を詳細に記載
- [x] **テスト戦略の判断根拠が明記されている**: セクション3で ALL 戦略の判断根拠を詳細に記載
- [x] **テストコード戦略の判断根拠が明記されている**: セクション4で CREATE_TEST 戦略の判断根拠を詳細に記載
- [x] **既存コードへの影響範囲が分析されている**: セクション5で詳細な影響範囲分析を実施
- [x] **変更が必要なファイルがリストアップされている**: セクション6で新規作成・修正・削除ファイルを明記
- [x] **設計が実装可能である**: セクション7で実装可能な詳細設計を記載

---

## 12. まとめ

### プロジェクトの目標

AI Workflow の Phase 1-8 完了後にプロジェクト全体を評価し、次のアクション（PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT）を判定する Project Evaluation フェーズを追加し、プロジェクトマネージャーが成果を総合的に評価できるようにする。

### 主要な設計判断

1. **実装戦略: CREATE**
   - 新規フェーズクラス（`EvaluationPhase`）の作成
   - 既存コードの拡張（`MetadataManager`、`GitHubClient`）
   - 既存の Phase 0-8 には影響を与えない

2. **テスト戦略: ALL**
   - ユニットテスト: 各メソッドのロジック検証
   - インテグレーションテスト: 評価フローの統合検証
   - BDDテスト: ユーザーストーリー検証

3. **テストコード戦略: CREATE_TEST**
   - 新規テストファイルの作成
   - 既存テストファイルへの追加（`MetadataManager`、`GitHubClient`）

### 主要な成果物

1. **新規フェーズクラス**: `scripts/ai-workflow/phases/evaluation.py`
2. **新規プロンプト**: `scripts/ai-workflow/prompts/evaluation/execute.txt`, `review.txt`, `revise.txt`
3. **拡張モジュール**: `metadata_manager.py`, `github_client.py`, `workflow_state.py`
4. **テストコード**:
   - `tests/unit/phases/test_evaluation.py`
   - `tests/integration/test_evaluation_integration.py`
   - `tests/bdd/features/evaluation.feature`
   - `tests/bdd/steps/test_evaluation_steps.py`
5. **テンプレートファイル**: `metadata.json.template`（evaluation フィールド追加）

### 期待される効果

- **品質向上**: プロジェクトマネージャーの視点で成果物を総合評価
- **残タスク管理**: PASS_WITH_ISSUES判定により、追加タスクを自動的にIssue化
- **再実行効率化**: FAIL_PHASE_X判定により、問題のあるフェーズから再実行可能
- **リスク軽減**: ABORT判定により、致命的な問題を早期発見し、無駄な作業を回避

### 次のステップ

Phase 3（テストシナリオ）に進み、Evaluation フェーズの全判定タイプ（PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT）に対するテストシナリオを作成します。

---

**作成日**: 2025-10-12
**設計者**: Claude AI (Phase 2 - Design)
**実装戦略**: CREATE
**テスト戦略**: ALL
**テストコード戦略**: CREATE_TEST
**見積もり総工数**: 約18時間（Planning Document より）
**リスクレベル**: 高
**優先度**: 高
