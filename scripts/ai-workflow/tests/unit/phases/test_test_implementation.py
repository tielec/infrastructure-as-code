"""
Unitテスト: TestImplementationPhase

Issue #324: Phase 5（test_implementation）の新設
テストシナリオ: .ai-workflow/issue-324/03_test_scenario/output/test-scenario.md

このテストファイルは、TestImplementationPhaseクラスの全メソッド（__init__, execute, review, revise）
の動作を検証します。
"""
import pytest
from unittest.mock import patch, MagicMock, call, mock_open
from pathlib import Path

# テスト対象のTestImplementationPhaseをインポート
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'scripts' / 'ai-workflow'))

from phases.test_implementation import TestImplementationPhase
from phases.base_phase import BasePhase


class TestTestImplementationPhaseInit:
    """TestImplementationPhase.__init__() のテスト"""

    def test_init_正常系(self):
        """
        テストケース: test_init_正常系

        目的: TestImplementationPhaseクラスが正しく初期化されることを検証
        前提条件:
          - BasePhaseが正常にインポート可能
          - ClaudeAgentClient、MetadataManagerが正常に動作
        入力:
          - issue_number=324
          - working_dir=/tmp/test_workspace
        期待結果:
          - phase_name='test_implementation'が設定される
          - 例外が発生しない
        """
        with patch.object(TestImplementationPhase, '__init__', lambda self, *args, **kwargs: None):
            phase = TestImplementationPhase()
            phase.phase_name = 'test_implementation'

            # 検証: phase_nameが正しく設定されている
            assert phase.phase_name == 'test_implementation'


