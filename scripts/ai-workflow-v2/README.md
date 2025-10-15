# AI Workflow v2 (TypeScript)

TypeScript で再実装した AI Workflow 自動化ツールの概要です。CLI が Codex と Claude Code のエージェントを連携させ、GitHub / Jenkins / Pulumi と統合した 10 フェーズの Issue ワークフロー（planning 〜 evaluation）を実行します。

## 特長

- **Codex + Claude のデュアルエージェント** … Codex（`gpt-5-codex`）で高い推論が必要な編集を担当し、状況に応じて自動で Claude にフォールバックします。
- **決定的なプロンプト管理** … すべてのプロンプトテンプレートは `src/prompts/{phase}` に配置され、ビルド時に `dist` へコピーされます。
- **永続化されたワークフロー状態** … `.ai-workflow/issue-*/metadata.json` へメタデータを保存する `MetadataManager` により、途中再開やコスト集計が可能です。
- **GitHub & Jenkins 対応** … 個人アクセストークンと Jenkins Job DSL に対応し、Docker コンテナ内で TypeScript CLI を実行できます。

## リポジトリ構成

```
scripts/ai-workflow-v2/
├── Dockerfile                 # Node 20 ベースの Codex 対応イメージ
├── package.json               # CLI エントリーポイント（bin: ai-workflow-v2）
├── scripts/
│   └── copy-static-assets.mjs # prompts/templates を dist/ へコピー
├── src/
│   ├── core/                  # エージェント・Git/GitHub ヘルパー・メタデータ管理
│   ├── phases/                # 各フェーズ実装（planning 〜 evaluation）
│   ├── prompts/               # フェーズ別プロンプト
│   ├── templates/             # PR ボディなどのテンプレート
│   ├── main.ts                # CLI 定義
│   └── index.ts               # bin エントリ
└── dist/                      # `npm run build` 後に生成される JS
```

## 前提条件

- Node.js 20 以上
- npm 10 以上
- Codex API キー（`CODEX_API_KEY` または `OPENAI_API_KEY`）
- Claude Code 認証ファイル（`credentials.json`）
- GitHub パーソナルアクセストークン（`repo`, `workflow`, `read:org`）
- （任意）Docker 24 以上（コンテナ内で実行する場合）

## クイックスタート（ローカル）

```bash
# 依存関係のインストールとビルド
npm install
npm run build

# 環境変数
export CODEX_API_KEY="sk-code..."        # Codex 高推論キー
export CLAUDE_CODE_CREDENTIALS_PATH="$HOME/.claude-code/credentials.json"
export GITHUB_TOKEN="ghp_..."
export GITHUB_REPOSITORY="owner/repo"

# Issue URL からワークフローを初期化
node dist/index.js init \
  --issue-url https://github.com/owner/repo/issues/385

# 全フェーズ実行
node dist/index.js execute --phase all --issue 385

# 失敗したフェーズのみ再実行
node dist/index.js execute --phase requirements --issue 385 --agent codex
```

## CLI オプション

```bash
ai-workflow-v2 init \
  --issue-url <URL>

ai-workflow-v2 execute \
  --issue <number> \
  [--phase <name>|--phase all] \
  [--agent auto|codex|claude] \
  [--preset <name>] \
  [--force-reset] \
  [--skip-dependency-check|--ignore-dependencies] \
  [--requirements-doc <path>] [...] \
  [--git-user <name>] [--git-email <email>]

ai-workflow-v2 review \
  --phase <name> \
  --issue <number>
```

### エージェントモード

- `auto`（既定）: Codex API キーがあれば Codex を使用し、なければ Claude にフォールバックします。
- `codex`: Codex のみを使用（`gpt-5-codex`）。Claude 認証情報は無視されます。
- `claude`: Claude Code を強制使用。`CLAUDE_CODE_CREDENTIALS_PATH` が必須です。

### 依存関係チェックのフラグ

- `--skip-dependency-check` … すべてのフェーズ依存関係チェックを無効化します（慎重に使用）。
- `--ignore-dependencies` … 依存関係の警告を表示しつつ処理を続行します。

## フェーズ概要

| フェーズ | ファイル                         | 説明                                        |
|--------:|----------------------------------|---------------------------------------------|
| 0       | `src/phases/planning.ts`         | 計画ドキュメントと設計メモの草案            |
| 1       | `src/phases/requirements.ts`     | 要件収集・外部資料の整理                    |
| 2       | `src/phases/design.ts`           | アーキテクチャ設計                          |
| 3       | `src/phases/test-scenario.ts`    | テストシナリオ策定                          |
| 4       | `src/phases/implementation.ts`   | コード実装                                  |
| 5       | `src/phases/test-implementation.ts` | テストコードの実装                      |
| 6       | `src/phases/testing.ts`          | テスト実行と証跡収集                        |
| 7       | `src/phases/documentation.ts`    | ドキュメント・ランブック更新                |
| 8       | `src/phases/report.ts`           | ステータスレポート・PR ボディ生成          |
| 9       | `src/phases/evaluation.ts`       | 最終評価と残作業の整理                     |

各フェーズは `BasePhase` を継承し、メタデータ永続化、実行/レビューサイクル、エージェント制御、Git 自動コミットなど共通機能を利用します。

## Docker での実行

```bash
docker build -t ai-workflow-v2 .

docker run --rm \
  -e CODEX_API_KEY \
  -e CLAUDE_CODE_CREDENTIALS_PATH=/root/.claude-code/credentials.json \
  -e GITHUB_TOKEN \
  -e GITHUB_REPOSITORY \
  -v "$HOME/.claude-code:/root/.claude-code:ro" \
  -v "$(pwd)/..:/workspace" \
  -w /workspace/scripts/ai-workflow-v2 \
  ai-workflow-v2 \
  node dist/index.js execute --phase all --issue 385 --agent auto
```

## 開発フロー

```bash
# 依存関係のインストールとウォッチャー起動
npm install
npm run dev

# （任意）Lint
npx eslint --ext .ts src

# ユニットテスト（必要に応じて追加）
npx vitest
```

## 参考ドキュメント

- [ARCHITECTURE.md](ARCHITECTURE.md) … モジュール構成とデータフロー
- [DOCKER_AUTH_SETUP.md](DOCKER_AUTH_SETUP.md) … Codex / Claude 認証の準備手順
- [SETUP_TYPESCRIPT.md](SETUP_TYPESCRIPT.md) … ローカル開発環境の構築手順
- [ROADMAP.md](ROADMAP.md) … 今後の改善計画
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) … よくあるトラブルと対処法

---

**バージョン**: 0.2.0（TypeScript リライト版）  
**最終更新日**: 2025-10-15
