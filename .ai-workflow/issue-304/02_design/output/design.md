# 詳細設計書: AI駆動開発自動化ワークフローMVP v1.0.0

## ドキュメント情報
- **Issue番号**: #304
- **バージョン**: v1.0.0 (MVP)
- **作成日**: 2025-10-09
- **ステータス**: Phase 2 - 詳細設計
- **前提ドキュメント**: [要件定義書](./../01_requirements/output/requirements.md)

---

## 1. アーキテクチャ設計

### 1.1 システム全体像

```
┌─────────────────────────────────────────────────────────────┐
│                    外部システム                                │
├─────────────────────────────────────────────────────────────┤
│  GitHub API                                                 │
│  - Issue情報取得                                             │
│  - PR作成（将来）                                            │
│  - コメント投稿                                              │
│                                                              │
│  Claude Agent SDK                                            │
│  - 要件定義書生成                                            │
│  - 設計書生成                                                │
│  - テストシナリオ生成                                        │
│  - コード実装（将来）                                        │
│  - テスト実行（将来）                                        │
│  - ドキュメント生成（将来）                                  │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ API Call
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     CLIインターフェース                        │
│                    (main.py - Click)                         │
├─────────────────────────────────────────────────────────────┤
│  コマンド:                                                   │
│  - init: ワークフロー初期化                                  │
│  - execute: フェーズ実行                                     │
│  - review: フェーズレビュー                                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    コアモジュール (core/)                      │
├─────────────────────────────────────────────────────────────┤
│  WorkflowState                                               │
│  - metadata.json の読み書き                                  │
│  - フェーズステータス管理                                    │
│  - タイムスタンプ管理                                        │
│                                                              │
│  MetadataManager                                             │
│  - WorkflowStateのラッパー                                   │
│  - Phase実装向けインターフェース                              │
│  - コストトラッキング                                        │
│                                                              │
│  ClaudeAgentClient                                           │
│  - Claude Agent SDK呼び出し                                  │
│  - プロンプト実行                                            │
│  - レスポンス取得                                            │
│                                                              │
│  GitHubClient                                                │
│  - GitHub API呼び出し                                        │
│  - Issue情報取得                                             │
│  - コメント投稿                                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  フェーズ実装 (phases/)                        │
├─────────────────────────────────────────────────────────────┤
│  BasePhase (抽象基底クラス)                                   │
│  ├─ execute() - フェーズ実行                                 │
│  ├─ review() - フェーズレビュー                              │
│  ├─ revise() - 修正実行                                      │
│  └─ run() - 実行・レビュー・リトライループ                   │
│                                                              │
│  RequirementsPhase (Phase 1)                                 │
│  - Issue情報から要件定義書を生成                              │
│  - クリティカルシンキングレビュー                            │
│  - 修正（リトライ最大3回）                                   │
│                                                              │
│  DesignPhase (Phase 2) ※MVP実装対象                          │
│  - 要件定義書から詳細設計書を生成                             │
│  - 実装戦略・テスト戦略・テストコード戦略の判断               │
│  - クリティカルシンキングレビュー                            │
│  - 修正（リトライ最大3回）                                   │
│                                                              │
│  TestScenarioPhase (Phase 3) ※将来実装                        │
│  - 設計書からテストシナリオを生成                             │
│                                                              │
│  ImplementationPhase (Phase 4) ※将来実装                      │
│  - 設計書に基づいてコード実装                                │
│                                                              │
│  TestingPhase (Phase 5) ※将来実装                             │
│  - テストシナリオに基づいてテスト実行                         │
│                                                              │
│  DocumentationPhase (Phase 6) ※将来実装                       │
│  - 実装結果をドキュメント化                                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    永続化層                                    │
├─────────────────────────────────────────────────────────────┤
│  .ai-workflow/issue-{number}/                                │
│  ├─ metadata.json                                            │
│  ├─ 01_requirements/                                         │
│  │   ├─ output/requirements.md                               │
│  │   ├─ execute/                                             │
│  │   ├─ review/                                              │
│  │   └─ revise/                                              │
│  ├─ 02_design/                                               │
│  │   ├─ output/design.md                                     │
│  │   ├─ execute/                                             │
│  │   ├─ review/                                              │
│  │   └─ revise/                                              │
│  ├─ 03_test_scenario/                                        │
│  ├─ 04_implementation/                                       │
│  ├─ 05_testing/                                              │
│  └─ 06_documentation/                                        │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 コンポーネント間の関係

```
main.py
  ├─ WorkflowState.create_new() (init時)
  └─ {Phase}.run() (execute時)
      ├─ execute()
      │   └─ ClaudeAgentClient.execute_task_sync()
      ├─ review()
      │   └─ ClaudeAgentClient.execute_task_sync()
      └─ revise() (FAIL時)
          └─ ClaudeAgentClient.execute_task_sync()
