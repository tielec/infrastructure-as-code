// YAMLから渡されたjenkinsManagedRepositoriesを使用してリポジトリ情報を構築
def repositories = jenkinsManagedRepositories.collect { name, repo ->
    [
        name: name,
        url: repo.httpsUrl,
        branch: repo.mainBranch,
        docBranch: repo.docBranch,
        credentialsId: repo.credentialsId
    ]
}

// 共通設定を定義するメソッド
def createDocumentGeneratorJob(repoConfig) {
    // 共通設定を取得
    def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']
    
    // ジョブ設定を取得（このDSLファイル自体の設定）
    def jobKey = 'docs_generator_auto_insert_doxygen_comment_job'
    def jobConfig = jenkinsJobsConfig[jobKey]
    
    // ジョブ名を新しい構造に合わせて調整
    def jobName = "Document_Generator/${repoConfig.name}/${jobConfig.name}"
    
    pipelineJob(jobName) {
        description("""\
            |# 概要
            |ソースコードのドキュメントを自動生成するジョブ
            |リポジトリ:${repoConfig.name}
            |
            |## 処理内容
            |1. リポジトリからソースコードを取得
            |2. ドキュメントコメントの生成
            |3. PRの作成
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

        // パラメータ設定
        parameters {
            // AGENT_LABELパラメータ
            choiceParam('AGENT_LABEL', ['ec2-fleet-small', 'ec2-fleet-medium', 'ec2-fleet-micro'],
                'Jenkins エージェントのラベル（small: 2並列/2GB, medium: 3並列/4GB, micro: 1並列/1GB）')

            stringParam('REPO_URL', repoConfig.url, 'リポジトリURL')
            stringParam('TARGET_BRANCH', repoConfig.branch, 'ドキュメント生成元のブランチ')
            stringParam('PR_TARGET_BRANCH', repoConfig.docBranch, 'PRのマージ先ブランチ')
            choiceParam('COMMIT_MODE', ['DIRECT_PUSH', 'CREATE_PR'], 'コミットモード（直接プッシュ or PR作成）')
            booleanParam('OVERWRITE_DOCS', true, 'Python,shellの既存のコメントを上書きするかどうか')
            stringParam('MAX_FILES', '0', '処理する最大ファイル数（0は無制限）')
            stringParam('MAX_RETRIES', '3', '1ファイルあたりの最大リトライ回数')
            choiceParam('FILE_SELECTION_MODE', ['LATEST_PR', 'SPECIFIC_PR', 'ALL_FILES'], 'ファイル選択モード: 最新PR/指定PR/全ファイル')
            stringParam('PR_NUMBER', '', '処理対象とするPRの番号（FILE_SELECTION_MODEがSPECIFIC_PRの場合に使用）')
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

        // ジョブの無効化状態
        disabled(false)
    }
}

// 各リポジトリのジョブを作成
repositories.each { repo ->
    createDocumentGeneratorJob(repo)
}
