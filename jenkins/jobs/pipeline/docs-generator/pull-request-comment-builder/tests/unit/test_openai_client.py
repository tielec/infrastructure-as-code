import importlib
import json
import sys
import types

import pytest

from pr_comment_generator.models import FileChange, PRInfo
from pr_comment_generator.prompt_manager import PromptTemplateManager


def _prepare_openai_client(monkeypatch, tmp_path):
    """Stub openai module and reload client for isolated tests."""
    dummy_module = types.ModuleType("openai")

    class DummyChat:
        def __init__(self):
            self.completions = self

        def create(self, **kwargs):
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))],
                usage=types.SimpleNamespace(prompt_tokens=5, completion_tokens=5, total_tokens=10),
            )

    class DummyOpenAI:
        def __init__(self, api_key=None):
            self.chat = DummyChat()

    dummy_module.OpenAI = DummyOpenAI
    monkeypatch.setitem(sys.modules, "openai", dummy_module)

    import pr_comment_generator.openai_client as oc

    oc = importlib.reload(oc)

    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "base_template.md").write_text("Base {input_format} {additional_instructions}", encoding="utf-8")
    (template_dir / "chunk_analysis_extension.md").write_text("chunk extra", encoding="utf-8")
    (template_dir / "summary_extension.md").write_text("summary extra", encoding="utf-8")
    prompt_manager = PromptTemplateManager(str(template_dir))
    return oc, prompt_manager


