# AI駆動開発自動化ワークフロー

Claude Agent SDKを使った7フェーズの自動開発ワークフロー

## 概要

このツールは、GitHubのIssueからプロジェクト計画、要件定義、設計、テスト、実装、ドキュメント作成までを自動化します。

### 主な特徴

- **Claude Pro Max活用**: Claude Code headless modeで自律的にタスクを実行
- **8フェーズワークフロー**: Phase 0（プロジェクト計画） → Phase 1（要件定義） → Phase 2（設計） → Phase 3（テストシナリオ） → Phase 4（実装） → Phase 5（テスト） → Phase 6（ドキュメント） → Phase 7（レポート）
- **Phase 0 (Planning)**: プロジェクトマネージャとして実装戦略・テスト戦略を事前決定し、後続フェーズの効率を最大化
  - Jenkins統合: START_PHASEパラメータで`planning`を選択可能（デフォルト値）
  - 全Phase連携: Planning Documentが後続の全Phase（Requirements～Report）で自動参照される
  - Planning Phaseスキップ可能: 後方互換性を維持（警告ログのみ出力）
- **クリティカルシンキングレビュー**: 各フェーズで品質チェック（最大3回リトライ）
- **execute()自動リトライ**: execute()失敗時も自動的にrevise()による修正を試行し、一時的なエラーからの回復が可能
- **GitHub統合**: Issue情報の取得、進捗報告、レビュー結果の投稿
- **Docker対応**: Linux環境で安定動作

## システム要件

### 必須
- Docker Desktop
- Claude Pro/Max契約
- GitHub Personal Access Token

### 推奨
- Git 2.0+
- Python 3.11+ (ローカル開発時)
- Node.js 20+ (ローカル開発時)

## クイックスタート

### 1. 環境変数の設定

```bash
# Claude Code OAuth Token（~/.claude/.credentials.jsonから抽出）
export CLAUDE_CODE_OAUTH_TOKEN="sk-ant-oat01-..."

# GitHub Personal Access Token
export GITHUB_TOKEN="ghp_..."

# GitHubリポジトリ名
export GITHUB_REPOSITORY="tielec/infrastructure-as-code"
```

**OAuth Token取得方法**: [DOCKER_AUTH_SETUP.md](DOCKER_AUTH_SETUP.md) を参照

**GitHub Token作成方法**:
1. GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token (classic)
3. Scopes: `repo` (Full control of private repositories)
4. トークンをコピーして`GITHUB_TOKEN`に設定

### 2. ワークフロー初期化

```bash
# リポジトリルートに移動
cd C:\Users\ytaka\TIELEC\development\infrastructure-as-code

# Issue URLを指定してワークフロー初期化
docker run --rm \
  -v "$(pwd):/workspace" \
  -w /workspace/scripts/ai-workflow \
  ai-workflow:v1.1.0 \
  python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/304
```

### 3. Phase 0（プロジェクト計画）実行（推奨）

```bash
# Phase 0を実行して事前に実装戦略を決定
docker run --rm \
  -e CLAUDE_CODE_OAUTH_TOKEN="${CLAUDE_CODE_OAUTH_TOKEN}" \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  -e GITHUB_REPOSITORY="${GITHUB_REPOSITORY}" \
  -v "$(pwd):/workspace" \
  -w /workspace/scripts/ai-workflow \
  ai-workflow:v1.1.0 \
  python main.py execute --phase planning --issue 304
```

### 4. Phase 1（要件定義）実行

```bash
# Phase 1を実行
docker run --rm \
  -e CLAUDE_CODE_OAUTH_TOKEN="${CLAUDE_CODE_OAUTH_TOKEN}" \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  -e GITHUB_REPOSITORY="${GITHUB_REPOSITORY}" \
  -v "$(pwd):/workspace" \
  -w /workspace/scripts/ai-workflow \
  ai-workflow:v1.1.0 \
  python main.py execute --phase requirements --issue 304
```

### 5. 結果確認

