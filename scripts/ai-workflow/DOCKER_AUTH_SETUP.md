# Docker環境でのClaude Agent SDK認証設定ガイド

## 概要

Docker環境でClaude Agent SDK（Claude Code headless mode）を使用するには、Claude Pro/Max契約のOAuth認証が必要です。
このドキュメントでは、ホストマシンのClaude認証情報をDockerコンテナで使用する方法を説明します。

## 前提条件

- Claude Pro/Max契約済み
- ホストマシンでClaude Code CLIにログイン済み（`claude login`実行済み）
- Docker Desktop起動済み

## 認証の仕組み

Claude Agent SDKは以下の認証方法をサポートしています：

1. **ローカル認証ファイル**（`~/.claude/.credentials.json`）
   - ホストマシンのCLI認証で使用
   - Dockerコンテナからは直接アクセス不可

2. **環境変数** (`CLAUDE_CODE_OAUTH_TOKEN`)
   - Docker環境で推奨
   - OAuth 2.0アクセストークンを直接指定

## セットアップ手順

### Step 1: OAuthトークンの抽出

ホストマシンの認証ファイルからOAuthトークンを抽出します。

**Windows（PowerShell）:**
```powershell
# 認証ファイルのパス確認
ls $HOME\.claude\.credentials.json

# トークン抽出
python -c "import json; data=json.load(open(r'$HOME\.claude\.credentials.json')); print(data['claudeAiOauth']['accessToken'])"
```

**Linux/macOS（Bash）:**
```bash
# トークン抽出
cat ~/.claude/.credentials.json | python -c "import sys, json; data=json.load(sys.stdin); print(data['claudeAiOauth']['accessToken'])"
```

**出力例:**
```
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
```

### Step 2: 環境変数としてDockerコンテナに渡す

抽出したトークンを`CLAUDE_CODE_OAUTH_TOKEN`環境変数として設定し、Dockerコンテナを実行します。

**テスト実行:**
```bash
docker run --rm \
  -e CLAUDE_CODE_OAUTH_TOKEN="sk-ant-oat01-..." \
  ai-workflow:latest \
  python test_docker.py
```

**実際のワークフロー実行:**
```bash
docker run --rm \
  -e CLAUDE_CODE_OAUTH_TOKEN="sk-ant-oat01-..." \
  -v "$(pwd)/.ai-workflow:/workspace/.ai-workflow" \
  ai-workflow:latest \
  python main.py --issue 304 --phase requirements
```

### Step 3: 動作確認

正常に認証できている場合、以下のような出力が得られます：

```
[INFO] Docker環境でClaude Agent SDK動作確認...
[PROMPT] 2 + 2の計算結果を教えてください。簡潔に答えだけ返してください。
[RESPONSE]
SystemMessage(subtype='init', data={...model='claude-sonnet-4-5-20250929'...})
AssistantMessage(content=[TextBlock(text='4')], model='claude-sonnet-4-5-20250929', ...)
ResultMessage(subtype='success', duration_ms=2427, total_cost_usd=0.0361836, usage={...}, result='4')
[OK] Claude Agent SDK動作確認完了
```

**認証失敗の場合:**
```
ERROR: Invalid API key · Please run /login
```

## セキュリティ上の注意事項

### ⚠️ トークンの取り扱い

1. **コミット禁止**: OAuthトークンをGitリポジトリにコミットしないこと
2. **環境変数管理**: トークンは環境変数またはシークレット管理ツールで管理
3. **トークン有効期限**: OAuth 2.0トークンには有効期限があり、定期的な更新が必要
4. **アクセス制御**: トークンへのアクセス権限を必要最小限に制限

### トークンの保管場所（推奨）

**開発環境:**
- `.env`ファイル（`.gitignore`に追加）
- 環境変数設定スクリプト（ローカル）

**Jenkins環境:**
- Jenkins Credentials（Secret text）
- AWS Secrets Manager（本番環境）

## Jenkins統合

### Jenkins Credentials設定

1. **Credential作成**:
   - Kind: Secret text
   - Secret: `sk-ant-oat01-...`（抽出したトークン）
   - ID: `claude-code-oauth-token`
   - Description: Claude Code OAuth Token for AI Workflow

2. **Jenkinsfileでの使用**:
```groovy
pipeline {
    agent any

    environment {
        CLAUDE_CODE_OAUTH_TOKEN = credentials('claude-code-oauth-token')
    }

    stages {
        stage('AI Workflow') {
            steps {
                script {
                    sh '''
                        docker run --rm \
                          -e CLAUDE_CODE_OAUTH_TOKEN="${CLAUDE_CODE_OAUTH_TOKEN}" \
                          -v "${WORKSPACE}/.ai-workflow:/workspace/.ai-workflow" \
                          ai-workflow:latest \
                          python main.py --issue ${ISSUE_NUMBER} --phase ${PHASE}
                    '''
                }
            }
        }
    }
}
```

### AWS Secrets Manager統合（本番環境）

```groovy
pipeline {
    agent any

    stages {
        stage('AI Workflow') {
            steps {
                script {
                    def token = sh(
                        script: 'aws secretsmanager get-secret-value --secret-id claude-code-oauth-token --query SecretString --output text',
                        returnStdout: true
                    ).trim()

                    sh """
                        docker run --rm \
                          -e CLAUDE_CODE_OAUTH_TOKEN="${token}" \
                          -v "\${WORKSPACE}/.ai-workflow:/workspace/.ai-workflow" \
                          ai-workflow:latest \
                          python main.py --issue \${ISSUE_NUMBER} --phase \${PHASE}
                    """
                }
            }
        }
    }
}
```

## トラブルシューティング

### Q1: 認証エラーが発生する

**エラー:**
```
ERROR: Invalid API key · Please run /login
```

**原因と対策:**
1. **トークンが正しく抽出されていない**
   - `.credentials.json`の存在を確認: `ls ~/.claude/.credentials.json`
   - JSON構造を確認: `cat ~/.claude/.credentials.json | python -m json.tool`

2. **トークンの有効期限切れ**
   - ホストマシンで再ログイン: `claude login`
   - 新しいトークンを再抽出

3. **環境変数が正しく設定されていない**
   - Docker内で環境変数確認: `docker run --rm -e CLAUDE_CODE_OAUTH_TOKEN="..." ai-workflow:latest env | grep CLAUDE`

### Q2: トークンが見つからない

**エラー:**
```
FileNotFoundError: [Errno 2] No such file or directory: '~/.claude/.credentials.json'
```

**対策:**
1. ホストマシンでClaude Code CLIにログイン:
   ```bash
   claude login
   ```
2. ブラウザでOAuth認証を完了
3. 認証ファイルの存在を確認

### Q3: Docker内でClaude Codeが起動しない

**エラー:**
```
ERROR: Claude Code not found
```

**対策:**
1. Dockerイメージを再ビルド:
   ```bash
   docker build -t ai-workflow:latest .
   ```
2. Claude Code CLIのインストール確認:
   ```bash
   docker run --rm ai-workflow:latest claude --version
   ```

## リファレンス

- [Claude Code SDK](https://www.npmjs.com/package/@anthropic-ai/claude-code)
- [Claude Agent SDK Python](https://pypi.org/project/claude-agent-sdk/)
- [cabinlab/claude-code-sdk-docker](https://github.com/cabinlab/claude-code-sdk-docker) - Docker環境での実装例

## 更新履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|----------|
| 2025-10-08 | 1.0.0 | 初版作成 - OAuth認証設定方法とJenkins統合 |
