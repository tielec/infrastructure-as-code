// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'docs_generator_auto_insert_doxygen_comment_test_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Pipeline_Tests/Document_Generator/${jobConfig.name}"

pipelineJob(fullJobName) {
    displayName(jobConfig.displayName)
    description("""\
        |# 概要
        |ドキュメント生成の自動挿入テストジョブ
        |""".stripMargin())

    // 依存関係の保持設定
    keepDependencies(false)

    // ログローテーション設定
    logRotator {
        numToKeep(10)
    }

    // 同時実行の無効化（throttleConcurrentBuildsを使用）
    throttleConcurrentBuilds {
        maxTotal(1)
        throttleDisabled(false)
    }

    // プロパティ設定
    properties {
        rebuild {
            autoRebuild(false)
            rebuildDisabled(false)
        }
    }

    // パラメータ定義
    parameters {
        stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileが格納されているブランチ')
        // Jenkins Libraryブランチ
        stringParam('LIBRARY_BRANCH', 'main', 'Jenkins Shared Libraryのブランチ')
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

    // ジョブの無効化状態
    disabled(false)
}
