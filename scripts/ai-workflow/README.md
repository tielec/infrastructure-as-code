# AI駆動開発自動化ワークフロー

Claude Agent SDKを使った7フェーズの自動開発ワークフロー

## 概要

このツールは、GitHubのIssueからプロジェクト計画、要件定義、設計、テスト、実装、ドキュメント作成までを自動化します。

### 主な特徴

- **Claude Pro Max活用**: Claude Code headless modeで自律的にタスクを実行
- **10フェーズワークフロー**: Phase 0（プロジェクト計画） → Phase 1（要件定義） → Phase 2（設計） → Phase 3（テストシナリオ） → Phase 4（実装：実コードのみ） → **Phase 5（テストコード実装：テストコードのみ）** → Phase 6（テスト実行） → Phase 7（ドキュメント） → Phase 8（レポート） → **Phase 9（プロジェクト評価）**
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
# 用途: Claude Agent SDK（メインタスク - design.md生成など）
# モデル: Claude Code Pro Max デフォルト（Sonnet 4.5）
export CLAUDE_CODE_OAUTH_TOKEN="sk-ant-oat01-..."

# OpenAI API Key
# 用途: ContentParser（軽量タスク - レビュー結果パース、戦略抽出）
# モデル: gpt-4o-mini（安価・高速）
export OPENAI_API_KEY="sk-proj-..."

# GitHub Personal Access Token
export GITHUB_TOKEN="ghp_..."

# GitHubリポジトリ名
export GITHUB_REPOSITORY="tielec/infrastructure-as-code"
```

**OAuth Token取得方法**: [DOCKER_AUTH_SETUP.md](DOCKER_AUTH_SETUP.md) を参照

**OpenAI API Key取得方法**:
1. [OpenAI Platform](https://platform.openai.com/api-keys) にアクセス
2. "Create new secret key" をクリック
3. キーをコピーして`OPENAI_API_KEY`に設定

**GitHub Token作成方法**:
1. GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token (classic)
3. Scopes: `repo` (Full control of private repositories) - **PR作成に必須**
4. トークンをコピーして`GITHUB_TOKEN`に設定

### 2. ワークフロー初期化

```bash
# リポジトリルートに移動
cd C:\Users\ytaka\TIELEC\development\infrastructure-as-code

# Issue URLを指定してワークフロー初期化（ドラフトPR自動作成）
docker run --rm \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  -e GITHUB_REPOSITORY="${GITHUB_REPOSITORY}" \
  -v "$(pwd):/workspace" \
  -w /workspace/scripts/ai-workflow \
  ai-workflow:v1.1.0 \
  python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/304
```

**init コマンドの動作**:
1. `.ai-workflow/issue-XXX/metadata.json` を作成
2. ブランチ `ai-workflow/issue-XXX` を作成またはチェックアウト
3. metadata.json を Git コミット
4. リモートブランチに push（最大3回リトライ）
5. **ドラフトPRを自動作成**（既存PRがある場合はスキップ）

**注意事項**:
- `GITHUB_TOKEN` 未設定の場合、PR作成はスキップされます（警告表示）
- 既存PRが存在する場合、新規作成はスキップされます
- PR作成失敗時でも init 自体は成功として扱われます

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

### 4. 全フェーズ一括実行（オプション）

```bash
# 全フェーズ（Phase 1-8）を一括実行
docker run --rm \
  -e CLAUDE_CODE_OAUTH_TOKEN="${CLAUDE_CODE_OAUTH_TOKEN}" \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  -e GITHUB_REPOSITORY="${GITHUB_REPOSITORY}" \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  -v "$(pwd):/workspace" \
  -w /workspace/scripts/ai-workflow \
  ai-workflow:v1.1.0 \
  python main.py execute --phase all --issue 304
