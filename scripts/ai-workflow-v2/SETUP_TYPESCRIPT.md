# ローカルセットアップ ― TypeScript 版

`scripts/ai-workflow-v2` ディレクトリで開発するための環境構築手順です。

## 1. 前提ソフトウェア

- Node.js 20.x（nvm または公式インストーラで導入）
- npm 10.x
- Git
- Codex API キー（`gpt-5-codex` 高推論ライセンス）
- Claude Code 認証情報（`claude login` で生成される `credentials.json`）
- GitHub パーソナルアクセストークン（`repo`, `workflow`, `read:org` スコープ）
- （任意）Docker Desktop（Jenkins コンテナと同条件で動作確認したい場合）

## 2. クローンと依存関係のインストール

```bash
git clone https://github.com/tielec/infrastructure-as-code.git
cd infrastructure-as-code/scripts/ai-workflow-v2

npm install
npm run build   # dist/ に成果物を生成
```

## 3. 環境変数の設定

シェルの設定ファイル、または `direnv` を利用している場合は `.env.local` などに以下を追加します。

```bash
export CODEX_API_KEY="sk-code-..."                    # Codex API キー
export CLAUDE_CODE_CREDENTIALS_PATH="$HOME/.claude-code/credentials.json"
export GITHUB_TOKEN="ghp_..."                         # GitHub PAT
export GITHUB_REPOSITORY="owner/repo"                 # 既定のリポジトリ
```

CLI は `CODEX_API_KEY` を検出すると `OPENAI_API_KEY` にもコピーし、Codex CLI と同じ仕様に合わせます。

## 4. Codex / Claude の動作確認

```bash
codex --version              # CLI がインストールされているか確認
codex exec --json --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox - <<'EOF'
You are Codex. Reply "pong".
EOF

claude --version             # Claude Code CLI（グローバルインストール済みの場合）
claude login                 # 期限切れの場合は再ログイン
```

## 5. CLI の基本操作

```bash
# Issue のワークフローメタデータを初期化
node dist/index.js init --issue-url https://github.com/owner/repo/issues/385

# すべてのフェーズを自動エージェントで実行
node dist/index.js execute --phase all --issue 385

# Codex のみでフェーズ 4 を実行
node dist/index.js execute --phase implementation --issue 385 --agent codex

# フェーズの状態を確認
node dist/index.js review --phase planning --issue 385
```

## 6. 開発ワークフロー

```bash
# 変更を監視しながらコンパイル
npm run dev

# Lint（必要に応じてルール追加）
npx eslint --ext .ts src

# ユニット / 統合テスト（随時追加）
npx vitest
```

## 7. 便利なヒント

- プロンプトを変更したら `npm run build` を実行し、`dist/` へコピーします。
- メタデータのスキーマを変更する場合は `WorkflowState.migrate()` を更新し、移行ログを追加してください。
- Jenkins パイプラインも同じバイナリを利用するため、プッシュ前に `npm run build` を忘れずに実行します。
- Docker での動作確認例:
  ```bash
  docker build -t ai-workflow-v2 .
  docker run --rm ai-workflow-v2 node dist/index.js --help
  ```

これで TypeScript 版の開発環境が整います。Python 版と同様の挙動を保ちつつ、安心して改善を進めてください。
