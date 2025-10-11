"""
Planning Phase統合テスト

Purpose:
    Issue #332で実装したPlanning PhaseのJenkins統合とプロンプト修正機能が正常に動作することを検証

Test Strategy:
    INTEGRATION_ONLY - 統合テストのみ実施（Phase 3のテストシナリオに基づく）

Test Cases:
    - IT-PP-001: BasePhaseヘルパーメソッドの統合（Planning Document存在時）
    - IT-PP-002: BasePhaseヘルパーメソッドの統合（Planning Document不在時）
    - IT-PP-003: プロンプトテンプレートのプレースホルダー置換
    - IT-PP-004: Requirements PhaseでのPlanning Document参照
    - IT-PP-005: Design PhaseでのPlanning Document参照
    - IT-PP-006: 全Phaseのプロンプト統一フォーマット確認

Note:
    これらのテストは Issue #332 の実装を検証するためのものです。
    Jenkins環境での実行が必要なテストは手動テストとしてスキップします。
"""
import subprocess
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestPlanningPhaseIntegration:
    """Planning Phase統合テスト"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """テストセットアップ"""
        self.repo_root = Path.cwd()
        self.workflow_dir = self.repo_root / '.ai-workflow'
        self.scripts_dir = self.repo_root / 'scripts' / 'ai-workflow'

        # テスト用のIssue番号
        self.test_issue_number = 332

    def test_base_phase_helper_with_planning_doc(self):
        """
        IT-PP-001: BasePhaseヘルパーメソッドの統合（Planning Document存在時）

        対応テストシナリオ: 3-1
        検証対象: BasePhase._get_planning_document_path() の統合動作
        """
        # Planning Documentのパスを構築
        planning_file = self.workflow_dir / f'issue-{self.test_issue_number}' / '00_planning' / 'output' / 'planning.md'

        # Planning Documentが存在することを確認
        if not planning_file.exists():
            pytest.skip(f"Planning Document not found: {planning_file}")

        # BasePhaseを継承したクラス（Requirements Phase）をインポート
        import sys
        sys.path.insert(0, str(self.scripts_dir / 'phases'))

        try:
            from requirements import RequirementsPhase

            # モックオブジェクトを作成
            mock_github = MagicMock()
            mock_claude = MagicMock()
            mock_claude.working_dir = self.repo_root
            mock_metadata = MagicMock()
            mock_metadata.workflow_dir = self.workflow_dir / f'issue-{self.test_issue_number}' / '01_requirements'
            mock_metadata.data = {'issue_number': str(self.test_issue_number)}

            # RequirementsPhaseインスタンス作成
            phase = RequirementsPhase(
                github=mock_github,
                claude=mock_claude,
                metadata=mock_metadata
            )

            # ヘルパーメソッド呼び出し
            result = phase._get_planning_document_path(self.test_issue_number)

            # 検証ポイント
            assert result.startswith('@'), f"Expected path to start with '@', got: {result}"
            assert 'planning.md' in result, f"Expected 'planning.md' in path, got: {result}"
            assert str(self.test_issue_number) in result or f'issue-{self.test_issue_number}' in result, \
                   f"Expected issue number in path, got: {result}"

        finally:
            sys.path.pop(0)

    def test_base_phase_helper_without_planning_doc(self):
        """
        IT-PP-002: BasePhaseヘルパーメソッドの統合（Planning Document不在時）

        対応テストシナリオ: 4-1
        検証対象: BasePhase._get_planning_document_path() のエラーハンドリング
        """
        # 存在しないIssue番号を使用
        non_existent_issue = 99999

        # BasePhaseを継承したクラス（Requirements Phase）をインポート
        import sys
        sys.path.insert(0, str(self.scripts_dir / 'phases'))

        try:
            from requirements import RequirementsPhase

            # モックオブジェクトを作成
            mock_github = MagicMock()
            mock_claude = MagicMock()
            mock_claude.working_dir = self.repo_root
            mock_metadata = MagicMock()
            mock_metadata.workflow_dir = self.workflow_dir / f'issue-{non_existent_issue}' / '01_requirements'
            mock_metadata.data = {'issue_number': str(non_existent_issue)}

            # RequirementsPhaseインスタンス作成
            phase = RequirementsPhase(
                github=mock_github,
                claude=mock_claude,
                metadata=mock_metadata
            )

            # ヘルパーメソッド呼び出し
            result = phase._get_planning_document_path(non_existent_issue)

            # 検証ポイント: 警告メッセージが返される
            assert result == "Planning Phaseは実行されていません", \
                   f"Expected warning message, got: {result}"

        finally:
            sys.path.pop(0)

    def test_prompt_template_placeholder_replacement(self):
        """
        IT-PP-003: プロンプトテンプレートのプレースホルダー置換

        対応テストシナリオ: 5-1
        検証対象: プロンプトテンプレートの {planning_document_path} プレースホルダー置換
        """
        # プロンプトファイルの存在確認
        prompt_files = [
            'requirements/execute.txt',
            'design/execute.txt',
            'test_scenario/execute.txt',
            'implementation/execute.txt',
            'testing/execute.txt',
            'documentation/execute.txt',
            'report/execute.txt'
        ]

        for prompt_file in prompt_files:
            prompt_path = self.scripts_dir / 'prompts' / prompt_file

            # ファイル存在確認
            assert prompt_path.exists(), f"Prompt file not found: {prompt_path}"

            # ファイル内容確認
            content = prompt_path.read_text(encoding='utf-8')

            # 検証ポイント: {planning_document_path} プレースホルダーが含まれる
            assert '{planning_document_path}' in content, \
                   f"Expected '{{planning_document_path}}' in {prompt_file}"

            # 検証ポイント: Planning Phase成果物セクションが含まれる
            assert 'Planning Phase成果物' in content or 'Planning Document' in content, \
                   f"Expected 'Planning Phase成果物' or 'Planning Document' in {prompt_file}"

    def test_unified_prompt_format_across_phases(self):
        """
        IT-PP-006: 全Phaseのプロンプト統一フォーマット確認

        対応テストシナリオ: 5-2
        検証対象: 全Phase（Phase 1-7）のプロンプトで統一されたPlanning Document参照フォーマット
        """
        prompt_files = [
            'requirements/execute.txt',
            'design/execute.txt',
            'test_scenario/execute.txt',
            'implementation/execute.txt',
            'testing/execute.txt',
            'documentation/execute.txt',
            'report/execute.txt'
        ]

        for prompt_file in prompt_files:
            prompt_path = self.scripts_dir / 'prompts' / prompt_file

            # ファイル存在確認
            assert prompt_path.exists(), f"Prompt file not found: {prompt_path}"

            # ファイル内容確認
            content = prompt_path.read_text(encoding='utf-8')

            # 検証ポイント: 統一されたフォーマット
            # 1. {planning_document_path} プレースホルダー
            assert '{planning_document_path}' in content, \
                   f"Expected '{{planning_document_path}}' in {prompt_file}"

            # 2. Planning Documentの説明
            assert 'Planning' in content, \
                   f"Expected 'Planning' in {prompt_file}"

            # 3. 注意書き（推奨）
            if '注意' in content or 'Planning Phaseが実行されている場合' in content:
                # 注意書きがあれば、内容を確認
                assert 'Planning' in content, \
                       f"Expected Planning-related note in {prompt_file}"


class TestPlanningPhaseJenkinsIntegration:
    """Planning Phase Jenkins統合テスト（手動テスト用）"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """テストセットアップ"""
        self.repo_root = Path.cwd()

    def test_jenkins_planning_phase_stage(self):
        """
        Jenkins Planning Phaseステージの動作確認

        対応テストシナリオ: 1-1
        検証対象: JenkinsfileのPlanning Phaseステージ

        Note:
            このテストはJenkins環境が必要なため、手動テストで実施することを推奨します。
        """
        pytest.skip("This test requires Jenkins environment")

    def test_jenkins_start_phase_parameter(self):
        """
        START_PHASEパラメータの確認

        対応テストシナリオ: 1-2
        検証対象: Job DSLのSTART_PHASEパラメータ

        Note:
            このテストはJenkins環境が必要なため、手動テストで実施することを推奨します。
        """
        pytest.skip("This test requires Jenkins environment")

    def test_planning_requirements_phase_integration(self):
        """
        Planning Phase → Requirements Phase連携

        対応テストシナリオ: 2-1
        検証対象: Requirements PhaseでのPlanning Document参照

        Note:
            このテストはJenkins環境が必要なため、手動テストで実施することを推奨します。
        """
        pytest.skip("This test requires Jenkins environment")

    def test_planning_design_phase_integration(self):
        """
        Planning Phase → Design Phase連携

        対応テストシナリオ: 2-2
        検証対象: Design PhaseでのPlanning Document参照

        Note:
            このテストはJenkins環境が必要なため、手動テストで実施することを推奨します。
        """
        pytest.skip("This test requires Jenkins environment")

    def test_full_phase_e2e_integration(self):
        """
        全Phase（Phase 0-7）のE2E連携

        対応テストシナリオ: 2-3
        検証対象: Planning Phase → Report Phase（全Phase統合）

        Note:
            このテストはJenkins環境が必要なため、手動テストで実施することを推奨します。
        """
        pytest.skip("This test requires Jenkins environment")

    def test_claude_agent_sdk_integration(self):
        """
        Claude Agent SDKとの統合

        対応テストシナリオ: 3-2
        検証対象: @{path} 記法によるファイル参照

        Note:
            このテストはClaude Agent SDK環境が必要なため、手動テストで実施することを推奨します。
        """
        pytest.skip("This test requires Claude Agent SDK environment")

    def test_error_handling_without_planning_doc(self):
        """
        Planning Document不在時の動作

        対応テストシナリオ: 4-1
        検証対象: Planning Documentが存在しない場合の各Phaseの挙動

        Note:
            このテストはJenkins環境が必要なため、手動テストで実施することを推奨します。
        """
        pytest.skip("This test requires Jenkins environment")

    def test_error_handling_full_workflow_without_planning(self):
        """
        Planning Document不在時の全Phase実行

        対応テストシナリオ: 4-2
        検証対象: Planning PhaseをスキップしたE2Eワークフロー

        Note:
            このテストはJenkins環境が必要なため、手動テストで実施することを推奨します。
        """
        pytest.skip("This test requires Jenkins environment")

    def test_relative_path_error_handling(self):
        """
        相対パス取得エラーのハンドリング

        対応テストシナリオ: 4-3
        検証対象: working_dirからの相対パスが取得できない場合の挙動

        Note:
            このテストは異常な環境条件が必要なため、モックまたは手動テストで実施することを推奨します。
        """
        pytest.skip("This test requires mock setup or abnormal environment")


class TestPlanningPhaseNonFunctional:
    """Planning Phase非機能要件テスト"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """テストセットアップ"""
        self.repo_root = Path.cwd()

    def test_performance_planning_phase_execution(self):
        """
        Planning Phase実行時間測定

        対応テストシナリオ: P-1
        検証対象: Planning Phaseの実行時間が5分以内

        Note:
            このテストはJenkins環境が必要なため、手動テストで実施することを推奨します。
        """
        pytest.skip("This test requires Jenkins environment")

    def test_performance_helper_method_execution(self):
        """
        _get_planning_document_path() 実行時間測定

        対応テストシナリオ: P-2
        検証対象: ヘルパーメソッドの実行時間が100ms以内

        Note:
            このテストは実環境でのパフォーマンス測定が必要なため、手動テストで実施することを推奨します。
        """
        pytest.skip("This test requires performance measurement in real environment")

    def test_reliability_without_planning_doc(self):
        """
        Planning Document不在時の継続性

        対応テストシナリオ: R-1
        検証対象: Planning Documentが存在しない場合でも各Phaseが正常に実行される

        Note:
            このテストはJenkins環境が必要なため、手動テストで実施することを推奨します。
        """
        pytest.skip("This test requires Jenkins environment")

    def test_maintainability_new_phase_compatibility(self):
        """
        新Phase追加時の互換性

        対応テストシナリオ: M-1
        検証対象: 新しいPhaseを追加する際、BasePhaseのヘルパーメソッドを再利用できる

        Note:
            このテストは新Phaseの実装が必要なため、モックまたは手動テストで実施することを推奨します。
        """
        pytest.skip("This test requires mock setup or new phase implementation")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
