"""Phase 6: ドキュメント作成フェーズ

Phase 1-5の全成果物をまとめて、最終的なドキュメントを作成する。
このドキュメントは、人間がマージ判断を行うための情報をすべて含む。
"""
from pathlib import Path
from typing import Dict, Any, List
from .base_phase import BasePhase


class DocumentationPhase(BasePhase):
    """ドキュメント作成フェーズ"""

    def __init__(self, *args, **kwargs):
        """初期化"""
        super().__init__(
            phase_name='documentation',
            *args,
            **kwargs
        )

    def execute(self) -> Dict[str, Any]:
        """
        ドキュメント作成フェーズを実行

        Returns:
            Dict[str, Any]: 実行結果
                - success: bool
                - output: str - documentation.mdのパス
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

            # 実行プロンプトを読み込み
            execute_prompt_template = self.load_prompt('execute')

            # working_dirからの相対パスを使用
            rel_paths = {}
            for phase_name, phase_path in phase_outputs.items():
                rel_paths[phase_name] = phase_path.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            execute_prompt = execute_prompt_template.replace(
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

            # documentation.mdのパスを取得
            generated_file = self.metadata.workflow_dir / 'documentation.md'

            if not generated_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': f'documentation.mdが生成されませんでした。'
                }

            # output/ディレクトリに移動
            output_file = self.output_dir / 'documentation.md'
            generated_file.rename(output_file)
            print(f"[INFO] 成果物を移動: {generated_file} -> {output_file}")

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
            # documentation.mdを読み込み
            documentation_file = self.output_dir / 'documentation.md'

            if not documentation_file.exists():
                return {
                    'result': 'FAIL',
                    'feedback': 'documentation.mdが存在しません。',
                    'suggestions': ['execute()を実行してdocumentation.mdを生成してください。']
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
                '{documentation_document_path}',
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

            return review_result

        except Exception as e:
            return {
                'result': 'FAIL',
                'feedback': f'レビュー中にエラーが発生しました: {str(e)}',
                'suggestions': []
            }

    def revise(self, review_feedback: str) -> Dict[str, Any]:
        """
        レビュー結果を元にドキュメントを修正

        Args:
            review_feedback: レビュー結果のフィードバック

        Returns:
            Dict[str, Any]: 修正結果
                - success: bool
                - output: str - documentation.mdのパス
                - error: Optional[str]
        """
        try:
            # 元のドキュメントを読み込み
            documentation_file = self.output_dir / 'documentation.md'

            if not documentation_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': 'documentation.mdが存在しません。'
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
                '{documentation_document_path}',
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

            # documentation.mdのパスを取得
            generated_file = self.metadata.workflow_dir / 'documentation.md'
            output_file = self.output_dir / 'documentation.md'

            # 新しいファイルが生成された場合は移動
            if generated_file.exists() and generated_file != output_file:
                generated_file.replace(output_file)
                print(f"[INFO] 修正した成果物を移動: {generated_file} -> {output_file}")

            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': '修正されたdocumentation.mdが生成されませんでした。'
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

    def _parse_review_result(self, messages: List[str]) -> Dict[str, Any]:
        """
        レビュー結果メッセージから判定とフィードバックを抽出

        Args:
            messages: Claude Agent SDKからのレスポンスメッセージ

        Returns:
            Dict[str, Any]: レビュー結果
                - result: str
                - feedback: str
                - suggestions: List[str]
        """
        import re

        # 全テキストを結合
        full_text = ""
        for message in messages:
            if 'AssistantMessage' in message and 'TextBlock(text=' in message:
                text_start = message.find('TextBlock(text=') + 16
                text_end = message.find('\')', text_start)
                if text_end == -1:
                    continue

                text_content = message[text_start:text_end]

                # エスケープシーケンスを置換
                text_content = text_content.replace('\\n', '\n')
                text_content = text_content.replace('\\t', '\t')
                text_content = text_content.replace('\\r', '\r')

                full_text += text_content + "\n"

        # 判定を正規表現で抽出
        result_match = re.search(r'\*\*判定:\s*(PASS|PASS_WITH_SUGGESTIONS|FAIL)\*\*', full_text, re.IGNORECASE)

        if not result_match:
            return {
                'result': 'FAIL',
                'feedback': f'レビュー結果に判定が含まれていませんでした。\n\n{full_text[:500]}',
                'suggestions': ['レビュープロンプトで判定キーワードを確認してください。']
            }

        result = result_match.group(1).upper()

        return {
            'result': result,
            'feedback': full_text.strip(),
            'suggestions': []
        }
