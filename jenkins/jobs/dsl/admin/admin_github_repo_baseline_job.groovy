import jenkins.model.Jenkins

// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'admin_github_repo_baseline_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Admin_Jobs/${jobConfig.name}"

pipelineJob(fullJobName) {
    displayName(jobConfig.displayName)

    // 基本情報
    description('GitHubリポジトリに共通ベースライン（ルールセット、ブランチ保護、セキュリティ設定、ラベル）を一括適用するジョブです。')
    keepDependencies(false)
    disabled(false)

    // ビルド履歴の保持設定
    logRotator {
        daysToKeep(30)
        numToKeep(30)
        artifactDaysToKeep(7)
        artifactNumToKeep(10)
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

    // パラメータ定義
    parameters {
        // AGENT_LABELパラメータ
        choiceParam('AGENT_LABEL', ['ec2-fleet-micro', 'ec2-fleet-small', 'ec2-fleet-medium'],
            'Jenkins エージェントのラベル（micro: 1並列/1GB, small: 2並列/2GB, medium: 3並列/4GB）')

        // 基本設定
        stringParam('REPO_URL', '',
            'GitHubリポジトリのURL (必須。複数指定時はカンマまたは改行区切り)')

        choiceParam('ACTION', ['DRY_RUN', 'APPLY'],
            '実行する操作（DRY_RUN: 差分表示のみ、APPLY: 実際に適用）')

        choiceParam('TEMPLATE', ['default', 'strict', 'minimal'],
            '適用するベースラインテンプレート（default: 推奨設定、strict: セキュリティ重視、minimal: 基本設定のみ）')

        // 適用対象選択
        booleanParam('APPLY_RULESETS', true, 'ルールセットを適用する')
        booleanParam('APPLY_BRANCH_PROTECTION', true, 'ブランチ保護を適用する')
        booleanParam('APPLY_SECURITY', true, 'セキュリティ設定（Dependabot、Secret Scanning）を適用する')
        booleanParam('APPLY_LABELS', true, 'ラベルを適用する')

        // 詳細オプション
        stringParam('TARGET_BRANCH', '',
            '保護対象のブランチ名（空の場合はリポジトリのデフォルトブランチを使用）')

        booleanParam('FORCE_UPDATE', false,
            '既存設定を上書きする（警告: 既存設定が失われる可能性があります）')

        // Jenkinsfileブランチ
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
                    branch('${JENKINSFILE_BRANCH}')
                }
            }
            scriptPath(jobConfig.jenkinsfile)
            lightweight(true)
        }
    }
}
