// jenkins/jobs/dsl/infrastructure/infrastructure_ssm_dashboard_job.groovy

// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'infrastructure_ssm_dashboard_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// delivery-management-jobs/commonカテゴリに配置
def jobPath = "delivery-management-jobs/common/ssm-parameter-store-dashboard"

pipelineJob(jobPath) {
    displayName("SSM Parameter Store Dashboard")
        
    description("""
        |AWS Systems Manager Parameter Store ダッシュボード
        |
        |このジョブは、AWS SSMパラメータストアに保存されているパラメータを収集し、
        |見やすいダッシュボード形式で表示します。
        |
        |**機能**:
        |• 全パラメータの一覧表示
        |• パラメータ名、値、タイプ、説明、最終更新日の表示
        |• 階層構造での整理表示
        |• SecureStringパラメータの安全な表示
        |• フィルタリング機能
        |• CSV/JSONエクスポート機能
        |""".stripMargin())
        
    // パラメータ定義（重要: DSLで定義）
    parameters {
        // 環境選択
        choiceParam('ENVIRONMENT', ['dev', 'staging', 'prod', 'common'], '''実行環境
            |• dev: 開発環境のパラメータ
            |• staging: ステージング環境のパラメータ  
            |• prod: 本番環境のパラメータ
            |• common: 全環境共通のパラメータ
            |'''.stripMargin())
        
        // パラメータパスフィルタ
        stringParam('PARAMETER_PATH', '/', '''パラメータパス（プレフィックス）
            |例:
            |• / : すべてのパラメータ
            |• /jenkins-infra/ : Jenkins関連のパラメータのみ
            |• /lambda-api/ : Lambda API関連のパラメータのみ
            |'''.stripMargin())
        
        // パラメータ名フィルタ（ワイルドカード）
        stringParam('NAME_FILTER', '*', '''パラメータ名フィルタ（ワイルドカード対応）
            |例:
            |• * : すべて表示
            |• *database* : データベース関連のパラメータ
            |• /*/common/* : 各プロジェクトのcommonパラメータ
            |'''.stripMargin())
        
        // パラメータタイプフィルタ
        choiceParam('TYPE_FILTER', ['All', 'String', 'SecureString', 'StringList'], 
            'パラメータタイプでフィルタリング')
        
        // SecureStringの表示設定
        booleanParam('SHOW_SECURE_VALUES', false, 
            'SecureStringパラメータの値を表示（注意: 機密情報が表示されます）')
        
        // 結果の並び順
        choiceParam('SORT_BY', ['Name', 'LastModified', 'Type'], '''並び順
            |• Name: パラメータ名順
            |• LastModified: 最終更新日順（新しい順）
            |• Type: パラメータタイプ順
            |'''.stripMargin())
        
        // 最大表示件数
        stringParam('MAX_RESULTS', '500', '最大表示件数（デフォルト: 500）')
        
        // AWS設定
        choiceParam('AWS_REGION', ['ap-northeast-1', 'us-east-1', 'us-west-2'], 'AWSリージョン')
        
        // AWS認証情報
        stringParam('AWS_ACCESS_KEY_ID', '', 
            "AWS Access Key ID - SSMパラメータへの読み取りアクセス権限が必要です")
        
        nonStoredPasswordParam('AWS_SECRET_ACCESS_KEY', 
            'AWS Secret Access Key - セキュリティのため保存されません')
        
        nonStoredPasswordParam('AWS_SESSION_TOKEN', 
            'AWS Session Token（オプション） - STS一時認証情報を使用する場合')
        
        // 出力形式
        choiceParam('OUTPUT_FORMAT', ['HTML', 'JSON', 'CSV'], '''出力形式
            |• HTML: ブラウザで表示可能なダッシュボード
            |• JSON: プログラムで処理可能な形式
            |• CSV: Excelで開ける形式
            |'''.stripMargin())
        
        // 階層表示設定
        booleanParam('HIERARCHICAL_VIEW', true, 
            '階層構造で表示（パスの階層をツリー形式で表示）')
        
        // タグフィルタ（オプション）
        textParam('TAG_FILTERS', '', '''タグでフィルタリング（オプション）
            |形式: Key=Value （改行区切りで複数指定可能）
            |例:
            |Environment=Production
            |Project=Jenkins
            |'''.stripMargin())
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
        }
    }
    
    // ジョブプロパティ
    properties {
        // 同時実行を制限
        disableConcurrentBuilds()
        
        // ビルド履歴の保持設定
        buildDiscarder {
            logRotator {
                daysToKeep(7)
                numToKeep(20)
                artifactDaysToKeep(3)
                artifactNumToKeep(10)
            }
        }
    }
    
    // 実行環境の設定
    wrappers {
        // タイムアウト設定（5分）
        timeout {
            absolute(5)
        }
        
        // ANSI カラー出力を有効化
        ansiColor('xterm')
        
        // タイムスタンプを有効化
        timestamps()
    }
}