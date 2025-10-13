"""
Unit tests for core/git/repository.py

Test Scenarios:
- UT-GR-001: GitRepository.get_root() - 正常系
- UT-GR-002: GitRepository.__init__() - リポジトリ不存在
- UT-GR-003: GitRepository.get_status() - 変更なし
- UT-GR-004: GitRepository.get_status() - 変更あり
- UT-GR-005: GitRepository.get_changed_files() - Issue番号フィルタ
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from core.git.repository import GitRepository


class TestGitRepository:
    """GitRepository クラスのユニットテスト"""

    @patch('core.git.repository.Repo')
    def test_get_root_returns_repository_root(self, mock_repo_class):
        """UT-GR-001: get_root() がリポジトリルートを返すことを確認"""
        # Given: Gitリポジトリのモック
        mock_repo = Mock()
        mock_repo.working_dir = "/path/to/repo"
        mock_repo_class.return_value = mock_repo

        # When: GitRepositoryを初期化してget_root()を呼び出す
        repo = GitRepository(Path("/path/to/repo"))
        root = repo.get_root()

        # Then: リポジトリルートPathが返される
        assert isinstance(root, Path)
        assert str(root) == "/path/to/repo"

    @patch('core.git.repository.Repo')
    def test_init_raises_error_when_repo_not_found(self, mock_repo_class):
        """UT-GR-002: Gitリポジトリが存在しない場合にエラーが発生することを確認"""
        # Given: Repoがエラーを発生させる
        mock_repo_class.side_effect = Exception("Not a git repository")

        # When/Then: RuntimeErrorが発生する
        with pytest.raises(RuntimeError, match="Git repository not found"):
            GitRepository(Path("/invalid/path"))

    @patch('core.git.repository.Repo')
    def test_get_status_returns_clean_state(self, mock_repo_class):
        """UT-GR-003: 変更がない状態でステータスが正しく取得されることを確認"""
        # Given: クリーンなリポジトリのモック
        mock_repo = Mock()
        mock_repo.working_dir = "/path/to/repo"
        mock_repo.is_dirty.return_value = False
        mock_repo.untracked_files = []

        # index.diff() のモック
        mock_repo.index.diff.return_value = []

        mock_repo_class.return_value = mock_repo

        # When: get_status()を呼び出す
        repo = GitRepository(Path("/path/to/repo"))
        status = repo.get_status()

        # Then: クリーンな状態が返される
        assert status['is_dirty'] is False
        assert status['untracked_files'] == []
        assert status['modified_files'] == []
        assert status['staged_files'] == []

    @patch('core.git.repository.Repo')
    def test_get_status_returns_dirty_state(self, mock_repo_class):
        """UT-GR-004: 変更がある状態でステータスが正しく取得されることを確認"""
        # Given: 変更があるリポジトリのモック
        mock_repo = Mock()
        mock_repo.working_dir = "/path/to/repo"
        mock_repo.is_dirty.return_value = True
        mock_repo.untracked_files = ['new_file.py']

        # modified_filesのモック
        modified_item = Mock()
        modified_item.a_path = 'existing_file.py'

        # staged_filesのモック
        staged_item = Mock()
        staged_item.a_path = 'staged_file.py'

        # index.diff() のモック設定
        mock_repo.index.diff.side_effect = [
            [modified_item],  # index.diff(None) - modified files
            [staged_item]     # index.diff('HEAD') - staged files
        ]

        mock_repo_class.return_value = mock_repo

        # When: get_status()を呼び出す
        repo = GitRepository(Path("/path/to/repo"))
        status = repo.get_status()

        # Then: 変更がある状態が返される
        assert status['is_dirty'] is True
        assert 'new_file.py' in status['untracked_files']
        assert 'existing_file.py' in status['modified_files']
        assert 'staged_file.py' in status['staged_files']

    @patch('core.git.repository.Repo')
    def test_get_changed_files_filters_by_issue_number(self, mock_repo_class):
        """UT-GR-005: Issue番号でフィルタリングされたファイルリストが返されることを確認"""
        # Given: 複数のIssueのファイルがあるリポジトリのモック
        mock_repo = Mock()
        mock_repo.working_dir = "/path/to/repo"
        mock_repo.is_dirty.return_value = True
        mock_repo.untracked_files = [
            '.ai-workflow/issue-376/metadata.json',
            '.ai-workflow/issue-377/metadata.json',
            'other_file.py'
        ]

        # modified_filesのモック
        modified_item_376 = Mock()
        modified_item_376.a_path = '.ai-workflow/issue-376/00_planning/output/planning.md'

        modified_item_377 = Mock()
        modified_item_377.a_path = '.ai-workflow/issue-377/00_planning/output/planning.md'

        mock_repo.index.diff.side_effect = [
            [modified_item_376, modified_item_377],  # modified files
            []  # staged files
        ]

        mock_repo_class.return_value = mock_repo

        # When: Issue 376のファイルを取得
        repo = GitRepository(Path("/path/to/repo"))
        changed_files = repo.get_changed_files(issue_number=376)

        # Then: Issue 376のファイルのみ返される
        assert len(changed_files) == 2
        assert '.ai-workflow/issue-376/metadata.json' in changed_files
        assert '.ai-workflow/issue-376/00_planning/output/planning.md' in changed_files
        assert '.ai-workflow/issue-377/metadata.json' not in changed_files

    @patch('core.git.repository.Repo')
    def test_get_changed_files_removes_duplicates(self, mock_repo_class):
        """get_changed_files() が重複ファイルを除去することを確認"""
        # Given: 重複したファイルがあるリポジトリのモック
        mock_repo = Mock()
        mock_repo.working_dir = "/path/to/repo"
        mock_repo.is_dirty.return_value = True
        mock_repo.untracked_files = [
            '.ai-workflow/issue-376/metadata.json'
        ]

        # modified_filesとstaged_filesで同じファイル
        mock_item = Mock()
        mock_item.a_path = '.ai-workflow/issue-376/metadata.json'

        mock_repo.index.diff.side_effect = [
            [mock_item],  # modified files
            [mock_item]   # staged files
        ]

        mock_repo_class.return_value = mock_repo

        # When: 変更ファイルを取得
        repo = GitRepository(Path("/path/to/repo"))
        changed_files = repo.get_changed_files(issue_number=376)

        # Then: 重複が除去される
        assert len(changed_files) == 1
        assert changed_files.count('.ai-workflow/issue-376/metadata.json') == 1
