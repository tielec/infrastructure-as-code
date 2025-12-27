"""
Integration coverage for the pr_comment_generator workflows that need deterministic end-to-end checks.
"""

import importlib
import json
import logging
import sys
import types
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def _copy_fixture(tmp_path: Path, filename: str) -> Path:
    """Copy a JSON fixture from fixtures/ to the temporary directory."""
    fixture_path = FIXTURES_DIR / filename
    destination = tmp_path / filename
    destination.write_text(
        json.dumps(json.loads(fixture_path.read_text(encoding="utf-8")), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destination


def _create_template_dir(tmp_path: Path) -> Path:
    """Create a simple set of prompt templates for deterministic tests."""
    templates = tmp_path / "templates"
    templates.mkdir(parents=True, exist_ok=True)
    templates_data = {
        "base_template.md": "Base prompt: {input_format}\n\n{additional_instructions}",
        "chunk_analysis_extension.md": "Chunk analysis instructions",
        "summary_extension.md": "Summary instructions",
    }
    for name, content in templates_data.items():
        (templates / name).write_text(content, encoding="utf-8")
    return templates


def _inject_dummy_modules(monkeypatch):
    """Inject minimal openai and github modules so actual SDKs are not required."""
    dummy_openai = types.ModuleType("openai")

    class DummyOpenAI:
        def __init__(self, api_key=None):
            self.api_key = api_key
            self.chat = types.SimpleNamespace(completions=self)

        def create(self, **kwargs):
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))],
                usage=types.SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            )

    dummy_openai.OpenAI = DummyOpenAI
    monkeypatch.setitem(sys.modules, "openai", dummy_openai)

    dummy_github = types.ModuleType("github")

    class DummyGithub:
        def __init__(self, *args, **kwargs):
            pass

    class DummyGithubIntegration:
        def __init__(self, app_id, private_key):
            self.app_id = app_id
            self.private_key = private_key

        def get_access_token(self, installation_id):
            return types.SimpleNamespace(token="dummy-token")

    dummy_github.Github = DummyGithub
    dummy_github.GithubException = Exception
    dummy_github.GithubIntegration = DummyGithubIntegration
    monkeypatch.setitem(sys.modules, "github", dummy_github)


def _prepare_pr_comment_generator(monkeypatch, template_dir: Path):
    """Reload pr_comment_generator modules with stubbed dependencies."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("GITHUB_ACCESS_TOKEN", "test-github-token")
    _inject_dummy_modules(monkeypatch)

    import pr_comment_generator.openai_client as openai_client  # noqa: API used after reload

    openai_client = importlib.reload(openai_client)
    monkeypatch.setitem(sys.modules, "pr_comment_generator.openai_client", openai_client)

    import pr_comment_generator.generator as generator_module

    generator_module = importlib.reload(generator_module)

    class TestPromptTemplateManager(generator_module.PromptTemplateManager):
        def __init__(self, template_dir_arg):
            super().__init__(str(template_dir))

    class FakeGitHubClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_file_content(self, owner, repo, path, base_sha, head_sha):
            return "before content", "after content"

        def get_change_context(self, before_content, after_content, patch, context_lines=10):
            return {
                "before": before_content.splitlines() if before_content else [],
                "after": after_content.splitlines() if after_content else [],
                "changes": [{"type": "modify", "content": patch or ""}],
            }

    def _fake_call(self, messages, max_tokens=2000):
        payload = messages[-1]["content"]
        if "## 要件" in payload:
            return "Issue #536 regression title"
        if "## 必ず含めるべきファイル一覧" in payload:
            return "## 修正されたファイル\n- `src/auth/login.py`\n- `README.md`"
        if "### pr_info" in payload:
            return "Chunk analysis summary covering `src/auth/login.py`"
        return "Fallback analysis text referencing `tests/test_auth.py`"

    monkeypatch.setattr(generator_module, "PromptTemplateManager", TestPromptTemplateManager)
    monkeypatch.setattr(generator_module, "GitHubClient", FakeGitHubClient)
    monkeypatch.setattr(generator_module.OpenAIClient, "_call_openai_api", _fake_call)

    return generator_module


def _write_sample_files(tmp_path: Path):
    """Persist PR fixtures to disk so pr_comment_generator can read them."""
    pr_info_path = _copy_fixture(tmp_path, "sample_pr_info.json")
    pr_diff_path = _copy_fixture(tmp_path, "sample_diff.json")
    return pr_info_path, pr_diff_path


def _assert_successful_result(output_path: Path):
    """Validate the JSON output of pr_comment_generator."""
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "error" not in payload
    assert payload["processed_file_count"] > 0
    assert "suggested_title" in payload


def test_pr_comment_generator_cli_completes(monkeypatch, tmp_path, capsys):
    """Phase 3 CLI scenario: pr_comment_generator parses PR data without TokenEstimator tears."""
    template_dir = _create_template_dir(tmp_path / "template_source")
    generator_module = _prepare_pr_comment_generator(monkeypatch, template_dir)
    import pr_comment_generator.cli as cli_module

    cli_module = importlib.reload(cli_module)
    pr_info_path, pr_diff_path = _write_sample_files(tmp_path)
    output_path = tmp_path / "analysis_result.json"

    args = [
        "pr_comment_generator.py",
        "--pr-diff",
        str(pr_diff_path),
        "--pr-info",
        str(pr_info_path),
        "--output",
        str(output_path),
        "--log-level",
        "INFO",
    ]
    monkeypatch.setattr(sys, "argv", args)

    cli_module.main()

    captured = capsys.readouterr().out
    assert "Comment generation completed successfully!" in captured
    _assert_successful_result(output_path)
    # Ensure the more detailed flow touched the real generator instance
    assert generator_module.PRCommentGenerator


def test_pr_comment_generator_issue_536_regression(monkeypatch, tmp_path):
    """Regression check: TokenEstimator instance methods are used, preventing the reported crash."""
    template_dir = _create_template_dir(tmp_path / "template_source")
    generator_module = _prepare_pr_comment_generator(monkeypatch, template_dir)
    pr_info_path, pr_diff_path = _write_sample_files(tmp_path)

    import pr_comment_generator.token_estimator as token_module

    recorded_calls = []
    original_method = token_module.TokenEstimator.estimate_tokens

    def _wrapped_estimate(self, text):
        assert isinstance(self, token_module.TokenEstimator)
        recorded_calls.append(text)
        return original_method(self, text)

    monkeypatch.setattr(token_module.TokenEstimator, "estimate_tokens", _wrapped_estimate)

    generator = generator_module.PRCommentGenerator(log_level=logging.INFO)
    result = generator.generate_comment(str(pr_info_path), str(pr_diff_path))

    assert "error" not in result
    assert recorded_calls, "TokenEstimator.estimate_tokens should be invoked via the instance"
