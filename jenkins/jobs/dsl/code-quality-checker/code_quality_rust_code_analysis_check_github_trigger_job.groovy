// YAMLから渡されたjenkinsManagedRepositoriesを使用してリポジトリ情報を構築
def repositories = jenkinsManagedRepositories.collect { name, repo ->
    [
        name: name,
        url: repo.httpsUrl,  // HTTPSのURLを使用（GitHubトリガー用）
        branch: repo.mainBranch
    ]
}

// 共通設定を定義するメソッド
def createGitHubTriggerJob(repoConfig) {
    // 共通設定を取得
    def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

    // ジョブ設定を取得（このDSLファイル自体の設定）
    def jobKey = 'code_quality_rust_code_analysis_check_github_trigger_job'
    def jobConfig = jenkinsJobsConfig[jobKey]
    
    // ジョブ名を新しい構造に合わせて調整
    def jobName = "Code_Quality_Checker/${repoConfig.name}/${jobConfig.name}"
    def downstreamJob = "Code_Quality_Checker/${repoConfig.name}/${jobConfig.downstreamJob}"
    
    job(jobName) {
        displayName(jobConfig.displayName)
        // ジョブの説明
        description("""\
            |# 概要
            |GitHubプッシュをトリガーとしてRust Code Analysisメトリクス分析ジョブを実行するトリガージョブ
            |
            |## トリガー実行タイミング
            |以下の条件でジョブが自動実行されます：
            |* 対象ブランチ（${repoConfig.branch}）へのプッシュ時
            |* マージリクエストのマージ時
            |* 直接コミット時
            |* タグプッシュ時
            |
            |**注意**: プルリクエストの作成やコメント追加では実行されません
            |
            |## 処理内容
            |1. GitHubからのプッシュイベントを監視
            |2. プッシュイベント発生時に後続ジョブを起動
            |3. 対象リポジトリの最新コードを取得
            |4. 後続ジョブ「${downstreamJob}」を実行
            |
            |## 分析内容
            |後続ジョブでは以下のメトリクスを分析します：
            |* 循環的複雑度（Cyclomatic Complexity）
            |* 認知的複雑度（Cognitive Complexity）
            |
            |## 関連リソース
            |* リポジトリ: [${repoConfig.name}](${repoConfig.url})
            |* 監視ブランチ: ${repoConfig.branch}
            |* 後続ジョブ: ${downstreamJob}
            |
            |## 注意事項
            |* このジョブは自動実行専用です
            |* 手動実行は後続ジョブを直接実行してください
            |* GitHubのWebhook設定が必要です
            |""".stripMargin())
        
        // 依存関係の保持設定
        keepDependencies(false)
        
        // ログローテーション設定
        logRotator {
            numToKeep(10)
            daysToKeep(30)
        }
        
        // 同時実行制御
        throttleConcurrentBuilds {
            maxTotal(1)
            throttleDisabled(false)
        }
        
        // プロパティ設定
        properties {
            // GitHub Project設定
            githubProjectUrl("${repoConfig.url}/")
            
            // リビルド設定
            rebuild {
                autoRebuild(false)
                rebuildDisabled(false)
            }
        }
        
        // SCM設定
        scm {
            git {
                remote {
                    url(repoConfig.url)
                    credentials(jenkinsPipelineRepo.credentials)
                }
                branch("*/${repoConfig.branch}")
            }
        }
        
        // GitHubプッシュトリガーの設定
        triggers {
            githubPush()
        }
        
        // ビルドステップ（空のシェルステップを追加してフリースタイルジョブとして動作させる）
        steps {
            shell("echo \"GitHub push trigger activated for Rust Code Analysis on ${repoConfig.name}\"")
        }
        
        // 後続ジョブの設定
        publishers {
            downstream(downstreamJob, 'SUCCESS')
        }
        
        // ジョブの無効化状態
        disabled(false)
    }
}

// 各リポジトリのジョブを作成
repositories.each { repo ->
    createGitHubTriggerJob(repo)
}
