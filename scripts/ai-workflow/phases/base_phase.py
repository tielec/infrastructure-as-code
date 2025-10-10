"""AI Workflow フェーズ基底クラス

各フェーズの共通インターフェースと機能を提供
- execute(): フェーズ実行
- review(): フェーズレビュー
- メタデータ管理
- Claude Agent SDK統合
- GitHub API統合
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List
from core.metadata_manager import MetadataManager
from core.claude_agent_client import ClaudeAgentClient
from core.github_client import GitHubClient


class BasePhase(ABC):
    """フェーズ基底クラス"""

    # フェーズ番号マッピング
    PHASE_NUMBERS = {
        'requirements': '01',
        'design': '02',
        'test_scenario': '03',
        'implementation': '04',
        'testing': '05',
        'documentation': '06',
        'report': '07'
    }

    def __init__(
        self,
        phase_name: str,
        working_dir: Path,
        metadata_manager: MetadataManager,
        claude_client: ClaudeAgentClient,
        github_client: GitHubClient
    ):
        """
        初期化

        Args:
            phase_name: フェーズ名（requirements, design, test_scenario, implementation, testing, documentation, report）
            working_dir: 作業ディレクトリ
            metadata_manager: メタデータマネージャー
            claude_client: Claude Agent SDKクライアント
            github_client: GitHub APIクライアント
        """
        self.phase_name = phase_name
        self.working_dir = working_dir
        self.metadata = metadata_manager
        self.claude = claude_client
        self.github = github_client

        # プロンプトディレクトリ（scripts/ai-workflow/prompts/{phase_name}/）
        self.prompts_dir = working_dir / 'prompts' / phase_name

        # フェーズディレクトリ（.ai-workflow/issue-{number}/01_requirements/）
        phase_number = self.PHASE_NUMBERS.get(phase_name, '00')
        self.phase_dir = self.metadata.workflow_dir / f'{phase_number}_{phase_name}'

        # サブディレクトリ
        self.output_dir = self.phase_dir / 'output'
        self.execute_dir = self.phase_dir / 'execute'
        self.review_dir = self.phase_dir / 'review'
        self.revise_dir = self.phase_dir / 'revise'

        # ディレクトリを作成
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.execute_dir.mkdir(parents=True, exist_ok=True)
        self.review_dir.mkdir(parents=True, exist_ok=True)
        self.revise_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def execute(self) -> Dict[str, Any]:
        """
        フェーズを実行

        Returns:
            Dict[str, Any]: 実行結果
                - success: bool - 成功/失敗
                - output: Any - 実行結果の出力
                - error: Optional[str] - エラーメッセージ

        Raises:
            NotImplementedError: サブクラスで実装必須
        """
        raise NotImplementedError("execute() must be implemented by subclass")

    @abstractmethod
    def review(self) -> Dict[str, Any]:
        """
        フェーズをレビュー

        Returns:
            Dict[str, Any]: レビュー結果
                - result: str - PASS/PASS_WITH_SUGGESTIONS/FAIL
                - feedback: str - フィードバック
                - suggestions: List[str] - 改善提案一覧

        Raises:
            NotImplementedError: サブクラスで実装必須
        """
        raise NotImplementedError("review() must be implemented by subclass")

    def load_prompt(self, prompt_type: str) -> str:
        """
        プロンプトファイルを読み込み

        Args:
            prompt_type: プロンプトタイプ（execute, review, etc.）

        Returns:
            str: プロンプトテキスト

        Raises:
            FileNotFoundError: プロンプトファイルが存在しない
        """
        prompt_file = self.prompts_dir / f'{prompt_type}.txt'

        if not prompt_file.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_file}\n"
                f"Expected path: {prompt_file.absolute()}"
            )

        return prompt_file.read_text(encoding='utf-8')

    def update_phase_status(
        self,
        status: str,
        output_file: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
        review_result: Optional[str] = None
    ):
        """
        フェーズステータスを更新

        Args:
            status: ステータス（pending, in_progress, completed, failed）
            output_file: 出力ファイル名（省略可）
            input_tokens: 入力トークン数
            output_tokens: 出力トークン数
            cost_usd: コスト（USD）
            review_result: レビュー結果（PASS/PASS_WITH_SUGGESTIONS/FAIL）
        """
        self.metadata.update_phase_status(
            phase_name=self.phase_name,
            status=status,
            output_file=output_file,
            review_result=review_result
        )

        # コストトラッキング更新
        if input_tokens > 0 or output_tokens > 0:
            self.metadata.add_cost(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd
            )

    def post_progress(
        self,
        status: str,
        details: Optional[str] = None
    ):
        """
        GitHubに進捗報告

        Args:
            status: ステータス（pending, in_progress, completed, failed）
            details: 詳細情報（省略可）
        """
        try:
            issue_number = int(self.metadata.data['issue_number'])

            self.github.post_workflow_progress(
                issue_number=issue_number,
                phase=self.phase_name,
                status=status,
                details=details
            )
            print(f"[INFO] GitHub Issue #{issue_number} に進捗を投稿しました: {status}")
        except Exception as e:
            print(f"[WARNING] GitHub投稿に失敗しました: {e}")

    def post_review(
        self,
        result: str,
        feedback: Optional[str] = None,
        suggestions: Optional[List[str]] = None
    ):
        """
        GitHubにレビュー結果を投稿

        Args:
            result: レビュー結果（PASS, PASS_WITH_SUGGESTIONS, FAIL）
            feedback: フィードバック（省略可）
            suggestions: 改善提案一覧（省略可）
        """
        try:
            issue_number = int(self.metadata.data['issue_number'])

            self.github.post_review_result(
                issue_number=issue_number,
                phase=self.phase_name,
                result=result,
                feedback=feedback,
                suggestions=suggestions
            )
            print(f"[INFO] GitHub Issue #{issue_number} にレビュー結果を投稿しました: {result}")
        except Exception as e:
            print(f"[WARNING] GitHub投稿に失敗しました: {e}")

    def post_output(
        self,
        output_content: str,
        title: Optional[str] = None
    ):
        """
        GitHubに成果物の内容を投稿

        Args:
            output_content: 成果物の内容（Markdown形式）
            title: タイトル（省略可、指定しない場合はフェーズ名を使用）
        """
        try:
            issue_number = int(self.metadata.data['issue_number'])

            # フェーズ名の日本語マッピング
            phase_names = {
                'requirements': '要件定義',
                'design': '設計',
                'test_scenario': 'テストシナリオ',
                'implementation': '実装',
                'testing': 'テスト',
                'documentation': 'ドキュメント',
                'report': 'レポート'
            }

            phase_jp = phase_names.get(self.phase_name, self.phase_name)
            header = title if title else f"{phase_jp}フェーズ - 成果物"

            body = f"## 📄 {header}\n\n"
            body += output_content
            body += "\n\n---\n"
            body += "*AI駆動開発自動化ワークフロー (Claude Agent SDK)*"

            self.github.post_comment(issue_number, body)
            print(f"[INFO] GitHub Issue #{issue_number} に成果物を投稿しました: {header}")
        except Exception as e:
            print(f"[WARNING] GitHub投稿に失敗しました: {e}")

    def execute_with_claude(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_turns: int = 50,
        verbose: bool = True,
        save_logs: bool = True,
        log_prefix: str = ''
    ) -> List[str]:
        """
        Claude Agent SDKでタスクを実行

        Args:
            prompt: タスクプロンプト
            system_prompt: システムプロンプト（省略可）
            max_turns: 最大ターン数
            verbose: 詳細ログ出力（リアルタイムメッセージ表示、デフォルト: True）
            save_logs: プロンプトとエージェントログを保存するか（デフォルト: True）
            log_prefix: ログファイル名のプレフィックス（例: 'review', 'execute'）

        Returns:
            List[str]: レスポンスメッセージのリスト
        """
        # Claude Agent SDKでタスク実行
        messages = self.claude.execute_task_sync(
            prompt=prompt,
            system_prompt=system_prompt,
            max_turns=max_turns,
            verbose=verbose
        )

        # ログ保存
        if save_logs:
            self._save_execution_logs(
                prompt=prompt,
                messages=messages,
                log_prefix=log_prefix
            )

        return messages

    def _save_execution_logs(
        self,
        prompt: str,
        messages: List[str],
        log_prefix: str = ''
    ):
        """
        プロンプトとエージェントログを保存

        Args:
            prompt: 実行したプロンプト
            messages: エージェントからのレスポンスメッセージ
            log_prefix: ログファイル名のプレフィックス（'execute' or 'review'）
        """
        # log_prefixに応じてディレクトリを選択
        if log_prefix == 'execute':
            target_dir = self.execute_dir
        elif log_prefix == 'review':
            target_dir = self.review_dir
        elif log_prefix == 'revise':
            target_dir = self.revise_dir
        else:
            # デフォルトはフェーズディレクトリ
            target_dir = self.phase_dir

        # プロンプトを保存
        prompt_file = target_dir / 'prompt.txt'
        prompt_file.write_text(prompt, encoding='utf-8')
        print(f"[INFO] プロンプトを保存: {prompt_file}")

        # エージェントログをマークダウン形式で整形
        formatted_log = self._format_agent_log(messages)
        agent_log_file = target_dir / 'agent_log.md'
        agent_log_file.write_text(formatted_log, encoding='utf-8')
        print(f"[INFO] エージェントログを保存: {agent_log_file}")

        # 生ログも保存（デバッグ用）
        raw_log_file = target_dir / 'agent_log_raw.txt'
        raw_log = '\n\n'.join(messages)
        raw_log_file.write_text(raw_log, encoding='utf-8')
        print(f"[INFO] 生ログを保存: {raw_log_file}")

    def _format_agent_log(self, messages: List[str]) -> str:
        """
        エージェントログをマークダウン形式に整形

        Args:
            messages: エージェントからのレスポンスメッセージ

        Returns:
            str: マークダウン形式の整形済みログ
        """
        import re
        from datetime import datetime

        formatted_parts = []
        formatted_parts.append("# Claude Agent 実行ログ")
        formatted_parts.append("")
        formatted_parts.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        formatted_parts.append("")
        formatted_parts.append("---")
        formatted_parts.append("")

        # メッセージを解析
        turn_count = 0
        session_id = None
        total_cost = 0.0
        total_duration_ms = 0
        num_turns = 0
        usage_info = {}

        for i, message in enumerate(messages, 1):
            # SystemMessageの処理
            if 'SystemMessage' in message and 'subtype' in message:
                turn_count += 1
                formatted_parts.append(f"## Turn {turn_count}: システム初期化")
                formatted_parts.append("")

                # セッションID抽出
                session_match = re.search(r"'session_id':\s*'([^']+)'", message)
                if session_match:
                    session_id = session_match.group(1)
                    formatted_parts.append(f"**セッションID**: `{session_id}`")

                # モデル情報抽出
                model_match = re.search(r"'model':\s*'([^']+)'", message)
                if model_match:
                    formatted_parts.append(f"**モデル**: {model_match.group(1)}")

                # 権限モード抽出
                permission_match = re.search(r"'permissionMode':\s*'([^']+)'", message)
                if permission_match:
                    formatted_parts.append(f"**権限モード**: {permission_match.group(1)}")

                # 利用可能ツール抽出
                tools_match = re.search(r"'tools':\s*\[([^\]]+)\]", message)
                if tools_match:
                    tools_str = tools_match.group(1)
                    tools = [t.strip().strip("'\"") for t in tools_str.split(',')]
                    formatted_parts.append(f"**利用可能ツール**: {', '.join(tools[:5])}... (他{len(tools)-5}個)")

                formatted_parts.append("")

            # AssistantMessageの処理
            elif 'AssistantMessage' in message and 'TextBlock' in message:
                turn_count += 1
                formatted_parts.append(f"## Turn {turn_count}: AI応答")
                formatted_parts.append("")

                # TextBlockの内容を抽出
                text_match = re.search(r"TextBlock\(text='(.*?)'\)", message, re.DOTALL)
                if text_match:
                    text_content = text_match.group(1)
                    # エスケープシーケンスを置換
                    text_content = text_content.replace('\\n', '\n')
                    text_content = text_content.replace('\\t', '\t')
                    text_content = text_content.replace('\\r', '\r')
                    text_content = text_content.replace("\\'", "'")
                    text_content = text_content.replace('\\"', '"')

                    formatted_parts.append(text_content)
                else:
                    formatted_parts.append("*(テキスト内容の抽出に失敗)*")

                formatted_parts.append("")

            # ToolUseMessageの処理
            elif 'ToolUse' in message:
                turn_count += 1
                formatted_parts.append(f"## Turn {turn_count}: ツール使用")
                formatted_parts.append("")

                # ツール名抽出
                tool_name = None
                tool_match = re.search(r"name='([^']+)'", message)
                if tool_match:
                    tool_name = tool_match.group(1)
                    formatted_parts.append(f"**ツール**: `{tool_name}`")
                    formatted_parts.append("")

                # input パラメータを抽出して整形
                input_match = re.search(r"input=(\{[^}]+\})", message)
                if input_match:
                    input_str = input_match.group(1)
                    # パラメータを抽出（簡易的なパース）
                    params = []
                    # 'key': 'value' または 'key': value の形式を抽出
                    param_pattern = r"'([^']+)':\s*'([^']+)'|'([^']+)':\s*([^',}\]]+)"
                    for match in re.finditer(param_pattern, input_str):
                        if match.group(1):  # 'key': 'value' 形式
                            params.append((match.group(1), match.group(2)))
                        elif match.group(3):  # 'key': value 形式
                            params.append((match.group(3), match.group(4).strip()))

                    if params:
                        formatted_parts.append("**パラメータ**:")
                        for key, value in params:
                            # 長い値は省略
                            if len(value) > 100:
                                value = value[:100] + "..."
                            formatted_parts.append(f"- `{key}`: `{value}`")
                    else:
                        # パースに失敗した場合は元のinputをそのまま表示
                        formatted_parts.append("**入力**:")
                        formatted_parts.append("```python")
                        formatted_parts.append(input_str)
                        formatted_parts.append("```")
                else:
                    # input が見つからない場合は、メッセージ全体を表示（デバッグ用）
                    formatted_parts.append("**詳細**:")
                    formatted_parts.append("```")
                    formatted_parts.append(message[:300] + "..." if len(message) > 300 else message)
                    formatted_parts.append("```")

                formatted_parts.append("")

            # ResultMessageの処理
            elif 'ResultMessage' in message:
                formatted_parts.append("## 実行結果サマリー")
                formatted_parts.append("")

                # 各種統計情報を抽出
                duration_match = re.search(r"duration_ms=(\d+)", message)
                if duration_match:
                    total_duration_ms = int(duration_match.group(1))
                    formatted_parts.append(f"**実行時間**: {total_duration_ms / 1000:.2f}秒")

                api_duration_match = re.search(r"duration_api_ms=(\d+)", message)
                if api_duration_match:
                    api_duration_ms = int(api_duration_match.group(1))
                    formatted_parts.append(f"**API実行時間**: {api_duration_ms / 1000:.2f}秒")

                turns_match = re.search(r"num_turns=(\d+)", message)
                if turns_match:
                    num_turns = int(turns_match.group(1))
                    formatted_parts.append(f"**ターン数**: {num_turns}")

                cost_match = re.search(r"total_cost_usd=([\d.]+)", message)
                if cost_match:
                    total_cost = float(cost_match.group(1))
                    formatted_parts.append(f"**コスト**: ${total_cost:.4f}")

                # usage情報を抽出
                usage_match = re.search(r"usage=(\{[^}]+\})", message)
                if usage_match:
                    usage_str = usage_match.group(1)
                    # 簡易パース（完全なJSONパーサーではない）
                    input_tokens_match = re.search(r"'input_tokens':\s*(\d+)", usage_str)
                    output_tokens_match = re.search(r"'output_tokens':\s*(\d+)", usage_str)
                    cache_creation_match = re.search(r"'cache_creation_input_tokens':\s*(\d+)", usage_str)
                    cache_read_match = re.search(r"'cache_read_input_tokens':\s*(\d+)", usage_str)

                    formatted_parts.append("")
                    formatted_parts.append("### トークン使用量")
                    if input_tokens_match:
                        formatted_parts.append(f"- 入力トークン: {int(input_tokens_match.group(1)):,}")
                    if output_tokens_match:
                        formatted_parts.append(f"- 出力トークン: {int(output_tokens_match.group(1)):,}")
                    if cache_creation_match:
                        formatted_parts.append(f"- キャッシュ作成: {int(cache_creation_match.group(1)):,}")
                    if cache_read_match:
                        formatted_parts.append(f"- キャッシュ読み込み: {int(cache_read_match.group(1)):,}")

                formatted_parts.append("")

        formatted_parts.append("---")
        formatted_parts.append("")
        formatted_parts.append("*このログは Claude Agent SDK の実行ログを整形したものです。*")
        formatted_parts.append("*生ログは `agent_log_raw.txt` を参照してください。*")

        return '\n'.join(formatted_parts)

    def run(self) -> bool:
        """
        フェーズを実行してレビュー（リトライ機能付き）

        Returns:
            bool: 成功/失敗

        Notes:
            1. フェーズステータスをin_progressに更新
            2. GitHubに進捗報告
            3. execute()を実行
            4. review()を実行
            5. FAIL時は最大3回までrevise()でリトライ
            6. レビュー結果に応じてステータス更新
            7. GitHubにレビュー結果を投稿
            8. Git自動commit & push（成功・失敗問わず実行）
        """
        MAX_RETRIES = 3

        git_manager = None
        final_status = 'failed'
        review_result = None

        try:
            # GitManagerを初期化
            from core.git_manager import GitManager
            git_manager = GitManager(
                repo_path=self.working_dir.parent.parent,  # リポジトリルート
                metadata_manager=self.metadata
            )

            # フェーズ開始
            self.update_phase_status(status='in_progress')
            self.post_progress(
                status='in_progress',
                details=f'{self.phase_name}フェーズを開始しました。'
            )

            # フェーズ実行
            execute_result = self.execute()

            if not execute_result.get('success', False):
                # 実行失敗
                final_status = 'failed'
                self.update_phase_status(status='failed')
                self.post_progress(
                    status='failed',
                    details=f"実行エラー: {execute_result.get('error', 'Unknown error')}"
                )
                return False

            # レビュー＆リトライループ
            retry_count = 0
            while retry_count <= MAX_RETRIES:
                # レビュー実行
                review_result_dict = self.review()

                result = review_result_dict.get('result', 'FAIL')
                feedback = review_result_dict.get('feedback')
                suggestions = review_result_dict.get('suggestions', [])

                # レビュー結果を投稿
                self.post_review(
                    result=result,
                    feedback=feedback,
                    suggestions=suggestions
                )

                # レビュー結果に応じて処理
                if result == 'PASS' or result == 'PASS_WITH_SUGGESTIONS':
                    # 合格 - レビュー結果を保存
                    final_status = 'completed'
                    review_result = result
                    self.update_phase_status(status='completed', review_result=result)
                    self.post_progress(
                        status='completed',
                        details=f'{self.phase_name}フェーズが完了しました。'
                    )
                    return True

                # FAIL - リトライチェック
                if retry_count >= MAX_RETRIES:
                    # リトライ回数上限に達した - 最終レビュー結果を保存
                    final_status = 'failed'
                    review_result = result
                    self.update_phase_status(status='failed', review_result=result)
                    self.post_progress(
                        status='failed',
                        details=f'レビューで不合格となりました（リトライ{MAX_RETRIES}回実施）。フィードバックを確認してください。'
                    )
                    return False

                # リトライ: revise()で修正
                retry_count += 1
                self.metadata.increment_retry_count(self.phase_name)
                print(f"[INFO] レビュー不合格のため修正を実施します（{retry_count}/{MAX_RETRIES}回目）")

                self.post_progress(
                    status='in_progress',
                    details=f'レビュー不合格のため修正を実施します（{retry_count}/{MAX_RETRIES}回目）。'
                )

                # revise()メソッドが存在するか確認
                if not hasattr(self, 'revise'):
                    print(f"[WARNING] {self.__class__.__name__}.revise()メソッドが実装されていません。リトライできません。")
                    final_status = 'failed'
                    self.update_phase_status(status='failed')
                    self.post_progress(
                        status='failed',
                        details='revise()メソッドが未実装のため、修正できません。'
                    )
                    return False

                # 修正実行
                revise_result = self.revise(review_feedback=feedback)

                if not revise_result.get('success', False):
                    # 修正失敗
                    print(f"[ERROR] 修正に失敗しました: {revise_result.get('error')}")
                    final_status = 'failed'
                    self.update_phase_status(status='failed')
                    self.post_progress(
                        status='failed',
                        details=f"修正エラー: {revise_result.get('error', 'Unknown error')}"
                    )
                    return False

                print(f"[INFO] 修正完了。再度レビューを実施します。")

            # ループを抜けた場合（通常は到達しない）
            return False

        except Exception as e:
            # 予期しないエラー
            final_status = 'failed'
            self.update_phase_status(status='failed')
            self.post_progress(
                status='failed',
                details=f'エラーが発生しました: {str(e)}'
            )
            raise

        finally:
            # Git自動commit & push（成功・失敗問わず実行）
            if git_manager:
                self._auto_commit_and_push(
                    git_manager=git_manager,
                    status=final_status,
                    review_result=review_result
                )

    def _auto_commit_and_push(
        self,
        git_manager,
        status: str,
        review_result: Optional[str]
    ):
        """
        Git自動commit & push

        Args:
            git_manager: GitManagerインスタンス
            status: フェーズステータス（completed/failed）
            review_result: レビュー結果（省略可）

        Notes:
            - エラーが発生してもPhase自体は失敗させない
            - ログに記録して継続
        """
        try:
            # Commit
            commit_result = git_manager.commit_phase_output(
                phase_name=self.phase_name,
                status=status,
                review_result=review_result
            )

            if not commit_result.get('success', False):
                print(f"[WARNING] Git commit failed: {commit_result.get('error')}")
                return

            commit_hash = commit_result.get('commit_hash')
            files_committed = commit_result.get('files_committed', [])

            if commit_hash:
                print(f"[INFO] Git commit successful: {commit_hash}")
                print(f"[INFO] Files committed: {len(files_committed)} files")
            else:
                print("[INFO] No files to commit (clean state)")
                return

            # Push
            push_result = git_manager.push_to_remote()

            if not push_result.get('success', False):
                print(f"[WARNING] Git push failed: {push_result.get('error')}")
                return

            retries = push_result.get('retries', 0)
            print(f"[INFO] Git push successful (retries: {retries})")

        except Exception as e:
            print(f"[WARNING] Git auto-commit & push failed: {e}")
            # Phase自体は失敗させない

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

        # テキストブロックを収集
        text_blocks = []
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
                text_content = text_content.replace("\\'", "'")
                text_content = text_content.replace('\\\\', '\\')

                # デバッグメッセージや前置きを除外
                # 明らかにレビュー本文ではないパターン
                skip_patterns = [
                    r"^\s*'\s+in\s+message:",  # デバッグ出力
                    r"^\s*\d+→",  # 行番号付きデバッグ出力
                    r"^I'll\s+conduct",  # 前置き
                    r"^Let me\s+",  # 前置き
                    r"^Now\s+let\s+me",  # 前置き
                    r"^Based on\s+my\s+.*review.*,\s*let me\s+provide",  # 前置き
                ]

                should_skip = False
                for skip_pattern in skip_patterns:
                    if re.match(skip_pattern, text_content.strip(), re.IGNORECASE):
                        should_skip = True
                        break

                # 短すぎるメッセージも除外（ただし判定キーワードが含まれている場合は除外しない）
                if len(text_content.strip()) < 50 and '**判定:' not in text_content:
                    should_skip = True

                if not should_skip:
                    text_blocks.append(text_content)

        # テキストブロックを結合
        full_text = "\n".join(text_blocks)

        # 判定を正規表現で抽出
        # フォーマット: **判定: PASS** または **判定: PASS_WITH_SUGGESTIONS** または単に **判定: PASS (行末)
        result_match = re.search(r'\*\*判定:\s*(PASS|PASS_WITH_SUGGESTIONS|FAIL)(?:\*\*|$)', full_text, re.IGNORECASE | re.MULTILINE)

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
