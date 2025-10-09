"""Phase 3（テストシナリオフェーズ）の動作確認スクリプト"""
import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.metadata_manager import MetadataManager
from core.claude_agent_client import ClaudeAgentClient
from core.github_client import GitHubClient
from phases.test_scenario import TestScenarioPhase


def test_phase3():
    """Phase 3の動作確認"""

    print("[INFO] Phase 3（テストシナリオ）テスト開始...")

    # 環境変数からリポジトリ情報を取得
    github_repo = os.environ.get('GITHUB_REPOSITORY', 'tielec/infrastructure-as-code')
    github_token = os.environ.get('GITHUB_TOKEN', '')

    # working_dirを設定（Dockerコンテナ内では/workspace）
    working_dir = Path('/workspace/scripts/ai-workflow')

    # メタデータファイルのパス
    workflow_dir = Path('/workspace/.ai-workflow/issue-304')
    metadata_file = workflow_dir / 'metadata.json'

    print(f"[INFO] Workflow directory: {workflow_dir}")
    print(f"[INFO] Metadata file: {metadata_file}")

    # メタデータが存在するか確認
    if not metadata_file.exists():
        print("[ERROR] metadata.jsonが存在しません。Phase 1を先に実行してください。")
        return False

    # Phase 2の成果物が存在するか確認
    design_file = workflow_dir / '02_design' / 'output' / 'design.md'
    if not design_file.exists():
        print(f"[ERROR] Phase 2の成果物が見つかりません: {design_file}")
        return False

    print(f"[INFO] Phase 2の成果物を確認: {design_file}")

    # 各クライアントを初期化
    metadata_manager = MetadataManager(metadata_file)
    claude_client = ClaudeAgentClient(working_dir=Path('/workspace'))
    github_client = GitHubClient(token=github_token, repository=github_repo)

    # Phase 3を初期化
    phase3 = TestScenarioPhase(
        working_dir=working_dir,
        metadata_manager=metadata_manager,
        claude_client=claude_client,
        github_client=github_client
    )

    # Phase 3を実行
    print("[INFO] Phase 3実行中...")
    result = phase3.execute()

    if not result['success']:
        print(f"[ERROR] Phase 3が失敗しました: {result.get('error')}")
        return False

    print(f"[SUCCESS] Phase 3が成功しました: {result['output']}")

    # Phase 3のレビューを実行
    print("[INFO] Phase 3レビュー実行中...")
    review_result = phase3.review()

    print(f"[INFO] レビュー判定: {review_result['result']}")

    if review_result['result'] == 'FAIL':
        print("[WARNING] レビューが失敗しました。")
        print(f"[INFO] フィードバック（最初の500文字）: {review_result['feedback'][:500]}...")

        # 修正を実行
        print("[INFO] Phase 3修正実行中...")
        revise_result = phase3.revise(review_result['feedback'])

        if not revise_result['success']:
            print(f"[ERROR] 修正が失敗しました: {revise_result.get('error')}")
            return False

        print(f"[SUCCESS] 修正が成功しました: {revise_result['output']}")

        # 再度レビュー
        print("[INFO] 再レビュー実行中...")
        review_result = phase3.review()
        print(f"[INFO] 再レビュー判定: {review_result['result']}")

    print("[SUCCESS] Phase 3テスト完了")
    return True


if __name__ == '__main__':
    try:
        success = test_phase3()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[ERROR] テスト中に例外が発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
