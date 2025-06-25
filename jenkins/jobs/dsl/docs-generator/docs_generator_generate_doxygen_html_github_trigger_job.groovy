// YAMLから渡されたjenkinsManagedRepositoriesを使用してリポジトリ情報を構築
def repositories = jenkinsManagedRepositories.collect { name, repo ->
    [
        name: name,
        url: repo.httpsUrl,  // HTTPSのURLを使用（GitHubトリガー用）
        docBranch: repo.docBranch
    ]
}

// 共通設定を定義するメソッド
def createDoxygenHtmlTriggerJob(repoConfig) {
    // 共通設定を取得
    def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']
    
    // ジョブ設定を取得（このDSLファイル自体の設定）
    def jobKey = 'docs_generator_generate_doxygen_html_github_trigger_job'
    def jobConfig = jenkinsJobsConfig[jobKey]
    
    // ジョブ名を新しい構造に合わせて調整
    def jobName = "Document_Generator/${repoConfig.name}/${jobConfig.name}"
    def downstreamJob = "Document_Generator/${repoConfig.name}/${jobConfig.downstreamJob}"
    
    job(jobName) {
        // ジョブの説明
        description("""\
            |# 概要
            |ドキュメントブランチへのプッシュをトリガーとしてDoxygen HTML生成ジョブを実行するトリガージョブ
            |
            |## トリガー実行タイミング
            |以下の条件でジョブが自動実行されます：
            |* ドキュメントブランチ（${repoConfig.docBranch}）へのプッシュ時
            |* ドキュメント用コミットのマージ時
            |* Doxygenコメント更新時
            |* ドキュメント関連ファイルの変更時
            |
            |**注意**: メインブランチやその他のブランチへのプッシュでは実行されません
            |
            |## 処理内容
            |1. ドキュメントブランチからのプッシュイベントを監視
            |2. プッシュイベント発生時に後続ジョブを起動
            |3. 対象リポジトリの最新ドキュメントを取得
            |4. 後続ジョブ「${downstreamJob}」でDoxygen HTML生成を実行
            |
            |## 関連リソース
            |* リポジトリ: [${repoConfig.name}](${repoConfig.url})
            |* 監視ブランチ: ${repoConfig.docBranch}（ドキュメント専用ブランチ）
            |* 後続ジョブ: ${downstreamJob}
            |
            |## 注意事項
            |* このジョブは自動実行専用です
            |* 手動でのHTML生成は後続ジョブを直接実行してください
            |* GitHubのWebhook設定が必要です
            |* ドキュメントブランチのみを監視対象としています
            |""".stripMargin())
        
        // 依存関係の保持設定
        keepDependencies(false)
        disabled(true) // 初期状態では無効化
        
        // ログローテーション設定
        logRotator {
            numToKeep(15)
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
                // ドキュメントブランチを監視
                branch("*/${repoConfig.docBranch}")
            }
        }

        // GitHubプッシュトリガーの設定
        triggers {
            githubPush()
        }
        
        // ビルドステップ（トリガー確認用）
        steps {
            shell("echo \"GitHub push trigger activated for ${repoConfig.name} document branch (${repoConfig.docBranch})\"")
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
    createDoxygenHtmlTriggerJob(repo)
}
