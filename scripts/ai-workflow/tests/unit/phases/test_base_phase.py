"""BasePhaseのUnitテスト"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from core.metadata_manager import MetadataManager
from core.workflow_state import WorkflowState
from core.claude_agent_client import ClaudeAgentClient
from core.github_client import GitHubClient
from phases.base_phase import BasePhase


class ConcretePhase(BasePhase):
    """テスト用の具象Phaseクラス"""

    def __init__(self, *args, **kwargs):
        super().__init__(phase_name='requirements', *args, **kwargs)

    def execute(self):
        return {'success': True, 'output': 'Test output'}

    def review(self):
        return {
            'result': 'PASS',
            'feedback': 'Test feedback',
            'suggestions': []
        }


class TestBasePhase:
    """BasePhaseクラスのUnitテスト"""

    @pytest.fixture
    def setup_phase(self, tmp_path):
        """フェーズのセットアップ（モック使用）"""
        # metadata.jsonを作成
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='304',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/304',
            issue_title='Test Issue #304'
        )

        # working_dirを作成
        working_dir = tmp_path / 'working'
        working_dir.mkdir()

        # プロンプトディレクトリを作成
        prompts_dir = working_dir / 'prompts' / 'requirements'
        prompts_dir.mkdir(parents=True)

        # execute.txtプロンプトを作成
        execute_prompt = prompts_dir / 'execute.txt'
        execute_prompt.write_text('Test execute prompt', encoding='utf-8')

        # review.txtプロンプトを作成
        review_prompt = prompts_dir / 'review.txt'
        review_prompt.write_text('Test review prompt', encoding='utf-8')

        # メタデータマネージャー
        metadata_manager = MetadataManager(metadata_path)

        # モッククライアント
        claude_client = Mock(spec=ClaudeAgentClient)
        github_client = Mock(spec=GitHubClient)

        # フェーズインスタンス
        phase = ConcretePhase(
            working_dir=working_dir,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

        return {
            'phase': phase,
            'metadata_manager': metadata_manager,
            'claude_client': claude_client,
            'github_client': github_client,
            'prompts_dir': prompts_dir
        }

    def test_init(self, setup_phase):
        """
        初期化のテスト

        検証項目:
        - フェーズディレクトリが正しく作成されるか
        - サブディレクトリ（output, execute, review, revise）が作成されるか
        """
        # Arrange & Act
        phase = setup_phase['phase']

        # Assert
        assert phase.phase_name == 'requirements'
        assert phase.phase_dir.exists()
        assert phase.output_dir.exists()
        assert phase.execute_dir.exists()
        assert phase.review_dir.exists()
        assert phase.revise_dir.exists()

        # フェーズディレクトリ名が正しいか
        assert phase.phase_dir.name == '01_requirements'

    def test_load_prompt_success(self, setup_phase):
        """
        プロンプト読み込み成功のテスト

        検証項目:
        - 正しいプロンプトファイルを読み込めるか
        """
        # Arrange
        phase = setup_phase['phase']

        # Act
        execute_prompt = phase.load_prompt('execute')
        review_prompt = phase.load_prompt('review')

        # Assert
        assert execute_prompt == 'Test execute prompt'
        assert review_prompt == 'Test review prompt'

    def test_load_prompt_file_not_found(self, setup_phase):
        """
        プロンプトファイルが存在しない場合のエラーテスト

        検証項目:
        - FileNotFoundErrorが発生するか
        """
        # Arrange
        phase = setup_phase['phase']

        # Act & Assert
        with pytest.raises(FileNotFoundError, match='Prompt file not found'):
            phase.load_prompt('non_existent')

    def test_update_phase_status(self, setup_phase):
        """
        フェーズステータス更新のテスト

        検証項目:
        - update_phase_status()が正しく動作するか
        """
        # Arrange
        phase = setup_phase['phase']
        metadata_manager = setup_phase['metadata_manager']

        # Act
        phase.update_phase_status(status='in_progress')

        # Assert
        assert metadata_manager.get_phase_status('requirements') == 'in_progress'

    def test_update_phase_status_with_cost(self, setup_phase):
        """
        フェーズステータス更新（コストトラッキング付き）のテスト

        検証項目:
        - コストトラッキングが正しく記録されるか
        """
        # Arrange
        phase = setup_phase['phase']
        metadata_manager = setup_phase['metadata_manager']

        # Act
        phase.update_phase_status(
            status='completed',
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.05
        )

        # Assert
        assert metadata_manager.data['cost_tracking']['total_input_tokens'] == 1000
        assert metadata_manager.data['cost_tracking']['total_output_tokens'] == 500
        assert metadata_manager.data['cost_tracking']['total_cost_usd'] == 0.05

    def test_post_progress(self, setup_phase):
        """
        GitHub進捗報告のテスト

        検証項目:
        - GitHubClientのpost_workflow_progress()が呼び出されるか
        """
        # Arrange
        phase = setup_phase['phase']
        github_client = setup_phase['github_client']

        # Act
        phase.post_progress(status='in_progress', details='Test details')

        # Assert
        github_client.post_workflow_progress.assert_called_once_with(
            issue_number=304,
            phase='requirements',
            status='in_progress',
            details='Test details'
        )

    def test_post_review(self, setup_phase):
        """
        GitHubレビュー結果投稿のテスト

        検証項目:
        - GitHubClientのpost_review_result()が呼び出されるか
        """
        # Arrange
        phase = setup_phase['phase']
        github_client = setup_phase['github_client']

        # Act
        phase.post_review(
            result='PASS',
            feedback='Test feedback',
            suggestions=['suggestion1', 'suggestion2']
        )

        # Assert
        github_client.post_review_result.assert_called_once_with(
            issue_number=304,
            phase='requirements',
            result='PASS',
            feedback='Test feedback',
            suggestions=['suggestion1', 'suggestion2']
        )

    def test_execute_with_claude(self, setup_phase):
        """
        Claude Agent SDK実行のテスト（モック使用）

        検証項目:
        - ClaudeAgentClient.execute_task_sync()が呼び出されるか
        - ログファイルが保存されるか
        """
        # Arrange
        phase = setup_phase['phase']
        claude_client = setup_phase['claude_client']

        # モックの返り値を設定
        claude_client.execute_task_sync.return_value = ['Message 1', 'Message 2']

        # Act
        messages = phase.execute_with_claude(
            prompt='Test prompt',
            system_prompt='Test system prompt',
            max_turns=10,
            verbose=False,
            save_logs=True,
            log_prefix='execute'
        )

        # Assert
        claude_client.execute_task_sync.assert_called_once_with(
            prompt='Test prompt',
            system_prompt='Test system prompt',
            max_turns=10,
            verbose=False
        )
        assert messages == ['Message 1', 'Message 2']

        # ログファイルが保存されているか確認
        prompt_file = phase.execute_dir / 'prompt.txt'
        agent_log_file = phase.execute_dir / 'agent_log.md'
        raw_log_file = phase.execute_dir / 'agent_log_raw.txt'

        assert prompt_file.exists()
        assert agent_log_file.exists()
        assert raw_log_file.exists()

    def test_run_success(self, setup_phase):
        """
        run()メソッド成功のテスト

        検証項目:
        - execute() → review() の流れが正しく動作するか
        - レビュー結果がPASSの場合、ステータスがcompletedになるか
        """
        # Arrange
        phase = setup_phase['phase']
        metadata_manager = setup_phase['metadata_manager']
        github_client = setup_phase['github_client']

        # Act
        success = phase.run()

        # Assert
        assert success is True
        assert metadata_manager.get_phase_status('requirements') == 'completed'

        # GitHub投稿が呼び出されたか確認
        assert github_client.post_workflow_progress.call_count >= 2  # in_progress, completed
        assert github_client.post_review_result.call_count == 1

    def test_run_execute_failure(self, setup_phase):
        """
        run()メソッド（execute失敗）のテスト

        検証項目:
        - execute()が失敗した場合、ステータスがfailedになるか
        """
        # Arrange
        phase = setup_phase['phase']
        metadata_manager = setup_phase['metadata_manager']

        # execute()が失敗するように上書き
        phase.execute = Mock(return_value={'success': False, 'error': 'Test error'})

        # Act
        success = phase.run()

        # Assert
        assert success is False
        assert metadata_manager.get_phase_status('requirements') == 'failed'

    def test_run_review_fail_with_revise(self, setup_phase):
        """
        run()メソッド（レビュー失敗 + revise成功）のテスト

        検証項目:
        - レビュー結果がFAILの場合、revise()が呼び出されるか
        - revise後の再レビューでPASSになった場合、ステータスがcompletedになるか
        """
        # Arrange
        phase = setup_phase['phase']
        metadata_manager = setup_phase['metadata_manager']

        # 最初のreview()はFAIL、2回目はPASSを返すように設定
        review_results = [
            {'result': 'FAIL', 'feedback': 'Test failure', 'suggestions': []},
            {'result': 'PASS', 'feedback': 'Test success', 'suggestions': []}
        ]
        phase.review = Mock(side_effect=review_results)

        # revise()メソッドを追加（成功を返す）
        phase.revise = Mock(return_value={'success': True})

        # Act
        success = phase.run()

        # Assert
        assert success is True
        assert metadata_manager.get_phase_status('requirements') == 'completed'
        phase.revise.assert_called_once()

    def test_run_review_fail_max_retries(self, setup_phase):
        """
        run()メソッド（リトライ上限）のテスト

        検証項目:
        - リトライが3回失敗した場合、ステータスがfailedになるか
        """
        # Arrange
        phase = setup_phase['phase']
        metadata_manager = setup_phase['metadata_manager']

        # review()が常にFAILを返すように設定
        phase.review = Mock(return_value={
            'result': 'FAIL',
            'feedback': 'Test failure',
            'suggestions': []
        })

        # revise()メソッドを追加（成功を返す）
        phase.revise = Mock(return_value={'success': True})

        # Act
        success = phase.run()

        # Assert
        assert success is False
        assert metadata_manager.get_phase_status('requirements') == 'failed'
        # revise()が3回呼び出されたことを確認
        assert phase.revise.call_count == 3

    def test_run_revise_failure(self, setup_phase):
        """
        run()メソッド（revise失敗）のテスト

        検証項目:
        - revise()が失敗した場合、ステータスがfailedになるか
        """
        # Arrange
        phase = setup_phase['phase']
        metadata_manager = setup_phase['metadata_manager']

        # review()がFAILを返すように設定
        phase.review = Mock(return_value={
            'result': 'FAIL',
            'feedback': 'Test failure',
            'suggestions': []
        })

        # revise()が失敗を返すように設定
        phase.revise = Mock(return_value={'success': False, 'error': 'Revise error'})

        # Act
        success = phase.run()

        # Assert
        assert success is False
        assert metadata_manager.get_phase_status('requirements') == 'failed'
        phase.revise.assert_called_once()
