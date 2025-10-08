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
        'documentation': '06'
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
            phase_name: フェーズ名（requirements, design, test_scenario, implementation, testing, documentation）
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

        # ディレクトリを作成
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.execute_dir.mkdir(parents=True, exist_ok=True)
        self.review_dir.mkdir(parents=True, exist_ok=True)

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
        cost_usd: float = 0.0
    ):
        """
        フェーズステータスを更新

        Args:
            status: ステータス（pending, in_progress, completed, failed）
            output_file: 出力ファイル名（省略可）
            input_tokens: 入力トークン数
            output_tokens: 出力トークン数
            cost_usd: コスト（USD）
        """
        self.metadata.update_phase_status(
            phase_name=self.phase_name,
            status=status,
            output_file=output_file
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
        issue_number = int(self.metadata.data['issue_number'])

        self.github.post_workflow_progress(
            issue_number=issue_number,
            phase=self.phase_name,
            status=status,
            details=details
        )

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
        issue_number = int(self.metadata.data['issue_number'])

        self.github.post_review_result(
            issue_number=issue_number,
            phase=self.phase_name,
            result=result,
            feedback=feedback,
            suggestions=suggestions
        )

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
                tool_match = re.search(r"name='([^']+)'", message)
                if tool_match:
                    formatted_parts.append(f"**ツール**: `{tool_match.group(1)}`")

                formatted_parts.append("")
                formatted_parts.append("```")
                formatted_parts.append(message[:500] + "..." if len(message) > 500 else message)
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
        フェーズを実行してレビュー

        Returns:
            bool: 成功/失敗

        Notes:
            1. フェーズステータスをin_progressに更新
            2. GitHubに進捗報告
            3. execute()を実行
            4. review()を実行
            5. レビュー結果に応じてステータス更新
            6. GitHubにレビュー結果を投稿
        """
        try:
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
                self.update_phase_status(status='failed')
                self.post_progress(
                    status='failed',
                    details=f"実行エラー: {execute_result.get('error', 'Unknown error')}"
                )
                return False

            # レビュー実行
            review_result = self.review()

            result = review_result.get('result', 'FAIL')
            feedback = review_result.get('feedback')
            suggestions = review_result.get('suggestions', [])

            # レビュー結果を投稿
            self.post_review(
                result=result,
                feedback=feedback,
                suggestions=suggestions
            )

            # レビュー結果に応じてステータス更新
            if result == 'PASS' or result == 'PASS_WITH_SUGGESTIONS':
                self.update_phase_status(status='completed')
                self.post_progress(
                    status='completed',
                    details=f'{self.phase_name}フェーズが完了しました。'
                )
                return True
            else:
                # FAIL
                self.update_phase_status(status='failed')
                self.post_progress(
                    status='failed',
                    details=f'レビューで不合格となりました。フィードバックを確認してください。'
                )
                return False

        except Exception as e:
            # 予期しないエラー
            self.update_phase_status(status='failed')
            self.post_progress(
                status='failed',
                details=f'エラーが発生しました: {str(e)}'
            )
            raise
