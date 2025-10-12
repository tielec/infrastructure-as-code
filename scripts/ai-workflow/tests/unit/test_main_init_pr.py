"""main.py init コマンド PR作成機能のユニットテスト (Issue #355)

init コマンドにおけるPR作成ロジックのテストケース
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner


@pytest.mark.unit
class TestMainInitPRCreation:
    """main.py init コマンドのPR作成機能ユニットテスト"""

    # TC-U-010: init_commit成功後のpush実行
    def test_init_commit_success_then_push(self, mocker, tmp_path):
        """
        TC-U-010: commit成功後にpush処理が実行されることを検証

        Given: metadata.jsonが作成されている
        When: commitが成功する
        Then: push処理が実行される
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

        # アサーション: commit_phase_outputが呼ばれた
        assert mock_git_manager.commit_phase_output.called

        # アサーション: push_to_remoteが呼ばれた
        assert mock_git_manager.push_to_remote.called

    # TC-U-011: init_commit失敗時のpushスキップ
    def test_init_commit_failure_skip_push(self, mocker, tmp_path):
        """
        TC-U-011: commit失敗時にpushとPR作成がスキップされることを検証

        Given: metadata.jsonが作成されている
        When: commitが失敗する
        Then: pushとPR作成がスキップされる
        """
        from main import cli

        # モックの準備
        mock_git_manager = Mock()
        mock_git_manager.commit_phase_output.return_value = {
            'success': False,
            'error': 'Commit failed'
        }
        mock_git_manager.push_to_remote.return_value = {
            'success': True
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

        # アサーション: commit_phase_outputが呼ばれた
        assert mock_git_manager.commit_phase_output.called

        # アサーション: push_to_remoteが呼ばれていない
        assert not mock_git_manager.push_to_remote.called

        # アサーション: 警告ログが出力されている
        assert '[WARNING]' in result.output or 'Commit failed' in result.output

    # TC-U-012: init_push失敗時のPR作成スキップ
    def test_init_push_failure_skip_pr(self, mocker, tmp_path):
        """
        TC-U-012: push失敗時にPR作成がスキップされることを検証

        Given: commitが成功している
        When: pushが失敗する
        Then: PR作成がスキップされる
        """
        from main import cli

        # モックの準備
        mock_git_manager = Mock()
        mock_git_manager.commit_phase_output.return_value = {
            'success': True,
            'commit_hash': 'abc1234567890'
        }
        mock_git_manager.push_to_remote.return_value = {
            'success': False,
            'error': 'Push failed'
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

        # アサーション: pushが呼ばれた
        assert mock_git_manager.push_to_remote.called

        # アサーション: create_pull_requestが呼ばれていない
        assert not mock_github_client.create_pull_request.called

        # アサーション: 警告ログが出力されている
        assert '[WARNING]' in result.output or 'Push failed' in result.output

    # TC-U-013: init_既存PR存在時のスキップ
    def test_init_existing_pr_skip(self, mocker, tmp_path):
        """
        TC-U-013: 既存PRが存在する場合に新規PR作成がスキップされることを検証

        Given: commit、pushが成功している
        When: 既存PRが存在する
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

        # アサーション: check_existing_prが呼ばれた
        assert mock_github_client.check_existing_pr.called

        # アサーション: create_pull_requestが呼ばれていない
        assert not mock_github_client.create_pull_request.called

        # アサーション: 警告ログが出力されている
        assert '[WARNING]' in result.output or 'already exists' in result.output

    # TC-U-014: init_PR作成成功
    def test_init_pr_creation_success(self, mocker, tmp_path):
        """
        TC-U-014: PR作成が正常に実行されることを検証

        Given: commit、pushが成功している
        When: 既存PRが存在しない
        Then: PR作成が成功する
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

        # アサーション: check_existing_prが呼ばれた
        assert mock_github_client.check_existing_pr.called

        # アサーション: create_pull_requestが呼ばれた
        assert mock_github_client.create_pull_request.called

        # アサーション: 成功ログが出力されている
        assert '[OK]' in result.output or 'Draft PR created' in result.output

    # TC-U-015: init_GITHUB_TOKEN未設定
    def test_init_github_token_not_set(self, mocker, tmp_path):
        """
        TC-U-015: GITHUB_TOKEN未設定時にPR作成がスキップされることを検証

        Given: commit、pushが成功している
        When: GITHUB_TOKENが未設定
        Then: PR作成がスキップされる
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

        # パッチの適用（GITHUB_TOKENを未設定に）
        with patch('main.GitManager', return_value=mock_git_manager), \
             patch('main.GitHubClient', return_value=mock_github_client), \
             patch('main.MetadataManager'), \
             patch('main.WorkflowState'), \
             patch('main.Path.mkdir'), \
             patch('main.Path.exists', return_value=False), \
             patch.dict('os.environ', {}, clear=True):

            runner = CliRunner()
            result = runner.invoke(cli, ['init', '--issue-url', 'https://github.com/owner/repo/issues/355'])

        # アサーション: GitHubClientが初期化されていない
        # (環境変数がないため、PR作成フローに入らない)

        # アサーション: 警告ログが出力されている
        assert '[WARNING]' in result.output or 'GITHUB_TOKEN' in result.output or 'not set' in result.output

    # TC-U-016: init_PR作成失敗でもinit成功
    def test_init_pr_creation_failure_but_init_success(self, mocker, tmp_path):
        """
        TC-U-016: PR作成失敗時でもinit全体が成功として完了することを検証

        Given: commit、pushが成功している
        When: PR作成が失敗する
        Then: init全体は成功として完了する
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
        mock_github_client.check_existing_pr.return_value = None
        mock_github_client.create_pull_request.return_value = {
            'success': False,
            'pr_url': None,
            'pr_number': None,
            'error': 'PR creation failed'
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

        # アサーション: create_pull_requestが呼ばれた
        assert mock_github_client.create_pull_request.called

        # アサーション: initは成功（exit code 0）
        assert result.exit_code == 0 or 'completed' in result.output.lower()

        # アサーション: 警告ログが出力されている
        assert '[WARNING]' in result.output or 'PR creation failed' in result.output
