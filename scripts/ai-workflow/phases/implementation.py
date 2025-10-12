"""Phase 4: 実装フェーズ

設計書とテストシナリオに基づいて、実際のコード実装を行う。
Claude Agent SDKを使用して、コード生成・編集を実行する。
"""
import re
from pathlib import Path
from typing import Dict, Any, List
from .base_phase import BasePhase


class ImplementationPhase(BasePhase):
    """実装フェーズ"""

    def __init__(self, *args, **kwargs):
        """初期化"""
        super().__init__(
            phase_name='implementation',
            *args,
            **kwargs
        )

    def execute(self) -> Dict[str, Any]:
        """
        実装フェーズを実行

        Returns:
            Dict[str, Any]: 実行結果
                - success: bool
                - output: str - implementation.mdのパス
                - error: Optional[str]
        """
        try:
            # Issue情報を取得
            issue_number = int(self.metadata.data['issue_number'])

            # 要件定義書、設計書、テストシナリオを読み込み
            requirements_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '01_requirements' / 'output' / 'requirements.md'
            design_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '02_design' / 'output' / 'design.md'
            test_scenario_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '03_test_scenario' / 'output' / 'test-scenario.md'

            if not requirements_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': f'要件定義書が見つかりません: {requirements_file}'
                }

            if not design_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': f'設計書が見つかりません: {design_file}'
                }

            if not test_scenario_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': f'テストシナリオが見つかりません: {test_scenario_file}'
                }

            # 実装戦略を取得（Phase 2で決定済み）
            implementation_strategy = self.metadata.data['design_decisions'].get('implementation_strategy')

            if not implementation_strategy:
                return {
                    'success': False,
                    'output': None,
                    'error': '実装戦略が設計フェーズで決定されていません。Phase 2を先に実行してください。'
                }

            # Planning Phase成果物のパス取得
            planning_path_str = self._get_planning_document_path(issue_number)

            # 実行プロンプトを読み込み
            execute_prompt_template = self.load_prompt('execute')

            # working_dirからの相対パスを使用
            rel_path_requirements = requirements_file.relative_to(self.claude.working_dir)
            rel_path_design = design_file.relative_to(self.claude.working_dir)
            rel_path_test_scenario = test_scenario_file.relative_to(self.claude.working_dir)

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
                '{implementation_strategy}',
                implementation_strategy
            ).replace(
                '{issue_number}',
                str(issue_number)
            )

            # Claude Agent SDKでタスクを実行
            # 実装フェーズは時間がかかる可能性があるため、max_turnsを多めに
            # 大規模リファクタリング（Issue #376等）では150ターンに設定
            messages = self.execute_with_claude(
                prompt=execute_prompt,
                max_turns=150,
                log_prefix='execute'
            )

            # implementation.mdのパスを取得
            output_file = self.output_dir / 'implementation.md'

            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': f'implementation.mdが生成されませんでした: {output_file}'
                }

            # GitHub Issueに成果物を投稿
            try:
                output_content = output_file.read_text(encoding='utf-8')
                self.post_output(
                    output_content=output_content,
                    title="実装ログ"
                )
            except Exception as e:
                print(f"[WARNING] 成果物のGitHub投稿に失敗しました: {e}")

            # ステータス更新: BasePhase.run()で実行されるため不要
            # self.metadata.update_phase_status('implementation', 'completed', str(output_file))
            # self.post_progress('completed', f'実装が完了しました: {output_file.name}')

            return {
                'success': True,
                'output': str(output_file),
                'error': None
            }

        except Exception as e:
            # ステータス更新: 失敗
            self.metadata.update_phase_status('implementation', 'failed')
            # BasePhase.run()で実行されるため不要
            # self.post_progress('failed', f'実装が失敗しました: {str(e)}')

            return {
                'success': False,
                'output': None,
                'error': str(e)
            }

    def review(self) -> Dict[str, Any]:
        """
        実装をレビュー

        Returns:
            Dict[str, Any]: レビュー結果
                - result: str - PASS/PASS_WITH_SUGGESTIONS/FAIL
                - feedback: str
                - suggestions: List[str]
        """
        try:
            # implementation.mdを読み込み
            implementation_file = self.output_dir / 'implementation.md'

            if not implementation_file.exists():
                return {
                    'result': 'FAIL',
                    'feedback': 'implementation.mdが存在しません。',
                    'suggestions': ['execute()を実行してimplementation.mdを生成してください。']
                }

            # 設計書とテストシナリオのパス
            issue_number = int(self.metadata.data['issue_number'])
            design_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '02_design' / 'output' / 'design.md'
            test_scenario_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '03_test_scenario' / 'output' / 'test-scenario.md'

            # 実装戦略を取得（Noneの場合もUNKNOWNを使用）
            implementation_strategy = self.metadata.data['design_decisions'].get('implementation_strategy') or 'UNKNOWN'

            # レビュープロンプトを読み込み
            review_prompt_template = self.load_prompt('review')

            # working_dirからの相対パスを使用
            rel_path_implementation = implementation_file.relative_to(self.claude.working_dir)
            rel_path_design = design_file.relative_to(self.claude.working_dir)
            rel_path_test_scenario = test_scenario_file.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            review_prompt = review_prompt_template.replace(
                '{implementation_document_path}',
                f'@{rel_path_implementation}'
            ).replace(
                '{design_document_path}',
                f'@{rel_path_design}'
            ).replace(
                '{test_scenario_document_path}',
                f'@{rel_path_test_scenario}'
            ).replace(
                '{implementation_strategy}',
                implementation_strategy
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

            # GitHub Issueにレビュー結果を投稿: BasePhase.run()で実行されるため不要
            # self.post_review(
            #     result=review_result['result'],
            #     feedback=review_result['feedback'],
            #     suggestions=review_result.get('suggestions')
            # )

            return review_result

        except Exception as e:
            return {
                'result': 'FAIL',
                'feedback': f'レビュー中にエラーが発生しました: {str(e)}',
                'suggestions': []
            }

    def revise(self, review_feedback: str) -> Dict[str, Any]:
        """
        レビュー結果を元に実装を修正

        Args:
            review_feedback: レビュー結果のフィードバック

        Returns:
            Dict[str, Any]: 修正結果
                - success: bool
                - output: str - implementation.mdのパス
                - error: Optional[str]
        """
        try:
            # 元の実装ログを読み込み
            implementation_file = self.output_dir / 'implementation.md'

            if not implementation_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': 'implementation.mdが存在しません。'
                }

            # 設計書とテストシナリオのパス
            issue_number = int(self.metadata.data['issue_number'])
            design_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '02_design' / 'output' / 'design.md'
            test_scenario_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '03_test_scenario' / 'output' / 'test-scenario.md'

            # 実装戦略を取得（Noneの場合もUNKNOWNを使用）
            implementation_strategy = self.metadata.data['design_decisions'].get('implementation_strategy') or 'UNKNOWN'

            # 修正プロンプトを読み込み
            revise_prompt_template = self.load_prompt('revise')

            # working_dirからの相対パスを使用
            rel_path_implementation = implementation_file.relative_to(self.claude.working_dir)
            rel_path_design = design_file.relative_to(self.claude.working_dir)
            rel_path_test_scenario = test_scenario_file.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            revise_prompt = revise_prompt_template.replace(
                '{implementation_document_path}',
                f'@{rel_path_implementation}'
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
                '{implementation_strategy}',
                implementation_strategy
            ).replace(
                '{issue_number}',
                str(issue_number)
            )

            # Claude Agent SDKでタスクを実行
            # 大規模リファクタリング（Issue #376等）では150ターンに設定
            messages = self.execute_with_claude(
                prompt=revise_prompt,
                max_turns=150,
                log_prefix='revise'
            )

            # implementation.mdのパスを取得
            output_file = self.output_dir / 'implementation.md'

            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': '修正されたimplementation.mdが生成されませんでした。'
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