```

### 1.3 データフロー

```
1. ワークフロー初期化
   GitHub Issue URL
      ↓
   main.py init
      ↓
   WorkflowState.create_new()
      ↓
   .ai-workflow/issue-{number}/metadata.json

2. フェーズ実行
   metadata.json
      ↓
   Phase.execute()
      ↓
   Claude Agent SDK
      ↓
   成果物（design.md等）
      ↓
   metadata.json更新（コスト・ステータス）

3. レビュー
   成果物（design.md等）
      ↓
   Phase.review()
      ↓
   Claude Agent SDK
      ↓
   レビュー結果（PASS/FAIL）
      ↓
   GitHub Issue コメント投稿

4. リトライ
   レビュー結果（FAIL）
      ↓
   Phase.revise()
      ↓
   Claude Agent SDK
      ↓
   修正版成果物
      ↓
   Phase.review() (再実行)
```

---

## 2. 実装戦略判断

### 実装戦略: **EXTEND（拡張）**

**判断根拠**:
1. **既存コードベースの存在**: `scripts/ai-workflow/` 配下に、ワークフロー基盤（CLI、状態管理、Claude Agent SDK連携、GitHub連携、Phase基底クラス、Phase 1実装）が既に存在する
2. **既存パターンの踏襲**: Phase 1（RequirementsPhase）と同様の実装パターンで Phase 2（DesignPhase）を実装することで、コードの一貫性を保ちつつ拡張が可能
3. **既存ファイルへの影響が限定的**: 主に新規ファイルの追加と、一部既存ファイル（Jenkinsfile、BDDテスト）の更新のみで実現可能
4. **既存機能との統合**: 既存の `BasePhase`、`MetadataManager`、`ClaudeAgentClient`、`GitHubClient` を再利用し、既存の実行フローに Phase 2 を統合する

**既存コードとの関係**:
- **再利用**: `BasePhase`、`MetadataManager`、`ClaudeAgentClient`、`GitHubClient`
- **新規作成**: Phase 2 実装（`phases/design.py`）、Phase 2 プロンプトファイル（3種類）、Phase 2 E2Eテスト
- **修正**: Jenkinsfile（Phase 2ステージの実装）、BDDテスト（Phase 2シナリオ追加）

---

## 3. テスト戦略判断

### テスト戦略: **UNIT_BDD**

**判断根拠**:
1. **BDDテスト（必須）**: 既存のBDD featureファイル（`tests/features/workflow.feature`）が存在し、ワークフロー全体の振る舞いをGherkin形式で定義しているため、Phase 2のシナリオを追加する
2. **Unitテスト（推奨）**: Phase 2のロジック（特に、実装戦略・テスト戦略・テストコード戦略のパース処理）は独立した機能であり、単体テストで検証可能
3. **Integrationテストは不要**: Phase 1と同様、E2EテストがPhase実行全体（execute → review → revise）をカバーするため、個別のIntegrationテストは冗長

**テストレベル別の目的**:
- **Unit**: `DesignPhase._parse_review_result()`, `DesignPhase._parse_design_decisions()` 等の内部ロジック検証
- **BDD**: ワークフロー全体の振る舞い検証（Given-When-Then形式）
- **E2E**: Phase 2の実行→レビュー→修正の完全なフロー検証（Docker環境内）

---

## 4. テストコード戦略判断

### テストコード戦略: **EXTEND_TEST（既存テストの拡張）**

**判断根拠**:
1. **既存BDDテストの拡張**: `tests/features/workflow.feature` に Phase 2 のシナリオを追加（Phase 1 と同じファイル内）
2. **既存E2Eテストパターンの踏襲**: `tests/e2e/test_phase1.py` と同様のパターンで `tests/e2e/test_phase2.py` を**新規作成**
3. **既存Unitテストパターンの踏襲**: `tests/unit/phases/` ディレクトリ内に `test_design_phase.py` を**新規作成**

**ファイル配置**:
- **拡張**: `tests/features/workflow.feature`（Phase 2シナリオ追加）
- **新規作成**:
  - `tests/e2e/test_phase2.py`
  - `tests/unit/phases/test_design_phase.py`

---

## 5. 影響範囲分析

### 5.1 既存コードへの影響

| コンポーネント | 影響レベル | 変更内容 |
|--------------|----------|---------|
| `core/workflow_state.py` | **なし** | 変更不要（Phase 2用のステータス管理は既に実装済み） |
| `core/metadata_manager.py` | **なし** | 変更不要（設計判断記録機能は既に実装済み） |
| `core/claude_agent_client.py` | **なし** | 変更不要（Phase 2でも再利用） |
| `core/github_client.py` | **なし** | 変更不要（Phase 2でも再利用） |
| `phases/base_phase.py` | **なし** | 変更不要（Phase 2でも継承して使用） |
| `phases/requirements.py` | **なし** | 変更不要（Phase 1実装はそのまま） |
| `main.py` | **なし** | 変更不要（`DesignPhase`は既にimportリストに含まれている） |
| `jenkins/jobs/pipeline/.../Jenkinsfile` | **小** | Phase 2ステージの実装（現在は未実装メッセージのみ） |
| `tests/features/workflow.feature` | **小** | Phase 2シナリオの追加 |

### 5.2 依存関係の変更

**新規依存関係**: なし（既存パッケージのみ使用）

**既存依存関係**: 変更なし

### 5.3 マイグレーション要否

**マイグレーション不要**

理由:
- `metadata.json` のスキーマは変更なし（Phase 2のフィールドは既に存在）
- データベース未使用（ファイルベース）

---

## 6. 変更・追加ファイルリスト

### 6.1 新規作成ファイル

| ファイルパス | 説明 |
|------------|------|
| `scripts/ai-workflow/phases/design.py` | Phase 2（詳細設計）の実装 |
| `scripts/ai-workflow/prompts/design/execute.txt` | Phase 2実行プロンプト |
| `scripts/ai-workflow/prompts/design/review.txt` | Phase 2レビュープロンプト |
| `scripts/ai-workflow/prompts/design/revise.txt` | Phase 2修正プロンプト |
| `scripts/ai-workflow/tests/e2e/test_phase2.py` | Phase 2 E2Eテスト |
| `scripts/ai-workflow/tests/unit/phases/test_design_phase.py` | Phase 2 Unitテスト |

### 6.2 修正が必要な既存ファイル

| ファイルパス | 変更内容 |
|------------|---------|
| `jenkins/jobs/pipeline/ai-workflow/ai-workflow-orchestrator/Jenkinsfile` | Phase 2ステージの実装（`python main.py execute --phase design --issue ${env.ISSUE_NUMBER}` を実行） |
| `scripts/ai-workflow/tests/features/workflow.feature` | Phase 2シナリオの追加（Gherkin形式） |

### 6.3 削除が必要なファイル

**なし**

---

## 7. 詳細設計

### 7.1 クラス設計

#### 7.1.1 DesignPhase

**継承**: `BasePhase`

**責務**:
- 要件定義書から詳細設計書を生成
- 実装戦略・テスト戦略・テストコード戦略の判断
- 設計書のクリティカルシンキングレビュー
- レビュー結果に基づく修正（リトライ）

**主要メソッド**:

```python
class DesignPhase(BasePhase):
    """Phase 2: 詳細設計フェーズ"""

    def __init__(self, *args, **kwargs):
        """初期化（phase_name='design'）"""
        super().__init__(phase_name='design', *args, **kwargs)

    def execute(self) -> Dict[str, Any]:
        """
        詳細設計フェーズを実行

        Returns:
            Dict[str, Any]:
                - success: bool
                - output: str - design.mdのパス
                - error: Optional[str]

        処理フロー:
            1. 要件定義書を読み込み
            2. 実行プロンプトに埋め込み
            3. Claude Agent SDKで設計書を生成
            4. design.mdの存在確認
            5. metadata.jsonに設計判断を記録
        """
        pass

    def review(self) -> Dict[str, Any]:
        """
        設計書をレビュー

        Returns:
            Dict[str, Any]:
                - result: str - PASS/PASS_WITH_SUGGESTIONS/FAIL
                - feedback: str
                - suggestions: List[str]

        処理フロー:
            1. design.mdを読み込み
            2. レビュープロンプトに埋め込み（@記法）
            3. Claude Agent SDKでレビュー実行
            4. レビュー結果をパース
            5. review/result.mdに保存
        """
        pass

    def revise(self, review_feedback: str) -> Dict[str, Any]:
        """
        レビュー結果を元に設計書を修正

        Args:
            review_feedback: レビュー結果のフィードバック

        Returns:
            Dict[str, Any]:
                - success: bool
                - output: str - design.mdのパス
                - error: Optional[str]

        処理フロー:
            1. 要件定義書と元の設計書を読み込み
            2. 修正プロンプトに埋め込み
            3. Claude Agent SDKで修正版を生成
            4. design.mdを上書き
        """
        pass

    def _parse_review_result(self, messages: List[str]) -> Dict[str, Any]:
        """
        レビュー結果メッセージから判定とフィードバックを抽出

        Args:
            messages: Claude Agent SDKからのレスポンスメッセージ

        Returns:
            Dict[str, Any]:
                - result: str (PASS/PASS_WITH_SUGGESTIONS/FAIL)
                - feedback: str
                - suggestions: List[str]

        処理ロジック:
            - AssistantMessageからTextBlock部分を抽出
            - 正規表現で「**判定: PASS**」等を検索
            - 全テキストをfeedbackとして保存
        """
        pass

    def _parse_design_decisions(self, design_md_content: str) -> Dict[str, str]:
        """
        設計書から3つの戦略判断を抽出してmetadata.jsonに記録

        Args:
            design_md_content: design.mdの内容

        Returns:
            Dict[str, str]:
                - implementation_strategy: CREATE/EXTEND/REFACTOR
                - test_strategy: UNIT_ONLY/INTEGRATION_ONLY/BDD_ONLY/UNIT_INTEGRATION/UNIT_BDD/INTEGRATION_BDD/ALL
                - test_code_strategy: EXTEND_TEST/CREATE_TEST/BOTH_TEST

        処理ロジック:
            - 正規表現で「### 実装戦略: CREATE」等を検索
            - metadata.design_decisionsに記録
        """
        pass
