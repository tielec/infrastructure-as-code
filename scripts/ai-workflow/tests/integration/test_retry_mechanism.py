"""リトライメカニズムの統合テスト (Issue #331)

execute()失敗時のリトライ機能が正しく動作することを検証する統合テスト。
実際のPhaseクラス、メタデータ、GitHub、Git連携を統合的にテストする。
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from core.metadata_manager import MetadataManager
from core.workflow_state import WorkflowState
from core.claude_agent_client import ClaudeAgentClient
from core.github_client import GitHubClient
from phases.requirements import RequirementsPhase


class TestRetryMechanism:
    """リトライメカニズムの統合テスト"""

    @pytest.fixture
    def setup_integration(self, tmp_path):
        """統合テスト環境のセットアップ"""
        # metadata.jsonを作成
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='999',
            issue_url='https://github.com/test/test/issues/999',
            issue_title='Test Issue #999'
        )

        # working_dirを作成
        working_dir = tmp_path / 'working'
        working_dir.mkdir()

        # プロンプトディレクトリを作成
        prompts_dir = working_dir / 'prompts' / 'requirements'
        prompts_dir.mkdir(parents=True)

        # プロンプトファイルを作成
        (prompts_dir / 'execute.txt').write_text('Test execute prompt', encoding='utf-8')
        (prompts_dir / 'review.txt').write_text('Test review prompt', encoding='utf-8')
        (prompts_dir / 'revise.txt').write_text('Test revise prompt', encoding='utf-8')

        # メタデータマネージャー
        metadata_manager = MetadataManager(metadata_path)

        # モッククライアント
        claude_client = Mock(spec=ClaudeAgentClient)
        github_client = Mock(spec=GitHubClient)

        return {
            'tmp_path': tmp_path,
            'working_dir': working_dir,
            'metadata_manager': metadata_manager,
            'claude_client': claude_client,
            'github_client': github_client
        }

    def test_retry_mechanism_with_mocked_phase(self, setup_integration):
        """
        IT-001: モック化したPhaseでのexecute()失敗→revise()成功フロー

        検証項目:
        - execute()が失敗した場合、revise()によるリトライが実行される
        - 最終的に成功する
        - メタデータのretry_countが正しく更新される
        - GitHub Issueにレビュー結果が投稿される
        """
        # Arrange
        setup = setup_integration
        phase = RequirementsPhase(
            working_dir=setup['working_dir'],
            metadata_manager=setup['metadata_manager'],
            claude_client=setup['claude_client'],
            github_client=setup['github_client']
        )

        # execute()が失敗を返すようにモック化
        phase.execute = Mock(return_value={'success': False, 'error': 'Initial error'})

        # review()は1回目FAIL、2回目PASS
        review_results = [
            {'result': 'FAIL', 'feedback': 'Test feedback', 'suggestions': []},
            {'result': 'PASS', 'feedback': '', 'suggestions': []}
        ]
        phase.review = Mock(side_effect=review_results)

        # revise()は成功を返す
        phase.revise = Mock(return_value={'success': True, 'output': 'revised_output'})

        # Act
        success = phase.run()

        # Assert
        assert success is True
        assert phase.execute.call_count == 1
        assert phase.review.call_count == 2
        assert phase.revise.call_count == 1

        # メタデータのretry_countが1になる
        retry_count = setup['metadata_manager'].data['phases']['requirements'].get('retry_count', 0)
        assert retry_count == 1

        # GitHub Issueにレビュー結果が投稿された
        assert setup['github_client'].post_review_result.call_count == 2

    def test_retry_mechanism_max_retries_reached(self, setup_integration):
        """
        IT-002: 最大リトライ到達時の動作確認

        検証項目:
        - execute()失敗後、最大リトライ回数（3回）に到達する
        - 失敗終了する
        - メタデータのphase statusが'failed'になる
        - メタデータのretry_countが2になる（revise()が2回実行）
        - GitHub Issueに「最大リトライ回数(3)に到達しました」が投稿される
        """
        # Arrange
        setup = setup_integration
        phase = RequirementsPhase(
            working_dir=setup['working_dir'],
            metadata_manager=setup['metadata_manager'],
            claude_client=setup['claude_client'],
            github_client=setup['github_client']
        )

        # execute()が失敗を返す
        phase.execute = Mock(return_value={'success': False, 'error': 'Test error'})

        # review()が常にFAILを返す
        phase.review = Mock(return_value={
            'result': 'FAIL',
            'feedback': 'Test feedback',
            'suggestions': []
        })

        # revise()が常に失敗を返す
        phase.revise = Mock(return_value={'success': False, 'error': 'Revise failed'})

        # Act
        success = phase.run()

        # Assert
        assert success is False
        assert phase.execute.call_count == 1
        assert phase.review.call_count == 2
        assert phase.revise.call_count == 2

        # メタデータのphase statusが'failed'
        assert setup['metadata_manager'].get_phase_status('requirements') == 'failed'

        # メタデータのretry_countが2（revise()が2回実行）
        retry_count = setup['metadata_manager'].data['phases']['requirements'].get('retry_count', 0)
        assert retry_count == 2

        # GitHub投稿で「最大リトライ回数(3)に到達しました」が呼ばれた
        calls = [str(call) for call in setup['github_client'].post_workflow_progress.call_args_list]
        assert any('最大リトライ回数(3)に到達しました' in call for call in calls)

    def test_retry_mechanism_successful_execution(self, setup_integration):
        """
        IT-003: execute()成功→review()合格の正常フロー

        検証項目:
        - execute()が成功し、review()が合格する
        - revise()は実行されない
        - メタデータのphase statusが'completed'になる
        - メタデータのreview_resultが'PASS'になる
        - メタデータのretry_countが0のまま
        """
        # Arrange
        setup = setup_integration
        phase = RequirementsPhase(
            working_dir=setup['working_dir'],
            metadata_manager=setup['metadata_manager'],
            claude_client=setup['claude_client'],
            github_client=setup['github_client']
        )

        # execute()が成功を返す
        phase.execute = Mock(return_value={'success': True, 'output': 'test_output'})

        # review()がPASSを返す
        phase.review = Mock(return_value={
            'result': 'PASS',
            'feedback': '',
            'suggestions': []
        })

        # revise()は呼ばれないはず
        phase.revise = Mock(return_value={'success': True, 'output': 'revised_output'})

        # Act
        success = phase.run()

        # Assert
        assert success is True
        assert phase.execute.call_count == 1
        assert phase.revise.call_count == 0  # revise()は実行されない

        # メタデータのphase statusが'completed'
        assert setup['metadata_manager'].get_phase_status('requirements') == 'completed'

        # メタデータのreview_resultが'PASS'
        phase_data = setup['metadata_manager'].data['phases']['requirements']
        assert phase_data.get('review_result') == 'PASS'

        # メタデータのretry_countが0
        retry_count = phase_data.get('retry_count', 0)
        assert retry_count == 0

    def test_retry_mechanism_metadata_update(self, setup_integration):
        """
        IT-004: リトライ回数のメタデータへの記録

        検証項目:
        - リトライ実行時にメタデータのretry_countが正しく更新される
        - 初期状態: retry_count=0
        - 1回目のrevise()実行前: retry_count=1にインクリメント
        - 最終的なretry_count=1
        """
        # Arrange
        setup = setup_integration
        phase = RequirementsPhase(
            working_dir=setup['working_dir'],
            metadata_manager=setup['metadata_manager'],
            claude_client=setup['claude_client'],
            github_client=setup['github_client']
        )

        # 初期状態のretry_countを確認
        initial_retry_count = setup['metadata_manager'].data['phases']['requirements'].get('retry_count', 0)
        assert initial_retry_count == 0

        # execute()が失敗を返す
        phase.execute = Mock(return_value={'success': False, 'error': 'Test error'})

        # review()は1回目FAIL、2回目PASS
        review_results = [
            {'result': 'FAIL', 'feedback': 'Test feedback', 'suggestions': []},
            {'result': 'PASS', 'feedback': '', 'suggestions': []}
        ]
        phase.review = Mock(side_effect=review_results)

        # revise()は成功を返す
        phase.revise = Mock(return_value={'success': True, 'output': 'revised_output'})

        # Act
        success = phase.run()

        # Assert
        assert success is True

        # 最終的なretry_countが1
        final_retry_count = setup['metadata_manager'].data['phases']['requirements'].get('retry_count', 0)
        assert final_retry_count == 1

    def test_retry_mechanism_github_integration(self, setup_integration):
        """
        IT-007: GitHub Issue投稿の統合テスト（成功ケース）

        検証項目:
        - フェーズ開始時に進捗投稿される
        - レビュー結果が投稿される
        - フェーズ完了時に完了投稿される
        """
        # Arrange
        setup = setup_integration
        phase = RequirementsPhase(
            working_dir=setup['working_dir'],
            metadata_manager=setup['metadata_manager'],
            claude_client=setup['claude_client'],
            github_client=setup['github_client']
        )

        # execute()が成功を返す
        phase.execute = Mock(return_value={'success': True, 'output': 'test_output'})

        # review()がPASSを返す
        phase.review = Mock(return_value={
            'result': 'PASS',
            'feedback': '',
            'suggestions': []
        })

        # Act
        success = phase.run()

        # Assert
        assert success is True

        # GitHub投稿の確認
        github_client = setup['github_client']

        # post_workflow_progressが呼ばれた（開始、完了）
        assert github_client.post_workflow_progress.call_count >= 2

        # post_review_resultが呼ばれた
        assert github_client.post_review_result.call_count >= 1

    def test_retry_mechanism_github_integration_with_retry(self, setup_integration):
        """
        IT-008: GitHub Issue投稿の統合テスト（リトライケース）

        検証項目:
        - フェーズ開始時に進捗投稿される
        - 1回目のレビュー結果が投稿される（FAIL）
        - revise()実行前に進捗投稿される
        - 最終レビュー結果が投稿される（PASS）
        - フェーズ完了時に完了投稿される
        """
        # Arrange
        setup = setup_integration
        phase = RequirementsPhase(
            working_dir=setup['working_dir'],
            metadata_manager=setup['metadata_manager'],
            claude_client=setup['claude_client'],
            github_client=setup['github_client']
        )

        # execute()が失敗を返す
        phase.execute = Mock(return_value={'success': False, 'error': 'Initial error'})

        # review()は1回目FAIL、2回目PASS
        review_results = [
            {'result': 'FAIL', 'feedback': 'Test feedback', 'suggestions': ['Suggestion 1']},
            {'result': 'PASS', 'feedback': '', 'suggestions': []}
        ]
        phase.review = Mock(side_effect=review_results)

        # revise()は成功を返す
        phase.revise = Mock(return_value={'success': True, 'output': 'revised_output'})

        # Act
        success = phase.run()

        # Assert
        assert success is True

        # GitHub投稿の確認
        github_client = setup['github_client']

        # post_workflow_progressが複数回呼ばれた（開始、revise実行前、完了）
        assert github_client.post_workflow_progress.call_count >= 3

        # post_review_resultが2回呼ばれた（FAIL、PASS）
        assert github_client.post_review_result.call_count == 2


# 注意: 実際のClaude Agent SDK、GitHub API、Gitリポジトリとの統合テストは、
# 環境構築とコスト（API呼び出し）の観点から、手動テストまたはE2Eテストで実施することを推奨します。
# 本ファイルのテストは、モックを使用した統合テストです。
