// YAMLから渡されたjenkinsManagedRepositoriesを使用してリポジトリ情報を構築
def repositories = jenkinsManagedRepositories.collect { name, repo ->
    [
        name: name,
        url: repo.httpsUrl,
        targetBranch: repo.mainBranch,  // mainBranchをtargetBranchとして使用
        docBranch: repo.docBranch,
        credentialsId: repo.credentialsId,
        startDate: repo.technicalDocsStartDate,  // YAMLではtechnicalDocsStartDateという名前
        docFile: repo.technicalDocsFile // YAMLではtechnicalDocsFileという名前
    ]
}

// 共通設定を定義するメソッド
def createDocumentGeneratorJob(repoConfig) {
    // 共通設定を取得
    def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']
    
    // ジョブ設定を取得（このDSLファイル自体の設定）
    def jobKey = 'docs_generator_technical_docs_writer_job'
    def jobConfig = jenkinsJobsConfig[jobKey]
    
    // ジョブ名を新しい構造に合わせて調整
    def jobName = "Document_Generator/${repoConfig.name}/${jobConfig.name}"
    
    pipelineJob(jobName) {
        description("""\
        |# 技術ドキュメント自動生成ジョブ
        |
        |## 処理内容
        |1. 指定されたGitリポジトリをクローン
        |2. 指定期間のPR情報を取得
        |3. OpenAI APIを使用してドキュメントを生成
        |4. 指定された最適化戦略でドキュメントを構造化
        |5. 必要に応じてGitHubにPR作成
        |
        |## 関連リソース
        |* リポジトリ:${repoConfig.name}
        |""".stripMargin())
        
        // キープビルド依存設定
        keepDependencies(false)
        
        // ビルドの保存期間設定
        logRotator {
            numToKeep(10)
            daysToKeep(30)
        }
        
        // ジョブのプロパティ設定
        properties {
            // リビルド設定
            rebuild {
                autoRebuild(false)
                rebuildDisabled(false)
            }
            
            // スロットル設定
            throttleConcurrentBuilds {
                maxPerNode(0)
                maxTotal(0)
                throttleDisabled(false)
            }
        }
        
        // パラメータ設定
        parameters {
            // 文字列パラメータ
            stringParam('GIT_REPO_URL', repoConfig.url, 'GitHubリポジトリのURL')
            stringParam('GIT_TARGET_BRANCH', repoConfig.targetBranch, 'PRのマージ先ブランチ')
            stringParam('GIT_CREDENTIALS_ID', repoConfig.credentialsId, 'GitHubの認証情報ID')
            stringParam('GIT_DOCUMENT_BRANCH', repoConfig.docBranch, 'ドキュメント用ブランチ')
            stringParam('START_DATE', repoConfig.startDate, '処理開始日 (YYYY-MM-DD形式)')
            stringParam('END_DATE', '', '処理終了日 (YYYY-MM-DD形式、空の場合は現在日時まで)')
            stringParam('OPENAI_MODEL', 'gpt-4.1-mini', '使用するOpenAIモデル')
            stringParam('DOC_FILENAME', repoConfig.docFile, '生成するドキュメントのファイル名（拡張子は.md固定）')
            
            // 真偽値パラメータ
            booleanParam('GENERATE_INITIAL_DOC', false, '初回のPRからドキュメントを新規生成するかどうか（falseの場合は既存ドキュメントを更新します）')
            booleanParam('CREATE_PR', true, '生成したドキュメントをGitHubにPRとしてコミットする')
            
            // 選択パラメータ
            choiceParam('DOC_OPTIMIZE_STRATEGY', ['FINAL_ONLY', 'FIVE_STEP', 'NONE'], 'ドキュメント構造最適化の戦略（FINAL_ONLY=最後のPRの後に1回だけ、FIVE_STEP=5回に1回、NONE=最適化なし）')
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
        
        // ジョブの無効化設定
        disabled(false)
    }
}

// 各リポジトリのジョブを作成
repositories.each { repo ->
    createDocumentGeneratorJob(repo)
}
