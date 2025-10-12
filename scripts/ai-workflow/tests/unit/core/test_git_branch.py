"""
Unit tests for core/git/branch.py

Test Scenarios:
- UT-GB-001: GitBranch.create() - 新規ブランチ作成
- UT-GB-002: GitBranch.create() - 既存ブランチ
- UT-GB-003: GitBranch.switch() - 正常系
- UT-GB-004: GitBranch.switch() - 未コミット変更あり
- UT-GB-005: GitBranch.exists() - ローカルブランチ存在
- UT-GB-006: GitBranch.exists() - リモートブランチのみ存在
- UT-GB-007: GitBranch.get_current() - 正常系
"""
import pytest
from unittest.mock import Mock, MagicMock
from git import GitCommandError
from core.git.branch import GitBranch
from common.error_handler import GitBranchError


class TestGitBranch:
    """GitBranch クラスのユニットテスト"""

    def test_create_new_branch_succeeds(self):
        """UT-GB-001: 新規ブランチが正常に作成されることを確認"""
        # Given: Gitリポジトリのモック
        mock_repo = Mock()
        mock_repo.git.checkout = Mock()

        # ブランチ存在チェック用のモック
        mock_repo.branches = []

        # When: 新規ブランチを作成
        git_branch = GitBranch(mock_repo)

        # exists() をモック
        git_branch.exists = Mock(return_value=False)

        result = git_branch.create(branch_name="ai-workflow/issue-376")

        # Then: ブランチが作成される
        assert result['success'] is True
        assert result['branch_name'] == "ai-workflow/issue-376"
        assert result['error'] is None
        mock_repo.git.checkout.assert_called_with('-b', 'ai-workflow/issue-376')

    def test_create_existing_branch_checks_out(self):
        """UT-GB-002: 既存ブランチの場合にチェックアウトされることを確認"""
        # Given: 既存ブランチがあるリポジトリのモック
        mock_repo = Mock()
        mock_repo.git.checkout = Mock()

        git_branch = GitBranch(mock_repo)

        # exists() をモック（既存ブランチ）
        git_branch.exists = Mock(return_value=True)

        # When: 既存ブランチを作成しようとする
        result = git_branch.create(branch_name="existing-branch")

        # Then: チェックアウトのみ実行される
        assert result['success'] is True
        assert result['branch_name'] == "existing-branch"
        mock_repo.git.checkout.assert_called_with('existing-branch')

    def test_create_with_base_branch(self):
        """基準ブランチを指定してブランチ作成することを確認"""
        # Given: Gitリポジトリのモック
        mock_repo = Mock()
        mock_repo.git.checkout = Mock()

        git_branch = GitBranch(mock_repo)
        git_branch.exists = Mock(return_value=False)

        # When: 基準ブランチを指定してブランチ作成
        result = git_branch.create(
            branch_name="feature-branch",
            base_branch="main"
        )

        # Then: 基準ブランチにチェックアウト後、新規ブランチ作成
        assert result['success'] is True
        assert mock_repo.git.checkout.call_count == 2
        mock_repo.git.checkout.assert_any_call('main')
        mock_repo.git.checkout.assert_any_call('-b', 'feature-branch')

    def test_create_raises_error_on_failure(self):
        """ブランチ作成失敗時にエラーが発生することを確認"""
        # Given: checkout がエラーを発生させるモック
        mock_repo = Mock()
        mock_repo.git.checkout.side_effect = GitCommandError("checkout", "error")

        git_branch = GitBranch(mock_repo)
        git_branch.exists = Mock(return_value=False)

        # When/Then: GitBranchErrorが発生する
        with pytest.raises(GitBranchError):
            git_branch.create(branch_name="new-branch")

    def test_switch_to_different_branch_succeeds(self):
        """UT-GB-003: ブランチ切り替えが正常に動作することを確認"""
        # Given: Gitリポジトリのモック
        mock_repo = Mock()
        mock_repo.git.checkout = Mock()

        # 現在のブランチをモック
        mock_active_branch = Mock()
        mock_active_branch.name = "current-branch"
        mock_repo.active_branch = mock_active_branch

        git_branch = GitBranch(mock_repo)

        # When: 別のブランチに切り替え
        result = git_branch.switch(branch_name="main")

        # Then: 切り替えが成功する
        assert result['success'] is True
        assert result['branch_name'] == "main"
        assert result['error'] is None
        mock_repo.git.checkout.assert_called_with('main')

    def test_switch_to_same_branch_skips(self):
        """同じブランチへの切り替えがスキップされることを確認"""
        # Given: 現在mainブランチにいるモック
        mock_repo = Mock()
        mock_active_branch = Mock()
        mock_active_branch.name = "main"
        mock_repo.active_branch = mock_active_branch

        git_branch = GitBranch(mock_repo)

        # When: 同じブランチに切り替え
        result = git_branch.switch(branch_name="main")

        # Then: スキップされる
        assert result['success'] is True
        assert result['branch_name'] == "main"
        # checkoutは呼ばれない
        assert not mock_repo.git.checkout.called

    def test_switch_with_uncommitted_changes_fails(self):
        """UT-GB-004: 未コミット変更がある場合にエラーが返されることを確認"""
        # Given: checkout がエラーを発生させるモック
        mock_repo = Mock()
        mock_active_branch = Mock()
        mock_active_branch.name = "current-branch"
        mock_repo.active_branch = mock_active_branch

        mock_repo.git.checkout.side_effect = GitCommandError(
            "checkout",
            "Your local changes would be overwritten"
        )

        git_branch = GitBranch(mock_repo)

        # When: 未コミット変更がある状態でブランチ切り替え
        result = git_branch.switch(branch_name="main", force=False)

        # Then: エラーが返される
        assert result['success'] is False
        assert result['branch_name'] == "main"
        assert "Your local changes would be overwritten" in result['error']

    def test_switch_with_force_flag(self):
        """force=Trueで強制切り替えされることを確認"""
        # Given: Gitリポジトリのモック
        mock_repo = Mock()
        mock_active_branch = Mock()
        mock_active_branch.name = "current-branch"
        mock_repo.active_branch = mock_active_branch

        mock_repo.git.checkout = Mock()

        git_branch = GitBranch(mock_repo)

        # When: force=Trueでブランチ切り替え
        result = git_branch.switch(branch_name="main", force=True)

        # Then: -f オプション付きでcheckoutされる
        assert result['success'] is True
        mock_repo.git.checkout.assert_called_with('-f', 'main')

    def test_exists_returns_true_for_local_branch(self):
        """UT-GB-005: ローカルブランチの存在確認が正常に動作することを確認"""
        # Given: ローカルブランチが存在するモック
        mock_branch = Mock()
        mock_branch.name = "main"

        mock_repo = Mock()
        mock_repo.branches = [mock_branch]

        git_branch = GitBranch(mock_repo)

        # When: ローカルブランチの存在確認
        exists = git_branch.exists("main", check_remote=False)

        # Then: Trueが返される
        assert exists is True

    def test_exists_returns_true_for_remote_branch(self):
        """UT-GB-006: リモートブランチの存在確認が正常に動作することを確認"""
        # Given: リモートブランチのみ存在するモック
        mock_repo = Mock()
        mock_repo.branches = []  # ローカルブランチなし

        # リモートブランチのモック
        mock_remote_ref = Mock()
        mock_remote_ref.name = "origin/remote-only-branch"

        mock_remote = Mock()
        mock_remote.refs = [mock_remote_ref]

        mock_repo.remote.return_value = mock_remote

        git_branch = GitBranch(mock_repo)

        # When: リモートブランチの存在確認
        exists = git_branch.exists("remote-only-branch", check_remote=True)

        # Then: Trueが返される
        assert exists is True

    def test_exists_returns_false_for_nonexistent_branch(self):
        """存在しないブランチでFalseが返されることを確認"""
        # Given: ブランチが存在しないモック
        mock_repo = Mock()
        mock_repo.branches = []

        # リモートも空
        mock_remote = Mock()
        mock_remote.refs = []
        mock_repo.remote.return_value = mock_remote

        git_branch = GitBranch(mock_repo)

        # When: 存在しないブランチを確認
        exists = git_branch.exists("nonexistent-branch", check_remote=True)

        # Then: Falseが返される
        assert exists is False

    def test_get_current_returns_branch_name(self):
        """UT-GB-007: 現在のブランチ名が正しく取得されることを確認"""
        # Given: 現在のブランチがあるモック
        mock_active_branch = Mock()
        mock_active_branch.name = "ai-workflow/issue-376"

        mock_repo = Mock()
        mock_repo.active_branch = mock_active_branch

        git_branch = GitBranch(mock_repo)

        # When: 現在のブランチ名を取得
        current = git_branch.get_current()

        # Then: ブランチ名が返される
        assert current == "ai-workflow/issue-376"

    def test_get_current_returns_head_for_detached_state(self):
        """デタッチHEAD状態で'HEAD'が返されることを確認"""
        # Given: デタッチHEAD状態のモック
        mock_repo = Mock()
        mock_repo.active_branch = Mock(side_effect=TypeError)

        git_branch = GitBranch(mock_repo)

        # When: 現在のブランチ名を取得
        current = git_branch.get_current()

        # Then: 'HEAD'が返される
        assert current == "HEAD"
