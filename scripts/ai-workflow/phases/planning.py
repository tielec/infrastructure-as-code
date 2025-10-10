"""Phase 0: プロジェクト計画フェーズ

GitHub Issue情報から以下を策定:
- Issue複雑度分析
- 実装タスクの洗い出しと分割
- タスク間依存関係の特定
- 各フェーズの見積もり
- リスク評価とリスク軽減策
- 実装戦略・テスト戦略の事前決定
"""
from pathlib import Path
from typing import Dict, Any, List
from .base_phase import BasePhase
from core.content_parser import ClaudeContentParser


class PlanningPhase(BasePhase):
    """プロジェクト計画フェーズ"""

    def __init__(self, *args, **kwargs):
        """初期化"""
        super().__init__(
            phase_name='planning',
            *args,
            **kwargs
        )
        # Claude Messages APIベースのコンテンツパーサーを初期化
        self.content_parser = ClaudeContentParser()

    def execute(self) -> Dict[str, Any]:
        """
        プロジェクト計画フェーズを実行

        処理フロー:
        1. Issue情報を取得
        2. Issue情報をフォーマット
        3. 実行プロンプトを読み込み
        4. Claude Agent SDKでタスクを実行
        5. planning.mdのパスを取得
        6. 戦略判断を抽出してmetadata.jsonに保存
        7. GitHub Issueに成果物を投稿

        Returns:
            Dict[str, Any]: 実行結果
                - success: bool
                - output: str - planning.mdのパス
                - error: Optional[str]
        """
        try:
            # 1. Issue情報を取得
            issue_number = int(self.metadata.data['issue_number'])
            issue_info = self.github.get_issue_info(issue_number)

            # 2. Issue情報をフォーマット
            issue_info_text = self._format_issue_info(issue_info)

            # 3. 実行プロンプトを読み込み
            execute_prompt_template = self.load_prompt('execute')

            # 4. プロンプトに情報を埋め込み
            execute_prompt = execute_prompt_template.replace(
                '{issue_info}',
                issue_info_text
            ).replace(
                '{issue_number}',
                str(issue_number)
            )

            # 5. Claude Agent SDKでタスクを実行（計画フェーズは複雑なので多めに）
            messages = self.execute_with_claude(
                prompt=execute_prompt,
                max_turns=50,
                log_prefix='execute'
            )

            # 6. planning.mdのパスを取得
            output_file = self.output_dir / 'planning.md'

            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': f'planning.mdが生成されませんでした: {output_file}'
                }

            # 7. 戦略判断を抽出してmetadata.jsonに保存
            planning_content = output_file.read_text(encoding='utf-8')
            decisions = self._extract_design_decisions(planning_content)

            if decisions:
                self.metadata.data['design_decisions'].update(decisions)
                self.metadata.save()
                print(f"[INFO] 戦略判断をmetadata.jsonに保存: {decisions}")

            # 8. GitHub Issueに成果物を投稿
            try:
                self.post_output(
                    output_content=planning_content,
                    title="プロジェクト計画書"
                )
            except Exception as e:
                print(f"[WARNING] 成果物のGitHub投稿に失敗しました: {e}")

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
        計画書をレビュー

        処理フロー:
        1. planning.mdを読み込み
        2. レビュープロンプトを読み込み
        3. Claude Agent SDKでレビューを実行
        4. レビュー結果をパース
        5. レビュー結果をファイルに保存

        Returns:
            Dict[str, Any]: レビュー結果
                - result: str - PASS/PASS_WITH_SUGGESTIONS/FAIL
                - feedback: str
                - suggestions: List[str]
        """
        try:
            # planning.mdを読み込み（output/ディレクトリから）
            planning_file = self.output_dir / 'planning.md'

            if not planning_file.exists():
                return {
                    'result': 'FAIL',
                    'feedback': 'planning.mdが存在しません。',
                    'suggestions': ['execute()を実行してplanning.mdを生成してください。']
                }

            # レビュープロンプトを読み込み
            review_prompt_template = self.load_prompt('review')

            # planning.mdのパスを@記法で埋め込み（Claude Codeがファイルを読み取る）
            # working_dirからの相対パスを使用
            rel_path = planning_file.relative_to(self.claude.working_dir)
            review_prompt = review_prompt_template.replace(
                '{planning_document_path}',
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

    def revise(self, review_feedback: str) -> Dict[str, Any]:
        """
        レビュー結果を元に計画書を修正

        処理フロー:
        1. Issue情報を取得
        2. 元の計画書を読み込み
        3. 修正プロンプトを読み込み
        4. Claude Agent SDKでタスクを実行
        5. planning.mdのパスを取得
        6. 戦略判断を再抽出してmetadata.jsonに保存

        Args:
            review_feedback: レビュー結果のフィードバック

        Returns:
            Dict[str, Any]: 修正結果
                - success: bool
                - output: str - planning.mdのパス
                - error: Optional[str]
        """
        try:
            # Issue情報を取得
            issue_number = int(self.metadata.data['issue_number'])
            issue_info = self.github.get_issue_info(issue_number)

            # Issue情報をフォーマット
            issue_info_text = self._format_issue_info(issue_info)

            # 元の計画書を読み込み
            planning_file = self.output_dir / 'planning.md'

            if not planning_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': 'planning.mdが存在しません。'
                }

            # 修正プロンプトを読み込み
            revise_prompt_template = self.load_prompt('revise')

            # working_dirからの相対パスを使用
            rel_path = planning_file.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            revise_prompt = revise_prompt_template.replace(
                '{planning_document_path}',
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
                max_turns=50,
                log_prefix='revise'
            )

            # planning.mdのパスを取得
            output_file = self.output_dir / 'planning.md'

            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': '修正されたplanning.mdが生成されませんでした。'
                }

            # 戦略判断を再抽出してmetadata.jsonに保存
            planning_content = output_file.read_text(encoding='utf-8')
            decisions = self._extract_design_decisions(planning_content)

            if decisions:
                self.metadata.data['design_decisions'].update(decisions)
                self.metadata.save()
                print(f"[INFO] 戦略判断をmetadata.jsonに再保存: {decisions}")

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

{issue_info['body'] if issue_info['body'] else '(本文なし)'}
"""
        return formatted.strip()

    def _extract_design_decisions(self, planning_content: str) -> Dict[str, str]:
        """
        計画書から戦略判断を抽出（Claude Messages API使用）

        Args:
            planning_content: 計画書の内容

        Returns:
            Dict[str, str]: 戦略判断
                - implementation_strategy: CREATE/EXTEND/REFACTOR
                - test_strategy: UNIT_ONLY/.../ALL
                - test_code_strategy: EXTEND_TEST/CREATE_TEST/BOTH_TEST

        Notes:
            - 正規表現ベースの抽出からClaude Messages APIベースの抽出に置き換え
            - より高精度で柔軟な抽出が可能
        """
        return self.content_parser.extract_design_decisions(planning_content)
