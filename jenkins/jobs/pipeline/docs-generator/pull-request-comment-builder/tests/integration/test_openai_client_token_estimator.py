"""
Integration tests for OpenAIClient ↔ TokenEstimator interactions.
"""

import importlib
import sys
import types

import pytest

from pr_comment_generator.models import FileChange, PRInfo
from pr_comment_generator.prompt_manager import PromptTemplateManager


def _create_stubbed_openai_client(monkeypatch, tmp_path):
    """OpenAIClient を安全に初期化するためのヘルパー"""
    dummy_module = types.ModuleType("openai")

    class DummyChat:
        def __init__(self):
            self.completions = self

        def create(self, **kwargs):
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))],
                usage=types.SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            )

    class DummyOpenAI:
        def __init__(self, api_key=None):
            self.chat = DummyChat()

    dummy_module.OpenAI = DummyOpenAI
    monkeypatch.setitem(sys.modules, "openai", dummy_module)

    import pr_comment_generator.openai_client as oc  # pylint: disable=import-outside-toplevel
    oc = importlib.reload(oc)

    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "base_template.md").write_text("Base {input_format} {additional_instructions}", encoding="utf-8")
    (template_dir / "chunk_analysis_extension.md").write_text("chunk extra", encoding="utf-8")
    (template_dir / "summary_extension.md").write_text("summary extra", encoding="utf-8")

    prompt_manager = PromptTemplateManager(str(template_dir))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    return oc.OpenAIClient(prompt_manager)


def test_openai_client_estimate_chunk_tokens_calls_token_estimator(monkeypatch, tmp_path):
    """
    Given: OpenAIClient と TokenEstimator が初期化済み
    When: _estimate_chunk_tokens() を呼び出す
    Then: TokenEstimator.estimate_tokens() が PR情報と変更ごとに呼ばれる
    """
    client = _create_stubbed_openai_client(monkeypatch, tmp_path)
    captured_calls = []

    def fake_estimate(text):
        captured_calls.append(text)
        return 7

    client.token_estimator.estimate_tokens = fake_estimate

    pr_info = PRInfo(
        title="Fix TokenEstimator",
        number=1,
        body="Impactful change",
        author="dev",
        base_branch="main",
        head_branch="feature",
        base_sha="000",
        head_sha="111",
    )
    changes = [
        FileChange(
            filename="file.py",
            status="modified",
            additions=10,
            deletions=5,
            changes=15,
            patch="+ change\n" * 10,
        )
    ]

    total = client._estimate_chunk_tokens(pr_info, changes)

    assert total == 7 + 7 + 1000
    assert len(captured_calls) == 2
    assert "Fix TokenEstimator" in captured_calls[0]
    assert "file.py" in captured_calls[1]


def test_openai_client_truncate_chunk_analyses_uses_estimator(monkeypatch, tmp_path):
    """
    Given: OpenAIClient と複数チャンク分析
    When: _truncate_chunk_analyses() を実行する
    Then: TokenEstimator.truncate_text() がそれぞれのチャンクに対して呼ばれる
    """
    client = _create_stubbed_openai_client(monkeypatch, tmp_path)
    recorded = []

    def spy_truncate(text, max_tokens):
        recorded.append((text, max_tokens))
        return f"truncated:{int(max_tokens)}"

    client.token_estimator.truncate_text = spy_truncate

    analyses = ["analysis chunk one", "analysis chunk two", "analysis chunk three"]
    truncated = client._truncate_chunk_analyses(analyses)

    assert len(recorded) == len(analyses)
    expected_limit = int((client.MAX_TOKENS_PER_REQUEST * 0.6) / len(analyses))
    assert truncated == [f"truncated:{expected_limit}"] * len(analyses)
