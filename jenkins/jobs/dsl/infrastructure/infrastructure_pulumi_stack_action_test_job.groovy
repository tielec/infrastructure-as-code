// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'infrastructure_pulumi_stack_action_test_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Pipeline_Tests/Infrastructure/${jobConfig.name}"

pipelineJob(fullJobName) {
    displayName(jobConfig.displayName)
    description("""\
        |# 概要
        |Pulumiを使用したインフラストラクチャの管理パイプライン
        |
        |## 機能
        |* **プレビュー**: 変更内容の事前確認
        |* **デプロイ**: インフラストラクチャのデプロイメント
        |* **削除**: リソースの削除
        |
        |## サポートするプロジェクトタイプ
        |* Node.js/TypeScript
        |* Python
        |* Go
        |* .NET
        |
        |## レポート機能
        |* デプロイ/削除時のHTMLレポート自動生成
        |* スタック情報の可視化
        |* 依存関係グラフの生成
        |""".stripMargin())

    // パラメータ定義
    parameters {
        // === 基本パラメータ ===
        choiceParam('ENVIRONMENT', ['dev'], 'デプロイ先環境')
        choiceParam('ACTION', ['preview', 'deploy', 'destroy'], '実行するアクション')
        choiceParam('AGENT_LABEL', ['ec2-fleet-small', 'ec2-fleet-medium', 'ec2-fleet-micro'], 'Jenkins エージェントのラベル')

        // === AWS認証情報 ===
        stringParam('AWS_ACCESS_KEY_ID', '', 'AWS Access Key ID')
        nonStoredPasswordParam('AWS_SECRET_ACCESS_KEY', 'AWS Secret Access Key')
        nonStoredPasswordParam('AWS_SESSION_TOKEN', 'AWS Session Token（一時認証情報を使用する場合）')
        choiceParam('AWS_REGION', ['ap-northeast-1', 'us-west-2'], 'AWSリージョン')        
        // === Pulumiプロジェクト設定 ===
        choiceParam('PULUMI_REPO_URL', ['https://github.com/tielec/infrastructure-as-code'], 'GitリポジトリURL')      
        stringParam('PULUMI_TARGET_BRANCH', 'main', 'チェックアウトするブランチ')
        choiceParam('PULUMI_PROJECT_PATH', ['pulumi/test-s3'], 'テスト用Pulumiプロジェクトのパス')
        choiceParam('PROJECT_TYPE', ['nodejs'], 'プロジェクトのタイプ')
        
        // === オプション設定 ===
        booleanParam('SKIP_CONFIRMATION', true, 'デプロイ/削除時の確認をスキップ')
        booleanParam('GENERATE_REPORT', true, 'HTMLレポートを生成する')
        
        // === Pulumi設定ファイルのアップロード（オプション） ===
        booleanParam('USE_CUSTOM_CONFIG_FILE', false, """カスタムPulumi設定ファイルを使用
            |有効にすると、実行時にファイルアップロード画面が表示されます。
            |環境に応じて以下のファイル名で配置されます：
            |* dev環境: Pulumi.dev.yaml
            |
            |アップロードされたファイルが最優先で使用されます。""".stripMargin())
        
        // Jenkinsfile ブランチ
        stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileが格納されているブランチ')
    }

    // 依存関係の保持設定
    keepDependencies(false)

    // ログローテーション設定
    logRotator {
        numToKeep(30)
        artifactNumToKeep(10)
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
