"""
pytest共通設定ファイル

このファイルは全テストで共有されるフィクスチャと設定を提供します。
"""

import pytest
import sys
import os
import logging

# プロジェクトのsrcディレクトリをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)


@pytest.fixture(scope="session")
def test_logger():
    """
    テスト用のロガーを提供する（セッションスコープ）

    Returns:
        logging.Logger: テスト用のロガーインスタンス
    """
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)

    # コンソールハンドラー
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # フォーマッター
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger


@pytest.fixture
def sample_pr_info_data():
    """
    テスト用のPR情報JSONデータを提供する

    Returns:
        dict: PR情報のサンプルデータ
    """
    return {
        "title": "Test PR Title",
        "number": 123,
        "body": "This is a test PR body",
        "user": {"login": "testuser"},
        "base": {"ref": "main", "sha": "abc123def456"},
        "head": {"ref": "feature-branch", "sha": "def456abc123"}
    }


@pytest.fixture
def sample_file_change_data():
    """
    テスト用のファイル変更JSONデータを提供する

    Returns:
        dict: ファイル変更のサンプルデータ
    """
    return {
        "filename": "src/test.py",
        "status": "modified",
        "additions": 10,
        "deletions": 5,
        "changes": 15,
        "patch": "@@ -1,3 +1,4 @@\n import sys\n+import os\n def main():\n     pass"
    }


@pytest.fixture
def sample_file_changes_list():
    """
    テスト用のファイル変更リストを提供する

    Returns:
        list: ファイル変更データのリスト
    """
    return [
        {
            "filename": "src/main.py",
            "status": "modified",
            "additions": 20,
            "deletions": 10,
            "changes": 30,
            "patch": "@@ -1,10 +1,20 @@\n# Changes"
        },
        {
            "filename": "src/utils.py",
            "status": "added",
            "additions": 50,
            "deletions": 0,
            "changes": 50,
            "patch": "@@ -0,0 +1,50 @@\n# New file"
        },
        {
            "filename": "tests/test_new.py",
            "status": "added",
            "additions": 100,
            "deletions": 0,
            "changes": 100,
            "patch": "@@ -0,0 +1,100 @@\n# New test file"
        }
    ]


# pytest設定
def pytest_configure(config):
    """pytestの設定をカスタマイズ"""
    # カスタムマーカーの登録
    config.addinivalue_line(
        "markers", "unit: ユニットテスト"
    )
    config.addinivalue_line(
        "markers", "integration: 統合テスト"
    )
    config.addinivalue_line(
        "markers", "bdd: BDDテスト"
    )
    config.addinivalue_line(
        "markers", "slow: 実行に時間がかかるテスト"
    )
