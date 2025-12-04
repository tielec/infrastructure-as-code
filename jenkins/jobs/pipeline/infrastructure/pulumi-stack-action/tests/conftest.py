"""
pytest共通フィクスチャ

テストデータの準備、共通のセットアップ/ティアダウン処理を定義。
"""
import json
import sys
import pytest
from pathlib import Path


# src/ディレクトリをPythonパスに追加
@pytest.fixture(scope="session", autouse=True)
def add_src_to_path():
    """src/ディレクトリをPythonパスに追加"""
    src_path = Path(__file__).parent.parent / "src"
    sys.path.insert(0, str(src_path))
    yield
    sys.path.remove(str(src_path))


@pytest.fixture(scope="session")
def test_data_dir():
    """テストデータディレクトリのパスを返す"""
    return Path(__file__).parent / "fixtures" / "test_data"


@pytest.fixture(scope="session")
def sample_urns(test_data_dir):
    """サンプルURNデータを読み込む"""
    with open(test_data_dir / "sample_urns.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def sample_resources(test_data_dir):
    """サンプルリソースデータを読み込む"""
    with open(test_data_dir / "sample_resources.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def sample_dot_strings(test_data_dir):
    """サンプルDOT文字列を読み込む"""
    with open(test_data_dir / "sample_dot_strings.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def dot_file_generator():
    """DotFileGeneratorインスタンスを返す"""
    from dot_processor import DotFileGenerator
    return DotFileGenerator()


@pytest.fixture
def dot_file_processor():
    """DotFileProcessorインスタンスを返す"""
    from dot_processor import DotFileProcessor
    return DotFileProcessor()
