// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

def jobKey = 'shared_library_git_repo_baseline_operation_test_job'
def jobConfig = jenkinsJobsConfig[jobKey]

def fullJobName = "Shared_Library/Git_Utils/${jobConfig.name}"

pipelineJob(fullJobName) {
    description('Gitリポジトリのベースライン適用機能を統合テストするジョブです。')
    keepDependencies(false)
    disabled(false)

    logRotator {
        daysToKeep(30)
        numToKeep(50)
        artifactDaysToKeep(-1)
        artifactNumToKeep(-1)
    }

    parameters {
        choiceParam('AGENT_LABEL', ['ec2-fleet-micro', 'ec2-fleet-small', 'ec2-fleet-medium'], 'Jenkinsエージェントのラベル')
        choiceParam('TEST_TYPE', ['ALL', 'RULESETS', 'BRANCH_PROTECTION', 'SECURITY', 'LABELS', 'FACADE', 'PIPELINE', 'ERROR', 'IDEMPOTENT'], '実行するテストカテゴリ')
        choiceParam('TEMPLATE', ['default', 'strict', 'minimal'], '使用するベースラインテンプレート')
        choiceParam('ACTION', ['DRY_RUN', 'APPLY'], 'ベースライン適用モード（DRY_RUN推奨）')
        stringParam('REPO_URL', 'https://github.com/tielec/infrastructure-as-code', 'テスト対象リポジトリのURL')
        stringParam('TARGET_BRANCH', '', 'ブランチ保護の対象（未指定ならデフォルトブランチ）')
        booleanParam('CLEANUP_AFTER_TEST', true, 'テストで作成したリソースを削除するか')
        stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileを取得するブランチ')
    }

    properties {
        rebuild {
            autoRebuild(false)
            rebuildDisabled(false)
        }
    }

    throttleConcurrentBuilds {
        maxTotal(1)
        throttleDisabled(false)
    }

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
