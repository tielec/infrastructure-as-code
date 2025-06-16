// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'admin_github_deploykeys_setting_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Admin_Jobs/${jobConfig.name}"

pipelineJob(fullJobName) {
    displayName(jobConfig.displayName)
    
    // 基本情報
    description('GitHubのDeploy Keysを設定するジョブです。')
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
        stringParam('REPO_URL', 'https://github.com/your-owg-name/your-repo-name', 'GitHubリポジトリのURL (例: https://github.com/owner/repo)')
        choiceParam('ACTION', ['CREATE', 'UPDATE', 'DELETE', 'LIST'], '実行するアクション')
        booleanParam('READ_ONLY', false, 'Deploy Keyを読み取り専用にする（チェックなしで読み書き可能）')
        stringParam('CREDENTIAL_DOMAIN', '_', 'Jenkins Credentialのドメイン (デフォルト: グローバルドメイン)')
        stringParam('CREDENTIAL_FOLDER', 'system::system::jenkins', 'Jenkins Credentialを保存するフォルダ')
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
                    branch(jenkinsPipelineRepo.branch)
                }
            }
            scriptPath(jobConfig.jenkinsfile)
            lightweight(true)
        }
    }
}
