// YAMLから渡されたjenkinsManagedRepositoriesを使用してリポジトリ情報を構築
def repositories = jenkinsManagedRepositories.collect { name, repo ->
    [
        name: name,
        url: repo.httpsUrl,  // HTTPSのURLを使用
        updateTitle: repo.updatePullRequestTitle // PRタイトル更新の有無
    ]
}

// 共通設定を定義するメソッド
//
// 【ドラフトPRフィルタリング機能】
// このジョブはドラフト状態のPRに対しては下流ジョブを起動しません。
// - Generic Webhook Triggerで`$.pull_request.draft`を取得
// - Conditional BuildStepで`draft=false`の場合のみ下流ジョブを起動
// - ドラフト解除後（ready_for_review）に自動的に処理が再開されます
def createPRCommentTriggerJob(repoConfig) {
    // 共通設定を取得
    def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']
    
    // ジョブ設定を取得（このDSLファイル自体の設定）
    def jobKey = 'docx_generator_pull_request_comment_builder_github_trigger_job'
    def jobConfig = jenkinsJobsConfig[jobKey]
    
    // ジョブ名を新しい構造に合わせて調整
    def jobName = "Document_Generator/${repoConfig.name}/${jobConfig.name}"
    def downstreamJobName = "Document_Generator/${repoConfig.name}/${jobConfig.downstreamJob}"
    def tokenValue = "${repoConfig.name.replaceAll('-', '')}-jenkins-webhook"
    
    job(jobName) {
        description("""\
        |# GitHub PR コメント自動化トリガー
        |
        |GitHubでPRが作成または更新されたときに自動的に実行され、PR解析とコメント生成ジョブをキックします。
        |Generic Webhook Triggerプラグインを使用してPRイベントをトリガーします。
        |
        |## 処理内容
        |1. GitHub PRイベントの検証
        |2. PR情報を取得して子ジョブに必要なパラメータを設定
        |3. PR自動コメント生成ジョブを起動
        |
        |## 関連リソース
        |* GitHub リポジトリ: [${repoConfig.name}](${repoConfig.url})
        |""".stripMargin())
        
        // ジョブの基本設定
        keepDependencies(false)
        
        // ログローテーション設定
        logRotator {
            daysToKeep(-1)
            numToKeep(10)
            artifactDaysToKeep(-1)
            artifactNumToKeep(5)
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
                    // ドラフト状態を取得（ドラフトPRフィルタリング機能）
                    genericVariable {
                        key('PR_DRAFT')
                        value('$.pull_request.draft')
                        expressionType('JSONPath')
                        regexpFilter('')
                    }
                }
                
                // PullRequestが作成時または再オープン時のみトリガー
                // 必要に応じて 'opened|reopened|synchronize' に変更可能
                regexpFilterText('$ACTION')
                regexpFilterExpression('opened|reopened')
                
                // イベントコールのためのトークン（WebhookのURLに含める）
                token(tokenValue)
                
                // レスポンスのステータスコード
                causeString('GitHub PR #$PR_NUMBER が $ACTION されました (Draft: $PR_DRAFT)')
                
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
            // ドラフトPRの場合はスキップ（ドラフトPRフィルタリング機能）
            conditionalSteps {
                condition {
                    // draft=falseの場合のみ実行（非ドラフトPR）
                    stringsMatch('$PR_DRAFT', 'false', false)
                }
                runner('DontRun')  // 条件が不一致の場合はステップをスキップ（ビルドは継続）
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
                                    'PR_NUMBER': '$PR_NUMBER',
                                    'UPDATE_TITLE': repoConfig.updateTitle,
                                    'FORCE_ANALYSIS': 'true'
                                ])
                            }
                        }
                    }
                }
            }
        }
    }
}

// 各リポジトリのジョブを作成
repositories.each { repo ->
    createPRCommentTriggerJob(repo)
}