```

**推奨実行順序:**
1. Phase 0（planning）を個別実行して実装戦略を決定
2. `--phase all`で全フェーズを一括実行

**注意:**
- 全フェーズ実行には30-60分程度かかります
- Phase 0（planning）は`--phase all`に含まれないため、事前に個別実行を推奨

### 5. Phase 1（要件定義）実行（個別実行の場合）

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

### 6. 結果確認

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

**Phase 1-8の成果物**:
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

**Phase 9（プロジェクト評価）の成果物**:
- **評価レポート**: `.ai-workflow/issue-304/09_evaluation/output/evaluation_report.md`
  - Phase 1-8の全成果物を総合評価
  - 4つの判定タイプ（PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT）のいずれかを決定
- **判定別のアクション**:
  - **PASS**: ワークフロー完了、成功サマリーをGitHub Issueに投稿
  - **PASS_WITH_ISSUES**: 残タスクを新しいGitHub Issueとして自動作成、ワークフロー完了
  - **FAIL_PHASE_X**: metadata.jsonをPhase Xに巻き戻し、Phase Xから再実行可能な状態にする
  - **ABORT**: GitHub IssueとPull Requestをクローズし、ワークフロー中止

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
| START_PHASE | planning | 開始フェーズ（planning推奨）<br>選択肢: planning, requirements, design, test_scenario, implementation, test_implementation, testing, documentation, report |
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

### ✅ 完了（v1.7.0 Phase分離 - Issue #324）
- [x] Phase 5（test_implementation）の新設
  - **実装フェーズとテストコード実装フェーズの責務を明確に分離**
  - Phase 4（implementation）: 実コード（ビジネスロジック、API、データモデル等）のみを実装
  - Phase 5（test_implementation）: テストコード（ユニットテスト、統合テスト等）のみを実装
  - テストシナリオ（Phase 3）と実装コード（Phase 4）を参照してテストコードを生成
- [x] Phase番号のシフト
  - 旧Phase 5（testing） → 新Phase 6（testing）
  - 旧Phase 6（documentation） → 新Phase 7（documentation）
  - 旧Phase 7（report） → 新Phase 8（report）
- [x] プロンプトファイルの更新
  - `prompts/test_implementation/`: 新規作成（execute.txt, review.txt, revise.txt）
  - `prompts/implementation/execute.txt`: 責務明確化（実コードのみ実装と明記）
  - `prompts/testing/execute.txt`: Phase番号更新（5→6）、参照先を test_implementation に変更
  - `prompts/documentation/execute.txt`: Phase番号更新（6→7）
  - `prompts/report/execute.txt`: Phase番号更新（7→8）
- [x] 後方互換性の維持
  - 既存ワークフロー（Phase 1-7構成）も引き続き動作
  - WorkflowStateは新旧両方の構造を動的に扱う

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

### ✅ 完了（v1.8.0 Init時PR自動作成）
- [x] Init時ドラフトPR自動作成機能（Issue #355）
  - metadata.json作成後、自動commit → push → PR作成
  - GitHubClient拡張（create_pull_request, check_existing_pr）
  - 既存PRチェック機能
  - GitHub Token `repo` スコープ必須

### ✅ 完了（v1.9.0 レジューム機能 - Issue #360）
- [x] `--phase all`実行時の自動レジューム機能
  - 失敗したフェーズから自動的に再開
  - メタデータJSON（`.ai-workflow/issue-XXX/metadata.json`）に記録されたフェーズステータスを活用
  - レジューム開始フェーズの優先順位決定（failed > in_progress > pending）
- [x] `--force-reset`フラグの追加
  - メタデータとワークフローディレクトリをクリアして最初から実行
  - `MetadataManager.clear()`メソッドの実装
- [x] エッジケース対応
  - メタデータ不存在時: 新規ワークフローとして実行
  - メタデータ破損時: 警告表示して新規ワークフローとして実行
  - 全フェーズ完了時: 完了メッセージ表示、`--force-reset`で再実行可能
- [x] レジューム状態のログ出力
  - 完了済みフェーズ、失敗フェーズ、進行中フェーズ、未実行フェーズを明示
  - レジューム開始フェーズを明確に表示

### ✅ 完了（v2.0.0 Phase 9実装 - Issue #362）
- [x] Phase 9: プロジェクト評価フェーズ（phases/evaluation.py）
  - Phase 1-8の全成果物を統合評価
  - 4つの判定タイプ（PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT）による後続処理の自動決定
- [x] 判定別アクション実装
  - **PASS**: ワークフロー正常完了
  - **PASS_WITH_ISSUES**: 残タスクを新GitHub Issueとして自動作成
  - **FAIL_PHASE_X**: metadata.jsonをPhase Xに巻き戻し、再実行準備
  - **ABORT**: Issue/PRクローズ、ワークフロー中止
- [x] MetadataManager拡張（rollback_to_phase, backup_metadata等）
- [x] GitHubClient拡張（Issue自動作成、クローズ処理）
- [x] 評価レポート生成（evaluation_report.md）

### ✅ 完了（v2.1.0 フェーズ依存関係の柔軟化と選択的実行 - Issue #319）
- [x] フェーズ依存関係チェック機能（core/phase_dependencies.py）
  - 全10フェーズの依存関係を定義したPHASE_DEPENDENCIES
  - validate_phase_dependencies()による依存関係検証
  - detect_circular_dependencies()による循環参照検出
- [x] 依存関係制御フラグ
  - `--skip-dependency-check`: 依存関係チェックを完全にスキップ
  - `--ignore-dependencies`: 依存関係エラーを警告に変換して実行継続
- [x] 実行プリセット機能
  - requirements-only: Phase 1のみ実行
  - design-phase: Phase 0-2実行
  - implementation-phase: Phase 0-4実行
  - full-workflow: Phase 0-9全実行
- [x] 外部ドキュメント指定機能
  - `--requirements-doc`: 外部要件定義書を指定してPhase 1スキップ
  - `--design-doc`: 外部設計書を指定してPhase 2スキップ
  - `--test-scenario-doc`: 外部テストシナリオを指定してPhase 3スキップ
  - validate_external_document()によるドキュメント存在確認
- [x] BasePhase統合
  - run()メソッドでの依存関係自動チェック
  - フェーズスキップ時の適切なステータス管理
- [x] 包括的テスト実装
  - 21ユニットテスト（tests/unit/core/test_phase_dependencies.py）
  - 18統合テスト（tests/integration/test_phase_dependencies_integration.py）

### 🚧 開発中（v2.0.0以降）
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
│   ├── github_client.py         # GitHub API統合
│   │   ├── get_issue()          # Issue情報取得
│   │   ├── create_pull_request() # PR作成（v1.8.0で追加）
│   │   └── check_existing_pr()  # 既存PRチェック（v1.8.0で追加）
│   └── phase_dependencies.py    # フェーズ依存関係管理（v2.1.0で追加）
│       ├── PHASE_DEPENDENCIES   # フェーズ依存関係定義
│       ├── PHASE_PRESETS        # 実行プリセット定義
│       ├── validate_phase_dependencies() # 依存関係検証
│       ├── detect_circular_dependencies() # 循環参照検出
│       └── validate_external_document()   # 外部ドキュメント検証
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
│   ├── implementation.py        # Phase 4: 実装（実コードのみ）
│   │                            # - ビジネスロジック、API、データモデル等を実装
│   │                            # - テストコードは実装しない（Phase 5で実装）
│   ├── test_implementation.py   # Phase 5: テストコード実装（新規 v1.7.0）
│   │                            # - ユニットテスト、統合テストを実装
│   │                            # - Phase 3（テストシナリオ）とPhase 4（実装）を参照
│   │                            # - 実コードは変更しない
│   ├── testing.py               # Phase 6: テスト実行（旧Phase 5）
│   │                            # - Phase 5で実装されたテストコードを実行
│   ├── documentation.py         # Phase 7: ドキュメント（旧Phase 6）
│   │                            # - Planning Document参照ロジック追加
│   ├── report.py                # Phase 8: レポート（旧Phase 7）
│   │                            # - Planning Document参照ロジック追加
│   └── evaluation.py            # Phase 9: プロジェクト評価（v2.0.0で追加）
│                                # - Phase 1-8の全成果物を統合評価
│                                # - 4つの判定タイプによる後続処理の自動決定
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
│   ├── test_implementation/     # Phase 5: テストコード実装プロンプト（新規）
│   │   ├── execute.txt          # テストコード実装プロンプト
│   │   ├── review.txt           # テストコードレビュープロンプト
│   │   └── revise.txt           # テストコード修正プロンプト
│   ├── evaluation/              # Phase 9: プロジェクト評価プロンプト（v2.0.0で追加）
│   │   ├── execute.txt          # 評価実行プロンプト
│   │   ├── review.txt           # 評価レビュープロンプト
│   │   └── revise.txt           # 評価修正プロンプト
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

**動作内容（v1.8.0で拡張）**:
1. `.ai-workflow/issue-XXX/` ディレクトリと metadata.json を作成
2. ブランチ `ai-workflow/issue-XXX` を作成またはチェックアウト
3. metadata.json を自動コミット
4. リモートブランチに自動 push（最大3回リトライ）
5. **ドラフトPRを自動作成**（新機能）
   - PRタイトル: `[AI-Workflow] Issue #XXX`
   - PR本文: ワークフロー進捗チェックリストを含む
   - 既存PRがある場合はスキップ
   - PR作成失敗時は警告のみ（init 自体は成功）

