# Jenkins Dockerイメージ使用状況ドキュメント

このドキュメントは、Jenkinsパイプラインで使用されているDockerイメージの一覧と使用方法をまとめています。

## 目次

- [概要](#概要)
- [統計情報](#統計情報)
- [イメージ一覧](#イメージ一覧)
  - [Python系イメージ](#python系イメージ)
  - [Node.js系イメージ](#node系イメージ)
  - [Rust系イメージ](#rust系イメージ)
  - [AWS系イメージ](#aws系イメージ)
  - [Pulumi系イメージ](#pulumi系イメージ)
  - [Ubuntu系イメージ](#ubuntu系イメージ)
  - [カスタムイメージ](#カスタムイメージ)
- [メンテナンス推奨事項](#メンテナンス推奨事項)
- [バージョン管理方針](#バージョン管理方針)

---

## 概要

本プロジェクトのJenkinsパイプラインでは、様々なDockerイメージを使用して、隔離された実行環境を提供しています。
各イメージは特定の用途に最適化されており、必要な依存関係を事前にインストールすることで、パイプラインの実行時間を短縮しています。

---

## 統計情報

### イメージファミリー別使用数

| イメージファミリー | 使用箇所数 | 割合 |
|-------------------|-----------|------|
| Python系 | 3 | 25% |
| Node.js系 | 2 | 16.7% |
| Rust系 | 2 | 16.7% |
| Python + Node.js複合 | 3 | 25% |
| AWS CLI | 2 | 16.7% |
| Pulumi | 1 | 8.3% |
| Ubuntu | 1 | 8.3% |
| カスタム (Dockerfile) | 1 | 8.3% |

### 使用方法別の分布

| 使用方法 | 使用箇所数 |
|---------|-----------|
| `agent { docker }` | 9箇所 |
| `withDockerContainer` | 2箇所 |
| `agent { dockerfile }` | 1箇所 |

---

## イメージ一覧

### Python系イメージ

#### `python:3.11-slim`

**概要**: Python 3.11の軽量版イメージ

| 項目 | 詳細 |
|------|------|
| **公式イメージ** | Yes (Docker Hub) |
| **バージョン** | 3.11-slim |
| **ベースイメージ** | Debian Bookworm |
| **イメージサイズ** | 約130MB |
| **使用方法** | `agent { docker }` |

**使用箇所**:

1. **pull-request-comment-builder/Jenkinsfile**
   - **用途**: GitHub PRコメント自動生成
   - **パス**: `jenkins/jobs/pipeline/pr-automation/pull-request-comment-builder/Jenkinsfile`
   - **インストールパッケージ**: jinja2, PyGithub, python-dotenv
   - **実行内容**: PRコメントテンプレート処理、GitHub API連携

2. **diagram-generator/Jenkinsfile**
   - **用途**: アーキテクチャダイアグラム生成
   - **パス**: `jenkins/jobs/pipeline/docs-generator/diagram-generator/Jenkinsfile`
   - **インストールパッケージ**: diagrams, graphviz
   - **実行内容**: Python Diagramsライブラリを使用したインフラ図生成

**特徴**:
- 軽量で起動が高速
- Pythonスクリプトの実行に必要最小限のパッケージのみを含む
- pipでの追加パッケージインストールが容易

---

### Node.js系イメージ

#### `node:18-slim`

**概要**: Node.js 18の軽量版イメージ

| 項目 | 詳細 |
|------|------|
| **公式イメージ** | Yes (Docker Hub) |
| **バージョン** | 18-slim |
| **ベースイメージ** | Debian Bookworm |
| **イメージサイズ** | 約180MB |
| **使用方法** | `agent { docker }` |

**使用箇所**:

1. **mermaid-generator/Jenkinsfile**
   - **用途**: Mermaidダイアグラム生成
   - **パス**: `jenkins/jobs/pipeline/docs-generator/mermaid-generator/Jenkinsfile`
   - **インストールパッケージ**: @mermaid-js/mermaid-cli
   - **実行内容**: Mermaid記法からSVG/PNG画像生成

**特徴**:
- Node.js 18 LTSバージョン
- npmパッケージマネージャー標準搭載
- JavaScript/TypeScriptツールの実行に最適

---

### Rust系イメージ

#### `rust:1.76-slim`

**概要**: Rust 1.76の軽量版イメージ

| 項目 | 詳細 |
|------|------|
| **公式イメージ** | Yes (Docker Hub) |
| **バージョン** | 1.76-slim |
| **ベースイメージ** | Debian Bookworm |
| **イメージサイズ** | 約700MB |
| **使用方法** | `agent { docker }`, `withDockerContainer` |

**使用箇所**:

1. **rust-code-analysis-check/Jenkinsfile**
   - **用途**: 複数言語のコード品質解析
   - **パス**: `jenkins/jobs/pipeline/code-quality/rust-code-analysis-check/Jenkinsfile`
   - **使用方法**: `withDockerContainer`
   - **バージョン選択**:
     - デフォルト: `rust:1.76-slim`
     - Latest指定時: `rust:slim`
     - パラメータ指定時: `rust:${RUST_VERSION}-slim`
   - **インストールツール**: tokei, scc, cloc, loc
   - **対応言語**: Rust, Python, JavaScript, TypeScript, Go, Java, C/C++, Shell, など

2. **pr-complexity-analyzer/Jenkinsfile**
   - **用途**: PR複雑度解析
   - **パス**: `jenkins/jobs/pipeline/pr-automation/pr-complexity-analyzer/Jenkinsfile`
   - **使用方法**: `agent { docker }`
   - **バージョン**: 固定 (`CONSTANTS.DOCKER_IMAGE = 'rust:1.76-slim'`)
   - **インストールツール**: tokei
   - **実行内容**: PRの変更内容から複雑度指標を計算

**特徴**:
- Rustコンパイラとcargoを標準搭載
- 多言語対応のコード解析ツール（tokei、scc等）のビルドに利用
- cargoでのツールインストールが高速

**バージョン戦略**:
- **固定バージョン (1.76)**: 安定性重視（本番環境）
- **Latest (slim)**: 最新機能テスト用
- **パラメータ指定**: 特定バージョンでのテスト

---

### AWS系イメージ

#### `amazon/aws-cli:latest`

**概要**: AWS CLI公式イメージ

| 項目 | 詳細 |
|------|------|
| **公式イメージ** | Yes (AWS公式) |
| **バージョン** | latest |
| **ベースイメージ** | Amazon Linux 2023 |
| **イメージサイズ** | 約400MB |
| **使用方法** | `agent { docker }` |

**使用箇所**:

1. **ssm-dashboard/Jenkinsfile**
   - **用途**: AWS Systems Manager Parameter Store パラメータ収集
   - **パス**: `jenkins/jobs/pipeline/infrastructure/ssm-dashboard/Jenkinsfile`
   - **ステージ**: `Collect SSM Parameters`
   - **実行内容**:
     - SSMパラメータのリスト取得
     - パラメータ値の取得（SecureString対応）
     - JSON形式でのデータ出力
   - **認証方法**: EC2インスタンスロール or AWS認証情報パラメータ

2. **pulumi-dashboard/Jenkinsfile**
   - **用途**: PulumiステートファイルのS3収集
   - **パス**: `jenkins/jobs/pipeline/infrastructure/pulumi-dashboard/Jenkinsfile`
   - **ステージ**: `Collect Pulumi States`
   - **実行内容**:
     - S3バケットからPulumiステートファイル一覧取得
     - ステートファイルのダウンロード
     - メタデータ抽出
   - **認証方法**: EC2インスタンスロール or AWS認証情報パラメータ

**特徴**:
- AWS CLIバージョン2を標準搭載
- IAMロールベース認証に対応
- AWS SDK for Pythonも利用可能

**Dockerオプション**:
```groovy
args "--entrypoint='' -v ${WORKSPACE}:/workspace -w /workspace -u root"
```
- `--entrypoint=''`: デフォルトエントリーポイントを無効化
- `-u root`: root権限で実行（ファイル書き込み権限確保）
- `reuseNode true`: 同じノードでエージェントを再利用

---

### Pulumi系イメージ

#### `pulumi/pulumi:latest`

**概要**: Pulumi CLI公式イメージ

| 項目 | 詳細 |
|------|------|
| **公式イメージ** | Yes (Pulumi公式) |
| **バージョン** | latest |
| **ベースイメージ** | Debian |
| **イメージサイズ** | 約1GB |
| **使用方法** | `agent { docker }` |

**使用箇所**:

1. **pulumi-dashboard/Jenkinsfile**
   - **用途**: Pulumiステートデータの処理
   - **パス**: `jenkins/jobs/pipeline/infrastructure/pulumi-dashboard/Jenkinsfile`
   - **ステージ**: `Process State Data`
   - **実行内容**:
     - Pulumiステートファイルの解析
     - リソース情報の抽出
     - プロジェクト/スタック情報の集計
   - **インストールツール**: jq, python3

**特徴**:
- Pulumi CLI最新版を標準搭載
- 複数のクラウドプロバイダー対応（AWS, Azure, GCP等）
- Node.js、Python、Go等のランタイムを含む

**Dockerオプション**:
```groovy
args "--entrypoint='' -v ${WORKSPACE}:/workspace -w /workspace -u root"
```

---

### Ubuntu系イメージ

#### `ubuntu:22.04`

**概要**: Ubuntu 22.04 LTS公式イメージ

| 項目 | 詳細 |
|------|------|
| **公式イメージ** | Yes (Docker Hub) |
| **バージョン** | 22.04 (Jammy Jellyfish) |
| **LTSサポート** | 2027年4月まで |
| **イメージサイズ** | 約80MB |
| **使用方法** | `withDockerContainer` |

**使用箇所**:

1. **generate-doxygen-html/Jenkinsfile**
   - **用途**: Doxygen HTMLドキュメント生成
   - **パス**: `jenkins/jobs/pipeline/docs-generator/generate-doxygen-html/Jenkinsfile`
   - **実行内容**:
     - Doxygenのダウンロードとインストール
     - GraphvizとPython3のインストール
     - Doxygen実行によるAPIドキュメント生成
     - Doxygen Awesome CSSテーマの適用
   - **インストールパッケージ**:
     - `doxygen` (v1.13.2)
     - `graphviz`
     - `python3`

**特徴**:
- LTS版で長期サポート
- apt-getでのパッケージインストールが容易
- 豊富なパッケージリポジトリ

**Dockerオプション**:
```groovy
args "-u root -v ${WORKSPACE}:/workspace -w /workspace"
```

---

### Python + Node.js複合イメージ

#### `nikolaik/python-nodejs:python3.11-nodejs20`

**概要**: PythonとNode.jsの両方を含むマルチランタイムイメージ

| 項目 | 詳細 |
|------|------|
| **公式イメージ** | No (サードパーティ - Docker Hub認証済み) |
| **Pythonバージョン** | 3.11 |
| **Node.jsバージョン** | 20 |
| **ベースイメージ** | Debian |
| **イメージサイズ** | 約1GB |
| **使用方法** | `agent { docker }` |

**使用箇所**:

1. **auto-insert-doxygen-comment/Jenkinsfile**
   - **用途**: Doxygenコメント自動挿入
   - **パス**: `jenkins/jobs/pipeline/ai-automation/auto-insert-doxygen-comment/Jenkinsfile`
   - **実行内容**:
     - TypeScript/PythonコードへのDoxygenコメント挿入
     - OpenAI APIを使用したコメント生成
   - **Python要件**: openai, anthropic
   - **Node.js要件**: TypeScriptコンパイル、ts-node

2. **auto-insert-doxygen-comment/tests/Jenkinsfile**
   - **用途**: Doxygenコメント自動挿入のテスト
   - **パス**: `jenkins/jobs/pipeline/ai-automation/auto-insert-doxygen-comment/tests/Jenkinsfile`
   - **実行内容**: 単体テスト、統合テスト

3. **technical-docs-writer/Jenkinsfile**
   - **用途**: 技術ドキュメント自動作成
   - **パス**: `jenkins/jobs/pipeline/docs-generator/technical-docs-writer/Jenkinsfile`
   - **実行内容**:
     - ソースコード解析
     - OpenAI APIによるドキュメント生成
     - Markdownフォーマット出力
   - **Python要件**: openai, jinja2
   - **Node.js要件**: TypeScript処理、マークダウン変換

**特徴**:
- PythonとNode.jsの両方が必要なプロジェクトに最適
- pipとnpmの両方が使用可能
- AI系ツール（TypeScript + Python）の実行に便利

**メンテナンス元**:
- GitHub: https://github.com/nikolaik/docker-python-nodejs
- Docker Hub: https://hub.docker.com/r/nikolaik/python-nodejs

---

### カスタムイメージ

#### AI Workflow Orchestrator (Dockerfile)

**概要**: AI Workflow実行用カスタムビルドイメージ

| 項目 | 詳細 |
|------|------|
| **ビルド方法** | `agent { dockerfile }` |
| **Dockerfileパス** | `scripts/ai-workflow-v2/Dockerfile` |
| **ベースイメージ** | Node.js (バージョンはDockerfile依存) |
| **使用方法** | ビルド時にDockerfileから動的生成 |

**使用箇所**:

1. **ai-workflow-orchestrator/Jenkinsfile**
   - **用途**: AI Workflow実行環境（GitHub Issue → PR自動作成）
   - **パス**: `jenkins/jobs/pipeline/ai-workflow/ai-workflow-orchestrator/Jenkinsfile`
   - **実行内容**:
     - Claude Agent SDKの実行
     - GitHub API連携
     - OpenAI API連携
     - TypeScriptベースのワークフロー実行
   - **環境変数**:
     - `CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS=1`
     - `OPENAI_API_KEY`
     - `GITHUB_TOKEN`
     - `CLAUDE_CODE_CREDENTIALS_PATH`
   - **ボリュームマウント**:
     - ワークスペース全体をマウント
     - Claude認証情報ディレクトリマウント

**Dockerオプション**:
```groovy
dockerfile {
    label 'ec2-fleet'
    dir 'scripts/ai-workflow-v2'
    filename 'Dockerfile'
    args '-v ${WORKSPACE}:/workspace -w /workspace -e CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS=1 -e OPENAI_API_KEY=${OPENAI_API_KEY} -e GITHUB_TOKEN=${GITHUB_TOKEN} -e CLAUDE_CODE_CREDENTIALS_PATH=/home/node/.claude-code/credentials.json'
}
```

**特徴**:
- プロジェクト固有の依存関係を事前インストール
- TypeScript実行環境、ビルドツールを含む
- Claude Agent SDK、OpenAI SDK、GitHub SDKを含む
- ビルドキャッシュにより2回目以降の起動が高速化

**カスタマイズ推奨事項**:
- Dockerfileのベースイメージバージョン固定を推奨
- 依存パッケージのバージョンをpackage.jsonで明示的に管理
- マルチステージビルドによるイメージサイズ最適化

---

## メンテナンス推奨事項

### 定期的な更新タスク

#### 1. イメージバージョンの定期更新（四半期ごと）

| イメージ | 更新頻度 | チェック項目 |
|---------|---------|-------------|
| `python:3.11-slim` | 3ヶ月ごと | セキュリティパッチ、Python 3.12への移行検討 |
| `node:18-slim` | 3ヶ月ごと | Node.js 20 LTSへの移行検討 |
| `rust:1.76-slim` | 毎月 | 最新安定版への追従 |
| `amazon/aws-cli:latest` | 必要時のみ | AWS CLI破壊的変更の確認 |
| `pulumi/pulumi:latest` | 必要時のみ | Pulumi破壊的変更の確認 |
| `ubuntu:22.04` | 6ヶ月ごと | LTSサポート状況確認 |
| `nikolaik/python-nodejs:*` | 3ヶ月ごと | 上流イメージ更新確認 |

#### 2. セキュリティスキャン

```bash
# Trivyによる脆弱性スキャン（推奨）
trivy image python:3.11-slim
trivy image node:18-slim
trivy image rust:1.76-slim
trivy image amazon/aws-cli:latest
trivy image pulumi/pulumi:latest
trivy image ubuntu:22.04
trivy image nikolaik/python-nodejs:python3.11-nodejs20
```

#### 3. イメージサイズ最適化

- **多段階ビルド導入**: カスタムDockerfileでビルド依存とランタイム依存を分離
- **.dockerignore活用**: 不要なファイルをコンテキストから除外
- **Alpine Linuxの検討**: セキュリティとサイズのバランスを評価

#### 4. バージョン固定の検討

**現状の課題**:
- `latest`タグの使用は再現性を損なう可能性がある
- 予期しない破壊的変更のリスク

**推奨対応**:
```groovy
// ❌ 現状（latestタグ）
image 'amazon/aws-cli:latest'

// ✅ 推奨（バージョン固定）
image 'amazon/aws-cli:2.15.30'

// ✅ または環境変数で管理
image "amazon/aws-cli:${env.AWS_CLI_VERSION}"
```

---

## バージョン管理方針

### 推奨: 環境変数による集中管理

**jenkins/config/docker-images.properties** (例)

```properties
# Python
PYTHON_IMAGE=python:3.11.8-slim
PYTHON_NODEJS_IMAGE=nikolaik/python-nodejs:python3.11-nodejs20

# Node.js
NODE_IMAGE=node:20.11.1-slim

# Rust
RUST_IMAGE=rust:1.77.2-slim

# AWS
AWS_CLI_IMAGE=amazon/aws-cli:2.15.30

# Pulumi
PULUMI_IMAGE=pulumi/pulumi:3.109.0

# Ubuntu
UBUNTU_IMAGE=ubuntu:22.04

# Docker Image Update Date
LAST_UPDATED=2024-03-15
```

**Jenkinsfileでの使用例**:

```groovy
@Library('jenkins-shared-lib') _

pipeline {
    agent {
        docker {
            image dockerImages.PYTHON_IMAGE  // 共有ライブラリから取得
            args '--user root'
        }
    }
    // ...
}
```

### バージョン更新手順

1. **テスト環境で新バージョン検証**
   ```bash
   # ローカルテスト
   docker run --rm python:3.12-slim python --version
   ```

2. **プロパティファイル更新**
   ```bash
   vi jenkins/config/docker-images.properties
   git add jenkins/config/docker-images.properties
   git commit -m "[jenkins] update: Docker imageバージョン更新 (Python 3.11 → 3.12)"
   ```

3. **Staging環境でのテスト実行**

4. **Production環境への適用**

5. **このドキュメントの更新**

---

## トラブルシューティング

### よくある問題と解決方法

#### 1. イメージプル失敗

**症状**:
```
Error: failed to pull image "python:3.11-slim": manifest unknown
```

**原因**: ネットワーク問題またはタグ名の誤り

**解決方法**:
```groovy
// リトライロジック追加
retry(3) {
    docker.image('python:3.11-slim').inside {
        sh 'python --version'
    }
}
```

#### 2. 権限エラー

**症状**:
```
Permission denied: cannot write to /workspace
```

**解決方法**:
```groovy
// root権限で実行
args '-u root -v ${WORKSPACE}:/workspace'
```

#### 3. エントリーポイント衝突

**症状**:
```
Error: container exited immediately
```

**解決方法**:
```groovy
// エントリーポイントを無効化
args "--entrypoint=''"
```

---

## 関連ドキュメント

- [Jenkins README](./README.md) - Jenkinsプロジェクト全体のドキュメント
- [Jenkins CONTRIBUTION](./CONTRIBUTION.md) - 開発者向けガイドライン
- [Docker公式ドキュメント](https://docs.docker.com/)
- [Jenkins Docker Plugin](https://plugins.jenkins.io/docker-plugin/)

---

## 更新履歴

| 日付 | バージョン | 変更内容 | 担当者 |
|------|-----------|---------|--------|
| 2024-XX-XX | 1.0.0 | 初版作成 | Claude Code |

---

**最終更新日**: 2024-XX-XX
**ドキュメントオーナー**: Infrastructure Team
**レビュワー**: Platform Engineering Team
