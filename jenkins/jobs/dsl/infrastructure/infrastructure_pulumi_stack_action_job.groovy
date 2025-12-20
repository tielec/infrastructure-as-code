// jenkins/jobs/dsl/infrastructure/pulumi_deployments.groovy

// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'infrastructure_pulumi_stack_action_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// Pulumiプロジェクト設定を取得
def pulumiProjects = pulumi_projects ?: [:]

// 環境設定
def environments = [
    'common': [
        folderName: 'common',
        displayEnv: 'Common',
        awsAccountHint: '共通AWSアカウント',
        defaultSkipConfirmation: false,
        defaultRefresh: false
    ],
    'dev': [
        folderName: 'development',
        displayEnv: 'Development',
        awsAccountHint: '開発用AWSアカウント',
        defaultSkipConfirmation: true,
        defaultRefresh: false
    ],
    'prod': [
        folderName: 'production',
        displayEnv: 'Production',
        awsAccountHint: '本番用AWSアカウント',
        defaultSkipConfirmation: false,
        defaultRefresh: true
    ]
]

// Pulumiプロジェクトごとにジョブを生成
pulumiProjects.each { repoKey, repoConfig ->
    repoConfig.projects?.each { projectKey, projectConfig ->
        // プロジェクトが対応する環境をチェック
        def projectEnvironments = projectConfig.environments ?: ['common']
        
        projectEnvironments.each { envName ->
            def env = envName
            def envConfig = environments[env]
            
            if (!envConfig) {
                println "Warning: Unknown environment '${env}' for project ${projectKey}"
                return
            }
            
            // ジョブパス
            def jobPath = "delivery-management-jobs/${envConfig.folderName}/pulumi-deployments/${repoKey}-${projectKey}"
            
            pipelineJob(jobPath) {
                // Display Nameを「リポジトリ名 - プロジェクト名」形式に変更
                displayName("${repoKey} - ${projectKey}")
                
                // 環境に応じた説明文（簡潔版）
                def envWarning = env == 'prod' ? "⚠️ **本番環境** - 変更前に影響範囲を必ず確認してください\n\n" : 
                                env == 'common' ? "⚠️ **共通環境** - Jenkins基盤に影響する変更です\n\n" : ""
                
                description("""\
                    |${envWarning}${projectConfig.description ?: 'Pulumi Infrastructure Deployment'}
                    |
                    |**環境**: ${envConfig.displayEnv} | **スタック**: ${env} | **パス**: ${projectConfig.project_path}
                    |""".stripMargin())
                
                // パラメータ定義
                parameters {
                    // === AGENT_LABELパラメータ ===
                    choiceParam('AGENT_LABEL', ['ec2-fleet-medium', 'ec2-fleet-small', 'ec2-fleet-micro'],
                        'Jenkins エージェントのラベル（small: 2並列/2GB, medium: 3並列/4GB, micro: 1並列/1GB）')

                    // === 基本パラメータ ===

                    // 環境（読み取り専用として表示）
                    choiceParam('ENVIRONMENT', [env], '環境（自動設定） - この値は変更できません。ジョブの配置場所により自動的に決定されます。')
                    
                    // アクション
                    choiceParam('ACTION', ['preview', 'deploy', 'refresh', 'destroy'], '''実行するアクション - 実行するPulumiアクションを選択してください：
                        |* preview: 変更内容の確認のみ（推奨: 初回実行時）
                        |* deploy: リソースの作成・更新
                        |* refresh: 実インフラとPulumi状態の同期
                        |* destroy: リソースの削除（要注意）'''.stripMargin())
                    
                    // === AWS認証情報 ===
                    
                    stringParam('AWS_ACCESS_KEY_ID', '', "AWS Access Key ID（${envConfig.awsAccountHint}） - 一時的な認証情報を使用することを推奨します")
                    
                    nonStoredPasswordParam('AWS_SECRET_ACCESS_KEY', 'AWS Secret Access Key - セキュリティのため、この値は保存されません')
                    
                    nonStoredPasswordParam('AWS_SESSION_TOKEN', 'AWS Session Token（オプション） - STS一時認証情報を使用する場合に入力してください')
                    
                    choiceParam('AWS_REGION', [projectConfig.aws_region ?: 'ap-northeast-1', 'us-west-2'], 'AWSリージョン - プロジェクトで使用するAWSリージョン')
                    
                    // === Pulumiプロジェクト設定（固定値） ===
                    
                    choiceParam('PULUMI_REPO_URL', ['https://github.com/tielec/infrastructure-as-code'], 'Pulumiリポジトリ（固定） - インフラストラクチャコードのGitリポジトリ')
                    
                    choiceParam('PULUMI_PROJECT_PATH', [projectConfig.project_path], 'プロジェクトパス（固定） - Pulumiプロジェクトのパス')
                    
                    // ブランチ設定（環境により異なる）
                    if (env == 'dev') {
                        stringParam('PULUMI_TARGET_BRANCH', projectConfig.branch ?: 'main', 'ブランチ - 使用するGitブランチ（開発環境では変更可能）')
                    } else {
                        choiceParam('PULUMI_TARGET_BRANCH', [projectConfig.branch ?: 'main'], 'ブランチ（固定） - 本番環境では固定ブランチを使用')
                    }
                                        
                    choiceParam('PROJECT_TYPE', [projectConfig.project_type], 'プロジェクトタイプ（固定） - Pulumiプロジェクトの言語/フレームワーク')
                    
                    // === 実行オプション ===
                    
                    // SKIP_CONFIRMATION（本番環境と共通環境では無効化）
                    if (env == 'dev') {
                        booleanParam('SKIP_CONFIRMATION', envConfig.defaultSkipConfirmation, 
                            '確認プロンプトをスキップ - 開発環境では効率化のため有効にできます。')
                    } else {
                        // 本番環境と共通環境ではchoiceParamを使用して強制的にfalseに固定
                        def warningMsg = env == 'prod' ? '本番環境' : '共通環境'
                        choiceParam('SKIP_CONFIRMATION', ['false'], 
                            "確認プロンプトをスキップ - ⚠️ ${warningMsg}では無効化されています。安全のため、すべての操作で確認が必要です。")
                    }
                    
                    
                    // GENERATE_REPORT（本番環境と共通環境では常にtrue）
                    if (env == 'dev') {
                        booleanParam('GENERATE_REPORT', true, 'HTMLレポートを生成 - deploy/destroy時に詳細なHTMLレポートを生成します')
                    } else {
                        def envMsg = env == 'prod' ? '本番環境' : '共通環境'
                        choiceParam('GENERATE_REPORT', ['true'], "HTMLレポートを生成 - ${envMsg}では常にレポートが生成されます")
                    }
                    
                    // === Pulumi設定ファイルのアップロード（オプション） ===
                    // プロジェクト設定からuse_custom_config_fileの値を取得（デフォルトはfalse）
                    def useCustomConfigDefault = projectConfig.use_custom_config_file ?: false
                    booleanParam('USE_CUSTOM_CONFIG_FILE', useCustomConfigDefault, """カスタムPulumi設定ファイルを使用
                        |有効にすると、実行時にファイルアップロード画面が表示されます。
                        |環境に応じて以下のファイル名で配置されます：
                        |* ${env}環境: Pulumi.${env}.yaml
                        |
                        |アップロードされたファイルが最優先で使用されます。""".stripMargin())
                    
                    // === 詳細設定（通常は変更不要） ===

                    // Jenkinsfileブランチ
                    stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileが格納されているブランチ')
                }
                
                // ログローテーション設定
                logRotator {
                    numToKeep(50)
                    artifactNumToKeep(10)
                }
                
                // プロパティ設定
                properties {
                    // 同時実行の制限（重要）
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
    }
}

// 処理完了メッセージ
println "=== Pulumi deployment jobs creation completed ==="