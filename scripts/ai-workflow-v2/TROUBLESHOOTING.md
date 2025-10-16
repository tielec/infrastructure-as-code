# トラブルシューティング ― AI Workflow v2 (TypeScript)

TypeScript CLI をローカルまたは Jenkins で利用する際によく発生する事象と対処方法をまとめました。

## 1. Codex CLI 関連

### `exceeded retry limit, last status: 401 Unauthorized`

- `CODEX_API_KEY`（または `OPENAI_API_KEY`）が `gpt-5-codex` の高推論キーか確認します。
- 旧来の `auth.json` は使用せず、API キーのみを渡してください。
- CLI の疎通チェック:
  ```bash
  codex exec --json --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox - <<'EOF'
  You are Codex. Reply "pong".
  EOF
  ```

### `codex: command not found`

- グローバルにインストールします: `npm install -g @openai/codex`
- PATH を通すか、`CODEX_CLI_PATH` に実行ファイルのパスを指定します（Jenkins / Docker でも同様）。

## 2. Claude Code 関連

### `Claude Code credentials are not configured`

- Jenkins では Base64 化した `credentials.json` を渡し、パイプラインでデコードして配置します。
- ローカルでは `export CLAUDE_CODE_CREDENTIALS_PATH="$HOME/.claude-code/credentials.json"` を設定。
- `Invalid bearer token` が出た場合は `claude login` を再実行します。

## 3. GitHub 連携

### `GITHUB_TOKEN and GITHUB_REPOSITORY are required`

- 両方の環境変数が設定されているか確認します。
- PAT のスコープは `repo`, `workflow`, `read:org` が必要です。
- Jenkins では `github-token` のシークレットが存在するか、ジョブ DSL を再適用してください。

### API レート制限 / Abuse Detection

- 同時実行ジョブを減らす、または時間を置いて再実行します。
- CLI 内でのリトライを待っても回復しない場合はリセットを待つしかありません（通常 1 時間あたり 5,000 リクエスト）。

## 4. メタデータ / 再開

### `Workflow not found. Run init first.`

- 実行前に `ai-workflow-v2 init --issue-url ...` を行っているか確認。
- `.ai-workflow/issue-*/metadata.json` が存在するか、権限があるかを確認します。

### フェーズ状態が想定外

- `--force-reset` でワークフロー状態を初期化できます:
  ```bash
  node dist/index.js execute --phase all --issue 385 --force-reset
  ```
- Issue メタデータは保持され、フェーズ状態のみ `pending` に戻ります。

## 5. Docker / Jenkins

### Codex ログが空になる

- Jenkins 側で `stdout` が途中で切れていないか確認します。
- TypeScript 版では `agent_log_raw.txt`（JSON）と Markdown の両方に書き込みます。Markdown が空の場合は、`.ai-workflow/.../execute/` の書き込み権限やディスク残量を確認してください。

### `spawn codex ENOENT`

- `CODEX_CLI_PATH=/usr/local/bin/codex` など、実際のパスを設定します。
- Docker イメージ内で Codex CLI がインストールされているか（`Dockerfile` の `npm install -g @openai/codex`）を確認。

### Jenkins パラメータが表示されない

- `jenkins/jobs/dsl/ai-workflow/ai_workflow_orchestrator.groovy` で `AGENT_MODE` を定義しています。シードジョブを再実行して DSL を再適用してください。

## 6. プリセット関連

### `Unknown preset: <name>`

- プリセット名が存在しません。`--list-presets` で利用可能なプリセット一覧を確認してください:
  ```bash
  node dist/index.js execute --list-presets
  ```
- 旧プリセット名（`requirements-only`, `design-phase`, `implementation-phase`, `full-workflow`）は非推奨ですが、6ヶ月間は動作します（警告が表示されます）。

### プリセット実行時の依存関係エラー

- プリセットに含まれるフェーズの依存関係が満たされていない場合、エラーメッセージが表示されます:
  ```
  [ERROR] Phase "implementation" requires the following phases to be completed:
    ✗ planning - NOT COMPLETED
    ✗ requirements - NOT COMPLETED
  ```
- **対処法**:
  1. 必要なフェーズを先に実行する
  2. `--phase all` で全フェーズを実行
  3. `--ignore-dependencies` で警告のみ表示して実行継続（非推奨）

### `full-workflow` プリセットが使えない

- `full-workflow` プリセットは削除されました。代わりに `--phase all` を使用してください:
  ```bash
  node dist/index.js execute --phase all --issue 385
  ```

## 7. デバッグのヒント

- Codex の問題切り分けには `--agent claude`、Claude の問題切り分けには `--agent codex` を利用。
- `.ai-workflow/issue-*/<phase>/execute/agent_log_raw.txt` の生ログを確認すると詳細が分かります。
- `DEBUG=ai-workflow:*` を設定すると詳細ログ（カスタムフック）が出力されます。
- Git の問題は `GIT_TRACE=1` を付与して調査できます。

対処できない場合は、実行したコマンド、環境変数（機微情報をマスク）、`agent_log_raw.txt` の該当箇所を添えて Issue もしくはチームチャンネルで共有してください。
