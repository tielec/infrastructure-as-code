import json
import logging
import types

import pytest

from pr_comment_generator.generator import PRCommentGenerator
from pr_comment_generator.models import FileChange, PRInfo


def _make_generator():
    gen = PRCommentGenerator.__new__(PRCommentGenerator)
    gen.logger = logging.getLogger("generator-test")
    gen.skipped_file_names = []
    gen.max_files_to_process = 50
    gen.max_file_size = 10000
    gen.parallel_processing = False
    return gen


def test_normalize_file_paths_prefers_full_paths():
    gen = _make_generator()
    file_paths = ["main.py", "src/utils.py", "src/utils.py"]
    base_paths = ["src/main.py", "src/utils.py"]

    normalized = gen._normalize_file_paths(file_paths, base_paths)

    assert normalized == ["src/main.py", "src/utils.py"]


def test_rebuild_file_section_deduplicates_and_appends_skipped():
    gen = _make_generator()
    gen.skipped_file_names = ["src/ignored.py"]
    comment = """## 修正されたファイル
- `src/app.py`: updated
- `app.py`: duplicate entry
## その他
details here"""
    rebuilt = gen._rebuild_file_section(comment, ["src/app.py"])

    assert rebuilt.count("src/app.py") == 1
    assert "ignored.py" in rebuilt


def test_load_pr_data_reads_pr_info_and_diff(tmp_path):
    gen = _make_generator()
    gen._fetch_file_contents_sequential = types.MethodType(lambda self, pr_data, pr_info, changes: changes, gen)

    pr_info_path = tmp_path / "pr_info.json"
    pr_diff_path = tmp_path / "pr_diff.json"
    pr_info_path.write_text(
        json.dumps(
            {
                "title": "T",
                "number": 99,
                "body": "B",
                "user": {"login": "dev"},
                "base": {"ref": "main", "sha": "1"},
                "head": {"ref": "feature", "sha": "2"},
            }
        ),
        encoding="utf-8",
    )
    pr_diff_path.write_text(
        json.dumps([{"filename": "src/app.py", "status": "modified", "additions": 10, "deletions": 2, "changes": 12}]),
        encoding="utf-8",
    )

    pr_info, changes, skipped = gen.load_pr_data(str(pr_info_path), str(pr_diff_path))

    assert pr_info.number == 99
    assert [c.filename for c in changes] == ["src/app.py"]
    assert skipped == []


def test_load_pr_data_raises_on_missing_file(tmp_path):
    gen = _make_generator()
    gen._fetch_file_contents_sequential = types.MethodType(lambda self, pr_data, pr_info, changes: changes, gen)
    pr_diff_path = tmp_path / "pr_diff.json"
    pr_diff_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError):
        gen.load_pr_data(str(tmp_path / "missing.json"), str(pr_diff_path))


def test_load_pr_data_raises_on_invalid_json(tmp_path):
    gen = _make_generator()
    gen._fetch_file_contents_sequential = types.MethodType(lambda self, pr_data, pr_info, changes: changes, gen)

    pr_info_path = tmp_path / "pr_info.json"
    pr_info_path.write_text("{invalid-json", encoding="utf-8")
    pr_diff_path = tmp_path / "pr_diff.json"
    pr_diff_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError):
        gen.load_pr_data(str(pr_info_path), str(pr_diff_path))


def test_filter_large_files_filters_and_returns_skipped():
    gen = _make_generator()
    gen.max_file_size = 50
    small = FileChange(filename="small.py", status="modified", additions=10, deletions=5, changes=15)
    large = FileChange(filename="large.py", status="modified", additions=100, deletions=0, changes=100)

    filtered, skipped = gen._filter_large_files([small, large])

    assert filtered == [small]
    assert skipped == [large]


def test_filter_large_files_all_small_pass_through():
    gen = _make_generator()
    gen.max_file_size = 500
    files = [
        FileChange(filename="a.py", status="modified", additions=5, deletions=1, changes=6),
        FileChange(filename="b.py", status="modified", additions=10, deletions=2, changes=12),
    ]

    filtered, skipped = gen._filter_large_files(files)

    assert filtered == files
    assert skipped == []


def test_is_binary_file_detects_extensions():
    gen = _make_generator()

    assert gen._is_binary_file("image.png") is True
    assert gen._is_binary_file("archive.zip") is True
    assert gen._is_binary_file("script.py") is False
    assert gen._is_binary_file("config.json") is False


