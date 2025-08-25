// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'admin_restore_config_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Admin_Jobs/${jobConfig.name}"

pipelineJob(fullJobName) {
    displayName(jobConfig.displayName)
    description('''\
        |Jenkinsの設定ファイルをリストアするジョブ
        |
        |## 概要
        |指定されたGitブランチから設定ファイルを取得し、Jenkinsの設定として適用します。
        |
        |### リストア元
        |* リポジトリ: [infrastructure-as-code](https://github.com/tielec/infrastructure-as-code)
        |* デフォルトブランチ: main
        |* デフォルト設定ファイル: jenkins/config/casc/jenkins.yaml
        |
        |### 処理内容
        |1. 設定ファイルの検証
        |2. 現在の設定のバックアップ
        |3. 新しい設定の適用
        |4. （オプション）Jenkinsの再起動
        |'''.stripMargin())
    
    // 依存関係の保持設定
    keepDependencies(false)
    
    // ビルド履歴の保持設定
    logRotator {
        daysToKeep(30)
        numToKeep(30)
        artifactDaysToKeep(-1)
        artifactNumToKeep(-1)
    }
    
    // プロパティ設定
    properties {
        // リビルド設定
        rebuild {
            autoRebuild(false)
            rebuildDisabled(false)
        }
    }
    
    // 同時実行制御
    throttleConcurrentBuilds {
        maxTotal(1)
        throttleDisabled(false)
    }
    
    // パラメータ設定
    parameters {
        stringParam('TARGET_BRANCH', 'main', 'リストア対象のブランチ')
        stringParam('CONFIG_FILE', 'jenkins/config/casc/jenkins.yaml', 'リストア対象の設定ファイルパス')
        booleanParam('RESTART_JENKINS', false, 'リストア後にJenkinsを再起動するか')
        stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileが格納されているブランチ')
        // Jenkins Libraryブランチ
        stringParam('LIBRARY_BRANCH', 'main', 'Jenkins Shared Libraryのブランチ')
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
    
    // 無効化設定
    disabled(false)
}
