"""Pytest共通設定・フィクスチャ

全テストで共有するフィクスチャを定義
"""
import os
import sys
from pathlib import Path
import pytest
from git import Repo


# プロジェクトルートをPYTHONPATHに追加
@pytest.fixture(scope="session", autouse=True)
def add_project_root_to_path():
    """プロジェクトルートをsys.pathに追加"""
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Gitリポジトリのルートディレクトリを取得"""
    try:
        repo = Repo(search_parent_directories=True)
        return Path(repo.working_dir)
    except Exception:
        return Path.cwd()


@pytest.fixture(scope="session")
def scripts_dir(repo_root) -> Path:
    """scripts/ai-workflowディレクトリのパスを取得"""
    return repo_root / 'scripts' / 'ai-workflow'


@pytest.fixture(scope="session")
def test_issue_number() -> str:
    """テスト用Issue番号"""
    return "304"


@pytest.fixture(scope="session")
def test_workflow_dir(repo_root, test_issue_number) -> Path:
    """テスト用ワークフローディレクトリ"""
    return repo_root / '.ai-workflow' / f'issue-{test_issue_number}'


@pytest.fixture(scope="session")
def github_token() -> str:
    """GitHub Personal Access Token"""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        pytest.skip("GITHUB_TOKEN not set")
    return token


@pytest.fixture(scope="session")
def github_repository() -> str:
    """GitHubリポジトリ名"""
    repo = os.getenv('GITHUB_REPOSITORY', 'tielec/infrastructure-as-code')
    return repo


@pytest.fixture(scope="session")
def claude_token() -> str:
    """Claude Code OAuth Token"""
    token = os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
    if not token:
        pytest.skip("CLAUDE_CODE_OAUTH_TOKEN not set")
    return token


@pytest.fixture
def sample_issue_info() -> dict:
    """サンプルIssue情報"""
    return {
        'number': 304,
        'title': '[TASK] AI駆動開発自動化ワークフロー MVP v1.0.0 - Phase 1実装',
        'state': 'open',
        'url': 'https://github.com/tielec/infrastructure-as-code/issues/304',
        'labels': ['enhancement', 'ai-workflow'],
        'body': 'Issue本文のサンプル...'
    }


@pytest.fixture
def sample_metadata() -> dict:
    """サンプルmetadata.json"""
    return {
        "workflow_version": "1.0.0",
        "issue_number": "304",
        "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/304",
        "issue_title": "AI駆動開発自動化ワークフロー MVP v1.0.0",
        "created_at": "2025-01-08T10:00:00Z",
        "updated_at": "2025-01-08T10:00:00Z",
        "status": "in_progress",
        "current_phase": "requirements",
        "phases": {
            "requirements": {"status": "completed", "started_at": "2025-01-08T10:00:00Z", "completed_at": "2025-01-08T10:30:00Z"},
            "design": {"status": "pending"},
            "test_scenario": {"status": "pending"},
            "implementation": {"status": "pending"},
            "testing": {"status": "pending"},
            "documentation": {"status": "pending"}
        },
        "cost_tracking": {
            "total_input_tokens": 50000,
            "total_output_tokens": 20000,
            "total_cost_usd": 2.5
        },
        "retry_count": 0,
        "max_retries": 3
    }
