"""Phase 6: ドキュメント更新フェーズ

Phase 1-5の変更内容に基づいて、プロジェクトドキュメント（README.md等）を更新する。
影響を受けるドキュメントを特定し、更新内容を記録する。
"""
from pathlib import Path
from typing import Dict, Any, List
from .base_phase import BasePhase


class DocumentationPhase(BasePhase):
    """ドキュメント更新フェーズ"""

    def __init__(self, *args, **kwargs):
        """初期化"""
        super().__init__(
            phase_name='documentation',
            *args,
            **kwargs
        )

    def execute(self) -> Dict[str, Any]:
        """
        ドキュメント更新フェーズを実行

        Returns:
            Dict[str, Any]: 実行結果
                - success: bool
                - output: str - documentation-update-log.mdのパス
                - error: Optional[str]
        """
        try:
            # Issue情報を取得
            issue_number = int(self.metadata.data['issue_number'])

            # 各フェーズの成果物パスを取得
            phase_outputs = self._get_phase_outputs(issue_number)

            # 必須フェーズの成果物が存在するか確認
            required_phases = ['requirements', 'design', 'test_scenario', 'implementation', 'test_result']
            for phase in required_phases:
                if not phase_outputs[phase].exists():
                    return {
                        'success': False,
                        'output': None,
                        'error': f'{phase}の成果物が見つかりません: {phase_outputs[phase]}'
                    }

            # Planning Phase成果物のパス取得
            planning_path_str = self._get_planning_document_path(issue_number)

            # 実行プロンプトを読み込み
            execute_prompt_template = self.load_prompt('execute')

            # working_dirからの相対パスを使用
            rel_paths = {}
            for phase_name, phase_path in phase_outputs.items():
                rel_paths[phase_name] = phase_path.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            execute_prompt = execute_prompt_template.replace(
                '{planning_document_path}',
                planning_path_str
            ).replace(
                '{requirements_document_path}',
                f'@{rel_paths["requirements"]}'
            ).replace(
                '{design_document_path}',
                f'@{rel_paths["design"]}'
            ).replace(
                '{test_scenario_document_path}',
                f'@{rel_paths["test_scenario"]}'
            ).replace(
                '{implementation_document_path}',
                f'@{rel_paths["implementation"]}'
            ).replace(
                '{test_result_document_path}',
                f'@{rel_paths["test_result"]}'
            ).replace(
                '{issue_number}',
                str(issue_number)
            )

            # Claude Agent SDKでタスクを実行
            messages = self.execute_with_claude(
                prompt=execute_prompt,
                max_turns=30,
                log_prefix='execute'
            )

            # documentation-update-log.mdのパスを取得
            output_file = self.output_dir / 'documentation-update-log.md'

            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': f'documentation-update-log.mdが生成されませんでした: {output_file}'
                }

            # GitHub Issueに成果物を投稿
            try:
                output_content = output_file.read_text(encoding='utf-8')
                self.post_output(
                    output_content=output_content,
                    title="ドキュメント更新ログ"
                )
            except Exception as e:
                print(f"[WARNING] 成果物のGitHub投稿に失敗しました: {e}")

            # ステータス更新: BasePhase.run()で実行されるため不要
            # self.metadata.update_phase_status('documentation', 'completed', str(output_file))
            # self.post_progress('completed', f'ドキュメントが完了しました: {output_file.name}')

            return {
                'success': True,
                'output': str(output_file),
                'error': None
            }

        except Exception as e:
            # ステータス更新: 失敗
            self.metadata.update_phase_status('documentation', 'failed')
            # BasePhase.run()で実行されるため不要
            # self.post_progress('failed', f'ドキュメントが失敗しました: {str(e)}')

            return {
                'success': False,
                'output': None,
                'error': str(e)
            }

    def review(self) -> Dict[str, Any]:
        """
        ドキュメントをレビュー

        Returns:
            Dict[str, Any]: レビュー結果
                - result: str - PASS/PASS_WITH_SUGGESTIONS/FAIL
                - feedback: str
                - suggestions: List[str]
        """
        try:
            # documentation-update-log.mdを読み込み
            documentation_file = self.output_dir / 'documentation-update-log.md'

            if not documentation_file.exists():
                return {
                    'result': 'FAIL',
                    'feedback': 'documentation-update-log.mdが存在しません。',
                    'suggestions': ['execute()を実行してdocumentation-update-log.mdを生成してください。']
                }

            # 各フェーズの成果物パス
            issue_number = int(self.metadata.data['issue_number'])
            phase_outputs = self._get_phase_outputs(issue_number)

            # レビュープロンプトを読み込み
            review_prompt_template = self.load_prompt('review')

            # working_dirからの相対パスを使用
            rel_path_documentation = documentation_file.relative_to(self.claude.working_dir)
            rel_paths = {}
            for phase_name, phase_path in phase_outputs.items():
                rel_paths[phase_name] = phase_path.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            review_prompt = review_prompt_template.replace(
                '{documentation_update_log_path}',
                f'@{rel_path_documentation}'
            ).replace(
                '{requirements_document_path}',
                f'@{rel_paths["requirements"]}'
            ).replace(
                '{design_document_path}',
                f'@{rel_paths["design"]}'
            ).replace(
                '{test_scenario_document_path}',
                f'@{rel_paths["test_scenario"]}'
            ).replace(
                '{implementation_document_path}',
                f'@{rel_paths["implementation"]}'
            ).replace(
                '{test_result_document_path}',
                f'@{rel_paths["test_result"]}'
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
        レビュー結果を元にドキュメント更新を修正

        Args:
            review_feedback: レビュー結果のフィードバック

        Returns:
            Dict[str, Any]: 修正結果
                - success: bool
                - output: str - documentation-update-log.mdのパス
                - error: Optional[str]
        """
        try:
            # 元のドキュメントを読み込み
            documentation_file = self.output_dir / 'documentation-update-log.md'

            if not documentation_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': 'documentation-update-log.mdが存在しません。'
                }

            # 各フェーズの成果物パス
            issue_number = int(self.metadata.data['issue_number'])
            phase_outputs = self._get_phase_outputs(issue_number)

            # 修正プロンプトを読み込み
            revise_prompt_template = self.load_prompt('revise')

            # working_dirからの相対パスを使用
            rel_path_documentation = documentation_file.relative_to(self.claude.working_dir)
            rel_paths = {}
            for phase_name, phase_path in phase_outputs.items():
                rel_paths[phase_name] = phase_path.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            revise_prompt = revise_prompt_template.replace(
                '{documentation_update_log_path}',
                f'@{rel_path_documentation}'
            ).replace(
                '{review_feedback}',
                review_feedback
            ).replace(
                '{requirements_document_path}',
                f'@{rel_paths["requirements"]}'
            ).replace(
                '{design_document_path}',
                f'@{rel_paths["design"]}'
            ).replace(
                '{test_scenario_document_path}',
                f'@{rel_paths["test_scenario"]}'
            ).replace(
                '{implementation_document_path}',
                f'@{rel_paths["implementation"]}'
            ).replace(
                '{test_result_document_path}',
                f'@{rel_paths["test_result"]}'
            ).replace(
                '{issue_number}',
                str(issue_number)
            )

            # Claude Agent SDKでタスクを実行
            messages = self.execute_with_claude(
                prompt=revise_prompt,
                max_turns=30,
                log_prefix='revise'
            )

            # documentation-update-log.mdのパスを取得
            output_file = self.output_dir / 'documentation-update-log.md'

            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': '修正されたdocumentation-update-log.mdが生成されませんでした。'
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

    def _get_phase_outputs(self, issue_number: int) -> Dict[str, Path]:
        """
        各フェーズの成果物パスを取得

        Args:
            issue_number: Issue番号

        Returns:
            Dict[str, Path]: フェーズ名 → 成果物パス
        """
        base_dir = self.metadata.workflow_dir.parent / f'issue-{issue_number}'

        return {
            'requirements': base_dir / '01_requirements' / 'output' / 'requirements.md',
            'design': base_dir / '02_design' / 'output' / 'design.md',
            'test_scenario': base_dir / '03_test_scenario' / 'output' / 'test-scenario.md',
            'implementation': base_dir / '04_implementation' / 'output' / 'implementation.md',
            'test_result': base_dir / '05_testing' / 'output' / 'test-result.md'
        }
