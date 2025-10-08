"""Docker環境でClaude Agent SDK動作確認"""
import sys
from pathlib import Path
from core.claude_agent_client import ClaudeAgentClient

def main():
    """簡単な動作確認"""
    print("[INFO] Docker環境でClaude Agent SDK動作確認...")

    client = ClaudeAgentClient(working_dir=Path.cwd())

    # 簡単な計算タスク
    prompt = "2 + 2の計算結果を教えてください。簡潔に答えだけ返してください。"

    print(f"[PROMPT] {prompt}")

    try:
        messages = client.execute_task_sync(
            prompt=prompt,
            max_turns=1
        )

        print(f"[RESPONSE]")
        for msg in messages:
            print(msg)

        print("[OK] Claude Agent SDK動作確認完了")
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
