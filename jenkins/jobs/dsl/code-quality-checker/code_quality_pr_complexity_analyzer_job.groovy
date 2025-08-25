// YAMLから渡されたjenkinsManagedRepositoriesを使用してリポジトリ情報を構築
def repositories = jenkinsManagedRepositories.collect { name, repo ->
    [
        name: name,
        url: repo.httpsUrl,  // HTTPSのURLを使用
        credentialsId: repo.credentialsId
    ]
}

// 各リポジトリのジョブを作成
repositories.each { repo ->
    // 共通設定を取得
    def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']
    
    // ジョブ設定を取得（このDSLファイル自体の設定）
    def jobKey = 'code_quality_pr_complexity_analyzer_job'
    def jobConfig = jenkinsJobsConfig[jobKey]
    
    // ジョブ名を新しい構造に合わせて調整
    def jobName = "Code_Quality_Checker/${repo.name}/${jobConfig.name}"
    
    pipelineJob(jobName) {
        displayName(jobConfig.displayName)
        // 基本情報
        description("""\
            |# 概要
            |Pull Requestの複雑度を分析し、コード品質レポートを生成します。
            |リポジトリ: ${repo.name}
            |
            |## 処理内容
            |- PRで変更されたファイルの複雑度分析
            |- 循環的複雑度（Cyclomatic Complexity）の計算
            |- 認知的複雑度（Cognitive Complexity）の計算
            |- 閾値を超えた関数・メソッドの検出
            |- 分析結果のPRコメントへの投稿
            |- 既存の分析コメントがある場合は上書き更新
            |- 分析レポートを成果物として保存
            |
            |## 対応言語
            |- Python, JavaScript, TypeScript, Java, C++, C#, Go, Rust など
            |""".stripMargin())
        
        // 依存関係の保持設定
        keepDependencies(false)
        
        // ビルド設定
        logRotator {
            numToKeep(20)
            artifactNumToKeep(10)
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
            stringParam('REPO_URL', repo.url, 'Git repository URL to analyze (e.g., https://github.com/owner/repo)')
            stringParam('PR_NUMBER', 'Latest', 'PR number to analyze or "Latest" for the most recent PR')
            stringParam('GIT_SOURCE_REPO_CREDENTIALS_ID', repo.credentialsId, 'Jenkins credentials ID for Git authentication')
            stringParam('CYCLOMATIC_THRESHOLD', '15', 'Cyclomatic complexity threshold')
            stringParam('COGNITIVE_THRESHOLD', '20', 'Cognitive complexity threshold')
            booleanParam('FORCE_ANALYSIS', true, 'Force re-analysis even if comment exists')
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
}