**環境変数要件**:
- `GITHUB_TOKEN`: PR作成に必須（`repo` スコープ）
- `GITHUB_REPOSITORY`: リポジトリ名（例: `owner/repo`）

### `execute` - フェーズ実行

```bash
python main.py execute --phase <phase_name> --issue <issue_number> [--git-user <username>] [--git-email <email>]
```

**オプション:**
- `--git-user <username>`: Gitコミット時のユーザー名（オプション）
- `--git-email <email>`: Gitコミット時のメールアドレス（オプション）
- `--skip-dependency-check`: フェーズ依存関係のチェックをスキップ（オプション、v2.1.0で追加）
- `--ignore-dependencies`: 依存関係エラーを無視して実行を継続（オプション、v2.1.0で追加）
- `--preset <preset_name>`: 事前定義された実行プリセットを使用（オプション、v2.1.0で追加）
- `--requirements-doc <path>`: 外部要件定義書を指定してPhase 1をスキップ（オプション、v2.1.0で追加）
- `--design-doc <path>`: 外部設計書を指定してPhase 2をスキップ（オプション、v2.1.0で追加）
- `--test-scenario-doc <path>`: 外部テストシナリオを指定してPhase 3をスキップ（オプション、v2.1.0で追加）

**フェーズ名:**
- `all`: **全フェーズ一括実行（Phase 1-9）** ← 新機能（v1.8.0）
- `planning`: プロジェクト計画（Phase 0）
- `requirements`: 要件定義（Phase 1）
- `design`: 設計（Phase 2）
- `test_scenario`: テストシナリオ（Phase 3）
- `implementation`: 実装（Phase 4、実コードのみ）
- `test_implementation`: テストコード実装（Phase 5、テストコードのみ）
- `testing`: テスト実行（Phase 6）
- `documentation`: ドキュメント（Phase 7）
- `report`: レポート（Phase 8）
- `evaluation`: プロジェクト評価（Phase 9）

