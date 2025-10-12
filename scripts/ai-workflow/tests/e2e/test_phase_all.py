"""E2Eテスト - 全フェーズ一括実行機能 (--phase all)

このテストファイルは、--phase allオプションによる全フェーズ一括実行機能のE2Eテストを提供します。
実際にClaude API、GitHub API、Git操作を実行し、エンドツーエンドでの動作を検証します。

注意:
- このテストは実行時間が長い（30-60分）ため、@pytest.mark.slowでマークされています
- CI環境では選択的に実行されます（pytest -m slow で実行）
- 環境変数 GITHUB_TOKEN, CLAUDE_CODE_OAUTH_TOKEN が必要です
"""

import pytest
import subprocess
import json
import os
from pathlib import Path
from git import Repo


@pytest.mark.slow
@pytest.mark.e2e
class TestPhaseAllE2E:
    """全フェーズ一括実行のE2Eテストクラス"""

    @pytest.fixture
    def test_issue_number(self):
        """テスト用Issue番号

        Note: 実際のテストでは専用のテストIssueを使用してください
        """
        return "999"

    @pytest.fixture
    def repo_root(self):
        """リポジトリルートディレクトリ"""
        try:
            repo = Repo(search_parent_directories=True)
            return Path(repo.working_dir)
        except Exception:
            return Path.cwd()

    @pytest.fixture
    def cleanup_test_workflow(self, repo_root, test_issue_number):
        """テスト用ワークフローのクリーンアップ（テスト後）"""
        yield  # テスト実行

        # テスト後のクリーンアップ
        workflow_dir = repo_root / '.ai-workflow' / f'issue-{test_issue_number}'
        if workflow_dir.exists():
            import shutil
            shutil.rmtree(workflow_dir)
            print(f"[CLEANUP] Removed test workflow directory: {workflow_dir}")

    def test_full_workflow_all_phases(self, repo_root, test_issue_number, cleanup_test_workflow):
        """TC-E-001: 全フェーズ実行の正常系（完全統合テスト）

        目的: 実際に全フェーズを実行し、エンドツーエンドで正常に動作することを検証

        前提条件:
        - テスト用Issueが存在する（例: Issue #999）
        - 環境変数が設定されている（GITHUB_TOKEN, CLAUDE_CODE_OAUTH_TOKEN）
        - リポジトリがクリーンな状態
        - テスト用ブランチが作成可能

        実行時間: 30-60分
        """
        # 環境変数チェック
        if not os.getenv('GITHUB_TOKEN'):
            pytest.skip("GITHUB_TOKEN not set")
        if not os.getenv('CLAUDE_CODE_OAUTH_TOKEN'):
            pytest.skip("CLAUDE_CODE_OAUTH_TOKEN not set")

        # テスト用Issue URLを環境変数から取得、またはデフォルトを使用
        github_repository = os.getenv('GITHUB_REPOSITORY', 'tielec/infrastructure-as-code')
        issue_url = f"https://github.com/{github_repository}/issues/{test_issue_number}"

        # 1. ワークフロー初期化
        print(f"\n[TEST] Step 1: Initializing workflow for issue {test_issue_number}")
        init_result = subprocess.run(
            ['python', 'main.py', 'init', '--issue-url', issue_url],
            cwd=repo_root / 'scripts' / 'ai-workflow',
            capture_output=True,
            text=True,
            timeout=60
        )

        # 初期化の結果を確認
        print(f"[TEST] Init stdout: {init_result.stdout}")
        if init_result.returncode != 0:
            print(f"[TEST] Init stderr: {init_result.stderr}")
            pytest.fail(f"Workflow initialization failed: {init_result.stderr}")

        # metadata.jsonが作成されたことを確認
        workflow_dir = repo_root / '.ai-workflow' / f'issue-{test_issue_number}'
        metadata_path = workflow_dir / 'metadata.json'
        assert metadata_path.exists(), "metadata.jsonが作成されていない"
        print(f"[TEST] metadata.json created: {metadata_path}")

        # 2. 全フェーズ実行
        print(f"\n[TEST] Step 2: Executing all phases for issue {test_issue_number}")
        print(f"[TEST] This will take 30-60 minutes...")

        execute_result = subprocess.run(
            ['python', 'main.py', 'execute', '--phase', 'all', '--issue', test_issue_number],
            cwd=repo_root / 'scripts' / 'ai-workflow',
            capture_output=True,
            text=True,
            timeout=4800  # 80分タイムアウト（余裕を持たせる）
        )

        # 実行結果を表示
        print(f"\n[TEST] Execute stdout:\n{execute_result.stdout}")
        if execute_result.stderr:
            print(f"\n[TEST] Execute stderr:\n{execute_result.stderr}")

        # 3. 実行結果確認
        assert execute_result.returncode == 0, \
            f"全フェーズ実行が失敗しました（終了コード: {execute_result.returncode}）"

        assert 'All phases completed successfully!' in execute_result.stdout, \
            "成功メッセージが表示されていない"

        # 4. メタデータ確認
        print(f"\n[TEST] Step 3: Verifying metadata.json")
        with open(metadata_path) as f:
            metadata = json.load(f)

        # 全フェーズのステータスが completed であることを確認
        expected_phases = [
            'requirements', 'design', 'test_scenario', 'implementation',
            'test_implementation', 'testing', 'documentation', 'report'
        ]

        for phase in expected_phases:
            assert phase in metadata['phases'], f"フェーズ {phase} がメタデータに存在しない"
            assert metadata['phases'][phase]['status'] == 'completed', \
                f"フェーズ {phase} のステータスが completed ではない: {metadata['phases'][phase]['status']}"
            assert metadata['phases'][phase]['review_result'] in ['PASS', 'PASS_WITH_SUGGESTIONS'], \
                f"フェーズ {phase} のレビュー結果が PASS または PASS_WITH_SUGGESTIONS ではない: {metadata['phases'][phase]['review_result']}"
            print(f"[TEST] Phase {phase}: {metadata['phases'][phase]['status']} - {metadata['phases'][phase]['review_result']}")

        # 5. 出力ファイル確認
        print(f"\n[TEST] Step 4: Verifying output files")
        for phase in expected_phases:
            # 各フェーズのディレクトリが存在することを確認
            phase_dirs = list(workflow_dir.glob(f'*{phase}*'))
            assert len(phase_dirs) > 0, f"フェーズ {phase} のディレクトリが存在しない"
            print(f"[TEST] Phase {phase} directory exists: {phase_dirs[0]}")

        # 6. GitHub確認（オプション）
        print(f"\n[TEST] Step 5: GitHub integration check")
        # Note: GitHub Issue への投稿確認は手動で行うか、GitHub APIを使用して確認
        # ここでは確認をスキップ
        print(f"[TEST] GitHub issue comments should be posted to {issue_url}")

        # 7. Git確認
        print(f"\n[TEST] Step 6: Verifying Git commits")
        repo = Repo(repo_root)
        commits = list(repo.iter_commits(max_count=10))

        # 各フェーズのコミットが作成されていることを確認
        commit_messages = [c.message for c in commits]
        print(f"[TEST] Recent commits: {commit_messages[:5]}")

        # コミットメッセージに [ai-workflow] プレフィックスが含まれることを確認
        ai_workflow_commits = [msg for msg in commit_messages if '[ai-workflow]' in msg]
        assert len(ai_workflow_commits) >= len(expected_phases), \
            f"AIワークフローのコミット数が不足: {len(ai_workflow_commits)} < {len(expected_phases)}"
        print(f"[TEST] Found {len(ai_workflow_commits)} AI workflow commits")

        # テスト成功
        print(f"\n[TEST] ✓ All E2E tests passed!")

    def test_full_workflow_phase_failure(self, repo_root):
        """TC-E-002: 途中フェーズ失敗時のE2Eテスト

        目的: 途中のフェーズが失敗した場合、それ以降のフェーズが実行されず、
             適切にエラーハンドリングされることを検証

        前提条件: TC-E-001と同じ

        実行時間: 15-30分

        Note: このテストは実際に失敗させることが難しいため、
             モックを使用した統合テストとして実装するか、
             意図的に失敗するテスト用Issueを使用する必要があります。
        """
        # このテストは実装が複雑になるため、スキップ
        # 実際の失敗ケースはユニットテストでカバーされている
        pytest.skip("Phase failure E2E test requires special setup")


