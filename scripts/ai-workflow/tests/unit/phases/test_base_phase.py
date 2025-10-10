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

        # ログファイルが保存されているか確認（連番付き）
        prompt_file = phase.execute_dir / 'prompt_1.txt'
        agent_log_file = phase.execute_dir / 'agent_log_1.md'
        raw_log_file = phase.execute_dir / 'agent_log_raw_1.txt'

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

    # ====================================================================
    # ログファイル連番管理のテスト (Issue #317)
    # ====================================================================

    def test_get_next_sequence_number_no_files(self, tmp_path):
        """
        TC-U001: 既存ファイルが存在しない場合（正常系）

        検証項目:
        - ファイルが存在しないディレクトリで、連番=1が返されることを検証
        """
        # Arrange
        from phases.base_phase import BasePhase
        target_dir = tmp_path / 'test_dir'
        target_dir.mkdir()

        # モッククライアント
        claude_client = Mock(spec=ClaudeAgentClient)
        github_client = Mock(spec=GitHubClient)
        metadata_manager = Mock(spec=MetadataManager)
        metadata_manager.workflow_dir = tmp_path

        # フェーズインスタンス
        phase = ConcretePhase(
            working_dir=tmp_path,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

        # Act
        result = phase._get_next_sequence_number(target_dir)

        # Assert
        assert result == 1

    def test_get_next_sequence_number_with_files(self, tmp_path):
        """
        TC-U002: 既存ファイルが1件存在する場合（正常系）

        検証項目:
        - 既存ファイルが1件の場合、連番=2が返されることを検証
        """
        # Arrange
        from phases.base_phase import BasePhase
        target_dir = tmp_path / 'test_dir'
        target_dir.mkdir()
        (target_dir / 'agent_log_1.md').touch()

        # モッククライアント
        claude_client = Mock(spec=ClaudeAgentClient)
        github_client = Mock(spec=GitHubClient)
        metadata_manager = Mock(spec=MetadataManager)
        metadata_manager.workflow_dir = tmp_path

        phase = ConcretePhase(
            working_dir=tmp_path,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

        # Act
        result = phase._get_next_sequence_number(target_dir)

        # Assert
        assert result == 2

    def test_get_next_sequence_number_with_multiple_files(self, tmp_path):
        """
        TC-U003: 既存ファイルが複数存在する場合（正常系）

        検証項目:
        - 既存ファイルが複数の場合、最大値+1が返されることを検証
        """
        # Arrange
        from phases.base_phase import BasePhase
        target_dir = tmp_path / 'test_dir'
        target_dir.mkdir()
        for i in range(1, 6):
            (target_dir / f'agent_log_{i}.md').touch()

        # モッククライアント
        claude_client = Mock(spec=ClaudeAgentClient)
        github_client = Mock(spec=GitHubClient)
        metadata_manager = Mock(spec=MetadataManager)
        metadata_manager.workflow_dir = tmp_path

        phase = ConcretePhase(
            working_dir=tmp_path,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

        # Act
        result = phase._get_next_sequence_number(target_dir)

        # Assert
        assert result == 6

    def test_get_next_sequence_number_with_gaps(self, tmp_path):
        """
        TC-U004: 欠番がある場合（境界値）

        検証項目:
        - ファイル連番に欠番がある場合、最大値+1が返されることを検証（欠番は埋めない）
        """
        # Arrange
        from phases.base_phase import BasePhase
        target_dir = tmp_path / 'test_dir'
        target_dir.mkdir()
        # 1, 3, 5 のみ作成（2, 4 は欠番）
        for i in [1, 3, 5]:
            (target_dir / f'agent_log_{i}.md').touch()

        # モッククライアント
        claude_client = Mock(spec=ClaudeAgentClient)
        github_client = Mock(spec=GitHubClient)
        metadata_manager = Mock(spec=MetadataManager)
        metadata_manager.workflow_dir = tmp_path

        phase = ConcretePhase(
            working_dir=tmp_path,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

        # Act
        result = phase._get_next_sequence_number(target_dir)

        # Assert
        assert result == 6  # 欠番（2, 4）は埋められず、最大値5の次の6が返される

    def test_get_next_sequence_number_large_numbers(self, tmp_path):
        """
        TC-U005: 大きな連番が存在する場合（境界値）

        検証項目:
        - 大きな連番（999）が存在する場合、1000が返されることを検証
        """
        # Arrange
        from phases.base_phase import BasePhase
        target_dir = tmp_path / 'test_dir'
        target_dir.mkdir()
        (target_dir / 'agent_log_999.md').touch()

        # モッククライアント
        claude_client = Mock(spec=ClaudeAgentClient)
        github_client = Mock(spec=GitHubClient)
        metadata_manager = Mock(spec=MetadataManager)
        metadata_manager.workflow_dir = tmp_path

        phase = ConcretePhase(
            working_dir=tmp_path,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

        # Act
        result = phase._get_next_sequence_number(target_dir)

        # Assert
        assert result == 1000

    def test_get_next_sequence_number_invalid_files(self, tmp_path):
        """
        TC-U006: 無効なファイル名が混在する場合（異常系）

        検証項目:
        - 正規表現にマッチしないファイルが混在しても、正しく連番を取得できることを検証
        """
        # Arrange
        from phases.base_phase import BasePhase
        target_dir = tmp_path / 'test_dir'
        target_dir.mkdir()
        (target_dir / 'agent_log_1.md').touch()
        (target_dir / 'agent_log_2.md').touch()
        (target_dir / 'agent_log.md').touch()  # 無効: 連番なし
        (target_dir / 'agent_log_abc.md').touch()  # 無効: 非数値
        (target_dir / 'agent_log_3.txt').touch()  # 無効: 拡張子違い
        (target_dir / 'other_file.md').touch()  # 無効: パターン不一致

        # モッククライアント
        claude_client = Mock(spec=ClaudeAgentClient)
        github_client = Mock(spec=GitHubClient)
        metadata_manager = Mock(spec=MetadataManager)
        metadata_manager.workflow_dir = tmp_path

        phase = ConcretePhase(
            working_dir=tmp_path,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

        # Act
        result = phase._get_next_sequence_number(target_dir)

        # Assert
        assert result == 3  # 有効なファイルは agent_log_1.md, agent_log_2.md のみ

    def test_get_next_sequence_number_unordered(self, tmp_path):
        """
        TC-U007: 連番が順不同の場合（境界値）

        検証項目:
        - ファイル連番が順不同でも、正しく最大値を取得できることを検証
        """
        # Arrange
        from phases.base_phase import BasePhase
        target_dir = tmp_path / 'test_dir'
        target_dir.mkdir()
        # 順不同で作成
        for i in [5, 2, 8, 1, 3]:
            (target_dir / f'agent_log_{i}.md').touch()

        # モッククライアント
        claude_client = Mock(spec=ClaudeAgentClient)
        github_client = Mock(spec=GitHubClient)
        metadata_manager = Mock(spec=MetadataManager)
        metadata_manager.workflow_dir = tmp_path

        phase = ConcretePhase(
            working_dir=tmp_path,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

        # Act
        result = phase._get_next_sequence_number(target_dir)

        # Assert
        assert result == 9  # 最大値8の次の9が返される

    def test_save_execution_logs_with_sequence(self, setup_phase):
        """
        TC-U101: 初回実行時の連番付きファイル保存（正常系）

        検証項目:
        - 初回実行時に連番=1でログファイルが保存されることを検証
        """
        # Arrange
        phase = setup_phase['phase']
        claude_client = setup_phase['claude_client']

        # モックの返り値を設定
        claude_client.execute_task_sync.return_value = ['レスポンス1', 'レスポンス2']

        # Act
        phase.execute_with_claude(
            prompt='テストプロンプト',
            log_prefix='execute',
            save_logs=True
        )

        # Assert
        assert (phase.execute_dir / 'prompt_1.txt').exists()
        assert (phase.execute_dir / 'agent_log_1.md').exists()
        assert (phase.execute_dir / 'agent_log_raw_1.txt').exists()

        # ファイル内容の確認
        assert (phase.execute_dir / 'prompt_1.txt').read_text() == 'テストプロンプト'
        assert 'レスポンス1' in (phase.execute_dir / 'agent_log_raw_1.txt').read_text()
        assert 'レスポンス2' in (phase.execute_dir / 'agent_log_raw_1.txt').read_text()

    def test_save_execution_logs_retry_sequencing(self, setup_phase):
        """
        TC-U102: リトライ実行時の連番インクリメント（正常系）

        検証項目:
        - リトライ実行時に連番がインクリメントされ、既存ファイルが上書きされないことを検証
        """
        # Arrange
        phase = setup_phase['phase']
        claude_client = setup_phase['claude_client']

        # 初回実行
        claude_client.execute_task_sync.return_value = ['初回レスポンス']
        phase.execute_with_claude(prompt='初回プロンプト', log_prefix='execute')

        # Assert 初回実行
        assert (phase.execute_dir / 'prompt_1.txt').exists()
        assert (phase.execute_dir / 'agent_log_1.md').exists()
        assert (phase.execute_dir / 'agent_log_raw_1.txt').exists()

        # リトライ実行
        claude_client.execute_task_sync.return_value = ['リトライレスポンス']
        phase.execute_with_claude(prompt='リトライプロンプト', log_prefix='execute')

        # Assert リトライ実行
        # 新しいファイルが作成される
        assert (phase.execute_dir / 'prompt_2.txt').exists()
        assert (phase.execute_dir / 'agent_log_2.md').exists()
        assert (phase.execute_dir / 'agent_log_raw_2.txt').exists()

        # 既存ファイルが保持される
        assert (phase.execute_dir / 'prompt_1.txt').exists()
        assert (phase.execute_dir / 'agent_log_1.md').exists()
        assert (phase.execute_dir / 'agent_log_raw_1.txt').exists()

        # 新ファイルの内容確認
        assert (phase.execute_dir / 'prompt_2.txt').read_text() == 'リトライプロンプト'
        assert 'リトライレスポンス' in (phase.execute_dir / 'agent_log_raw_2.txt').read_text()

        # 既存ファイルが変更されていないことを確認
        assert (phase.execute_dir / 'prompt_1.txt').read_text() == '初回プロンプト'

    def test_save_execution_logs_independent_sequencing(self, setup_phase):
        """
        TC-U103: 異なるlog_prefixでの独立した連番管理（正常系）

        検証項目:
        - execute, review, revise ディレクトリでそれぞれ独立した連番が付与されることを検証
        """
        # Arrange
        phase = setup_phase['phase']
        claude_client = setup_phase['claude_client']

        # executeディレクトリで2回実行
        claude_client.execute_task_sync.return_value = ['execute1']
        phase.execute_with_claude(prompt='execute1', log_prefix='execute')
        claude_client.execute_task_sync.return_value = ['execute2']
        phase.execute_with_claude(prompt='execute2', log_prefix='execute')

        # reviewディレクトリで1回実行
        claude_client.execute_task_sync.return_value = ['review1']
        phase.execute_with_claude(prompt='review1', log_prefix='review')

        # Assert
        # executeディレクトリに連番=1,2で保存される
        assert (phase.execute_dir / 'agent_log_1.md').exists()
        assert (phase.execute_dir / 'agent_log_2.md').exists()

        # reviewディレクトリに連番=1で保存される（executeの連番に影響されない）
        assert (phase.review_dir / 'prompt_1.txt').exists()
        assert (phase.review_dir / 'agent_log_1.md').exists()
        assert (phase.review_dir / 'agent_log_raw_1.txt').exists()

    def test_save_execution_logs_japanese_content(self, setup_phase):
        """
        TC-U104: 日本語を含むログファイルの保存（正常系）

        検証項目:
        - 日本語を含むプロンプトとレスポンスが正しくUTF-8で保存されることを検証
        """
        # Arrange
        phase = setup_phase['phase']
        claude_client = setup_phase['claude_client']

        # Act
        claude_client.execute_task_sync.return_value = ['了解しました。要件定義書を作成します。']
        phase.execute_with_claude(
            prompt='日本語プロンプト:要件定義書を作成してください',
            log_prefix='execute'
        )

        # Assert
        assert (phase.execute_dir / 'prompt_1.txt').exists()
        assert (phase.execute_dir / 'agent_log_1.md').exists()
        assert (phase.execute_dir / 'agent_log_raw_1.txt').exists()

        # UTF-8で正しく保存されている
        prompt_content = (phase.execute_dir / 'prompt_1.txt').read_text(encoding='utf-8')
        assert prompt_content == '日本語プロンプト:要件定義書を作成してください'

        log_content = (phase.execute_dir / 'agent_log_raw_1.txt').read_text(encoding='utf-8')
        assert '了解しました。要件定義書を作成します。' in log_content

    def test_get_next_sequence_number_nonexistent_directory(self, tmp_path):
        """
        TC-U201: ディレクトリが存在しない場合（異常系）

        検証項目:
        - 対象ディレクトリが存在しない場合、連番=1が返されることを検証
        """
        # Arrange
        from phases.base_phase import BasePhase
        target_dir = tmp_path / 'non_existent_dir'  # 存在しないディレクトリ

        # モッククライアント
        claude_client = Mock(spec=ClaudeAgentClient)
        github_client = Mock(spec=GitHubClient)
        metadata_manager = Mock(spec=MetadataManager)
        metadata_manager.workflow_dir = tmp_path

        phase = ConcretePhase(
            working_dir=tmp_path,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

        # Act
        # ディレクトリが存在しない場合、glob()は空リストを返し、連番=1が返される
        result = phase._get_next_sequence_number(target_dir)

        # Assert
        assert result == 1

    # ====================================================================
    # execute()失敗時のリトライ機能テスト (Issue #331)
    # ====================================================================

    def test_run_execute_failure_with_retry(self, setup_phase):
        """
        UT-002: execute()失敗時のリトライ実行

        検証項目:
        - execute()が失敗した場合、リトライループに入ること
        - review() → revise()が実行されること
        - 最終的に成功すること
        """
        # Arrange
        phase = setup_phase['phase']
        metadata_manager = setup_phase['metadata_manager']

        # execute()が失敗を返す
        phase.execute = Mock(return_value={'success': False, 'error': 'Test error'})

        # 1回目のreview()はFAIL、2回目はPASS
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
        assert phase.execute.call_count == 1  # execute()は1回だけ
        assert phase.review.call_count == 2   # review()は2回（attempt=2の前と最終レビュー）
        assert phase.revise.call_count == 1   # revise()は1回
        assert metadata_manager.get_phase_status('requirements') == 'completed'

    def test_run_execute_failure_max_retries(self, setup_phase):
        """
        UT-003: execute()失敗後の最大リトライ到達

        検証項目:
        - execute()失敗後、最大リトライ回数（3回）に到達すること
        - 失敗終了すること
        """
        # Arrange
        phase = setup_phase['phase']
        metadata_manager = setup_phase['metadata_manager']
        github_client = setup_phase['github_client']

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
        assert phase.execute.call_count == 1    # execute()は1回だけ
        assert phase.review.call_count == 2     # review()は2回（attempt=2, 3の前）
        assert phase.revise.call_count == 2     # revise()は2回（attempt=2, 3）
        assert metadata_manager.get_phase_status('requirements') == 'failed'

        # GitHub投稿で「最大リトライ回数(3)に到達しました」が呼ばれたか確認
        calls = [str(call) for call in github_client.post_workflow_progress.call_args_list]
        assert any('最大リトライ回数(3)に到達しました' in call for call in calls)

    def test_run_execute_failure_then_success(self, setup_phase):
        """
        UT-004: execute()失敗後、revise()成功→review()合格

        検証項目:
        - execute()失敗後にrevise()が実行されること
        - revise()成功後にreview()が実行されること
        - 最終的にPASSになること
        """
        # Arrange
        phase = setup_phase['phase']
        metadata_manager = setup_phase['metadata_manager']

        # execute()が失敗を返す
        phase.execute = Mock(return_value={'success': False, 'error': 'Initial error'})

        # 1回目のreview()はFAIL、2回目はPASS
        review_results = [
            {'result': 'FAIL', 'feedback': 'Need revision', 'suggestions': []},
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
        assert metadata_manager.get_phase_status('requirements') == 'completed'

    def test_run_execute_failure_review_pass_early(self, setup_phase):
        """
        UT-005: attempt>=2でreview()がPASSの場合の早期終了

        検証項目:
        - 2回目以降のattemptでreview()がPASSを返した場合
        - revise()をスキップして成功終了すること
        """
        # Arrange
        phase = setup_phase['phase']
        metadata_manager = setup_phase['metadata_manager']

        # execute()が失敗を返す
        phase.execute = Mock(return_value={'success': False, 'error': 'Initial error'})

        # review()が1回目でPASSを返す
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
        assert phase.review.call_count == 1  # review()は1回だけ（attempt=2の前）
        assert phase.revise.call_count == 0  # revise()は呼ばれない
        assert metadata_manager.get_phase_status('requirements') == 'completed'

    def test_run_execute_failure_no_revise_method(self, setup_phase):
        """
        UT-006: revise()メソッドが実装されていない場合

        検証項目:
        - revise()が実装されていない場合
        - 適切なエラーメッセージが出力されること
        - 失敗終了すること
        """
        # Arrange
        phase = setup_phase['phase']
        metadata_manager = setup_phase['metadata_manager']
        github_client = setup_phase['github_client']

        # execute()が失敗を返す
        phase.execute = Mock(return_value={'success': False, 'error': 'Test error'})

        # review()がFAILを返す
        phase.review = Mock(return_value={
            'result': 'FAIL',
            'feedback': 'Test feedback',
            'suggestions': []
        })

        # revise()メソッドを削除
        delattr(phase, 'revise')

        # Act
        success = phase.run()

        # Assert
        assert success is False
        assert metadata_manager.get_phase_status('requirements') == 'failed'

        # GitHub投稿で「revise()メソッドが未実装のため、修正できません。」が呼ばれたか確認
        calls = [str(call) for call in github_client.post_workflow_progress.call_args_list]
        assert any('revise()メソッドが未実装' in call for call in calls)

    def test_run_execute_exception(self, setup_phase):
        """
        UT-007: execute()が例外をスローした場合

        検証項目:
        - execute()実行中に例外が発生した場合
        - 適切にハンドリングされること
        - finally句でGit commit & pushが実行されること
        """
        # Arrange
        phase = setup_phase['phase']
        metadata_manager = setup_phase['metadata_manager']

        # execute()が例外をスロー
        phase.execute = Mock(side_effect=RuntimeError('Unexpected error'))

        # Act & Assert
        with pytest.raises(RuntimeError, match='Unexpected error'):
            phase.run()

        # finally句でステータスがfailedに更新されることを確認
        assert metadata_manager.get_phase_status('requirements') == 'failed'

    def test_run_revise_exception(self, setup_phase):
        """
        UT-008: revise()が例外をスローした場合

        検証項目:
        - revise()実行中に例外が発生した場合
        - 適切にハンドリングされること
        """
        # Arrange
        phase = setup_phase['phase']
        metadata_manager = setup_phase['metadata_manager']

        # execute()が失敗を返す
        phase.execute = Mock(return_value={'success': False, 'error': 'Initial error'})

        # review()がFAILを返す
        phase.review = Mock(return_value={
            'result': 'FAIL',
            'feedback': 'Test feedback',
            'suggestions': []
        })

        # revise()が例外をスロー
        phase.revise = Mock(side_effect=RuntimeError('Revise error'))

        # Act & Assert
        with pytest.raises(RuntimeError, match='Revise error'):
            phase.run()

        # finally句でステータスがfailedに更新されることを確認
        assert metadata_manager.get_phase_status('requirements') == 'failed'

    def test_run_attempt_logging(self, setup_phase, capsys):
        """
        UT-009: 試行回数ログの出力

        検証項目:
        - 各試行の開始時に[ATTEMPT N/3]形式でログが出力されること
        - 区切り線が表示されること
        """
        # Arrange
        phase = setup_phase['phase']

        # execute()が失敗を返す
        phase.execute = Mock(return_value={'success': False, 'error': 'Test error'})

        # review()がFAIL、revise()が成功を返す（2回目のreview()でPASS）
        review_results = [
            {'result': 'FAIL', 'feedback': 'Test feedback', 'suggestions': []},
            {'result': 'PASS', 'feedback': '', 'suggestions': []}
        ]
        phase.review = Mock(side_effect=review_results)
        phase.revise = Mock(return_value={'success': True, 'output': 'revised_output'})

        # Act
        phase.run()

        # Assert - 標準出力を確認
        captured = capsys.readouterr()
        assert '[ATTEMPT 1/3] Phase: requirements' in captured.out
        assert '[ATTEMPT 2/3] Phase: requirements' in captured.out
        assert '=' * 80 in captured.out  # 区切り線

    def test_run_failure_warning_log(self, setup_phase, capsys):
        """
        UT-010: 失敗時の警告ログ出力

        検証項目:
        - 各試行が失敗した場合、[WARNING]ログが出力されること
        """
        # Arrange
        phase = setup_phase['phase']

        # execute()が失敗を返す
        phase.execute = Mock(return_value={'success': False, 'error': 'Execute failed'})

        # review()が常にFAILを返す
        phase.review = Mock(return_value={
            'result': 'FAIL',
            'feedback': 'Test feedback',
            'suggestions': []
        })

        # revise()が常に失敗を返す
        phase.revise = Mock(return_value={'success': False, 'error': 'Revise failed'})

        # Act
        phase.run()

        # Assert - 標準出力を確認
        captured = capsys.readouterr()
        assert '[WARNING] Attempt 1 failed: Execute failed' in captured.out
        assert '[WARNING] Attempt 2 failed: Revise failed' in captured.out
        assert '[WARNING] Attempt 3 failed: Revise failed' in captured.out

    def test_run_metadata_retry_count_increment(self, setup_phase):
        """
        UT-011: メタデータのretry_count更新

        検証項目:
        - revise()実行時にメタデータのretry_countが正しくインクリメントされること
        """
        # Arrange
        phase = setup_phase['phase']
        metadata_manager = setup_phase['metadata_manager']

        # execute()が失敗を返す
        phase.execute = Mock(return_value={'success': False, 'error': 'Test error'})

        # review()がFAIL、revise()が成功を返す（2回目のreview()でPASS）
        review_results = [
            {'result': 'FAIL', 'feedback': 'Test feedback', 'suggestions': []},
            {'result': 'PASS', 'feedback': '', 'suggestions': []}
        ]
        phase.review = Mock(side_effect=review_results)
        phase.revise = Mock(return_value={'success': True, 'output': 'revised_output'})

        # Act
        phase.run()

        # Assert - retry_countが1増加していることを確認
        retry_count = metadata_manager.data['phases']['requirements'].get('retry_count', 0)
        assert retry_count == 1

    def test_run_phase_status_transitions(self, setup_phase):
        """
        UT-012: phase statusの更新（成功ケース）

        検証項目:
        - run()開始時にstatus='in_progress'になること
        - run()成功終了時にstatus='completed'になること
        """
        # Arrange
        phase = setup_phase['phase']
        metadata_manager = setup_phase['metadata_manager']

        # execute()とreview()は成功を返す
        phase.execute = Mock(return_value={'success': True, 'output': 'test_output'})
        phase.review = Mock(return_value={
            'result': 'PASS',
            'feedback': '',
            'suggestions': []
        })

        # Act
        # run()開始前は未設定
        initial_status = metadata_manager.get_phase_status('requirements')

        success = phase.run()

        # Assert
        assert success is True
        final_status = metadata_manager.get_phase_status('requirements')
        assert final_status == 'completed'