```

### 7.2 関数設計

#### 7.2.1 主要関数（DesignPhase内）

**execute()**

```
入力:
  - self.metadata.data['issue_number']（Issue番号）
  - 要件定義書（.ai-workflow/issue-{number}/01_requirements/output/requirements.md）
  - 実行プロンプト（prompts/design/execute.txt）

処理:
  1. 要件定義書を読み込み
  2. プロンプトテンプレートに埋め込み
  3. Claude Agent SDK実行
  4. design.mdの存在確認
  5. 設計判断をパースしてmetadata.jsonに記録

出力:
  - design.md（.ai-workflow/issue-{number}/02_design/output/design.md）
  - metadata.json更新（design_decisions）
  - 実行ログ（execute/prompt.txt, execute/agent_log.md）
```

**review()**

```
入力:
  - design.md（.ai-workflow/issue-{number}/02_design/output/design.md）
  - レビュープロンプト（prompts/design/review.txt）

処理:
  1. design.mdを読み込み
  2. プロンプトテンプレートに@記法で埋め込み
  3. Claude Agent SDK実行
  4. レビュー結果をパース
  5. レビュー結果をファイル保存

出力:
  - レビュー結果（PASS/PASS_WITH_SUGGESTIONS/FAIL）
  - レビューログ（review/result.md, review/agent_log.md）
