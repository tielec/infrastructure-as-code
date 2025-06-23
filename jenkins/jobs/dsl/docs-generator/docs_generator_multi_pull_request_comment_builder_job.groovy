// YAMLから渡されたjenkinsManagedRepositoriesを使用してリポジトリ情報を構築
def repositories = jenkinsManagedRepositories.collect { name, repo ->
    [
        name: name,
        url: repo.httpsUrl,  // HTTPSのURLを使用
        targetBranch: repo.mainBranch  // mainBranchをtargetBranchとして使用
    ]
}

// 各リポジトリのジョブを作成
repositories.each { repo ->
    // 共通設定を取得
    def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']
    
    // ジョブ設定を取得（このDSLファイル自体の設定）
    def jobKey = 'docs_generator_multi_pull_request_comment_builder_job'
    def jobConfig = jenkinsJobsConfig[jobKey]
    
    // ジョブ名を新しい構造に合わせて調整
    def jobName = "Document_Generator/${repo.name}/${jobConfig.name}"
    
    pipelineJob(jobName) {
        // 基本情報の設定
        description("""\
            |# 概要
            |複数のPRに対して一括でコメントを生成するジョブ
            |
            |## 処理内容
            |1. 指定された範囲のPR番号に対してコメントを生成
            |2. 対象リポジトリのPRに対して処理を実行
            |3. PRのステータスに応じた処理の適用
            |
            |## 関連リソース
            |* リポジトリ: [${repo.name}](${repo.url})
            |""".stripMargin())
            
        // 依存関係の保持設定
        keepDependencies(false)
        
        // ビルド履歴の管理
        logRotator {
            numToKeep(10)  // 10件のビルド履歴を保持
            artifactNumToKeep(5)  // 5件のアーティファクトを保持
        }
        
        // プロパティの設定
        properties {
            // リビルド設定
            rebuild {
                autoRebuild(false)
                rebuildDisabled(false)
            }
            
            // 同時実行制御
            throttleConcurrentBuilds {
                maxTotal(1)
                throttleDisabled(false)
            }
        }
        
        // パラメータの設定
        parameters {
            // PRの範囲指定
            stringParam('START_PR_NUMBER', null, '処理を開始するPR番号')
            stringParam('END_PR_NUMBER', null, '処理を終了するPR番号')
            
            // リポジトリ設定
            stringParam('REPO_URL', repo.url, '対象リポジトリのURL')
            
            // ブランチ指定
            stringParam('TARGET_BRANCH', repo.targetBranch, '対象とするマージ先ブランチ（例: main, master, develop）')
            
            // PRステータス選択
            choiceParam('PR_STATUS', ['all', 'open', 'merged', 'closed_without_merge'], '処理対象とするPRのステータス')
            
            // タイトル更新設定
            booleanParam('UPDATE_TITLE', false, 'PRタイトルを更新するかどうか')

            // 強制更新設定
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
                lightweight(true)  // 軽量チェックアウトを有効化
            }
        }
        
        // ジョブの無効化状態
        disabled(false)
    }
}
