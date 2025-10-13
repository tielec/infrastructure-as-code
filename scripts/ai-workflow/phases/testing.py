"""Phase 5: テスト実行フェーズ

Phase 4で実装したテストコードを実行し、結果を記録する。
テスト失敗時はPhase 4に戻って修正が必要。
"""
import re
from pathlib import Path
from typing import Dict, Any, List
from phases.base.abstract_phase import AbstractPhase


class TestingPhase(AbstractPhase):
    """テスト実行フェーズ"""

    def __init__(self, *args, **kwargs):
        """初期化"""
        super().__init__(
            phase_name='testing',
            *args,
            **kwargs
        )

    def execute(self) -> Dict[str, Any]:
        """
        テスト実行フェーズを実行

        Returns:
            Dict[str, Any]: 実行結果
                - success: bool
                - output: str - test-result.mdのパス
                - error: Optional[str]
        """
        try:
            # Issue情報を取得
            issue_number = int(self.metadata.data['issue_number'])

            # 必要なファイルのパスを定義
            test_implementation_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '05_test_implementation' / 'output' / 'test-implementation.md'
            implementation_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '04_implementation' / 'output' / 'implementation.md'
            test_scenario_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '03_test_scenario' / 'output' / 'test-scenario.md'

            if not test_implementation_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': f'テスト実装ログが見つかりません: {test_implementation_file}'
                }

            if not implementation_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': f'実装ログが見つかりません: {implementation_file}'
                }

            if not test_scenario_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': f'テストシナリオが見つかりません: {test_scenario_file}'
                }

            # Planning Phase成果物のパス取得
            planning_path_str = self._get_planning_document_path(issue_number)

            # 実行プロンプトを読み込み
            execute_prompt_template = self.load_prompt('execute')

            # working_dirからの相対パスを使用
            rel_path_test_implementation = test_implementation_file.relative_to(self.claude.working_dir)
            rel_path_implementation = implementation_file.relative_to(self.claude.working_dir)
            rel_path_test_scenario = test_scenario_file.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            execute_prompt = execute_prompt_template.replace(
                '{planning_document_path}',
                planning_path_str
            ).replace(
                '{test_implementation_document_path}',
                f'@{rel_path_test_implementation}'
            ).replace(
                '{implementation_document_path}',
                f'@{rel_path_implementation}'
            ).replace(
                '{test_scenario_document_path}',
                f'@{rel_path_test_scenario}'
            ).replace(
                '{issue_number}',
                str(issue_number)
            )

            # test-result.mdのパスを取得
            output_file = self.output_dir / 'test-result.md'

            # 既存ファイルの最終更新時刻を記録（上書き確認用）
            old_mtime = output_file.stat().st_mtime if output_file.exists() else None

            # Claude Agent SDKでタスクを実行
            messages = self.execute_with_claude(
                prompt=execute_prompt,
                max_turns=30,
                log_prefix='execute'
            )

            # test-result.mdが存在するか確認
            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': f'test-result.mdが生成されませんでした: {output_file}'
                }

            # ファイルが更新されたか確認（タイムスタンプチェック）
            new_mtime = output_file.stat().st_mtime
            if old_mtime is not None and new_mtime == old_mtime:
                return {
                    'success': False,
                    'output': None,
                    'error': f'test-result.mdが更新されませんでした（古いファイルのまま）: {output_file}'
                }

            # GitHub Issueに成果物を投稿
            try:
                output_content = output_file.read_text(encoding='utf-8')
                self.post_output(
                    output_content=output_content,
                    title="テスト結果"
                )
            except Exception as e:
                print(f"[WARNING] 成果物のGitHub投稿に失敗しました: {e}")

            # ステータス更新: BasePhase.run()で実行されるため不要
            # self.metadata.update_phase_status('testing', 'completed', str(output_file))
            # self.post_progress('completed', f'テストが完了しました: {output_file.name}')

            return {
                'success': True,
                'output': str(output_file),
                'error': None
            }

        except Exception as e:
            # ステータス更新: 失敗
            self.metadata.update_phase_status('testing', 'failed')
            # BasePhase.run()で実行されるため不要
            # self.post_progress('failed', f'テストが失敗しました: {str(e)}')

            return {
                'success': False,
                'output': None,
                'error': str(e)
            }

    def review(self) -> Dict[str, Any]:
        """
        テスト結果をレビュー

        Returns:
            Dict[str, Any]: レビュー結果
                - result: str - PASS/PASS_WITH_SUGGESTIONS/FAIL
                - feedback: str
                - suggestions: List[str]
        """
        try:
            # test-result.mdを読み込み
            test_result_file = self.output_dir / 'test-result.md'

            if not test_result_file.exists():
                return {
                    'result': 'FAIL',
                    'feedback': 'test-result.mdが存在しません。',
                    'suggestions': ['execute()を実行してtest-result.mdを生成してください。']
                }

            # 実装ログとテストシナリオのパス
            issue_number = int(self.metadata.data['issue_number'])
            implementation_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '04_implementation' / 'output' / 'implementation.md'
            test_scenario_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '03_test_scenario' / 'output' / 'test-scenario.md'

            # レビュープロンプトを読み込み
            review_prompt_template = self.load_prompt('review')

            # working_dirからの相対パスを使用
            rel_path_test_result = test_result_file.relative_to(self.claude.working_dir)
            rel_path_implementation = implementation_file.relative_to(self.claude.working_dir)
            rel_path_test_scenario = test_scenario_file.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            review_prompt = review_prompt_template.replace(
                '{test_result_document_path}',
                f'@{rel_path_test_result}'
            ).replace(
                '{implementation_document_path}',
                f'@{rel_path_implementation}'
            ).replace(
                '{test_scenario_document_path}',
                f'@{rel_path_test_scenario}'
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
        レビュー結果を元にテストを再実行または実装を修正

        Args:
            review_feedback: レビュー結果のフィードバック

        Returns:
            Dict[str, Any]: 修正結果
                - success: bool
                - output: str - test-result.mdのパス
                - error: Optional[str]
        """
        try:
            # 元のテスト結果のパス
            test_result_file = self.output_dir / 'test-result.md'

            if not test_result_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': 'test-result.mdが存在しません。'
                }

            # 必要なファイルのパスを定義
            issue_number = int(self.metadata.data['issue_number'])
            test_implementation_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '05_test_implementation' / 'output' / 'test-implementation.md'
            implementation_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '04_implementation' / 'output' / 'implementation.md'
            test_scenario_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '03_test_scenario' / 'output' / 'test-scenario.md'

            # 修正プロンプトを読み込み
            revise_prompt_template = self.load_prompt('revise')

            # working_dirからの相対パスを使用
            rel_path_test_result = test_result_file.relative_to(self.claude.working_dir)
            rel_path_test_implementation = test_implementation_file.relative_to(self.claude.working_dir)
            rel_path_implementation = implementation_file.relative_to(self.claude.working_dir)
            rel_path_test_scenario = test_scenario_file.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            revise_prompt = revise_prompt_template.replace(
                '{test_result_document_path}',
                f'@{rel_path_test_result}'
            ).replace(
                '{review_feedback}',
                review_feedback
            ).replace(
                '{test_implementation_document_path}',
                f'@{rel_path_test_implementation}'
            ).replace(
                '{implementation_document_path}',
                f'@{rel_path_implementation}'
            ).replace(
                '{test_scenario_document_path}',
                f'@{rel_path_test_scenario}'
            ).replace(
                '{issue_number}',
                str(issue_number)
            )

            # 既存ファイルの最終更新時刻を記録（上書き確認用）
            old_mtime = test_result_file.stat().st_mtime if test_result_file.exists() else None

            # Claude Agent SDKでタスクを実行
            messages = self.execute_with_claude(
                prompt=revise_prompt,
                max_turns=30,
                log_prefix='revise'
            )

            # test-result.mdが存在するか確認
            output_file = self.output_dir / 'test-result.md'

            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': '修正されたtest-result.mdが生成されませんでした。'
                }

            # ファイルが更新されたか確認（タイムスタンプチェック）
            new_mtime = output_file.stat().st_mtime
            if old_mtime is not None and new_mtime == old_mtime:
                return {
                    'success': False,
                    'output': None,
                    'error': f'test-result.mdが更新されませんでした（古いファイルのまま）: {output_file}'
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
