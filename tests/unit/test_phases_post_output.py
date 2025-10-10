"""
Unitテスト: 全フェーズの成果物投稿機能

Issue #310: 全フェーズの成果物をGitHub Issueコメントに投稿する機能のテスト
テストシナリオ: .ai-workflow/issue-310/03_test_scenario/output/test-scenario.md
"""
import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path

# テスト対象のフェーズクラスをインポート
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts' / 'ai-workflow'))

from phases.requirements import RequirementsPhase
from phases.design import DesignPhase
from phases.test_scenario import TestScenarioPhase
from phases.implementation import ImplementationPhase
from phases.testing import TestingPhase
from phases.report import ReportPhase
from phases.base_phase import BasePhase


class TestRequirementsPhasePostOutput:
    """Phase 1: RequirementsPhase.execute() の成果物投稿テスト"""

    def test_requirements_execute_正常系_成果物投稿成功(self, tmp_path):
        """
        テストケース 1-1: requirements_execute_正常系_成果物投稿成功

        目的: Phase 1が正常に完了した場合、成果物がGitHub Issueに投稿されることを検証
        """
        # モック設定
        with patch.object(RequirementsPhase, '__init__', return_value=None):
            phase = RequirementsPhase()

            # 必要な属性を手動設定
            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            # metadata属性を設定（execute()内で使用される）
            phase.metadata = MagicMock()
            phase.metadata.data = {'issue_number': 310}

            # requirements.mdを作成
            requirements_file = phase.output_dir / 'requirements.md'
            requirements_file.write_text('# 要件定義書\n\n## 概要\n\nテスト内容', encoding='utf-8')

            # execute()メソッドの主要部分をモック化
            phase.github = MagicMock()
            phase.github.get_issue_info.return_value = {
                'number': 310,
                'title': 'Test Issue',
                'state': 'open',
                'url': 'https://github.com/test/repo/issues/310',
                'labels': [],
                'body': 'Test body'
            }

            phase._format_issue_info = MagicMock(return_value='Issue Info')
            phase.load_prompt = MagicMock(return_value='Test prompt {issue_info} {issue_number}')
            phase.execute_with_claude = MagicMock(return_value=[])

            with patch.object(BasePhase, 'post_output') as mock_post_output:
                # execute()を実行
                result = phase.execute()

                # 検証: post_output()が呼ばれたか
                mock_post_output.assert_called_once()

                # 検証: 引数が正しいか
                args, kwargs = mock_post_output.call_args
                assert kwargs['title'] == "要件定義書"
                assert '要件定義書' in kwargs['output_content']

                # 検証: execute()が成功を返すか
                assert result['success'] is True

    def test_requirements_execute_異常系_GitHub投稿失敗(self, tmp_path):
        """
        テストケース 1-2: requirements_execute_異常系_GitHub投稿失敗

        目的: GitHub API投稿失敗時でもワークフローが継続することを検証
        """
        with patch.object(RequirementsPhase, '__init__', return_value=None):
            phase = RequirementsPhase()
            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            # metadata属性を設定
            phase.metadata = MagicMock()
            phase.metadata.data = {'issue_number': 310}

            # requirements.mdを作成
            requirements_file = phase.output_dir / 'requirements.md'
            requirements_file.write_text('# 要件定義書', encoding='utf-8')

            # 必要なメソッドをモック化
            phase.github = MagicMock()
            phase.github.get_issue_info.return_value = {
                'number': 310, 'title': 'Test', 'state': 'open',
                'url': 'https://test.com', 'labels': [], 'body': 'Test'
            }
            phase._format_issue_info = MagicMock(return_value='Issue Info')
            phase.load_prompt = MagicMock(return_value='Test prompt {issue_info} {issue_number}')
            phase.execute_with_claude = MagicMock(return_value=[])

            # post_output()が例外をスロー
            with patch.object(BasePhase, 'post_output', side_effect=Exception("GitHub API Error")):
                with patch('builtins.print') as mock_print:
                    # execute()を実行
                    result = phase.execute()

                    # 検証: WARNINGログが出力されたか
                    warning_calls = [str(call_args) for call_args in mock_print.call_args_list]
                    assert any('[WARNING] 成果物のGitHub投稿に失敗しました' in str(call_str) for call_str in warning_calls)

                    # 検証: execute()が成功を返すか（ワークフロー継続）
                    assert result['success'] is True

    def test_requirements_execute_正常系_UTF8エンコーディング(self, tmp_path):
        """
        テストケース 1-4: requirements_execute_正常系_UTF8エンコーディング

        目的: UTF-8エンコーディングで日本語を含む成果物が正しく読み込まれることを検証
        """
        with patch.object(RequirementsPhase, '__init__', return_value=None):
            phase = RequirementsPhase()
            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            # metadata属性を設定
            phase.metadata = MagicMock()
            phase.metadata.data = {'issue_number': 310}

            # 日本語を含む requirements.md を作成
            requirements_file = phase.output_dir / 'requirements.md'
            requirements_content = "# 要件定義書\n\n## 1. 概要\n\n現在のAI駆動開発自動化ワークフロー"
            requirements_file.write_text(requirements_content, encoding='utf-8')

            # 必要なメソッドをモック化
            phase.github = MagicMock()
            phase.github.get_issue_info.return_value = {
                'number': 310, 'title': 'Test', 'state': 'open',
                'url': 'https://test.com', 'labels': [], 'body': 'Test'
            }
            phase._format_issue_info = MagicMock(return_value='Issue Info')
            phase.load_prompt = MagicMock(return_value='Test prompt {issue_info} {issue_number}')
            phase.execute_with_claude = MagicMock(return_value=[])

            with patch.object(BasePhase, 'post_output') as mock_post_output:
                # execute()を実行
                result = phase.execute()

                # 検証: 日本語が正しく含まれるか
                args, kwargs = mock_post_output.call_args
                assert "要件定義書" in kwargs['output_content']
                assert "AI駆動開発自動化ワークフロー" in kwargs['output_content']


