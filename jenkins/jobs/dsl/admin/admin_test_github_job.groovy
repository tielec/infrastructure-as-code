// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'admin_test_github_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Admin_Jobs/${jobConfig.name}"

job(fullJobName) {
    displayName(jobConfig.displayName)
    description('''\
        |GitHub リポジトリへのアクセステストを行うジョブです。
        |
        |### 主な機能
        |* 指定されたGitHubリポジトリにアクセスできることを確認
        |* 認証情報（PAT）が正しく機能していることを検証
        |
        |### 確認項目
        |* リポジトリへの接続
        |* ブランチの取得
        |* コードのチェックアウト
        |
        |### 注意
        |* このジョブは認証情報のテストのみを目的としています
        |* 実際のビルド処理は行いません
        |'''.stripMargin())

    // プロパティの設定
    properties {
        rebuild {
            autoRebuild(false)
            rebuildDisabled(false)
        }
        
        rateLimitBuilds {
            throttle {
                durationName('second')
                count(1)
                userBoost(false)
            }
        }
    }

    // パラメータ定義
    parameters {
        stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileが格納されているブランチ')
        // Jenkins Libraryブランチ
        stringParam('LIBRARY_BRANCH', 'main', 'Jenkins Shared Libraryのブランチ')
    }
    
    // Git設定
    scm {
        git {
            remote {
                url(jenkinsPipelineRepo.url)
                credentials(jenkinsPipelineRepo.credentials)
            }
            branch('${JENKINSFILE_BRANCH}')
        }
    }

    // ジョブの基本設定
    keepDependencies(false)
    disabled(false)
    concurrentBuild(false)
    
    // ビルドラッパー
    wrappers {
        preBuildCleanup {
            deleteDirectories(false)
            cleanupParameter('')
        }
    }
}
