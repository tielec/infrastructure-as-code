"""Docker環境 統合テスト

Docker環境でのClaude Agent SDK動作確認
"""
import pytest
from pathlib import Path
from core.claude_agent_client import ClaudeAgentClient


pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_docker,
    pytest.mark.requires_claude
]


def test_docker_claude_agent_execution(repo_root):
    """Docker環境でのClaude Agent SDK実行テスト"""
    client = ClaudeAgentClient(working_dir=repo_root)

    # 簡単な計算タスク
    prompt = "2 + 2の計算結果を教えてください。簡潔に答えだけ返してください。"

    messages = client.execute_task_sync(
        prompt=prompt,
        max_turns=1,
        verbose=True
    )

    assert len(messages) > 0

    # レスポンスに"4"が含まれることを確認
    full_response = '\n'.join(str(msg) for msg in messages)
    assert '4' in full_response

    print(f"[OK] Docker環境でClaude Agent SDK動作確認完了")
