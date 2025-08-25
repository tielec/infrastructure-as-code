// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'admin_user_management_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Admin_Jobs/${jobConfig.name}"

pipelineJob(fullJobName) {
    displayName(jobConfig.displayName)
    
    // 基本情報
    description('Jenkinsのユーザーアカウントを管理します。特定のユーザーの削除や、@tielec.netドメイン以外のユーザーのクリーンアップが可能です。')
    keepDependencies(false)
    disabled(false)

    // ビルド履歴の保持設定
    logRotator {
        daysToKeep(30)
        numToKeep(50)
        artifactDaysToKeep(-1)
        artifactNumToKeep(-1)
    }

    // プロパティ設定
    properties {
        rebuild {
            autoRebuild(false)
            rebuildDisabled(false)
        }

        pipelineTriggers {
            triggers {
                cron {
                    spec('0 9 * * 1')  // 毎週月曜日 JST 18:00 = UTC 9:00
                }
            }
        }
    }

    // 同時実行制御（ユーザー管理は同時実行を避ける）
    throttleConcurrentBuilds {
        maxTotal(1)
        throttleDisabled(false)
    }

    // パラメータ設定
    parameters {
        choiceParam('EXECUTION_MODE', ['EXECUTE', 'DRY_RUN'], 'EXECUTE: apply changes, DRY_RUN: check only')
        booleanParam('CLEANUP_USERS', false, 'Enable user cleanup functionality')
        textParam('USERS_TO_DELETE', '', 'Comma-separated list of usernames to delete (e.g., user1,user2,user3). Only works when CLEANUP_USERS is true.')
        booleanParam('DELETE_NON_DOMAIN_USERS', false, 'Delete all non @tielec.net users except admin and SYSTEM. Only works when CLEANUP_USERS is true.')
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
