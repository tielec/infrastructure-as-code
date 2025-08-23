// jenkins/jobs/dsl/infrastructure/infrastructure_pulumi_dashboard_job.groovy

// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'infrastructure_pulumi_dashboard_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// 環境設定
def environments = [
    'dev': [
        displayName: 'Development',
        s3Bucket: '', // S3バケット名は実行時にクレデンシャルから動的に取得
        awsRegion: 'ap-northeast-1' // 東京リージョン
    ],
    'prod': [
        displayName: 'Production',
        s3Bucket: '', // S3バケット名は実行時にクレデンシャルから動的に取得
        awsRegion: 'ap-northeast-1' // 東京リージョン
    ]
]

// 各環境用のダッシュボードジョブを作成
environments.each { env, envConfig ->
    def jobPath = "delivery-management-jobs/${env == 'prod' ? 'production' : 'development'}/pulumi-dashboard"
    
    pipelineJob(jobPath) {
        displayName("Pulumi Projects Dashboard - ${envConfig.displayName}")
        
        description("""
            |Pulumi プロジェクトの統合ダッシュボード
            |
            |このジョブは、S3バックエンドに保存されているすべてのPulumiプロジェクトの状態を収集し、
            |統合ダッシュボードとして表示します。
            |
            |**環境**: ${envConfig.displayName}
            |**S3バケット**: ${envConfig.s3Bucket}
            |**リージョン**: ${envConfig.awsRegion}
            |
            |**機能**:
            |• 全プロジェクトの一覧表示
            |• 各スタックのリソース数とステータス
            |• 最終更新日時の表示
            |• リソースタイプ別の集計
            |""".stripMargin())
        
        // パラメータ定義
        parameters {
            // 環境（固定）
            choiceParam('ENVIRONMENT', [env], '環境（自動設定）')
            
            // S3バケット設定（固定）
            choiceParam('S3_BUCKET', [envConfig.s3Bucket], 'Pulumi State S3バケット（固定）')
            
            choiceParam('AWS_REGION', [envConfig.awsRegion], 'AWSリージョン（固定）')
            
            // AWS認証情報
            stringParam('AWS_ACCESS_KEY_ID', '', "AWS Access Key ID - S3バケットへの読み取りアクセス権限が必要です")
            
            nonStoredPasswordParam('AWS_SECRET_ACCESS_KEY', 'AWS Secret Access Key - セキュリティのため保存されません')
            
            nonStoredPasswordParam('AWS_SESSION_TOKEN', 'AWS Session Token（オプション） - STS一時認証情報を使用する場合')
            
            // フィルタリングオプション
            stringParam('PROJECT_FILTER', '*', '''プロジェクトフィルタ - 表示するプロジェクトをフィルタリング
                |* すべて表示: *
                |* 特定プロジェクト: project-name
                |'''.stripMargin())
            
            stringParam('STACK_FILTER', '*', '''スタックフィルタ - 表示するスタックをフィルタリング
                |* すべて表示: *
                |* 特定スタック: dev, prod
                |'''.stripMargin())
            
            // Jenkinsfileブランチ
            stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileが格納されているブランチ')
        }
        
        // ログローテーション設定
        logRotator {
            numToKeep(30)
            artifactNumToKeep(10)
        }
        
        // プロパティ設定
        properties {
            // 同時実行を制限
            disableConcurrentBuilds()
            
            // 再ビルド設定
            rebuild {
                autoRebuild(false)
                rebuildDisabled(false)
            }
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

println "=== Pulumi dashboard jobs creation completed ==="