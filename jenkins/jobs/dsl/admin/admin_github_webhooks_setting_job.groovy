// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'admin_github_webhooks_setting_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Admin_Jobs/${jobConfig.name}"

pipelineJob(fullJobName) {
    displayName(jobConfig.displayName)
    
    // 基本情報
    description('GitHubのWebhookを設定するジョブです。')
    keepDependencies(false)
    disabled(false)

    // ビルド履歴の保持設定
    logRotator {
        daysToKeep(30)
        numToKeep(30)
        artifactDaysToKeep(-1)
        artifactNumToKeep(-1)
    }

    // プロパティ設定
    properties {
        rebuild {
            autoRebuild(false)
            rebuildDisabled(false)
        }
    }

    // 同時実行制御
    throttleConcurrentBuilds {
        maxTotal(1)
        throttleDisabled(false)
    }

    // パラメータ定義
    parameters {
        // 基本設定
        stringParam('REPO_URL', 'https://github.com/tielec/infrastructure-as-code', 'GitHubリポジトリのURL (必須)')
        
        choiceParam('ACTION', ['CREATE_OR_UPDATE', 'DELETE', 'LIST', 'VALIDATE'], '実行する操作')
        
        // Webhook設定
        stringParam('WEBHOOK_TOKEN_SUFFIX', 'jenkins-webhook', 'Webhook URLのトークン接尾辞 (デフォルト: jenkins-webhook)')
        
        stringParam('JENKINS_BASE_URL', 'https://your.jenkins.host', 'Jenkins のベースURL')
        
        // イベント設定
        textParam('WEBHOOK_EVENTS', 'pull_request', 'トリガーするイベント (カンマ区切り)。例: pull_request,push,issues')
        
        // 詳細設定
        choiceParam('CONTENT_TYPE', ['application/json', 'application/x-www-form-urlencoded'], 'Content-Type (デフォルト: application/json)')
        
        booleanParam('SSL_VERIFICATION', true, 'SSL検証を有効にする')
        
        booleanParam('WEBHOOK_ACTIVE', true, 'Webhookを有効にする')
        
        // オプション: 手動でIDを指定する場合
        stringParam('WEBHOOK_ID', '', '(オプション) 特定のWebhook IDを対象にする場合のみ指定')
        
        // カスタムWebhook URL（オプション）
        stringParam('CUSTOM_WEBHOOK_URL', '', '(オプション) カスタムWebhook URLを使用する場合')
        
        // 操作オプション
        booleanParam('DRY_RUN', false, 'ドライラン（実際の変更を行わない）')
        stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileが格納されているブランチ')
    }

    // パイプライン定義
    definition {
        cpsScm {
            scm {
                git {
                    remote {
                        url(jenkinsPipelineRepo.url)
                        credentials(jenkinsPipelineRepo.credentials)
                    }
                    branch('${JENKINSFILE_BRANCH}')
                }
            }
            scriptPath(jobConfig.jenkinsfile)
            lightweight(true)
        }
    }
}
