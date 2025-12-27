# jenkins/jobs/pipeline/docs-generator/pull-request-comment-builder/src/pr_comment_generator/token_estimator.py
"""
トークン推定ユーティリティ

このモジュールは、テキストのトークン数を推定し、
トークン制限に基づいてテキストを切り詰める機能を提供します。

主要なクラス:
- TokenEstimator: トークン数の推定とテキストの切り詰め機能
"""

import logging


class TokenEstimator:
    """トークン数を推定するクラス"""

    # トークン推定の定数
    AVERAGE_TOKEN_PER_CHAR_JA = 0.6  # 日本語の平均トークン/文字比率
    AVERAGE_TOKEN_PER_CHAR_EN = 0.25  # 英語の平均トークン/文字比率

    def __init__(self, logger: logging.Logger = None):
        """初期化

        Args:
            logger: ロガーインスタンス（省略時は新規作成）
        """
        self.logger = logger or logging.getLogger(__name__)

    def estimate_tokens(self, text: str) -> int:
        """テキストのトークン数を推定する

        英語と日本語の混在テキストに対応し、
        日本語が50%以上の場合はより高いレートで推定します。

        Args:
            text: トークン数を推定するテキスト

        Returns:
            int: 推定トークン数
        """
        if text is None:
            raise TypeError("text must not be None")

        if not text:
            return 0

        # 日本語文字の割合を計算
        ja_chars = sum(1 for c in text if ord(c) > 0x3000)
        en_chars = len(text) - ja_chars

        # トークン数を推定
        estimated_tokens = int(
            ja_chars * self.AVERAGE_TOKEN_PER_CHAR_JA +
            en_chars * self.AVERAGE_TOKEN_PER_CHAR_EN
        )

        return estimated_tokens

    def truncate_text(self, text: str, max_tokens: int) -> str:
        """テキストを指定されたトークン数以下に切り詰める

        バイナリサーチを使用して、指定されたトークン数以下に
        収まる最大の長さを効率的に見つけます。

        Args:
            text: 切り詰めるテキスト
            max_tokens: 最大トークン数

        Returns:
            str: 切り詰められたテキスト
        """
        if max_tokens <= 0:
            return ""

        if self.estimate_tokens(text) <= max_tokens:
            return text

        # バイナリサーチで適切な長さを見つける
        left, right = 0, len(text)
        while left < right:
            mid = (left + right + 1) // 2
            if self.estimate_tokens(text[:mid]) <= max_tokens:
                left = mid
            else:
                right = mid - 1

        truncated = text[:left]
        self.logger.warning(
            f"Text truncated from {len(text)} to {len(truncated)} chars "
            f"to fit within {max_tokens} tokens"
        )
        return truncated