```

**revise()**

```
入力:
  - review_feedback（レビュー結果のフィードバック）
  - 要件定義書（requirements.md）
  - 元の設計書（design.md）
  - 修正プロンプト（prompts/design/revise.txt）

処理:
  1. 要件定義書と元の設計書を読み込み
  2. プロンプトテンプレートにフィードバックと@記法で埋め込み
  3. Claude Agent SDK実行
  4. design.mdを上書き

出力:
  - 修正版 design.md
  - 修正ログ（revise/prompt.txt, revise/agent_log.md）
```

### 7.3 データ構造設計

#### 7.3.1 metadata.json（Phase 2関連フィールド）

```json
{
  "design_decisions": {
    "implementation_strategy": "EXTEND",
    "test_strategy": "UNIT_BDD",
    "test_code_strategy": "EXTEND_TEST"
  },
  "phases": {
    "design": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-09T03:00:00.000000Z",
      "completed_at": "2025-10-09T03:05:00.000000Z",
      "review_result": "PASS",
      "output_files": ["02_design/output/design.md"]
    }
  }
}
```

#### 7.3.2 design.md（出力形式）

```markdown
# 詳細設計書: {タイトル}

## ドキュメント情報
- Issue番号: #{number}
- バージョン: v1.0.0
- 作成日: YYYY-MM-DD
- ステータス: Phase 2 - 詳細設計

