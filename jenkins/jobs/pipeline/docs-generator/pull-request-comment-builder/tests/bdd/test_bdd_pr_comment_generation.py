"""
BDDテスト: PRコメント生成機能

テスト対象:
- エンドユーザーのユースケース
- Given-When-Thenシナリオ
"""

import pytest
import json
import tempfile
import os
import logging
from pr_comment_generator.models import PRInfo, FileChange
from pr_comment_generator.statistics import PRCommentStatistics
from pr_comment_generator.formatter import CommentFormatter
from pr_comment_generator.token_estimator import TokenEstimator
from pr_comment_generator.prompt_manager import PromptTemplateManager


class TestPRCommentGenerationBDD:
    """PRコメント生成機能のBDDテスト"""

    @pytest.fixture
    def logger(self):
        """ロガーをフィクスチャとして提供"""
        return logging.getLogger("test_bdd")

    @pytest.fixture
    def temp_template_dir(self):
        """一時テンプレートディレクトリを作成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # テンプレートファイルを作成
            base_template = os.path.join(tmpdir, "base_template.md")
            with open(base_template, "w", encoding="utf-8") as f:
                f.write("以下のPRを分析してください：\n\nPR #{pr_number}: {title}\n著者: {author}\n")

            chunk_template = os.path.join(tmpdir, "chunk_analysis_extension.md")
            with open(chunk_template, "w", encoding="utf-8") as f:
                f.write("チャンク {chunk_index} の分析を行ってください。")

            summary_template = os.path.join(tmpdir, "summary_extension.md")
            with open(summary_template, "w", encoding="utf-8") as f:
                f.write("以下の分析からサマリーを生成してください。")

            yield tmpdir

    def test_scenario_小規模PRのコメント生成(self, logger, temp_template_dir):
        """
        Scenario: 小規模PRのコメント生成

        Given: ユーザーがPR情報JSONファイルを用意している
          And: PR情報には以下が含まれる:
               - number: 123
               - title: "Add new feature"
               - author: "testuser"
          And: 変更ファイルは3個で、合計100行の変更である
        When: ユーザーがPRコメント生成処理を実行する
        Then: 最終的なコメントが生成される
          And: コメントに"# 変更内容サマリー"ヘッダーが含まれる
          And: コメントにファイルリストが含まれる
        """
        # Given: PR情報を準備
        pr_info = PRInfo.from_json({
            "title": "Add new feature",
            "number": 123,
            "body": "This PR adds a new feature to the system",
            "user": {"login": "testuser"},
            "base": {"ref": "main", "sha": "abc123"},
            "head": {"ref": "feature-branch", "sha": "def456"}
        })

        # And: 変更ファイルを準備（3個、合計100行）
        files = [
            FileChange(
                filename="src/main.py",
                status="modified",
                additions=20,
                deletions=10,
                changes=30,
                patch="@@ -1,10 +1,20 @@\n# Changes here"
            ),
            FileChange(
                filename="src/utils.py",
                status="added",
                additions=50,
                deletions=0,
                changes=50,
                patch="@@ -0,0 +1,50 @@\n# New file"
            ),
            FileChange(
                filename="README.md",
                status="modified",
                additions=15,
                deletions=5,
                changes=20,
                patch="@@ -1,5 +1,15 @@\n# Documentation updates"
            )
        ]

        # モジュールを準備
        token_estimator = TokenEstimator(logger=logger)
        statistics = PRCommentStatistics(token_estimator=token_estimator, logger=logger)
        formatter = CommentFormatter(logger=logger)
        prompt_manager = PromptTemplateManager(template_dir=temp_template_dir)

        # When: コメント生成処理を実行
        # Step 1: チャンクサイズを計算
        chunk_size = statistics.calculate_optimal_chunk_size(files, max_tokens=3000)

        # Step 2: ファイルをチャンクに分割
        chunks = [files[i:i + chunk_size] for i in range(0, len(files), chunk_size)]

        # Step 3: 統計情報を計算
        stats = statistics.calculate_statistics(files)

        # Step 4: チャンク分析（ダミー）
        chunk_analyses = [
            f"チャンク {i+1}: {len(chunk)} 個のファイルを分析しました。"
            for i, chunk in enumerate(chunks)
        ]

        # Step 5: サマリーを作成（ダミー）
        summary = f"このPRは {pr_info.title} を実装しています。{stats['file_count']} 個のファイルが変更され、合計 {stats['total_changes']} 行の変更があります。"

        # Step 6: 最終コメントをフォーマット
        comment = formatter.format_final_comment(summary, chunk_analyses, files)

        # Then: コメントが生成される
        assert comment is not None
        assert len(comment) > 0

        # And: "# 変更内容サマリー"ヘッダーが含まれる
        assert "# 変更内容サマリー" in comment

        # And: サマリーが含まれる
        assert summary in comment

        # And: ファイルリストが含まれる
        assert "## 変更されたファイル" in comment
        assert "src/main.py" in comment
        assert "src/utils.py" in comment
        assert "README.md" in comment

        # And: 変更行数が含まれる
        assert "+20" in comment
        assert "+50" in comment

    def test_scenario_大規模PRのコメント生成_チャンク分割(self, logger, temp_template_dir):
        """
        Scenario: 大規模PRのコメント生成（チャンク分割）

        Given: ユーザーがPR情報JSONファイルを用意している
          And: PR情報には以下が含まれる:
               - number: 456
               - title: "Major refactoring"
               - author: "developer"
          And: 変更ファイルは50個で、合計5000行の変更である
          And: 一部のファイルは1000行を超える変更がある
        When: ユーザーがPRコメント生成処理を実行する
        Then: ファイルが複数のチャンクに分割される
          And: 各チャンクが個別に分析される
          And: スキップされたファイルの情報がコメントに含まれる
        """
        # Given: PR情報を準備
        pr_info = PRInfo.from_json({
            "title": "Major refactoring",
            "number": 456,
            "body": "This PR refactors the entire codebase",
            "user": {"login": "developer"},
            "base": {"ref": "develop", "sha": "xyz789"},
            "head": {"ref": "refactor-branch", "sha": "uvw012"}
        })

        # And: 大量のファイル変更を準備（50個）
        files = []
        for i in range(50):
            changes = 100  # 各ファイル100行変更
            files.append(
                FileChange(
                    filename=f"src/module{i}.py",
                    status="modified",
                    additions=50,
                    deletions=50,
                    changes=changes,
                    patch="@@ -1,50 +1,50 @@\n# Refactored code" * 5
                )
            )

        # And: 1000行を超える大きなファイルを追加
        large_file = FileChange(
            filename="src/large_module.py",
            status="modified",
            additions=800,
            deletions=800,
            changes=1600,
            patch="@@ -1,800 +1,800 @@\n# Large refactoring"
        )

        # モジュールを準備
        token_estimator = TokenEstimator(logger=logger)
        statistics = PRCommentStatistics(token_estimator=token_estimator, logger=logger)
        formatter = CommentFormatter(logger=logger)

        # When: コメント生成処理を実行
        # Step 1: 大きすぎるファイルをスキップ
        processed_files = []
        skipped_files = []
        for file in files + [large_file]:
            if file.changes > 1000:
                skipped_files.append(file)
            else:
                processed_files.append(file)

        # Step 2: チャンクサイズを計算
        chunk_size = statistics.calculate_optimal_chunk_size(processed_files, max_tokens=3000)

        # Step 3: ファイルをチャンクに分割
        chunks = [processed_files[i:i + chunk_size] for i in range(0, len(processed_files), chunk_size)]

        # Then: ファイルが複数のチャンクに分割される
        assert len(chunks) > 1

        # Step 4: 各チャンクを分析（ダミー）
        chunk_analyses = [
            f"チャンク {i+1}: {len(chunk)} 個のファイルを分析しました。"
            for i, chunk in enumerate(chunks)
        ]

        # And: 各チャンクが個別に分析される
        assert len(chunk_analyses) == len(chunks)

        # Step 5: サマリーを作成
        stats = statistics.calculate_statistics(processed_files)
        summary = f"大規模なリファクタリングPRです。{stats['file_count']} 個のファイルが処理されました。"

        # Step 6: 最終コメントをフォーマット
        comment = formatter.format_final_comment(summary, chunk_analyses, processed_files, skipped_files)

        # And: スキップされたファイルの情報がコメントに含まれる
        assert "⚠️ スキップされたファイル" in comment
        assert "src/large_module.py" in comment
        assert len(skipped_files) > 0

    def test_scenario_互換性レイヤーを使用したPRコメント生成(self, logger, temp_template_dir):
        """
        Scenario: 旧インポートパスでのPRコメント生成

        Given: 既存のスクリプトが旧インポートパスを使用している
        When: 既存のスクリプトを実行する
        Then: スクリプトが正常に動作する
          And: 非推奨警告が表示される
          And: PRコメントが正しく生成される
        """
        import warnings
        import importlib
        import pr_comment_generator

        # 警告をキャッチ
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Given: 旧インポートパスを使用（再読み込みで非推奨警告を確実に捕捉）
            importlib.reload(pr_comment_generator)
            from pr_comment_generator import PRInfo, FileChange, CommentFormatter

            # PR情報を作成
            pr_info = PRInfo.from_json({
                "title": "Legacy PR",
                "number": 999,
                "body": "Using legacy import path",
                "user": {"login": "legacyuser"},
                "base": {"ref": "main", "sha": "aaa"},
                "head": {"ref": "legacy", "sha": "bbb"}
            })

            files = [
                FileChange.from_json({
                    "filename": "legacy.py",
                    "status": "modified",
                    "additions": 10,
                    "deletions": 5,
                    "changes": 15,
                    "patch": "diff"
                })
            ]

            # When: コメント生成処理を実行
            formatter = CommentFormatter(logger=logger)
            comment = formatter.format_final_comment(
                summary="Legacy PR summary",
                chunk_analyses=["Legacy analysis"],
                files=files
            )

            # Then: スクリプトが正常に動作する
            assert comment is not None
            assert "# 変更内容サマリー" in comment
            assert "legacy.py" in comment

            # And: 非推奨警告が表示される
            deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1

    def test_scenario_エンドツーエンド_統計からフォーマットまで(self, logger, temp_template_dir):
        """
        Scenario: エンドツーエンドのPRコメント生成フロー

        Given: ユーザーがPR情報とファイル変更データを用意している
        When: 統計計算→チャンク分割→分析→フォーマットの全ステップを実行する
        Then: 最終的な完全なPRコメントが生成される
          And: コメントにすべての必要な情報が含まれる
        """
        # Given: データを準備
        pr_info = PRInfo.from_json({
            "title": "Comprehensive Feature Implementation",
            "number": 777,
            "body": "This PR implements a comprehensive feature with tests and documentation",
            "user": {"login": "fullstackdev"},
            "base": {"ref": "main", "sha": "base123"},
            "head": {"ref": "feature/comprehensive", "sha": "head456"}
        })

        files = [
            FileChange(filename="src/feature.py", status="added", additions=200, deletions=0, changes=200, patch="new feature"),
            FileChange(filename="src/helper.py", status="modified", additions=50, deletions=20, changes=70, patch="helper updates"),
            FileChange(filename="tests/test_feature.py", status="added", additions=150, deletions=0, changes=150, patch="new tests"),
            FileChange(filename="docs/feature.md", status="added", additions=100, deletions=0, changes=100, patch="documentation"),
            FileChange(filename="README.md", status="modified", additions=20, deletions=5, changes=25, patch="readme updates"),
        ]

        # モジュールを準備
        token_estimator = TokenEstimator(logger=logger)
        statistics = PRCommentStatistics(token_estimator=token_estimator, logger=logger)
        formatter = CommentFormatter(logger=logger)

        # When: 全ステップを実行
        # Step 1: 統計計算
        stats = statistics.calculate_statistics(files)

        # Step 2: チャンクサイズ計算と分割
        chunk_size = statistics.calculate_optimal_chunk_size(files, max_tokens=3000)
        chunks = [files[i:i + chunk_size] for i in range(0, len(files), chunk_size)]

        # Step 3: チャンク分析（ダミー）
        chunk_analyses = []
        for i, chunk in enumerate(chunks):
            analysis = f"チャンク {i+1} の分析:\n"
            for file in chunk:
                analysis += f"  - {file.filename}: {file.status} (+{file.additions} -{file.deletions})\n"
            chunk_analyses.append(analysis)

        # Step 4: サマリー作成
        summary = (
            f"このPRは {pr_info.title} を実装しています。\n\n"
            f"**統計情報:**\n"
            f"- ファイル数: {stats['file_count']}\n"
            f"- 追加行数: {stats['total_additions']}\n"
            f"- 削除行数: {stats['total_deletions']}\n"
            f"- 合計変更行数: {stats['total_changes']}\n"
        )

        # Step 5: 最終コメントをフォーマット
        comment = formatter.format_final_comment(summary, chunk_analyses, files)

        # Then: 完全なコメントが生成される
        assert comment is not None
        assert len(comment) > 0

        # And: すべての必要な情報が含まれる
        # ヘッダー
        assert "# 変更内容サマリー" in comment

        # サマリー情報
        assert pr_info.title in comment
        assert "統計情報" in comment
        assert str(stats['file_count']) in comment
        assert str(stats['total_additions']) in comment

        # チャンク分析
        for i in range(len(chunks)):
            assert f"チャンク {i+1}" in comment

        # ファイルリスト
        assert "## 変更されたファイル" in comment
        for file in files:
            assert file.filename in comment

        # 絵文字
        assert "✨" in comment  # added files
        assert "📝" in comment  # modified files
