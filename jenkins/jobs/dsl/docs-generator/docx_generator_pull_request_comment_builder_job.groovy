// YAMLから渡されたdocsGeneratorRepositoriesを使用してリポジトリ情報を構築
def repositories = docsGeneratorRepositories.collect { name, repo ->
    [
        name: name,
        url: repo.httpsUrl  // HTTPSのURLを使用
    ]
}

// 各リポジトリのジョブを作成
repositories.each { repo ->
    // 共通設定を取得
    def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']
    
    // ジョブ設定を取得（このDSLファイル自体の設定）
    def jobKey = 'docx_generator_pull_request_comment_builder_job'
    def jobConfig = jenkinsJobsConfig[jobKey]
    
    // ジョブ名を新しい構造に合わせて調整
    def jobName = "Document_Generator/${repo.name}/${jobConfig.name}"
    
    pipelineJob(jobName) {
        // 基本情報
        description("""\
            |# 概要
            |以下の機能を持つGitHub PRの自動コメント生成を行います。
            |リポジトリ: ${repo.name}
            |
            |## 処理内容
            |- OpenAI API（GPT-4.1）を使用してPRの内容を分析
            |- PR情報と差分の取得・解析
            |- コメントの自動生成とPRへの投稿
            |- オプションでPRタイトルの更新も可能
            |- 既存の自動生成コメントがある場合は上書き更新
            |- プロセスの実行結果を成果物として保存
            |""".stripMargin())
        
        // 依存関係の保持設定
        keepDependencies(false)
        
        // ビルド設定
        logRotator {
            numToKeep(10)
            artifactNumToKeep(5)
        }
        
        // 同時実行の無効化（throttleConcurrentBuildsを使用）
        throttleConcurrentBuilds {
            maxTotal(1)
            throttleDisabled(false)
        }
        
        // プロパティ設定
        properties {
            // リビルド設定
            rebuild {
                autoRebuild(false)
                rebuildDisabled(false)
            }
        }
        
        // パラメータ設定
        parameters {
            stringParam('REPO_URL', repo.url, 'リポジトリURL')
            stringParam('PR_NUMBER', 'Latest', 'プルリクエスト番号（"Latest"の場合は最新のPRを対象）')
            booleanParam('UPDATE_TITLE', false, 'PRのタイトルを更新するかどうか')
            booleanParam('FORCE_ANALYSIS', false, '既存のコメントが存在しても強制的に分析とコメント更新を実行するかどうか')
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