---

## 1. アーキテクチャ設計
（システム全体図、コンポーネント間の関係、データフロー）

---

## 2. 実装戦略判断

### 実装戦略: CREATE / EXTEND / REFACTOR

**判断根拠**:
- （理由1）
- （理由2）

---

## 3. テスト戦略判断

### テスト戦略: UNIT_ONLY / INTEGRATION_ONLY / BDD_ONLY / UNIT_INTEGRATION / UNIT_BDD / INTEGRATION_BDD / ALL

**判断根拠**:
- （理由1）
- （理由2）

---

## 4. テストコード戦略判断

### テストコード戦略: EXTEND_TEST / CREATE_TEST / BOTH_TEST

**判断根拠**:
- （理由1）
- （理由2）

---

## 5. 影響範囲分析
（既存コードへの影響、依存関係の変更、マイグレーション要否）

---

## 6. 変更・追加ファイルリスト
（新規作成ファイル、修正が必要な既存ファイル、削除が必要なファイル）

---

## 7. 詳細設計
（クラス設計、関数設計、データ構造設計、インターフェース設計）

---

## 8. セキュリティ考慮事項
（認証・認可、データ保護、セキュリティリスクと対策）

---

## 9. 非機能要件への対応
（パフォーマンス、スケーラビリティ、保守性）

---

