import logging
import types

from pr_comment_generator.chunk_analyzer import ChunkAnalyzer
from pr_comment_generator.models import FileChange, PRInfo
from pr_comment_generator.openai_client import OpenAIClient


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


def _make_pr_info():
    return PRInfo(
        title="t",
        number=1,
        body="b",
        author="a",
        base_branch="main",
        head_branch="feature",
        base_sha="1",
        head_sha="2",
    )


def _make_openai_client_with_real_chunk_logic():
    client = types.SimpleNamespace()
    client.logger = logging.getLogger("openai-stub")
    client._calculate_optimal_chunk_size = OpenAIClient._calculate_optimal_chunk_size.__get__(client, OpenAIClient)
    client._split_changes_into_chunks = OpenAIClient._split_changes_into_chunks.__get__(client, OpenAIClient)

    def _analyze_chunk(self, pr_info, chunk, index):
        return f"analysis-{index}:{len(chunk)}"

    client._analyze_chunk = types.MethodType(_analyze_chunk, client)
    return client


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
    result = analyzer.analyze_single_chunk(_make_pr_info(), _make_changes(1), 1)

    assert "失敗" in result


def test_calculate_optimal_chunk_size_variants():
    client = _make_openai_client_with_real_chunk_logic()
    analyzer = ChunkAnalyzer(client, log_level=logging.DEBUG)

    small_changes = [
        FileChange(filename=f"small{i}.py", status="modified", additions=50, deletions=50, changes=100) for i in range(3)
    ]
    large_changes = [
        FileChange(filename=f"large{i}.py", status="modified", additions=300, deletions=200, changes=500) for i in range(20)
    ]

    assert analyzer.calculate_optimal_chunk_size(small_changes) >= 2
    assert analyzer.calculate_optimal_chunk_size(large_changes) == 1
    assert analyzer.calculate_optimal_chunk_size([]) == 0
    assert analyzer.calculate_optimal_chunk_size([small_changes[0]]) == 1


def test_split_into_chunks_respects_boundaries():
    client = _make_openai_client_with_real_chunk_logic()
    analyzer = ChunkAnalyzer(client, log_level=logging.DEBUG)

    ten_files = [
        FileChange(filename=f"file{i}.txt", status="modified", additions=1, deletions=0, changes=1) for i in range(10)
    ]
    nine_files = [
        FileChange(filename=f"even{i}.txt", status="modified", additions=1, deletions=0, changes=1) for i in range(9)
    ]
    two_files = [
        FileChange(filename=f"tiny{i}.txt", status="modified", additions=1, deletions=0, changes=1) for i in range(2)
    ]

    chunks = analyzer.split_into_chunks(ten_files, 3)
    assert [len(c) for c in chunks] == [3, 3, 3, 1]

    even_chunks = analyzer.split_into_chunks(nine_files, 3)
    assert [len(c) for c in even_chunks] == [3, 3, 3]

    small_chunk = analyzer.split_into_chunks(two_files, 5)
    assert len(small_chunk) == 1
    assert len(small_chunk[0]) == 2


def test_analyze_all_chunks_includes_results_and_errors():
    client = DummyOpenAIClient()
    analyzer = ChunkAnalyzer(client, log_level=logging.DEBUG)
    pr_info = _make_pr_info()
    chunks = [ _make_changes(1), _make_changes(2) ]

    results = analyzer.analyze_all_chunks(pr_info, chunks)

    assert results == ["analysis-1", "analysis-2"]
    assert ("analyze", 2, ["file0.py", "file1.py"]) in client.calls


def test_analyze_all_chunks_continues_on_failure():
    class FlakyClient(DummyOpenAIClient):
        def _analyze_chunk(self, pr_info, chunk, index):
            if index == 2:
                raise ValueError("chunk fail")
            return super()._analyze_chunk(pr_info, chunk, index)

    analyzer = ChunkAnalyzer(FlakyClient(), log_level=logging.DEBUG)
    pr_info = _make_pr_info()
    chunks = [_make_changes(1), _make_changes(1), _make_changes(1)]

    results = analyzer.analyze_all_chunks(pr_info, chunks)

    assert len(results) == 3
    assert "分析に失敗しました" in results[1]
    assert results[2].startswith("analysis-")
