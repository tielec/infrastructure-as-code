# AI駆動開発自動化ワークフロー

Claude Agent SDKを使った7フェーズの自動開発ワークフロー

## 概要

このツールは、GitHubのIssueからプロジェクト計画、要件定義、設計、テスト、実装、ドキュメント作成までを自動化します。

### 主な特徴

- **Claude Pro Max活用**: Claude Code headless modeで自律的にタスクを実行
- **7フェーズワークフロー**: プロジェクト計画 → 要件定義 → 設計 → テストシナリオ → 実装 → テスト → ドキュメント
- **事前計画機能**: Phase 0で実装戦略・テスト戦略を事前決定し、後続フェーズの負荷を軽減
- **クリティカルシンキングレビュー**: 各フェーズで品質チェック
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

**Phase 0の成果物**:
- **プロジェクト計画書**: `.ai-workflow/issue-304/00_planning/output/planning.md`
- **実装戦略**: metadata.jsonのdesign_decisionsに保存（CREATE/EXTEND/REFACTOR、テスト戦略等）

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
| START_PHASE | planning | 開始フェーズ（planning推奨） |
| DRY_RUN | false | ドライランモード |
| SKIP_REVIEW | false | レビュースキップ |
| MAX_RETRIES | 3 | 最大リトライ回数 |
| COST_LIMIT_USD | 5.0 | コスト上限（USD） |

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

### ✅ 完了（v1.5.0 Phase 0実装）
- [x] Phase 0: プロジェクト計画フェーズ（planning.py）
- [x] 実装戦略・テスト戦略の事前決定機能
- [x] planning.mdとmetadata.jsonへの戦略保存
- [x] Phase 2との連携（戦略情報の参照）

### 🚧 開発中（v1.6.0以降）
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
│   ├── planning.py              # Phase 0: プロジェクト計画
│   ├── requirements.py          # Phase 1: 要件定義
│   ├── design.py                # Phase 2: 設計
│   ├── test_scenario.py         # Phase 3: テストシナリオ
│   ├── implementation.py        # Phase 4: 実装
│   ├── testing.py               # Phase 5: テスト
│   └── documentation.py         # Phase 6: ドキュメント
├── prompts/
│   ├── planning/
│   │   ├── execute.txt          # 計画書生成プロンプト
│   │   ├── review.txt           # 計画書レビュープロンプト
│   │   └── revise.txt           # 計画書修正プロンプト
│   ├── requirements/
│   │   ├── execute.txt          # 要件定義実行プロンプト
│   │   ├── review.txt           # 要件定義レビュープロンプト
│   │   └── revise.txt           # 要件定義修正プロンプト
│   ├── design/
│   │   ├── execute.txt          # 設計実行プロンプト
│   │   ├── review.txt           # 設計レビュープロンプト
│   │   └── revise.txt           # 設計修正プロンプト
│   └── ...                      # 他のフェーズのプロンプト
├── reviewers/
│   └── critical_thinking.py     # クリティカルシンキングレビュー（未実装）
├── tests/
│   ├── features/                # BDDテスト
│   └── unit/                    # ユニットテスト
├── Dockerfile                   # Docker環境定義
├── requirements.txt             # Python依存パッケージ
└── README.md                    # このファイル
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
