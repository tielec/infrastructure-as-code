"""
ユニットテスト: token_estimator.py

テスト対象:
- TokenEstimator: トークン数推定とテキスト切り詰め機能
"""

import pytest
import logging
from pr_comment_generator.token_estimator import TokenEstimator


class TestTokenEstimator:
    """TokenEstimatorクラスのテスト"""

    @pytest.fixture
    def estimator(self):
        """TokenEstimatorインスタンスをフィクスチャとして提供"""
        logger = logging.getLogger("test")
        return TokenEstimator(logger=logger)

    def test_estimate_tokens_正常系_英語テキスト(self, estimator):
        """
        Given: 英語テキストが与えられた場合
        When: estimate_tokens()を呼び出す
        Then: 正しいトークン数が推定される
        """
        # Given
        text = "Hello, this is a test."  # 23文字

        # When
        tokens = estimator.estimate_tokens(text)

        # Then
        # 英語は約0.25トークン/文字なので、23 * 0.25 = 5.75 ≒ 5トークン
        assert tokens >= 5
        assert tokens <= 6

    def test_estimate_tokens_正常系_日本語テキスト(self, estimator):
        """
        Given: 日本語テキストが与えられた場合
        When: estimate_tokens()を呼び出す
        Then: 正しいトークン数が推定される
        """
        # Given
        text = "これはテストです。"  # 9文字

        # When
        tokens = estimator.estimate_tokens(text)

        # Then
        # 日本語は約0.6トークン/文字なので、9 * 0.6 = 5.4 ≒ 5トークン
        assert tokens >= 5
        assert tokens <= 6

    def test_estimate_tokens_正常系_混在テキスト(self, estimator):
        """
        Given: 日本語と英語が混在したテキスト
        When: estimate_tokens()を呼び出す
        Then: 正しいトークン数が推定される
        """
        # Given
        text = "これはtest です。Hello world!"

        # When
        tokens = estimator.estimate_tokens(text)

        # Then
        # 日本語部分: "これはです。" (6文字) = 6 * 0.6 = 3.6
        # 英語部分: "test Hello world!" (17文字) = 17 * 0.25 = 4.25
        # 合計: 約8トークン
        assert tokens >= 7
        assert tokens <= 9

    def test_estimate_tokens_境界値_空文字列(self, estimator):
        """
        Given: 空文字列が与えられた場合
        When: estimate_tokens()を呼び出す
        Then: 0トークンが返される
        """
        # Given
        text = ""

        # When
        tokens = estimator.estimate_tokens(text)

        # Then
        assert tokens == 0

    def test_truncate_text_正常系(self, estimator):
        """
        Given: 長いテキストと最大トークン数が与えられた場合
        When: truncate_text()を呼び出す
        Then: テキストが指定されたトークン数以下に切り詰められる
        """
        # Given
        text = "This is a very long text that needs to be truncated." * 10
        max_tokens = 50

        # When
        truncated = estimator.truncate_text(text, max_tokens)

        # Then
        assert estimator.estimate_tokens(truncated) <= max_tokens
        assert len(truncated) < len(text)

    def test_truncate_text_境界値_トークン数以下(self, estimator):
        """
        Given: トークン数が既に制限以下のテキスト
        When: truncate_text()を呼び出す
        Then: テキストがそのまま返される
        """
        # Given
        text = "Short."
        max_tokens = 100

        # When
        truncated = estimator.truncate_text(text, max_tokens)

        # Then
        assert truncated == text

    def test_truncate_text_境界値_ちょうど最大トークン(self, estimator):
        """
        Given: ちょうど最大トークン数のテキスト
        When: truncate_text()を呼び出す
        Then: テキストがそのまま返される
        """
        # Given
        text = "Test text"
        estimated_tokens = estimator.estimate_tokens(text)
        max_tokens = estimated_tokens

        # When
        truncated = estimator.truncate_text(text, max_tokens)

        # Then
        assert truncated == text

    def test_estimate_tokens_正常系_記号を含むテキスト(self, estimator):
        """
        Given: 記号を含むテキストが与えられた場合
        When: estimate_tokens()を呼び出す
        Then: 正しいトークン数が推定される
        """
        # Given
        text = "Hello @user! Check #123 and visit https://example.com"

        # When
        tokens = estimator.estimate_tokens(text)

        # Then
        # 記号も英語として扱われる（ASCII文字）
        assert tokens > 0

    def test_truncate_text_正常系_日本語テキスト(self, estimator):
        """
        Given: 長い日本語テキストが与えられた場合
        When: truncate_text()を呼び出す
        Then: テキストが適切に切り詰められる
        """
        # Given
        text = "これは非常に長いテキストで、切り詰める必要があります。" * 10
        max_tokens = 30

        # When
        truncated = estimator.truncate_text(text, max_tokens)

        # Then
        assert estimator.estimate_tokens(truncated) <= max_tokens
        assert len(truncated) < len(text)

    def test_estimator_初期化_ロガー共有(self):
        """
        Given: Loggerを渡す
        When: TokenEstimatorを初期化する
        Then: 同じLoggerインスタンスが利用される
        """
        logger = logging.getLogger("shared")
        estimator = TokenEstimator(logger=logger)

        assert estimator.logger is logger

    def test_estimate_tokens_異常系_None値(self, estimator):
        """
        Given: Noneが渡された場合
        When: estimate_tokens()を呼び出す
        Then: TypeErrorが発生することで入力値の検証が担保される
        """
        with pytest.raises(TypeError):
            estimator.estimate_tokens(None)

    def test_estimate_tokens_境界値_超大テキスト(self, estimator):
        """
        Given: 非常に長いテキスト（100KB以上）
        When: estimate_tokens()を呼び出す
        Then: メモリエラーなく正のトークン数が返される
        """
        long_text = "A" * 100_000
        tokens = estimator.estimate_tokens(long_text)

        assert isinstance(tokens, int)
        assert tokens > 0

    def test_estimate_tokens_正常系_絵文字混在(self, estimator):
        """
        Given: 絵文字や特殊文字を含むテキスト
        When: estimate_tokens()を呼び出す
        Then: エラーなく正のトークン数が算出される
        """
        text = "Hello 👋 World 🌍 Test 🧪"
        tokens = estimator.estimate_tokens(text)

        assert tokens >= 1

    def test_truncate_text_正常系_UTF8文字列(self, estimator):
        """
        Given: UTF-8文字列（絵文字含む）と最大トークン数
        When: truncate_text()を呼び出す
        Then: トークン数が制限内に収まり、絵文字が保持される
        """
        text = "こんにちは 🌍 " * 100
        max_tokens = 10

        truncated = estimator.truncate_text(text, max_tokens)

        assert estimator.estimate_tokens(truncated) <= max_tokens
        assert "🌍" in truncated
        assert len(truncated) < len(text)

    def test_truncate_text_異常系_負のトークン数(self, estimator):
        """
        Given: 負のトークン数
        When: truncate_text()を呼び出す
        Then: 文字列が空になり、トークン数が0であることが保証される
        """
        truncated = estimator.truncate_text("Test text", -5)

        assert truncated == ""
        assert estimator.estimate_tokens(truncated) == 0

    def test_truncate_text_境界値_ゼロトークン(self, estimator):
        """
        Given: max_tokens=0
        When: truncate_text()を呼び出す
        Then: 空文字列が返ってくる
        """
        truncated = estimator.truncate_text("Test text", 0)

        assert truncated == ""
        assert estimator.estimate_tokens(truncated) == 0