class TestTestImplementationPhaseExecute:
    """TestImplementationPhase.execute() のテスト"""

    def test_execute_正常系(self, tmp_path):
        """
        テストケース: test_execute_正常系

        目的: テストコード実装が正常に実行されることを検証
        前提条件:
          - Phase 0〜4が正常に完了している
          - 必須ファイルが存在する
          - metadata.jsonにtest_strategy='UNIT_INTEGRATION'が設定されている
          - metadata.jsonにtest_code_strategy='CREATE_TEST'が設定されている
        入力: なし（execute()は引数なし）
        期待結果:
          - 戻り値: {'success': True, 'output': '<test-implementation.mdのパス>', 'error': None}
          - test-implementation.mdが生成される
          - metadata.jsonのtest_implementationステータスが'completed'に更新される
        """
        with patch.object(TestImplementationPhase, '__init__', return_value=None):
            phase = TestImplementationPhase()

            # 必要な属性を手動設定
            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            # metadata属性を設定
            phase.metadata = MagicMock()
            phase.metadata.data = {
                'issue_number': 324,
                'design_decisions': {
                    'test_strategy': 'UNIT_INTEGRATION',
                    'test_code_strategy': 'CREATE_TEST'
                }
            }
            phase.metadata.workflow_dir = tmp_path / '.ai-workflow' / 'issue-324'
            phase.metadata.workflow_dir.mkdir(parents=True)

            # 必須ファイルを作成
            requirements_dir = tmp_path / 'issue-324' / '01_requirements' / 'output'
            requirements_dir.mkdir(parents=True)
            requirements_file = requirements_dir / 'requirements.md'
            requirements_file.write_text('# 要件定義書', encoding='utf-8')

            design_dir = tmp_path / 'issue-324' / '02_design' / 'output'
            design_dir.mkdir(parents=True)
            design_file = design_dir / 'design.md'
            design_file.write_text('# 詳細設計書', encoding='utf-8')

            test_scenario_dir = tmp_path / 'issue-324' / '03_test_scenario' / 'output'
            test_scenario_dir.mkdir(parents=True)
            test_scenario_file = test_scenario_dir / 'test-scenario.md'
            test_scenario_file.write_text('# テストシナリオ', encoding='utf-8')

            implementation_dir = tmp_path / 'issue-324' / '04_implementation' / 'output'
            implementation_dir.mkdir(parents=True)
            implementation_file = implementation_dir / 'implementation.md'
            implementation_file.write_text('# 実装ログ', encoding='utf-8')

            # Claude関連のモック
            phase.claude = MagicMock()
            phase.claude.working_dir = tmp_path

            # メソッドをモック化
            phase.load_prompt = MagicMock(return_value='Test prompt {planning_document_path} {requirements_document_path} {design_document_path} {test_scenario_document_path} {implementation_document_path} {test_strategy} {test_code_strategy} {issue_number}')
            phase._get_planning_document_path = MagicMock(return_value='@.ai-workflow/issue-324/00_planning/output/planning.md')
            phase.execute_with_claude = MagicMock(return_value=[])
            phase.post_output = MagicMock()

            # test-implementation.mdを作成（execute_with_claude実行後に生成される想定）
            test_implementation_file = phase.output_dir / 'test-implementation.md'
            test_implementation_file.write_text('# テストコード実装ログ\n\n## 実装内容', encoding='utf-8')

            # execute()を実行
            result = phase.execute()

            # 検証: 戻り値が成功
            assert result['success'] is True
            assert result['error'] is None
            assert 'test-implementation.md' in result['output']

            # 検証: execute_with_claudeが呼ばれた
            phase.execute_with_claude.assert_called_once()

            # 検証: post_outputが呼ばれた
            phase.post_output.assert_called_once()

    def test_execute_必須ファイル不在エラー(self, tmp_path):
        """
        テストケース: test_execute_必須ファイル不在エラー

        目的: 必須ファイルが存在しない場合にエラーが返されることを検証
        前提条件:
          - requirements.mdが存在しない
        入力: なし
        期待結果:
          - 戻り値: {'success': False, 'output': None, 'error': '必要なファイルが見つかりません: <パス>'}
          - test-implementation.mdが生成されない
        """
        with patch.object(TestImplementationPhase, '__init__', return_value=None):
            phase = TestImplementationPhase()

            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            phase.metadata = MagicMock()
            phase.metadata.data = {
                'issue_number': 324,
                'design_decisions': {
                    'test_strategy': 'UNIT_INTEGRATION',
                    'test_code_strategy': 'CREATE_TEST'
                }
            }
            phase.metadata.workflow_dir = tmp_path / '.ai-workflow' / 'issue-324'
            phase.metadata.workflow_dir.mkdir(parents=True)

            # 必須ファイルを作成しない（requirements.mdが存在しない）

            # execute()を実行
            result = phase.execute()

            # 検証: エラーが返される
            assert result['success'] is False
            assert result['output'] is None
            assert '必要なファイルが見つかりません' in result['error']
            assert '要件定義書' in result['error']

    def test_execute_テスト戦略未定義エラー(self, tmp_path):
        """
        テストケース: test_execute_テスト戦略未定義エラー

        目的: テスト戦略が設計フェーズで決定されていない場合にエラーが返されることを検証
        前提条件:
          - 必須ファイルは存在する
          - metadata.jsonにtest_strategyが含まれていない
        入力: なし
        期待結果:
          - 戻り値: {'success': False, 'output': None, 'error': 'テスト戦略が設計フェーズで決定されていません。Phase 2を先に実行してください。'}
        """
        with patch.object(TestImplementationPhase, '__init__', return_value=None):
            phase = TestImplementationPhase()

            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            phase.metadata = MagicMock()
            phase.metadata.data = {
                'issue_number': 324,
                'design_decisions': {}  # test_strategyが未定義
            }
            phase.metadata.workflow_dir = tmp_path / '.ai-workflow' / 'issue-324'
            phase.metadata.workflow_dir.mkdir(parents=True)

            # 必須ファイルを作成
            requirements_dir = tmp_path / 'issue-324' / '01_requirements' / 'output'
            requirements_dir.mkdir(parents=True)
            (requirements_dir / 'requirements.md').write_text('# 要件定義書', encoding='utf-8')

            design_dir = tmp_path / 'issue-324' / '02_design' / 'output'
            design_dir.mkdir(parents=True)
            (design_dir / 'design.md').write_text('# 詳細設計書', encoding='utf-8')

            test_scenario_dir = tmp_path / 'issue-324' / '03_test_scenario' / 'output'
            test_scenario_dir.mkdir(parents=True)
            (test_scenario_dir / 'test-scenario.md').write_text('# テストシナリオ', encoding='utf-8')

            implementation_dir = tmp_path / 'issue-324' / '04_implementation' / 'output'
            implementation_dir.mkdir(parents=True)
            (implementation_dir / 'implementation.md').write_text('# 実装ログ', encoding='utf-8')

            # execute()を実行
            result = phase.execute()

            # 検証
            assert result['success'] is False
            assert result['output'] is None
            assert 'テスト戦略が設計フェーズで決定されていません' in result['error']

    def test_execute_出力ファイル生成失敗エラー(self, tmp_path):
        """
        テストケース: test_execute_出力ファイル生成失敗エラー

        目的: Claude Agent SDK実行後に出力ファイルが生成されない場合のエラー処理を検証
        前提条件:
          - 必須ファイルは存在する
          - test_strategyは定義されている
          - Claude Agent SDKが実行されるが、test-implementation.mdが生成されない
        入力: なし
        期待結果:
          - 戻り値: {'success': False, 'output': None, 'error': 'test-implementation.mdが生成されませんでした: <パス>'}
        """
        with patch.object(TestImplementationPhase, '__init__', return_value=None):
            phase = TestImplementationPhase()

            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            phase.metadata = MagicMock()
            phase.metadata.data = {
                'issue_number': 324,
                'design_decisions': {
                    'test_strategy': 'UNIT_INTEGRATION',
                    'test_code_strategy': 'CREATE_TEST'
                }
            }
            phase.metadata.workflow_dir = tmp_path / '.ai-workflow' / 'issue-324'
            phase.metadata.workflow_dir.mkdir(parents=True)

            # 必須ファイルを作成
            requirements_dir = tmp_path / 'issue-324' / '01_requirements' / 'output'
            requirements_dir.mkdir(parents=True)
            (requirements_dir / 'requirements.md').write_text('# 要件定義書', encoding='utf-8')

            design_dir = tmp_path / 'issue-324' / '02_design' / 'output'
            design_dir.mkdir(parents=True)
            (design_dir / 'design.md').write_text('# 詳細設計書', encoding='utf-8')

            test_scenario_dir = tmp_path / 'issue-324' / '03_test_scenario' / 'output'
            test_scenario_dir.mkdir(parents=True)
            (test_scenario_dir / 'test-scenario.md').write_text('# テストシナリオ', encoding='utf-8')

            implementation_dir = tmp_path / 'issue-324' / '04_implementation' / 'output'
            implementation_dir.mkdir(parents=True)
            (implementation_dir / 'implementation.md').write_text('# 実装ログ', encoding='utf-8')

            phase.claude = MagicMock()
            phase.claude.working_dir = tmp_path

            phase.load_prompt = MagicMock(return_value='Test prompt')
            phase._get_planning_document_path = MagicMock(return_value='@planning.md')
            phase.execute_with_claude = MagicMock(return_value=[])

            # test-implementation.mdを生成しない（エラーケース）

            # execute()を実行
            result = phase.execute()

            # 検証
            assert result['success'] is False
            assert result['output'] is None
            assert 'test-implementation.mdが生成されませんでした' in result['error']


