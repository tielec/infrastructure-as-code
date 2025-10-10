/**
 * AI Workflow Orchestrator - Job DSL定義
 *
 * GitHub IssueからPR作成まで、Claude AIによる自動開発を実行する
 * 6フェーズワークフロー（要件定義→詳細設計→テストシナリオ→実装→テスト→ドキュメント）
 */

pipelineJob('AI_Workflow/ai_workflow_orchestrator') {
    description('''
AI駆動開発自動化ワークフロー

GitHub IssueからPR作成まで、Claude AIが自動的に開発プロセスを実行します。

【ワークフロー】
1. Phase 1: 要件定義 (Requirements)
2. Phase 2: 詳細設計 (Design)
3. Phase 3: テストシナリオ (Test Scenario)
4. Phase 4: 実装 (Implementation)
5. Phase 5: テスト実行 (Testing)
6. Phase 6: ドキュメント作成 (Documentation)
7. PR作成

【レビュー】
各フェーズ完了後、AIが批判的思考レビューを実施：
- PASS: 次フェーズへ進行
- PASS_WITH_SUGGESTIONS: 改善提案あり、次フェーズへ進行
- FAIL: リトライ（最大3回）

【コスト管理】
- 1ワークフローあたり最大 $5.00 USD
- 超過時は自動停止

【現在の実装状況】
MVP v1.0.0: ワークフロー基盤のみ実装
Phase 1-6の自動実行は今後の拡張で実装予定

【ドキュメント】
- README: scripts/ai-workflow/README.md
- アーキテクチャ: scripts/ai-workflow/ARCHITECTURE.md
- ロードマップ: scripts/ai-workflow/ROADMAP.md
    '''.stripIndent())

    // パラメータ定義（重要: Jenkinsfileではパラメータ定義禁止）
    parameters {
        stringParam('ISSUE_URL', '', '''
GitHub Issue URL（必須）

例: https://github.com/tielec/infrastructure-as-code/issues/123

このIssueの内容を元に、要件定義から実装まで自動実行します。
        '''.stripIndent().trim())

        choiceParam('START_PHASE', ['planning', 'requirements', 'design', 'test_scenario', 'implementation', 'testing', 'documentation', 'report'], '''
開始フェーズ

ワークフローを開始するフェーズを指定します。
途中からジョブを再開する場合に使用します。

デフォルト: planning（最初から実行）
        '''.stripIndent().trim())

        stringParam('GITHUB_REPOSITORY', 'tielec/infrastructure-as-code', '''
GitHubリポジトリ

形式: owner/repo
例: tielec/infrastructure-as-code

デフォルト: tielec/infrastructure-as-code
        '''.stripIndent().trim())

        booleanParam('DRY_RUN', false, '''
ドライランモード

true: 実際のAPI呼び出しやGitコミットを行わず、動作確認のみ
false: 通常実行（デフォルト）
        '''.stripIndent().trim())

        booleanParam('SKIP_REVIEW', false, '''
レビュースキップ（開発・テスト用）

true: 各フェーズのAIレビューをスキップして次へ進む
false: レビュー実施（デフォルト、本番推奨）
        '''.stripIndent().trim())

        choiceParam('MAX_RETRIES', ['3', '1', '5', '10'], '''
最大リトライ回数

各フェーズでFAIL判定を受けた際のリトライ上限回数
デフォルト: 3回
        '''.stripIndent().trim())

        stringParam('COST_LIMIT_USD', '5.0', '''
コスト上限（USD）

1ワークフローあたりのClaude API利用料金上限
超過時はワークフローを停止します

デフォルト: $5.00
        '''.stripIndent().trim())

        choiceParam('LOG_LEVEL', ['INFO', 'DEBUG', 'WARNING', 'ERROR'], '''
ログレベル

DEBUG: 詳細ログ（開発・トラブルシューティング用）
INFO: 通常ログ（デフォルト）
WARNING: 警告以上
ERROR: エラーのみ
        '''.stripIndent().trim())
    }

    // ビルド保持設定
    logRotator {
        numToKeep(30)        // 最新30件を保持
        daysToKeep(90)       // 90日間保持
    }

    // Git設定
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

    // ビルドトリガー（手動実行のみ、自動トリガーなし）
    // GitHub Webhook連携は将来実装

    // 環境変数
    environmentVariables {
        env('WORKFLOW_VERSION', '1.0.0')
        env('PYTHON_PATH', '/usr/bin/python3')
    }

    // プロパティ
    properties {
        disableConcurrentBuilds()  // 同時実行を禁止
    }
}
