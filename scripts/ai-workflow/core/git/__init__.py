"""Git Operations - Git操作モジュール

このモジュールは、Git操作を責務別に分割したクラスを提供します。

Classes:
    GitRepository: リポジトリ操作（リポジトリルート取得、ステータス確認等）
    GitBranch: ブランチ管理（ブランチ作成、切り替え、存在確認等）
    GitCommit: コミット操作（コミット作成、プッシュ、メッセージ生成等）

使用例:
    >>> from core.git import GitRepository, GitBranch, GitCommit
    >>>
    >>> repo = GitRepository(Path('/path/to/repo'))
    >>> branch = GitBranch(repo.repo)
    >>> commit = GitCommit(repo.repo, metadata_manager)
    >>>
    >>> # ブランチ作成
    >>> result = branch.create('feature/test')
    >>>
    >>> # ファイルコミット
    >>> files = repo.get_changed_files()
    >>> target_files = repo.filter_phase_files(files, issue_number)
    >>> result = commit.commit_phase_output('requirements', 'completed', target_files)
"""

from .repository import GitRepository
from .branch import GitBranch
from .commit import GitCommit

__all__ = [
    'GitRepository',
    'GitBranch',
    'GitCommit'
]
