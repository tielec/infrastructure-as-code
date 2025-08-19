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

- **Admin Jobs**: Jenkins管理・メンテナンス
- **Account Setup**: ユーザーアカウント管理
- **Code Quality Checker**: コード品質分析
- **Docs Generator**: ドキュメント自動生成
- **Shared Library Tests**: 共有ライブラリのテスト

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

## Job DSL

### 概要

Job DSLを使用してジョブをコードとして管理します。すべてのジョブ定義は `jobs/dsl/` ディレクトリに配置されています。

### フォルダ構造

```groovy
// jobs/dsl/folders.groovy
folder('Admin_Jobs') {
    displayName('管理ジョブ')
    description('システム管理用のジョブ群')
}

folder('Account_Setup') {
    displayName('アカウント設定')
    description('ユーザーアカウント管理ジョブ')
}

folder('Code_Quality_Checker') {
    displayName('コード品質チェッカー')
    description('コード品質分析ジョブ')
}

folder('Docs_Generator') {
    displayName('ドキュメント生成')
    description('自動ドキュメント生成ジョブ')
}
```

### ジョブ定義例

```groovy
// jobs/dsl/admin/admin_backup_config_job.groovy
pipelineJob('Admin_Jobs/backup-config') {
    displayName('設定バックアップ')
    description('Jenkins設定をS3にバックアップ')
    
    definition {
        cpsScm {
            scm {
                git {
                    remote {
                        url('https://github.com/org/jenkins-config.git')
                        credentials('github-credentials')
                    }
                    branches('*/main')
                }
            }
            scriptPath('jobs/pipeline/admin/backup-config/Jenkinsfile')
        }
    }
    
    triggers {
        cron('H 2 * * *') // 毎日午前2時に実行
    }
    
    properties {
        buildDiscarder {
            logRotator {
                daysToKeep(30)
                numToKeep(10)
            }
        }
    }
}
```

### GitHub連携ジョブ

```groovy
// GitHub Webhookトリガージョブ
pipelineJob('Docs_Generator/pr-comment-builder-github-trigger') {
    displayName('PRコメント生成（GitHub連携）')
    
    properties {
        githubProjectUrl('https://github.com/org/repo')
    }
    
    triggers {
        genericTrigger {
            genericVariables {
                genericVariable {
                    key('action')
                    value('$.action')
                }
                genericVariable {
                    key('pr_number')
                    value('$.pull_request.number')
                }
            }
            causeString('GitHub PR Event: $action on PR #$pr_number')
            token('pr-comment-token')
            regexpFilterText('$action')
            regexpFilterExpression('^(opened|synchronize)$')
        }
    }
}
```

## パイプライン

### Jenkinsfile構造

標準的なJenkinsfileの構造：

```groovy
// jobs/pipeline/{category}/{job-name}/Jenkinsfile
pipeline {
    agent { label 'ec2-fleet' }
    
    options {
        timestamps()
        ansiColor('xterm')
        timeout(time: 1, unit: 'HOURS')
        buildDiscarder(logRotator(daysToKeep: 30, numToKeep: 10))
    }
    
    environment {
        AWS_REGION = 'ap-northeast-1'
        GITHUB_TOKEN = credentials('github-token')
    }
    
    parameters {
        string(name: 'BRANCH', defaultValue: 'main', description: 'ブランチ名')
        choice(name: 'ENVIRONMENT', choices: ['dev', 'staging', 'prod'], description: '環境')
    }
    
    stages {
        stage('準備') {
            steps {
                script {
                    echo "環境: ${params.ENVIRONMENT}"
                    echo "ブランチ: ${params.BRANCH}"
                }
            }
        }
        
        stage('ビルド') {
            steps {
                sh '''
                    echo "ビルド処理"
                    # ビルドコマンド
                '''
            }
        }
        
        stage('テスト') {
            steps {
                sh '''
                    echo "テスト実行"
                    # テストコマンド
                '''
            }
        }
        
        stage('デプロイ') {
            when {
                expression { params.ENVIRONMENT == 'prod' }
            }
            steps {
                input message: '本番環境へのデプロイを承認しますか？'
                sh '''
                    echo "デプロイ実行"
                    # デプロイコマンド
                '''
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
        success {
            echo 'パイプライン成功'
        }
        failure {
            echo 'パイプライン失敗'
            // 通知処理
        }
    }
}
```

