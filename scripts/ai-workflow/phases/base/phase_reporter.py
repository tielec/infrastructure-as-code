"""Phase Reporter - フェーズレポート生成

このモジュールは、フェーズの進捗状況とレビュー結果をGitHubに報告する機能を提供します。

機能:
    - 進捗状況のGitHub Issue/PRへの投稿
    - レビュー結果のGitHub Issue/PRへの投稿
    - Markdown形式のレポート生成
    - 統合進捗コメントの更新

使用例:
    >>> reporter = PhaseReporter(issue_client, comment_client, metadata_manager)
    >>> reporter.post_progress('planning', 'in_progress', '計画フェーズを開始しました')
    >>> reporter.post_review('planning', 'PASS', 'すべての項目が適切です')
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from core.metadata_manager import MetadataManager
from core.github.issue_client import IssueClient
from core.github.comment_client import CommentClient
from common.logger import Logger


class PhaseReporter:
    """フェーズレポート生成クラス

    フェーズの進捗状況とレビュー結果をGitHubに報告します。

    Attributes:
        issue_client: Issue操作クライアント
        comment_client: Comment操作クライアント
        metadata: メタデータマネージャー
        logger: ロガーインスタンス
    """

    def __init__(
        self,
        issue_client: IssueClient,
        comment_client: CommentClient,
        metadata_manager: MetadataManager
    ):
        """初期化

        Args:
            issue_client: Issue操作クライアント
            comment_client: Comment操作クライアント
            metadata_manager: メタデータマネージャー
        """
        self.issue_client = issue_client
        self.comment_client = comment_client
        self.metadata = metadata_manager
        self.logger = Logger.get_logger(__name__)

    def post_progress(
        self,
        phase_name: str,
        status: str,
        details: Optional[str] = None
    ):
        """GitHubに進捗報告（統合コメント形式）

        全フェーズの進捗状況を1つのコメントで管理し、更新します。

        Args:
            phase_name: フェーズ名（例: 'planning', 'design'）
            status: ステータス（pending, in_progress, completed, failed）
            details: 詳細情報（省略可）

        Example:
            >>> reporter.post_progress('planning', 'in_progress', '計画フェーズを開始しました')
        """
        try:
            issue_number = int(self.metadata.data['issue_number'])

            # 統合コメント形式のMarkdownを生成
            content = self._format_progress_content(phase_name, status, details)

            # コメント作成または更新
            comment_id = self.metadata.get_progress_comment_id()
            result = self.comment_client.create_or_update_progress_comment(
                issue_number=issue_number,
                content=content,
                comment_id=comment_id
            )

            # コメントIDを保存（初回のみ）
            if not comment_id:
                self.metadata.save_progress_comment_id(
                    comment_id=result['comment_id'],
                    comment_url=result['comment_url']
                )

            self.logger.info(f"Progress comment updated: {result['comment_url']}")

        except Exception as e:
            self.logger.warning(f"Failed to post progress: {e}")

    def post_review(
        self,
        phase_name: str,
        result: str,
        feedback: Optional[str] = None,
        suggestions: Optional[List[str]] = None
    ):
        """GitHubにレビュー結果を投稿

        Args:
            phase_name: フェーズ名（例: 'planning', 'design'）
            result: レビュー結果（PASS, PASS_WITH_SUGGESTIONS, FAIL）
            feedback: フィードバック（省略可）
            suggestions: 改善提案一覧（省略可）

        Example:
            >>> reporter.post_review(
            ...     'planning',
            ...     'PASS',
            ...     'すべての項目が適切です',
            ...     ['リスク分析をさらに詳細化できます']
            ... )
        """
        try:
            issue_number = int(self.metadata.data['issue_number'])

            # レビュー結果Markdown生成
            body = self._format_review_content(phase_name, result, feedback, suggestions)

            # コメント投稿
            self.comment_client.post_comment(issue_number, body)

            self.logger.info(f"Review result posted to issue #{issue_number}")

        except Exception as e:
            self.logger.warning(f"Failed to post review: {e}")

    def _format_progress_content(
        self,
        current_phase: str,
        status: str,
        details: Optional[str]
    ) -> str:
        """進捗コメントのMarkdownフォーマットを生成

        Args:
            current_phase: 現在のフェーズ名
            status: ステータス（pending, in_progress, completed, failed）
            details: 詳細情報

        Returns:
            str: Markdown形式のコメント本文
        """
        # ステータスアイコンマッピング
        status_emoji = {
            'pending': '⏸️',
            'in_progress': '🔄',
            'completed': '✅',
            'failed': '❌'
        }

        # フェーズ名マッピング
        phase_names = {
            'planning': ('Phase 0', 'Planning'),
            'requirements': ('Phase 1', 'Requirements'),
            'design': ('Phase 2', 'Design'),
            'test_scenario': ('Phase 3', 'Test Scenario'),
            'implementation': ('Phase 4', 'Implementation'),
            'test_implementation': ('Phase 5', 'Test Implementation'),
            'testing': ('Phase 6', 'Testing'),
            'documentation': ('Phase 7', 'Documentation'),
            'report': ('Phase 8', 'Report'),
            'evaluation': ('Phase 9', 'Evaluation')
        }

        # 全フェーズのステータスを取得
        phases_status = self.metadata.get_all_phases_status()

        # ヘッダー
        content_parts = []
        content_parts.append("## 🤖 AI Workflow - 進捗状況\n")
        content_parts.append("\n### 全体進捗\n\n")

        # 全体進捗セクション
        for phase_key, (phase_number, phase_label) in phase_names.items():
            phase_status = phases_status.get(phase_key, 'pending')
            emoji = status_emoji.get(phase_status, '📝')

            status_line = f"- {emoji} {phase_number}: {phase_label} - **{phase_status.upper()}**"

            if phase_status == 'completed':
                phase_data = self.metadata.data['phases'].get(phase_key, {})
                completed_at = phase_data.get('completed_at')
                if completed_at:
                    status_line += f" ({completed_at})"

            content_parts.append(status_line + "\n")

        # 現在のフェーズの詳細セクション
        if current_phase:
            phase_number, phase_label = phase_names.get(current_phase, ('Phase X', current_phase))
            content_parts.append(f"\n### 現在のフェーズ: {phase_number} ({phase_label})\n\n")
            content_parts.append(f"**ステータス**: {status.upper()}\n")

            if details:
                content_parts.append(f"\n{details}\n")

        # フッター
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        content_parts.append("\n---\n")
        content_parts.append(f"*最終更新: {current_time}*\n")
        content_parts.append("*AI駆動開発自動化ワークフロー (Claude Agent SDK)*\n")

        return ''.join(content_parts)

    def _format_review_content(
        self,
        phase_name: str,
        result: str,
        feedback: Optional[str],
        suggestions: Optional[List[str]]
    ) -> str:
        """レビュー結果のMarkdownフォーマットを生成

        Args:
            phase_name: フェーズ名
            result: レビュー結果（PASS, PASS_WITH_SUGGESTIONS, FAIL）
            feedback: フィードバック
            suggestions: 改善提案一覧

        Returns:
            str: Markdown形式のコメント本文
        """
        # レビュー結果絵文字マッピング
        result_emoji = {
            'PASS': '✅',
            'PASS_WITH_SUGGESTIONS': '⚠️',
            'FAIL': '❌'
        }

        emoji = result_emoji.get(result, '📝')

        body = f"## {emoji} レビュー結果 - {phase_name}フェーズ\n\n"
        body += f"**判定**: {result}\n\n"

        if feedback:
            body += f"### フィードバック\n\n{feedback}\n\n"

        if suggestions:
            body += "### 改善提案\n\n"
            for i, suggestion in enumerate(suggestions, 1):
                body += f"{i}. {suggestion}\n"
            body += "\n"

        body += "---\n"
        body += "*AI駆動開発自動化ワークフロー - クリティカルシンキングレビュー*"

        return body
