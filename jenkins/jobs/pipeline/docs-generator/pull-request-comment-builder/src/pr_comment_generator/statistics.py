# jenkins/jobs/pipeline/docs-generator/pull-request-comment-builder/src/pr_comment_generator/statistics.py
"""
統計処理モジュール

このモジュールは、PRコメント生成のための統計データの収集・計算機能を提供します。

主要なクラス:
- PRCommentStatistics: PR変更の統計計算とチャンクサイズの最適化
"""

import logging
from typing import List, Dict, Any

from .models import FileChange
from .token_estimator import TokenEstimator


class PRCommentStatistics:
    """PRコメント生成のための統計処理を行うクラス"""

    DEFAULT_MAX_CHUNK_TOKENS = 3000
    DEFAULT_MIN_CHUNK_SIZE = 1

    def __init__(self, token_estimator: TokenEstimator = None,
                 logger: logging.Logger = None):
        """初期化

        Args:
            token_estimator: トークン推定器
            logger: ロガーインスタンス
        """
        self.token_estimator = token_estimator or TokenEstimator()
        self.logger = logger or logging.getLogger(__name__)

    def calculate_optimal_chunk_size(
        self,
        files: List[FileChange],
        max_tokens: int = DEFAULT_MAX_CHUNK_TOKENS
    ) -> int:
        """最適なチャンクサイズを計算する

        ファイル数とサイズから最適なチャンクサイズを判断します。
        大きなファイルは個別にチャンク化し、
        小さなファイルは複数まとめてチャンク化します。

        Args:
            files: ファイル変更リスト
            max_tokens: チャンクあたりの最大トークン数

        Returns:
            int: 最適なチャンクサイズ（ファイル数）
        """
        if not files:
            return self.DEFAULT_MIN_CHUNK_SIZE

        total_files = len(files)

        # ファイル数が少ない場合は全て1チャンクに
        if total_files <= 2:
            return total_files

        # 大きなファイルがある場合は1ファイル1チャンクに
        for file_change in files:
            if self._is_large_file(file_change):
                self.logger.info(
                    f"Large file detected: {file_change.filename} "
                    f"with {file_change.changes} changes. Using 1 file per chunk."
                )
                return 1

        # 平均ファイルサイズに基づいてチャンクサイズを決定
        avg_file_size = sum(f.changes for f in files) / total_files

        if avg_file_size > 200:
            self.logger.info(f"Average file size is large: {avg_file_size:.1f} changes. Using 1 file per chunk.")
            return 1
        elif avg_file_size > 100:
            self.logger.info(f"Average file size is medium: {avg_file_size:.1f} changes. Using 2 files per chunk.")
            return 2
        else:
            self.logger.info(f"Average file size is small: {avg_file_size:.1f} changes. Using 3 files per chunk.")
            return 3

    def _is_large_file(self, file_change: FileChange) -> bool:
        """ファイルが大きいかどうかを判定する

        Args:
            file_change: ファイル変更情報

        Returns:
            bool: 大きなファイルの場合True
        """
        # 変更行数が多い場合
        if file_change.changes > 300:
            return True

        # ファイル内容が大きい場合
        if file_change.content_before and len(file_change.content_before) > 10000:
            return True
        if file_change.content_after and len(file_change.content_after) > 10000:
            return True

        return False

    def estimate_chunk_tokens(self, chunk: List[FileChange]) -> int:
        """チャンクのトークン数を推定する

        Args:
            chunk: ファイル変更のチャンク

        Returns:
            int: 推定トークン数
        """
        total_tokens = 0
        for file_change in chunk:
            content = file_change.patch or ""
            total_tokens += self.token_estimator.estimate_tokens(content)

        return total_tokens

    def calculate_statistics(self, files: List[FileChange]) -> Dict[str, Any]:
        """ファイル変更の統計情報を計算する

        Args:
            files: ファイル変更リスト

        Returns:
            Dict[str, Any]: 統計情報の辞書
        """
        if not files:
            return {
                'file_count': 0,
                'total_additions': 0,
                'total_deletions': 0,
                'total_changes': 0,
                'avg_changes_per_file': 0
            }

        total_additions = sum(f.additions for f in files)
        total_deletions = sum(f.deletions for f in files)
        total_changes = sum(f.changes for f in files)

        return {
            'file_count': len(files),
            'total_additions': total_additions,
            'total_deletions': total_deletions,
            'total_changes': total_changes,
            'avg_changes_per_file': total_changes / len(files)
        }