### パイプライン例

#### ドキュメント生成パイプライン

```groovy
// jobs/pipeline/docs-generator/auto-insert-doxygen-comment/Jenkinsfile
pipeline {
    agent { label 'python' }
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r src/requirements.txt
                '''
            }
        }
        
        stage('Generate Comments') {
            steps {
                sh '''
                    . venv/bin/activate
                    python src/main.py \
                        --input ${WORKSPACE}/target \
                        --output ${WORKSPACE}/output \
                        --language python
                '''
            }
        }
        
        stage('Commit Changes') {
            steps {
                script {
                    gitUtils.commitAndPush(
                        branch: params.BRANCH,
                        message: 'docs: Doxygenコメントを自動追加',
                        files: 'output/**'
                    )
                }
            }
        }
    }
}
```

#### コード品質チェックパイプライン

```groovy
// jobs/pipeline/code-quality-checker/pr-complexity-analyzer/Jenkinsfile
pipeline {
    agent { label 'docker' }
    
    stages {
        stage('Checkout PR') {
            steps {
                script {
                    gitUtils.checkoutPullRequest(params.PR_NUMBER)
                }
            }
        }
        
        stage('Analyze Complexity') {
            steps {
                sh '''
                    ./scripts/analyze_complexity.sh
                    python src/pr_complexity_comment_generator.py \
                        --pr ${PR_NUMBER} \
                        --threshold-file config/complexity_thresholds.json
                '''
            }
        }
        
        stage('Post Comment') {
            steps {
                script {
                    def comment = readFile('complexity_report.md')
                    gitUtils.postPRComment(
                        pr: params.PR_NUMBER,
                        comment: comment
                    )
                }
            }
        }
    }
}
```

## 共有ライブラリ

### 構造

```
jobs/shared/
├── src/jp/co/tielec/          # パッケージ構造
│   ├── aws/                   # AWSユーティリティ
│   │   ├── AwsGeneralUtils.groovy
│   │   └── AwsSqsUtils.groovy
│   ├── git/                   # Git/GitHub操作
│   │   ├── GitClientBase.groovy
│   │   ├── GitHubApiClient.groovy
│   │   └── GitHubPullRequest.groovy
│   └── jenkins/               # Jenkins操作
│       └── JenkinsCliClient.groovy
└── vars/                      # グローバル変数
    ├── awsUtils.groovy
    ├── gitUtils.groovy
    └── jenkinsCliUtils.groovy
```

### 使用例

#### gitUtils

```groovy
// vars/gitUtils.groovy
def checkoutRepository(Map config) {
    checkout([
        $class: 'GitSCM',
        branches: [[name: config.branch ?: 'main']],
        userRemoteConfigs: [[
            url: config.url,
            credentialsId: config.credentials ?: 'github-credentials'
        ]]
    ])
}

def deployKeys(Map config) {
    def client = new jp.co.tielec.git.GitHubApiClient()
    client.setupDeployKey(
        repo: config.repo,
        key: config.key,
        title: config.title ?: 'Jenkins Deploy Key'
    )
}

def postPRComment(Map config) {
    def pr = new jp.co.tielec.git.GitHubPullRequest()
    pr.postComment(
        number: config.pr,
        body: config.comment
    )
}
```

#### awsUtils

