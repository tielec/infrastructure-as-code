"""Jenkins Git統合Integrationテスト

このテストは、Issue #304で実装済みのGitManager・BasePhaseが
Jenkins環境で正常に動作することを検証します。

テストシナリオ（IT-JG-001～IT-JG-008）に基づいてテストを実装
"""
import subprocess
import json
import tempfile
import shutil
import os
from pathlib import Path
import pytest


@pytest.fixture
def temp_workflow_dir():
    """一時的なワークフローディレクトリを作成"""
    temp_dir = tempfile.mkdtemp()

    # .ai-workflowディレクトリを作成
    workflow_dir = Path(temp_dir) / '.ai-workflow' / 'issue-305'
    workflow_dir.mkdir(parents=True, exist_ok=True)

    # metadata.jsonを作成
    metadata = {
        'issue_number': 305,
        'issue_title': '[TASK] AI Workflow: Jenkins統合完成とPhase終了後の自動commit & push機能',
        'created_at': '2025-10-09T00:00:00Z',
        'phases': {}
    }
    metadata_file = workflow_dir / 'metadata.json'
    metadata_file.write_text(json.dumps(metadata, indent=2))

    yield temp_dir

    # クリーンアップ
    shutil.rmtree(temp_dir)


class TestJenkinsGitIntegration:
    """Jenkins Git統合テストクラス"""

    # IT-JG-001: Phase 1完了後の自動commit（既存実装の検証）
    def test_phase1_auto_commit(self, temp_workflow_dir):
        """
        AC-004: Phase 1完了後の自動commit

        検証内容:
        - BasePhase.run() → GitManager.commit_phase_output()の統合動作
        - .ai-workflow/issue-305/配下のファイルがcommitされる
        - コミットメッセージフォーマットが正しい
        """
        # このテストは実際のJenkins環境で実行する必要があるため、
        # ここではテスト構造のみを定義
        pytest.skip("Jenkins環境での手動実行が必要")

        # テスト手順（手動実行時）:
        # 1. ワークフロー初期化
        #    python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/305
        # 2. Phase 1実行
        #    python main.py execute --phase requirements --issue 305
        # 3. Git履歴確認
        #    git log -1 --pretty=format:"%s"
        # 4. 期待結果確認
        #    - コミットメッセージ: [ai-workflow] Phase 1 (requirements) - completed
        #    - コミットファイルに .ai-workflow/issue-305/ が含まれる

    # IT-JG-002: Phase 1完了後の自動push（既存実装の検証）
    def test_phase1_auto_push(self, temp_workflow_dir):
        """
        AC-006: Phase 1完了後の自動push

        検証内容:
        - GitManager.push_to_remote()の実環境での動作
        - リモートリポジトリに正常にpushされる
        """
        pytest.skip("Jenkins環境での手動実行が必要")

        # テスト手順（手動実行時）:
        # 1. Phase 1実行（IT-JG-001から継続）
        # 2. ローカルコミットハッシュ取得
        #    git rev-parse HEAD
        # 3. リモートリポジトリのコミットハッシュ取得
        #    git ls-remote origin feature/ai-workflow-mvp | awk '{print $1}'
        # 4. 期待結果確認
        #    - ローカルとリモートのコミットハッシュが一致

    # IT-JG-003: Phase失敗時もcommit実行（既存実装の検証）
    def test_phase_failed_commit(self, temp_workflow_dir):
        """
        AC-005: Phase失敗時もcommit実行

        検証内容:
        - BasePhase.run()のfinally句が失敗時も確実に実行される
        - 失敗時もログファイルがcommitされる
        """
        pytest.skip("Jenkins環境での手動実行が必要")

        # テスト手順（手動実行時）:
        # 1. Phase実行を失敗させる（モックまたはタイムアウト設定）
        #    python main.py execute --phase requirements --issue 305
        # 2. Git履歴確認
        #    git log -1 --pretty=format:"%s%n%b"
        # 3. 期待結果確認
        #    - コミットメッセージ: [ai-workflow] Phase 1 (requirements) - failed
        #    - ログファイルがcommitされている

    # IT-JG-004: コミットメッセージフォーマット検証（既存実装の検証）
    def test_commit_message_format(self, temp_workflow_dir):
        """
        AC-008: コミットメッセージフォーマット検証

        検証内容:
        - GitManager.create_commit_message()の実装
        - 指定フォーマットに従っている
        """
        pytest.skip("Jenkins環境での手動実行が必要")

        # テスト手順（手動実行時）:
        # 1. Phase 1実行
        #    python main.py execute --phase requirements --issue 305
        # 2. コミットメッセージ全文取得
        #    git log -1 --pretty=format:"%s%n%b"
        # 3. 期待結果確認
        #    - サブジェクト行: [ai-workflow] Phase 1 (requirements) - completed
        #    - Issue: #305
        #    - Phase: 1 (requirements)
        #    - Status: completed
        #    - Review: PASS
        #    - Auto-generated by AI Workflow

    # IT-JG-005: Git pushリトライロジック（既存実装の検証）
    def test_git_push_retry(self, temp_workflow_dir):
        """
        AC-007: Git pushリトライロジック

        検証内容:
        - GitManager.push_to_remote()のリトライロジック
        - ネットワークエラー時にリトライされる
        """
        pytest.skip("Jenkins環境での手動実行が必要（モック使用推奨）")

        # テスト手順（手動実行時）:
        # 1. GitManager.push_to_remote()をモックし、
        #    1回目はネットワークタイムアウト、2回目は成功するように設定
        # 2. Phase 1実行
        #    python main.py execute --phase requirements --issue 305
        # 3. ログ確認
        #    grep "Git push" .ai-workflow/issue-305/01_requirements/execute/agent_log.md
        # 4. 期待結果確認
        #    - 1回目のpush失敗ログ
        #    - 2回目のpush成功ログ

    # IT-JG-006: Jenkins Phase実行ステージの動作確認（既存実装の検証）
    def test_jenkins_phase_execution(self, temp_workflow_dir):
        """
        AC-001: Jenkins Phase実行ステージの動作確認

        検証内容:
        - Jenkinsfile（Phase 1-7実行ステージ、Issue #304で実装済み）
        - Jenkins上でPhase 1が正常に動作する
        """
        pytest.skip("Jenkins UI経由での手動実行が必要")

        # テスト手順（手動実行時）:
        # 1. Jenkins UIから ai_workflow_orchestrator ジョブを手動実行
        # 2. パラメータ設定:
        #    - ISSUE_URL: https://github.com/tielec/infrastructure-as-code/issues/305
        #    - START_PHASE: requirements
        #    - DRY_RUN: false
        # 3. Jenkins Console Outputを確認
        # 4. 期待結果確認
        #    - "Stage: Phase 1 - Requirements Definition" が表示される
        #    - Phase実行が正常に完了する

    # IT-JG-007: 複数Phase順次実行（既存実装の検証）
    def test_multiple_phases_sequential(self, temp_workflow_dir):
        """
        AC-002: 複数Phase順次実行

        検証内容:
        - Jenkinsfile（全Phase実行ループ、Issue #304で実装済み）
        - Phase 1-7が順次実行される
        """
        pytest.skip("Jenkins UI経由での手動実行が必要")

        # テスト手順（手動実行時）:
        # 1. Jenkins UIからジョブを実行
        # 2. Phase 1-7の実行を監視
        # 3. 各Phaseの成果物とGit履歴を確認
        # 4. 期待結果確認
        #    - 各Phaseが順次実行される
        #    - 各Phase完了後にGit commitが作成される（合計7コミット）

    # IT-JG-008: エラーハンドリング（既存実装の検証）
    def test_error_handling(self, temp_workflow_dir):
        """
        AC-003: エラーハンドリング

        検証内容:
        - BasePhase.run()のエラーハンドリングとGitHub連携
        - エラーが適切にハンドリングされる
        """
        pytest.skip("Jenkins環境での手動実行が必要")

        # テスト手順（手動実行時）:
        # 1. Claude APIタイムアウトを再現（モック使用または実際のタイムアウト）
        # 2. Phase 1実行
        # 3. エラーログ確認
        # 4. GitHub Issue確認
        # 5. 期待結果確認
        #    - エラーメッセージがJenkins Console Outputに出力される
        #    - Phaseステータスが"failed"になる
        #    - GitHub Issueにコメント投稿される


