// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'shared_library_ssm_parameter_test_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Shared_Library/AWS_Utils/${jobConfig.name}"

pipelineJob(fullJobName) {
    // 基本情報
    description('''### SSM Parameter Store共有ライブラリテスト

このジョブはSSMパラメータ取得ユーティリティの機能テストを実行します。

#### テスト内容
- 単一パラメータ取得
- 複数パラメータ一括取得
- パス配下のパラメータ取得
- 環境変数として設定
- エラーハンドリング
- パフォーマンステスト

#### 前提条件
- AWS CLIが設定済み
- SSM Parameter Storeへの読み取り権限
- テスト用パラメータが作成済み（または自動作成）

#### 使用方法
1. AWS_REGIONにテスト対象のリージョンを指定
2. TEST_PARAMETER_PATHにテスト用パラメータのパスを指定
3. TEST_TYPEで実行するテストを選択
4. 必要に応じてCREATE_TEST_PARAMSを有効化してテスト用パラメータを自動作成
''')
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
        stringParam('AWS_REGION', 'ap-northeast-1', 'AWSリージョン')
        stringParam('TEST_PARAMETER_PATH', '/jenkins/test', 'テスト用パラメータのパス')
        choiceParam('TEST_TYPE', ['all', 'single', 'multiple', 'path', 'withEnv'], 'テストタイプの選択')
        stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileが格納されているブランチ')
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
                    branch('*/' + '${JENKINSFILE_BRANCH}')
                }
            }
            scriptPath(jobConfig.jenkinsfile)
        }
    }
}