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
        max_turns: int = 50
    ) -> List[str]:
        """
        タスクを実行

        Args:
            prompt: タスクプロンプト
            system_prompt: システムプロンプト
            max_turns: 最大ターン数

        Returns:
            List[str]: レスポンスメッセージのリスト
        """
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            max_turns=max_turns,
            cwd=str(self.working_dir)
        )

        messages = []
        async for message in query(prompt=prompt, options=options):
            messages.append(str(message))

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
        max_turns: int = 50
    ) -> List[str]:
        """
        タスクを同期実行（anyio.runを使用）

        Args:
            prompt: タスクプロンプト
            system_prompt: システムプロンプト
            max_turns: 最大ターン数

        Returns:
            List[str]: レスポンスメッセージのリスト
        """
        return anyio.run(
            self.execute_task,
            prompt,
            system_prompt,
            max_turns
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
