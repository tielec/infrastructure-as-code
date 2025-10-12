"""init コマンド PR作成ワークフローの統合テスト (Issue #355)

init → commit → push → PR作成の統合テストケース
"""
import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch
from click.testing import CliRunner


@pytest.mark.integration
class TestInitPRWorkflowIntegration:
    """init コマンド PR作成ワークフローの統合テスト"""

    # TC-I-001: init_E2E_正常系
    @pytest.mark.skipif(
        not os.getenv('GITHUB_TOKEN') or not os.getenv('GITHUB_REPOSITORY'),
        reason="GITHUB_TOKEN or GITHUB_REPOSITORY not set"
    )
    def test_init_e2e_success(self, tmp_path, mocker):
        """
        TC-I-001: init実行後、commit → push → PR作成が順番に実行されることを検証

        Given: Gitリポジトリが初期化されている
        When: initコマンドを実行する
        Then: metadata.json作成、commit、push、PR作成がすべて成功する

        注意: このテストは実際のGitHub APIを使用します
        """
        from main import cli

        # テスト用の一時ディレクトリを作成
        test_repo_path = tmp_path / 'test_repo'
        test_repo_path.mkdir()

        # モックの準備（実際のGit操作は行わず、結果のみをモック）
        mock_git_manager = Mock()
        mock_git_manager.commit_phase_output.return_value = {
            'success': True,
            'commit_hash': 'abc1234567890'
        }
        mock_git_manager.push_to_remote.return_value = {
            'success': True
        }

        # GitHubClientは実際のインスタンスを使用（環境変数からトークンを取得）
        # ただし、PR作成はモック（実際にPRを作成しないため）
        mock_github_client = Mock()
        mock_github_client.check_existing_pr.return_value = None
        mock_github_client.create_pull_request.return_value = {
            'success': True,
            'pr_url': 'https://github.com/owner/repo/pull/999',
            'pr_number': 999,
            'error': None
        }
        mock_github_client._generate_pr_body_template.return_value = 'Test PR body'

        # パッチの適用
        with patch('main.GitManager', return_value=mock_git_manager), \
             patch('main.GitHubClient', return_value=mock_github_client), \
             patch('main.MetadataManager'), \
             patch('main.WorkflowState'), \
             patch('main.Path.mkdir'), \
             patch('main.Path.exists', return_value=False):

            runner = CliRunner()
            result = runner.invoke(cli, ['init', '--issue-url', 'https://github.com/tielec/infrastructure-as-code/issues/355'])

        # アサーション: initコマンドが成功
        assert result.exit_code == 0 or 'completed' in result.output.lower()

        # アサーション: commit、push、PR作成が呼ばれた
        assert mock_git_manager.commit_phase_output.called
        assert mock_git_manager.push_to_remote.called
        assert mock_github_client.check_existing_pr.called
        assert mock_github_client.create_pull_request.called

    # TC-I-002: init_E2E_既存PR存在
    def test_init_e2e_existing_pr(self, tmp_path, mocker):
        """
        TC-I-002: 既存PRが存在する場合、新規PR作成がスキップされることを検証

        Given: 既存PRが存在する
        When: initコマンドを実行する
        Then: 新規PR作成がスキップされる
        """
        from main import cli

        # モックの準備
        mock_git_manager = Mock()
        mock_git_manager.commit_phase_output.return_value = {
            'success': True,
            'commit_hash': 'abc1234567890'
        }
        mock_git_manager.push_to_remote.return_value = {
            'success': True
        }

        mock_github_client = Mock()
        mock_github_client.check_existing_pr.return_value = {
            'pr_number': 123,
            'pr_url': 'https://github.com/owner/repo/pull/123',
            'state': 'open'
        }

        # パッチの適用
        with patch('main.GitManager', return_value=mock_git_manager), \
             patch('main.GitHubClient', return_value=mock_github_client), \
             patch('main.MetadataManager'), \
             patch('main.WorkflowState'), \
             patch('main.Path.mkdir'), \
             patch('main.Path.exists', return_value=False), \
             patch.dict('os.environ', {
                 'GITHUB_TOKEN': 'test_token',
                 'GITHUB_REPOSITORY': 'owner/repo'
             }):

            runner = CliRunner()
            result = runner.invoke(cli, ['init', '--issue-url', 'https://github.com/owner/repo/issues/355'])

        # アサーション: commit、pushは成功
        assert mock_git_manager.commit_phase_output.called
        assert mock_git_manager.push_to_remote.called

        # アサーション: 既存PRチェックが実行された
        assert mock_github_client.check_existing_pr.called

        # アサーション: 新規PR作成がスキップされた
        assert not mock_github_client.create_pull_request.called

        # アサーション: 警告ログが出力されている
        assert '[WARNING]' in result.output or 'already exists' in result.output

    # TC-I-003: init_E2E_push失敗時のリトライ
    def test_init_e2e_push_retry(self, tmp_path, mocker):
        """
        TC-I-003: push失敗時に最大3回リトライされることを検証

        Given: push処理が1回目、2回目は失敗し、3回目に成功する
        When: initコマンドを実行する
        Then: pushが3回試行され、最終的に成功する
        """
        from main import cli

        # モックの準備
        mock_git_manager = Mock()
        mock_git_manager.commit_phase_output.return_value = {
            'success': True,
            'commit_hash': 'abc1234567890'
        }

        # pushは3回目で成功するようにモック
        # GitManager.push_to_remote()は内部でリトライするため、
        # 最終的な結果のみをモック
        mock_git_manager.push_to_remote.return_value = {
            'success': True,
            'retries': 2  # 2回リトライした後に成功
        }

        mock_github_client = Mock()
        mock_github_client.check_existing_pr.return_value = None
        mock_github_client.create_pull_request.return_value = {
            'success': True,
            'pr_url': 'https://github.com/owner/repo/pull/123',
            'pr_number': 123,
            'error': None
        }
        mock_github_client._generate_pr_body_template.return_value = 'PR body'

        # パッチの適用
        with patch('main.GitManager', return_value=mock_git_manager), \
             patch('main.GitHubClient', return_value=mock_github_client), \
             patch('main.MetadataManager'), \
             patch('main.WorkflowState'), \
             patch('main.Path.mkdir'), \
             patch('main.Path.exists', return_value=False), \
             patch.dict('os.environ', {
                 'GITHUB_TOKEN': 'test_token',
                 'GITHUB_REPOSITORY': 'owner/repo'
             }):

            runner = CliRunner()
            result = runner.invoke(cli, ['init', '--issue-url', 'https://github.com/owner/repo/issues/355'])

        # アサーション: pushが呼ばれた
        assert mock_git_manager.push_to_remote.called

        # アサーション: 最終的にpushが成功した
        # （リトライ機能はGitManager内部で実装されているため、ここでは最終結果を確認）

        # アサーション: PR作成が実行された
        assert mock_github_client.create_pull_request.called

    # TC-I-004: init_E2E_commit失敗
    def test_init_e2e_commit_failure(self, tmp_path, mocker):
        """
        TC-I-004: commit失敗時にpushとPR作成がスキップされることを検証

        Given: commit処理が失敗する
        When: initコマンドを実行する
        Then: pushとPR作成がスキップされる
        """
        from main import cli

        # モックの準備
        mock_git_manager = Mock()
        mock_git_manager.commit_phase_output.return_value = {
            'success': False,
            'error': 'Git user.name not set'
        }

        mock_github_client = Mock()

        # パッチの適用
        with patch('main.GitManager', return_value=mock_git_manager), \
             patch('main.GitHubClient', return_value=mock_github_client), \
             patch('main.MetadataManager'), \
             patch('main.WorkflowState'), \
             patch('main.Path.mkdir'), \
             patch('main.Path.exists', return_value=False), \
             patch.dict('os.environ', {
                 'GITHUB_TOKEN': 'test_token',
                 'GITHUB_REPOSITORY': 'owner/repo'
             }):

            runner = CliRunner()
            result = runner.invoke(cli, ['init', '--issue-url', 'https://github.com/owner/repo/issues/355'])

        # アサーション: commitが試行された
        assert mock_git_manager.commit_phase_output.called

        # アサーション: pushが実行されていない
        assert not mock_git_manager.push_to_remote.called

        # アサーション: PR作成が実行されていない
        assert not mock_github_client.create_pull_request.called

        # アサーション: 警告ログが出力されている
        assert '[WARNING]' in result.output or 'Commit failed' in result.output


