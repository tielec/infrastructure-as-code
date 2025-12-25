import logging

from pr_comment_generator.chunk_analyzer import ChunkAnalyzer
from pr_comment_generator.models import FileChange, PRInfo


class DummyOpenAIClient:
    def __init__(self):
        self.calls = []

    def _calculate_optimal_chunk_size(self, changes):
        self.calls.append(("calculate", len(changes)))
        return 2

    def _split_changes_into_chunks(self, changes, chunk_size):
        self.calls.append(("split", chunk_size))
        return [changes[i : i + chunk_size] for i in range(0, len(changes), chunk_size)]

    def _analyze_chunk(self, pr_info, chunk, index):
        self.calls.append(("analyze", index, [c.filename for c in chunk]))
        return f"analysis-{index}"


def _make_changes(count=3):
    return [
        FileChange(filename=f"file{i}.py", status="modified", additions=1, deletions=1, changes=1)
        for i in range(count)
    ]


def test_calculate_and_split_delegate_to_openai_client():
    client = DummyOpenAIClient()
    analyzer = ChunkAnalyzer(client, log_level=logging.DEBUG)
    changes = _make_changes(4)

    size = analyzer.calculate_optimal_chunk_size(changes)
    chunks = analyzer.split_into_chunks(changes, size)

    assert size == 2
    assert len(chunks) == 2
    assert ("calculate", 4) in client.calls
    assert ("split", 2) in client.calls


def test_analyze_single_chunk_handles_exceptions():
    class ExplodingClient(DummyOpenAIClient):
        def _analyze_chunk(self, pr_info, chunk, index):
            raise RuntimeError("boom")

    analyzer = ChunkAnalyzer(ExplodingClient(), log_level=logging.DEBUG)
    pr_info = PRInfo(
        title="t",
        number=1,
        body="b",
        author="a",
        base_branch="main",
        head_branch="feature",
        base_sha="1",
        head_sha="2",
    )
    result = analyzer.analyze_single_chunk(pr_info, _make_changes(1), 1)

    assert "失敗" in result
