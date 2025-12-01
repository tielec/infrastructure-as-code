"""
ユニットテスト: statistics.py

テスト対象:
- PRCommentStatistics: 統計計算とチャンクサイズ最適化機能
"""

import pytest
import logging
from pr_comment_generator.statistics import PRCommentStatistics
from pr_comment_generator.models import FileChange
from pr_comment_generator.token_estimator import TokenEstimator


class TestPRCommentStatistics:
    """PRCommentStatisticsクラスのテスト"""

    @pytest.fixture
    def statistics(self):
        """PRCommentStatisticsインスタンスをフィクスチャとして提供"""
        logger = logging.getLogger("test")
        token_estimator = TokenEstimator(logger=logger)
        return PRCommentStatistics(token_estimator=token_estimator, logger=logger)

    @pytest.fixture
    def sample_files(self):
        """サンプルのFileChangeリストを提供"""
        return [
            FileChange(
                filename="file1.py",
                status="modified",
                additions=10,
                deletions=5,
                changes=15,
                patch="diff content " * 50
            ),
            FileChange(
                filename="file2.py",
                status="modified",
                additions=20,
                deletions=10,
                changes=30,
                patch="diff content " * 100
            ),
            FileChange(
                filename="file3.py",
                status="added",
                additions=50,
                deletions=0,
                changes=50,
                patch="diff content " * 150
            )
        ]

    def test_calculate_optimal_chunk_size_正常系(self, statistics, sample_files):
        """
        Given: ファイル変更リストが与えられた場合
        When: calculate_optimal_chunk_size()を呼び出す
        Then: 最適なチャンクサイズが計算される
        """
        # Given
        max_tokens = 3000

        # When
        chunk_size = statistics.calculate_optimal_chunk_size(sample_files, max_tokens)

        # Then
        assert chunk_size >= 1
        assert chunk_size <= len(sample_files)

    def test_calculate_optimal_chunk_size_境界値_空リスト(self, statistics):
        """
        Given: 空のファイルリストが与えられた場合
        When: calculate_optimal_chunk_size()を呼び出す
        Then: デフォルトの最小チャンクサイズが返される
        """
        # Given
        files = []

        # When
        chunk_size = statistics.calculate_optimal_chunk_size(files)

        # Then
        assert chunk_size == PRCommentStatistics.DEFAULT_MIN_CHUNK_SIZE

    def test_estimate_chunk_tokens_正常系(self, statistics, sample_files):
        """
        Given: ファイルチャンクが与えられた場合
        When: estimate_chunk_tokens()を呼び出す
        Then: チャンクのトークン数が推定される
        """
        # Given
        chunk = sample_files[:2]

        # When
        tokens = statistics.estimate_chunk_tokens(chunk)

        # Then
        assert tokens > 0

    def test_estimate_chunk_tokens_境界値_空チャンク(self, statistics):
        """
        Given: 空のチャンクが与えられた場合
        When: estimate_chunk_tokens()を呼び出す
        Then: 0トークンが返される
        """
        # Given
        chunk = []

        # When
        tokens = statistics.estimate_chunk_tokens(chunk)

        # Then
        assert tokens == 0

    def test_estimate_chunk_tokens_正常系_patch_None(self, statistics):
        """
        Given: patchがNoneのファイルを含むチャンク
        When: estimate_chunk_tokens()を呼び出す
        Then: エラーなくトークン数が推定される
        """
        # Given
        chunk = [
            FileChange(
                filename="renamed.py",
                status="renamed",
                additions=0,
                deletions=0,
                changes=0,
                patch=None
            )
        ]

        # When
        tokens = statistics.estimate_chunk_tokens(chunk)

        # Then
        assert tokens == 0

    def test_calculate_statistics_正常系(self, statistics, sample_files):
        """
        Given: ファイル変更リストが与えられた場合
        When: calculate_statistics()を呼び出す
        Then: 統計情報が正しく計算される
        """
        # When
        stats = statistics.calculate_statistics(sample_files)

        # Then
        assert stats['file_count'] == 3
        assert stats['total_additions'] == 80  # 10 + 20 + 50
        assert stats['total_deletions'] == 15  # 5 + 10 + 0
        assert stats['total_changes'] == 95   # 15 + 30 + 50
        assert stats['avg_changes_per_file'] == pytest.approx(95 / 3)

    def test_calculate_statistics_境界値_空リスト(self, statistics):
        """
        Given: 空のファイルリストが与えられた場合
        When: calculate_statistics()を呼び出す
        Then: ゼロ値の統計情報が返される
        """
        # Given
        files = []

        # When
        stats = statistics.calculate_statistics(files)

        # Then
        assert stats['file_count'] == 0
        assert stats['total_additions'] == 0
        assert stats['total_deletions'] == 0
        assert stats['total_changes'] == 0
        assert stats['avg_changes_per_file'] == 0

    def test_calculate_statistics_正常系_1ファイル(self, statistics):
        """
        Given: 1つのファイル変更のみのリスト
        When: calculate_statistics()を呼び出す
        Then: 統計情報が正しく計算される
        """
        # Given
        files = [
            FileChange(
                filename="single.py",
                status="modified",
                additions=100,
                deletions=50,
                changes=150,
                patch="content"
            )
        ]

        # When
        stats = statistics.calculate_statistics(files)

        # Then
        assert stats['file_count'] == 1
        assert stats['total_additions'] == 100
        assert stats['total_deletions'] == 50
        assert stats['total_changes'] == 150
        assert stats['avg_changes_per_file'] == 150

    def test_calculate_optimal_chunk_size_正常系_大きなトークン制限(self, statistics, sample_files):
        """
        Given: 大きなmax_tokensが設定されている場合
        When: calculate_optimal_chunk_size()を呼び出す
        Then: 全ファイルを含むチャンクサイズが返される
        """
        # Given
        max_tokens = 100000  # 非常に大きな値

        # When
        chunk_size = statistics.calculate_optimal_chunk_size(sample_files, max_tokens)

        # Then
        # 全ファイルが1チャンクに収まる
        assert chunk_size == len(sample_files)

    def test_calculate_optimal_chunk_size_正常系_小さなトークン制限(self, statistics, sample_files):
        """
        Given: 小さなmax_tokensが設定されている場合
        When: calculate_optimal_chunk_size()を呼び出す
        Then: 最小チャンクサイズが返される
        """
        # Given
        max_tokens = 10  # 非常に小さな値

        # When
        chunk_size = statistics.calculate_optimal_chunk_size(sample_files, max_tokens)

        # Then
        # 最小チャンクサイズが保証される
        assert chunk_size >= PRCommentStatistics.DEFAULT_MIN_CHUNK_SIZE
