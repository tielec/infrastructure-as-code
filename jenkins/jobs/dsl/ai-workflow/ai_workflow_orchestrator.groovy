/**
 * AI Workflow Orchestrator - Job DSL定義
 *
 * GitHub IssueからPR作成まで、Claude AIによる自動開発を実行する
 * 8フェーズワークフロー（計画→要件定義→詳細設計→テストシナリオ→実装→テスト実装→テスト→ドキュメント）
 */

pipelineJob('AI_Workflow/ai_workflow_orchestrator') {
    description('''
AI駆動開発自動化ワークフロー

GitHub IssueからPR作成まで、Claude AIが自動的に開発プロセスを実行します。

【ワークフロー】
0. Phase 0: 計画 (Planning)
1. Phase 1: 要件定義 (Requirements)
2. Phase 2: 詳細設計 (Design)
3. Phase 3: テストシナリオ (Test Scenario)
4. Phase 4: 実装 (Implementation)
5. Phase 5: テスト実装 (Test Implementation)
6. Phase 6: テスト実行 (Testing)
7. Phase 7: ドキュメント作成 (Documentation)
8. Phase 8: レポート生成 (Report)
9. Phase 9: プロジェクト評価 (Evaluation)

【実行モード】
- all_phases（推奨）: 全フェーズを1つのステージで一括実行
  - resume機能により、失敗したフェーズから自動再開
  - 実行時間とコストを最適化
- single_phase（デバッグ用）: 特定のフェーズのみ実行

【レビュー】
各フェーズ完了後、AIが批判的思考レビューを実施：
- PASS: 次フェーズへ進行
- PASS_WITH_SUGGESTIONS: 改善提案あり、次フェーズへ進行
- FAIL: リトライ（最大3回）

【resume機能】
途中で失敗した場合、次回実行時に失敗したフェーズから自動再開：
- メタデータ（.ai-workflow/issue-XXX/metadata.json）に記録された進捗を活用
- 無駄な実行を避け、コストを削減
- --force-resetフラグで最初から実行し直すことも可能

【コスト管理】
- 1ワークフローあたり最大 $5.00 USD
- 超過時は自動停止

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

        choiceParam('EXECUTION_MODE', ['all_phases', 'single_phase'], '''
実行モード

- all_phases: 全フェーズを一括実行（planning → report）（デフォルト、推奨）
- single_phase: START_PHASEで指定したフェーズのみ実行（デバッグ用）

デフォルト: all_phases

【all_phasesモードの特徴】
- resume機能: 途中で失敗した場合、次回実行時に失敗したフェーズから自動再開
- コスト効率: 無駄な実行を避け、必要なフェーズのみ実行
- Phase 0-9を順次実行（planning → requirements → ... → evaluation）
        '''.stripIndent().trim())

        choiceParam('START_PHASE', ['planning', 'requirements', 'design', 'test_scenario', 'implementation', 'test_implementation', 'testing', 'documentation', 'report', 'evaluation'], '''
開始フェーズ

EXECUTION_MODEに応じて動作が変わります：
- all_phases: 無視される（常にplanningから開始、resume機能により自動再開）
- single_phase: このフェーズのみ実行

デフォルト: planning
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

        booleanParam('FORCE_RESET', false, '''
強制リセット

全フェーズを最初から実行し直します。
既存のメタデータとワークフロー成果物を削除して新規実行します。

true: メタデータをクリアして最初から実行
false: 通常実行（resume機能により途中から再開）（デフォルト）

注意: 破壊的操作です。既存の進捗はすべて失われます。
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

        stringParam('GIT_COMMIT_USER_NAME', 'AI Workflow Bot', '''
Gitコミット時のユーザー名

AIワークフローがコミットを作成する際のGitユーザー名を指定します。

デフォルト: AI Workflow Bot
        '''.stripIndent().trim())

        stringParam('GIT_COMMIT_USER_EMAIL', 'ai-workflow@example.com', '''
Gitコミット時のメールアドレス

AIワークフローがコミットを作成する際のGitメールアドレスを指定します。

デフォルト: ai-workflow@example.com
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