class TestCommitMessageFormat:
    """コミットメッセージフォーマットのUnitテスト（補助）"""

    def test_commit_message_structure(self):
        """
        コミットメッセージの構造をUnitテストで検証

        実際のGitManager実装を使用してテスト
        """
        from core.git_manager import GitManager
        from core.metadata_manager import MetadataManager
        from unittest.mock import Mock

        # モックMetadataManager
        mock_metadata = Mock(spec=MetadataManager)
        mock_metadata.data = {
            'issue_number': 305,
            'issue_title': 'Test Issue'
        }

        # GitManagerを一時リポジトリで初期化（mockを使用）
        temp_dir = tempfile.mkdtemp()
        try:
            # Gitリポジトリを初期化
            subprocess.run(['git', 'init'], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=temp_dir, check=True, capture_output=True)

            # GitManager初期化
            git_manager = GitManager(
                repo_path=Path(temp_dir),
                metadata_manager=mock_metadata
            )

            # コミットメッセージ生成
            message = git_manager.create_commit_message(
                phase_name='requirements',
                status='completed',
                review_result='PASS'
            )

            # 検証ポイント
            assert '[ai-workflow] Phase 1 (requirements) - completed' in message
            assert 'Issue: #305' in message
            assert 'Phase: 1 (requirements)' in message
            assert 'Status: completed' in message
            assert 'Review: PASS' in message
            assert 'Auto-generated by AI Workflow' in message

        finally:
            shutil.rmtree(temp_dir)