**Phase 0（プロジェクト計画）の成果物**:
- **プロジェクト計画書**: `.ai-workflow/issue-304/00_planning/output/planning.md`
  - Issue分析（複雑度、見積もり工数、リスク評価）
  - 実装戦略判断（CREATE/EXTEND/REFACTOR）
  - テスト戦略判断（UNIT_ONLY/.../ALL）
  - テストコード戦略（EXTEND_TEST/CREATE_TEST/BOTH_TEST）
  - タスク分割とPhase別見積もり
  - 依存関係図（Mermaid形式）
  - リスクと軽減策
  - 品質ゲート
- **戦略情報**: metadata.jsonのdesign_decisionsに自動保存
- **Phase 2での活用**: Phase 2は実装戦略決定をスキップし、Phase 0の戦略を参照

**Phase 1以降の成果物**:
- **要件定義書**: `.ai-workflow/issue-304/01_requirements/output/requirements.md`
- **実行ログ**: `.ai-workflow/issue-304/01_requirements/execute/`
  - `agent_log_1.md` - エージェント実行ログ（Markdown形式）
  - `agent_log_raw_1.txt` - エージェント実行ログ（生テキスト）
  - `prompt_1.txt` - エージェントへの入力プロンプト
  - ※リトライ時は連番がインクリメント（`agent_log_2.md`、`agent_log_3.md`...）
- **GitHub Issue**:
  - 成果物（要件定義書）がコメント投稿される
  - レビュー結果とフィードバックがコメント投稿される
- **メタデータ**: `.ai-workflow/issue-304/metadata.json`

## Jenkins統合

### ai-workflow-orchestratorジョブ

GitHub IssueからPR作成まで、Claude AIが自動的に開発プロセスを実行します。

#### 使用方法

**1. Jenkins UIからジョブ実行**
- ジョブ: `AI_Workflow/ai_workflow_orchestrator`
- 必須パラメータ: `ISSUE_URL`

**2. パラメータ**

| パラメータ | デフォルト | 説明 |
|-----------|----------|------|
| ISSUE_URL | (必須) | GitHub Issue URL |
| START_PHASE | planning | 開始フェーズ（planning推奨）<br>選択肢: planning, requirements, design, test_scenario, implementation, testing, documentation, report |
| DRY_RUN | false | ドライランモード |
| SKIP_REVIEW | false | レビュースキップ |
| MAX_RETRIES | 3 | 最大リトライ回数 |
| COST_LIMIT_USD | 5.0 | コスト上限（USD） |

**START_PHASEの推奨設定**:
- **planning（推奨）**: Phase 0から開始し、実装戦略・テスト戦略を事前決定することで後続フェーズの効率が向上
- **requirements以降**: Planning Phaseをスキップし、直接要件定義から開始（後方互換性のため警告ログのみ出力）

**3. 実行例**

```bash
# Jenkins CLI経由での実行（オプション）
jenkins-cli build AI_Workflow/ai_workflow_orchestrator \
  -p ISSUE_URL=https://github.com/tielec/infrastructure-as-code/issues/305 \
  -p START_PHASE=planning
```

**4. Git自動commit & push**

各Phase完了後、成果物が自動的にGitにcommit & pushされます。

- **コミットメッセージフォーマット**:
  ```
  [ai-workflow] Phase X (phase_name) - completed/failed

  Issue: #XXX
  Phase: X (phase_name)
  Status: completed/failed
  Review: PASS/PASS_WITH_SUGGESTIONS/FAIL

  Auto-generated by AI Workflow
  ```

- **コミット対象**:
  - `.ai-workflow/issue-XXX/` 配下のすべてのファイル
  - プロジェクト本体で変更されたファイル（.ai-workflow/以外）

- **除外対象**:
  - 他のIssueのファイル（`.ai-workflow/issue-YYY/`）
  - Jenkins一時ディレクトリ（`*@tmp/`）

**5. トラブルシューティング**

- **Git push失敗**: ネットワークエラー時は最大3回リトライ
- **権限エラー**: GITHUB_TOKEN環境変数が正しく設定されているか確認
- **Detached HEAD**: Jenkinsfileで自動的にブランチにcheckout