class TestTestImplementationPhaseReview:
    """TestImplementationPhase.review() のテスト"""

    def test_review_正常系_PASS(self, tmp_path):
        """
        テストケース: test_review_正常系_PASS

        目的: テストコードレビューが正常に実行され、PASSが返されることを検証
        前提条件:
          - execute()が正常に完了している
          - test-implementation.mdが存在する
          - 設計書、テストシナリオ、実装ログが存在する
        入力: なし
        期待結果:
          - 戻り値: {'result': 'PASS', 'feedback': '<フィードバック内容>', 'suggestions': []}
          - review/result.mdが生成される
        """
        with patch.object(TestImplementationPhase, '__init__', return_value=None):
            phase = TestImplementationPhase()

            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            phase.review_dir = tmp_path / 'review'
            phase.review_dir.mkdir()

            # test-implementation.mdを作成
            test_implementation_file = phase.output_dir / 'test-implementation.md'
            test_implementation_file.write_text('# テストコード実装ログ\n\n## 実装内容', encoding='utf-8')

            phase.metadata = MagicMock()
            phase.metadata.data = {
                'issue_number': 324,
                'design_decisions': {
                    'test_strategy': 'UNIT_INTEGRATION',
                    'test_code_strategy': 'CREATE_TEST'
                }
            }
            phase.metadata.workflow_dir = tmp_path / '.ai-workflow' / 'issue-324'

            # 参照ファイルを作成
            design_dir = tmp_path / 'issue-324' / '02_design' / 'output'
            design_dir.mkdir(parents=True)
            (design_dir / 'design.md').write_text('# 詳細設計書', encoding='utf-8')

            test_scenario_dir = tmp_path / 'issue-324' / '03_test_scenario' / 'output'
            test_scenario_dir.mkdir(parents=True)
            (test_scenario_dir / 'test-scenario.md').write_text('# テストシナリオ', encoding='utf-8')

            implementation_dir = tmp_path / 'issue-324' / '04_implementation' / 'output'
            implementation_dir.mkdir(parents=True)
            (implementation_dir / 'implementation.md').write_text('# 実装ログ', encoding='utf-8')

            phase.claude = MagicMock()
            phase.claude.working_dir = tmp_path

            phase.load_prompt = MagicMock(return_value='Review prompt')
            phase.execute_with_claude = MagicMock(return_value=[])
            phase._parse_review_result = MagicMock(return_value={
                'result': 'PASS',
                'feedback': 'テストコードの品質は十分です。',
                'suggestions': []
            })

            # review()を実行
            result = phase.review()

            # 検証
            assert result['result'] == 'PASS'
            assert 'テストコードの品質は十分です' in result['feedback']
            assert result['suggestions'] == []

            # 検証: result.mdが生成された
            assert (phase.review_dir / 'result.md').exists()

    def test_review_正常系_PASS_WITH_SUGGESTIONS(self, tmp_path):
        """
        テストケース: test_review_正常系_PASS_WITH_SUGGESTIONS

        目的: テストコードレビューでPASS_WITH_SUGGESTIONSが返されることを検証
        前提条件:
          - execute()が正常に完了している
          - test-implementation.mdに軽微な改善提案がある
        入力: なし
        期待結果:
          - 戻り値: {'result': 'PASS_WITH_SUGGESTIONS', 'feedback': '<フィードバック>', 'suggestions': ['<提案1>', '<提案2>']}
        """
        with patch.object(TestImplementationPhase, '__init__', return_value=None):
            phase = TestImplementationPhase()

            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            phase.review_dir = tmp_path / 'review'
            phase.review_dir.mkdir()

            test_implementation_file = phase.output_dir / 'test-implementation.md'
            test_implementation_file.write_text('# テストコード実装ログ', encoding='utf-8')

            phase.metadata = MagicMock()
            phase.metadata.data = {
                'issue_number': 324,
                'design_decisions': {
                    'test_strategy': 'UNIT_INTEGRATION',
                    'test_code_strategy': 'CREATE_TEST'
                }
            }
            phase.metadata.workflow_dir = tmp_path / '.ai-workflow' / 'issue-324'

            # 参照ファイルを作成
            design_dir = tmp_path / 'issue-324' / '02_design' / 'output'
            design_dir.mkdir(parents=True)
            (design_dir / 'design.md').write_text('# 詳細設計書', encoding='utf-8')

            test_scenario_dir = tmp_path / 'issue-324' / '03_test_scenario' / 'output'
            test_scenario_dir.mkdir(parents=True)
            (test_scenario_dir / 'test-scenario.md').write_text('# テストシナリオ', encoding='utf-8')

            implementation_dir = tmp_path / 'issue-324' / '04_implementation' / 'output'
            implementation_dir.mkdir(parents=True)
            (implementation_dir / 'implementation.md').write_text('# 実装ログ', encoding='utf-8')

            phase.claude = MagicMock()
            phase.claude.working_dir = tmp_path

            phase.load_prompt = MagicMock(return_value='Review prompt')
            phase.execute_with_claude = MagicMock(return_value=[])
            phase._parse_review_result = MagicMock(return_value={
                'result': 'PASS_WITH_SUGGESTIONS',
                'feedback': 'テストコードは概ね良好ですが、軽微な改善提案があります。',
                'suggestions': ['テストカバレッジを向上させる', 'エッジケースのテストを追加']
            })

            # review()を実行
            result = phase.review()

            # 検証
            assert result['result'] == 'PASS_WITH_SUGGESTIONS'
            assert len(result['suggestions']) == 2
            assert 'テストカバレッジを向上させる' in result['suggestions']

    def test_review_正常系_FAIL(self, tmp_path):
        """
        テストケース: test_review_正常系_FAIL

        目的: テストコードレビューでFAILが返されることを検証
        前提条件:
          - execute()が正常に完了している
          - test-implementation.mdに致命的な問題がある（例: 実コードが変更されている）
        入力: なし
        期待結果:
          - 戻り値: {'result': 'FAIL', 'feedback': '<フィードバック>', 'suggestions': ['<修正提案1>', '<修正提案2>']}
        """
        with patch.object(TestImplementationPhase, '__init__', return_value=None):
            phase = TestImplementationPhase()

            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            phase.review_dir = tmp_path / 'review'
            phase.review_dir.mkdir()

            test_implementation_file = phase.output_dir / 'test-implementation.md'
            test_implementation_file.write_text('# テストコード実装ログ（実コード変更あり）', encoding='utf-8')

            phase.metadata = MagicMock()
            phase.metadata.data = {
                'issue_number': 324,
                'design_decisions': {
                    'test_strategy': 'UNIT_INTEGRATION',
                    'test_code_strategy': 'CREATE_TEST'
                }
            }
            phase.metadata.workflow_dir = tmp_path / '.ai-workflow' / 'issue-324'

            # 参照ファイルを作成
            design_dir = tmp_path / 'issue-324' / '02_design' / 'output'
            design_dir.mkdir(parents=True)
            (design_dir / 'design.md').write_text('# 詳細設計書', encoding='utf-8')

            test_scenario_dir = tmp_path / 'issue-324' / '03_test_scenario' / 'output'
            test_scenario_dir.mkdir(parents=True)
            (test_scenario_dir / 'test-scenario.md').write_text('# テストシナリオ', encoding='utf-8')

            implementation_dir = tmp_path / 'issue-324' / '04_implementation' / 'output'
            implementation_dir.mkdir(parents=True)
            (implementation_dir / 'implementation.md').write_text('# 実装ログ', encoding='utf-8')

            phase.claude = MagicMock()
            phase.claude.working_dir = tmp_path

            phase.load_prompt = MagicMock(return_value='Review prompt')
            phase.execute_with_claude = MagicMock(return_value=[])
            phase._parse_review_result = MagicMock(return_value={
                'result': 'FAIL',
                'feedback': '実コードが変更されています。Phase 5ではテストコードのみを実装してください。',
                'suggestions': ['実コード変更を削除する', 'テストコードのみを実装する']
            })

            # review()を実行
            result = phase.review()

            # 検証
            assert result['result'] == 'FAIL'
            assert '実コードが変更されています' in result['feedback']
            assert len(result['suggestions']) == 2

    def test_review_出力ファイル不在エラー(self, tmp_path):
        """
        テストケース: test_review_出力ファイル不在エラー

        目的: test-implementation.mdが存在しない場合にエラーが返されることを検証
        前提条件:
          - test-implementation.mdが存在しない
        入力: なし
        期待結果:
          - 戻り値: {'result': 'FAIL', 'feedback': 'test-implementation.mdが存在しません。', 'suggestions': [...]}
        """
        with patch.object(TestImplementationPhase, '__init__', return_value=None):
            phase = TestImplementationPhase()

            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            phase.metadata = MagicMock()
            phase.metadata.data = {'issue_number': 324}

            # test-implementation.mdを作成しない

            # review()を実行
            result = phase.review()

            # 検証
            assert result['result'] == 'FAIL'
            assert 'test-implementation.mdが存在しません' in result['feedback']
            assert len(result['suggestions']) > 0


