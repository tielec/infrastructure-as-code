"""Claude Agent SDK クライアント

Claude Code headless modeを使ってAIエージェントを実行
- Claude Pro Max契約を活用
- Read/Write/Edit/Bash/Grep/Globツールが使える
- 自律的にタスクを実行
"""
import os
import anyio
from pathlib import Path
from typing import Optional, List, Dict
from claude_agent_sdk import query, ClaudeAgentOptions


class ClaudeAgentClient:
    """Claude Agent SDK クライアント"""

    def __init__(self, working_dir: Optional[Path] = None, model: Optional[str] = None):
        """
        初期化

        Args:
            working_dir: 作業ディレクトリ（省略時はカレントディレクトリ）
            model: 使用するClaudeモデル（省略時はClaude Code Pro Maxのデフォルトモデルを使用）
                  - CLAUDE_CODE_OAUTH_TOKEN 使用時: デフォルトで claude-sonnet-4-5-20250929（最新Sonnet）
                  - ANTHROPIC_API_KEY 使用時: 明示的に指定が必要
        """
        self.working_dir = working_dir or Path.cwd()
        # CLAUDE_CODE_OAUTH_TOKEN を使う場合は強力なモデルを使用
        # model が指定されていない場合は、Claude Code Pro Max のデフォルトモデルを使用
        self.model = model

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

        Raises:
            ValueError: CLAUDE_CODE_OAUTH_TOKEN が設定されていない場合
        """
        # CLAUDE_CODE_OAUTH_TOKEN が設定されているか確認
        if not os.environ.get('CLAUDE_CODE_OAUTH_TOKEN'):
            raise ValueError(
                "CLAUDE_CODE_OAUTH_TOKEN が設定されていません。\n"
                "Claude Agent SDK は CLAUDE_CODE_OAUTH_TOKEN (Claude Code Pro Max) を使用します。\n"
                "設定方法: export CLAUDE_CODE_OAUTH_TOKEN='sk-ant-oat01-...'\n"
                "詳細は DOCKER_AUTH_SETUP.md を参照してください。"
            )

        # 環境変数でBashコマンド承認スキップを有効化（Docker環境内で安全）
        # Note: すでにDocker containerで隔離されているため、セキュリティリスクは限定的
        os.environ['CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS'] = '1'

        print("[INFO] Using CLAUDE_CODE_OAUTH_TOKEN for Claude Agent SDK (Claude Code Pro Max)")

        # ClaudeAgentOptions の設定
        options_kwargs = {
            'system_prompt': system_prompt,
            'max_turns': max_turns,
            'cwd': str(self.working_dir),
            'permission_mode': 'bypassPermissions',  # すべてのツール使用を自動承認（Docker環境内で安全）
        }

        # model が指定されている場合のみ追加
        # デフォルト（model=None）の場合は Claude Code Pro Max のデフォルトモデル（Sonnet 4.5）を使用
        if self.model is not None:
            options_kwargs['model'] = self.model

        options = ClaudeAgentOptions(**options_kwargs)

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
                        if 'name=' in message_str:
                            # ツール名を抽出
                            name_start = message_str.find('name=') + 6
                            name_end = message_str.find('\'', name_start)
                            tool_name = message_str[name_start:name_end]

                            # 詳細ログを出力
                            print(f"[AGENT ACTION] Using tool: {tool_name}")

                            # ツールパラメータを抽出（input=以降、次のフィールドの手前まで）
                            if 'input=' in message_str:
                                params_start = message_str.find('input=') + 6
                                # ')' が次のフィールドの開始なので、そこまでを取得
                                # ToolUseBlock(id='...', name='...', input={...}) の構造
                                # input= の後から最後の ')' の手前までが input の内容

                                # より正確に抽出: input= から次の '), ' または末尾の ')' まで
                                # まず 'ToolUseBlock' の終わりを探す
                                toolblock_end = message_str.find(')]', params_start)
                                if toolblock_end == -1:
                                    toolblock_end = len(message_str)

                                params_str = message_str[params_start:toolblock_end].strip()
                                # 最後の ')' を除去
                                if params_str.endswith(')'):
                                    params_str = params_str[:-1]

                                # 長すぎる場合は省略（最初の500文字）
                                if len(params_str) > 500:
                                    params_str = params_str[:500] + "..."

                                print(f"[AGENT ACTION] Parameters: {params_str}")

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