```groovy
// vars/awsUtils.groovy
def uploadToS3(Map config) {
    sh """
        aws s3 cp ${config.source} s3://${config.bucket}/${config.key} \
            --region ${config.region ?: 'ap-northeast-1'}
    """
}

def getParameter(String name) {
    def utils = new jp.co.tielec.aws.AwsGeneralUtils()
    return utils.getSSMParameter(name)
}

def sendSQSMessage(Map config) {
    def sqs = new jp.co.tielec.aws.AwsSqsUtils()
    sqs.sendMessage(
        queueUrl: config.queueUrl,
        messageBody: config.message
    )
}
```

### クラスライブラリ例

```groovy
// src/jp/co/tielec/git/GitHubApiClient.groovy
package jp.co.tielec.git

class GitHubApiClient implements Serializable {
    
    private String baseUrl = "https://api.github.com"
    private String token
    
    GitHubApiClient(String token = null) {
        this.token = token ?: System.getenv('GITHUB_TOKEN')
    }
    
    def getRepository(String owner, String repo) {
        def url = "${baseUrl}/repos/${owner}/${repo}"
        return makeRequest('GET', url)
    }
    
    def createWebhook(Map config) {
        def url = "${baseUrl}/repos/${config.owner}/${config.repo}/hooks"
        def payload = [
            name: 'web',
            active: true,
            events: config.events ?: ['push', 'pull_request'],
            config: [
                url: config.webhookUrl,
                content_type: 'json',
                secret: config.secret
            ]
        ]
        return makeRequest('POST', url, payload)
    }
    
    private def makeRequest(String method, String url, Map body = null) {
        // HTTPリクエスト実装
    }
}
```

## 設定管理

### Configuration as Code (JCasC)

Jenkins設定をYAMLで管理（scripts/jenkins/casc/配下に配置）：

```yaml
# scripts/jenkins/casc/jenkins.yaml.template
jenkins:
  systemMessage: "Jenkins ${JENKINS_VERSION} - 環境: ${ENVIRONMENT}"
  numExecutors: 2
  mode: NORMAL
  
  securityRealm:
    local:
      allowsSignup: false
      users:
        - id: "${ADMIN_USER}"
          password: "${ADMIN_PASSWORD}"
  
  authorizationStrategy:
    globalMatrix:
      permissions:
        - "Overall/Administer:admin"
        - "Overall/Read:authenticated"
  
  clouds:
    - amazonEC2:
        name: "ec2-fleet"
        region: "${AWS_REGION}"
        useInstanceProfileForCredentials: true

credentials:
  system:
    domainCredentials:
      - credentials:
          - string:
              scope: GLOBAL
              id: "github-token"
              secret: "${GITHUB_TOKEN}"
              description: "GitHub API Token"
          - usernamePassword:
              scope: GLOBAL
              id: "github-credentials"
              username: "${GITHUB_USER}"
              password: "${GITHUB_PASSWORD}"

unclassified:
  location:
    url: "${JENKINS_URL}"
    adminAddress: "${ADMIN_EMAIL}"
  
  gitHubPluginConfig:
    configs:
      - name: "GitHub"
        apiUrl: "https://api.github.com"
        credentialsId: "github-token"
```

### Groovy初期化スクリプト

Jenkinsの初期設定用Groovyスクリプト：

```groovy
// scripts/groovy/basic-settings.groovy
import jenkins.model.*
import hudson.security.*

def instance = Jenkins.getInstance()

// 基本設定
instance.setSystemMessage("Jenkins CI/CD - Production Ready")
instance.setNumExecutors(2)
instance.setQuietPeriod(5)

// CSRF保護を有効化
instance.setCrumbIssuer(new DefaultCrumbIssuer(true))

// マスターでのビルドを無効化
instance.setMode(hudson.model.Node.Mode.EXCLUSIVE)

instance.save()
```

