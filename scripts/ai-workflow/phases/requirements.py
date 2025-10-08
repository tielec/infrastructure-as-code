"""Phase 1: 要件定義フェーズ

GitHubのIssue情報から詳細な要件定義書を作成
- Issue情報の取得・解析
- 要件定義書の生成（requirements.md）
- クリティカルシンキングによるレビュー
"""
import json
from pathlib import Path
from typing import Dict, Any, List
from .base_phase import BasePhase


class RequirementsPhase(BasePhase):
    """要件定義フェーズ"""

    def __init__(self, *args, **kwargs):
        """初期化"""
        super().__init__(
            phase_name='requirements',
            *args,
            **kwargs
        )

    def execute(self) -> Dict[str, Any]:
        """
        要件定義フェーズを実行

        Returns:
            Dict[str, Any]: 実行結果
                - success: bool
                - output: str - requirements.mdのパス
                - error: Optional[str]
        """
        try:
            # Issue情報を取得
            issue_number = int(self.metadata.data['issue_number'])
            issue_info = self.github.get_issue_info(issue_number)

            # Issue情報をフォーマット
            issue_info_text = self._format_issue_info(issue_info)

            # 実行プロンプトを読み込み
            execute_prompt_template = self.load_prompt('execute')

            # Issue情報をプロンプトに埋め込み
            execute_prompt = execute_prompt_template.replace(
                '{issue_info}',
                issue_info_text
            ).replace(
                '{issue_number}',
                str(issue_number)
            )

            # Claude Agent SDKでタスクを実行（プロンプトとログは自動保存）
            messages = self.execute_with_claude(
                prompt=execute_prompt,
                max_turns=30,
                log_prefix='execute'
            )

            # requirements.mdのパスを取得（エージェントが生成した場所）
            generated_file = self.metadata.workflow_dir / 'requirements.md'

            if not generated_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': f'requirements.mdが生成されませんでした。'
                }

            # output/ディレクトリに移動
            output_file = self.output_dir / 'requirements.md'
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
        要件定義書をレビュー

        Returns:
            Dict[str, Any]: レビュー結果
                - result: str - PASS/PASS_WITH_SUGGESTIONS/FAIL
                - feedback: str
                - suggestions: List[str]
        """
        try:
            # requirements.mdを読み込み（output/ディレクトリから）
            requirements_file = self.output_dir / 'requirements.md'

            if not requirements_file.exists():
                return {
                    'result': 'FAIL',
                    'feedback': 'requirements.mdが存在しません。',
                    'suggestions': ['execute()を実行してrequirements.mdを生成してください。']
                }

            # レビュープロンプトを読み込み
            review_prompt_template = self.load_prompt('review')

            # requirements.mdのパスを@記法で埋め込み（Claude Codeがファイルを読み取る）
            # working_dirからの相対パスを使用
            rel_path = requirements_file.relative_to(self.claude.working_dir)
            review_prompt = review_prompt_template.replace(
                '{requirements_document_path}',
                f'@{rel_path}'
            )

            # Claude Agent SDKでレビューを実行（プロンプトとログは自動保存）
            messages = self.execute_with_claude(
                prompt=review_prompt,
                max_turns=30,
                log_prefix='review'
            )

            # レビュー結果をパース
            review_result = self._parse_review_result(messages)

            # レビュー結果をファイルに保存（review/ディレクトリ）
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

    def revise(self, review_feedback: str) -> Dict[str, Any]:
        """
        レビュー結果を元に要件定義書を修正

        Args:
            review_feedback: レビュー結果のフィードバック

        Returns:
            Dict[str, Any]: 修正結果
                - success: bool
                - output: str - requirements.mdのパス
                - error: Optional[str]
        """
        try:
            # Issue情報を取得
            issue_number = int(self.metadata.data['issue_number'])
            issue_info = self.github.get_issue_info(issue_number)

            # Issue情報をフォーマット
            issue_info_text = self._format_issue_info(issue_info)

            # 元の要件定義書を読み込み
            requirements_file = self.output_dir / 'requirements.md'

            if not requirements_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': 'requirements.mdが存在しません。'
                }

            # 修正プロンプトを読み込み
            revise_prompt_template = self.load_prompt('revise')

            # working_dirからの相対パスを使用
            rel_path = requirements_file.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            revise_prompt = revise_prompt_template.replace(
                '{requirements_document_path}',
                f'@{rel_path}'
            ).replace(
                '{review_feedback}',
                review_feedback
            ).replace(
                '{issue_info}',
                issue_info_text
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

            # requirements.mdのパスを取得（エージェントが更新した場所）
            # revise処理では、元のファイルを直接更新するか、新しい場所に生成する可能性がある
            generated_file = self.metadata.workflow_dir / 'requirements.md'
            output_file = self.output_dir / 'requirements.md'

            # 新しいファイルが生成された場合は移動
            if generated_file.exists() and generated_file != output_file:
                generated_file.replace(output_file)
                print(f"[INFO] 修正した成果物を移動: {generated_file} -> {output_file}")

            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': '修正されたrequirements.mdが生成されませんでした。'
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

                # エスケープシーケンスを置換（日本語文字を保持）
                text_content = text_content.replace('\\n', '\n')
                text_content = text_content.replace('\\t', '\t')
                text_content = text_content.replace('\\r', '\r')

                full_text += text_content + "\n"

        # 判定を正規表現で抽出
        result_match = re.search(r'\*\*判定:\s*(PASS|PASS_WITH_SUGGESTIONS|FAIL)\*\*', full_text, re.IGNORECASE)

        if not result_match:
            # 判定が見つからない場合
            return {
                'result': 'FAIL',
                'feedback': f'レビュー結果に判定が含まれていませんでした。\n\n{full_text[:500]}',
                'suggestions': ['レビュープロンプトで判定キーワードを確認してください。']
            }

        result = result_match.group(1).upper()

        return {
            'result': result,
            'feedback': full_text.strip(),
            'suggestions': []  # 全文に含まれているため不要
        }