def _create_openai_client(monkeypatch, tmp_path, retry_config=None):
    """Helper to build OpenAIClient with a stubbed openai module."""
    oc, prompt_manager = _prepare_openai_client(monkeypatch, tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = oc.OpenAIClient(prompt_manager, retry_config=retry_config)
    return oc, client


def test_init_without_api_key_raises(monkeypatch, tmp_path):
    oc, prompt_manager = _prepare_openai_client(monkeypatch, tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError):
        oc.OpenAIClient(prompt_manager)


def test_init_applies_custom_retry_config(monkeypatch, tmp_path):
    oc, prompt_manager = _prepare_openai_client(monkeypatch, tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    retry_config = {"max_retries": 3, "initial_backoff": 2, "max_backoff": 30}

    client = oc.OpenAIClient(prompt_manager, retry_config=retry_config)

    assert client.retry_config == retry_config
    assert client.usage_stats["retries"] == 0


def test_manage_input_size_leaves_small_payload(monkeypatch, tmp_path):
    oc, prompt_manager = _prepare_openai_client(monkeypatch, tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(oc.TokenEstimator, "estimate_tokens", staticmethod(lambda text: 10))
    client = oc.OpenAIClient(prompt_manager)

    payload = {"pr_info": {"title": "t"}, "changes": []}
    managed = client._manage_input_size(payload, is_single_file=False)

    assert managed == payload


def test_calculate_optimal_chunk_size_handles_large_file(monkeypatch, tmp_path):
    oc, prompt_manager = _prepare_openai_client(monkeypatch, tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = oc.OpenAIClient(prompt_manager)

    changes = [FileChange(filename="big.py", status="modified", additions=0, deletions=0, changes=400)]

    assert client._calculate_optimal_chunk_size(changes) == 1


def test_call_api_success_updates_usage(monkeypatch, tmp_path):
    oc, client = _create_openai_client(monkeypatch, tmp_path)
    monkeypatch.setattr(client, "_save_prompt_and_result_if_needed", lambda *_, **__: None)

    result = client._call_openai_api([{"role": "user", "content": "hello"}], max_tokens=50)

    assert result == "ok"
    assert client.usage_stats["prompt_tokens"] == 5
    assert client.usage_stats["completion_tokens"] == 5
    assert client.usage_stats["retries"] == 0


def test_call_api_retries_on_rate_limit_then_succeeds(monkeypatch, tmp_path):
    oc, client = _create_openai_client(monkeypatch, tmp_path)
    waits = []
    monkeypatch.setattr(client, "_wait_before_retry", lambda sleep_time: waits.append(sleep_time))
    monkeypatch.setattr(client, "_save_prompt_and_result_if_needed", lambda *_, **__: None)

    class RateLimitError(Exception):
        def __init__(self, message, status_code=429):
            super().__init__(message)
            self.status_code = status_code

    success_response = types.SimpleNamespace(
        choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="recovered"))],
        usage=types.SimpleNamespace(prompt_tokens=7, completion_tokens=9, total_tokens=16),
    )
    responses = iter(
        [
            RateLimitError("rate limit: retry after 2 seconds"),
            RateLimitError("rate limit: retry after 2 seconds"),
            success_response,
        ]
    )

    def fake_make_api_request(messages, max_tokens):
        next_item = next(responses)
        if isinstance(next_item, Exception):
            raise next_item
        return next_item

    monkeypatch.setattr(client, "_make_api_request", fake_make_api_request)

    result = client._call_openai_api([{"role": "user", "content": "need retry"}])

    assert result == "recovered"
    assert client.usage_stats["retries"] == 2
    assert waits == [2, 2]


def test_call_api_raises_after_max_retries(monkeypatch, tmp_path):
    _, client = _create_openai_client(
        monkeypatch,
        tmp_path,
        retry_config={"max_retries": 2, "initial_backoff": 0, "max_backoff": 0},
    )
    waits = []
    monkeypatch.setattr(client, "_wait_before_retry", lambda sleep_time: waits.append(sleep_time))
    monkeypatch.setattr(client, "_save_prompt_and_result_if_needed", lambda *_, **__: None)

    call_count = {"attempts": 0}

    def always_fail(messages, max_tokens=0):
        call_count["attempts"] += 1
        raise RuntimeError("unrecoverable")

    monkeypatch.setattr(client, "_make_api_request", always_fail)

    with pytest.raises(RuntimeError):
        client._call_openai_api([{"role": "user", "content": "boom"}], max_tokens=10)

    assert call_count["attempts"] == 2
    assert client.usage_stats["retries"] == 2
    assert waits == [0]


def test_calculate_optimal_chunk_size_small_pr(monkeypatch, tmp_path):
    _, client = _create_openai_client(monkeypatch, tmp_path)
    changes = [
        FileChange(filename=f"file{i}.py", status="modified", additions=50, deletions=50, changes=100)
        for i in range(3)
    ]

    assert client._calculate_optimal_chunk_size(changes) == 3


def test_calculate_optimal_chunk_size_large_pr(monkeypatch, tmp_path):
    _, client = _create_openai_client(monkeypatch, tmp_path)
    changes = [
        FileChange(filename=f"file{i}.py", status="modified", additions=250, deletions=250, changes=500)
        for i in range(20)
    ]

    assert client._calculate_optimal_chunk_size(changes) == 1


def test_calculate_optimal_chunk_size_empty(monkeypatch, tmp_path):
    _, client = _create_openai_client(monkeypatch, tmp_path)

    assert client._calculate_optimal_chunk_size([]) == 0


def test_calculate_optimal_chunk_size_single(monkeypatch, tmp_path):
    _, client = _create_openai_client(monkeypatch, tmp_path)
    changes = [FileChange(filename="solo.py", status="modified", additions=10, deletions=1, changes=11)]

    assert client._calculate_optimal_chunk_size(changes) == 1


def test_save_prompt_and_result_writes_files(monkeypatch, tmp_path):
    _, client = _create_openai_client(monkeypatch, tmp_path)
    monkeypatch.setenv("SAVE_PROMPTS", "true")
    output_dir = tmp_path / "prompts"
    monkeypatch.setenv("PROMPT_OUTPUT_DIR", str(output_dir))
    client.pr_info = PRInfo(
        title="t",
        number=42,
        body="b",
        author="dev",
        base_branch="main",
        head_branch="feature",
        base_sha="1",
        head_sha="2",
    )
    client.usage_stats["prompt_tokens"] = 3
    client.usage_stats["completion_tokens"] = 7

    client._save_prompt_and_result("prompt text", "result text", chunk_index=2, phase="summary")

    pr_dirs = list(output_dir.iterdir())
    assert len(pr_dirs) == 1
    pr_dir = pr_dirs[0]
    assert pr_dir.name.startswith("pr_42_")
    assert (pr_dir / "summary_chunk2_prompt.txt").read_text(encoding="utf-8") == "prompt text"
    assert (pr_dir / "summary_chunk2_result.txt").read_text(encoding="utf-8") == "result text"
    meta = json.loads((pr_dir / "summary_chunk2_meta.json").read_text(encoding="utf-8"))
    assert meta["pr_number"] == 42
    assert meta["chunk_index"] == 2
    assert meta["phase"] == "summary"
    assert meta["usage_stats"]["prompt_tokens"] == 3
    assert meta["usage_stats"]["completion_tokens"] == 7


def test_save_prompt_and_result_skips_when_disabled(monkeypatch, tmp_path):
    _, client = _create_openai_client(monkeypatch, tmp_path)
    monkeypatch.setenv("SAVE_PROMPTS", "false")
    output_dir = tmp_path / "no_write"
    monkeypatch.setenv("PROMPT_OUTPUT_DIR", str(output_dir))
    client.pr_info = PRInfo(
        title="t",
        number=99,
        body="b",
        author="dev",
        base_branch="main",
        head_branch="feature",
        base_sha="1",
        head_sha="2",
    )

    client._save_prompt_and_result("prompt text", "result text", chunk_index=0, phase="chunk")

    assert not output_dir.exists()
