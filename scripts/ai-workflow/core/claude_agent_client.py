"""Claude Agent SDK クライアント

Claude Code headless modeを使ってAIエージェントを実行
- Claude Pro Max契約を活用
- Read/Write/Edit/Bash/Grep/Globツールが使える
- 自律的にタスクを実行
"""
import anyio
from pathlib import Path
from typing import Optional, List, Dict
from claude_agent_sdk import query, ClaudeAgentOptions


class ClaudeAgentClient:
    """Claude Agent SDK クライアント"""

    def __init__(self, working_dir: Optional[Path] = None):
        """
        初期化

        Args:
            working_dir: 作業ディレクトリ（省略時はカレントディレクトリ）
        """
        self.working_dir = working_dir or Path.cwd()

    async def execute_task(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_turns: int = 50,
        verbose: bool = True
    ) -> List[str]:
        """
        タスクを実行

        Args:
            prompt: タスクプロンプト
            system_prompt: システムプロンプト
            max_turns: 最大ターン数
            verbose: 詳細ログ出力（リアルタイムメッセージ表示）

        Returns:
            List[str]: レスポンスメッセージのリスト
        """
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            max_turns=max_turns,
            cwd=str(self.working_dir),
            permission_mode='acceptEdits'  # 編集を自動的に受け入れる
        )

        messages = []
        async for message in query(prompt=prompt, options=options):
            message_str = str(message)
            messages.append(message_str)

            # リアルタイムログ出力
            if verbose:
                # AssistantMessageの場合は思考内容を表示
                if 'AssistantMessage' in message_str:
                    # TextBlockを抽出して表示（全文表示）
                    if 'TextBlock(text=' in message_str:
                        start = message_str.find('TextBlock(text=') + 16
                        end = message_str.find('\')', start)
                        if end > start:
                            text = message_str[start:end]
                            print(f"[AGENT THINKING] {text}")
                    # ToolUseBlockを抽出して表示（詳細情報含む）
                    elif 'ToolUseBlock' in message_str:
                        # メッセージ全体を表示（デバッグ用）
                        print(f"[AGENT ACTION DEBUG] Full message: {message_str[:500]}")

                        if 'name=' in message_str:
                            # ツール名を抽出
                            name_start = message_str.find('name=') + 6
                            name_end = message_str.find('\'', name_start)
                            tool_name = message_str[name_start:name_end]

                            # ツールパラメータを抽出
                            params_info = ""
                            if 'input=' in message_str:
                                params_start = message_str.find('input=') + 6
                                # 次のフィールド区切り(, id=)を探す
                                params_end = message_str.find(', id=', params_start)
                                if params_end > params_start:
                                    params_info = message_str[params_start:params_end]

                            # 詳細ログを出力
                            print(f"[AGENT ACTION] Using tool: {tool_name}")
                            if params_info:
                                print(f"[AGENT ACTION] Parameters: {params_info}")
                            else:
                                print(f"[AGENT ACTION DEBUG] No parameters found (input= exists: {'input=' in message_str})")

        return messages

    async def execute_task_from_file(
        self,
        prompt_file: Path,
        template_vars: Optional[Dict[str, str]] = None,
        system_prompt: Optional[str] = None,
        max_turns: int = 50
    ) -> List[str]:
        """
        プロンプトファイルからタスクを実行

        Args:
            prompt_file: プロンプトファイルパス
            template_vars: テンプレート変数（{variable_name}を置換）
            system_prompt: システムプロンプト
            max_turns: 最大ターン数

        Returns:
            List[str]: レスポンスメッセージのリスト
        """
        # プロンプトファイルを読み込み
        prompt = prompt_file.read_text(encoding='utf-8')

        # テンプレート変数を置換
        if template_vars:
            for key, value in template_vars.items():
                prompt = prompt.replace(f'{{{key}}}', value)

        return await self.execute_task(
            prompt=prompt,
            system_prompt=system_prompt,
            max_turns=max_turns
        )

    def execute_task_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_turns: int = 50,
        verbose: bool = True
    ) -> List[str]:
        """
        タスクを同期実行（anyio.runを使用）

        Args:
            prompt: タスクプロンプト
            system_prompt: システムプロンプト
            max_turns: 最大ターン数
            verbose: 詳細ログ出力（リアルタイムメッセージ表示）

        Returns:
            List[str]: レスポンスメッセージのリスト
        """
        return anyio.run(
            self.execute_task,
            prompt,
            system_prompt,
            max_turns,
            verbose
        )

    def execute_task_from_file_sync(
        self,
        prompt_file: Path,
        template_vars: Optional[Dict[str, str]] = None,
        system_prompt: Optional[str] = None,
        max_turns: int = 50
    ) -> List[str]:
        """
        プロンプトファイルからタスクを同期実行

        Args:
            prompt_file: プロンプトファイルパス
            template_vars: テンプレート変数
            system_prompt: システムプロンプト
            max_turns: 最大ターン数

        Returns:
            List[str]: レスポンスメッセージのリスト
        """
        return anyio.run(
            self.execute_task_from_file,
            prompt_file,
            template_vars,
            system_prompt,
            max_turns
        )
