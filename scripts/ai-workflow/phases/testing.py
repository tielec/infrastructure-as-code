"""Phase 5: テスト実行フェーズ

Phase 4で実装したテストコードを実行し、結果を記録する。
テスト失敗時はPhase 4に戻って修正が必要。
"""
import re
from pathlib import Path
from typing import Dict, Any, List
from .base_phase import BasePhase


class TestingPhase(BasePhase):
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

            # 実装ログとテストシナリオを読み込み
            implementation_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '04_implementation' / 'output' / 'implementation.md'
            test_scenario_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '03_test_scenario' / 'output' / 'test-scenario.md'

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

            # 実行プロンプトを読み込み
            execute_prompt_template = self.load_prompt('execute')

            # working_dirからの相対パスを使用
            rel_path_implementation = implementation_file.relative_to(self.claude.working_dir)
            rel_path_test_scenario = test_scenario_file.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            execute_prompt = execute_prompt_template.replace(
                '{implementation_document_path}',
                f'@{rel_path_implementation}'
            ).replace(
                '{test_scenario_document_path}',
                f'@{rel_path_test_scenario}'
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

            # test-result.mdのパスを取得
            generated_file = self.metadata.workflow_dir / 'test-result.md'

            if not generated_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': f'test-result.mdが生成されませんでした。'
                }

            # output/ディレクトリに移動
            output_file = self.output_dir / 'test-result.md'
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
            # 元のテスト結果を読み込み
            test_result_file = self.output_dir / 'test-result.md'

            if not test_result_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': 'test-result.mdが存在しません。'
                }

            # 実装ログとテストシナリオのパス
            issue_number = int(self.metadata.data['issue_number'])
            implementation_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '04_implementation' / 'output' / 'implementation.md'
            test_scenario_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '03_test_scenario' / 'output' / 'test-scenario.md'

            # 修正プロンプトを読み込み
            revise_prompt_template = self.load_prompt('revise')

            # working_dirからの相対パスを使用
            rel_path_test_result = test_result_file.relative_to(self.claude.working_dir)
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
                '{implementation_document_path}',
                f'@{rel_path_implementation}'
            ).replace(
                '{test_scenario_document_path}',
                f'@{rel_path_test_scenario}'
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

            # test-result.mdのパスを取得
            generated_file = self.metadata.workflow_dir / 'test-result.md'
            output_file = self.output_dir / 'test-result.md'

            # 新しいファイルが生成された場合は移動
            if generated_file.exists() and generated_file != output_file:
                generated_file.replace(output_file)
                print(f"[INFO] 修正した成果物を移動: {generated_file} -> {output_file}")

            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': '修正されたtest-result.mdが生成されませんでした。'
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
