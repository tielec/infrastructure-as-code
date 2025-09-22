// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'code_quality_reflection_cloud_api_multibranch_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Code_Quality_Checker/${jobConfig.name}"

// MultiBranch Pipeline ジョブの作成
multibranchPipelineJob(fullJobName) {
    displayName(jobConfig.displayName)
    
    // 基本情報
    description(jobConfig.description ?: 'reflection-cloud-apiリポジトリのマルチブランチパイプラインジョブ')
    
    // ブランチソースの設定
    branchSources {
        branchSource {
            source {
                github {
                    id(UUID.randomUUID().toString())
                    apiUri('https://api.github.com')
                    credentialsId('github-app-credentials')
                    repoOwner('tielec')
                    repository('reflection-cloud-api')
                    
                    // ブランチ検出の設定 - configureを使用
                    traits {
                        gitHubBranchDiscovery {
                            strategyId(3)  // すべてのブランチを検出
                        }
                    }
                }
            }
        }
    }
    
    // 孤立したアイテム戦略
    orphanedItemStrategy {
        discardOldItems {
            daysToKeep(-1)
            numToKeep(-1)
        }
    }
    
    // トリガー設定
    triggers {
        // 定期的なポーリング（30分ごと）
        periodicFolderTrigger {
            interval('30m')
        }
    }
    
    // パイプラインスクリプトのパス
    factory {
        workflowBranchProjectFactory {
            scriptPath('Jenkinsfile')
        }
    }
}