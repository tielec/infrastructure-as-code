// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'infrastructure_shutdown_environment_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Infrastructure_Management/${jobConfig.name}"

pipelineJob(fullJobName) {
    displayName(jobConfig.displayName)
    
    // 基本情報
    description('''Jenkins環境全体を安全に停止します。

### 停止対象
- EC2 Fleet (SpotFleet) エージェント
- NAT インスタンス
- Jenkins Controller インスタンス

### 停止順序
1. EC2 Fleet のキャパシティを0に設定
2. 実行中のエージェントジョブの完了を待機
3. NAT インスタンスを停止
4. Controller インスタンスを停止（非同期実行）

### 注意事項
- このジョブは環境全体を停止するため、実行前に他のジョブの状況を確認してください
- ジョブ自身も停止対象のため、非同期で実行されます
- 停止処理は最大30分でタイムアウトします
''')
    
    keepDependencies(false)
    disabled(false)

    // ビルド履歴の保持設定
    logRotator {
        daysToKeep(30)
        numToKeep(50)
        artifactDaysToKeep(-1)
        artifactNumToKeep(-1)
    }

    // プロパティ設定
    properties {
        rebuild {
            autoRebuild(false)
            rebuildDisabled(false)
        }
    }

    // 同時実行制御
    throttleConcurrentBuilds {
        maxTotal(1)
        throttleDisabled(false)
    }

    // パラメータ設定
    parameters {
        choiceParam('ENVIRONMENT', ['dev', 'staging', 'prod'], '''対象環境

停止するJenkins環境を選択します。
''')
        
        choiceParam('AWS_REGION', ['ap-northeast-1', 'us-east-1', 'us-west-2'], 'AWSリージョン')
        
        booleanParam('CONFIRM_SHUTDOWN', false, '''環境停止の確認

このチェックボックスをONにすることで、環境の停止を承認します。
停止する前に以下を確認してください：
- 実行中の重要なジョブがないこと
- 他のユーザーへの影響を考慮済みであること
''')
        
        choiceParam('SHUTDOWN_MODE', ['graceful', 'immediate'], '''停止モード

- graceful: エージェントのジョブ完了を待ってから停止（推奨）
- immediate: 即座に停止（緊急時のみ）
''')
        
        stringParam('WAIT_TIMEOUT_MINUTES', '30', '''待機タイムアウト（分）

gracefulモードで、エージェントジョブの完了を待つ最大時間。
この時間を超えた場合は強制的に停止処理を続行します。
''')
        
        booleanParam('DRY_RUN', false, '''ドライラン

実際の停止を行わず、停止対象のリソースの確認のみを行います。
''')
        
        // Jenkinsfileブランチ
        stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileが格納されているブランチ')
    }

    // Pipeline定義
    definition {
        cpsScm {
            scm {
                git {
                    remote {
                        url(jenkinsPipelineRepo.url)
                        credentials(jenkinsPipelineRepo.credentials)
                    }
                    branch('${JENKINSFILE_BRANCH}')
                    extensions {
                        cleanBeforeCheckout()
                        cloneOptions {
                            shallow(true)
                            depth(1)
                            noTags(true)
                            timeout(10)
                        }
                    }
                }
            }
            scriptPath(jobConfig.jenkinsfile)
            lightweight(true)
        }
    }
}