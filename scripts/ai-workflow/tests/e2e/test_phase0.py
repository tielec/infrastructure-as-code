"""Phase 0（プロジェクト計画フェーズ）の動作確認スクリプト"""
import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.metadata_manager import MetadataManager
from core.claude_agent_client import ClaudeAgentClient
from core.github_client import GitHubClient
from phases.planning import PlanningPhase


def test_phase0():
    """Phase 0の動作確認"""

    print("[INFO] Phase 0（プロジェクト計画）テスト開始...")

    # 環境変数からリポジトリ情報を取得
    github_repo = os.environ.get('GITHUB_REPOSITORY', 'tielec/infrastructure-as-code')
    github_token = os.environ.get('GITHUB_TOKEN', '')

    # working_dirを設定（Dockerコンテナ内では/workspace）
    working_dir = Path('/workspace/scripts/ai-workflow')

    # メタデータファイルのパス
    workflow_dir = Path('/workspace/.ai-workflow/issue-313')
    metadata_file = workflow_dir / 'metadata.json'

    print(f"[INFO] Workflow directory: {workflow_dir}")
    print(f"[INFO] Metadata file: {metadata_file}")

    # 各クライアントを初期化
    metadata_manager = MetadataManager(metadata_file)
    claude_client = ClaudeAgentClient(working_dir=Path('/workspace'))
    github_client = GitHubClient(token=github_token, repository=github_repo)

    # Phase 0を初期化
    phase0 = PlanningPhase(
        working_dir=working_dir,
        metadata_manager=metadata_manager,
        claude_client=claude_client,
        github_client=github_client
    )

    # Phase 0を実行
    print("[INFO] Phase 0実行中...")
    result = phase0.execute()

    if not result['success']:
        print(f"[ERROR] Phase 0が失敗しました: {result.get('error')}")
        return False

    print(f"[SUCCESS] Phase 0が成功しました: {result['output']}")

    # metadata.jsonから戦略判断を確認
    decisions = metadata_manager.data['design_decisions']
    print(f"[INFO] 実装戦略: {decisions.get('implementation_strategy')}")
    print(f"[INFO] テスト戦略: {decisions.get('test_strategy')}")
    print(f"[INFO] テストコード戦略: {decisions.get('test_code_strategy')}")

    # Phase 0のレビューを実行
    print("[INFO] Phase 0レビュー実行中...")
    review_result = phase0.review()

    print(f"[INFO] レビュー判定: {review_result['result']}")

    if review_result['result'] == 'FAIL':
        print("[WARNING] レビューが失敗しました。")
        print(f"[INFO] フィードバック（最初の500文字）: {review_result['feedback'][:500]}...")

        # 修正を実行
        print("[INFO] Phase 0修正実行中...")
        revise_result = phase0.revise(review_result['feedback'])

        if not revise_result['success']:
            print(f"[ERROR] 修正が失敗しました: {revise_result.get('error')}")
            return False

        print(f"[SUCCESS] 修正が成功しました: {revise_result['output']}")

        # 再度レビュー
        print("[INFO] 再レビュー実行中...")
        review_result = phase0.review()
        print(f"[INFO] 再レビュー判定: {review_result['result']}")

    # 戦略判断が正しく保存されているか確認
    decisions = metadata_manager.data['design_decisions']

    if decisions.get('implementation_strategy') not in ['CREATE', 'EXTEND', 'REFACTOR']:
        print(f"[ERROR] 実装戦略が正しく設定されていません: {decisions.get('implementation_strategy')}")
        return False

    if decisions.get('test_strategy') is None:
        print("[ERROR] テスト戦略が設定されていません")
        return False

    if decisions.get('test_code_strategy') not in ['EXTEND_TEST', 'CREATE_TEST', 'BOTH_TEST']:
        print(f"[ERROR] テストコード戦略が正しく設定されていません: {decisions.get('test_code_strategy')}")
        return False

    print("[SUCCESS] Phase 0テスト完了")
    print("[SUCCESS] 戦略判断が正しく保存されました")
    return True


if __name__ == '__main__':
    try:
        success = test_phase0()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[ERROR] テスト中に例外が発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
