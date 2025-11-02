/**
 * AI Workflow Orchestrator - Job DSL
 *
 * GitHub Issue から PR 作成まで、Claude / Codex を使って自動開発ワークフローを実行する
 * 9 フェーズ構成: planning → requirements → design → test_scenario → implementation → test_implementation → testing → documentation → report → evaluation
 */

pipelineJob('AI_Workflow/ai_workflow_orchestrator') {
    description('''
AI駆動開発ワークフロー

GitHub Issue を入力として、要件定義から報告までの開発プロセスを AI が自律実行します。

【ワークフロー】
0. Phase 0: 計画 (Planning)
1. Phase 1: 要件定義 (Requirements)
2. Phase 2: 詳細設計 (Design)
3. Phase 3: テストシナリオ (Test Scenario)
4. Phase 4: 実装 (Implementation)
5. Phase 5: テスト実装 (Test Implementation)
6. Phase 6: テスト実行 (Testing)
7. Phase 7: ドキュメント作成 (Documentation)
8. Phase 8: レポート作成 (Report)
9. Phase 9: 評価 (Evaluation)

【実行モード】
- all_phases: 全フェーズを順次実行（resume により途中から再開可能）
- preset（推奨）: 定義済みワークフローパターンを実行（例: quick-fix, implementation, testing）
- single_phase: 指定フェーズのみ実行（デバッグ用）
- rollback: フェーズ差し戻し実行（v0.4.0、Issue #90）

【レビューとリトライ】
- PASS: 次フェーズへ進行
- PASS_WITH_SUGGESTIONS: 改善提案あり
- FAIL: 最大3回リトライ

【コスト管理】
- 1 ワークフローあたり最大 $5.00 USD（Claude API 使用料）
    '''.stripIndent())

    // パラメータ定義（Jenkinsfile には記述しないこと）
    parameters {
        // ========================================
        // 基本設定
        // ========================================
        stringParam('ISSUE_URL', '', '''
GitHub Issue URL（必須）

例: https://github.com/tielec/my-project/issues/123
注: Issue URL から対象リポジトリを自動判定します（マルチリポジトリ対応）
        '''.stripIndent().trim())

        stringParam('GITHUB_REPOSITORY', '', '''
GitHub リポジトリ（owner/repo）
注: 通常は ISSUE_URL から自動判定されるため、空欄で問題ありません
        '''.stripIndent().trim())

        stringParam('BRANCH_NAME', '', '''
作業ブランチ名（任意）
AI Workflow の作業ブランチを個別指定する場合に使用
空欄の場合は Issue 番号から自動生成されます
        '''.stripIndent().trim())

        choiceParam('AGENT_MODE', ['auto', 'codex', 'claude'], '''
エージェントの実行モード
- auto: Codex APIキーがあれば Codex を優先し、なければ Claude Code を使用
- codex: Codex のみを使用（CODEX_API_KEY または OPENAI_API_KEY が必要）
- claude: Claude Code のみを使用（credentials.json が必要）
        '''.stripIndent().trim())

        // ========================================
        // 実行制御
        // ========================================
        choiceParam('EXECUTION_MODE', ['all_phases', 'preset', 'single_phase', 'rollback'], '''
実行モード

- all_phases: planning から evaluation まで一括実行（resume により失敗フェーズから再開）
- preset: 定義済みワークフローパターンを実行（推奨）
- single_phase: START_PHASE で指定したフェーズのみ実行
- rollback: フェーズ差し戻し実行（v0.4.0、Issue #90）
        '''.stripIndent().trim())

        choiceParam('PRESET', ['quick-fix', 'implementation', 'testing', 'review-requirements', 'review-design', 'review-test-scenario', 'finalize'], '''
プリセット（preset モード時のみ有効）

- quick-fix: 軽微な修正用（Implementation → Documentation → Report）
- implementation: 通常の実装フロー（Implementation → TestImplementation → Testing → Documentation → Report）
- testing: テスト追加用（TestImplementation → Testing）
- review-requirements: 要件定義レビュー用（Planning → Requirements）
- review-design: 設計レビュー用（Planning → Requirements → Design）
- review-test-scenario: テストシナリオレビュー用（Planning → Requirements → Design → TestScenario）
- finalize: 最終化用（Documentation → Report → Evaluation）
        '''.stripIndent().trim())

        choiceParam('START_PHASE', ['planning', 'requirements', 'design', 'test_scenario', 'implementation', 'test_implementation', 'testing', 'documentation', 'report', 'evaluation'], '''
開始フェーズ（single_phase モード時のみ有効）
        '''.stripIndent().trim())

        // ========================================
        // Rollback 設定（v0.4.0、Issue #90）
        // ========================================
        choiceParam('ROLLBACK_TO_PHASE', ['implementation', 'planning', 'requirements', 'design', 'test_scenario', 'test_implementation', 'testing', 'documentation', 'report'], '''
差し戻し先フェーズ（rollback モード時のみ有効）

差し戻したいフェーズを指定します。メタデータが更新され、指定されたフェーズから再実行可能になります。
注: evaluation フェーズへの差し戻しはできません。
        '''.stripIndent().trim())

        choiceParam('ROLLBACK_TO_STEP', ['revise', 'execute', 'review'], '''
差し戻し先ステップ（rollback モード時、省略可）

デフォルトは revise です。
- execute: フェーズの最初から再実行
- review: レビューステップから再実行
- revise: 修正ステップから再実行（差し戻し理由がプロンプトに注入されます）
        '''.stripIndent().trim())

        textParam('ROLLBACK_REASON', '', '''
差し戻し理由（rollback モード時のみ有効、省略可）

差し戻しの理由を記述します。この内容は revise プロンプトに自動注入されます。
空欄の場合、CI環境では差し戻しが実行されません（インタラクティブ入力が必要）。
        '''.stripIndent().trim())

        stringParam('ROLLBACK_REASON_FILE', '', '''
差し戻し理由ファイルパス（rollback モード時、省略可）

差し戻し理由を記述したファイルのパスを指定します。
ROLLBACK_REASON と ROLLBACK_REASON_FILE の両方が指定された場合、ROLLBACK_REASON_FILE が優先されます。
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

    logRotator {
        numToKeep(30)
        daysToKeep(90)
    }

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

    environmentVariables {
        env('WORKFLOW_VERSION', '0.2.0')
    }

    properties {
        disableConcurrentBuilds()
    }
}