## 開発ステータス

### ✅ 完了（v1.0.0 MVP）
- [x] ワークフロー初期化（metadata.json）
- [x] フェーズステータス管理（Enum: pending/in_progress/completed/failed）
- [x] BDDテスト（behave）
- [x] Jenkins統合（Job DSL + Jenkinsfile）
- [x] Git workflow（feature branch）

### ✅ 完了（v1.1.0 Phase 1実装）
- [x] Claude Agent SDK統合（Docker環境）
- [x] OAuth認証（CLAUDE_CODE_OAUTH_TOKEN）
- [x] GitHub API統合（PyGithub）
- [x] Phase基底クラス（BasePhase）
- [x] プロンプト管理（prompts/requirements/）
- [x] Phase 1: 要件定義フェーズ（requirements.py）

### ✅ 完了（v1.2.0 Phase 2実装）
- [x] Phase 2: 設計フェーズ（phases/design.py）
- [x] プロンプト管理（prompts/design/）
- [x] 設計判断機能（実装戦略・テスト戦略・テストコード戦略）
- [x] Phase 2 E2Eテスト（tests/e2e/test_phase2.py）

### ✅ 完了（v1.3.0 全Phase完成 + Jenkins統合完成）
- [x] Phase 3-7実装（test_scenario, implementation, testing, documentation, report）
- [x] GitManager実装（Git自動commit & push機能）
- [x] BasePhase Git統合（finally句で自動commit & push）
- [x] Jenkinsfile完成（全Phase実行ステージ）
- [x] クリティカルシンキングレビュー統合

### ✅ 完了（v1.4.0 GitHub統合強化）
- [x] 全フェーズの成果物をGitHub Issueコメントに自動投稿
- [x] BasePhase.post_output()メソッド統合
- [x] エラーハンドリング強化（投稿失敗時でもワークフロー継続）

### ✅ 完了（v1.5.0 Phase 0実装 - Issue #313）
- [x] Phase 0: プロジェクト計画フェーズ（phases/planning.py）
  - プロジェクトマネージャ役割として機能
  - Issue複雑度分析、タスク分割、依存関係特定
  - 各フェーズの見積もり、リスク評価と軽減策
- [x] 実装戦略・テスト戦略の事前決定機能
  - Implementation Strategy: CREATE/EXTEND/REFACTOR
  - Test Strategy: UNIT_ONLY/.../ALL
  - Test Code Strategy: EXTEND_TEST/CREATE_TEST/BOTH_TEST
- [x] planning.mdとmetadata.jsonへの戦略保存
  - 正規表現による戦略判断自動抽出
  - metadata.json design_decisionsセクションへ保存
- [x] Phase 2との連携（戦略情報の参照）
  - Phase 2は実装戦略決定をスキップし、Phase 0の判断を優先
  - Phase 0がスキップされた場合のフォールバック機能
- [x] Phase 0 Unit/E2Eテスト（tests/unit/phases/test_planning.py, tests/e2e/test_phase0.py）

### ✅ 完了（v1.6.0 リトライ機能強化 - Issue #331）
- [x] execute()失敗時の自動リトライ機能
  - execute()とrevise()を統一リトライループに統合
  - 一時的なエラー（ネットワーク障害、API制限等）からの自動回復
  - 試行回数の可視化（`[ATTEMPT N/3]`ログ）
  - 最大3回までの自動リトライ

### 🚧 開発中（v1.7.0以降）
- [ ] Phase 7: Report実装（全体評価と残課題抽出）
- [ ] Phase 8: Evaluation実装（進捗トラッキング、再実行機能）
- [ ] PR自動作成機能
- [ ] GitHub Webhook連携
- [ ] レビュー基準カスタマイズ
- [ ] コスト最適化とモニタリング

## アーキテクチャ

