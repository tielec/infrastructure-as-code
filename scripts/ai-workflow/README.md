# AI駆動開発自動化ワークフロー

GitHub IssueからPR作成まで、Claude AIが自動的に要件定義・設計・実装・テストを実行するワークフローシステムです。

## 概要

このプロジェクトは、Claude APIを活用してソフトウェア開発プロセスを自動化します：

```
GitHub Issue → 要件定義 → 詳細設計 → テストシナリオ → 実装 → テスト → ドキュメント → PR作成
```

各フェーズでAIレビューを実施し、品質を担保しながら自動で開発を進めます。

## 現在の実装状況（MVP v1.0.0）

**実装完了機能**:
- ✅ ワークフロー初期化（`init`コマンド）
- ✅ メタデータ管理（metadata.json）
- ✅ フェーズ状態管理（6フェーズ対応）
- ✅ BDDテスト基盤

**未実装機能**（今後の拡張）:
- ⏳ Phase 1-6の自動実行
- ⏳ Claude API統合
- ⏳ Git操作（ブランチ作成、コミット、PR作成）
- ⏳ AIレビュー機能

## クイックスタート

### 前提条件

- Python 3.10以上
- pip
- Git
- PowerShellまたはコマンドプロンプト（Windows）

### インストール

```powershell
# 1. リポジトリのクローン（既にクローン済みの場合はスキップ）
cd C:\Users\ytaka\TIELEC\development\infrastructure-as-code

# 2. ai-workflowディレクトリに移動
cd scripts\ai-workflow

# 3. 依存パッケージのインストール
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### 基本的な使い方

#### 1. ワークフロー初期化

```powershell
python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/123
```

**実行結果**:
```
✓ Workflow initialized: .ai-workflow\issue-123
✓ metadata.json created
```

#### 2. 生成されたファイル確認

```powershell
# ワークフローディレクトリの確認
dir ..\..\..\.ai-workflow\issue-123

# metadata.jsonの内容確認
type ..\..\..\.ai-workflow\issue-123\metadata.json
```

**metadata.json の内容例**:
```json
{
  "issue_number": "123",
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/123",
  "issue_title": "Issue #123",
  "workflow_version": "1.0.0",
  "current_phase": "requirements",
  "design_decisions": {
    "implementation_strategy": null,
    "test_strategy": null,
    "test_code_strategy": null
  },
  "cost_tracking": {
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_cost_usd": 0.0
  },
  "phases": {
    "requirements": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    },
    "design": { "status": "pending", ... },
    "test_scenario": { "status": "pending", ... },
    "implementation": { "status": "pending", ... },
    "testing": { "status": "pending", ... },
    "documentation": { "status": "pending", ... }
  },
  "created_at": "2025-10-07T12:34:56.789Z",
  "updated_at": "2025-10-07T12:34:56.789Z"
}
```

#### 3. BDDテスト実行

```powershell
# テストの実行
behave tests/features/workflow.feature

# カバレッジ付きテスト（オプション）
pytest --cov=core --cov-report=html tests/
```

**期待される出力**:
```
Feature: AI駆動開発自動化ワークフロー

  Scenario: ワークフロー初期化とメタデータ作成
    前提 作業ディレクトリが "..." である               passed
    もし 開発者がワークフローを初期化する               passed
    ならば ワークフローディレクトリ "..." が作成される    passed
    かつ "metadata.json" ファイルが存在する             passed
    かつ metadata.json に以下の情報が含まれる           passed
    かつ すべてのフェーズのステータスが "pending" である passed

1 scenario (1 passed)
6 steps (6 passed)
```

## CLIコマンドリファレンス

### `init` - ワークフロー初期化

GitHub IssueからAIワークフローを初期化します。

```powershell
python main.py init --issue-url <ISSUE_URL>
```

**オプション**:
- `--issue-url` (必須): GitHub Issue URL

**例**:
```powershell
python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/999
```

### `execute` - フェーズ実行（未実装）

指定したフェーズを実行します。

```powershell
python main.py execute --phase <PHASE_NAME> --issue <ISSUE_NUMBER>
```

**オプション**:
- `--phase` (必須): フェーズ名（requirements, design, test_scenario, implementation, testing, documentation）
- `--issue` (必須): Issue番号

**例**:
```powershell
python main.py execute --phase requirements --issue 999
```

**注意**: MVP版では状態更新のみ実装。Phase 1-6の実装は今後の拡張で追加予定。

### `review` - レビュー実行（未実装）

指定したフェーズをAIレビューします。

```powershell
python main.py review --phase <PHASE_NAME> --issue <ISSUE_NUMBER>
```

**オプション**:
- `--phase` (必須): フェーズ名
- `--issue` (必須): Issue番号

**例**:
```powershell
python main.py review --phase requirements --issue 999
```

## プロジェクト構成

```
scripts/ai-workflow/
├── main.py                    # CLIエントリーポイント
├── config.yaml                # 設定ファイル
├── requirements.txt           # 本番依存パッケージ
├── requirements-test.txt      # テスト依存パッケージ
├── core/                      # コアモジュール
│   ├── __init__.py
│   ├── workflow_state.py      # metadata.json管理
│   ├── claude_client.py       # Claude API（未実装）
│   ├── git_operations.py      # Git操作（未実装）
│   └── context_manager.py     # コンテキスト管理（未実装）
├── phases/                    # フェーズ実装（未実装）
│   ├── base_phase.py
│   ├── requirements.py
│   ├── design.py
│   ├── test_scenario.py
│   ├── implementation.py
│   ├── testing.py
│   └── documentation.py
├── reviewers/                 # レビューエンジン（未実装）
│   └── critical_thinking.py
├── prompts/                   # プロンプトテンプレート（未実装）
│   ├── requirements/
│   ├── design/
│   └── ...
└── tests/                     # テストコード
    └── features/
        ├── workflow.feature
        └── steps/
            └── workflow_steps.py
```

## 設定ファイル

### config.yaml

ワークフローの動作設定を定義します。

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

## 開発ドキュメント

詳細な設計・実装情報は以下のドキュメントを参照してください：

- **[ai-workflow-requirements.md](../../ai-workflow-requirements.md)**: 要件定義書（v1.2.0）
- **[ai-workflow-design.md](../../ai-workflow-design.md)**: 詳細設計書（v1.0.0）
- **[ai-workflow-test-scenario.md](../../ai-workflow-test-scenario.md)**: BDDテストシナリオ（v2.0.0）
- **[04-implementation.md](../../04-implementation.md)**: 実装ログ
- **[05-testing.md](../../05-testing.md)**: テスト実行ログ
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: アーキテクチャドキュメント
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**: トラブルシューティング
- **[ROADMAP.md](ROADMAP.md)**: 今後の拡張計画

## トラブルシューティング

よくある問題と解決方法は [TROUBLESHOOTING.md](TROUBLESHOOTING.md) を参照してください。

## 今後の拡張計画

今後の開発ロードマップは [ROADMAP.md](ROADMAP.md) を参照してください。

## ライセンス

このプロジェクトは infrastructure-as-code リポジトリの一部です。

## 貢献

バグ報告や機能要望は GitHub Issue で受け付けています。

---

**バージョン**: 1.0.0 (MVP)
**最終更新**: 2025-10-07
