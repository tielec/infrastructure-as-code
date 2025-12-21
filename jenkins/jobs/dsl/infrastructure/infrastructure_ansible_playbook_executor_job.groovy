// Ansible Playbook実行ジョブ

// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'infrastructure_ansible_playbook_executor_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// Ansibleプレイブック設定を取得
def ansiblePlaybooks = ansible_playbooks ?: [:]

// 環境設定
def environments = [
    'dev': [
        folderName: 'development',
        displayEnv: 'Development',
        description: '開発環境',
        defaultCheck: false
    ],
    'prod': [
        folderName: 'production',
        displayEnv: 'Production',
        description: '本番環境',
        defaultCheck: true
    ],
    'common': [
        folderName: 'common',
        displayEnv: 'Common',
        description: '共通環境（両環境で使用）',
        defaultCheck: false
    ]
]

// 各プレイブックごとにジョブを生成
ansiblePlaybooks.each { repoKey, repoConfig ->
    repoConfig.playbooks?.each { playbookKey, playbookConfig ->
        
        def category = playbookConfig.category ?: 'uncategorized'
        
        // 環境リストを取得（デフォルトはcommon）
        def targetEnvironments = playbookConfig.environments ?: ['common']
        
        // 各環境に対してジョブを生成
        targetEnvironments.each { env ->
            if (!environments.containsKey(env)) {
                println "Warning: Unknown environment '${env}' for playbook '${playbookKey}'"
                return
            }
            
            def envConfig = environments[env]
            def jobPath = "delivery-management-jobs/${envConfig.folderName}/ansible-deployments/${playbookKey}"
        
        // playbook_pathを処理（配列または文字列）
        def playbookPaths = []
        if (playbookConfig.playbook_path instanceof List) {
            playbookPaths = playbookConfig.playbook_path
        } else {
            playbookPaths = [playbookConfig.playbook_path]
        }
        
        // PLAYBOOKSパラメータのデフォルト値を設定
        def playbooksDefaultValue = playbookPaths.join(',')
        
        // ANSIBLE_EXTRA_VARSのデフォルト値を取得（存在しない場合は空文字列）
        def ansibleExtraVarsDefault = playbookConfig.ansible_extra_vars ?: ''
        
        pipelineJob(jobPath) {
            displayName(playbookConfig.display_name ?: playbookKey)
            
            def playbookListText = playbookPaths.size() > 1 ? 
                "**プレイブック** (${playbookPaths.size()}個):\n${playbookPaths.collect { '  - ' + it }.join('\n')}" :
                "**プレイブック**: ${playbookPaths[0]}"
            
            // teardownジョブの場合は警告を追加
            def warningText = ""
            if (playbookKey.contains('teardown')) {
                warningText = """
⚠️ **警告**: このジョブはJenkins環境を完全に削除します！
⚠️ 削除後は復旧できません。実行前に必ず確認してください。
                
"""
            }
            
            description("""${warningText}${playbookConfig.description ?: 'Ansible Playbook Execution'}
            
${playbookListText}
**カテゴリ**: ${category}
**リポジトリ**: ${repoKey}""")
            
            parameters {
                // AGENT_LABELパラメータ
                choiceParam('AGENT_LABEL', ['ec2-fleet-micro', 'ec2-fleet-small', 'ec2-fleet-medium'],
                    'Jenkins エージェントのラベル（micro: 1並列/1GB, small: 2並列/2GB, medium: 3並列/4GB）')

                // 環境選択（固定値：このジョブの環境のみ）
                choiceParam('ENVIRONMENT', [env], '実行環境')
                
                // AWSリージョン
                choiceParam('AWS_REGION', ['us-west-2', 'ap-northeast-1'], 'AWSリージョン')
                
                // ブランチ選択
                stringParam('BRANCH', 'main', 'リポジトリブランチ（デフォルト: main）')
                
                // Jenkinsfileブランチ
                stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileが格納されているブランチ')
                
                // プレイブックパス（デフォルト値を設定）
                stringParam('PLAYBOOKS', playbooksDefaultValue, 
                    playbookPaths.size() > 1 ? 
                    '実行するプレイブック（カンマ区切り）\n順番を変更する場合は編集してください' : 
                    'プレイブックパス（自動設定）')
                
                // カスタム設定ファイルオプション
                booleanParam('USE_CUSTOM_CONFIG_FILE', false, 'カスタムgroup_vars/all.yml設定を使用（対話的に値を更新）')
                
                // Ansibleオプション
                stringParam('ANSIBLE_EXTRA_VARS', ansibleExtraVarsDefault, '''追加のAnsible変数（例: key1=value1 key2=value2）

【重要】Lambda Teardown Pipeline実行時の必須パラメータ:
- 非対話モード（Jenkins/CI）から実行する場合、force_destroy=true の明示的な設定が必須です
- 例: env=dev force_destroy=true
- SSMパラメータも削除する場合: env=dev force_destroy=true destroy_ssm=true
- 詳細は jenkins/README.md の「Lambda Teardown Pipeline」セクションを参照''')
                
                booleanParam('ANSIBLE_VERBOSE', false, 'Ansibleの詳細出力を有効化（-vvv）')
                
                booleanParam('ANSIBLE_CHECK', false, 'チェックモード（実際の変更は行わない）')
                
                stringParam('ANSIBLE_LIMIT', '', 'ホストの制限（例: controller,agent）')
                
                stringParam('ANSIBLE_TAGS', '', '実行するタグ（カンマ区切り）')
                
                stringParam('ANSIBLE_SKIP_TAGS', '', 'スキップするタグ（カンマ区切り）')
                
                // 実行制御
                booleanParam('DRY_RUN', false, '実行コマンドの確認のみ（実際には実行しない）')
            }
            
            // ログローテーション設定
            logRotator {
                numToKeep(30)
                artifactNumToKeep(5)
            }
            
            // プロパティ設定
            properties {
                // 同時実行の制限
                disableConcurrentBuilds()
            }
            
            // スケジュール設定（設定がある場合のみ）
            if (playbookConfig.schedule) {
                triggers {
                    cron(playbookConfig.schedule)
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
println "=== Ansible playbook jobs creation completed ==="