```groovy
// scripts/groovy/install-plugins.groovy
import jenkins.model.*
import java.util.logging.Logger

def logger = Logger.getLogger("")
def installed = false
def initialized = false

def plugins = [
    "job-dsl",
    "pipeline",
    "git",
    "github-branch-source",
    "aws-credentials",
    "configuration-as-code",
    "timestamper",
    "ansicolor"
]

def instance = Jenkins.getInstance()
def pm = instance.getPluginManager()
def uc = instance.getUpdateCenter()

plugins.each { plugin ->
    if (!pm.getPlugin(plugin)) {
        logger.info("Installing plugin: ${plugin}")
        def installFuture = uc.getPlugin(plugin).install()
        installFuture.get()
        installed = true
    }
}

if (installed) {
    instance.save()
    instance.restart()
}
```

## セキュリティ

### クレデンシャル管理

```groovy
// クレデンシャルの作成（Groovyスクリプト）
import jenkins.model.*
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.common.*
import com.cloudbees.plugins.credentials.domains.*
import com.cloudbees.plugins.credentials.impl.*
import org.jenkinsci.plugins.plaincredentials.impl.*

def store = Jenkins.instance.getExtensionList('com.cloudbees.plugins.credentials.SystemCredentialsProvider')[0].getStore()

// 文字列クレデンシャル
def githubToken = new StringCredentialsImpl(
    CredentialsScope.GLOBAL,
    "github-token",
    "GitHub API Token",
    hudson.util.Secret.fromString(System.getenv("GITHUB_TOKEN"))
)

// ユーザー名/パスワード
def githubCreds = new UsernamePasswordCredentialsImpl(
    CredentialsScope.GLOBAL,
    "github-credentials",
    "GitHub Credentials",
    System.getenv("GITHUB_USER"),
    System.getenv("GITHUB_PASSWORD")
)

store.addCredentials(Domain.global(), githubToken)
store.addCredentials(Domain.global(), githubCreds)
```

### セキュリティベストプラクティス

1. **最小権限の原則**
   - ジョブごとに必要最小限の権限のみ付与
   - フォルダーレベルでの権限管理

2. **クレデンシャルの暗号化**
   - すべての機密情報はJenkins Credentials Storeで管理
   - SSM Parameter Storeとの連携

3. **監査ログ**
   - すべてのジョブ実行を記録
   - 設定変更の追跡

4. **ネットワークセキュリティ**
   - プライベートサブネットでの実行
   - セキュリティグループによるアクセス制限

## ベストプラクティス

### ジョブ設計

1. **単一責任の原則**
   ```groovy
   // ✅ 良い例：単一の目的
   pipelineJob('test-unit') {
       // ユニットテストのみ
   }
   
   // ❌ 悪い例：複数の責任
   pipelineJob('test-build-deploy-all') {
       // すべてを1つのジョブで
   }
   ```

2. **パラメータ化**
   ```groovy
   parameters {
       string(name: 'BRANCH', defaultValue: 'main')
       choice(name: 'ENV', choices: ['dev', 'staging', 'prod'])
       booleanParam(name: 'SKIP_TESTS', defaultValue: false)
   }
   ```

3. **エラーハンドリング**
   ```groovy
   stage('Critical Step') {
       steps {
           script {
               try {
                   // 重要な処理
               } catch (Exception e) {
                   currentBuild.result = 'FAILURE'
                   error "Critical step failed: ${e.message}"
               }
           }
       }
   }
   ```

### パイプライン設計

1. **ステージの明確化**
   ```groovy
   stages {
       stage('準備') { /* ... */ }
       stage('ビルド') { /* ... */ }
       stage('テスト') { /* ... */ }
       stage('デプロイ') { /* ... */ }
   }
   ```

2. **並列実行の活用**
   ```groovy
   stage('Tests') {
       parallel {
           stage('Unit Tests') { /* ... */ }
           stage('Integration Tests') { /* ... */ }
           stage('Lint') { /* ... */ }
       }
   }
   ```

