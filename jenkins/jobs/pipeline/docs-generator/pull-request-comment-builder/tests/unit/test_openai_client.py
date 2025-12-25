import importlib
import sys
import types

import pytest

from pr_comment_generator.models import FileChange
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
