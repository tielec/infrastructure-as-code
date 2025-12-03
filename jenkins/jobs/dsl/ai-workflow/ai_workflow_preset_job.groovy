/**
 * AI Workflow Preset Job DSL
 *
 * プリセット実行用ジョブ（定義済みワークフローパターンを実行）
 * EXECUTION_MODE: preset（固定値、パラメータとして表示しない）
 * パラメータ数: 15個（all_phasesの14個 + PRESET）
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
def jobKey = 'ai_workflow_preset_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// 各リポジトリのジョブを作成
repositories.each { repo ->
    def jobName = "AI_Workflow/${repo.name}/${jobConfig.name}"

    pipelineJob(jobName) {
        displayName(jobConfig.displayName)

        description("""\
            |# AI Workflow - Preset Execution
            |
            |リポジトリ: ${repo.name}
            |
            |## 概要
            |定義済みワークフローパターンを実行します（quick-fix, implementation等）。
            |
            |## プリセット
            |- quick-fix: 軽微な修正用（Implementation → Documentation → Report）
            |- implementation: 通常の実装フロー（Implementation → TestImplementation → Testing → Documentation → Report）
            |- testing: テスト追加用（TestImplementation → Testing）
            |- review-requirements: 要件定義レビュー用（Planning → Requirements）
            |- review-design: 設計レビュー用（Planning → Requirements → Design）
            |- review-test-scenario: テストシナリオレビュー用（Planning → Requirements → Design → TestScenario）
            |- finalize: 最終化用（Documentation → Report → Evaluation）
            |
            |## 注意事項
            |- EXECUTION_MODEは内部的に'preset'に固定されます
            |- コスト上限: デフォルト \$5.00 USD
            """.stripMargin())

        // パラメータ定義
        parameters {
            // ========================================
            // 基本設定
            // ========================================
            stringParam('ISSUE_URL', '', '''
GitHub Issue URL（必須）

例: https://github.com/tielec/my-project/issues/123
注: Issue URL から対象リポジトリを自動判定します
            '''.stripIndent().trim())

            stringParam('BRANCH_NAME', '', '''
作業ブランチ名（任意）
空欄の場合は Issue 番号から自動生成されます
            '''.stripIndent().trim())

            choiceParam('AGENT_MODE', ['auto', 'codex', 'claude'], '''
エージェントの実行モード
- auto: Codex APIキーがあれば Codex を優先し、なければ Claude Code を使用
- codex: Codex のみを使用（CODEX_API_KEY または OPENAI_API_KEY が必要）
- claude: Claude Code のみを使用（credentials.json が必要）
            '''.stripIndent().trim())

            // ========================================
            // プリセット設定
            // ========================================
            choiceParam('PRESET', ['quick-fix', 'implementation', 'testing', 'review-requirements', 'review-design', 'review-test-scenario', 'finalize'], '''
プリセット（必須）

- quick-fix: 軽微な修正用（Implementation → Documentation → Report）
- implementation: 通常の実装フロー（Implementation → TestImplementation → Testing → Documentation → Report）
- testing: テスト追加用（TestImplementation → Testing）
- review-requirements: 要件定義レビュー用（Planning → Requirements）
- review-design: 設計レビュー用（Planning → Requirements → Design）
- review-test-scenario: テストシナリオレビュー用（Planning → Requirements → Design → TestScenario）
- finalize: 最終化用（Documentation → Report → Evaluation）
            '''.stripIndent().trim())

            // ========================================
            // 実行オプション
            // ========================================
            booleanParam('DRY_RUN', false, '''
ドライランモード（API 呼び出しや Git 操作を行わず動作確認のみ実施）
            '''.stripIndent().trim())

            booleanParam('SKIP_REVIEW', false, '''
AI レビューをスキップする（検証・デバッグ用）
            '''.stripIndent().trim())

            booleanParam('FORCE_RESET', false, '''
メタデータを初期化して最初から実行する
            '''.stripIndent().trim())

            choiceParam('MAX_RETRIES', ['3', '1', '5', '10'], '''
フェーズ失敗時の最大リトライ回数
            '''.stripIndent().trim())

            booleanParam('CLEANUP_ON_COMPLETE_FORCE', false, '''
Evaluation Phase完了後にワークフローディレクトリを強制削除
詳細: Issue #2、v0.3.0で追加
            '''.stripIndent().trim())

            // ========================================
            // Git 設定
            // ========================================
            stringParam('GIT_COMMIT_USER_NAME', 'AI Workflow Bot', '''
Git コミットユーザー名
            '''.stripIndent().trim())

            stringParam('GIT_COMMIT_USER_EMAIL', 'ai-workflow@example.com', '''
Git コミットメールアドレス
            '''.stripIndent().trim())

            // ========================================
            // AWS 認証情報（Infrastructure as Code 用）
            // ========================================
            stringParam('AWS_ACCESS_KEY_ID', '', '''
AWS アクセスキー ID（任意）
Infrastructure as Code実行時に必要
            '''.stripIndent().trim())

            nonStoredPasswordParam('AWS_SECRET_ACCESS_KEY', '''
AWS シークレットアクセスキー（任意）
Infrastructure as Code実行時に必要
            '''.stripIndent().trim())

            nonStoredPasswordParam('AWS_SESSION_TOKEN', '''
AWS セッショントークン（任意）
一時的な認証情報を使用する場合
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
            env('EXECUTION_MODE', 'preset')
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
