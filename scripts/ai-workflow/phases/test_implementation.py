"""Phase 5: テストコード実装フェーズ

Phase 3で作成されたテストシナリオとPhase 4で実装された実コードを基に、
テストコードのみを実装する。実コードの修正は行わない。
"""
import re
from pathlib import Path
from typing import Dict, Any, List
from .base_phase import BasePhase


class TestImplementationPhase(BasePhase):
    """テストコード実装フェーズ"""

    def __init__(self, *args, **kwargs):
        """初期化"""
        super().__init__(
            phase_name='test_implementation',
            *args,
            **kwargs
        )

    def execute(self) -> Dict[str, Any]:
        """
        テストコード実装フェーズを実行

        Returns:
            Dict[str, Any]: 実行結果
                - success: bool
                - output: str - test-implementation.mdのパス
                - error: Optional[str]
        """
        try:
            # Issue情報を取得
            issue_number = int(self.metadata.data['issue_number'])

            # 要件定義書、設計書、テストシナリオ、実装ログを読み込み
            requirements_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '01_requirements' / 'output' / 'requirements.md'
            design_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '02_design' / 'output' / 'design.md'
            test_scenario_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '03_test_scenario' / 'output' / 'test-scenario.md'
            implementation_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '04_implementation' / 'output' / 'implementation.md'

            # ファイル存在確認
            missing_files = []
            if not requirements_file.exists():
                missing_files.append(f'要件定義書: {requirements_file}')
            if not design_file.exists():
                missing_files.append(f'設計書: {design_file}')
            if not test_scenario_file.exists():
                missing_files.append(f'テストシナリオ: {test_scenario_file}')
            if not implementation_file.exists():
                missing_files.append(f'実装ログ: {implementation_file}')

            if missing_files:
                return {
                    'success': False,
                    'output': None,
                    'error': f'必要なファイルが見つかりません:\n' + '\n'.join(missing_files)
                }

            # テスト戦略を取得（Phase 2で決定済み）
            test_strategy = self.metadata.data['design_decisions'].get('test_strategy')
            test_code_strategy = self.metadata.data['design_decisions'].get('test_code_strategy')

            if not test_strategy or not test_code_strategy:
                return {
                    'success': False,
                    'output': None,
                    'error': 'テスト戦略が設計フェーズで決定されていません。Phase 2を先に実行してください。'
                }

            # Planning Phase成果物のパス取得
            planning_path_str = self._get_planning_document_path(issue_number)

            # 実行プロンプトを読み込み
            execute_prompt_template = self.load_prompt('execute')

            # working_dirからの相対パスを使用
            rel_path_requirements = requirements_file.relative_to(self.claude.working_dir)
            rel_path_design = design_file.relative_to(self.claude.working_dir)
            rel_path_test_scenario = test_scenario_file.relative_to(self.claude.working_dir)
            rel_path_implementation = implementation_file.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            execute_prompt = execute_prompt_template.replace(
                '{planning_document_path}',
                planning_path_str
            ).replace(
                '{requirements_document_path}',
                f'@{rel_path_requirements}'
            ).replace(
                '{design_document_path}',
                f'@{rel_path_design}'
            ).replace(
                '{test_scenario_document_path}',
                f'@{rel_path_test_scenario}'
            ).replace(
                '{implementation_document_path}',
                f'@{rel_path_implementation}'
            ).replace(
                '{test_strategy}',
                test_strategy
            ).replace(
                '{test_code_strategy}',
                test_code_strategy
            ).replace(
                '{issue_number}',
                str(issue_number)
            )

            # Claude Agent SDKでタスクを実行
            # テスト実装フェーズは時間がかかる可能性があるため、max_turnsを多めに
            messages = self.execute_with_claude(
                prompt=execute_prompt,
                max_turns=50,
                log_prefix='execute'
            )

            # test-implementation.mdのパスを取得
            output_file = self.output_dir / 'test-implementation.md'

            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': f'test-implementation.mdが生成されませんでした: {output_file}'
                }

            # GitHub Issueに成果物を投稿
            try:
                output_content = output_file.read_text(encoding='utf-8')
                self.post_output(
                    output_content=output_content,
                    title="テストコード実装ログ"
                )
            except Exception as e:
                print(f"[WARNING] 成果物のGitHub投稿に失敗しました: {e}")

            return {
                'success': True,
                'output': str(output_file),
                'error': None
            }

        except Exception as e:
            # ステータス更新: 失敗
            self.metadata.update_phase_status('test_implementation', 'failed')

            return {
                'success': False,
                'output': None,
                'error': str(e)
            }

    def review(self) -> Dict[str, Any]:
        """
        テストコード実装をレビュー

        Returns:
            Dict[str, Any]: レビュー結果
                - result: str - PASS/PASS_WITH_SUGGESTIONS/FAIL
                - feedback: str
                - suggestions: List[str]
        """
        try:
            # test-implementation.mdを読み込み
            test_implementation_file = self.output_dir / 'test-implementation.md'

            if not test_implementation_file.exists():
                return {
                    'result': 'FAIL',
                    'feedback': 'test-implementation.mdが存在しません。',
                    'suggestions': ['execute()を実行してtest-implementation.mdを生成してください。']
                }

            # 設計書、テストシナリオ、実装ログのパス
            issue_number = int(self.metadata.data['issue_number'])
            design_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '02_design' / 'output' / 'design.md'
            test_scenario_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '03_test_scenario' / 'output' / 'test-scenario.md'
            implementation_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '04_implementation' / 'output' / 'implementation.md'

            # テスト戦略を取得
            test_strategy = self.metadata.data['design_decisions'].get('test_strategy', 'UNKNOWN')
            test_code_strategy = self.metadata.data['design_decisions'].get('test_code_strategy', 'UNKNOWN')

            # レビュープロンプトを読み込み
            review_prompt_template = self.load_prompt('review')

            # working_dirからの相対パスを使用
            rel_path_test_implementation = test_implementation_file.relative_to(self.claude.working_dir)
            rel_path_design = design_file.relative_to(self.claude.working_dir)
            rel_path_test_scenario = test_scenario_file.relative_to(self.claude.working_dir)
            rel_path_implementation = implementation_file.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            review_prompt = review_prompt_template.replace(
                '{test_implementation_document_path}',
                f'@{rel_path_test_implementation}'
            ).replace(
                '{design_document_path}',
                f'@{rel_path_design}'
            ).replace(
                '{test_scenario_document_path}',
                f'@{rel_path_test_scenario}'
            ).replace(
                '{implementation_document_path}',
                f'@{rel_path_implementation}'
            ).replace(
                '{test_strategy}',
                test_strategy
            ).replace(
                '{test_code_strategy}',
                test_code_strategy
            )

            # Claude Agent SDKでレビューを実行
            messages = self.execute_with_claude(
                prompt=review_prompt,
                max_turns=30,
                log_prefix='review'
            )

            # レビュー結果をパース
            review_result = self._parse_review_result(messages)

            # レビュー結果をファイルに保存
            review_file = self.review_dir / 'result.md'
            review_file.write_text(review_result['feedback'], encoding='utf-8')
            print(f"[INFO] レビュー結果を保存: {review_file}")

            return review_result

        except Exception as e:
            return {
                'result': 'FAIL',
                'feedback': f'レビュー中にエラーが発生しました: {str(e)}',
                'suggestions': []
            }

    def revise(self, review_feedback: str) -> Dict[str, Any]:
        """
        レビュー結果を元にテストコードを修正

        Args:
            review_feedback: レビュー結果のフィードバック

        Returns:
            Dict[str, Any]: 修正結果
                - success: bool
                - output: str - test-implementation.mdのパス
                - error: Optional[str]
        """
        try:
            # 元のテスト実装ログを読み込み
            test_implementation_file = self.output_dir / 'test-implementation.md'

            if not test_implementation_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': 'test-implementation.mdが存在しません。'
                }

            # 設計書、テストシナリオ、実装ログのパス
            issue_number = int(self.metadata.data['issue_number'])
            design_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '02_design' / 'output' / 'design.md'
            test_scenario_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '03_test_scenario' / 'output' / 'test-scenario.md'
            implementation_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '04_implementation' / 'output' / 'implementation.md'

            # テスト戦略を取得
            test_strategy = self.metadata.data['design_decisions'].get('test_strategy', 'UNKNOWN')
            test_code_strategy = self.metadata.data['design_decisions'].get('test_code_strategy', 'UNKNOWN')

            # 修正プロンプトを読み込み
            revise_prompt_template = self.load_prompt('revise')

            # working_dirからの相対パスを使用
            rel_path_test_implementation = test_implementation_file.relative_to(self.claude.working_dir)
            rel_path_design = design_file.relative_to(self.claude.working_dir)
            rel_path_test_scenario = test_scenario_file.relative_to(self.claude.working_dir)
            rel_path_implementation = implementation_file.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            revise_prompt = revise_prompt_template.replace(
                '{test_implementation_document_path}',
                f'@{rel_path_test_implementation}'
            ).replace(
                '{review_feedback}',
                review_feedback
            ).replace(
                '{design_document_path}',
                f'@{rel_path_design}'
            ).replace(
                '{test_scenario_document_path}',
                f'@{rel_path_test_scenario}'
            ).replace(
                '{implementation_document_path}',
                f'@{rel_path_implementation}'
            ).replace(
                '{test_strategy}',
                test_strategy
            ).replace(
                '{test_code_strategy}',
                test_code_strategy
            ).replace(
                '{issue_number}',
                str(issue_number)
            )

            # Claude Agent SDKでタスクを実行
            messages = self.execute_with_claude(
                prompt=revise_prompt,
                max_turns=50,
                log_prefix='revise'
            )

            # test-implementation.mdのパスを取得
            output_file = self.output_dir / 'test-implementation.md'

            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': '修正されたtest-implementation.mdが生成されませんでした。'
                }

            return {
                'success': True,
                'output': str(output_file),
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'output': None,
                'error': str(e)
            }
