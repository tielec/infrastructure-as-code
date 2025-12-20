// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'shared_library_git_webhook_operation_test_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Shared_Library/Git_Utils/${jobConfig.name}"

pipelineJob(fullJobName) {
    // 基本情報
    description('GitのWebhook操作をテストするジョブです。')
    keepDependencies(false)
    disabled(false)

    // ビルド履歴の保持設定
    logRotator {
        daysToKeep(30)
        numToKeep(30)
        artifactDaysToKeep(-1)
        artifactNumToKeep(-1)
    }

    // パラメータ定義
    parameters {
        // AGENT_LABELパラメータ
        choiceParam('AGENT_LABEL', ['ec2-fleet-micro', 'ec2-fleet-small', 'ec2-fleet-medium'],
            'Jenkins エージェントのラベル（small: 2並列/2GB, medium: 3並列/4GB, micro: 1並列/1GB）')

        choiceParam('TEST_TYPE', ['ALL', 'CREATE_UPDATE', 'BATCH_CREATE', 'LIST_ONLY'], 'テストする操作を選択')
        stringParam('REPO_URL', 'https://github.com/tielec/infrastructure-as-code', 'リポジトリのURL')
        stringParam('WEBHOOK_URL', 'https://webhook.site/fa61f672-940a-406f-9850-848c8bdf8315', 'テスト用WebhookURL (webhook.siteを推奨)')
        booleanParam('CLEANUP_AFTER_TEST', true, 'テスト後にリソースを削除する')
        booleanParam('DRY_RUN', false, 'ドライラン（読み取り操作のみ）')
        stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileが格納されているブランチ')
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
