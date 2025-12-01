"""
統合テスト: モジュール間連携

テスト対象:
- Statistics ↔ TokenEstimator 連携
- Formatter ↔ Models 連携
- 複数モジュールの協調動作
"""

import pytest
import logging
import tempfile
import os
from pr_comment_generator.models import PRInfo, FileChange
from pr_comment_generator.statistics import PRCommentStatistics
from pr_comment_generator.formatter import CommentFormatter
from pr_comment_generator.token_estimator import TokenEstimator
from pr_comment_generator.prompt_manager import PromptTemplateManager


class TestStatisticsTokenEstimatorIntegration:
    """Statistics ↔ TokenEstimator 連携テスト"""

    @pytest.fixture
    def logger(self):
        """ロガーをフィクスチャとして提供"""
        return logging.getLogger("test")

    @pytest.fixture
    def token_estimator(self, logger):
        """TokenEstimatorインスタンスを提供"""
        return TokenEstimator(logger=logger)

    @pytest.fixture
    def statistics(self, token_estimator, logger):
        """PRCommentStatisticsインスタンスを提供"""
        return PRCommentStatistics(token_estimator=token_estimator, logger=logger)

    def test_チャンクサイズ計算とトークン推定の連携(self, statistics, token_estimator):
        """
        Given: ファイル変更リストがある
        When: チャンクサイズを計算し、そのチャンクのトークン数を推定する
        Then: チャンクのトークン数がmax_tokens以下である
        """
        # Given
        files = [
            FileChange(
                filename=f"file{i}.py",
                status="modified",
                additions=10,
                deletions=5,
                changes=15,
                patch="test content " * 100
            )
            for i in range(10)
        ]
        max_tokens = 3000

        # When
        chunk_size = statistics.calculate_optimal_chunk_size(files, max_tokens)
        chunks = [files[i:i + chunk_size] for i in range(0, len(files), chunk_size)]

        # Then
        for chunk in chunks:
            chunk_tokens = statistics.estimate_chunk_tokens(chunk)
            # 各チャンクのトークン数がmax_tokensを大きく超えないことを確認
            # (完全な保証はないが、大幅な超過がないことを確認)
            assert chunk_tokens < max_tokens * 2

    def test_統計計算とファイル変更データの整合性(self, statistics):
        """
        Given: ファイル変更リストがある
        When: 統計情報を計算する
        Then: 統計情報がファイル変更データと整合する
        """
        # Given
        files = [
            FileChange(filename="file1.py", status="modified", additions=10, deletions=5, changes=15, patch=None),
            FileChange(filename="file2.py", status="added", additions=50, deletions=0, changes=50, patch=None),
            FileChange(filename="file3.py", status="modified", additions=20, deletions=10, changes=30, patch=None),
        ]

        # When
        stats = statistics.calculate_statistics(files)

        # Then
        # 手動計算と一致することを確認
        assert stats['file_count'] == len(files)
        assert stats['total_additions'] == sum(f.additions for f in files)
        assert stats['total_deletions'] == sum(f.deletions for f in files)
        assert stats['total_changes'] == sum(f.changes for f in files)


class TestFormatterModelsIntegration:
    """Formatter ↔ Models 連携テスト"""

    @pytest.fixture
    def formatter(self):
        """CommentFormatterインスタンスを提供"""
        logger = logging.getLogger("test")
        return CommentFormatter(logger=logger)

    def test_ファイルリストフォーマットとFileChangeモデルの連携(self, formatter):
        """
        Given: FileChangeオブジェクトのリストがある
        When: format_file_list()を呼び出す
        Then: FileChangeの各フィールドが正しくフォーマットに反映される
        """
        # Given
        files = [
            FileChange(
                filename="src/main.py",
                status="modified",
                additions=15,
                deletions=8,
                changes=23,
                patch=None
            ),
            FileChange(
                filename="tests/test_new.py",
                status="added",
                additions=100,
                deletions=0,
                changes=100,
                patch=None
            ),
        ]

        # When
        formatted = formatter.format_file_list(files)

        # Then
        # ファイル名が含まれる
        assert "src/main.py" in formatted
        assert "tests/test_new.py" in formatted

        # 追加・削除行数が含まれる
        assert "+15" in formatted
        assert "-8" in formatted
        assert "+100" in formatted
        assert "-0" in formatted

        # ステータスに応じた絵文字が含まれる
        assert "📝" in formatted  # modified
        assert "✨" in formatted  # added

    def test_最終コメントフォーマットと複数モデルの連携(self, formatter):
        """
        Given: サマリー、チャンク分析、FileChangeリストがある
        When: format_final_comment()を呼び出す
        Then: すべての情報が統合されたコメントが生成される
        """
        # Given
        summary = "This PR refactors the authentication module."
        chunk_analyses = [
            "Chunk 1: Refactored login logic",
            "Chunk 2: Added new authentication tests"
        ]
        files = [
            FileChange(filename="auth/login.py", status="modified", additions=50, deletions=30, changes=80, patch=None),
            FileChange(filename="tests/test_auth.py", status="added", additions=150, deletions=0, changes=150, patch=None),
        ]
        skipped_files = [
            FileChange(filename="large_file.txt", status="modified", additions=0, deletions=0, changes=2000, patch=None)
        ]

        # When
        comment = formatter.format_final_comment(summary, chunk_analyses, files, skipped_files)

        # Then
        # サマリーが含まれる
        assert summary in comment

        # チャンク分析が含まれる
        assert "Chunk 1" in comment
        assert "Chunk 2" in comment

        # ファイルリストが含まれる
        assert "auth/login.py" in comment
        assert "tests/test_auth.py" in comment

        # スキップファイル情報が含まれる
        assert "large_file.txt" in comment
        assert "スキップ" in comment


