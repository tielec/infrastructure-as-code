import importlib
import json
import logging
import sys
import types
import os

import pytest


def _import_cli_with_stub(monkeypatch):
    """Reload CLI module with a stubbed openai dependency."""
    dummy_openai = types.ModuleType("openai")

    class DummyOpenAI:
        def __init__(self, api_key=None):
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **kwargs: None))

    dummy_openai.OpenAI = DummyOpenAI
    monkeypatch.setitem(sys.modules, "openai", dummy_openai)

    import pr_comment_generator.openai_client as oc
    oc = importlib.reload(oc)
    sys.modules["pr_comment_generator.openai_client"] = oc

    import pr_comment_generator.generator as gen
    gen = importlib.reload(gen)
    sys.modules["pr_comment_generator.generator"] = gen

    import pr_comment_generator.cli as cli

    return importlib.reload(cli)


def test_create_argument_parser_requires_arguments(monkeypatch):
    cli = _import_cli_with_stub(monkeypatch)
    parser = cli.create_argument_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_setup_environment_from_args_creates_prompt_dir(monkeypatch, tmp_path):
    cli = _import_cli_with_stub(monkeypatch)
    prompt_dir = tmp_path / "prompts"
    args = types.SimpleNamespace(
        pr_diff="d",
        pr_info="i",
        output="o",
        log_level="INFO",
        parallel=True,
        save_prompts=True,
        prompt_output_dir=str(prompt_dir),
    )

    cli.setup_environment_from_args(args)

    assert os.environ["PARALLEL_PROCESSING"] == "true"
    assert os.environ["SAVE_PROMPTS"] == "true"
    assert prompt_dir.exists()


def test_setup_environment_from_args_defaults_keep_env_clean(monkeypatch):
    cli = _import_cli_with_stub(monkeypatch)
    monkeypatch.delenv("PARALLEL_PROCESSING", raising=False)
    monkeypatch.delenv("SAVE_PROMPTS", raising=False)
    args = types.SimpleNamespace(
        pr_diff="d",
        pr_info="i",
        output="o",
        log_level="INFO",
        parallel=False,
        save_prompts=False,
        prompt_output_dir="/tmp/prompts",
    )

    cli.setup_environment_from_args(args)

    assert os.environ.get("SAVE_PROMPTS") is None
    assert os.environ.get("PARALLEL_PROCESSING") is None


def test_main_writes_output_file(monkeypatch, tmp_path):
    cli = _import_cli_with_stub(monkeypatch)

    class FakeGenerator:
        def __init__(self, log_level=logging.INFO):
            self.log_level = log_level

        def generate_comment(self, pr_info, pr_diff):
            return {
                "comment": "ok",
                "suggested_title": "title",
                "usage": {"total_tokens": 1},
                "file_count": 1,
                "total_changes": 1,
                "skipped_file_count": 0,
                "processed_file_count": 1,
                "skipped_files": [],
            }

    monkeypatch.setattr(cli, "PRCommentGenerator", FakeGenerator)

    pr_info_path = tmp_path / "pr_info.json"
    pr_diff_path = tmp_path / "pr_diff.json"
    output_path = tmp_path / "out.json"

    pr_info_path.write_text(
        json.dumps(
            {
                "title": "T",
                "number": 1,
                "body": "B",
                "user": {"login": "dev"},
                "base": {"ref": "main", "sha": "1"},
                "head": {"ref": "feature", "sha": "2"},
            }
        ),
        encoding="utf-8",
    )
    pr_diff_path.write_text(json.dumps([{"filename": "f.py", "changes": 1, "status": "modified"}]), encoding="utf-8")

    monkeypatch.setenv("SAVE_PROMPTS", "false")
    monkeypatch.setenv("PARALLEL_PROCESSING", "false")
    sys.argv = [
        "prog",
        "--pr-diff",
        str(pr_diff_path),
        "--pr-info",
        str(pr_info_path),
        "--output",
        str(output_path),
    ]

    cli.main()

    assert output_path.exists()
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["comment"] == "ok"


def test_main_writes_error_json_on_exception(monkeypatch, tmp_path):
    cli = _import_cli_with_stub(monkeypatch)

    class ExplodingGenerator:
        def __init__(self, log_level=logging.INFO):
            self.log_level = log_level

        def generate_comment(self, pr_info, pr_diff):
            raise ValueError("missing input files")

    monkeypatch.setattr(cli, "PRCommentGenerator", ExplodingGenerator)

    output_path = tmp_path / "error.json"
    sys.argv = [
        "prog",
        "--pr-diff",
        str(tmp_path / "nonexistent_diff.json"),
        "--pr-info",
        str(tmp_path / "nonexistent_info.json"),
        "--output",
        str(output_path),
    ]

    with pytest.raises(SystemExit):
        cli.main()

    assert output_path.exists()
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["error"] == "missing input files"
    assert "traceback" in data