## 10. 実装の順序
（実装順序の推奨、依存関係の考慮）
```

### 7.4 インターフェース設計

#### 7.4.1 CLI（main.py）

**既存**: `python main.py execute --phase design --issue 304`

**変更なし**（既に実装済み）

#### 7.4.2 Jenkinsパイプライン

**変更箇所**: `jenkins/jobs/pipeline/ai-workflow/ai-workflow-orchestrator/Jenkinsfile`

```groovy
stage('Phase 2: Design') {
    steps {
        script {
            echo "========================================="
            echo "Stage: Phase 2 - Detailed Design"
            echo "========================================="

            // MVP v1.0.0では未実装 → 実装に変更
            dir(env.WORKFLOW_DIR) {
                sh """
                    ${env.PYTHON_PATH} main.py execute --phase design --issue ${env.ISSUE_NUMBER}
                """

                if (!params.SKIP_REVIEW) {
                    sh """
                        ${env.PYTHON_PATH} main.py review --phase design --issue ${env.ISSUE_NUMBER}
                    """
                }
            }
        }
    }
}
```

---

## 8. セキュリティ考慮事項

### 8.1 認証・認可

| 項目 | 対策 | 実装箇所 |
|-----|------|---------|
| **GitHub API認証** | Personal Access Token（環境変数 `GITHUB_TOKEN`） | `core/github_client.py` |
| **Claude API認証** | API Key（環境変数 `ANTHROPIC_API_KEY`） | `core/claude_agent_client.py` |
| **Jenkins認証** | Jenkinsクレデンシャルストア | `Jenkinsfile` (credentials('github-token')) |

### 8.2 データ保護

| 項目 | リスク | 対策 |
|-----|-------|------|
| **metadata.json** | 機密情報の記録 | Issue情報のみ記録（パスワード・キー等は含めない） |
| **プロンプトログ** | 機密情報の露出 | GitHub Token等はマスク（`***`）、Issue本文は記録OK |
| **設計書** | コードベース情報の露出 | Gitリポジトリ内に保存（プライベートリポジトリ推奨） |

### 8.3 セキュリティリスクと対策

| リスク | 影響 | 対策 |
|-------|-----|------|
| **APIキーの漏洩** | 高 | 環境変数管理、Jenkinsクレデンシャルストア使用、ハードコーディング禁止 |
| **コストの過剰消費** | 中 | metadata.jsonでコストトラッキング、上限設定（`config.yaml`） |
| **無限ループ** | 中 | リトライ回数上限（3回）、タイムアウト設定（Jenkinsfile: 30分） |

---

## 9. 非機能要件への対応

### 9.1 パフォーマンス

| 要件ID | 要件 | 対応 | 実装箇所 |
|-------|-----|------|---------|
| **NFR-001** | ワークフロー初期化は5秒以内 | ディレクトリ作成とJSON書き込みのみ | `WorkflowState.create_new()` |
| **NFR-002** | metadata.json読み書きは1秒以内 | ファイルI/O最適化（小サイズ） | `WorkflowState.save()` |
| **NFR-003** | BDDテスト実行時間は5分以内 | E2Eテストは並列化可能 | `pytest -n auto` |

### 9.2 スケーラビリティ

| 項目 | 対応 |
|-----|------|
| **複数Issue同時実行** | 将来対応（MVP v1.0.0ではサポート外） |
| **フェーズの追加** | BasePhaseを継承して新規Phaseを追加可能 |
| **プロンプトのカスタマイズ** | `prompts/{phase_name}/` ディレクトリ内のテキストファイルを編集 |

### 9.3 保守性

| 項目 | 対応 |
|-----|------|
| **コーディング規約** | PEP 8準拠、日本語コメント（CLAUDE.md） |
| **モジュラー設計** | BasePhase基底クラス、各Phaseは独立したモジュール |
| **テスタビリティ** | Unit/BDD/E2Eテストでカバレッジ80%以上 |
| **ドキュメント** | 各Phaseに対応するREADME、プロンプトファイルにコメント |

---

## 10. 実装の順序

### 10.1 推奨実装順序

```
ステップ1: Phase 2実装（コア機能）
  ├─ 1-1. phases/design.py作成
  ├─ 1-2. prompts/design/execute.txt作成
  ├─ 1-3. prompts/design/review.txt作成
  └─ 1-4. prompts/design/revise.txt作成

