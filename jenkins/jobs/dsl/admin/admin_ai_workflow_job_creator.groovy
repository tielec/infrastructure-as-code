/**
 * AI Workflow Job Creator
 *
 * AI Workflowジョブを自動生成するシードジョブ
 */

// 設定の取得
def jobKey = 'ai_workflow_job_creator'
def jobConfig = jenkinsJobsConfig[jobKey]
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']
def fullJobName = "Admin_Jobs/${jobConfig.name}"

pipelineJob(fullJobName) {
    displayName(jobConfig.displayName)

    description('''\
        # AI Workflow Job Creator

        ## 概要
        AI Workflowジョブを自動生成するシードジョブです。

        ## 生成されるジョブ
        - AI_Workflow/develop配下のジョブ（5種類）
        - AI_Workflow/stable-1〜stable-9配下のジョブ（各5種類）
        - 合計: 50ジョブ

        ## 注意事項
        - DSLから削除されたジョブは自動的に削除されます
        - フォルダ構造はfolder-config.yamlで管理されています
        - job-creatorとの並行実行が可能です
    '''.stripIndent().trim())

    // 基本情報
    keepDependencies(false)
    disabled(false)

    // ビルド履歴の保持設定
    logRotator {
        daysToKeep(90)
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
        disableConcurrentBuilds()
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
                    branch(jenkinsPipelineRepo.branch)
                }
            }
            scriptPath(jobConfig.jenkinsfile)
            lightweight(true)
        }
    }
}
