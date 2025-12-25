import logging

from pr_comment_generator.generator import PRCommentGenerator


def _make_generator():
    gen = PRCommentGenerator.__new__(PRCommentGenerator)
    gen.logger = logging.getLogger("generator-test")
    gen.skipped_file_names = []
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