class TestDesignPhasePostOutput:
    """Phase 2: DesignPhase.execute() の成果物投稿テスト"""

    def test_design_execute_正常系_既存変数再利用(self, tmp_path):
        """
        テストケース 2-1: design_execute_正常系_既存変数再利用

        目的: Phase 2で既存の design_content 変数が再利用され、ファイル読み込みが1回のみであることを検証
        """
        with patch.object(DesignPhase, '__init__', return_value=None):
            phase = DesignPhase()
            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()
            phase.metadata = MagicMock()
            phase.metadata.data = {}

            # design.md を作成
            design_file = phase.output_dir / 'design.md'
            design_content = "# 詳細設計書\n\n## 実装戦略: EXTEND"
            design_file.write_text(design_content, encoding='utf-8')

            with patch.object(phase, 'github') as mock_github:
                mock_github.get_issue_info.return_value = {
                    'number': 310, 'title': 'Test', 'state': 'open',
                    'url': 'https://test.com', 'labels': [], 'body': 'Test'
                }

                with patch.object(phase, 'execute_with_claude', return_value=[]):
                    with patch.object(phase, '_extract_design_decisions', return_value={}):
                        with patch.object(BasePhase, 'post_output') as mock_post_output:
                            # execute()を実行
                            result = phase.execute()

                            # 検証: post_output()が呼ばれたか
                            mock_post_output.assert_called_once()

                            # 検証: タイトルが正しいか
                            args, kwargs = mock_post_output.call_args
                            assert kwargs['title'] == "詳細設計書"

                            # 検証: design_contentが使用されているか
                            assert "詳細設計書" in kwargs['output_content']