class TestTestImplementationPhaseRevise:
    """TestImplementationPhase.revise() のテスト"""

    def test_revise_正常系(self, tmp_path):
        """
        テストケース: test_revise_正常系

        目的: レビューフィードバックに基づいてテストコードが修正されることを検証
        前提条件:
          - review()が実行され、FAILが返されている
          - review_feedbackが提供されている
        入力:
          - review_feedback="実コードの変更を削除してください。テストコードのみを実装してください。"
        期待結果:
          - 戻り値: {'success': True, 'output': '<test-implementation.mdのパス>', 'error': None}
          - test-implementation.mdが更新される
        """
        with patch.object(TestImplementationPhase, '__init__', return_value=None):
            phase = TestImplementationPhase()

            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            # test-implementation.mdを作成
            test_implementation_file = phase.output_dir / 'test-implementation.md'
            test_implementation_file.write_text('# テストコード実装ログ（修正前）', encoding='utf-8')

            phase.metadata = MagicMock()
            phase.metadata.data = {
                'issue_number': 324,
                'design_decisions': {
                    'test_strategy': 'UNIT_INTEGRATION',
                    'test_code_strategy': 'CREATE_TEST'
                }
            }
            phase.metadata.workflow_dir = tmp_path / '.ai-workflow' / 'issue-324'

            # 参照ファイルを作成
            design_dir = tmp_path / 'issue-324' / '02_design' / 'output'
            design_dir.mkdir(parents=True)
            (design_dir / 'design.md').write_text('# 詳細設計書', encoding='utf-8')

            test_scenario_dir = tmp_path / 'issue-324' / '03_test_scenario' / 'output'
            test_scenario_dir.mkdir(parents=True)
            (test_scenario_dir / 'test-scenario.md').write_text('# テストシナリオ', encoding='utf-8')

            implementation_dir = tmp_path / 'issue-324' / '04_implementation' / 'output'
            implementation_dir.mkdir(parents=True)
            (implementation_dir / 'implementation.md').write_text('# 実装ログ', encoding='utf-8')

            phase.claude = MagicMock()
            phase.claude.working_dir = tmp_path

            phase.load_prompt = MagicMock(return_value='Revise prompt {review_feedback}')
            phase.execute_with_claude = MagicMock(return_value=[])

            # 修正後のファイルを作成（execute_with_claude実行後に更新される想定）
            test_implementation_file.write_text('# テストコード実装ログ（修正後）', encoding='utf-8')

            # revise()を実行
            review_feedback = "実コードの変更を削除してください。テストコードのみを実装してください。"
            result = phase.revise(review_feedback)

            # 検証
            assert result['success'] is True
            assert result['error'] is None
            assert 'test-implementation.md' in result['output']

            # 検証: execute_with_claudeが呼ばれた
            phase.execute_with_claude.assert_called_once()

    def test_revise_出力ファイル不在エラー(self, tmp_path):
        """
        テストケース: test_revise_出力ファイル不在エラー

        目的: 元のtest-implementation.mdが存在しない場合にエラーが返されることを検証
        前提条件:
          - test-implementation.mdが存在しない
        入力:
          - review_feedback="修正してください"
        期待結果:
          - 戻り値: {'success': False, 'output': None, 'error': 'test-implementation.mdが存在しません。'}
        """
        with patch.object(TestImplementationPhase, '__init__', return_value=None):
            phase = TestImplementationPhase()

            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            phase.metadata = MagicMock()
            phase.metadata.data = {'issue_number': 324}

            # test-implementation.mdを作成しない

            # revise()を実行
            result = phase.revise("修正してください")

            # 検証
            assert result['success'] is False
            assert result['output'] is None
            assert 'test-implementation.mdが存在しません' in result['error']

    def test_revise_修正後ファイル生成失敗エラー(self, tmp_path):
        """
        テストケース: test_revise_修正後ファイル生成失敗エラー

        目的: Claude Agent SDK実行後に修正されたファイルが生成されない場合のエラー処理を検証
        前提条件:
          - 元のtest-implementation.mdは存在する
          - Claude Agent SDKが実行されるが、修正後のファイルが生成されない
        入力:
          - review_feedback="修正してください"
        期待結果:
          - 戻り値: {'success': False, 'output': None, 'error': '修正されたtest-implementation.mdが生成されませんでした。'}
        """
        with patch.object(TestImplementationPhase, '__init__', return_value=None):
            phase = TestImplementationPhase()

            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            # test-implementation.mdを作成
            test_implementation_file = phase.output_dir / 'test-implementation.md'
            test_implementation_file.write_text('# テストコード実装ログ', encoding='utf-8')

            phase.metadata = MagicMock()
            phase.metadata.data = {
                'issue_number': 324,
                'design_decisions': {
                    'test_strategy': 'UNIT_INTEGRATION',
                    'test_code_strategy': 'CREATE_TEST'
                }
            }
            phase.metadata.workflow_dir = tmp_path / '.ai-workflow' / 'issue-324'

            # 参照ファイルを作成
            design_dir = tmp_path / 'issue-324' / '02_design' / 'output'
            design_dir.mkdir(parents=True)
            (design_dir / 'design.md').write_text('# 詳細設計書', encoding='utf-8')

            test_scenario_dir = tmp_path / 'issue-324' / '03_test_scenario' / 'output'
            test_scenario_dir.mkdir(parents=True)
            (test_scenario_dir / 'test-scenario.md').write_text('# テストシナリオ', encoding='utf-8')

            implementation_dir = tmp_path / 'issue-324' / '04_implementation' / 'output'
            implementation_dir.mkdir(parents=True)
            (implementation_dir / 'implementation.md').write_text('# 実装ログ', encoding='utf-8')

            phase.claude = MagicMock()
            phase.claude.working_dir = tmp_path

            phase.load_prompt = MagicMock(return_value='Revise prompt')
            phase.execute_with_claude = MagicMock(return_value=[])

            # 修正後のファイルを削除（生成失敗をシミュレート）
            test_implementation_file.unlink()

            # revise()を実行
            result = phase.revise("修正してください")

            # 検証
            assert result['success'] is False
            assert result['output'] is None
            assert '修正されたtest-implementation.mdが生成されませんでした' in result['error']


