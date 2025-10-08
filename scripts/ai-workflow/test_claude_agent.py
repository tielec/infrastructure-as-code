"""Claude Agent SDK 動作確認テスト"""
import sys
import shutil
from pathlib import Path
from core.claude_agent_client import ClaudeAgentClient

def main():
    """簡単な動作確認"""
    # Claude Code の場所を確認
    claude_path = shutil.which("claude")
    print(f"[DEBUG] Claude Code path: {claude_path}")

    if not claude_path:
        print("[ERROR] Claude Code not found in PATH")
        sys.exit(1)

    client = ClaudeAgentClient(working_dir=Path.cwd())

    print("[INFO] Claude Agent SDK動作確認...")

    # 簡単な計算タスク
    prompt = "2 + 2の計算結果を教えてください。簡潔に答えだけ返してください。"

    print(f"[PROMPT] {prompt}")

    messages = client.execute_task_sync(
        prompt=prompt,
        max_turns=1
    )

    print(f"[RESPONSE]")
    for msg in messages:
        print(msg)

    print("[OK] Claude Agent SDK動作確認完了")

if __name__ == '__main__':
    main()