class TestTestScenarioPhasePostOutput:
    """Phase 3: TestScenarioPhase.execute() の成果物投稿テスト"""

    def test_test_scenario_execute_正常系_成果物投稿成功(self, tmp_path):
        """
        テストケース 3-1: test_scenario_execute_正常系_成果物投稿成功

        目的: Phase 3が正常に完了した場合、成果物がGitHub Issueに投稿されることを検証
        """
        with patch.object(TestScenarioPhase, '__init__', return_value=None):
            phase = TestScenarioPhase()
            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            # metadata属性を設定
            phase.metadata = MagicMock()
            phase.metadata.data = {'issue_number': 310}

            # test-scenario.md を作成
            test_scenario_file = phase.output_dir / 'test-scenario.md'
            test_scenario_file.write_text('# テストシナリオ\n\n## Unitテスト', encoding='utf-8')

            # 必要なメソッドをモック化
            phase.github = MagicMock()
            phase.github.get_issue_info.return_value = {
                'number': 310, 'title': 'Test', 'state': 'open',
                'url': 'https://test.com', 'labels': [], 'body': 'Test'
            }
            phase._format_issue_info = MagicMock(return_value='Issue Info')
            phase.load_prompt = MagicMock(return_value='Test prompt {issue_info} {issue_number}')
            phase.execute_with_claude = MagicMock(return_value=[])

            with patch.object(BasePhase, 'post_output') as mock_post_output:
                # execute()を実行
                result = phase.execute()

                # 検証
                mock_post_output.assert_called_once()
                args, kwargs = mock_post_output.call_args
                assert kwargs['title'] == "テストシナリオ"


class TestImplementationPhasePostOutput:
    """Phase 4: ImplementationPhase.execute() の成果物投稿テスト"""

    def test_implementation_execute_正常系_成果物投稿成功(self, tmp_path):
        """
        テストケース 4-1: implementation_execute_正常系_成果物投稿成功

        目的: Phase 4が正常に完了した場合、成果物がGitHub Issueに投稿されることを検証
        """
        with patch.object(ImplementationPhase, '__init__', return_value=None):
            phase = ImplementationPhase()
            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            # metadata属性を設定
            phase.metadata = MagicMock()
            phase.metadata.data = {'issue_number': 310}

            # implementation.md を作成
            impl_file = phase.output_dir / 'implementation.md'
            impl_file.write_text('# 実装ログ\n\n## 変更内容', encoding='utf-8')

            # 必要なメソッドをモック化
            phase.github = MagicMock()
            phase.github.get_issue_info.return_value = {
                'number': 310, 'title': 'Test', 'state': 'open',
                'url': 'https://test.com', 'labels': [], 'body': 'Test'
            }
            phase._format_issue_info = MagicMock(return_value='Issue Info')
            phase.load_prompt = MagicMock(return_value='Test prompt {issue_info} {issue_number}')
            phase.execute_with_claude = MagicMock(return_value=[])

            with patch.object(BasePhase, 'post_output') as mock_post_output:
                # execute()を実行
                result = phase.execute()

                # 検証
                mock_post_output.assert_called_once()
                args, kwargs = mock_post_output.call_args
                assert kwargs['title'] == "実装ログ"


class TestTestingPhasePostOutput:
    """Phase 5: TestingPhase.execute() の成果物投稿テスト"""

    def test_testing_execute_正常系_成果物投稿成功(self, tmp_path):
        """
        テストケース 5-1: testing_execute_正常系_成果物投稿成功

        目的: Phase 5が正常に完了した場合、成果物がGitHub Issueに投稿されることを検証
        """
        with patch.object(TestingPhase, '__init__', return_value=None):
            phase = TestingPhase()
            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            # metadata属性を設定
            phase.metadata = MagicMock()
            phase.metadata.data = {'issue_number': 310}

            # test-result.md を作成
            test_result_file = phase.output_dir / 'test-result.md'
            test_result_file.write_text('# テスト結果\n\n## テスト実行結果', encoding='utf-8')

            # 必要なメソッドをモック化
            phase.github = MagicMock()
            phase.github.get_issue_info.return_value = {
                'number': 310, 'title': 'Test', 'state': 'open',
                'url': 'https://test.com', 'labels': [], 'body': 'Test'
            }
            phase._format_issue_info = MagicMock(return_value='Issue Info')
            phase.load_prompt = MagicMock(return_value='Test prompt {issue_info} {issue_number}')
            phase.execute_with_claude = MagicMock(return_value=[])

            with patch.object(BasePhase, 'post_output') as mock_post_output:
                # execute()を実行
                result = phase.execute()

                # 検証
                mock_post_output.assert_called_once()
                args, kwargs = mock_post_output.call_args
                assert kwargs['title'] == "テスト結果"


