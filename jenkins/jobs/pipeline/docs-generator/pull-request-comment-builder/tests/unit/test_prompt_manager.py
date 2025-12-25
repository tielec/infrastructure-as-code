"""
ユニットテスト: prompt_manager.py

テスト対象:
- PromptTemplateManager: プロンプトテンプレート管理機能
"""

import pytest
import os
import tempfile
from pr_comment_generator.prompt_manager import PromptTemplateManager


class TestPromptTemplateManager:
    """PromptTemplateManagerクラスのテスト"""

    @pytest.fixture
    def temp_template_dir(self):
        """一時的なテンプレートディレクトリを作成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # テストテンプレートファイルを作成
            base_template = os.path.join(tmpdir, "base_template.md")
            chunk_template = os.path.join(tmpdir, "chunk_analysis_extension.md")
            summary_template = os.path.join(tmpdir, "summary_extension.md")

            with open(base_template, "w", encoding="utf-8") as f:
                f.write("Base prompt for PR #{pr_number} by {author}")

            with open(chunk_template, "w", encoding="utf-8") as f:
                f.write("Analyze chunk {chunk_index} with {file_count} files")

            with open(summary_template, "w", encoding="utf-8") as f:
                f.write("Generate summary from {analysis_count} analyses")

            yield tmpdir

    def test_初期化_正常系(self, temp_template_dir):
        """
        Given: テンプレートファイルが存在するディレクトリ
        When: PromptTemplateManagerを初期化する
        Then: テンプレートが正しく読み込まれる
        """
        # When
        manager = PromptTemplateManager(template_dir=temp_template_dir)

        # Then
        assert manager.templates['base'] != ""
        assert manager.templates['chunk'] != ""
        assert manager.templates['summary'] != ""

    def test_get_base_prompt_正常系(self, temp_template_dir):
        """
        Given: PromptTemplateManagerが初期化されている
        When: get_base_prompt()を呼び出す
        Then: ベースプロンプトが返される
        """
        # Given
        manager = PromptTemplateManager(template_dir=temp_template_dir)

        # When
        prompt = manager.get_base_prompt()

        # Then
        assert prompt == "Base prompt for PR #{pr_number} by {author}"

    def test_get_chunk_analysis_prompt_正常系(self, temp_template_dir):
        """
        Given: PromptTemplateManagerが初期化されている
        When: get_chunk_analysis_prompt()を呼び出す
        Then: チャンク分析プロンプトが返される
        """
        # Given
        manager = PromptTemplateManager(template_dir=temp_template_dir)

        # When
        prompt = manager.get_chunk_analysis_prompt()

        # Then
        assert prompt == (
            "Base prompt for PR #{pr_number} by {author}\n\n"
            "Analyze chunk {chunk_index} with {file_count} files"
        )

    def test_get_summary_prompt_正常系(self, temp_template_dir):
        """
        Given: PromptTemplateManagerが初期化されている
        When: get_summary_prompt()を呼び出す
        Then: サマリープロンプトが返される
        """
        # Given
        manager = PromptTemplateManager(template_dir=temp_template_dir)

        # When
        prompt = manager.get_summary_prompt()

        # Then
        assert prompt == (
            "Base prompt for PR #{pr_number} by {author}\n\n"
            "Generate summary from {analysis_count} analyses"
        )

    def test_format_prompt_正常系(self, temp_template_dir):
        """
        Given: PromptTemplateManagerが初期化されている
        When: format_prompt()でプレースホルダーを置換する
        Then: プロンプトが正しくフォーマットされる
        """
        # Given
        manager = PromptTemplateManager(template_dir=temp_template_dir)

        # When
        formatted = manager.format_prompt(
            "base",
            pr_number=123,
            author="testuser"
        )

        # Then
        assert formatted == "Base prompt for PR #123 by testuser"

    def test_format_prompt_異常系_キー欠損(self, temp_template_dir, capfd):
        """
        Given: PromptTemplateManagerが初期化されている
        When: format_prompt()で必要なキーが欠損している場合
        Then: 警告が出力され、元のテンプレートが返される
        """
        # Given
        manager = PromptTemplateManager(template_dir=temp_template_dir)

        # When
        formatted = manager.format_prompt("base")  # キーが欠損

        # Then
        # 警告が出力される
        captured = capfd.readouterr()
        assert "Warning: Missing format variable" in captured.out

        # 元のテンプレートが返される
        assert "{pr_number}" in formatted
        assert "{author}" in formatted

    def test_初期化_異常系_テンプレートファイル不在(self, capfd):
        """
        Given: テンプレートファイルが存在しないディレクトリ
        When: PromptTemplateManagerを初期化する
        Then: 警告が出力され、空のテンプレートが設定される
        """
        # Given
        with tempfile.TemporaryDirectory() as tmpdir:
            # When
            manager = PromptTemplateManager(template_dir=tmpdir)

            # Then
            captured = capfd.readouterr()
            assert "Warning: Template file" in captured.out

            # 空のテンプレートが設定される
            assert manager.templates['base'] == ""
            assert manager.templates['chunk'] == ""
            assert manager.templates['summary'] == ""

    def test_format_prompt_正常系_複数のプレースホルダー(self, temp_template_dir):
        """
        Given: PromptTemplateManagerが初期化されている
        When: format_prompt()で複数のプレースホルダーを置換する
        Then: すべてのプレースホルダーが正しく置換される
        """
        # Given
        manager = PromptTemplateManager(template_dir=temp_template_dir)

        # When
        formatted = manager.format_prompt(
            "chunk",
            chunk_index=2,
            file_count=5
        )

        # Then
        assert formatted == "Analyze chunk 2 with 5 files"

    def test_get_base_prompt_境界値_空のテンプレート(self):
        """
        Given: 空のテンプレートディレクトリ
        When: get_base_prompt()を呼び出す
        Then: 空文字列が返される
        """
        # Given
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PromptTemplateManager(template_dir=tmpdir)

            # When
            prompt = manager.get_base_prompt()

            # Then
            assert prompt == ""
