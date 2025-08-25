// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'shared_library_git_deploykeys_operation_test_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Shared_Library/Git_Utils/${jobConfig.name}"

pipelineJob(fullJobName) {
    // 基本情報
    description('GitのDeploy Keys操作をテストするジョブです。')
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
        choiceParam('TEST_TYPE', ['ALL', 'CREATE_UPDATE', 'BATCH_CREATE', 'SEARCH', 'LIST_ONLY'], 'テストする操作を選択')
        stringParam('DEPLOY_KEY_TITLE', 'Jenkins Test Key', 'テスト用Deploy Keyのタイトル')
        booleanParam('CLEANUP_AFTER_TEST', true, 'テスト後にリソースを削除する')
        booleanParam('DRY_RUN', false, 'ドライラン（読み取り操作のみ）')
        stringParam('REPO_URL', 'https://github.com/tielec/infrastructure-as-code', 'リポジトリのURL')
        stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileが格納されているブランチ')
        // Jenkins Libraryブランチ
        stringParam('LIBRARY_BRANCH', 'main', 'Jenkins Shared Libraryのブランチ')
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
