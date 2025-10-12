# Jenkins CI/CD設定・ジョブ管理

Jenkins環境の設定、ジョブ定義、パイプライン、共有ライブラリを管理するディレクトリです。

## 📋 目次

- [概要](#概要)
- [ディレクトリ構造](#ディレクトリ構造)
- [初期セットアップ](#初期セットアップ)
- [Job DSL](#job-dsl)
- [パイプライン](#パイプライン)
- [共有ライブラリ](#共有ライブラリ)
- [設定管理](#設定管理)
- [セキュリティ](#セキュリティ)
- [ベストプラクティス](#ベストプラクティス)
- [トラブルシューティング](#トラブルシューティング)

## 概要

このディレクトリは、Jenkins環境の完全な設定とジョブ定義を含んでいます：

### 主要機能

- **Job DSL**: コードによるジョブ定義と管理
- **Pipeline as Code**: Jenkinsfileによるパイプライン定義
- **Shared Library**: 再利用可能な共通処理
- **Configuration as Code (JCasC)**: Jenkins設定の自動化
- **自動化ジョブ**: ドキュメント生成、コード品質チェック、管理タスク

### ジョブカテゴリ

#### フォルダ構成（ナンバリング体系）

| 番号 | カテゴリ | フォルダ名 | 説明 |
|------|----------|------------|------|
| 01 | [Admin] | Admin_Jobs | Jenkins管理・メンテナンス |
| 02 | [Admin] | Account_Setup | ユーザーアカウント管理 |
| 10 | [Deploy] | delivery-management-jobs | デリバリー・デプロイメント管理 |
| 20 | [Ops] | Infrastructure_Management | インフラ運用・保守 |
| 30 | [Quality] | Code_Quality_Checker | コード品質分析 |
| 31 | [Quality] | Document_Generator | ドキュメント自動生成 |
| 40 | [Test] | Shared_Library | 共有ライブラリテスト |
| 41 | [Test] | Pipeline_Tests | パイプラインテスト |
| 90 | [Sandbox] | Playgrounds | 個人作業・実験環境 |

#### カテゴリ分類ルール

- **01-09 [Admin]**: 管理系 - Jenkins自体の管理、ユーザー管理等
- **10-19 [Deploy]**: デプロイ系 - アプリケーション、インフラのデプロイ
- **20-29 [Ops]**: 運用系 - インフラの運用、メンテナンス、コスト最適化
- **30-39 [Quality]**: 品質系 - コード品質、ドキュメント生成
- **40-49 [Test]**: テスト系 - ライブラリ、パイプラインのテスト
- **90-99 [Sandbox]**: サンドボックス - 個人の実験、検証用

## ディレクトリ構造

```
jenkins/
├── INITIAL_SETUP.md        # 初期セットアップ手順
├── jobs/                   # ジョブ定義
│   ├── dsl/               # Job DSLスクリプト
│   │   ├── folders.groovy # フォルダ構造定義
│   │   ├── admin/         # 管理ジョブ
│   │   ├── account-setup/ # アカウント管理
│   │   ├── code-quality-checker/ # コード品質
│   │   ├── docs-generator/ # ドキュメント生成
│   │   └── shared-library/ # ライブラリテスト
│   ├── pipeline/          # Jenkinsfileとスクリプト
│   │   ├── _seed/         # シードジョブ
│   │   └── {category}/    # カテゴリ別パイプライン
│   └── shared/            # 共有ライブラリ
│       ├── src/           # Groovyクラス
│       └── vars/          # グローバル変数
└── scripts/               # ユーティリティスクリプト
    ├── jenkins/           # Jenkins設定スクリプト
    └── groovy/            # Groovy初期化スクリプト
```

## 初期セットアップ

### 1. 前提条件

- Jenkins 2.426.1以上
- 必要なプラグイン（後述）
- AWS環境へのアクセス権限
- GitHub連携設定

### 2. セットアップ手順

詳細は [INITIAL_SETUP.md](INITIAL_SETUP.md) を参照してください。

```bash
# 1. Jenkinsインスタンスの起動確認
curl -I http://jenkins.example.com/login

# 2. 初期管理者パスワードの取得（AWS SSM経由）
aws ssm get-parameter --name /jenkins-infra/dev/jenkins/admin-password \
  --with-decryption --query 'Parameter.Value' --output text

# 3. シードジョブの実行
# Jenkins UIから: Admin_Jobs > job-creator を実行
```

### 3. 必須プラグイン

以下のプラグインが必要です（自動インストール対応）：

- Job DSL
- Pipeline
- GitHub Branch Source
- AWS Credentials
- Configuration as Code
- Credentials Binding
- Timestamper
- AnsiColor
- Blue Ocean（オプション）

## 利用可能なジョブ

### ジョブカテゴリと主要ジョブ

| カテゴリ | 説明 | 主要ジョブ |
|---------|------|-----------|
| **Admin_Jobs** | システム管理 | backup-config（設定バックアップ）<br>restore-config（設定リストア）<br>ssm-parameter-backup（SSMパラメータバックアップ）<br>ssm-parameter-restore（SSMパラメータリストア）<br>github-webhooks-setting（GitHub Webhook設定）<br>github-deploykeys-setting（デプロイキー設定）<br>user-management（ユーザー管理） |
| **Account_Setup** | アカウント管理 | account-self-activation（アカウント自己有効化） |
| **AI_Workflow** | AI駆動開発自動化 | ai_workflow_orchestrator（9フェーズ自動開発ワークフロー） |
| **Code_Quality_Checker** | コード品質分析 | pr-complexity-analyzer（PR複雑度分析）<br>rust-code-analysis（Rustコード解析） |
| **Document_Generator** | ドキュメント生成 | auto-insert-doxygen-comment（Doxygenコメント自動挿入）<br>generate-doxygen-html（DoxygenHTML生成）<br>technical-docs-writer（技術文書作成）<br>pr-comment-builder（PRコメントビルダー） |
| **Infrastructure_Management** | インフラ管理 | shutdown-jenkins-environment（Jenkins環境停止）<br>terminate-lambda-nat（Lambda NAT削除）<br>Ansible Playbook実行、Pulumi Stack管理 |
| **Shared_Library** | ライブラリテスト | git-webhook-operation（Git Webhook操作）<br>jenkins-credentials-operation（認証情報操作）<br>aws-sqs-check-operation（SQS操作）<br>github-apps-basic-operation（GitHub Apps操作） |

### ジョブの実行方法

1. **Jenkins UIから実行**
   - Jenkinsダッシュボードにログイン
   - 対象のフォルダ（例：Admin_Jobs）を選択
   - 実行したいジョブをクリック
   - 「ビルド実行」または「Build with Parameters」をクリック

2. **Jenkins CLIから実行**
   ```bash
   # CLIのダウンロード
   wget http://jenkins.example.com/jnlpJars/jenkins-cli.jar
   
   # ジョブの実行
   java -jar jenkins-cli.jar -s http://jenkins.example.com build Admin_Jobs/backup-config \
     -p ENVIRONMENT=dev
   ```

3. **REST APIから実行**
   ```bash
   curl -X POST http://jenkins.example.com/job/Admin_Jobs/job/backup-config/build \
     --user username:api-token \
     --data-urlencode json='{"parameter": [{"name":"ENVIRONMENT", "value":"dev"}]}'
   ```

## パイプライン

### パイプラインの仕組み

各ジョブは`Jenkinsfile`で定義されたパイプラインとして実行されます。パイプラインは以下の特徴を持ちます：

- **宣言的パイプライン**: 構造化された形式で記述
- **ステージベース**: 準備→ビルド→テスト→デプロイなどのステージに分割
- **パラメータ化**: 実行時にパラメータを指定可能
- **共有ライブラリ連携**: 再利用可能な共通処理を利用

### パイプラインジョブのパラメータ

一般的なパラメータ：

| パラメータ名 | 説明 | デフォルト値 |
|------------|------|------------|
| ENVIRONMENT | 実行環境 | dev |
| BRANCH | 対象ブランチ | main |
| SKIP_TESTS | テストをスキップ | false |
| DRY_RUN | ドライラン実行 | false |
| DEBUG | デバッグモード | false |

## 共有ライブラリ

### 利用可能なユーティリティ

パイプライン内で使用できる共有ライブラリ機能：

| ライブラリ | 機能 | 主要メソッド |
|-----------|------|------------|
| **gitUtils** | Git/GitHub操作 | checkoutRepository（リポジトリチェックアウト）<br>postPRComment（PRコメント投稿）<br>createTag（タグ作成） |
| **awsUtils** | AWS操作 | uploadToS3（S3アップロード）<br>getParameter（SSMパラメータ取得）<br>sendSQSMessage（SQSメッセージ送信） |
| **jenkinsCliUtils** | Jenkins操作 | triggerJob（ジョブトリガー）<br>getJobStatus（ジョブステータス取得）<br>copyArtifacts（成果物コピー） |
| **ssmParameter** | SSMパラメータ取得 | get（単一パラメータ取得）<br>getMultiple（複数パラメータ一括取得）<br>getByPath（パス配下のパラメータ取得）<br>exists（存在確認）<br>withParameters（環境変数として設定） |

### 共有ライブラリの使用方法

パイプライン内で共有ライブラリを使用する例：

```groovy
// Jenkinsfileの先頭で宣言
@Library('jenkins-shared-library@main') _

pipeline {
    agent any
    stages {
        stage('Deploy to S3') {
            steps {
                script {
                    // S3へファイルをアップロード
                    awsUtils.uploadToS3(
                        source: 'build/output.zip',
                        bucket: 'my-bucket',
                        key: 'releases/output.zip'
                    )
                }
            }
        }

        stage('Get SSM Parameters') {
            steps {
                script {
                    // SSMパラメータの取得（リージョン明示的指定）
                    def dbPassword = ssmParameter.get('/jenkins/db/password', 'ap-northeast-1')

                    // 複数パラメータの一括取得
                    def params = ssmParameter.getMultiple([
                        '/jenkins/api/key',
                        '/jenkins/api/secret'
                    ], 'ap-northeast-1')

                    // 環境変数として設定して使用
                    ssmParameter.withParameters([
                        '/jenkins/db/username': 'DB_USER',
                        '/jenkins/db/password': 'DB_PASSWORD'
                    ], 'ap-northeast-1') {
                        sh 'echo "Database user: ${DB_USER}"'
                    }
                }
            }
        }
    }
}
```

## 設定管理

### Jenkins設定の管理方法

Jenkins設定は以下の方法で管理されています：

1. **Configuration as Code (JCasC)**
   - Jenkins設定をYAMLファイルで定義
   - `scripts/jenkins/casc/`ディレクトリに配置
   - 環境変数による設定値の注入

2. **Groovy初期化スクリプト**
   - Jenkins起動時に自動実行
   - プラグインインストール、基本設定、セキュリティ設定
   - `scripts/groovy/`ディレクトリに配置

### 設定項目

| 設定種別 | 説明 | 管理方法 |
|---------|------|---------|
| システム設定 | エクゼキューター数、メッセージ等 | JCasC |
| セキュリティ | 認証、認可、CSRF保護 | JCasC + Groovy |
| プラグイン | 必要なプラグインのリスト | Groovy |
| クレデンシャル | API トークン、パスワード | JCasC + SSM |
| クラウド設定 | EC2 Fleet、Docker設定 | JCasC |

## セキュリティ

### 環境変数

Jenkins全体で使用される環境変数（JCaSCで定義）：

| 環境変数名 | デフォルト値 | 用途 |
|-----------|------------|------|
| `GITHUB_APP_CREDENTIALS_ID` | `github-app-credentials` | GitHub App認証用のクレデンシャルID |
| `GITHUB_PAT_CREDENTIALS_ID` | `github-pat` | GitHub Personal Access Token用のクレデンシャルID |
| `GIT_INFRASTRUCTURE_REPO_URL` | `https://github.com/tielec/infrastructure-as-code.git` | インフラストラクチャーリポジトリのURL |
| `GIT_INFRASTRUCTURE_REPO_BRANCH` | `main` | デフォルトブランチ |

これらの環境変数は、Jenkinsfile内で`env.VARIABLE_NAME`として参照できます。

### クレデンシャル管理

| クレデンシャルID | 用途 | 種別 | 環境変数での参照 |
|-----------------|------|------|-----------------|
| github-token | GitHub API アクセス | Secret Text | - |
| github-app-credentials | GitHub リポジトリアクセス | Username/Password | `${GITHUB_APP_CREDENTIALS_ID}` |
| github-pat | GitHub Personal Access Token | Secret Text | `${GITHUB_PAT_CREDENTIALS_ID}` |
| aws-credentials | AWS リソースアクセス | AWS Credentials | - |
| docker-registry | Docker Registry認証 | Username/Password | - |

### セキュリティ設定

- **認証**: ローカルユーザーまたはLDAP/AD連携
- **認可**: ロールベースアクセス制御（RBAC）
- **CSRF保護**: 有効化済み
- **マスター実行制限**: マスターノードでのビルド無効化
- **監査ログ**: すべての操作を記録

### 重要なジョブの詳細

#### Admin_Jobs/SSM_Parameter_Backup

**目的**: SSM Parameter Storeのパラメータを定期的にバックアップ

**機能**:
- 環境文字列を含むSSMパラメータを自動取得（パスに /dev/ または /prod/ を含む）
- すべてのパラメータタイプ（SecureString含む）をバックアップ
- JSON形式でS3バケットに保存
- 日付ベースのディレクトリ構造で整理
- S3ライフサイクルポリシーにより30日経過後に自動削除

**パラメータ**:
- `ENVIRONMENT`: バックアップ対象の環境（dev/prod）
- `DRY_RUN`: 実際のバックアップを行わず確認のみ（デフォルト: false）

**実行スケジュール**: 毎日 JST 03:00（UTC 18:00）

#### Admin_Jobs/SSM_Parameter_Restore

**目的**: バックアップからSSMパラメータをリストア

**機能**:
- 常に最新のバックアップからリストア
- 環境に対応するパラメータを自動フィルタリング（パスに /dev/ または /prod/ を含む）
- 変更内容の事前確認（ドライランモード）
- 既存パラメータの上書き制御

**パラメータ**:
- `ENVIRONMENT`: リストア対象の環境（dev/prod）
- `DRY_RUN`: 実際のリストアを行わず確認のみ（デフォルト: true）
- `FORCE_OVERWRITE`: 既存パラメータの強制上書き

#### Infrastructure_Management/Shutdown_Jenkins_Environment

**目的**: Jenkins環境全体を安全に停止

**停止対象**:
- EC2 Fleet (SpotFleet) エージェント - キャパシティを0に設定
- NAT インスタンス - インスタンスを停止
- Jenkins Controller インスタンス - 非同期で停止

**パラメータ**:
- `AWS_REGION`: 対象のAWSリージョン
- `CONFIRM_SHUTDOWN`: 停止実行の確認（必須）
- `SHUTDOWN_MODE`: graceful（推奨）またはimmediate
- `WAIT_TIMEOUT_MINUTES`: エージェント完了待機時間（デフォルト30分）
- `DRY_RUN`: 実際の停止を行わず確認のみ

**注意事項**:
- このジョブはJenkins自身を停止するため、実行後アクセスできなくなります
- 停止処理は非同期で実行され、ジョブは成功として終了します
- 環境の再起動はAWSコンソールから手動で行う必要があります
- 実行前に他の実行中ジョブがないことを確認してください

**使用例**:
```bash
# ドライランで停止対象を確認
DRY_RUN=true で実行

# 本番環境を安全に停止
CONFIRM_SHUTDOWN=true
SHUTDOWN_MODE=graceful
WAIT_TIMEOUT_MINUTES=30
```

#### Ansible Playbook Executor

**目的**: Workterminalを使用してAnsibleプレイブックを実行

**主な機能**:
- 単一または複数のプレイブックを順番に実行
- job-config.yamlで定義されたプレイブックを動的にジョブ化
- チェックモード、タグ制御、詳細出力などのオプション

**パラメータ**:
- `PLAYBOOKS`: 実行するプレイブック（カンマ区切りで複数指定可能）
- `ENVIRONMENT`: 実行環境（dev/staging/prod）
- `BRANCH`: リポジトリブランチ
- `ANSIBLE_EXTRA_VARS`: 追加のAnsible変数
- `ANSIBLE_VERBOSE`: 詳細出力の有効化
- `ANSIBLE_CHECK`: チェックモード（変更なし）
- `ANSIBLE_LIMIT`: ホストの制限
- `ANSIBLE_TAGS`: 実行するタグ
- `ANSIBLE_SKIP_TAGS`: スキップするタグ
- `DRY_RUN`: 実行コマンドの確認のみ
- `USE_NOHUP`: バックグラウンド実行（長時間タスク用、job-configで有効化されたジョブのみ）
- `NOHUP_TIMEOUT_MINUTES`: nohup実行時のタイムアウト時間
- `NOHUP_LOG_PATH`: nohup実行時のログファイルパス

**実行例**:
```bash
# 単一プレイブック実行
PLAYBOOKS: jenkins/deploy/deploy_jenkins_network.yml
ENVIRONMENT: dev

# 複数プレイブック実行（Jenkins完全セットアップ）
PLAYBOOKS: jenkins_deploy_ssm_init,jenkins_deploy_network,jenkins_deploy_security
ENVIRONMENT: dev

# nohupモードで長時間実行（job-configで有効化されたジョブのみ）
PLAYBOOKS: jenkins_deploy_controller
ENVIRONMENT: dev
USE_NOHUP: true
NOHUP_TIMEOUT_MINUTES: 30
```

**nohup実行について**:
- `enable_nohup: true`が設定されたプレイブックではnohupオプションが表示されます
- バックグラウンドで実行され、進捗状況は定期的に表示されます
- ログファイルはWorkterminalの指定パスに保存されます
- タイムアウト時間を超えるとプロセスは自動的に終了されます
- `continue_on_timeout`設定により、タイムアウト時の動作を制御可能：
  - `true`: タイムアウトしても次のプレイブックを実行（削除処理などで推奨）
  - `false`: タイムアウトでエラー終了（重要なデプロイ処理で推奨）

**定義済みプレイブック**:
- `jenkins-deploy/*`: Jenkins環境のデプロイ
- `jenkins-remove/*`: Jenkins環境の削除
- `jenkins-pipeline/*`: 複数プレイブックのチェーン実行
- `lambda/*`: Lambda関数の管理
- `test/*`: テストプレイブック

#### Infrastructure_Management/Shutdown-Environment-Scheduler

**目的**: 開発環境を毎日定時に自動停止してコストを最適化

**実行タイミング**:
- 日本時間（JST）午前0時
- 平日のみ（月曜日〜金曜日）
- 週末（土日）は実行されません

**動作内容**:
- `Infrastructure_Management/Shutdown_Jenkins_Environment`ジョブを自動トリガー
- 固定パラメータで実行:
  - `ENVIRONMENT`: dev（開発環境のみ）
  - `AWS_REGION`: ap-northeast-1
  - `SHUTDOWN_MODE`: graceful
  - `WAIT_TIMEOUT_MINUTES`: 30
  - `CONFIRM_SHUTDOWN`: true
  - `DRY_RUN`: false

**特徴**:
- Freestyleジョブ（Pipelineではない）
- パラメータは固定値（スケジュール実行のため変更不可）
- 並行実行は無効化
- ビルド履歴は30日間/90ビルド保持

**注意事項**:
- 本番環境（prod）は対象外
- dev環境のみが自動停止されます
- 停止を防ぐには、ジョブを手動で無効化してください
- 祝日の自動スキップは現在未対応

**管理方法**:
```bash
# スケジュールを一時的に無効化
Jenkins UI > Infrastructure_Management > Shutdown-Environment-Scheduler > 設定 > ビルドトリガから"Build periodically"のチェックを外す

# 手動実行
Jenkins UI > Infrastructure_Management > Shutdown-Environment-Scheduler > "Build Now"をクリック
```

#### AI_Workflow/ai_workflow_orchestrator

**目的**: GitHub IssueからClaude AIが自動的に開発プロセスを実行（9フェーズワークフロー）

**主な機能**:
- Phase 0（Planning）: プロジェクト計画、実装戦略・テスト戦略の事前決定
- Phase 1（Requirements）: 要件定義書の自動生成
- Phase 2（Design）: 詳細設計書の自動生成
- Phase 3（Test Scenario）: テストシナリオの自動生成
- Phase 4（Implementation）: 本番コード実装の自動実行
- Phase 5（Test Implementation）: テストコード実装の自動実行
- Phase 6（Testing）: テスト実行と結果レポート
- Phase 7（Documentation）: ドキュメント更新
- Phase 8（Report）: 全体レポート生成

**パラメータ**:
- `ISSUE_URL`: GitHub Issue URL（必須）
- `START_PHASE`: 開始フェーズ（デフォルト: planning）
  - 選択肢: planning, requirements, design, test_scenario, implementation, test_implementation, testing, documentation, report
  - 推奨: `planning`（Phase 0から開始することで、後続フェーズの効率が向上）
- `DRY_RUN`: ドライラン実行（デフォルト: false）
- `SKIP_REVIEW`: レビュースキップ（デフォルト: false）
- `MAX_RETRIES`: 最大リトライ回数（デフォルト: 3）
- `COST_LIMIT_USD`: コスト上限USD（デフォルト: 5.0）

**実行例**:
```bash
# Planning Phaseから全フェーズを実行（推奨）
START_PHASE: planning
ISSUE_URL: https://github.com/tielec/infrastructure-as-code/issues/332

# Requirements Phaseから実行（Planning Phaseをスキップ）
START_PHASE: requirements
ISSUE_URL: https://github.com/tielec/infrastructure-as-code/issues/332
```

**Planning Phase（Phase 0）の重要性**:
- **実装戦略の事前決定**: CREATE/EXTEND/REFACTORを判断し、Phase 2以降の負荷を軽減
- **テスト戦略の事前決定**: UNIT_ONLY/INTEGRATION_ONLY/ALL等を判断し、Phase 3の方針を明確化
- **Issue複雑度分析**: 工数見積もり、リスク評価、タスク分割を実施
- **開発計画書の生成**: planning.mdとして保存され、全フェーズで参照可能

**Phase間の連携**:
- Planning Phaseの成果物（planning.md）は後続の全Phase（Requirements～Report）で自動的に参照される
- Planning Phaseをスキップした場合でも、各Phaseは正常に動作する（警告ログのみ出力）

**成果物の自動投稿**:
- 各Phase完了後、成果物がGitHub Issueコメントとして自動投稿される
- レビュー結果とフィードバックもIssueコメントとして記録される

**Git自動commit & push**:
- 各Phase完了後、成果物が自動的にGitにcommit & pushされる
- ブランチ: `ai-workflow/issue-{番号}`
- コミットメッセージフォーマット: `[ai-workflow] Phase X (phase_name) - completed/failed`

**詳細ドキュメント**: [scripts/ai-workflow/README.md](../scripts/ai-workflow/README.md)

#### Infrastructure_Management/Terminate_Lambda_NAT

**目的**: Lambda NAT Instanceを夜間に自動削除してコスト削減

**実行タイミング**:
- 日本時間（JST）23:30（毎日）
- 開発環境のみ対象

**削除対象リソース**:
- NAT Instance (EC2)
- Elastic IP
- ルートテーブルのルート設定
- CloudWatchアラーム
- SSMパラメータ

**パラメータ（固定値）**:
- `ACTION`: destroy
- `PULUMI_PROJECT_PATH`: pulumi/lambda-nat
- `GENERATE_REPORT`: false
- `ENVIRONMENT`: dev
- `SKIP_CONFIRMATION`: true

**特徴**:
- 既存の`pulumi-stack-action`パイプラインを再利用
- 夜間はLambda実行がないため削除してコスト削減
- 朝の再作成は手動または別ジョブで実施
- Elastic IPも削除されるため、再作成時は新しいIPが割り当てられる

**注意事項**:
- 削除中はLambda関数から外部APIへのアクセス不可
- Elastic IPが変わるため、IP制限がある外部APIは再設定が必要
- 再作成時はルーティングが自動的に再設定される

**管理方法**:
```bash
# 手動削除
Jenkins UI > Infrastructure_Management > Terminate_Lambda_NAT > "Build Now"

# 手動再作成（コマンドライン）
cd pulumi/lambda-nat
pulumi up -y

# スケジュール無効化
Jenkins UI > Infrastructure_Management > Terminate_Lambda_NAT > 設定 > ビルドトリガから"Build periodically"のチェックを外す
```

## トラブルシューティング

### よくある問題と解決方法

| 問題 | 原因 | 解決方法 |
|-----|------|---------|
| ジョブが見つからない | Job DSLが未反映 | Admin_Jobs > job-creator を実行 |
| クレデンシャルエラー | ID不一致または権限不足 | Credentials画面でIDを確認、権限を付与 |
| ビルド失敗 | エージェント不足 | エージェントのラベルと状態を確認 |
| 共有ライブラリエラー | ライブラリ未設定 | Global Pipeline Librariesで設定 |
| プラグインエラー | プラグイン未インストール | Plugin Managerから必要なプラグインをインストール |

### ログ確認方法

| ログ種別 | 確認方法 |
|---------|---------|
| ジョブコンソール | ジョブページ > Console Output |
| システムログ | Manage Jenkins > System Log |
| エージェントログ | ノード管理 > 対象ノード > ログ |
| マスターログ | `/var/log/jenkins/jenkins.log` |

## 開発者向け情報

ジョブやパイプラインの開発方法については[CONTRIBUTION.md](CONTRIBUTION.md)を参照してください。

## 関連ドキュメント

### プロジェクトドキュメント
- [メインREADME](../README.md) - プロジェクト全体の概要
- [INITIAL_SETUP.md](INITIAL_SETUP.md) - Jenkins初期セットアップ手順
- [CONTRIBUTION.md](CONTRIBUTION.md) - Jenkinsジョブ開発規約
- [Ansible README](../ansible/README.md) - インフラのデプロイ方法
- [Pulumi README](../pulumi/README.md) - インフラストラクチャ定義

### 外部リソース
- [Jenkins公式ドキュメント](https://www.jenkins.io/doc/)
- [Jenkins Plugin Index](https://plugins.jenkins.io/)

## サポート

問題が発生した場合は、以下を確認してください：

1. このREADMEのトラブルシューティングセクション
2. 各ジョブのJenkinsfileのコメント
3. [Jenkins公式ドキュメント](https://www.jenkins.io/doc/)
4. [Jenkins Plugin Index](https://plugins.jenkins.io/)

## ライセンス

このプロジェクトは内部利用を目的としています。詳細は[LICENSE](../LICENSE)を参照してください。