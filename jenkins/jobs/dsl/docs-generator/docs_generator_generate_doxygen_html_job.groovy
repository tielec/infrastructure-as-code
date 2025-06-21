// YAMLから渡されたdocsGeneratorRepositoriesを使用してリポジトリ情報を構築
def repositories = docsGeneratorRepositories.collect { name, repo ->
    [
        name: name,
        url: repo.httpsUrl,  
        docBranch: repo.docBranch,
        credentialsId: repo.credentialsId
    ]
}

// 共通設定を定義するメソッド
def createDoxygenHtmlJob(repoConfig) {
    // 共通設定を取得
    def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']
    
    // ジョブ設定を取得（このDSLファイル自体の設定）
    def jobKey = 'docs_generator_generate_doxygen_html_job'
    def jobConfig = jenkinsJobsConfig[jobKey]
    
    // ジョブ名を新しい構造に合わせて調整
    def jobName = "Document_Generator/${repoConfig.name}/${jobConfig.name}"
    
    pipelineJob(jobName) {
        description("""\
            |# 概要
            |Doxygenを使用してHTMLドキュメントを生成するジョブ
            |リポジトリ:${repoConfig.name}
            |
            |## 処理内容
            |1. ソースコードリポジトリのクローン
            |2. Doxygenによるドキュメント生成
            |""".stripMargin())

        // 依存関係の保持設定
        keepDependencies(false)

        // ビルド履歴の保持設定
        logRotator {
            numToKeep(-1)
            daysToKeep(-1)
            artifactNumToKeep(-1)
            artifactDaysToKeep(-1)
        }

        // 同時実行の無効化（throttleConcurrentBuildsを使用）
        throttleConcurrentBuilds {
            maxTotal(1)
            throttleDisabled(false)
        }

        // Properties
        properties {
            rebuild {
                autoRebuild(false)
                rebuildDisabled(false)
            }
        }

        // パラメータ設定
        parameters {
            stringParam('GIT_SOURCE_REPO_URL', repoConfig.url, 'ドキュメント生成対象のソースコードリポジトリURL')
            stringParam('GIT_SOURCE_REPO_BRANCH', repoConfig.docBranch, 'ドキュメント生成対象のブランチ名')
            stringParam('GIT_SOURCE_REPO_CREDENTIALS_ID', repoConfig.credentialsId, 'GitHub認証情報ID')
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

        // ジョブの無効化状態
        disabled(false)
    }
}

// 各リポジトリのジョブを作成
repositories.each { repo ->
    createDoxygenHtmlJob(repo)
}
