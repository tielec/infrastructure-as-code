# jenkins/jobs/pipeline/docs-generator/pull-request-comment-builder/src/pr_comment_generator/formatter.py
"""
コメントフォーマット処理モジュール

このモジュールは、PRコメントのMarkdownフォーマット処理機能を提供します。

主要なクラス:
- CommentFormatter: コメントのフォーマット処理
"""

import os
import re
import logging
from typing import List, Dict, Any

from .models import FileChange


class CommentFormatter:
    """PRコメントのフォーマット処理を行うクラス"""

    def __init__(self, logger: logging.Logger = None):
        """初期化

        Args:
            logger: ロガーインスタンス
        """
        self.logger = logger or logging.getLogger(__name__)

    def clean_markdown_format(self, text: str) -> str:
        """Markdownフォーマットをクリーンアップする

        Args:
            text: クリーンアップするテキスト

        Returns:
            str: クリーンアップされたテキスト
        """
        # コードブロックマーカーの削除
        text = re.sub(r'^```markdown\s*\n', '', text)  # 先頭の```markdownを削除
        text = re.sub(r'\n```\s*$', '', text)          # 末尾の```を削除

        # 余分な空行を削除（3行以上の空行を2行に）
        text = re.sub(r'\n{3,}', '\n\n', text)

        # コードブロックの前後の空行を調整
        text = re.sub(r'\n+```', '\n```', text)
        text = re.sub(r'```\n+', '```\n', text)

        # 末尾の空白を削除
        text = '\n'.join(line.rstrip() for line in text.split('\n'))

        return text.strip()

    def format_chunk_analyses(self, analyses: List[str]) -> str:
        """チャンク分析結果をフォーマットする

        Args:
            analyses: チャンク分析結果のリスト

        Returns:
            str: フォーマットされた分析結果
        """
        if not analyses:
            return ""

        formatted_parts = []
        for i, analysis in enumerate(analyses, 1):
            # "...中略..."をスキップ
            if analysis == '...中略...':
                formatted_parts.append(analysis)
                continue

            header = f"=== チャンク {i} ===\n"
            formatted_parts.append(header + analysis)

        result = "\n\n".join(formatted_parts)
        return self.clean_markdown_format(result)

    def format_file_list(self, files: List[FileChange]) -> str:
        """ファイルリストをフォーマットする

        Args:
            files: ファイル変更リスト

        Returns:
            str: フォーマットされたファイルリスト
        """
        if not files:
            return "変更されたファイルはありません。"

        lines = ["## 変更されたファイル\n"]
        for file in files:
            # ステータスに応じた絵文字を選択
            status_emoji = {
                'added': '✨',
                'modified': '📝',
                'removed': '🗑️',
                'renamed': '📛'
            }.get(file.status, '📄')

            line = f"- {status_emoji} `{file.filename}` (+{file.additions} -{file.deletions})"
            lines.append(line)

        return "\n".join(lines)

    def format_skipped_files_info(
        self,
        skipped_files: List[FileChange],
        reason: str = "サイズ制限"
    ) -> str:
        """スキップされたファイルの情報をフォーマットする

        Args:
            skipped_files: スキップされたファイルリスト
            reason: スキップ理由

        Returns:
            str: フォーマットされた情報
        """
        if not skipped_files:
            return ""

        lines = [
            f"\n## ⚠️ スキップされたファイル ({reason})\n",
            f"以下の{len(skipped_files)}個のファイルは{reason}によりスキップされました：\n"
        ]

        for file in skipped_files:
            lines.append(
                f"- `{file.filename}` ({file.additions} 行追加, "
                f"{file.deletions} 行削除, 合計 {file.changes} 行変更)"
            )

        return "\n".join(lines)

    def rebuild_file_section(self, comment: str, original_file_paths: List[str]) -> str:
        """ファイルセクションを再構築する（ファイルパス正規化）

        コメント内のファイルパスを正規化し、重複を削除します。

        Args:
            comment: コメントテキスト
            original_file_paths: 元のファイルパスリスト

        Returns:
            str: 再構築されたコメント
        """
        # 修正されたファイルセクションを検索
        file_section_pattern = r'## 修正されたファイル.*?(?=##|$)'
        file_section_match = re.search(file_section_pattern, comment, re.DOTALL)

        if not file_section_match:
            self.logger.warning("File section not found in comment")
            return comment

        file_section = file_section_match.group(0)

        # ファイルパスを抽出（バッククォートで囲まれたパス）
        file_paths = re.findall(r'`([^`]+)`', file_section)

        # 正規化されたパスのセット（重複削除）
        normalized_paths = set()
        path_mapping = {}  # 正規化されたパス -> 元のパス

        for path in file_paths:
            # パスを正規化（末尾のスラッシュや余分な空白を削除）
            normalized = path.strip().rstrip('/')

            # 元のパスリストから最も近いパスを見つける
            best_match = self._find_best_match(normalized, original_file_paths)
            if best_match:
                normalized_paths.add(best_match)
                path_mapping[normalized] = best_match

        # 元のパスリストから漏れているファイルを追加
        for orig_path in original_file_paths:
            if orig_path not in normalized_paths:
                normalized_paths.add(orig_path)

        # 新しいファイルセクションを構築
        new_file_section = "## 修正されたファイル\n"
        for path in sorted(normalized_paths):
            new_file_section += f"- `{path}`\n"

        # コメント内のファイルセクションを置換
        new_comment = re.sub(file_section_pattern, new_file_section, comment, flags=re.DOTALL)

        return new_comment

    def _find_best_match(self, path: str, candidates: List[str]) -> str:
        """候補リストから最も近いパスを見つける

        Args:
            path: 検索対象のパス
            candidates: 候補パスのリスト

        Returns:
            str: 最も近いパス（見つからない場合は元のパス）
        """
        # 完全一致
        if path in candidates:
            return path

        # 部分一致（最も長い共通部分）
        best_match = None
        max_common_len = 0

        for candidate in candidates:
            common_len = len(os.path.commonprefix([path, candidate]))
            if common_len > max_common_len:
                max_common_len = common_len
                best_match = candidate

        return best_match if best_match else path

    def format_final_comment(
        self,
        summary: str,
        chunk_analyses: List[str],
        files: List[FileChange],
        skipped_files: List[FileChange] = None
    ) -> str:
        """最終的なPRコメントをフォーマットする

        Args:
            summary: サマリーテキスト
            chunk_analyses: チャンク分析結果
            files: ファイル変更リスト
            skipped_files: スキップされたファイルリスト

        Returns:
            str: フォーマットされた最終コメント
        """
        parts = [
            "# 変更内容サマリー\n",
            summary,
            "\n\n"
        ]

        # チャンク分析の追加（複数チャンクの場合のみ）
        if len(chunk_analyses) > 1:
            parts.append(self.format_chunk_analyses(chunk_analyses))
            parts.append("\n\n")

        # ファイルリストの追加
        parts.append(self.format_file_list(files))

        # スキップファイル情報の追加
        if skipped_files:
            parts.append(self.format_skipped_files_info(skipped_files))

        result = "".join(parts)
        return self.clean_markdown_format(result)
