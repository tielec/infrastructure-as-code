"""Phase 2: 詳細設計フェーズ

GitHub Issue情報と要件定義書から詳細設計書を作成し、
実装戦略・テスト戦略・テストコード戦略の判断を行う。
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, List
from .base_phase import BasePhase


class DesignPhase(BasePhase):
    """詳細設計フェーズ"""

    def __init__(self, *args, **kwargs):
        """初期化"""
        super().__init__(
            phase_name='design',
            *args,
            **kwargs
        )

    def execute(self) -> Dict[str, Any]:
        """
        詳細設計フェーズを実行

        Returns:
            Dict[str, Any]: 実行結果
                - success: bool
                - output: str - design.mdのパス
                - error: Optional[str]
        """
        try:
            # Issue情報を取得
            issue_number = int(self.metadata.data['issue_number'])
            issue_info = self.github.get_issue_info(issue_number)

            # Issue情報をフォーマット
            issue_info_text = self._format_issue_info(issue_info)

            # 要件定義書を読み込み
            requirements_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '01_requirements' / 'output' / 'requirements.md'

            if not requirements_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': f'要件定義書が見つかりません: {requirements_file}'
                }

            # 実行プロンプトを読み込み
            execute_prompt_template = self.load_prompt('execute')

            # working_dirからの相対パスを使用
            rel_path_requirements = requirements_file.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            execute_prompt = execute_prompt_template.replace(
                '{requirements_document_path}',
                f'@{rel_path_requirements}'
            ).replace(
                '{issue_info}',
                issue_info_text
            ).replace(
                '{issue_number}',
                str(issue_number)
            )

            # Claude Agent SDKでタスクを実行（プロンプトとログは自動保存）
            messages = self.execute_with_claude(
                prompt=execute_prompt,
                max_turns=40,  # 設計フェーズは複雑なので多めに
                log_prefix='execute'
            )

            # design.mdのパスを取得
            output_file = self.output_dir / 'design.md'

            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': f'design.mdが生成されませんでした: {output_file}'
                }

            # 戦略判断の処理（Phase 0で決定済みか確認）
            design_content = output_file.read_text(encoding='utf-8')
            decisions = self.metadata.data['design_decisions']

            # Phase 0で戦略が決定されているか確認
            if decisions.get('implementation_strategy') is not None:
                # Phase 0で決定済みの場合は、そのまま使用
                print(f"[INFO] Phase 0で決定済みの戦略を使用: {decisions}")
            else:
                # Phase 0がスキップされた場合は、Phase 2で決定（後方互換性）
                print("[INFO] Phase 0がスキップされているため、Phase 2で戦略を決定します")
                extracted_decisions = self._extract_design_decisions(design_content)

                if extracted_decisions:
                    self.metadata.data['design_decisions'].update(extracted_decisions)
                    self.metadata.save()
                    print(f"[INFO] 戦略判断をmetadata.jsonに保存: {extracted_decisions}")

            # GitHub Issueに成果物を投稿
            try:
                # design_content 変数を再利用（88行目で既に読み込み済み）
                self.post_output(
                    output_content=design_content,
                    title="詳細設計書"
                )
            except Exception as e:
                print(f"[WARNING] 成果物のGitHub投稿に失敗しました: {e}")

            # ステータス更新: BasePhase.run()で実行されるため不要
            # self.metadata.update_phase_status('design', 'completed', str(output_file))
            # self.post_progress('completed', f'詳細設計が完了しました: {output_file.name}')

            return {
                'success': True,
                'output': str(output_file),
                'error': None
            }

        except Exception as e:
            # ステータス更新: 失敗
            self.metadata.update_phase_status('design', 'failed')
            self.post_progress('failed', f'詳細設計が失敗しました: {str(e)}')

            return {
                'success': False,
                'output': None,
                'error': str(e)
            }

    def review(self) -> Dict[str, Any]:
        """
        設計書をレビュー

        Returns:
            Dict[str, Any]: レビュー結果
                - result: str - PASS/PASS_WITH_SUGGESTIONS/FAIL
                - feedback: str
                - suggestions: List[str]
        """
        try:
            # design.mdを読み込み（output/ディレクトリから）
            design_file = self.output_dir / 'design.md'

            if not design_file.exists():
                return {
                    'result': 'FAIL',
                    'feedback': 'design.mdが存在しません。',
                    'suggestions': ['execute()を実行してdesign.mdを生成してください。']
                }

            # 要件定義書のパス
            issue_number = int(self.metadata.data['issue_number'])
            requirements_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '01_requirements' / 'output' / 'requirements.md'

            # レビュープロンプトを読み込み
            review_prompt_template = self.load_prompt('review')

            # working_dirからの相対パスを使用
            rel_path_design = design_file.relative_to(self.claude.working_dir)
            rel_path_requirements = requirements_file.relative_to(self.claude.working_dir)

            # Issue情報を取得
            issue_info = self.github.get_issue_info(issue_number)
            issue_info_text = self._format_issue_info(issue_info)

            # プロンプトに情報を埋め込み
            review_prompt = review_prompt_template.replace(
                '{design_document_path}',
                f'@{rel_path_design}'
            ).replace(
                '{requirements_document_path}',
                f'@{rel_path_requirements}'
            ).replace(
                '{issue_info}',
                issue_info_text
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
        レビュー結果を元に設計書を修正

        Args:
            review_feedback: レビュー結果のフィードバック

        Returns:
            Dict[str, Any]: 修正結果
                - success: bool
                - output: str - design.mdのパス
                - error: Optional[str]
        """
        try:
            # Issue情報を取得
            issue_number = int(self.metadata.data['issue_number'])
            issue_info = self.github.get_issue_info(issue_number)

            # Issue情報をフォーマット
            issue_info_text = self._format_issue_info(issue_info)

            # 元の設計書を読み込み
            design_file = self.output_dir / 'design.md'

            if not design_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': 'design.mdが存在しません。'
                }

            # 要件定義書のパス
            requirements_file = self.metadata.workflow_dir.parent / f'issue-{issue_number}' / '01_requirements' / 'output' / 'requirements.md'

            # 修正プロンプトを読み込み
            revise_prompt_template = self.load_prompt('revise')

            # working_dirからの相対パスを使用
            rel_path_design = design_file.relative_to(self.claude.working_dir)
            rel_path_requirements = requirements_file.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            revise_prompt = revise_prompt_template.replace(
                '{design_document_path}',
                f'@{rel_path_design}'
            ).replace(
                '{review_feedback}',
                review_feedback
            ).replace(
                '{requirements_document_path}',
                f'@{rel_path_requirements}'
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
                max_turns=40,
                log_prefix='revise'
            )

            # design.mdのパスを取得
            output_file = self.output_dir / 'design.md'

            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': '修正されたdesign.mdが生成されませんでした。'
                }

            # 戦略判断の処理（Phase 0で決定済みの場合は抽出しない）
            design_content = output_file.read_text(encoding='utf-8')
            decisions = self.metadata.data['design_decisions']

            # Phase 0で戦略が決定されている場合は抽出しない（Phase 0の戦略を維持）
            if decisions.get('implementation_strategy') is None:
                # Phase 0がスキップされた場合のみ、Phase 2で戦略を抽出
                extracted_decisions = self._extract_design_decisions(design_content)

                if extracted_decisions:
                    self.metadata.data['design_decisions'].update(extracted_decisions)
                    self.metadata.save()
                    print(f"[INFO] 戦略判断を更新: {extracted_decisions}")
            else:
                print(f"[INFO] Phase 0で決定済みの戦略を維持: {decisions}")

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

    def _extract_design_decisions(self, design_content: str) -> Dict[str, str]:
        """
        設計書から戦略判断を抽出

        Args:
            design_content: 設計書の内容

        Returns:
            Dict[str, str]: 戦略判断
                - implementation_strategy: CREATE/EXTEND/REFACTOR
                - test_strategy: UNIT_ONLY/INTEGRATION_ONLY/BDD_ONLY/UNIT_INTEGRATION/UNIT_BDD/INTEGRATION_BDD/ALL
                - test_code_strategy: EXTEND_TEST/CREATE_TEST/BOTH_TEST
        """
        decisions = {}

        # 実装戦略を抽出
        impl_match = re.search(
            r'##\s*\d+\.\s*実装戦略[:：]\s*(CREATE|EXTEND|REFACTOR)',
            design_content,
            re.IGNORECASE | re.MULTILINE
        )
        if impl_match:
            decisions['implementation_strategy'] = impl_match.group(1).upper()

        # テスト戦略を抽出
        test_match = re.search(
            r'##\s*\d+\.\s*テスト戦略[:：]\s*(UNIT_ONLY|INTEGRATION_ONLY|BDD_ONLY|UNIT_INTEGRATION|UNIT_BDD|INTEGRATION_BDD|ALL)',
            design_content,
            re.IGNORECASE | re.MULTILINE
        )
        if test_match:
            decisions['test_strategy'] = test_match.group(1).upper()

        # テストコード戦略を抽出
        test_code_match = re.search(
            r'##\s*\d+\.\s*テストコード戦略[:：]\s*(EXTEND_TEST|CREATE_TEST|BOTH_TEST)',
            design_content,
            re.IGNORECASE | re.MULTILINE
        )
        if test_code_match:
            decisions['test_code_strategy'] = test_code_match.group(1).upper()

        return decisions
