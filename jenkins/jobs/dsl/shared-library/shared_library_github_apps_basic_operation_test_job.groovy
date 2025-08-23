// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'shared_library_github_apps_basic_operation_test_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Shared_Library/Git_Utils/${jobConfig.name}"

pipelineJob(fullJobName) {
    // 基本情報
    displayName(jobConfig.displayName)
    description('GitHub Apps認証を使用した基本操作をテストするジョブです。')
    keepDependencies(false)
    disabled(false)

    // ビルド履歴の保持設定
    logRotator {
        daysToKeep(30)
        numToKeep(30)
        artifactDaysToKeep(-1)
        artifactNumToKeep(-1)
    }

    // パラメータ定義
    parameters {
        choiceParam('AUTH_TYPE', ['GITHUB_APP', 'PAT'], 'GitHub認証タイプの選択')
        stringParam('GITHUB_APP_CREDENTIALS_ID', System.getenv("GITHUB_APP_CREDENTIALS_ID") ?: 'github-app-credentials', 'GitHub App認証用のJenkins認証情報ID')
        stringParam('PAT_CREDENTIALS_ID', 'github-pat', 'Personal Access Token用のJenkins認証情報ID')
        stringParam('REPO_OWNER', 'tielec', 'リポジトリオーナー名')
        stringParam('REPO_NAME', 'infrastructure-as-code', 'リポジトリ名')
        stringParam('BASE_BRANCH', 'main', 'PRのベースブランチ（マージ先のブランチ）')
        stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileが格納されているブランチ')
    }

    // プロパティ設定
    properties {
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
}