**例:**
```bash
# 全フェーズを一括実行（Phase 1-8を順次自動実行）
python main.py execute --phase all --issue 304

# Phase 0から開始する場合（推奨）
python main.py execute --phase planning --issue 304

# Phase 1から開始する場合
python main.py execute --phase requirements --issue 304

# Gitコミット時のユーザー名とメールアドレスを指定して実行
python main.py execute --phase requirements --issue 304 \
  --git-user "AI Workflow Bot" \
  --git-email "ai-workflow@example.com"
```

### フェーズ依存関係と選択的実行（v2.1.0で追加 - Issue #319）

#### 依存関係チェック

各フェーズには必要な前提フェーズが定義されており、デフォルトで自動的に依存関係をチェックします。

**依存関係の例:**
- Phase 2（design）: Phase 1（requirements）が完了している必要がある
- Phase 4（implementation）: Phase 2（design）とPhase 3（test_scenario）が完了している必要がある
- Phase 6（testing）: Phase 4（implementation）とPhase 5（test_implementation）が完了している必要がある

**依存関係チェックをスキップ:**
```bash
# 依存関係チェックを完全にスキップ（上級ユーザー向け）
python main.py execute --phase design --issue 304 --skip-dependency-check
```

**依存関係エラーを無視:**
```bash
# 依存関係エラーがあっても実行を継続（警告のみ表示）
python main.py execute --phase design --issue 304 --ignore-dependencies
```

#### 実行プリセット

よく使われるフェーズの組み合わせをプリセットとして提供します。

**利用可能なプリセット:**

1. **requirements-only**: 要件定義のみ実行
   ```bash
   python main.py execute --phase requirements --issue 304 --preset requirements-only
   ```
   - 実行フェーズ: Phase 1（requirements）のみ
   - 用途: 要件定義書だけ作成したい場合

2. **design-phase**: 設計フェーズまで実行
   ```bash
   python main.py execute --phase design --issue 304 --preset design-phase
   ```
   - 実行フェーズ: Phase 0（planning）→ Phase 1（requirements）→ Phase 2（design）
   - 用途: 設計書まで作成し、実装は手動で行う場合

3. **implementation-phase**: 実装フェーズまで実行
   ```bash
   python main.py execute --phase implementation --issue 304 --preset implementation-phase
   ```
   - 実行フェーズ: Phase 0-4（planning → requirements → design → test_scenario → implementation）
   - 用途: 実装コードまで自動生成し、テストは手動で行う場合

4. **full-workflow**: 全フェーズ実行（`--phase all`と同等）
   ```bash
   python main.py execute --phase all --issue 304 --preset full-workflow
   ```
   - 実行フェーズ: Phase 0-9（全フェーズ）
   - 用途: 完全自動化されたワークフロー

#### 外部ドキュメント指定

既存のドキュメントを使用してフェーズをスキップできます。

