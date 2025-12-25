"""ファイル変更をチャンク単位で分析するための補助モジュール。"""
import logging
from typing import List

from .models import PRInfo, FileChange
from .openai_client import OpenAIClient


class ChunkAnalyzer:
    """チャンク分割と分析のオーケストレーションを担当するクラス"""

    def __init__(self, openai_client: OpenAIClient, log_level: int = logging.INFO):
        self.openai_client = openai_client
        self.logger = logging.getLogger("chunk_analyzer")
        self.logger.setLevel(log_level)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def calculate_optimal_chunk_size(self, changes: List[FileChange]) -> int:
        """OpenAIクライアントのロジックを利用して最適チャンクサイズを計算"""
        return self.openai_client._calculate_optimal_chunk_size(changes)

    def split_into_chunks(self, changes: List[FileChange], chunk_size: int) -> List[List[FileChange]]:
        """チャンクサイズに従ってファイルリストを分割"""
        return self.openai_client._split_changes_into_chunks(changes, chunk_size)

    def analyze_all_chunks(self, pr_info: PRInfo, chunks: List[List[FileChange]]) -> List[str]:
        """チャンク群を順次分析"""
        analyses: List[str] = []
        for index, chunk in enumerate(chunks, 1):
            analyses.append(self.analyze_single_chunk(pr_info, chunk, index))
        return analyses

    def analyze_single_chunk(self, pr_info: PRInfo, chunk: List[FileChange], chunk_index: int) -> str:
        """単一チャンクを分析し、失敗時はエラーメッセージを返す"""
        self.logger.info(f"Analyzing chunk {chunk_index}/{len(chunk)} files: {[c.filename for c in chunk]}")
        try:
            return self.openai_client._analyze_chunk(pr_info, chunk, chunk_index)
        except Exception as exc:  # noqa: BLE001 既存の例外処理方針に合わせる
            self.logger.error(f"Error analyzing chunk {chunk_index}: {exc}")
            return f"[チャンク {chunk_index} の分析に失敗しました: {exc}]"
