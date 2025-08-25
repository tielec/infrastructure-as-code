// jenkins/jobs/dsl/infrastructure/infrastructure_pulumi_dashboard_job.groovy

// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'infrastructure_pulumi_dashboard_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// delivery-management-jobs/commonカテゴリに配置
def jobPath = "delivery-management-jobs/common/pulumi-dashboard"

pipelineJob(jobPath) {
    displayName("Pulumi Projects Dashboard")
        
    description("""
        |Pulumi プロジェクトの統合ダッシュボード
        |
        |このジョブは、S3バックエンドに保存されているすべてのPulumiプロジェクトの状態を収集し、
        |統合ダッシュボードとして表示します。
        |
        |**機能**:
        |• 全プロジェクトの一覧表示
        |• 各スタックのリソース数とステータス
        |• 最終更新日時の表示
        |• リソースタイプ別の集計
        |""".stripMargin())
        
    // パラメータ定義
    parameters {
        // 環境（common固定）
        choiceParam('ENVIRONMENT', ['common'], '環境（common固定）')
        
        // S3バケット設定
        stringParam('S3_BUCKET', '', 'Pulumi State S3バケット名')
        
        choiceParam('AWS_REGION', ['ap-northeast-1'], 'AWSリージョン')
            
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
        // Jenkins Libraryブランチ
        stringParam('LIBRARY_BRANCH', 'main', 'Jenkins Shared Libraryのブランチ')
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

println "=== Pulumi dashboard jobs creation completed ==="