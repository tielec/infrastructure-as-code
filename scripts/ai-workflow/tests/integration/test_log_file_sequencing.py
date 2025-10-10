"""ログファイル連番管理のIntegrationテスト

Issue #317: リトライ時のログファイル連番管理機能のテスト
execute → review → revise の各フェーズで独立した連番管理が行われることを検証
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from core.metadata_manager import MetadataManager
from core.workflow_state import WorkflowState
from core.claude_agent_client import ClaudeAgentClient
from core.github_client import GitHubClient
from phases.base_phase import BasePhase


class TestPhase(BasePhase):
    """テスト用のPhaseクラス"""

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


class TestLogFileSequencing:
    """ログファイル連番管理のIntegrationテスト"""

    @pytest.fixture
    def setup_integration_test(self, tmp_path):
        """統合テスト環境のセットアップ"""
        # metadata.jsonを作成
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='317',
            issue_url='https://github.com/test/repo/issues/317',
            issue_title='Test Issue #317'
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

        # メタデータマネージャー
        metadata_manager = MetadataManager(metadata_path)

        # モッククライアント
        claude_client = Mock(spec=ClaudeAgentClient)
        github_client = Mock(spec=GitHubClient)

        # フェーズインスタンス
        phase = TestPhase(
            working_dir=working_dir,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

        return {
            'phase': phase,
            'metadata_manager': metadata_manager,
            'claude_client': claude_client,
            'github_client': github_client
        }

    def test_log_sequencing_execute_review_revise(self, setup_integration_test):
        """
        TC-I001: 全フェーズでの連番管理（正常系）

        検証項目:
        - execute, review, revise の各フェーズで独立した連番管理が行われることを検証
        """
        # Arrange
        phase = setup_integration_test['phase']
        claude_client = setup_integration_test['claude_client']

        # executeフェーズ実行（初回）
        claude_client.execute_task_sync.return_value = ['execute response 1']
        phase.execute_with_claude(prompt='要件定義を作成', log_prefix='execute')

        # Assert: executeフェーズの確認
        assert (phase.execute_dir / 'agent_log_1.md').exists()
        assert (phase.execute_dir / 'agent_log_raw_1.txt').exists()
        assert (phase.execute_dir / 'prompt_1.txt').exists()

        # reviewフェーズ実行（初回）
        claude_client.execute_task_sync.return_value = ['review response 1']
        phase.execute_with_claude(prompt='要件をレビュー', log_prefix='review')

        # Assert: reviewフェーズの確認（連番=1から開始、executeの連番に影響されない）
        assert (phase.review_dir / 'agent_log_1.md').exists()
        assert (phase.review_dir / 'agent_log_raw_1.txt').exists()
        assert (phase.review_dir / 'prompt_1.txt').exists()

        # reviseフェーズ実行（初回）
        claude_client.execute_task_sync.return_value = ['revise response 1']
        phase.execute_with_claude(prompt='要件を修正', log_prefix='revise')

        # Assert: reviseフェーズの確認（連番=1から開始）
        assert (phase.revise_dir / 'agent_log_1.md').exists()
        assert (phase.revise_dir / 'agent_log_raw_1.txt').exists()
        assert (phase.revise_dir / 'prompt_1.txt').exists()

    def test_log_sequencing_retry_scenario(self, setup_integration_test):
        """
        TC-I002: reviseフェーズのリトライシナリオ（正常系）

        検証項目:
        - リトライ実行時に連番が正しくインクリメントされ、過去のログが保持されることを検証
        """
        # Arrange
        phase = setup_integration_test['phase']
        claude_client = setup_integration_test['claude_client']

        # 初回実行（execute, review）
        claude_client.execute_task_sync.return_value = ['execute response']
        phase.execute_with_claude(prompt='初回実行', log_prefix='execute')

        claude_client.execute_task_sync.return_value = ['review response']
        phase.execute_with_claude(prompt='初回レビュー', log_prefix='review')

        # reviseフェーズ初回実行
        claude_client.execute_task_sync.return_value = ['revise response 1']
        phase.execute_with_claude(prompt='要件を修正（初回）', log_prefix='revise')

        # Assert: 初回ファイル確認
        assert (phase.revise_dir / 'agent_log_1.md').exists()
        assert (phase.revise_dir / 'agent_log_raw_1.txt').exists()
        assert (phase.revise_dir / 'prompt_1.txt').exists()

        # reviseフェーズリトライ1回目
        claude_client.execute_task_sync.return_value = ['revise response 2']
        phase.execute_with_claude(prompt='要件を再修正（リトライ1）', log_prefix='revise')

        # Assert: 新規ファイル作成と既存ファイル保持
        assert (phase.revise_dir / 'agent_log_2.md').exists()
        assert (phase.revise_dir / 'agent_log_raw_2.txt').exists()
        assert (phase.revise_dir / 'prompt_2.txt').exists()
        # 既存ファイル保持
        assert (phase.revise_dir / 'agent_log_1.md').exists()
        assert (phase.revise_dir / 'agent_log_raw_1.txt').exists()
        assert (phase.revise_dir / 'prompt_1.txt').exists()

        # reviseフェーズリトライ2回目
        claude_client.execute_task_sync.return_value = ['revise response 3']
        phase.execute_with_claude(prompt='要件を再修正（リトライ2）', log_prefix='revise')

        # Assert: 新規ファイル作成と既存ファイル保持
        assert (phase.revise_dir / 'agent_log_3.md').exists()
        assert (phase.revise_dir / 'agent_log_raw_3.txt').exists()
        assert (phase.revise_dir / 'prompt_3.txt').exists()
        # 既存ファイル保持（1, 2）
        assert (phase.revise_dir / 'agent_log_1.md').exists()
        assert (phase.revise_dir / 'agent_log_2.md').exists()

    def test_log_sequencing_output_overwrite(self, setup_integration_test):
        """
        TC-I003: 成果物ファイルの上書き動作（正常系）

        検証項目:
        - output/ ディレクトリ配下の成果物ファイルは連番が付与されず、上書きされることを検証

        Note:
        - 成果物ファイルはPhaseの実装に依存するため、ここではログファイルの連番管理のみをテスト
        - 成果物の上書き動作は各PhaseのExecuteメソッドで実装される
        """
        # Arrange
        phase = setup_integration_test['phase']
        claude_client = setup_integration_test['claude_client']

        # 成果物ファイルを手動で作成（初回）
        output_file = phase.output_dir / 'requirements.md'
        output_file.write_text('初回要件定義', encoding='utf-8')
        initial_content = output_file.read_text()
        assert '初回要件定義' in initial_content

        # リトライ実行（revise）
        claude_client.execute_task_sync.return_value = ['revise response']
        phase.execute_with_claude(prompt='要件を修正', log_prefix='revise')

        # Assert: ログファイルは連番付きで保存される
        assert (phase.revise_dir / 'agent_log_1.md').exists()

        # 成果物ファイルを手動で更新（リトライ後）
        output_file.write_text('修正後要件定義', encoding='utf-8')
        updated_content = output_file.read_text()
        assert '修正後要件定義' in updated_content

        # Assert: 成果物ファイルは上書きされる（連番なし）
        assert output_file.exists()
        assert not (phase.output_dir / 'requirements_1.md').exists()
        assert not (phase.output_dir / 'requirements_2.md').exists()

    def test_log_sequencing_multiple_phases(self, tmp_path):
        """
        TC-I101: 複数フェーズ（requirements → design → implementation）での連番管理

        検証項目:
        - 異なるフェーズでそれぞれ独立した連番管理が行われることを検証
        """
        # Arrange: requirements フェーズ
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='317',
            issue_url='https://github.com/test/repo/issues/317',
            issue_title='Test Issue #317'
        )

        working_dir = tmp_path / 'working'
        working_dir.mkdir()

        # プロンプトディレクトリを作成
        for phase_name in ['requirements', 'design', 'test_scenario']:
            prompts_dir = working_dir / 'prompts' / phase_name
            prompts_dir.mkdir(parents=True)
            (prompts_dir / 'execute.txt').write_text(f'Test {phase_name} prompt', encoding='utf-8')

        metadata_manager = MetadataManager(metadata_path)
        claude_client = Mock(spec=ClaudeAgentClient)
        github_client = Mock(spec=GitHubClient)

        # Requirements Phase
        req_phase = TestPhase(
            working_dir=working_dir,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )
        claude_client.execute_task_sync.return_value = ['requirements response']
        req_phase.execute_with_claude(prompt='要件定義', log_prefix='execute')

        # Assert: requirements フェーズ
        assert (req_phase.execute_dir / 'agent_log_1.md').exists()

        # Design Phase (別のフェーズとして作成)
        class DesignPhase(BasePhase):
            def __init__(self, *args, **kwargs):
                super().__init__(phase_name='design', *args, **kwargs)

            def execute(self):
                return {'success': True}

            def review(self):
                return {'result': 'PASS', 'feedback': 'OK', 'suggestions': []}

        design_phase = DesignPhase(
            working_dir=working_dir,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )
        claude_client.execute_task_sync.return_value = ['design response']
        design_phase.execute_with_claude(prompt='設計書作成', log_prefix='execute')

        # Assert: design フェーズも連番=1から開始（requirements の連番に影響されない）
        assert (design_phase.execute_dir / 'agent_log_1.md').exists()

        # Test Scenario Phase
        class TestScenarioPhase(BasePhase):
            def __init__(self, *args, **kwargs):
                super().__init__(phase_name='test_scenario', *args, **kwargs)

            def execute(self):
                return {'success': True}

            def review(self):
                return {'result': 'PASS', 'feedback': 'OK', 'suggestions': []}

        test_scenario_phase = TestScenarioPhase(
            working_dir=working_dir,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )
        claude_client.execute_task_sync.return_value = ['test scenario response']
        test_scenario_phase.execute_with_claude(prompt='テストシナリオ作成', log_prefix='execute')

        # Assert: test_scenario フェーズも連番=1から開始
        assert (test_scenario_phase.execute_dir / 'agent_log_1.md').exists()

    def test_log_sequencing_backward_compatibility(self, setup_integration_test):
        """
        TC-I201: 既存の連番なしログファイルが存在する場合（互換性）

        検証項目:
        - 既存の連番なしログファイルとの共存を検証
        """
        # Arrange
        phase = setup_integration_test['phase']
        claude_client = setup_integration_test['claude_client']

        # 既存の連番なしファイルを作成
        (phase.execute_dir / 'agent_log.md').write_text('Old log', encoding='utf-8')
        (phase.execute_dir / 'agent_log_raw.txt').write_text('Old raw log', encoding='utf-8')
        (phase.execute_dir / 'prompt.txt').write_text('Old prompt', encoding='utf-8')

        # Assert: 既存ファイルの確認
        assert (phase.execute_dir / 'agent_log.md').exists()
        assert (phase.execute_dir / 'agent_log_raw.txt').exists()
        assert (phase.execute_dir / 'prompt.txt').exists()

        # 新しいロジックで実行
        claude_client.execute_task_sync.return_value = ['New response']
        phase.execute_with_claude(prompt='新規実行', log_prefix='execute')

        # Assert: 新規ファイルの確認（連番付き）
        assert (phase.execute_dir / 'agent_log_1.md').exists()
        assert (phase.execute_dir / 'agent_log_raw_1.txt').exists()
        assert (phase.execute_dir / 'prompt_1.txt').exists()

        # Assert: 既存ファイルが保持される
        assert (phase.execute_dir / 'agent_log.md').exists()
        assert (phase.execute_dir / 'agent_log_raw.txt').exists()
        assert (phase.execute_dir / 'prompt.txt').exists()

    def test_log_sequencing_performance(self, tmp_path):
        """
        TC-I301: 1000ファイル存在時の連番決定時間（性能）

        検証項目:
        - 1000ファイル存在時でも、連番決定が1秒以内に完了することを検証
        """
        import time
        import statistics

        # Arrange
        target_dir = tmp_path / 'perf_test_dir'
        target_dir.mkdir(exist_ok=True)

        # 1000ファイルの作成
        for i in range(1, 1001):
            (target_dir / f'agent_log_{i}.md').touch()

        # メタデータマネージャーとフェーズの作成
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='317',
            issue_url='https://github.com/test/repo/issues/317',
            issue_title='Performance Test'
        )

        working_dir = tmp_path / 'working'
        working_dir.mkdir()

        metadata_manager = MetadataManager(metadata_path)
        claude_client = Mock(spec=ClaudeAgentClient)
        github_client = Mock(spec=GitHubClient)

        phase = TestPhase(
            working_dir=working_dir,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

        # Act: 連番決定時間の計測（3回実行して平均を取る）
        execution_times = []
        for _ in range(3):
            start_time = time.time()
            next_seq = phase._get_next_sequence_number(target_dir)
            elapsed_time = time.time() - start_time
            execution_times.append(elapsed_time)
            assert next_seq == 1001

        avg_time = statistics.mean(execution_times)
        max_time = max(execution_times)

        # Assert: パフォーマンス要件
        # 平均実行時間が1秒以内
        assert avg_time < 1.0, f"Average time {avg_time:.3f}s exceeds 1.0s"
        # 最大実行時間も許容範囲内（1.2秒、±20%の許容誤差）
        assert max_time < 1.2, f"Max time {max_time:.3f}s exceeds 1.2s"

        print(f"[PERF] Average execution time: {avg_time:.3f}s")
        print(f"[PERF] Max execution time: {max_time:.3f}s")
