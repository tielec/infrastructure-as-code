"""Phase 1レビュープロセス 統合テスト

レビュー機能の統合テスト:
- 既存のrequirements.mdを読み込み
- Claude Agent SDKでレビュー実行
- レビュー結果をパース
- GitHub Issueにコメント投稿
"""
import sys
import os
import pytest
from pathlib import Path
from git import Repo
from core.metadata_manager import MetadataManager
from core.claude_agent_client import ClaudeAgentClient
from core.github_client import GitHubClient
from phases.requirements import RequirementsPhase


# テストマーカー
pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_docker,
    pytest.mark.requires_github,
    pytest.mark.requires_claude,
    pytest.mark.slow
]


def _get_repo_root() -> Path:
    """Gitリポジトリのルートディレクトリを取得"""
    try:
        repo = Repo(search_parent_directories=True)
        return Path(repo.working_dir)
    except Exception:
        return Path.cwd()


def main():
    """レビュープロセステスト"""
    print("[INFO] Phase 1レビュープロセステスト開始...")

    # 環境変数チェック
    github_token = os.getenv('GITHUB_TOKEN')
    github_repository = os.getenv('GITHUB_REPOSITORY')
    claude_token = os.getenv('CLAUDE_CODE_OAUTH_TOKEN')

    if not github_token or not github_repository:
        print("[ERROR] GITHUB_TOKEN and GITHUB_REPOSITORY environment variables are required.")
        sys.exit(1)

    if not claude_token:
        print("[WARN] CLAUDE_CODE_OAUTH_TOKEN is not set.")

    issue_number = "304"
    repo_root = _get_repo_root()
    workflow_dir = repo_root / '.ai-workflow' / f'issue-{issue_number}'
    metadata_path = workflow_dir / 'metadata.json'

    print(f"[INFO] Repo root: {repo_root}")
    print(f"[INFO] Workflow directory: {workflow_dir}")
    print(f"[INFO] Metadata path: {metadata_path}")

    if not metadata_path.exists():
        print(f"[ERROR] Workflow metadata not found")
        sys.exit(1)

    # requirements.mdの存在確認（新しいディレクトリ構造）
    requirements_file = workflow_dir / '01_requirements' / 'output' / 'requirements.md'
    if not requirements_file.exists():
        print(f"[ERROR] requirements.md not found: {requirements_file}")
        sys.exit(1)

    print(f"[OK] requirements.md found: {requirements_file}")
    print(f"[INFO] File size: {requirements_file.stat().st_size} bytes")

    # クライアント初期化
    print("[INFO] Initializing clients...")
    metadata_manager = MetadataManager(metadata_path)
    claude_client = ClaudeAgentClient(working_dir=repo_root)
    github_client = GitHubClient(token=github_token, repository=github_repository)
    print("[OK] Clients initialized")

    # Phase 1初期化
    print("[INFO] Initializing Phase 1...")
    phase = RequirementsPhase(
        working_dir=Path(__file__).parent,
        metadata_manager=metadata_manager,
        claude_client=claude_client,
        github_client=github_client
    )
    print("[OK] Phase 1 initialized")

    # review()のみ実行
    print("[INFO] Executing review()...")
    print("[INFO] This may take 3-5 minutes (Claude Agent SDK analyzing requirements.md)...")

    try:
        review_result = phase.review()

        print(f"\n{'='*60}")
        print("[REVIEW RESULT]")
        print(f"{'='*60}")
        print(f"Result: {review_result.get('result')}")
        print(f"\nFeedback:")
        print(review_result.get('feedback', 'N/A'))

        suggestions = review_result.get('suggestions', [])
        if suggestions:
            print(f"\nSuggestions ({len(suggestions)}):")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"  {i}. {suggestion}")
        print(f"{'='*60}\n")

        # GitHub投稿
        print("[INFO] Posting review result to GitHub...")
        phase.post_review(
            result=review_result.get('result'),
            feedback=review_result.get('feedback'),
            suggestions=review_result.get('suggestions', [])
        )
        print("[OK] Review result posted to GitHub Issue #304")

        # 結果判定
        if review_result.get('result') in ['PASS', 'PASS_WITH_SUGGESTIONS']:
            print(f"\n[OK] Review {review_result.get('result')}")
            sys.exit(0)
        else:
            print(f"\n[WARN] Review FAILED")
            sys.exit(1)

    except Exception as e:
        print(f"[ERROR] Review failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
