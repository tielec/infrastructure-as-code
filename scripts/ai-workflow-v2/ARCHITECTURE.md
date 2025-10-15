# アーキテクチャ概要 ― AI Workflow v2 (TypeScript)

このドキュメントでは、TypeScript 版 AI Workflow の構成、モジュール間の制御フロー、および Codex / Claude Code / GitHub との連携方法を説明します。

## 全体フロー

```
CLI (src/main.ts)
 ├─ init コマンド … メタデータ初期化 + ブランチ作成
 ├─ execute コマンド
 │    ├─ .ai-workflow/issue-*/metadata.json を読み込み
 │    ├─ エージェントモードを判定（Codex / Claude）
 │    ├─ 依存関係順にフェーズを実行
 │    │    ├─ BasePhase.run()
 │    │    │    ├─ execute()    … エージェントで成果物生成
 │    │    │    ├─ review()     … 可能ならレビューサイクル実施
 │    │    │    └─ revise()     … オプション（自動修正）
 │    │    └─ GitManager による自動コミット / プッシュ（必要に応じて）
 │    └─ 実行サマリーを生成
 └─ review コマンド … メタデータを取得し、フェーズの状態を表示
```

## モジュール一覧

| モジュール | 役割 |
|------------|------|
| `src/main.ts` | `commander` による CLI 定義。オプション解析、環境初期化、ブランチ検証を担当。 |
| `src/index.ts` | `ai-workflow-v2` 実行ファイルのエントリーポイント。`runCli` を呼び出す。 |
| `src/core/codex-agent-client.ts` | Codex CLI を起動し JSON イベントをストリーム処理。認証エラー検知・利用量記録も実施。 |
| `src/core/claude-agent-client.ts` | Claude Agent SDK を利用してイベントを取得し、Codex と同様の JSON 形式で保持。 |
| `src/core/content-parser.ts` | レビュー結果の解釈や判定を担当（OpenAI API を利用）。 |
| `src/core/github-client.ts` | Octokit ラッパー。コメント投稿、PR ボディ生成、ワークフロー情報の同期など。 |
| `src/core/git-manager.ts` | `simple-git` 経由でブランチ切替、pull、commit、push を実行。 |
| `src/core/metadata-manager.ts` | `.ai-workflow/issue-*/metadata.json` の CRUD、コスト集計、リトライ回数管理など。 |
| `src/core/workflow-state.ts` | メタデータの読み書きとマイグレーション処理。 |
| `src/phases/*.ts` | 各フェーズの具象クラス。`execute()`, `review()`, `revise()` を実装。 |
| `src/prompts/{phase}/*.txt` | フェーズ別のプロンプトテンプレート。 |
| `src/templates/*.md` | PR ボディ等の Markdown テンプレート。 |
| `scripts/copy-static-assets.mjs` | ビルド後に prompts / templates を `dist/` へコピー。 |

## BasePhase のライフサイクル

1. **依存関係チェック** … `validatePhaseDependencies` で前工程が完了しているか確認（フラグで無効化可能）。
2. **execute()** … プロンプトを整形しエージェントを呼び出して成果物を生成。
3. **review()（任意）** … レビュープロンプトを実行し、`ContentParser` で PASS / FAIL を判定。必要に応じてフィードバックを GitHub に投稿。
4. **revise()（任意）** … レビュー失敗時に最大 3 回まで自動修正サイクルを実行。
5. **メタデータ更新** … フェーズ状態、出力ファイル、コスト、Git コミット情報などを更新。
6. **進捗コメント** … `GitHubClient` を通じて Issue へ進捗コメントを投稿・更新。

## エージェントの選択

`src/main.ts` で `--agent` オプションを解釈します。

- `auto` … `CODEX_API_KEY` / `OPENAI_API_KEY` が設定されていれば Codex を優先し、なければ Claude を使用。
- `codex` … Codex API キー必須。ログは `CodexAgentClient` が収集。
- `claude` … Claude 認証情報が必須。Codex は無効化されます。

`CodexAgentClient` は JSON イベントを `agent_log_raw.txt` に蓄積し、Markdown サマリー（失敗時は生 JSON ブロック）を生成します。`ClaudeAgentClient` は従来の Markdown 形式を維持します。

## ワークフローメタデータ

```
.ai-workflow/issue-385/
├── metadata.json             # WorkflowState（フェーズ状態、コスト、設計メモ等）
├── 00_planning/
│   ├── execute/agent_log_raw.txt
│   ├── execute/prompt.txt
│   ├── review/...
│   └── output/planning.md
└── …
```

`metadata.json` には以下を記録します。

- `phases.*.status` … `pending | in_progress | completed | failed`
- `retry_count` … revise 実行回数
- `output_files` … 生成成果物のパス
- `design_decisions` … 設計フェーズでの意思決定ログ
- `cost_tracking` … トークン数と概算コスト（USD）
- `github_integration` … 進捗コメントの ID など

## 外部サービスとの連携

### Codex CLI
- バイナリパス: `codex`（必要に応じて `CODEX_CLI_PATH` で上書き）
- 必須環境変数: `CODEX_API_KEY` または `OPENAI_API_KEY`
- ログ: `agent_log_raw.txt`（JSON）＋ Markdown サマリー

### Claude Code SDK
- `CLAUDE_CODE_CREDENTIALS_PATH` もしくは `CLAUDE_CODE_OAUTH_TOKEN` が必要
- SDK のストリームイベントを Codex と同じ形式の JSON 配列として保存

### GitHub
- `GITHUB_TOKEN`, `GITHUB_REPOSITORY` を使用
- Issue への進捗コメント投稿、PR ボディ生成、成果物の添付に利用

### Git
- `GitManager` が checkout / pull / commit / push を担当
- 自動コミットメッセージは `"chore: update <phase>"`（実装を参照）

## Jenkins での利用

`jenkins/jobs/dsl/ai-workflow/ai_workflow_orchestrator.groovy` で `AGENT_MODE` パラメータを定義し、パイプライン（`jenkins/jobs/pipeline/ai-workflow/ai-workflow-orchestrator/Jenkinsfile`）が CLI に渡します。TypeScript プロジェクトの `Dockerfile` からビルドしたイメージ上で CLI を実行し、必要に応じて Claude 認証情報をコピーします。

## ビルドパイプライン

```
npm run build
 ├─ tsc -p tsconfig.json
 └─ node scripts/copy-static-assets.mjs
```

`dist/` ディレクトリは `src/` と同じ構造で生成され、Docker / Jenkins からもプロンプトとテンプレートを利用できるようになります。
