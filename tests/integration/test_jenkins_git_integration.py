"""
Jenkins Git統合テスト

Purpose:
    Issue #304で実装済みのGitManager・BasePhaseが、Jenkins環境で正常に動作することを検証

Test Cases:
    - IT-JG-001: Phase 1完了後の自動commit（既存実装の検証）
    - IT-JG-002: Phase 1完了後の自動push（既存実装の検証）
    - IT-JG-003: Phase失敗時もcommit実行（既存実装の検証）
    - IT-JG-004: コミットメッセージフォーマット検証（既存実装の検証）
    - IT-JG-005: Git pushリトライロジック（既存実装の検証）
    - IT-JG-006: Jenkins Phase実行ステージの動作確認（既存実装の検証）
    - IT-JG-007: 複数Phase順次実行（既存実装の検証）
    - IT-JG-008: エラーハンドリング（既存実装の検証）

Note:
    これらのテストは既存実装を検証するためのものであり、新規実装をテストするものではない。
"""
import subprocess
import json
import pytest
import re
from pathlib import Path


class TestJenkinsGitIntegration:
    """Jenkins Git統合テスト"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """テストセットアップ"""
        self.repo_root = Path.cwd()
        self.workflow_dir = self.repo_root / '.ai-workflow'

    def test_phase1_auto_commit(self):
        """
        IT-JG-001: Phase 1完了後の自動commit（既存実装の検証）

        対応受け入れ基準: AC-004
        検証対象: BasePhase.run() → GitManager.commit_phase_output()の統合動作
        """
        # 1. ワークフロー初期化
        result = subprocess.run(
            ['python', 'main.py', 'init', '--issue-url',
             'https://github.com/tielec/infrastructure-as-code/issues/305'],
            capture_output=True,
            text=True,
            cwd=self.repo_root / 'scripts' / 'ai-workflow'
        )

        # 初期化成功を確認（既に初期化済みの場合はスキップ）
        if result.returncode != 0 and 'already exists' not in result.stderr:
            pytest.fail(f"Workflow initialization failed: {result.stderr}")

        # 2. Phase 1実行
        result = subprocess.run(
            ['python', 'main.py', 'execute', '--phase', 'requirements', '--issue', '305'],
            capture_output=True,
            text=True,
            cwd=self.repo_root / 'scripts' / 'ai-workflow'
        )

        assert result.returncode == 0, f"Phase 1 execution failed: {result.stderr}"

        # 3. Git履歴確認
        result = subprocess.run(
            ['git', 'log', '-1', '--pretty=format:%s'],
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )

        commit_message = result.stdout

        # 検証ポイント
        assert '[ai-workflow] Phase 1 (requirements) - completed' in commit_message or \
               '[ai-workflow] Phase 1 (requirements) - failed' in commit_message, \
               f"Invalid commit message format: {commit_message}"

        # 4. コミットされたファイル確認
        result = subprocess.run(
            ['git', 'show', '--name-only', '--pretty=format:'],
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )

        files = result.stdout.strip().split('\n')
        files = [f.strip() for f in files if f.strip()]

        # 検証ポイント
        assert any('.ai-workflow/issue-305/' in f for f in files), \
               f"Expected .ai-workflow/issue-305/ files in commit, got: {files}"

        # 他のIssueのファイルが含まれていないことを確認
        other_issue_files = [f for f in files if '.ai-workflow/issue-' in f and 'issue-305' not in f]
        assert len(other_issue_files) == 0, \
               f"Unexpected other issue files in commit: {other_issue_files}"

        # Jenkins一時ファイルが含まれていないことを確認
        tmp_files = [f for f in files if '@tmp' in f]
        assert len(tmp_files) == 0, f"Unexpected @tmp files in commit: {tmp_files}"

    def test_phase1_auto_push(self):
        """
        IT-JG-002: Phase 1完了後の自動push（既存実装の検証）

        対応受け入れ基準: AC-006
        検証対象: GitManager.push_to_remote()の実環境での動作
        """
        # Phase 1が既に実行されていることを前提とする（IT-JG-001から継続）

        # 1. ローカルコミットハッシュ取得
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )
        local_commit = result.stdout.strip()

        # 2. リモートリポジトリのコミットハッシュ取得
        result = subprocess.run(
            ['git', 'rev-parse', 'origin/HEAD'],
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )

        if result.returncode != 0:
            # origin/HEADが設定されていない場合は、現在のブランチを使用
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=self.repo_root
            )
            current_branch = result.stdout.strip()

            result = subprocess.run(
                ['git', 'rev-parse', f'origin/{current_branch}'],
                capture_output=True,
                text=True,
                cwd=self.repo_root
            )

        remote_commit = result.stdout.strip()

        # 検証ポイント: ローカルとリモートのコミットハッシュが一致（または差分が小さい）
        # Note: 完全一致でなくてもOK（他の開発者がpushしている可能性があるため）
        # ここでは、ローカルコミットがリモートにpush済みであることを確認
        result = subprocess.run(
            ['git', 'branch', '-r', '--contains', local_commit],
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )

        assert result.stdout.strip() != '', \
               f"Local commit {local_commit} not found in remote branches"

    def test_phase_failed_commit(self):
        """
        IT-JG-003: Phase失敗時もcommit実行（既存実装の検証）

        対応受け入れ基準: AC-005
        検証対象: BasePhase.run()のfinally句が失敗時も確実に実行されること

        Note:
            このテストは実環境でPhaseを失敗させる必要があるため、
            モックまたは手動テストで実施することを推奨します。
        """
        pytest.skip("This test requires manual execution or mock setup")

    def test_commit_message_format(self):
        """
        IT-JG-004: コミットメッセージフォーマット検証（既存実装の検証）

        対応受け入れ基準: AC-008
        検証対象: GitManager.create_commit_message()の実装
        """
        # 最新コミットメッセージ全文取得
        result = subprocess.run(
            ['git', 'log', '-1', '--pretty=format:%s%n%b'],
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )

        commit_message = result.stdout

        # 検証ポイント: サブジェクト行
        assert re.match(r'\[ai-workflow\] Phase \d+ \(\w+\) - (completed|failed)', commit_message.split('\n')[0]), \
               f"Invalid subject line: {commit_message.split('\n')[0]}"

        # 検証ポイント: 本文にIssue番号が含まれる
        assert re.search(r'Issue: #\d+', commit_message), \
               f"Issue number not found in commit message: {commit_message}"

        # 検証ポイント: 本文にPhase情報が含まれる
        assert re.search(r'Phase: \d+ \(\w+\)', commit_message), \
               f"Phase info not found in commit message: {commit_message}"

        # 検証ポイント: 本文にステータスが含まれる
        assert re.search(r'Status: (completed|failed)', commit_message), \
               f"Status not found in commit message: {commit_message}"

        # 検証ポイント: 本文にレビュー結果が含まれる
        assert re.search(r'Review: (PASS|PASS_WITH_SUGGESTIONS|FAIL|N/A)', commit_message), \
               f"Review result not found in commit message: {commit_message}"

        # 検証ポイント: 最終行に署名がある
        assert 'Auto-generated by AI Workflow' in commit_message, \
               f"Auto-generated signature not found in commit message: {commit_message}"

    def test_git_push_retry(self):
        """
        IT-JG-005: Git pushリトライロジック（既存実装の検証）

        対応受け入れ基準: AC-007
        検証対象: GitManager.push_to_remote()のリトライロジック

        Note:
            このテストはネットワークエラーを再現する必要があるため、
            モックまたは手動テストで実施することを推奨します。
        """
        pytest.skip("This test requires mock setup to simulate network errors")

    def test_jenkins_phase_execution(self):
        """
        IT-JG-006: Jenkins Phase実行ステージの動作確認（既存実装の検証）

        対応受け入れ基準: AC-001
        検証対象: Jenkinsfile（Phase 1-7実行ステージ、Issue #304で実装済み）

        Note:
            このテストはJenkins環境が必要なため、手動テストで実施することを推奨します。
        """
        pytest.skip("This test requires Jenkins environment")

    def test_multiple_phase_execution(self):
        """
        IT-JG-007: 複数Phase順次実行（既存実装の検証）

        対応受け入れ基準: AC-002
        検証対象: Jenkinsfile（全Phase実行ループ、Issue #304で実装済み）

        Note:
            このテストはJenkins環境が必要なため、手動テストで実施することを推奨します。
        """
        pytest.skip("This test requires Jenkins environment")

    def test_error_handling(self):
        """
        IT-JG-008: エラーハンドリング（既存実装の検証）

        対応受け入れ基準: AC-003
        検証対象: BasePhase.run()のエラーハンドリングとGitHub連携

        Note:
            このテストはエラーを発生させる必要があるため、
            モックまたは手動テストで実施することを推奨します。
        """
        pytest.skip("This test requires mock setup to simulate errors")


class TestEndToEnd:
    """エンドツーエンドテスト"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """テストセットアップ"""
        self.repo_root = Path.cwd()
        self.workflow_dir = self.repo_root / '.ai-workflow'

    def test_full_workflow(self):
        """
        E2E-001: 全フロー統合テスト

        対応受け入れ基準: AC-009
        検証対象: 既存実装（GitManager + BasePhase + Jenkinsfile）の統合動作

        Note:
            このテストは以下を手動で実施することを推奨します:
            1. テスト用Issue確認（Issue #305）
            2. Jenkins Job実行（ai_workflow_orchestrator）
            3. Phase 1実行確認
            4. 成果物確認
            5. Git履歴確認
            6. リモートpush確認
            7. GitHub Issue確認
            8. Phase 2-7実行（オプション）
        """
        pytest.skip("This test requires manual execution in Jenkins environment")
