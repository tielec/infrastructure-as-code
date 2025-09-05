// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'infrastructure_terminate_lambda_nat_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Infrastructure_Management/${jobConfig.name}"

pipelineJob(fullJobName) {
    displayName(jobConfig.displayName)
    description("""\
        |# 概要
        |Lambda NAT Instanceを夜間に自動削除するジョブ
        |
        |## 目的
        |開発環境のコスト削減のため、夜間にLambda NAT InstanceとElastic IPを削除します。
        |
        |## 実行タイミング
        |* **自動実行**: 毎日 23:30 JST
        |* **手動実行**: 必要に応じていつでも実行可能
        |
        |## 削除対象リソース
        |* NAT Instance (EC2)
        |* Elastic IP
        |* ルートテーブルのルート設定
        |* CloudWatchアラーム
        |* SSMパラメータ
        |
        |## 注意事項
        |* 削除中はLambda関数から外部APIへのアクセスができません
        |* 再作成時（pulumi up）に新しいElastic IPが割り当てられます
        |""".stripMargin())

    // パラメータ定義（固定値）
    parameters {
        // === 固定パラメータ（変更不可） ===
        stringParam('ACTION', 'destroy', '実行するアクション（固定値：destroy）')
        stringParam('PULUMI_PROJECT_PATH', 'pulumi/lambda-nat', 'Pulumiプロジェクトのパス（固定値）')
        booleanParam('GENERATE_REPORT', false, 'HTMLレポート生成（固定値：false）')
        
        // === 環境設定 ===
        choiceParam('ENVIRONMENT', ['dev'], 'ターゲット環境')
        
        // === AWS認証情報 ===
        stringParam('AWS_ACCESS_KEY_ID', '', 'AWS Access Key ID')
        nonStoredPasswordParam('AWS_SECRET_ACCESS_KEY', 'AWS Secret Access Key')
        nonStoredPasswordParam('AWS_SESSION_TOKEN', 'AWS Session Token（一時認証情報を使用する場合）')
        choiceParam('AWS_REGION', ['ap-northeast-1'], 'AWSリージョン')
        
        // === Pulumiリポジトリ設定 ===
        stringParam('PULUMI_REPO_URL', 'https://github.com/tielec/infrastructure-as-code', 'GitリポジトリURL')
        stringParam('PULUMI_TARGET_BRANCH', 'main', 'チェックアウトするブランチ')
        choiceParam('PROJECT_TYPE', ['nodejs'], 'プロジェクトのタイプ')
        
        // === Pulumi設定 ===
        stringParam('PULUMI_BACKEND_URL', '', 'Pulumi S3バックエンドURL (空の場合はクレデンシャルから動的取得)')
        stringParam('PULUMI_CONFIG_PASSPHRASE_CREDENTIAL_ID', 'pulumi-config-passphrase', 'Pulumiスタック暗号化パスフレーズのCredential ID')
        
        // === 実行設定 ===
        booleanParam('SKIP_CONFIRMATION', true, 'デプロイ/削除時の確認をスキップ（固定値：true）')
        booleanParam('USE_CUSTOM_CONFIG_FILE', false, 'カスタムPulumi設定ファイルを使用しない（固定値：false）')
        
        // Jenkinsfile ブランチ
        stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileが格納されているブランチ')
    }

    // スケジューラ設定（毎日23:30 JST = 14:30 UTC）
    triggers {
        cron('30 14 * * *')
    }

    // 依存関係の保持設定
    keepDependencies(false)

    // ログローテーション設定
    logRotator {
        numToKeep(30)
        artifactNumToKeep(5)
        daysToKeep(30)
    }

    // 同時実行の制限
    throttleConcurrentBuilds {
        maxTotal(1)
        throttleDisabled(false)
    }

    // プロパティ設定
    properties {
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