class TestTestImplementationPhasePostOutput:
    """TestImplementationPhase.execute() の成果物投稿テスト"""

    def test_test_implementation_execute_正常系_成果物投稿成功(self, tmp_path):
        """
        テストケース: test_implementation_execute_正常系_成果物投稿成功

        目的: Phase 5が正常に完了した場合、成果物がGitHub Issueに投稿されることを検証
        """
        with patch.object(TestImplementationPhase, '__init__', return_value=None):
            phase = TestImplementationPhase()

            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            phase.metadata = MagicMock()
            phase.metadata.data = {
                'issue_number': 324,
                'design_decisions': {
                    'test_strategy': 'UNIT_INTEGRATION',
                    'test_code_strategy': 'CREATE_TEST'
                }
            }
            phase.metadata.workflow_dir = tmp_path / '.ai-workflow' / 'issue-324'
            phase.metadata.workflow_dir.mkdir(parents=True)

            # 必須ファイルを作成
            requirements_dir = tmp_path / 'issue-324' / '01_requirements' / 'output'
            requirements_dir.mkdir(parents=True)
            (requirements_dir / 'requirements.md').write_text('# 要件定義書', encoding='utf-8')

            design_dir = tmp_path / 'issue-324' / '02_design' / 'output'
            design_dir.mkdir(parents=True)
            (design_dir / 'design.md').write_text('# 詳細設計書', encoding='utf-8')

            test_scenario_dir = tmp_path / 'issue-324' / '03_test_scenario' / 'output'
            test_scenario_dir.mkdir(parents=True)
            (test_scenario_dir / 'test-scenario.md').write_text('# テストシナリオ', encoding='utf-8')

            implementation_dir = tmp_path / 'issue-324' / '04_implementation' / 'output'
            implementation_dir.mkdir(parents=True)
            (implementation_dir / 'implementation.md').write_text('# 実装ログ', encoding='utf-8')

            phase.claude = MagicMock()
            phase.claude.working_dir = tmp_path

            phase.load_prompt = MagicMock(return_value='Test prompt')
            phase._get_planning_document_path = MagicMock(return_value='@planning.md')
            phase.execute_with_claude = MagicMock(return_value=[])

            # test-implementation.mdを作成
            test_implementation_file = phase.output_dir / 'test-implementation.md'
            test_implementation_file.write_text('# テストコード実装ログ\n\n## 実装内容', encoding='utf-8')

            with patch.object(BasePhase, 'post_output') as mock_post_output:
                # execute()を実行
                result = phase.execute()

                # 検証: post_output()が呼ばれた
                mock_post_output.assert_called_once()

                # 検証: 引数が正しい
                args, kwargs = mock_post_output.call_args
                assert kwargs['title'] == "テストコード実装ログ"
                assert 'テストコード実装ログ' in kwargs['output_content']

                # 検証: execute()が成功を返す
                assert result['success'] is True

    def test_test_implementation_execute_異常系_GitHub投稿失敗(self, tmp_path):
        """
        テストケース: test_implementation_execute_異常系_GitHub投稿失敗

        目的: GitHub API投稿失敗時でもワークフローが継続することを検証
        """
        with patch.object(TestImplementationPhase, '__init__', return_value=None):
            phase = TestImplementationPhase()

            phase.output_dir = tmp_path / 'output'
            phase.output_dir.mkdir()

            phase.metadata = MagicMock()
            phase.metadata.data = {
                'issue_number': 324,
                'design_decisions': {
                    'test_strategy': 'UNIT_INTEGRATION',
                    'test_code_strategy': 'CREATE_TEST'
                }
            }
            phase.metadata.workflow_dir = tmp_path / '.ai-workflow' / 'issue-324'
            phase.metadata.workflow_dir.mkdir(parents=True)

            # 必須ファイルを作成
            requirements_dir = tmp_path / 'issue-324' / '01_requirements' / 'output'
            requirements_dir.mkdir(parents=True)
            (requirements_dir / 'requirements.md').write_text('# 要件定義書', encoding='utf-8')

            design_dir = tmp_path / 'issue-324' / '02_design' / 'output'
            design_dir.mkdir(parents=True)
            (design_dir / 'design.md').write_text('# 詳細設計書', encoding='utf-8')

            test_scenario_dir = tmp_path / 'issue-324' / '03_test_scenario' / 'output'
            test_scenario_dir.mkdir(parents=True)
            (test_scenario_dir / 'test-scenario.md').write_text('# テストシナリオ', encoding='utf-8')

            implementation_dir = tmp_path / 'issue-324' / '04_implementation' / 'output'
            implementation_dir.mkdir(parents=True)
            (implementation_dir / 'implementation.md').write_text('# 実装ログ', encoding='utf-8')

            phase.claude = MagicMock()
            phase.claude.working_dir = tmp_path

            phase.load_prompt = MagicMock(return_value='Test prompt')
            phase._get_planning_document_path = MagicMock(return_value='@planning.md')
            phase.execute_with_claude = MagicMock(return_value=[])

            # test-implementation.mdを作成
            test_implementation_file = phase.output_dir / 'test-implementation.md'
            test_implementation_file.write_text('# テストコード実装ログ', encoding='utf-8')

            # post_output()が例外をスロー
            with patch.object(BasePhase, 'post_output', side_effect=Exception("GitHub API Error")):
                with patch('builtins.print') as mock_print:
                    # execute()を実行
                    result = phase.execute()

                    # 検証: WARNINGログが出力された
                    warning_calls = [str(call_args) for call_args in mock_print.call_args_list]
                    assert any('[WARNING] 成果物のGitHub投稿に失敗しました' in str(call_str) for call_str in warning_calls)

                    # 検証: execute()が成功を返す（ワークフロー継続）
                    assert result['success'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