**要件定義書を指定してPhase 1をスキップ:**
```bash
python main.py execute --phase design --issue 304 \
  --requirements-doc ./docs/requirements.md
```

**設計書を指定してPhase 2をスキップ:**
```bash
python main.py execute --phase implementation --issue 304 \
  --design-doc ./docs/design.md
```

**テストシナリオを指定してPhase 3をスキップ:**
```bash
python main.py execute --phase implementation --issue 304 \
  --test-scenario-doc ./docs/test-scenario.md
```

**複数のドキュメントを同時に指定:**
```bash
python main.py execute --phase implementation --issue 304 \
  --requirements-doc ./docs/requirements.md \
  --design-doc ./docs/design.md \
  --test-scenario-doc ./docs/test-scenario.md
```

**`--phase all` の特徴:**
- Phase 1（requirements）からPhase 9（evaluation）まで順次自動実行
- 各フェーズ完了後、自動的に次フェーズに進行
- 途中でフェーズが失敗した場合、それ以降のフェーズは実行されず停止
- 実行サマリーで全フェーズの結果、総実行時間、総コストを表示
- Phase 0（planning）は含まれない（事前に個別実行を推奨）
- **レジューム機能**: 途中で失敗した場合、次回実行時に失敗したフェーズから自動的に再開
- **Phase 9（evaluation）**: Phase 1-8完了後に自動実行され、プロジェクト全体を評価

### レジューム機能（v1.9.0で追加 - Issue #360）

`--phase all`実行時、途中でフェーズが失敗した場合、次回実行時に**自動的に失敗したフェーズから再開**します。

#### デフォルト動作: 自動レジューム

```bash
# 初回実行（Phase 5で失敗したとする）
python main.py execute --phase all --issue 304

# 次回実行時、自動的にPhase 5から再開
python main.py execute --phase all --issue 304

# ログ例:
# [INFO] Existing workflow detected.
# [INFO] Completed phases: requirements, design, test_scenario, implementation
# [INFO] Failed phases: test_implementation
# [INFO] Resuming from phase: test_implementation
```

#### レジューム開始フェーズの決定ルール

以下の優先順位でレジューム開始フェーズを決定します：

1. **failedフェーズ**: 最初に失敗したフェーズから再開（最優先）
2. **in_progressフェーズ**: 異常終了したフェーズから再開
3. **pendingフェーズ**: 最初の未実行フェーズから再開
4. **全フェーズcompleted**: 既に完了済みメッセージを表示して終了

#### 強制リセット: --force-reset

最初から実行し直したい場合は`--force-reset`フラグを使用します。

```bash
# メタデータをクリアして最初から実行
python main.py execute --phase all --issue 304 --force-reset

# ログ例:
# [INFO] --force-reset specified. Restarting from Phase 1...
# [INFO] Clearing metadata: .ai-workflow/issue-304/metadata.json
# [INFO] Removing workflow directory: .ai-workflow/issue-304
# [OK] Workflow directory removed successfully
# [INFO] Starting new workflow.
```

**注意:**
- `--force-reset`は破壊的操作です。既存のメタデータとワークフローディレクトリ全体が削除されます。
- 全フェーズが完了している場合、レジュームは行われず、完了メッセージが表示されます。この場合も`--force-reset`で再実行可能です。

#### エッジケース

**メタデータ不存在時:**
```bash
# 初回実行（メタデータが存在しない場合）
python main.py execute --phase all --issue 304

# ログ例:
# [INFO] Starting new workflow.
```

**メタデータ破損時:**
```bash
# metadata.jsonが破損している場合
python main.py execute --phase all --issue 304

# ログ例:
# [WARNING] metadata.json is corrupted. Starting as new workflow.
# [INFO] Starting new workflow.
```

**全フェーズ完了時:**
```bash
# 全フェーズが既に完了している場合
python main.py execute --phase all --issue 304

# ログ例:
# [INFO] All phases are already completed.
# [INFO] To re-run, use --force-reset flag.
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

**バージョン**: 2.1.0
**最終更新**: 2025-10-12
**Phase 0実装**: Issue #313で追加（プロジェクトマネージャ役割）
**Phase 5実装**: Issue #324で追加（実装フェーズとテストコード実装フェーズの分離）
**Init時PR作成**: Issue #355で追加（Init実行時にドラフトPR自動作成）
**Phase 9実装**: Issue #362で追加（プロジェクト評価フェーズ、4つの判定タイプによる後続処理自動決定）
**フェーズ依存関係と選択的実行**: Issue #319で追加（依存関係チェック、実行プリセット、外部ドキュメント指定）
