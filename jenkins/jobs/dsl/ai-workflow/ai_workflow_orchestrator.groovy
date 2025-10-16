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

【レビューとリトライ】
- PASS: 次フェーズへ進行
- PASS_WITH_SUGGESTIONS: 改善提案あり
- FAIL: 最大3回リトライ

【コスト管理】
- 1 ワークフローあたり最大 $5.00 USD（Claude API 使用料）
    '''.stripIndent())

    // パラメータ定義（Jenkinsfile には記述しないこと）
    parameters {
        stringParam('ISSUE_URL', '', '''
GitHub Issue URL（必須）

例: https://github.com/tielec/infrastructure-as-code/issues/123
        '''.stripIndent().trim())

        choiceParam('AGENT_MODE', ['auto', 'codex', 'claude'], '''
エージェントの実行モード
- auto: Codex APIキーがあれば Codex を優先し、なければ Claude Code を使用
- codex: Codex のみを使用（CODEX_API_KEY または OPENAI_API_KEY が必要）
- claude: Claude Code のみを使用（credentials.json が必要）
        '''.stripIndent().trim())

        choiceParam('EXECUTION_MODE', ['all_phases', 'preset', 'single_phase'], '''
実行モード

- all_phases: planning から evaluation まで一括実行（resume により失敗フェーズから再開）
- preset: 定義済みワークフローパターンを実行（推奨）
- single_phase: START_PHASE で指定したフェーズのみ実行
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

        stringParam('GITHUB_REPOSITORY', 'tielec/infrastructure-as-code', '''
GitHub リポジトリ（owner/repo）
        '''.stripIndent().trim())

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

        stringParam('COST_LIMIT_USD', '5.0', '''
ワークフローあたりのコスト上限（USD）
        '''.stripIndent().trim())

        choiceParam('LOG_LEVEL', ['INFO', 'DEBUG', 'WARNING', 'ERROR'], '''
ログレベル
- INFO: 一般的な情報
- DEBUG: 詳細ログ（デバッグ用）
- WARNING / ERROR: 警告 / エラーのみ
        '''.stripIndent().trim())

        stringParam('GIT_COMMIT_USER_NAME', 'AI Workflow Bot', '''
Git コミットユーザー名
        '''.stripIndent().trim())

        stringParam('GIT_COMMIT_USER_EMAIL', 'ai-workflow@example.com', '''
Git コミットメールアドレス
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
                        url('https://github.com/tielec/infrastructure-as-code.git')
                        credentials('github-token')
                    }
                    branch('*/main')
                }
            }
            scriptPath('jenkins/jobs/pipeline/ai-workflow/ai-workflow-orchestrator/Jenkinsfile')
        }
    }

    environmentVariables {
        env('WORKFLOW_VERSION', '1.0.0')
        env('PYTHON_PATH', '/usr/bin/python3')
    }

    properties {
        disableConcurrentBuilds()
    }
}
