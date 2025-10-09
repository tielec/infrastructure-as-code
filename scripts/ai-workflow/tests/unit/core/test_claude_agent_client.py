"""Claude Agent Client ユニットテスト

Claude Agent SDKの基本的な動作確認
"""
import pytest
from pathlib import Path
from core.claude_agent_client import ClaudeAgentClient


@pytest.mark.unit
@pytest.mark.requires_claude
class TestClaudeAgentClient:
    """ClaudeAgentClientクラスのユニットテスト"""

    def test_client_initialization(self, repo_root):
        """クライアントの初期化テスト"""
        client = ClaudeAgentClient(working_dir=repo_root)
        assert client.working_dir == repo_root

    def test_simple_task_execution(self, repo_root):
        """簡単なタスク実行テスト"""
        client = ClaudeAgentClient(working_dir=repo_root)

        prompt = "2 + 2の計算結果を教えてください。簡潔に答えだけ返してください。"

        messages = client.execute_task_sync(
            prompt=prompt,
            max_turns=1,
            verbose=False
        )

        assert len(messages) > 0
        # レスポンスに"4"が含まれることを確認
        full_response = '\n'.join(str(msg) for msg in messages)
        assert '4' in full_response