class TestFileFiltering:
    """ファイルフィルタリングのUnitテスト（補助）"""

    def test_filter_phase_files_jenkins_tmp_exclusion(self):
        """
        Jenkins一時ディレクトリ（@tmp）の除外を検証

        設計書のフィルタリングロジックを検証
        """
        from core.git_manager import GitManager
        from core.metadata_manager import MetadataManager
        from unittest.mock import Mock

        # モックMetadataManager
        mock_metadata = Mock(spec=MetadataManager)
        mock_metadata.data = {
            'issue_number': 305
        }

        # GitManagerを一時リポジトリで初期化
        temp_dir = tempfile.mkdtemp()
        try:
            # Gitリポジトリを初期化
            subprocess.run(['git', 'init'], cwd=temp_dir, check=True, capture_output=True)

            # GitManager初期化
            git_manager = GitManager(
                repo_path=Path(temp_dir),
                metadata_manager=mock_metadata
            )

            # テストファイルリスト
            files = [
                '.ai-workflow/issue-305/01_requirements/output/requirements.md',
                '.ai-workflow/issue-305/metadata.json',
                '.ai-workflow/issue-999/01_requirements/output/requirements.md',  # 他Issue
                'workspace@tmp/temp.txt',  # Jenkins一時ファイル
                'scripts/ai-workflow/main.py'  # プロジェクト本体
            ]

            # フィルタリング実行
            filtered = git_manager._filter_phase_files(files, 305)

            # 検証ポイント
            assert '.ai-workflow/issue-305/01_requirements/output/requirements.md' in filtered
            assert '.ai-workflow/issue-305/metadata.json' in filtered
            assert 'workspace@tmp/temp.txt' not in filtered  # @tmpは除外
            assert '.ai-workflow/issue-999/' not in str(filtered)  # 他Issueは除外
            assert 'scripts/ai-workflow/main.py' not in filtered  # プロジェクト本体は除外（.ai-workflow以外）

        finally:
            shutil.rmtree(temp_dir)


