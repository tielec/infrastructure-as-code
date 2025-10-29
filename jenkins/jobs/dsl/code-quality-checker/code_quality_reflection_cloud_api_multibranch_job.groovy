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
                    repositoryUrl('https://github.com/tielec/reflection-cloud-api')
                    configuredByUrl(true)
                    apiUri('https://api.github.com')
                    credentialsId('github-app-credentials')
                    repoOwner('tielec')
                    repository('reflection-cloud-api')
                    
                    // ブランチ検出の設定
                    traits {
                        gitHubPullRequestDiscovery {
                            strategyId(2)  // プルリクエストのHEADとマージ後の両方を検出
                        }
                        gitHubIgnoreDraftPullRequestFilter()
                    }
                }
            }
        }
    }

    configure { node ->
        def traitsNode = node / 'sources' / 'jenkins.branch.BranchSource' / 'source' / 'traits'
        traitsNode.appendNode('org.jenkinsci.plugins.github__branch__source.IgnoreDraftPullRequestFilterTrait')
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
        // 定期的なポーリング（4時間ごと）
        periodicFolderTrigger {
            interval('240')  // 4時間 = 240分
        }
    }
    
    // パイプラインスクリプトのパス
    factory {
        workflowBranchProjectFactory {
            scriptPath('Jenkinsfile')
        }
    }
}
