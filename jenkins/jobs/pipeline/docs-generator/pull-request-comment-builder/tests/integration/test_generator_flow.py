import importlib
import json
import logging
import sys
import types


def test_generate_comment_happy_path(monkeypatch, tmp_path):
    dummy_openai = types.ModuleType("openai")
    dummy_openai.OpenAI = lambda api_key=None: None
    monkeypatch.setitem(sys.modules, "openai", dummy_openai)

    import pr_comment_generator.openai_client as oc

    oc = importlib.reload(oc)
    sys.modules["pr_comment_generator.openai_client"] = oc

    class FakeOpenAIClient:
        def __init__(self, prompt_manager, retry_config=None, log_level=logging.INFO):
            self.prompt_manager = prompt_manager

        def _calculate_optimal_chunk_size(self, changes):
            return 2

        def _split_changes_into_chunks(self, changes, chunk_size):
            return [changes]

        def _analyze_chunk(self, pr_info, chunk, index):
            return "analysis"

        def _generate_final_summary(self, pr_info, chunk_analyses):
            return "## 修正されたファイル\n- `src/main.py`: ok\n"

        def _generate_title_from_summary(self, comment):
            return "title"

        def get_usage_stats(self):
            return {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0, "retries": 0, "skipped_files": 0}

    class FakeChunkAnalyzer:
        def __init__(self, openai_client, log_level=logging.INFO):
            self.openai_client = openai_client

        def calculate_optimal_chunk_size(self, changes):
            return self.openai_client._calculate_optimal_chunk_size(changes)

        def split_into_chunks(self, changes, chunk_size):
            return [changes]

        def analyze_single_chunk(self, pr_info, chunk, index):
            return self.openai_client._analyze_chunk(pr_info, chunk, index)

    class FakeGitHubClient:
        def __init__(self, auth_method=None, app_id=None, token=None):
            self.calls = []

        def get_file_content(self, owner, repo, path, base_sha, head_sha):
            self.calls.append(("content", path))
            return "before", "after"

        def get_change_context(self, before_content, after_content, patch, context_lines=10):
            self.calls.append(("context", patch))
            return {"before": before_content, "after": after_content, "patch": patch}

    class FakePromptTemplateManager:
        def __init__(self, template_dir):
            self.template_dir = template_dir

    import pr_comment_generator.generator as gen

    monkeypatch.setattr(gen, "OpenAIClient", FakeOpenAIClient)
    monkeypatch.setattr(gen, "ChunkAnalyzer", FakeChunkAnalyzer)
    monkeypatch.setattr(gen, "GitHubClient", FakeGitHubClient)
    monkeypatch.setattr(gen, "PromptTemplateManager", FakePromptTemplateManager)

    pr_info_path = tmp_path / "info.json"
    pr_diff_path = tmp_path / "diff.json"

    pr_info_path.write_text(
        json.dumps(
            {
                "title": "PR",
                "number": 1,
                "body": "B",
                "user": {"login": "dev"},
                "base": {"ref": "main", "sha": "1"},
                "head": {"ref": "feature", "sha": "2"},
            }
        ),
        encoding="utf-8",
    )
    pr_diff_path.write_text(
        json.dumps([{"filename": "src/main.py", "status": "modified", "additions": 1, "deletions": 0, "changes": 1, "patch": "@@ -1 +1 @@\n-a\n+b"}]),
        encoding="utf-8",
    )

    generator = gen.PRCommentGenerator(log_level=logging.DEBUG)
    result = generator.generate_comment(str(pr_info_path), str(pr_diff_path))

    assert result["comment"].count("src/main.py") == 1
    assert result["suggested_title"] == "title"
    assert result["processed_file_count"] == 1
