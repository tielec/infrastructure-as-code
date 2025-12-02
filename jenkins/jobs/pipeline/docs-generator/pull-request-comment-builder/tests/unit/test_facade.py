"""
ユニットテスト: __init__.py (Facade)

テスト対象:
- 互換性レイヤー（Facadeパターン）の動作確認
"""

import pytest
import warnings


class TestFacade:
    """Facade（互換性レイヤー）のテスト"""

    def test_非推奨警告_表示(self):
        """
        Given: 旧インポートパスを使用する
        When: pr_comment_generatorパッケージをインポートする
        Then: 非推奨警告が発生する
        """
        # 警告をキャッチする
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # When
            import pr_comment_generator

            # Then
            # 警告が発生していることを確認
            assert len(w) >= 1
            # 警告がDeprecationWarningであることを確認
            assert any(issubclass(warning.category, DeprecationWarning) for warning in w)
            # 警告メッセージに新しいインポートパスが含まれることを確認
            warning_messages = [str(warning.message) for warning in w]
            assert any("pr_comment_generator.generator" in msg for msg in warning_messages)

    def test_再エクスポート_正常動作(self):
        """
        Given: 旧インポートパスでクラスをインポートする
        When: インポートしたクラスを使用する
        Then: 正常に動作する
        """
        # 警告を無視
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            # When
            from pr_comment_generator import PRInfo, FileChange

            # Then
            # クラスが取得できることを確認
            assert PRInfo is not None
            assert FileChange is not None

            # インスタンス化が可能
            pr_info = PRInfo.from_json({
                "title": "Test",
                "number": 123,
                "body": "Test body",
                "user": {"login": "testuser"},
                "base": {"ref": "main", "sha": "abc"},
                "head": {"ref": "feature", "sha": "def"}
            })
            assert pr_info.title == "Test"

    def test_バージョン情報_提供(self):
        """
        Given: pr_comment_generatorパッケージがインポートされている
        When: __version__属性を参照する
        Then: バージョン情報が返される
        """
        # 警告を無視
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            # When
            import pr_comment_generator

            # Then
            assert hasattr(pr_comment_generator, '__version__')
            assert pr_comment_generator.__version__ is not None

    def test_公開API_すべて利用可能(self):
        """
        Given: pr_comment_generatorパッケージがインポートされている
        When: __all__に含まれる各クラスを参照する
        Then: すべてのクラスが利用可能である
        """
        # 警告を無視
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            # When
            import pr_comment_generator

            # Then
            # __all__に含まれるすべてのクラスが存在することを確認
            expected_classes = [
                'PRInfo',
                'FileChange',
                'PRCommentStatistics',
                'CommentFormatter',
                'PromptTemplateManager',
                'TokenEstimator'
            ]

            for class_name in expected_classes:
                assert hasattr(pr_comment_generator, class_name)
                assert getattr(pr_comment_generator, class_name) is not None

    def test_非推奨警告_メッセージ内容(self):
        """
        Given: 旧インポートパスを使用する
        When: pr_comment_generatorパッケージをインポートする
        Then: 警告メッセージに適切な情報が含まれる
        """
        # 警告をキャッチする
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # When
            import pr_comment_generator

            # Then
            # 警告メッセージを取得
            warning_messages = [str(warning.message) for warning in w if issubclass(warning.category, DeprecationWarning)]

            if warning_messages:
                message = warning_messages[0]
                # 警告メッセージに必要な情報が含まれることを確認
                assert "非推奨" in message or "deprecated" in message.lower()
                assert "pr_comment_generator.generator" in message or "pr_comment_generator.models" in message
