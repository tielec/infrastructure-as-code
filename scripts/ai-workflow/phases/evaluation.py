"""Phase 9: プロジェクト評価フェーズ

Phase 1-8の成果物を統合評価し、次のアクションを判定する。
判定タイプ: PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
import re
from phases.base.abstract_phase import AbstractPhase


class EvaluationPhase(AbstractPhase):
    """プロジェクト評価フェーズ"""

    def __init__(self, *args, **kwargs):
        """初期化"""
        super().__init__(
            phase_name='evaluation',
            *args,
            **kwargs
        )

    def execute(self) -> Dict[str, Any]:
        """
        プロジェクト全体を評価

        Returns:
            Dict[str, Any]:
                - success: bool
                - output: str - evaluation_report.mdのパス
                - decision: str - PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT
                - error: Optional[str]
        """
        try:
            # Issue情報を取得
            issue_number = int(self.metadata.data['issue_number'])

            # Phase 1-8の成果物パスを取得
            phase_outputs = self._get_all_phase_outputs(issue_number)

            # 必須フェーズの成果物が存在するか確認
            required_phases = ['planning', 'requirements', 'design', 'test_scenario',
                             'implementation', 'test_implementation', 'testing',
                             'documentation', 'report']

            for phase in required_phases:
                if phase not in phase_outputs or not phase_outputs[phase].exists():
                    return {
                        'success': False,
                        'output': None,
                        'decision': None,
                        'error': f'{phase}の成果物が見つかりません: {phase_outputs.get(phase, "N/A")}'
                    }

            # Planning Phase成果物のパス取得
            planning_path_str = self._get_planning_document_path(issue_number)

            # Issue情報を取得
            issue_title = self.metadata.data.get('issue_title', f'Issue #{issue_number}')
            repo_name = self.metadata.data.get('repository', 'unknown')
            branch_name = f'ai-workflow/issue-{issue_number}'
            workflow_dir = str(self.metadata.workflow_dir)

            # 実行プロンプトを読み込み
            execute_prompt_template = self.load_prompt('execute')

            # working_dirからの相対パスを使用
            rel_paths = {}
            for phase_name, phase_path in phase_outputs.items():
                rel_paths[phase_name] = phase_path.relative_to(self.claude.working_dir)

            # フェーズ成果物のパス一覧を生成
            phase_outputs_list = '\n'.join([
                f'- **{phase_name.capitalize()}**: @{rel_path}'
                for phase_name, rel_path in rel_paths.items()
            ])

            # プロンプトに情報を埋め込み
            execute_prompt = execute_prompt_template.replace(
                '{issue_number}',
                str(issue_number)
            ).replace(
                '{issue_title}',
                issue_title
            ).replace(
                '{repo_name}',
                repo_name
            ).replace(
                '{branch_name}',
                branch_name
            ).replace(
                '{workflow_dir}',
                workflow_dir
            ).replace(
                '{phase_outputs}',
                phase_outputs_list
            ).replace(
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
                '{test_implementation_document_path}',
                f'@{rel_paths["test_implementation"]}'
            ).replace(
                '{test_result_document_path}',
                f'@{rel_paths["testing"]}'
            ).replace(
                '{documentation_update_log_path}',
                f'@{rel_paths["documentation"]}'
            ).replace(
                '{report_document_path}',
                f'@{rel_paths["report"]}'
            )

            # Claude Agent SDKでタスクを実行
            messages = self.execute_with_claude(
                prompt=execute_prompt,
                max_turns=50,
                log_prefix='execute'
            )

            # evaluation_report.mdのパスを取得
            output_file = self.output_dir / 'evaluation_report.md'

            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'decision': None,
                    'error': f'evaluation_report.mdが生成されませんでした: {output_file}'
                }

            # 評価レポートから判定タイプを決定
            evaluation_content = output_file.read_text(encoding='utf-8')
            decision_result = self._determine_decision(evaluation_content)

            if not decision_result.get('success', False):
                return {
                    'success': False,
                    'output': str(output_file),
                    'decision': None,
                    'error': decision_result.get('error', '判定タイプの決定に失敗しました')
                }

            decision = decision_result['decision']
            print(f"[INFO] 判定結果: {decision}")

            # 判定タイプに応じた処理を実行
            if decision == 'PASS':
                # PASS: 何もしない、ワークフロー完了
                print("[INFO] プロジェクト評価: PASS - ワークフロー完了")
                self.metadata.set_evaluation_decision(decision='PASS')

            elif decision == 'PASS_WITH_ISSUES':
                # PASS_WITH_ISSUES: 残タスクを抽出してIssue作成
                remaining_tasks = self._extract_remaining_tasks(evaluation_content)
                issue_result = self._handle_pass_with_issues(remaining_tasks, issue_number, output_file)

                if not issue_result.get('success', False):
                    print(f"[WARNING] Issue作成に失敗: {issue_result.get('error')}")
                    # Issue作成失敗してもワークフローは継続

                self.metadata.set_evaluation_decision(
                    decision='PASS_WITH_ISSUES',
                    remaining_tasks=remaining_tasks,
                    created_issue_url=issue_result.get('created_issue_url')
                )

            elif decision.startswith('FAIL_PHASE_'):
                # FAIL_PHASE_X: メタデータを巻き戻し
                failed_phase = decision_result.get('failed_phase')
                if not failed_phase:
                    return {
                        'success': False,
                        'output': str(output_file),
                        'decision': decision,
                        'error': '失敗したフェーズ名が特定できませんでした'
                    }

                rollback_result = self._handle_fail_phase_x(failed_phase)

                if not rollback_result.get('success', False):
                    return {
                        'success': False,
                        'output': str(output_file),
                        'decision': decision,
                        'error': f'メタデータの巻き戻しに失敗: {rollback_result.get("error")}'
                    }

                self.metadata.set_evaluation_decision(
                    decision=decision,
                    failed_phase=failed_phase
                )

            elif decision == 'ABORT':
                # ABORT: Issue/PRをクローズ
                abort_reason = decision_result.get('abort_reason', '致命的な問題が発見されました')
                abort_result = self._handle_abort(abort_reason, issue_number)

                if not abort_result.get('success', False):
                    print(f"[WARNING] Issue/PRクローズに失敗: {abort_result.get('error')}")

                self.metadata.set_evaluation_decision(
                    decision='ABORT',
                    abort_reason=abort_reason
                )

            else:
                return {
                    'success': False,
                    'output': str(output_file),
                    'decision': decision,
                    'error': f'不明な判定タイプ: {decision}'
                }

            # GitHub Issueに成果物を投稿
            try:
                output_content = output_file.read_text(encoding='utf-8')
                self.post_output(
                    output_content=output_content,
                    title="プロジェクト評価レポート"
                )
            except Exception as e:
                print(f"[WARNING] 成果物のGitHub投稿に失敗しました: {e}")

            return {
                'success': True,
                'output': str(output_file),
                'decision': decision,
                'error': None
            }

        except Exception as e:
            # ステータス更新: 失敗
            self.metadata.update_phase_status('evaluation', 'failed')

            return {
                'success': False,
                'output': None,
                'decision': None,
                'error': str(e)
            }

    def review(self) -> Dict[str, Any]:
        """
        評価結果をレビュー

        Returns:
            Dict[str, Any]:
                - result: str - PASS/PASS_WITH_SUGGESTIONS/FAIL
                - feedback: str
                - suggestions: List[str]
        """
        try:
            # evaluation_report.mdを読み込み
            evaluation_file = self.output_dir / 'evaluation_report.md'

            if not evaluation_file.exists():
                return {
                    'result': 'FAIL',
                    'feedback': 'evaluation_report.mdが存在しません。',
                    'suggestions': ['execute()を実行してevaluation_report.mdを生成してください。']
                }

            # Issue情報を取得
            issue_number = int(self.metadata.data['issue_number'])

            # Phase 1-8の成果物パスを取得
            phase_outputs = self._get_all_phase_outputs(issue_number)

            # レビュープロンプトを読み込み
            review_prompt_template = self.load_prompt('review')

            # working_dirからの相対パスを使用
            rel_path_evaluation = evaluation_file.relative_to(self.claude.working_dir)
            rel_paths = {}
            for phase_name, phase_path in phase_outputs.items():
                if phase_path.exists():
                    rel_paths[phase_name] = phase_path.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            review_prompt = review_prompt_template.replace(
                '{evaluation_report_path}',
                f'@{rel_path_evaluation}'
            ).replace(
                '{requirements_document_path}',
                f'@{rel_paths.get("requirements", "N/A")}'
            ).replace(
                '{design_document_path}',
                f'@{rel_paths.get("design", "N/A")}'
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
        レビュー結果を元に評価を修正

        Args:
            review_feedback: レビュー結果のフィードバック

        Returns:
            Dict[str, Any]:
                - success: bool
                - output: str - evaluation_report.mdのパス
                - error: Optional[str]
        """
        try:
            # 元の評価レポートを読み込み
            evaluation_file = self.output_dir / 'evaluation_report.md'

            if not evaluation_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': 'evaluation_report.mdが存在しません。'
                }

            # Issue情報を取得
            issue_number = int(self.metadata.data['issue_number'])

            # Phase 1-8の成果物パスを取得
            phase_outputs = self._get_all_phase_outputs(issue_number)

            # 修正プロンプトを読み込み
            revise_prompt_template = self.load_prompt('revise')

            # working_dirからの相対パスを使用
            rel_path_evaluation = evaluation_file.relative_to(self.claude.working_dir)
            rel_paths = {}
            for phase_name, phase_path in phase_outputs.items():
                if phase_path.exists():
                    rel_paths[phase_name] = phase_path.relative_to(self.claude.working_dir)

            # プロンプトに情報を埋め込み
            revise_prompt = revise_prompt_template.replace(
                '{evaluation_report_path}',
                f'@{rel_path_evaluation}'
            ).replace(
                '{review_feedback}',
                review_feedback
            ).replace(
                '{requirements_document_path}',
                f'@{rel_paths.get("requirements", "N/A")}'
            ).replace(
                '{design_document_path}',
                f'@{rel_paths.get("design", "N/A")}'
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

            # evaluation_report.mdのパスを取得
            output_file = self.output_dir / 'evaluation_report.md'

            if not output_file.exists():
                return {
                    'success': False,
                    'output': None,
                    'error': '修正されたevaluation_report.mdが生成されませんでした。'
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

    def _get_all_phase_outputs(self, issue_number: int) -> Dict[str, Path]:
        """
        Phase 0-8の全成果物パスを取得

        Args:
            issue_number: Issue番号

        Returns:
            Dict[str, Path]: フェーズ名 → 成果物パス
        """
        base_dir = self.metadata.workflow_dir.parent / f'issue-{issue_number}'

        return {
            'planning': base_dir / '00_planning' / 'output' / 'planning.md',
            'requirements': base_dir / '01_requirements' / 'output' / 'requirements.md',
            'design': base_dir / '02_design' / 'output' / 'design.md',
            'test_scenario': base_dir / '03_test_scenario' / 'output' / 'test-scenario.md',
            'implementation': base_dir / '04_implementation' / 'output' / 'implementation.md',
            'test_implementation': base_dir / '05_test_implementation' / 'output' / 'test-implementation.md',
            'testing': base_dir / '06_testing' / 'output' / 'test-result.md',
            'documentation': base_dir / '07_documentation' / 'output' / 'documentation-update-log.md',
            'report': base_dir / '08_report' / 'output' / 'report.md'
        }

    def _determine_decision(self, evaluation_content: str) -> Dict[str, Any]:
        """
        評価内容から判定タイプを決定

        Args:
            evaluation_content: evaluation_report.mdの内容

        Returns:
            Dict[str, Any]:
                - success: bool
                - decision: str - PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT
                - failed_phase: Optional[str] - FAIL_PHASE_Xの場合のフェーズ名
                - abort_reason: Optional[str] - ABORTの場合の理由
                - error: Optional[str]
        """
        try:
            # 判定結果セクションを抽出（正規表現ベース）
            # パターン1: ## 判定結果
            decision_match = re.search(
                r'##\s*判定結果.*?\n.*?(?:判定|決定|結果)[:：]\s*\**([A-Z_]+)\**',
                evaluation_content,
                re.IGNORECASE | re.DOTALL
            )

            if not decision_match:
                # パターン2: **判定**: PASS
                decision_match = re.search(
                    r'\*\*(?:判定|決定|結果)\*\*[:：]\s*\**([A-Z_]+)\**',
                    evaluation_content,
                    re.IGNORECASE
                )

            if not decision_match:
                return {
                    'success': False,
                    'decision': None,
                    'error': '判定結果が見つかりませんでした'
                }

            decision = decision_match.group(1).strip()

            # 判定タイプのバリデーション
            valid_decisions = ['PASS', 'PASS_WITH_ISSUES', 'ABORT']

            # FAIL_PHASE_Xパターンのチェック
            if decision.startswith('FAIL_PHASE_'):
                # フェーズ名を抽出
                phase_name = decision.replace('FAIL_PHASE_', '').lower()

                # フェーズ名マッピング
                phase_mapping = {
                    'planning': 'planning',
                    '0': 'planning',
                    'requirements': 'requirements',
                    '1': 'requirements',
                    'design': 'design',
                    '2': 'design',
                    'test_scenario': 'test_scenario',
                    'testscenario': 'test_scenario',
                    '3': 'test_scenario',
                    'implementation': 'implementation',
                    '4': 'implementation',
                    'test_implementation': 'test_implementation',
                    'testimplementation': 'test_implementation',
                    '5': 'test_implementation',
                    'testing': 'testing',
                    '6': 'testing',
                    'documentation': 'documentation',
                    '7': 'documentation',
                    'report': 'report',
                    '8': 'report'
                }

                failed_phase = phase_mapping.get(phase_name)

                if not failed_phase:
                    return {
                        'success': False,
                        'decision': decision,
                        'error': f'不正なフェーズ名: {phase_name}'
                    }

                return {
                    'success': True,
                    'decision': decision,
                    'failed_phase': failed_phase,
                    'abort_reason': None,
                    'error': None
                }

            elif decision in valid_decisions:
                # ABORT の場合、中止理由を抽出
                abort_reason = None
                if decision == 'ABORT':
                    reason_match = re.search(
                        r'(?:中止|ABORT)理由[:：]\s*(.+?)(?:\n\n|\n##|$)',
                        evaluation_content,
                        re.DOTALL
                    )
                    if reason_match:
                        abort_reason = reason_match.group(1).strip()
                    else:
                        abort_reason = '致命的な問題が発見されました'

                return {
                    'success': True,
                    'decision': decision,
                    'failed_phase': None,
                    'abort_reason': abort_reason,
                    'error': None
                }

            else:
                return {
                    'success': False,
                    'decision': decision,
                    'error': f'不明な判定タイプ: {decision}'
                }

        except Exception as e:
            return {
                'success': False,
                'decision': None,
                'error': f'判定タイプの決定中にエラー: {str(e)}'
            }

    def _extract_remaining_tasks(self, evaluation_content: str) -> List[Dict[str, Any]]:
        """
        評価内容から残タスクを抽出

        Args:
            evaluation_content: evaluation_report.mdの内容

        Returns:
            List[Dict[str, Any]]: 残タスクリスト
                - task: str - タスク内容
                - phase: str - 発見されたフェーズ
                - priority: str - 優先度（高/中/低）
        """
        remaining_tasks = []

        try:
            # 残タスクセクションを抽出
            # パターン: ## 残タスク または ## 残タスク一覧
            tasks_section_match = re.search(
                r'##\s*残タスク(?:一覧)?.*?\n(.*?)(?:\n##|$)',
                evaluation_content,
                re.DOTALL
            )

            if not tasks_section_match:
                print("[WARNING] 残タスクセクションが見つかりませんでした")
                return remaining_tasks

            tasks_text = tasks_section_match.group(1)

            # チェックボックス項目を抽出
            # パターン: - [ ] タスク内容（Phase: X、優先度: 高）
            task_lines = re.findall(
                r'- \[ \]\s*(.+?)(?:\n|$)',
                tasks_text
            )

            for task_line in task_lines:
                # タスク内容、Phase、優先度を抽出
                task_text = task_line

                # Phase抽出
                phase_match = re.search(r'(?:Phase|phase)[:：]\s*([^、,）)]+)', task_line)
                phase = phase_match.group(1).strip() if phase_match else 'unknown'

                # 優先度抽出
                priority_match = re.search(r'優先度[:：]\s*([高中低])', task_line)
                priority = priority_match.group(1) if priority_match else '中'

                # タスク本文から付加情報を削除
                task_clean = re.sub(r'[（(].*?[）)]', '', task_text).strip()

                remaining_tasks.append({
                    'task': task_clean,
                    'phase': phase,
                    'priority': priority
                })

            print(f"[INFO] 残タスクを {len(remaining_tasks)} 個抽出しました")

        except Exception as e:
            print(f"[WARNING] 残タスクの抽出中にエラー: {e}")

        return remaining_tasks

    def _handle_pass_with_issues(
        self,
        remaining_tasks: List[Dict],
        issue_number: int,
        evaluation_file: Path
    ) -> Dict[str, Any]:
        """
        PASS_WITH_ISSUES判定時の処理

        Args:
            remaining_tasks: 残タスクリスト
            issue_number: Issue番号
            evaluation_file: 評価レポートファイル

        Returns:
            Dict[str, Any]:
                - success: bool
                - created_issue_url: Optional[str]
                - error: Optional[str]
        """
        if not remaining_tasks:
            print("[INFO] 残タスクが0個のため、Issue作成をスキップします")
            return {
                'success': True,
                'created_issue_url': None,
                'error': None
            }

        try:
            # GitHubClientを使用してIssue作成
            evaluation_report_path = str(evaluation_file.relative_to(self.claude.working_dir.parent.parent))

            result = self.github.create_issue_from_evaluation(
                issue_number=issue_number,
                remaining_tasks=remaining_tasks,
                evaluation_report_path=evaluation_report_path
            )

            if result['success']:
                print(f"[INFO] 残タスク用Issueを作成しました: {result['issue_url']}")
                return {
                    'success': True,
                    'created_issue_url': result['issue_url'],
                    'error': None
                }
            else:
                print(f"[WARNING] Issue作成に失敗しました: {result['error']}")
                return {
                    'success': False,
                    'created_issue_url': None,
                    'error': result['error']
                }

        except Exception as e:
            print(f"[ERROR] Issue作成処理中にエラー: {e}")
            return {
                'success': False,
                'created_issue_url': None,
                'error': str(e)
            }

    def _handle_fail_phase_x(self, failed_phase: str) -> Dict[str, Any]:
        """
        FAIL_PHASE_X判定時の処理

        Args:
            failed_phase: 失敗したフェーズ名

        Returns:
            Dict[str, Any]:
                - success: bool
                - error: Optional[str]
        """
        try:
            print(f"[INFO] Phase {failed_phase} から再実行するため、メタデータを巻き戻します")

            # MetadataManagerを使用してメタデータ巻き戻し
            result = self.metadata.rollback_to_phase(failed_phase)

            if result['success']:
                print(f"[INFO] メタデータの巻き戻しが完了しました")
                print(f"[INFO] バックアップ: {result['backup_path']}")
                print(f"[INFO] 巻き戻されたフェーズ: {', '.join(result['rolled_back_phases'])}")
                return {
                    'success': True,
                    'error': None
                }
            else:
                print(f"[ERROR] メタデータの巻き戻しに失敗: {result['error']}")
                return {
                    'success': False,
                    'error': result['error']
                }

        except Exception as e:
            print(f"[ERROR] メタデータ巻き戻し処理中にエラー: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _handle_abort(self, abort_reason: str, issue_number: int) -> Dict[str, Any]:
        """
        ABORT判定時の処理

        Args:
            abort_reason: 中止理由
            issue_number: Issue番号

        Returns:
            Dict[str, Any]:
                - success: bool
                - error: Optional[str]
        """
        try:
            print(f"[INFO] ワークフローを中止します: {abort_reason}")

            # IssueをクローズGit
            issue_result = self.github.close_issue_with_reason(
                issue_number=issue_number,
                reason=abort_reason
            )

            if not issue_result['success']:
                print(f"[WARNING] Issueクローズに失敗: {issue_result['error']}")

            # PR番号を取得
            pr_number = self.github.get_pull_request_number(issue_number)

            if pr_number:
                # PRをクローズ
                pr_comment = f"## ⚠️ ワークフロー中止\n\n{abort_reason}\n\n*AI Workflow Phase 9 (Evaluation) - ABORT*"
                pr_result = self.github.close_pull_request(
                    pr_number=pr_number,
                    comment=pr_comment
                )

                if not pr_result['success']:
                    print(f"[WARNING] PRクローズに失敗: {pr_result['error']}")

            return {
                'success': True,
                'error': None
            }

        except Exception as e:
            print(f"[ERROR] ABORT処理中にエラー: {e}")
            return {
                'success': False,
                'error': str(e)
            }