@pytest.mark.integration
class TestPhaseAllIntegration:
    """全フェーズ一括実行の統合テストクラス（コンポーネント間連携）"""

    def test_claude_api_integration(self):
        """TC-I-001: Claude API連携テスト

        目的: 全フェーズ実行中にClaude APIが正しく呼び出されることを検証
        """
        # Note: Claude API連携は各フェーズの既存テストでカバーされている
        pytest.skip("Claude API integration is covered by phase-specific tests")

    def test_github_api_integration(self):
        """TC-I-002: GitHub API連携テスト

        目的: 全フェーズ実行中にGitHub APIが正しく呼び出され、
             進捗コメントが投稿されることを検証
        """
        # Note: GitHub API連携は各フェーズの既存テストでカバーされている
        pytest.skip("GitHub API integration is covered by phase-specific tests")

    def test_git_operations_integration(self):
        """TC-I-003: Git操作統合テスト

        目的: 全フェーズ実行中にGit操作（commit, push）が正しく実行されることを検証
        """
        # Note: Git操作は各フェーズの既存テストでカバーされている
        pytest.skip("Git operations are covered by phase-specific tests")

    def test_metadata_management_integration(self):
        """TC-I-004: メタデータ管理統合テスト

        目的: 全フェーズ実行中にメタデータが正しく更新されることを検証
        """
        # Note: メタデータ管理は各フェーズの既存テストでカバーされている
        pytest.skip("Metadata management is covered by phase-specific tests")


@pytest.mark.performance
class TestPhaseAllPerformance:
    """全フェーズ一括実行のパフォーマンステスト"""

    def test_execution_time_overhead(self):
        """TC-P-001: 実行時間オーバーヘッドテスト

        目的: 全フェーズ一括実行のオーバーヘッドが5%以内であることを検証（NFR-01）

        テスト手順:
        1. 個別フェーズ実行の総実行時間を測定
        2. 全フェーズ一括実行の実行時間を測定
        3. オーバーヘッドを計算: (一括実行時間 - 個別実行の総時間) / 個別実行の総時間 × 100
        """
        # Note: パフォーマンステストは実行時間が非常に長いため、
        # 必要に応じて手動で実行するか、CI環境で定期的に実行する
        pytest.skip("Performance test requires manual execution due to long runtime")


if __name__ == '__main__':
    # slowテストを含めて実行する場合:
    # pytest test_phase_all.py -v -s -m slow
    pytest.main([__file__, '-v', '-s'])
