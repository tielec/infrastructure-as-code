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
        github {
            id(UUID.randomUUID().toString())
            apiUri('https://api.github.com')
            scanCredentialsId('github-app-credentials')
            repoOwner('tielec')
            repository('reflection-cloud-api')
            repositoryUrl('https://github.com/tielec/reflection-cloud-api')
            
            // ブランチ検出設定
            traits {
                // ブランチ検出戦略
                // strategyId: 1 = オープンPRのブランチのみ
                // strategyId: 2 = 新しいPRとベースブランチ
                // strategyId: 3 = すべてのブランチ
                gitHubBranchDiscovery {
                    strategyId(3)  // すべてのブランチを検出
                }
                
                // PRのマージビルドを無効化
                gitHubPullRequestDiscovery {
                    strategyId(1)  // PRのヘッドのみビルド
                }
                
                // タグの検出を無効化
                gitHubTagDiscovery()
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
    
    // プロパティ設定
    configure { node ->
        // Docker設定（必要に応じて）
        def properties = node / 'properties'
        properties << 'org.jenkinsci.plugins.docker.workflow.declarative.FolderConfig' {
            dockerLabel('')
            registry(class: 'org.jenkinsci.plugins.docker.commons.credentials.DockerRegistryEndpoint') {
                credentialsId('')
            }
        }
        
        // ビルドの同時実行制御（必要に応じて）
        def triggers = node / 'triggers'
        if (triggers.isEmpty()) {
            node.appendNode('triggers')
        }
    }
    
    // フォルダプロパティ
    properties {
        folderCredentialsProperty {
            domainCredentials {
                domainCredentials {
                    domain {
                        name('github.com')
                        description('GitHub Domain')
                    }
                    credentials {
                        // ここに必要なクレデンシャルを追加
                    }
                }
            }
        }
    }
}