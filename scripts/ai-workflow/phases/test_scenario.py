"""Phase 3: テストシナリオフェーズ

要件定義書と設計書から、Phase 2で決定されたテスト戦略に基づいて
テストシナリオを作成する。
"""
import re
from pathlib import Path
from typing import Dict, Any, List
from .base_phase import BasePhase


class TestScenarioPhase(BasePhase):
    """テストシナリオフェーズ"""

    def __init__(self, *args, **kwargs):
        """初期化"""
        super().__init__(
            phase_name='test_scenario',
            *args,
            **kwargs
        )

    def execute(self) -> Dict[str, Any]:
        """
        テストシナリオフェーズを実行

        Returns:
            Dict[str, Any]: 実行結果
                - success: bool
                - output: str - test-scenario.mdのパス
                - error: Optional[str]
        """
        try:
            # Issue情報を取得
            issue_number = int(self.metadata.data['issue_number'])
            issue_info = self.github.get_issue_info(issue_number)
            issue_info_text = self._format_issue_info(issue_info)

            # 要件定義書と設計書を読み込み
            requirements_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '01_requirements' / 'output' / 'requirements.md'
            design_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '02_design' / 'output' / 'design.md'

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

            # テスト戦略を取得（Phase 2で決定済み）
            test_strategy = self.metadata.data['design_decisions'].get('test_strategy')

            if not test_strategy:
                return {
                    'success': False,
                    'output': None,
                    'error': 'テスト戦略が設計フェーズで決定されていません。Phase 2を先に実行してください。'
                }

            # 実行プロンプトを読み込み
            execute_prompt_template = self.load_prompt('execute')

            # working_dirからの相対パスを使用
            rel_path_requirements = requirements_file.relative_to(self.claude.working_dir)
            rel_path_design = design_file.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            execute_prompt = execute_prompt_template.replace(
                '{requirements_document_path}',
                f'@{rel_path_requirements}'
            ).replace(
                '{design_document_path}',
                f'@{rel_path_design}'
            ).replace(
                '{test_strategy}',
                test_strategy
            ).replace(
                '{issue_info}',
                issue_info_text
            ).replace(
                '{issue_number}',
                str(issue_number)
            )

            # Claude Agent SDKでタスクを実行
            messages = self.execute_with_claude(
                prompt=execute_prompt,
                max_turns=40,
                log_prefix='execute'
            )

            # test-scenario.mdのパスを取得
            output_file = self.output_dir / 'test-scenario.md'

            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': f'test-scenario.mdが生成されませんでした: {output_file}'
                }

            # ステータス更新: BasePhase.run()で実行されるため不要
            # self.metadata.update_phase_status('test_scenario', 'completed', str(output_file))
            # self.post_progress('completed', f'テストシナリオが完了しました: {output_file.name}')

            return {
                'success': True,
                'output': str(output_file),
                'error': None
            }

        except Exception as e:
            # ステータス更新: 失敗
            self.metadata.update_phase_status('test_scenario', 'failed')
            # BasePhase.run()で実行されるため不要
            # self.post_progress('failed', f'テストシナリオが失敗しました: {str(e)}')

            return {
                'success': False,
                'output': None,
                'error': str(e)
            }

    def review(self) -> Dict[str, Any]:
        """
        テストシナリオをレビュー

        Returns:
            Dict[str, Any]: レビュー結果
                - result: str - PASS/PASS_WITH_SUGGESTIONS/FAIL
                - feedback: str
                - suggestions: List[str]
        """
        try:
            # test-scenario.mdを読み込み
            test_scenario_file = self.output_dir / 'test-scenario.md'

            if not test_scenario_file.exists():
                return {
                    'result': 'FAIL',
                    'feedback': 'test-scenario.mdが存在しません。',
                    'suggestions': ['execute()を実行してtest-scenario.mdを生成してください。']
                }

            # 要件定義書と設計書のパス
            issue_number = int(self.metadata.data['issue_number'])
            requirements_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '01_requirements' / 'output' / 'requirements.md'
            design_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '02_design' / 'output' / 'design.md'

            # テスト戦略を取得
            test_strategy = self.metadata.data['design_decisions'].get('test_strategy', 'UNKNOWN')

            # レビュープロンプトを読み込み
            review_prompt_template = self.load_prompt('review')

            # working_dirからの相対パスを使用
            rel_path_test_scenario = test_scenario_file.relative_to(self.claude.working_dir)
            rel_path_design = design_file.relative_to(self.claude.working_dir)
            rel_path_requirements = requirements_file.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            review_prompt = review_prompt_template.replace(
                '{test_scenario_document_path}',
                f'@{rel_path_test_scenario}'
            ).replace(
                '{design_document_path}',
                f'@{rel_path_design}'
            ).replace(
                '{requirements_document_path}',
                f'@{rel_path_requirements}'
            ).replace(
                '{test_strategy}',
                test_strategy
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
        レビュー結果を元にテストシナリオを修正

        Args:
            review_feedback: レビュー結果のフィードバック

        Returns:
            Dict[str, Any]: 修正結果
                - success: bool
                - output: str - test-scenario.mdのパス
                - error: Optional[str]
        """
        try:
            # 元のテストシナリオを読み込み
            test_scenario_file = self.output_dir / 'test-scenario.md'

            if not test_scenario_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': 'test-scenario.mdが存在しません。'
                }

            # 要件定義書と設計書のパス
            issue_number = int(self.metadata.data['issue_number'])
            requirements_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '01_requirements' / 'output' / 'requirements.md'
            design_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '02_design' / 'output' / 'design.md'

            # テスト戦略を取得
            test_strategy = self.metadata.data['design_decisions'].get('test_strategy', 'UNKNOWN')

            # 修正プロンプトを読み込み
            revise_prompt_template = self.load_prompt('revise')

            # working_dirからの相対パスを使用
            rel_path_test_scenario = test_scenario_file.relative_to(self.claude.working_dir)
            rel_path_design = design_file.relative_to(self.claude.working_dir)
            rel_path_requirements = requirements_file.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            revise_prompt = revise_prompt_template.replace(
                '{test_scenario_document_path}',
                f'@{rel_path_test_scenario}'
            ).replace(
                '{review_feedback}',
                review_feedback
            ).replace(
                '{design_document_path}',
                f'@{rel_path_design}'
            ).replace(
                '{requirements_document_path}',
                f'@{rel_path_requirements}'
            ).replace(
                '{test_strategy}',
                test_strategy
            ).replace(
                '{issue_number}',
                str(issue_number)
            )

            # Claude Agent SDKでタスクを実行
            messages = self.execute_with_claude(
                prompt=revise_prompt,
                max_turns=40,
                log_prefix='revise'
            )

            # test-scenario.mdのパスを取得
            output_file = self.output_dir / 'test-scenario.md'

            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': '修正されたtest-scenario.mdが生成されませんでした。'
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

    def _format_issue_info(self, issue_info: Dict[str, Any]) -> str:
        """
        Issue情報をフォーマット

        Args:
            issue_info: Issue情報

        Returns:
            str: フォーマットされたIssue情報
        """
        formatted = f"""
## Issue情報

- **Issue番号**: #{issue_info['number']}
- **タイトル**: {issue_info['title']}
- **状態**: {issue_info['state']}
- **URL**: {issue_info['url']}
- **ラベル**: {', '.join(issue_info['labels']) if issue_info['labels'] else 'なし'}

### 本文

{issue_info['body']}
"""
        return formatted.strip()