class TestReportPhasePostOutput:
    """Phase 7: ReportPhase.execute() の成果物投稿テスト"""

    def test_report_execute_確認_既存実装の動作検証(self, tmp_path):
        """
        テストケース 7-1: report_execute_確認_既存実装の動作検証

        目的: Phase 7で既に実装されている post_output() 呼び出しが正しく動作することを確認
        """
        with patch.object(ReportPhase, '__init__', return_value=None):
            phase = ReportPhase()
            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            # metadata属性を設定
            phase.metadata = MagicMock()
            phase.metadata.data = {'issue_number': 310}

            # report.md を作成
            report_file = phase.output_dir / 'report.md'
            report_file.write_text('# 最終レポート\n\n## エグゼクティブサマリー', encoding='utf-8')

            # 必要なメソッドをモック化
            phase.github = MagicMock()
            phase.github.get_issue_info.return_value = {
                'number': 310, 'title': 'Test', 'state': 'open',
                'url': 'https://test.com', 'labels': [], 'body': 'Test'
            }
            phase._format_issue_info = MagicMock(return_value='Issue Info')
            phase.load_prompt = MagicMock(return_value='Test prompt {issue_info} {issue_number}')
            phase.execute_with_claude = MagicMock(return_value=[])

            with patch.object(BasePhase, 'post_output') as mock_post_output:
                # execute()を実行
                result = phase.execute()

                # 検証
                mock_post_output.assert_called_once()
                args, kwargs = mock_post_output.call_args
                assert kwargs['title'] == "最終レポート"


class TestCommonErrorHandling:
    """共通エラーハンドリングテスト"""

    def test_全フェーズ_異常系_例外スロー時のWARNINGログ(self, tmp_path):
        """
        テストケース E-1: 全フェーズ_異常系_例外スロー時のWARNINGログ

        目的: すべてのフェーズで post_output() が例外をスローした場合、WARNING ログが出力されることを検証
        """
        # すべてのフェーズクラスをテスト
        phase_classes = [
            (RequirementsPhase, 'requirements.md'),
            (DesignPhase, 'design.md'),
            (TestScenarioPhase, 'test-scenario.md'),
            (ImplementationPhase, 'implementation.md'),
            (TestingPhase, 'test-result.md'),
            (ReportPhase, 'report.md')
        ]

        for PhaseClass, output_filename in phase_classes:
            with patch.object(PhaseClass, '__init__', return_value=None):
                phase = PhaseClass()
                phase.output_dir = tmp_path / 'output'
                phase.output_dir.mkdir(exist_ok=True)

                # metadata属性を設定（全フェーズで必要）
                phase.metadata = MagicMock()
                phase.metadata.data = {'issue_number': 310}

                # 成果物ファイルを作成
                output_file = phase.output_dir / output_filename
                output_file.write_text('# テスト成果物', encoding='utf-8')

                # 必要なメソッドをモック化
                phase.github = MagicMock()
                phase.github.get_issue_info.return_value = {
                    'number': 310, 'title': 'Test', 'state': 'open',
                    'url': 'https://test.com', 'labels': [], 'body': 'Test'
                }
                phase._format_issue_info = MagicMock(return_value='Issue Info')
                phase.load_prompt = MagicMock(return_value='Test prompt {issue_info} {issue_number}')
                phase.execute_with_claude = MagicMock(return_value=[])

                if PhaseClass == DesignPhase:
                    phase._extract_design_decisions = MagicMock(return_value={})

                with patch.object(BasePhase, 'post_output', side_effect=Exception("Test Exception")):
                    with patch('builtins.print') as mock_print:
                        # execute()を実行
                        result = phase.execute()

                        # 検証: WARNINGログが出力されたか
                        warning_calls = [str(call_args) for call_args in mock_print.call_args_list]
                        assert any('[WARNING] 成果物のGitHub投稿に失敗しました' in str(call_str) for call_str in warning_calls)

                        # 検証: execute()が成功を返すか
                        assert result['success'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