```
scripts/ai-workflow/
├── main.py                      # CLIエントリーポイント
├── core/
│   ├── workflow_state.py        # ワークフロー状態管理
│   ├── metadata_manager.py      # メタデータ管理
│   ├── claude_agent_client.py   # Claude Agent SDK統合
│   └── github_client.py         # GitHub API統合
├── phases/
│   ├── base_phase.py            # Phase基底クラス
│   │                            # - _get_planning_document_path(): Planning Document参照ヘルパー
│   ├── planning.py              # Phase 0: プロジェクト計画
│   │                            # - planning.md生成、戦略判断をmetadata.jsonに保存
│   ├── requirements.py          # Phase 1: 要件定義
│   │                            # - Planning Document参照ロジック追加
│   ├── design.py                # Phase 2: 設計
│   │                            # - Planning Document参照ロジック追加
│   ├── test_scenario.py         # Phase 3: テストシナリオ
│   │                            # - Planning Document参照ロジック追加
│   ├── implementation.py        # Phase 4: 実装
│   │                            # - Planning Document参照ロジック追加
│   ├── testing.py               # Phase 5: テスト
│   │                            # - Planning Document参照ロジック追加
│   └── documentation.py         # Phase 6: ドキュメント
│                                # - Planning Document参照ロジック追加
├── prompts/
│   ├── planning/
│   │   ├── execute.txt          # 計画書生成プロンプト
│   │   ├── review.txt           # 計画書レビュープロンプト
│   │   └── revise.txt           # 計画書修正プロンプト
│   ├── requirements/
│   │   ├── execute.txt          # 要件定義実行プロンプト（Planning Document参照セクション追加）
│   │   ├── review.txt           # 要件定義レビュープロンプト
│   │   └── revise.txt           # 要件定義修正プロンプト
│   ├── design/
│   │   ├── execute.txt          # 設計実行プロンプト（Planning Document参照セクション追加）
│   │   ├── review.txt           # 設計レビュープロンプト
│   │   └── revise.txt           # 設計修正プロンプト
│   └── ...                      # 他のフェーズのプロンプト（すべてPlanning Document参照追加）
├── reviewers/
│   └── critical_thinking.py     # クリティカルシンキングレビュー（未実装）
├── tests/
│   ├── features/                # BDDテスト
│   ├── unit/                    # ユニットテスト
│   └── integration/             # 統合テスト
│       └── test_planning_phase_integration.py  # Planning Phase統合テスト
├── Dockerfile                   # Docker環境定義
├── requirements.txt             # Python依存パッケージ
└── README.md                    # このファイル
```

### Planning Document参照の仕組み

```
Phase 0 (Planning)
    │
    ├─ planning.md生成
    │   - Issue複雑度分析
    │   - 実装戦略判断（CREATE/EXTEND/REFACTOR）
    │   - テスト戦略判断（UNIT_ONLY/...ALL）
    │   - タスク分割、見積もり、リスク評価
    │
    ├─ metadata.jsonに戦略保存
    │   - design_decisions.implementation_strategy
    │   - design_decisions.test_strategy
    │   - design_decisions.test_code_strategy
    │
    ▼
Phase 1-7 (Requirements ~ Report)
    │
    ├─ BasePhase._get_planning_document_path()
    │   - Planning Document存在確認
    │   - @{relative_path}形式で返却
    │   - 存在しない場合: "Planning Phaseは実行されていません"
    │
    ├─ プロンプトに埋め込み
    │   - {planning_document_path}プレースホルダーを置換
    │   - Claude Agent SDKが@記法でファイル読み込み
    │
    └─ Planning Documentを参照して作業
        - 実装戦略に基づいた設計・実装
        - テスト戦略に基づいたテストシナリオ
        - リスク軽減策の考慮
```

## CLIコマンド

### `init` - ワークフロー初期化

```bash
python main.py init --issue-url <GitHub Issue URL>
```

**例:**
```bash
python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/304
```

### `execute` - フェーズ実行

```bash
python main.py execute --phase <phase_name> --issue <issue_number>
```