ステップ2: Unitテスト作成
  └─ 2-1. tests/unit/phases/test_design_phase.py作成

ステップ3: E2Eテスト作成
  └─ 3-1. tests/e2e/test_phase2.py作成

ステップ4: BDDテスト拡張
  └─ 4-1. tests/features/workflow.feature更新（Phase 2シナリオ追加）

ステップ5: Jenkins統合
  └─ 5-1. Jenkinsfile更新（Phase 2ステージ実装）

ステップ6: 動作確認
  ├─ 6-1. CLIでPhase 2実行（python main.py execute --phase design --issue 304）
  ├─ 6-2. Unitテスト実行（pytest tests/unit/phases/test_design_phase.py）
  ├─ 6-3. E2Eテスト実行（pytest tests/e2e/test_phase2.py）
  ├─ 6-4. BDDテスト実行（behave tests/features/）
  └─ 6-5. Jenkinsパイプライン実行
```

### 10.2 依存関係の考慮

```
ステップ1（Phase 2実装） → ステップ2（Unitテスト） → ステップ3（E2Eテスト）
                              ↓
                        ステップ4（BDDテスト）
                              ↓
                        ステップ5（Jenkins統合）
                              ↓
                        ステップ6（動作確認）
```

**重要な注意事項**:
- **ステップ1完了後**: Phase 2の基本機能が動作することを確認（手動実行）
- **ステップ2-4完了後**: テストがすべてパスすることを確認
- **ステップ5完了後**: Jenkinsパイプラインが正常に実行されることを確認

---

## 11. 品質ゲート（Phase 2）

この設計書は以下の品質ゲートを満たしています：

- ✅ **実装戦略の判断根拠が明記されている**: EXTEND戦略を選択（既存コード拡張）
- ✅ **テスト戦略の判断根拠が明記されている**: UNIT_BDD戦略を選択（UnitテストとBDDテスト）
- ✅ **既存コードへの影響範囲が分析されている**: 影響範囲分析（5.1節）で既存コードへの影響を明記
- ✅ **変更が必要なファイルがリストアップされている**: 変更・追加ファイルリスト（6節）で明記
- ✅ **設計が実装可能である**: クラス設計・関数設計・データ構造設計が具体的に記載されている

---

## 12. 補足情報

### 12.1 Phase 1との違い

| 項目 | Phase 1（RequirementsPhase） | Phase 2（DesignPhase） |
|-----|----------------------------|----------------------|
| **入力** | GitHub Issue情報 | 要件定義書（requirements.md） |
| **出力** | 要件定義書（requirements.md） | 詳細設計書（design.md） |
| **特殊処理** | Issue情報のフォーマット | 3つの戦略判断のパースとmetadata.json記録 |
| **プロンプト** | Issue内容を埋め込み | 要件定義書を@記法で参照 |

### 12.2 将来の拡張ポイント

1. **Phase 3-6の実装**: Phase 2と同様のパターンで実装可能
2. **PR自動作成**: GitHub APIを使用してPR作成機能を追加
3. **並列実行**: 複数Issueの同時処理をサポート
4. **カスタムフェーズ**: BasePhaseを継承して独自フェーズを追加
5. **ダッシュボードUI**: Webダッシュボードでワークフロー状況を可視化

### 12.3 参考ドキュメント

- [要件定義書](/workspace/.ai-workflow/issue-304/01_requirements/output/requirements.md)
- [CLAUDE.md](/workspace/CLAUDE.md)
- [ARCHITECTURE.md](/workspace/ARCHITECTURE.md)
- [CONTRIBUTION.md](/workspace/CONTRIBUTION.md)
- [scripts/ai-workflow/README.md](/workspace/scripts/ai-workflow/README.md)
- [scripts/ai-workflow/ARCHITECTURE.md](/workspace/scripts/ai-workflow/ARCHITECTURE.md)

---

**End of Document**
