// YAMLから渡されたjenkinsManagedRepositoriesを使用してリポジトリ情報を構築
def repositories = jenkinsManagedRepositories.collect { name, repo ->
    [
        name: name,
        url: repo.httpsUrl,  // HTTPSのURLを使用
        credentialsId: repo.credentialsId
    ]
}

// 共通設定を定義するメソッド
def createPRComplexityAnalyzerTriggerJob(repoConfig) {
    // 共通設定を取得
    def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']
    
    // ジョブ設定を取得（このDSLファイル自体の設定）
    def jobKey = 'code_quality_pr_complexity_analyzer_github_trigger_job'
    def jobConfig = jenkinsJobsConfig[jobKey]
    
    // ジョブ名を新しい構造に合わせて調整
    def jobName = "Code_Quality_Checker/${repoConfig.name}/${jobConfig.name}"
    def downstreamJobName = "Code_Quality_Checker/${repoConfig.name}/${jobConfig.downstreamJob}"
    def tokenValue = "${repoConfig.name.replaceAll('-', '')}-pr-complexity-webhook"
    
    job(jobName) {
        description("""\
        |# GitHub PR 複雑度分析自動化トリガー
        |
        |GitHubでPRが作成、更新、または同期されたときに自動的に実行され、
        |PR複雑度分析ジョブをキックします。
        |Generic Webhook Triggerプラグインを使用してPRイベントをトリガーします。
        |
        |## 処理内容
        |1. GitHub PRイベントの検証
        |2. PR情報を取得して子ジョブに必要なパラメータを設定
        |3. PR複雑度分析ジョブを起動
        |
        |## トリガー条件
        |- PRが作成された時（opened）
        |- PRが再オープンされた時（reopened）
        |- PRに新しいコミットがプッシュされた時（synchronize）
        |
        |## 関連リソース
        |* GitHub リポジトリ: [${repoConfig.name}](${repoConfig.url})
        |""".stripMargin())
        
        // ジョブの基本設定
        keepDependencies(false)
        
        // ログローテーション設定
        logRotator {
            daysToKeep(-1)
            numToKeep(30)
            artifactDaysToKeep(-1)
            artifactNumToKeep(10)
        }
        
        // ノード制約
        label('ec2-fleet')
        
        // ジョブのプロパティ設定
        properties {
            // GitHubプロジェクトURL設定
            githubProjectUrl(repoConfig.url)
            
            // リビルド設定
            rebuild {
                autoRebuild(false)
                rebuildDisabled(false)
            }
            
            // 同時実行制御
            throttleConcurrentBuilds {
                maxTotal(1)
                maxPerNode(0)
                throttleDisabled(false)
            }
        }
        
        // 実行を無効化（必要に応じてfalseに変更）
        disabled(false)
        
        // Generic Webhook Triggerの設定
        triggers {
            genericTrigger {
                genericVariables {
                    genericVariable {
                        key('PR_NUMBER')
                        value('$.pull_request.number')
                        expressionType('JSONPath')
                        regexpFilter('')
                    }
                    genericVariable {
                        key('REPO_URL')
                        value('$.repository.html_url')
                        expressionType('JSONPath')
                        regexpFilter('')
                    }
                    genericVariable {
                        key('ACTION')
                        value('$.action')
                        expressionType('JSONPath')
                        regexpFilter('')
                    }
                    genericVariable {
                        key('PR_HEAD_SHA')
                        value('$.pull_request.head.sha')
                        expressionType('JSONPath')
                        regexpFilter('')
                    }
                    genericVariable {
                        key('PR_BASE_BRANCH')
                        value('$.pull_request.base.ref')
                        expressionType('JSONPath')
                        regexpFilter('')
                    }
                }
                
                // PullRequestが作成、再オープン、または更新時にトリガー
                regexpFilterText('$ACTION')
                regexpFilterExpression('opened|reopened|synchronize')
                
                // イベントコールのためのトークン（WebhookのURLに含める）
                token(tokenValue)
                
                // レスポンスのステータスコード
                causeString('GitHub PR #$PR_NUMBER が $ACTION されました (SHA: $PR_HEAD_SHA)')
                
                // デバッグ設定
                printContributedVariables(true)
                printPostContent(false)
                
                // セキュリティ設定
                silentResponse(true)
            }
        }
        
        // 並列ビルドの無効化
        concurrentBuild(false)
        
        // ビルドステップ（子ジョブのトリガー）
        steps {
            // 子ジョブの起動
            downstreamParameterized {
                trigger(downstreamJobName) {
                    block {
                        buildStepFailure('FAILURE')
                        failure('FAILURE')
                        unstable('UNSTABLE')
                    }
                    parameters {
                        // 子ジョブに渡すパラメータ
                        predefinedProps([
                            'REPO_URL': '$REPO_URL',
                            'PR_NUMBER': '$PR_NUMBER'
                        ])
                    }
                }
            }
        }
    }
}

// 各リポジトリのジョブを作成
repositories.each { repo ->
    createPRComplexityAnalyzerTriggerJob(repo)
}
