// Lambda検証ジョブ

// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'infrastructure_lambda_verification_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// 環境設定
def environments = [
    'dev': [
        folderName: 'development',
        displayEnv: 'Development',
        description: '開発環境'
    ],
    'prod': [
        folderName: 'production',
        displayEnv: 'Production',
        description: '本番環境'
    ]
]

// 各環境に対してジョブを生成
environments.each { envKey, envConfig ->
    def jobPath = "delivery-management-jobs/${envConfig.folderName}/lambda-verification"
    
    pipelineJob(jobPath) {
        displayName('Lambda Deployment Verification')
        
        description("""Lambda API環境のデプロイメント検証と動作確認を実行します。

**環境**: ${envConfig.displayEnv} (${envKey})
**スクリプト**: scripts/lambda/verify-deployment.sh
**実行ノード**: ec2-fleet

**検証項目**:
- SSMパラメータの確認（API ID、エンドポイント、APIキー）
- Lambda関数の状態確認
- Lambda関数の実行テスト
- API Gatewayの存在確認とステージ確認
- エンドポイントテスト（health、version、echo）
- CloudWatchログの確認
- ネットワーク設定の確認
- Dead Letter Queueの設定確認""")
        
        parameters {
            // AGENT_LABELパラメータ
            choiceParam('AGENT_LABEL', ['ec2-fleet-micro', 'ec2-fleet-small', 'ec2-fleet-medium'],
                'Jenkins エージェントのラベル（micro: 1並列/1GB, small: 2並列/2GB, medium: 3並列/4GB）')

            // 環境（固定値、読み取り専用として表示）
            stringParam('ENVIRONMENT', envKey, '実行環境（固定）')
            
            // ブランチ選択
            stringParam('BRANCH', 'main', 'リポジトリブランチ（デフォルト: main）')
            
            // Jenkinsfileブランチ
            stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileが格納されているブランチ')
            
            // 詳細出力
            booleanParam('VERBOSE', false, '詳細ログを出力（APIキーの一部表示など）')
            
            // デバッグモード
            choiceParam('LOG_LEVEL', ['INFO', 'DEBUG', 'WARN', 'ERROR'], 'ログレベル')
        }
        
        // ログローテーション設定
        logRotator {
            numToKeep(30)
            artifactNumToKeep(10)
        }
        
        // プロパティ設定
        properties {
            // リビルド設定
            rebuild {
                autoRebuild(false)
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

// 処理完了メッセージ
println "=== Lambda verification jobs creation completed (dev/prod) ==="