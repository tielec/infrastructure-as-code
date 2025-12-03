/**
 * AI Workflow Auto Issue Job DSL
 *
 * AIによる自動Issue作成用ジョブ
 * EXECUTION_MODE: auto_issue（固定値、パラメータとして表示しない）
 * パラメータ数: 8個（最小）
 */

// リポジトリ情報を取得
def repositories = jenkinsManagedRepositories.collect { name, repo ->
    [
        name: name,
        url: repo.httpsUrl,
        credentialsId: repo.credentialsId
    ]
}

// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']
def jobKey = 'ai_workflow_auto_issue_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// 各リポジトリのジョブを作成
repositories.each { repo ->
    def jobName = "AI_Workflow/${repo.name}/${jobConfig.name}"

    pipelineJob(jobName) {
        displayName(jobConfig.displayName)

        description("""\
            |# AI Workflow - Auto Issue Creation
            |
            |リポジトリ: ${repo.name}
            |
            |## 概要
            |AIエージェントがリポジトリを探索し、バグや改善点を検出してIssueを自動作成します。
            |
            |## Issue検出カテゴリ
            |- bug: バグ・潜在的問題の検出（Phase 1で実装済み）
            |- refactor: リファクタリング候補の検出（Phase 2で実装予定）
            |- enhancement: 機能拡張提案（Phase 3で実装予定）
            |- all: 全カテゴリを検出
            |
            |## 機能
            |- 重複判定の類似度閾値設定（デフォルト: 0.8）
            |- 作成するIssueの最大数設定（デフォルト: 5）
            |
            |## 注意事項
            |- EXECUTION_MODEは内部的に'auto_issue'に固定されます
            |- ISSUE_URLは不要（リポジトリ探索により自動Issue作成）
            |- コスト上限: デフォルト \$5.00 USD
            """.stripMargin())

        // パラメータ定義
        parameters {
            // ========================================
            // 基本設定
            // ========================================
            stringParam('GITHUB_REPOSITORY', '', '''
GitHub リポジトリ（owner/repo）（必須）

例: tielec/ai-workflow-agent
            '''.stripIndent().trim())

            choiceParam('AGENT_MODE', ['auto', 'codex', 'claude'], '''
エージェントの実行モード
- auto: Codex APIキーがあれば Codex を優先し、なければ Claude Code を使用
- codex: Codex のみを使用（CODEX_API_KEY または OPENAI_API_KEY が必要）
- claude: Claude Code のみを使用（credentials.json が必要）
            '''.stripIndent().trim())

            // ========================================
            // Auto Issue 設定
            // ========================================
            choiceParam('AUTO_ISSUE_CATEGORY', ['bug', 'refactor', 'enhancement', 'all'], '''
Issue検出カテゴリ

- bug: バグ・潜在的問題の検出（Phase 1で実装済み）
- refactor: リファクタリング候補の検出（Phase 2で実装予定）
- enhancement: 機能拡張提案（Phase 3で実装予定）
- all: 全カテゴリを検出
            '''.stripIndent().trim())

            stringParam('AUTO_ISSUE_LIMIT', '5', '''
作成するIssueの最大数

1〜50の範囲で指定してください。
            '''.stripIndent().trim())

            stringParam('AUTO_ISSUE_SIMILARITY_THRESHOLD', '0.8', '''
重複判定の類似度閾値

0.0〜1.0の範囲で指定してください。
値が高いほど厳密に重複判定します（デフォルト: 0.8）。
            '''.stripIndent().trim())

            // ========================================
            // 実行オプション
            // ========================================
            booleanParam('DRY_RUN', false, '''
ドライランモード（API 呼び出しや Git 操作を行わず動作確認のみ実施）
            '''.stripIndent().trim())

            // ========================================
            // その他
            // ========================================
            stringParam('COST_LIMIT_USD', '5.0', '''
ワークフローあたりのコスト上限（USD）
            '''.stripIndent().trim())

            choiceParam('LOG_LEVEL', ['INFO', 'DEBUG', 'WARNING', 'ERROR'], '''
ログレベル
- INFO: 一般的な情報
- DEBUG: 詳細ログ（デバッグ用）
- WARNING / ERROR: 警告 / エラーのみ
            '''.stripIndent().trim())
        }

        // ログローテーション
        logRotator {
            numToKeep(30)
            daysToKeep(90)
        }

        // パイプライン定義
        definition {
            cpsScm {
                scm {
                    git {
                        remote {
                            url('https://github.com/tielec/ai-workflow-agent.git')
                            credentials('github-token')
                        }
                        branch('*/main')
                    }
                }
                scriptPath('Jenkinsfile')
            }
        }

        // 環境変数（EXECUTION_MODEを固定値として設定）
        environmentVariables {
            env('EXECUTION_MODE', 'auto_issue')
            env('WORKFLOW_VERSION', '0.2.0')
        }

        // プロパティ
        properties {
            disableConcurrentBuilds()
        }

        // ジョブの無効化状態
        disabled(false)
    }
}
