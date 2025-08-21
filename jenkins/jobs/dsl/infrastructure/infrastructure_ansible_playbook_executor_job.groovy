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
                // 環境選択
                choiceParam('ENVIRONMENT', ['dev', 'staging', 'prod'], '実行環境')
                
                // ブランチ選択
                stringParam('BRANCH', 'main', 'リポジトリブランチ（デフォルト: main）')
                
                // プレイブックパス（デフォルト値を設定）
                stringParam('PLAYBOOKS', playbooksDefaultValue, 
                    playbookPaths.size() > 1 ? 
                    '実行するプレイブック（カンマ区切り）\n順番を変更する場合は編集してください' : 
                    'プレイブックパス（自動設定）')
                
                // Ansibleオプション
                stringParam('ANSIBLE_EXTRA_VARS', '', '追加のAnsible変数（例: key1=value1 key2=value2）')
                
                booleanParam('ANSIBLE_VERBOSE', false, 'Ansibleの詳細出力を有効化（-vvv）')
                
                booleanParam('ANSIBLE_CHECK', false, 'チェックモード（実際の変更は行わない）')
                
                stringParam('ANSIBLE_LIMIT', '', 'ホストの制限（例: controller,agent）')
                
                stringParam('ANSIBLE_TAGS', '', '実行するタグ（カンマ区切り）')
                
                stringParam('ANSIBLE_SKIP_TAGS', '', 'スキップするタグ（カンマ区切り）')
                
                // 実行制御
                booleanParam('DRY_RUN', false, '実行コマンドの確認のみ（実際には実行しない）')
                
                // tmux実行オプション（設定で有効な場合のみ表示）
                if (playbookConfig.enable_tmux ?: playbookConfig.enable_nohup) {
                    booleanParam('USE_TMUX', playbookConfig.enable_tmux ?: playbookConfig.enable_nohup, 
                        'tmuxセッションでバックグラウンド実行\n長時間実行のプレイブックで推奨、リアルタイムログ確認可能')
                    
                    def timeoutMinutes = playbookConfig.tmux_timeout_minutes ?: playbookConfig.nohup_timeout_minutes ?: 60
                    stringParam('TMUX_TIMEOUT_MINUTES', timeoutMinutes.toString(), 
                        'tmux実行時のタイムアウト時間（分）')
                    
                    // 複数プレイブックの場合、タイムアウト時の動作を追加
                    if (playbookPaths.size() > 1) {
                        def continueOnTimeout = playbookConfig.continue_on_timeout ?: false
                        booleanParam('CONTINUE_ON_TIMEOUT', continueOnTimeout, 
                            'タイムアウト時も次のプレイブックを続行\n⚠️ 注意: タイムアウトしたプレイブックの処理は不完全な可能性があります')
                    }
                }
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