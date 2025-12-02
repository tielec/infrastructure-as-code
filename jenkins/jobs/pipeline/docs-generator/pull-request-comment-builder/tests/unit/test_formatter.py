"""
ユニットテスト: formatter.py

テスト対象:
- CommentFormatter: コメントフォーマット処理機能
"""

import pytest
import logging
from pr_comment_generator.formatter import CommentFormatter
from pr_comment_generator.models import FileChange


class TestCommentFormatter:
    """CommentFormatterクラスのテスト"""

    @pytest.fixture
    def formatter(self):
        """CommentFormatterインスタンスをフィクスチャとして提供"""
        logger = logging.getLogger("test")
        return CommentFormatter(logger=logger)

    def test_clean_markdown_format_正常系(self, formatter):
        """
        Given: 余分な空行を含むMarkdownテキスト
        When: clean_markdown_format()を呼び出す
        Then: Markdownが正しくクリーンアップされる
        """
        # Given
        text = """# Title


Some text


```code```


"""

        # When
        cleaned = formatter.clean_markdown_format(text)

        # Then
        # 3行以上の空行が2行に削減される
        assert "\n\n\n" not in cleaned
        # 末尾の空白が削除される
        assert not cleaned.endswith(" ")

    def test_clean_markdown_format_正常系_コードブロック(self, formatter):
        """
        Given: コードブロック前後に余分な空行があるMarkdown
        When: clean_markdown_format()を呼び出す
        Then: コードブロック前後の空行が調整される
        """
        # Given
        text = """
Some text


```python
code here
```


More text
"""

        # When
        cleaned = formatter.clean_markdown_format(text)

        # Then
        # コードブロック前後の余分な空行が削除される
        assert "\n\n```" not in cleaned
        assert "```\n\n\n" not in cleaned

    def test_format_chunk_analyses_正常系(self, formatter):
        """
        Given: チャンク分析結果のリスト
        When: format_chunk_analyses()を呼び出す
        Then: 正しくフォーマットされた分析結果が返される
        """
        # Given
        analyses = [
            "Analysis of chunk 1",
            "Analysis of chunk 2"
        ]

        # When
        formatted = formatter.format_chunk_analyses(analyses)

        # Then
        assert "## チャンク 1 の分析" in formatted
        assert "## チャンク 2 の分析" in formatted
        assert "Analysis of chunk 1" in formatted
        assert "Analysis of chunk 2" in formatted

    def test_format_chunk_analyses_境界値_空リスト(self, formatter):
        """
        Given: 空の分析結果リスト
        When: format_chunk_analyses()を呼び出す
        Then: 空文字列が返される
        """
        # Given
        analyses = []

        # When
        formatted = formatter.format_chunk_analyses(analyses)

        # Then
        assert formatted == ""

    def test_format_chunk_analyses_正常系_1チャンク(self, formatter):
        """
        Given: 1つのチャンク分析結果
        When: format_chunk_analyses()を呼び出す
        Then: 正しくフォーマットされる
        """
        # Given
        analyses = ["Single chunk analysis"]

        # When
        formatted = formatter.format_chunk_analyses(analyses)

        # Then
        assert "## チャンク 1 の分析" in formatted
        assert "Single chunk analysis" in formatted

    def test_format_file_list_正常系(self, formatter):
        """
        Given: ファイル変更リスト
        When: format_file_list()を呼び出す
        Then: 正しくフォーマットされたファイルリストが返される
        """
        # Given
        files = [
            FileChange(
                filename="src/main.py",
                status="modified",
                additions=10,
                deletions=5,
                changes=15,
                patch=None
            ),
            FileChange(
                filename="src/utils.py",
                status="added",
                additions=50,
                deletions=0,
                changes=50,
                patch=None
            )
        ]

        # When
        formatted = formatter.format_file_list(files)

        # Then
        assert "## 変更されたファイル" in formatted
        assert "📝 `src/main.py` (+10 -5)" in formatted
        assert "✨ `src/utils.py` (+50 -0)" in formatted

    def test_format_file_list_境界値_空リスト(self, formatter):
        """
        Given: 空のファイルリスト
        When: format_file_list()を呼び出す
        Then: メッセージが返される
        """
        # Given
        files = []

        # When
        formatted = formatter.format_file_list(files)

        # Then
        assert "変更されたファイルはありません" in formatted

    def test_format_file_list_正常系_様々なステータス(self, formatter):
        """
        Given: 様々なステータスのファイルリスト
        When: format_file_list()を呼び出す
        Then: 各ステータスに応じた絵文字が表示される
        """
        # Given
        files = [
            FileChange(filename="added.py", status="added", additions=10, deletions=0, changes=10, patch=None),
            FileChange(filename="modified.py", status="modified", additions=5, deletions=3, changes=8, patch=None),
            FileChange(filename="removed.py", status="removed", additions=0, deletions=20, changes=20, patch=None),
            FileChange(filename="renamed.py", status="renamed", additions=0, deletions=0, changes=0, patch=None),
        ]

        # When
        formatted = formatter.format_file_list(files)

        # Then
        assert "✨" in formatted  # added
        assert "📝" in formatted  # modified
        assert "🗑️" in formatted  # removed
        assert "📛" in formatted  # renamed

    def test_format_skipped_files_info_正常系(self, formatter):
        """
        Given: スキップされたファイルリスト
        When: format_skipped_files_info()を呼び出す
        Then: 正しくフォーマットされた情報が返される
        """
        # Given
        skipped_files = [
            FileChange(filename="large_file.txt", status="modified", additions=0, deletions=0, changes=2000, patch=None),
            FileChange(filename="another_large.txt", status="modified", additions=0, deletions=0, changes=1500, patch=None)
        ]
        reason = "サイズ制限"

        # When
        formatted = formatter.format_skipped_files_info(skipped_files, reason)

        # Then
        assert "## ⚠️ スキップされたファイル (サイズ制限)" in formatted
        assert "`large_file.txt`" in formatted
        assert "`another_large.txt`" in formatted

    def test_format_skipped_files_info_境界値_空リスト(self, formatter):
        """
        Given: 空のスキップファイルリスト
        When: format_skipped_files_info()を呼び出す
        Then: 空文字列が返される
        """
        # Given
        skipped_files = []

        # When
        formatted = formatter.format_skipped_files_info(skipped_files)

        # Then
        assert formatted == ""

    def test_format_final_comment_正常系(self, formatter):
        """
        Given: サマリー、チャンク分析、ファイルリスト
        When: format_final_comment()を呼び出す
        Then: 最終コメントが正しくフォーマットされる
        """
        # Given
        summary = "This PR adds a new feature."
        chunk_analyses = ["Analysis 1", "Analysis 2"]
        files = [
            FileChange(filename="src/main.py", status="modified", additions=10, deletions=5, changes=15, patch=None)
        ]

        # When
        comment = formatter.format_final_comment(summary, chunk_analyses, files)

        # Then
        assert "# 変更内容サマリー" in comment
        assert summary in comment
        assert "## チャンク 1 の分析" in comment
        assert "## 変更されたファイル" in comment

    def test_format_final_comment_正常系_スキップファイルあり(self, formatter):
        """
        Given: スキップファイルを含むデータ
        When: format_final_comment()を呼び出す
        Then: スキップファイル情報が含まれる
        """
        # Given
        summary = "Test summary"
        chunk_analyses = ["Analysis"]
        files = [FileChange(filename="test.py", status="modified", additions=1, deletions=0, changes=1, patch=None)]
        skipped_files = [FileChange(filename="large.txt", status="modified", additions=0, deletions=0, changes=2000, patch=None)]

        # When
        comment = formatter.format_final_comment(summary, chunk_analyses, files, skipped_files)

        # Then
        assert "⚠️ スキップされたファイル" in comment

    def test_clean_markdown_format_正常系_末尾空白削除(self, formatter):
        """
        Given: 各行の末尾に空白があるMarkdown
        When: clean_markdown_format()を呼び出す
        Then: 末尾の空白が削除される
        """
        # Given
        text = "Line 1   \nLine 2  \nLine 3   "

        # When
        cleaned = formatter.clean_markdown_format(text)

        # Then
        lines = cleaned.split('\n')
        for line in lines:
            assert not line.endswith(' ')