3. **適切なエージェント選択**
   ```groovy
   agent {
       label 'docker && linux'
   }
   // または
   agent {
       docker {
           image 'python:3.9'
       }
   }
   ```

### 共有ライブラリ設計

1. **インターフェース統一**
   ```groovy
   // すべてのメソッドでMapパラメータを使用
   def deploy(Map config) {
       validateConfig(config)
       // 処理
   }
   ```

2. **エラー処理**
   ```groovy
   def validateConfig(Map config) {
       if (!config.repo) {
           error "Repository is required"
       }
   }
   ```

3. **ログ出力**
   ```groovy
   def process(Map config) {
       echo "[INFO] Starting process: ${config.name}"
       // 処理
       echo "[INFO] Process completed: ${config.name}"
   }
   ```

## トラブルシューティング

### よくある問題

#### 1. ジョブが見つからない

```groovy
// シードジョブを実行してJob DSLを反映
// Admin_Jobs > job-creator を手動実行
```

#### 2. クレデンシャルエラー

```groovy
// クレデンシャルIDの確認
// Jenkins UI > Credentials で確認
// またはGroovyコンソールで：
Jenkins.instance.getExtensionList('com.cloudbees.plugins.credentials.SystemCredentialsProvider')[0]
    .getStore()
    .getCredentials(Domain.global())
    .each { println "${it.id}: ${it.description}" }
```

#### 3. パイプラインのデバッグ

```groovy
// デバッグ情報の出力
stage('Debug') {
    steps {
        sh 'printenv | sort'
        script {
            echo "Workspace: ${env.WORKSPACE}"
            echo "Build ID: ${env.BUILD_ID}"
            echo "Parameters: ${params}"
        }
    }
}
```

#### 4. 共有ライブラリが読み込めない

```groovy
// Jenkinsfileの先頭で明示的に読み込み
@Library('jenkins-shared-library@main') _

// または設定で自動読み込み
// Manage Jenkins > Configure System > Global Pipeline Libraries
```

### ログ確認

```bash
# Jenkinsマスターログ
sudo tail -f /var/log/jenkins/jenkins.log

# ジョブコンソール出力
curl -u admin:password http://jenkins.example.com/job/JobName/lastBuild/consoleText

# システム情報
curl -u admin:password http://jenkins.example.com/systemInfo
```

### パフォーマンス最適化

1. **ビルドエージェントの活用**
   - マスターノードでビルドしない
   - 適切なエージェントラベルの使用

2. **キャッシュの活用**
   ```groovy
   // 依存関係のキャッシュ
   stage('Cache Dependencies') {
       steps {
           cache(maxCacheSize: 250, caches: [
               arbitraryFileCache(
                   path: 'node_modules',
                   includes: '**/*',
                   fingerprinting: true
               )
           ]) {
               sh 'npm install'
           }
       }
   }
   ```

3. **不要なステップの削除**
   ```groovy
   // 条件付き実行
   when {
       not {
           changelog '.*\\[skip ci\\].*'
       }
   }
   ```

## 関連ドキュメント

- [メインREADME](../README.md) - プロジェクト全体の概要
- [INITIAL_SETUP.md](INITIAL_SETUP.md) - Jenkins初期セットアップ手順
- [Ansible README](../ansible/README.md) - インフラのデプロイ方法
- [Pulumi README](../pulumi/README.md) - インフラストラクチャ定義
- [CLAUDE.md](../CLAUDE.md) - 開発者向けガイドライン

## サポート

問題が発生した場合は、以下を確認してください：

1. このREADMEのトラブルシューティングセクション
2. 各ジョブのJenkinsfileのコメント
3. [Jenkins公式ドキュメント](https://www.jenkins.io/doc/)
4. [Jenkins Plugin Index](https://plugins.jenkins.io/)

## ライセンス

このプロジェクトは内部利用を目的としています。詳細は[LICENSE](../LICENSE)を参照してください。