def test_generate_comment_returns_summary_and_usage(tmp_path):
    gen = _make_generator()

    class StubChunkAnalyzer:
        def calculate_optimal_chunk_size(self, changes):
            return 2

        def split_into_chunks(self, changes, chunk_size):
            return [changes]

        def analyze_single_chunk(self, pr_info, chunk, index):
            return f"analysis-{index}-{len(chunk)}"

    class StubOpenAIClient:
        def _generate_final_summary(self, pr_info, analyses):
            return "## 修正されたファイル\n- `src/app.py`: ok\n"

        def _generate_title_from_summary(self, comment):
            return "good title"

        def get_usage_stats(self):
            return {"total_tokens": 5, "prompt_tokens": 2, "completion_tokens": 3}

    gen.chunk_analyzer = StubChunkAnalyzer()
    gen.openai_client = StubOpenAIClient()

    pr_info = PRInfo(
        title="T",
        number=42,
        body="B",
        author="dev",
        base_branch="main",
        head_branch="feature",
        base_sha="1",
        head_sha="2",
    )
    changes = [FileChange(filename="src/app.py", status="modified", additions=1, deletions=0, changes=1, patch="@@")]

    def _fake_load_pr_data(self, pr_info_path, pr_diff_path):
        return pr_info, changes, []

    gen.load_pr_data = types.MethodType(_fake_load_pr_data, gen)

    pr_info_path = tmp_path / "pr_info.json"
    pr_info_path.write_text("{}", encoding="utf-8")
    pr_diff_path = tmp_path / "pr_diff.json"
    pr_diff_path.write_text(json.dumps([{"filename": "src/app.py"}]), encoding="utf-8")

    result = gen.generate_comment(str(pr_info_path), str(pr_diff_path))

    assert result["comment"].count("src/app.py") == 1
    assert result["suggested_title"] == "good title"
    assert result["processed_file_count"] == 1
    assert result["file_count"] == 1
    assert result["usage"]["total_tokens"] == 5


def test_generate_comment_includes_skipped_files(tmp_path):
    gen = _make_generator()

    class StubChunkAnalyzer:
        def calculate_optimal_chunk_size(self, changes):
            return 1

        def split_into_chunks(self, changes, chunk_size):
            return [changes]

        def analyze_single_chunk(self, pr_info, chunk, index):
            return "analysis"

    class StubOpenAIClient:
        def _generate_final_summary(self, pr_info, analyses):
            return "## 修正されたファイル\n- `src/processed.py`: done\n"

        def _generate_title_from_summary(self, comment):
            return "title"

        def get_usage_stats(self):
            return {"total_tokens": 1}

    gen.chunk_analyzer = StubChunkAnalyzer()
    gen.openai_client = StubOpenAIClient()

    pr_info = PRInfo(
        title="T",
        number=7,
        body="B",
        author="dev",
        base_branch="main",
        head_branch="feature",
        base_sha="1",
        head_sha="2",
    )
    changes = [FileChange(filename="src/processed.py", status="modified", additions=1, deletions=0, changes=1, patch="@@" )]
    skipped = ["large.bin"]

    def _fake_load_pr_data(self, pr_info_path, pr_diff_path):
        return pr_info, changes, skipped

    gen.load_pr_data = types.MethodType(_fake_load_pr_data, gen)

    pr_info_path = tmp_path / "pr_info.json"
    pr_info_path.write_text("{}", encoding="utf-8")
    pr_diff_path = tmp_path / "pr_diff.json"
    pr_diff_path.write_text(
        json.dumps([{"filename": "src/processed.py"}, {"filename": "large.bin"}]), encoding="utf-8"
    )

    result = gen.generate_comment(str(pr_info_path), str(pr_diff_path))

    assert "large.bin" in result["comment"]
    assert result["skipped_files"] == ["large.bin"]
    assert result["skipped_file_count"] == 1
    assert result["file_count"] == 2


def test_generate_comment_returns_message_when_no_changes(tmp_path):
    gen = _make_generator()

    class StubOpenAIClient:
        def get_usage_stats(self):
            return {"total_tokens": 0}

    gen.chunk_analyzer = None
    gen.openai_client = StubOpenAIClient()

    pr_info = PRInfo(
        title="T",
        number=8,
        body="B",
        author="dev",
        base_branch="main",
        head_branch="feature",
        base_sha="1",
        head_sha="2",
    )

    def _fake_load_pr_data(self, pr_info_path, pr_diff_path):
        return pr_info, [], []

    gen.load_pr_data = types.MethodType(_fake_load_pr_data, gen)

    pr_info_path = tmp_path / "pr_info.json"
    pr_info_path.write_text("{}", encoding="utf-8")
    pr_diff_path = tmp_path / "pr_diff.json"
    pr_diff_path.write_text("[]", encoding="utf-8")

    result = gen.generate_comment(str(pr_info_path), str(pr_diff_path))

    assert result["error"] == "No valid files to analyze"
    assert result["processed_file_count"] == 0
    assert result["file_count"] == 0