class TestGitManagerRetryLogic:
    """GitManagerリトライロジックのUnitテスト（補助）"""

    def test_retry_logic_network_error(self):
        """
        ネットワークエラー時のリトライロジックを検証

        GitManager._is_retriable_error()の実装を検証
        """
        from core.git_manager import GitManager
        from core.metadata_manager import MetadataManager
        from git import GitCommandError
        from unittest.mock import Mock

        # モックMetadataManager
        mock_metadata = Mock(spec=MetadataManager)
        mock_metadata.data = {'issue_number': 305}

        # GitManagerを一時リポジトリで初期化
        temp_dir = tempfile.mkdtemp()
        try:
            # Gitリポジトリを初期化
            subprocess.run(['git', 'init'], cwd=temp_dir, check=True, capture_output=True)

            # GitManager初期化
            git_manager = GitManager(
                repo_path=Path(temp_dir),
                metadata_manager=mock_metadata
            )

            # ネットワークエラー（リトライ可能）
            network_error = GitCommandError('push', 'fatal: unable to access ... timeout')
            assert git_manager._is_retriable_error(network_error) is True

            # 権限エラー（リトライ不可能）
            permission_error = GitCommandError('push', 'fatal: Permission denied')
            assert git_manager._is_retriable_error(permission_error) is False

            # 認証エラー（リトライ不可能）
            auth_error = GitCommandError('push', 'fatal: Authentication failed')
            assert git_manager._is_retriable_error(auth_error) is False

        finally:
            shutil.rmtree(temp_dir)


# エンドツーエンドテスト（E2E-001）
class TestE2EWorkflow:
    """
    E2E-001: 全フロー統合テスト

    このテストは手動実行が必要です。
    Jenkins環境で実際に全フローを実行して検証します。
    """

    def test_full_workflow_integration(self):
        """
        AC-009: 全フロー統合テスト

        手動実行手順:

        1. テスト用Issue確認
           gh issue view 305

        2. Jenkins Job実行
           - Jenkins UI: AI_Workflow/ai_workflow_orchestrator
           - パラメータ:
             - ISSUE_URL: https://github.com/tielec/infrastructure-as-code/issues/305
             - START_PHASE: requirements
             - DRY_RUN: false
           - "Build with Parameters" → "Build"をクリック

        3. Phase 1実行確認
           - Jenkins Console Outputで進捗確認
           - Phase 1完了まで待機（約10分）

        4. 成果物確認
           ls -la .ai-workflow/issue-305/01_requirements/output/
           # → requirements.md が存在すること

        5. Git履歴確認
           git log -1 --pretty=format:"%s%n%b"
           # 期待される出力:
           # [ai-workflow] Phase 1 (requirements) - completed
           #
           # Issue: #305
           # Phase: 1 (requirements)
           # Status: completed
           # Review: PASS
           #
           # Auto-generated by AI Workflow

        6. リモートpush確認
           git log origin/feature/ai-workflow-mvp -1 --pretty=format:"%s"
           # リモートに同じコミットが存在すること

        7. GitHub Issue確認
           gh issue view 305 --comments
           # レビュー結果コメントが投稿されていること
           # フォーマット: "## 📄 要件定義フェーズ - 成果物"

        期待される結果:
        - ✅ Phase 1が正常に完了
        - ✅ .ai-workflow/issue-305/01_requirements/output/requirements.md が生成
        - ✅ Git commitが作成（コミットメッセージフォーマット正しい）
        - ✅ リモートリポジトリにpush成功
        - ✅ GitHub Issueにレビュー結果投稿
        - ✅ Jenkins Console Outputにエラーなし
        - ✅ metadata.jsonが更新される
        """
        pytest.skip("Jenkins環境での手動実行が必要")