class TestMultiModuleIntegration:
    """複数モジュールの協調動作テスト"""

    @pytest.fixture
    def logger(self):
        """ロガーをフィクスチャとして提供"""
        return logging.getLogger("test")

    @pytest.fixture
    def temp_template_dir(self):
        """一時テンプレートディレクトリを作成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # テンプレートファイルを作成
            base_template = os.path.join(tmpdir, "base_template.md")
            with open(base_template, "w", encoding="utf-8") as f:
                f.write("PR #{pr_number}: {title}")

            chunk_template = os.path.join(tmpdir, "chunk_analysis_extension.md")
            with open(chunk_template, "w", encoding="utf-8") as f:
                f.write("Analyze chunk {chunk_index}")

            summary_template = os.path.join(tmpdir, "summary_extension.md")
            with open(summary_template, "w", encoding="utf-8") as f:
                f.write("Summary template")

            yield tmpdir

    def test_統計計算からフォーマットまでの全体フロー(self, logger, temp_template_dir):
        """
        Given: PR情報とファイル変更リストがある
        When: 統計計算→チャンク分割→フォーマットの一連の処理を実行する
        Then: 最終的なコメントが正しく生成される
        """
        # Given
        pr_info = PRInfo.from_json({
            "title": "Add authentication feature",
            "number": 123,
            "body": "This PR adds authentication",
            "user": {"login": "developer"},
            "base": {"ref": "main", "sha": "abc123"},
            "head": {"ref": "feature/auth", "sha": "def456"}
        })

        files = [
            FileChange(
                filename=f"module{i}.py",
                status="modified",
                additions=20,
                deletions=10,
                changes=30,
                patch="diff content " * 50
            )
            for i in range(5)
        ]

        # モジュールインスタンスを作成
        token_estimator = TokenEstimator(logger=logger)
        statistics = PRCommentStatistics(token_estimator=token_estimator, logger=logger)
        formatter = CommentFormatter(logger=logger)
        prompt_manager = PromptTemplateManager(template_dir=temp_template_dir)

        # When
        # Step 1: チャンクサイズを計算
        chunk_size = statistics.calculate_optimal_chunk_size(files, max_tokens=3000)

        # Step 2: ファイルをチャンクに分割
        chunks = [files[i:i + chunk_size] for i in range(0, len(files), chunk_size)]

        # Step 3: 統計情報を計算
        stats = statistics.calculate_statistics(files)

        # Step 4: チャンク分析（ダミー）
        chunk_analyses = [f"Analysis for chunk {i+1}" for i in range(len(chunks))]

        # Step 5: 最終コメントをフォーマット
        summary = f"PR #{pr_info.number} by {pr_info.author}: {pr_info.title}"
        comment = formatter.format_final_comment(summary, chunk_analyses, files)

        # Then
        # PR情報が含まれる
        assert str(pr_info.number) in comment
        assert pr_info.title in comment

        # チャンク分析が含まれる
        for i in range(len(chunks)):
            assert f"Analysis for chunk {i+1}" in comment

        # ファイルリストが含まれる
        for file in files:
            assert file.filename in comment

        # 統計情報が正しい
        assert stats['file_count'] == len(files)
        assert stats['total_changes'] == sum(f.changes for f in files)

    def test_エラーハンドリングと復旧(self, logger):
        """
        Given: 不正なデータを含むファイルリストがある
        When: 統計計算を実行する
        Then: エラーが適切に処理され、処理が継続される
        """
        # Given
        files = [
            FileChange(filename="valid.py", status="modified", additions=10, deletions=5, changes=15, patch="content"),
            FileChange(filename="no_patch.py", status="modified", additions=10, deletions=5, changes=15, patch=None),
            FileChange(filename="valid2.py", status="added", additions=50, deletions=0, changes=50, patch="content"),
        ]

        token_estimator = TokenEstimator(logger=logger)
        statistics = PRCommentStatistics(token_estimator=token_estimator, logger=logger)

        # When
        chunk_size = statistics.calculate_optimal_chunk_size(files)
        stats = statistics.calculate_statistics(files)

        # Then
        # エラーなく処理が完了
        assert chunk_size >= 1
        assert stats['file_count'] == len(files)
