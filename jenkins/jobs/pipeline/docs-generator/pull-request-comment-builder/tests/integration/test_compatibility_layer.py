"""
統合テスト: 互換性レイヤー

テスト対象:
- Facadeパターンによる旧インポートパスのサポート
- 新旧インポートパスの動作同一性
"""

import pytest
import warnings


class TestCompatibilityLayer:
    """互換性レイヤーの統合テスト"""

    def test_旧インポートパスから新インポートパスへの移行(self):
        """
        Given: 旧インポートパスと新インポートパスの両方がある
        When: 同じクラスを使用する
        Then: 両方とも同じクラスを参照する
        """
        # 警告を無視
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            # 旧インポートパス
            from pr_comment_generator import PRInfo as PRInfo_old

            # 新インポートパス
            from pr_comment_generator.models import PRInfo as PRInfo_new

            # Then
            # 両方が同じクラスであることを確認
            assert PRInfo_old is PRInfo_new

    def test_旧インポートパスでの正常動作(self):
        """
        Given: 旧インポートパスを使用する既存コード
        When: そのコードを実行する
        Then: 正常に動作する
        """
        # 警告を無視
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            # When
            from pr_comment_generator import PRInfo, FileChange

            # PR情報を作成
            pr_info = PRInfo.from_json({
                "title": "Test PR",
                "number": 999,
                "body": "Test body",
                "user": {"login": "testuser"},
                "base": {"ref": "main", "sha": "abc"},
                "head": {"ref": "feature", "sha": "def"}
            })

            # ファイル変更を作成
            file_change = FileChange.from_json({
                "filename": "test.py",
                "status": "modified",
                "additions": 10,
                "deletions": 5,
                "changes": 15,
                "patch": "diff"
            })

            # Then
            # 正常に動作することを確認
            assert pr_info.title == "Test PR"
            assert pr_info.number == 999
            assert file_change.filename == "test.py"

    def test_新インポートパスでの正常動作(self):
        """
        Given: 新インポートパスを使用する新規コード
        When: そのコードを実行する
        Then: 正常に動作する
        """
        # When
        from pr_comment_generator.models import PRInfo, FileChange

        # PR情報を作成
        pr_info = PRInfo.from_json({
            "title": "New PR",
            "number": 1000,
            "body": "New body",
            "user": {"login": "newuser"},
            "base": {"ref": "develop", "sha": "xyz"},
            "head": {"ref": "feature/new", "sha": "uvw"}
        })

        # ファイル変更を作成
        file_change = FileChange.from_json({
            "filename": "new.py",
            "status": "added",
            "additions": 50,
            "deletions": 0,
            "changes": 50,
            "patch": None
        })

        # Then
        # 正常に動作することを確認
        assert pr_info.title == "New PR"
        assert pr_info.number == 1000
        assert file_change.filename == "new.py"

    def test_新旧インポートパスで同じ結果(self):
        """
        Given: 旧インポートパスと新インポートパスでそれぞれオブジェクトを作成
        When: 同じJSONデータから作成する
        Then: 同じ結果が得られる
        """
        # Given
        json_data = {
            "title": "Comparison Test",
            "number": 500,
            "body": "Comparison body",
            "user": {"login": "compuser"},
            "base": {"ref": "main", "sha": "aaa"},
            "head": {"ref": "feature/comp", "sha": "bbb"}
        }

        # When
        # 警告を無視して旧インポートパスを使用
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from pr_comment_generator import PRInfo as PRInfo_old
            pr_info_old = PRInfo_old.from_json(json_data)

        # 新インポートパスを使用
        from pr_comment_generator.models import PRInfo as PRInfo_new
        pr_info_new = PRInfo_new.from_json(json_data)

        # Then
        # 同じ結果が得られることを確認
        assert pr_info_old.title == pr_info_new.title
        assert pr_info_old.number == pr_info_new.number
        assert pr_info_old.body == pr_info_new.body
        assert pr_info_old.author == pr_info_new.author
        assert pr_info_old.base_branch == pr_info_new.base_branch

    def test_すべての公開クラスが旧インポートパスで利用可能(self):
        """
        Given: 旧インポートパスを使用する
        When: すべての公開クラスをインポートする
        Then: すべて利用可能である
        """
        # 警告を無視
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            # When
            from pr_comment_generator import (
                PRInfo,
                FileChange,
                PRCommentStatistics,
                CommentFormatter,
                PromptTemplateManager,
                TokenEstimator
            )

            # Then
            # すべてのクラスが利用可能であることを確認
            assert PRInfo is not None
            assert FileChange is not None
            assert PRCommentStatistics is not None
            assert CommentFormatter is not None
            assert PromptTemplateManager is not None
            assert TokenEstimator is not None

    def test_非推奨警告が適切に発生する(self):
        """
        Given: 旧インポートパスを使用する
        When: pr_comment_generatorをインポートする
        Then: 非推奨警告が発生する
        """
        # 警告をキャッチ
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # When
            # 新しくインポート（既にインポート済みの場合は警告が出ないため、importlibを使用）
            import importlib
            import sys

            # モジュールをリロードして警告を再度発生させる
            if 'pr_comment_generator' in sys.modules:
                importlib.reload(sys.modules['pr_comment_generator'])
            else:
                import pr_comment_generator

            # Then
            # 非推奨警告が発生していることを確認
            deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1

            # 警告メッセージに適切な情報が含まれることを確認
            message = str(deprecation_warnings[0].message)
            assert "非推奨" in message or "deprecated" in message.lower()