**フェーズ名:**
- `planning`: プロジェクト計画（Phase 0）
- `requirements`: 要件定義（Phase 1）
- `design`: 設計（Phase 2）
- `test_scenario`: テストシナリオ（Phase 3）
- `implementation`: 実装（Phase 4）
- `testing`: テスト（Phase 5）
- `documentation`: ドキュメント（Phase 6）

**例:**
```bash
# Phase 0から開始する場合（推奨）
python main.py execute --phase planning --issue 304

# Phase 1から開始する場合
python main.py execute --phase requirements --issue 304
```

## Docker環境

### イメージビルド

```bash
cd scripts/ai-workflow
docker build -t ai-workflow:v1.1.0 .
```

### 動作確認

```bash
# Claude Agent SDK動作確認
docker run --rm \
  -e CLAUDE_CODE_OAUTH_TOKEN="${CLAUDE_CODE_OAUTH_TOKEN}" \
  ai-workflow:v1.1.0 \
  python test_docker.py
```

### Phase 1テスト

```bash
# Phase 1動作テスト（Issue #304を使用）
docker run --rm \
  -e CLAUDE_CODE_OAUTH_TOKEN="${CLAUDE_CODE_OAUTH_TOKEN}" \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  -e GITHUB_REPOSITORY="${GITHUB_REPOSITORY}" \
  -v "$(pwd)/../..:/workspace" \
  -w /workspace/scripts/ai-workflow \
  ai-workflow:v1.1.0 \
  python test_phase1.py
```

## トラブルシューティング

### Q1: OAuth認証エラー

**エラー:**
```
ERROR: Invalid API key · Please run /login
```

**対策:**
1. OAuth Tokenが正しく設定されているか確認:
   ```bash
   echo $CLAUDE_CODE_OAUTH_TOKEN
   ```
2. トークンの有効期限を確認（期限切れの場合は再ログイン）:
   ```bash
   claude login
   ```
3. [DOCKER_AUTH_SETUP.md](DOCKER_AUTH_SETUP.md) を参照

### Q2: GitHub API認証エラー

**エラー:**
```
ERROR: GITHUB_TOKEN and GITHUB_REPOSITORY environment variables are required.
```

**対策:**
1. 環境変数が設定されているか確認:
   ```bash
   echo $GITHUB_TOKEN
   echo $GITHUB_REPOSITORY
   ```
2. GitHub Personal Access Tokenの権限を確認（`repo` scope必須）

### Q3: Dockerマウントエラー

**エラー:**
```
Error: Workflow metadata not found
```

**対策:**
1. ボリュームマウントが正しいか確認:
   ```bash
   docker run --rm -v "$(pwd):/workspace" ...
   ```
2. `.ai-workflow`ディレクトリが存在するか確認:
   ```bash
   ls .ai-workflow/issue-304/
   ```

## ローカル開発環境（オプション）

### セットアップ

```bash
# Python仮想環境作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージインストール
pip install -r requirements.txt
pip install -r requirements-test.txt

# Claude Code CLIインストール
npm install -g @anthropic-ai/claude-code

# Claude Codeログイン
claude login
```

### テスト実行

```bash
# BDDテスト
behave tests/features/

# ユニットテスト
pytest tests/unit/
```

### 新しいフェーズの追加

1. `phases/`に新しいPhaseクラスを作成（`BasePhase`を継承）
2. `prompts/{phase_name}/`にプロンプトファイルを作成
   - `execute.txt`: フェーズ実行プロンプト
   - `review.txt`: レビュープロンプト
3. `main.py`の`execute`コマンドに新しいフェーズを追加
4. BDDテストを追加

## 関連ドキュメント

- [DOCKER_AUTH_SETUP.md](DOCKER_AUTH_SETUP.md) - Docker環境でのOAuth認証設定
- [ROADMAP.md](ROADMAP.md) - 開発ロードマップ
- [../../CLAUDE.md](../../CLAUDE.md) - プロジェクト全体のガイド

## ライセンス

このプロジェクトは infrastructure-as-code リポジトリの一部です。

---

**バージョン**: 1.5.0
**最終更新**: 2025-10-10
**Phase 0実装**: Issue #313で追加（プロジェクトマネージャ役割）