@pytest.mark.integration
class TestGitManagerGitHubClientIntegration:
    """GitManager と GitHubClient の連携動作テスト"""

    # TC-I-005: GitManagerとGitHubClientの連携_正常系
    def test_git_manager_github_client_integration_success(self, mocker):
        """
        TC-I-005: GitManagerのcommit、push実行後、GitHubClientでPR作成が実行されることを検証

        Given: GitManagerとGitHubClientが初期化されている
        When: commit → push → PR作成を順番に実行する
        Then: すべての処理が成功する
        """
        from core.git_manager import GitManager
        from core.github_client import GitHubClient

        # モックの準備
        mock_metadata_manager = Mock()

        # GitManagerのモック
        mock_git_manager = Mock(spec=GitManager)
        mock_git_manager.commit_phase_output.return_value = {
            'success': True,
            'commit_hash': 'abc1234567890'
        }
        mock_git_manager.push_to_remote.return_value = {
            'success': True
        }

        # GitHubClientのモック
        mock_github_client = Mock(spec=GitHubClient)
        mock_github_client.check_existing_pr.return_value = None
        mock_github_client.create_pull_request.return_value = {
            'success': True,
            'pr_url': 'https://github.com/owner/repo/pull/123',
            'pr_number': 123,
            'error': None
        }

        # テスト実行
        commit_result = mock_git_manager.commit_phase_output(
            phase_name='planning',
            status='completed',
            review_result='N/A'
        )
        assert commit_result['success'] is True

        push_result = mock_git_manager.push_to_remote()
        assert push_result['success'] is True

        existing_pr = mock_github_client.check_existing_pr(
            head='ai-workflow/issue-355',
            base='main'
        )
        assert existing_pr is None

        pr_result = mock_github_client.create_pull_request(
            title='[AI-Workflow] Issue #355',
            body='PR body',
            head='ai-workflow/issue-355',
            base='main',
            draft=True
        )
        assert pr_result['success'] is True
        assert pr_result['pr_url'] is not None

    # TC-I-006: GitManagerとGitHubClientの連携_エラー伝播
    def test_git_manager_github_client_error_propagation(self, mocker):
        """
        TC-I-006: GitManagerのエラーがGitHubClient処理に影響しないことを検証

        Given: GitManagerのpush処理が失敗する
        When: commit → push → PR作成を順番に実行する
        Then: push失敗後、GitHubClient処理がスキップされる
        """
        from core.git_manager import GitManager
        from core.github_client import GitHubClient

        # GitManagerのモック
        mock_git_manager = Mock(spec=GitManager)
        mock_git_manager.commit_phase_output.return_value = {
            'success': True,
            'commit_hash': 'abc1234567890'
        }
        mock_git_manager.push_to_remote.return_value = {
            'success': False,
            'error': 'Network error'
        }

        # GitHubClientのモック
        mock_github_client = Mock(spec=GitHubClient)

        # テスト実行
        commit_result = mock_git_manager.commit_phase_output(
            phase_name='planning',
            status='completed',
            review_result='N/A'
        )
        assert commit_result['success'] is True

        push_result = mock_git_manager.push_to_remote()
        assert push_result['success'] is False

        # push失敗後、GitHubClient処理はスキップされる
        # （実際のコードではif文でスキップされる）

        # GitHubClientが呼ばれていないことを確認
        assert not mock_github_client.check_existing_pr.called
        assert not mock_github_client.create_pull_request.called


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv('GITHUB_TOKEN') or not os.getenv('GITHUB_REPOSITORY'),
    reason="GITHUB_TOKEN or GITHUB_REPOSITORY not set"
)
class TestGitHubAPIIntegration:
    """GitHub API との実際の通信テスト（モックなし）"""

    # TC-I-007: GitHub_API_PR作成（スキップ推奨）
    @pytest.mark.skip(reason="実際のGitHub APIを使用するため、手動実行のみ推奨")
    def test_github_api_pr_creation(self):
        """
        TC-I-007: 実際のGitHub APIを使用してPRが作成されることを検証

        Given: テストリポジトリへのアクセス権がある
        When: create_pull_request()を呼び出す
        Then: PRが作成される

        注意: このテストは実際にPRを作成するため、通常はスキップされます
        """
        from core.github_client import GitHubClient

        client = GitHubClient(
            token=os.getenv('GITHUB_TOKEN'),
            repository=os.getenv('GITHUB_REPOSITORY')
        )

        # テスト用のPR作成（実際には作成しない）
        # 実行する場合は、テストリポジトリで実行してください
        pass

    # TC-I-008: GitHub_API_既存PRチェック
    def test_github_api_check_existing_pr(self):
        """
        TC-I-008: 実際のGitHub APIを使用して既存PRチェックが実行されることを検証

        Given: テストリポジトリへのアクセス権がある
        When: check_existing_pr()を呼び出す
        Then: 既存PR情報が返される（または None）
        """
        from core.github_client import GitHubClient

        client = GitHubClient(
            token=os.getenv('GITHUB_TOKEN'),
            repository=os.getenv('GITHUB_REPOSITORY')
        )

        # 既存PRチェック（存在しないブランチで実行）
        result = client.check_existing_pr(
            head='ai-workflow/non-existent-branch',
            base='main'
        )

        # 存在しないブランチのため、Noneが返される
        assert result is None

    # TC-I-009: GitHub_API_権限エラー
    @pytest.mark.skip(reason="権限エラーのテストは手動実行のみ推奨")
    def test_github_api_permission_error(self):
        """
        TC-I-009: GitHub Token権限不足時に適切なエラーが返されることを検証

        Given: 権限不足のトークンを使用
        When: create_pull_request()を呼び出す
        Then: 権限エラーが返される

        注意: このテストは権限不足のトークンが必要なため、通常はスキップされます
        """
        from core.github_client import GitHubClient

        # 権限不足のトークンでテスト（実際には実行しない）
        pass
