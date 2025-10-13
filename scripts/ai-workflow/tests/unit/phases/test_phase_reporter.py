"""
Unit tests for phases/base/phase_reporter.py

Test Scenarios:
- UT-PR-001: PhaseReporter.post_progress() - 開始
- UT-PR-002: PhaseReporter.post_progress() - 完了
- UT-PR-003: PhaseReporter.post_review() - PASS
- UT-PR-004: PhaseReporter.post_review() - FAIL
"""
import pytest
from unittest.mock import Mock, patch
from phases.base.phase_reporter import PhaseReporter


class TestPhaseReporter:
    """PhaseReporter クラスのユニットテスト"""

    def test_post_progress_creates_new_comment_on_first_call(self):
        """UT-PR-001: 初回の進捗投稿で新規コメントが作成されることを確認"""
        # Given: 初回投稿（comment_idがNone）
        mock_issue_client = Mock()
        mock_comment_client = Mock()
        mock_comment_client.create_or_update_progress_comment.return_value = {
            'comment_id': 12345,
            'comment_url': 'https://github.com/.../issues/376#issuecomment-12345'
        }

        mock_metadata = Mock()
        mock_metadata.data = {'issue_number': 376, 'phases': {}}
        mock_metadata.get_progress_comment_id.return_value = None  # 初回
        mock_metadata.get_all_phases_status.return_value = {
            'planning': 'in_progress',
            'requirements': 'pending',
            'design': 'pending'
        }

        reporter = PhaseReporter(mock_issue_client, mock_comment_client, mock_metadata)

        # When: 進捗を投稿
        reporter.post_progress(
            phase_name='planning',
            status='in_progress',
            details='planningフェーズを開始しました。'
        )

        # Then: 新規コメントが作成され、comment_idが保存される
        mock_comment_client.create_or_update_progress_comment.assert_called_once()
        call_args = mock_comment_client.create_or_update_progress_comment.call_args
        assert call_args[1]['issue_number'] == 376
        assert call_args[1]['comment_id'] is None  # 初回はNone

        mock_metadata.save_progress_comment_id.assert_called_once_with(
            comment_id=12345,
            comment_url='https://github.com/.../issues/376#issuecomment-12345'
        )

    def test_post_progress_updates_existing_comment(self):
        """UT-PR-002: 2回目以降の進捗投稿で既存コメントが更新されることを確認"""
        # Given: 既存コメントが存在する（comment_idあり）
        mock_issue_client = Mock()
        mock_comment_client = Mock()
        mock_comment_client.create_or_update_progress_comment.return_value = {
            'comment_id': 12345,
            'comment_url': 'https://github.com/.../issues/376#issuecomment-12345'
        }

        mock_metadata = Mock()
        mock_metadata.data = {'issue_number': 376, 'phases': {}}
        mock_metadata.get_progress_comment_id.return_value = 12345  # 既存
        mock_metadata.get_all_phases_status.return_value = {
            'planning': 'completed',
            'requirements': 'in_progress',
            'design': 'pending'
        }

        reporter = PhaseReporter(mock_issue_client, mock_comment_client, mock_metadata)

        # When: 進捗を投稿
        reporter.post_progress(
            phase_name='requirements',
            status='in_progress',
            details='requirementsフェーズを開始しました。'
        )

        # Then: 既存コメントが更新される
        mock_comment_client.create_or_update_progress_comment.assert_called_once()
        call_args = mock_comment_client.create_or_update_progress_comment.call_args
        assert call_args[1]['comment_id'] == 12345  # 既存のID

        # 2回目以降はsave_progress_comment_id()は呼ばれない
        mock_metadata.save_progress_comment_id.assert_not_called()

    def test_post_review_creates_review_comment_pass(self):
        """UT-PR-003: レビュー結果PASSが正しく投稿されることを確認"""
        # Given: レビュー結果PASS
        mock_issue_client = Mock()
        mock_comment_client = Mock()

        mock_metadata = Mock()
        mock_metadata.data = {'issue_number': 376}

        reporter = PhaseReporter(mock_issue_client, mock_comment_client, mock_metadata)

        # When: レビュー結果を投稿
        reporter.post_review(
            phase_name='planning',
            result='PASS',
            feedback='All quality gates passed',
            suggestions=[]
        )

        # Then: コメントが投稿される
        mock_comment_client.post_comment.assert_called_once()
        call_args = mock_comment_client.post_comment.call_args
        issue_number = call_args[0][0]
        body = call_args[0][1]

        assert issue_number == 376
        assert 'PASS' in body
        assert 'planning' in body
        assert 'All quality gates passed' in body

    def test_post_review_creates_review_comment_fail(self):
        """UT-PR-004: レビュー結果FAILが正しく投稿されることを確認"""
        # Given: レビュー結果FAIL
        mock_issue_client = Mock()
        mock_comment_client = Mock()

        mock_metadata = Mock()
        mock_metadata.data = {'issue_number': 376}

        reporter = PhaseReporter(mock_issue_client, mock_comment_client, mock_metadata)

        # When: レビュー結果を投稿
        reporter.post_review(
            phase_name='planning',
            result='FAIL',
            feedback='Quality gates not met',
            suggestions=['Add more details', 'Fix typos']
        )

        # Then: コメントが投稿される
        mock_comment_client.post_comment.assert_called_once()
        call_args = mock_comment_client.post_comment.call_args
        issue_number = call_args[0][0]
        body = call_args[0][1]

        assert issue_number == 376
        assert 'FAIL' in body
        assert 'planning' in body
        assert 'Quality gates not met' in body
        assert 'Add more details' in body
        assert 'Fix typos' in body

    def test_format_progress_content_includes_all_phases(self):
        """_format_progress_content()が全フェーズの進捗を含むことを確認"""
        # Given: 複数フェーズのステータス
        mock_issue_client = Mock()
        mock_comment_client = Mock()

        mock_metadata = Mock()
        mock_metadata.data = {
            'issue_number': 376,
            'phases': {
                'planning': {'status': 'completed', 'completed_at': '2025-10-12T10:00:00'},
                'requirements': {'status': 'in_progress'},
                'design': {'status': 'pending'}
            }
        }
        mock_metadata.get_all_phases_status.return_value = {
            'planning': 'completed',
            'requirements': 'in_progress',
            'design': 'pending',
            'test_scenario': 'pending',
            'implementation': 'pending',
            'test_implementation': 'pending',
            'testing': 'pending',
            'documentation': 'pending',
            'report': 'pending',
            'evaluation': 'pending'
        }

        reporter = PhaseReporter(mock_issue_client, mock_comment_client, mock_metadata)

        # When: Markdownコンテンツを生成
        content = reporter._format_progress_content(
            current_phase='requirements',
            status='in_progress',
            details='Requirements フェーズを実行中'
        )

        # Then: 全フェーズと現在のフェーズ詳細が含まれる
        assert '## 🤖 AI Workflow - 進捗状況' in content
        assert 'Phase 0: Planning' in content
        assert 'Phase 1: Requirements' in content
        assert 'Phase 2: Design' in content
        assert '✅' in content  # completed emoji
        assert '🔄' in content  # in_progress emoji
        assert '⏸️' in content  # pending emoji
        assert 'Requirements フェーズを実行中' in content
        assert '最終更新:' in content

    def test_format_review_content_with_suggestions(self):
        """_format_review_content()が改善提案を含むことを確認"""
        # Given: 改善提案付きレビュー
        mock_issue_client = Mock()
        mock_comment_client = Mock()
        mock_metadata = Mock()

        reporter = PhaseReporter(mock_issue_client, mock_comment_client, mock_metadata)

        # When: レビューコンテンツを生成
        content = reporter._format_review_content(
            phase_name='planning',
            result='PASS_WITH_SUGGESTIONS',
            feedback='Overall good',
            suggestions=['Improve risk analysis', 'Add timeline']
        )

        # Then: 改善提案が含まれる
        assert 'PASS_WITH_SUGGESTIONS' in content
        assert 'Overall good' in content
        assert '改善提案' in content
        assert 'Improve risk analysis' in content
        assert 'Add timeline' in content
        assert '⚠️' in content  # PASS_WITH_SUGGESTIONS emoji

    def test_post_progress_handles_exception_gracefully(self):
        """post_progress()が例外を適切に処理することを確認"""
        # Given: post_comment()が例外を発生させる
        mock_issue_client = Mock()
        mock_comment_client = Mock()
        mock_comment_client.create_or_update_progress_comment.side_effect = Exception("API Error")

        mock_metadata = Mock()
        mock_metadata.data = {'issue_number': 376, 'phases': {}}
        mock_metadata.get_progress_comment_id.return_value = None
        mock_metadata.get_all_phases_status.return_value = {}

        reporter = PhaseReporter(mock_issue_client, mock_comment_client, mock_metadata)

        # When: 進捗を投稿（例外が発生）
        # Then: 例外が発生せず、警告ログが出力される
        reporter.post_progress('planning', 'in_progress', 'Test details')

        # 例外が発生しないことを確認（警告ログで処理される）
        mock_comment_client.create_or_update_progress_comment.assert_called_once()

    def test_post_review_handles_exception_gracefully(self):
        """post_review()が例外を適切に処理することを確認"""
        # Given: post_comment()が例外を発生させる
        mock_issue_client = Mock()
        mock_comment_client = Mock()
        mock_comment_client.post_comment.side_effect = Exception("API Error")

        mock_metadata = Mock()
        mock_metadata.data = {'issue_number': 376}

        reporter = PhaseReporter(mock_issue_client, mock_comment_client, mock_metadata)

        # When: レビュー結果を投稿（例外が発生）
        # Then: 例外が発生せず、警告ログが出力される
        reporter.post_review('planning', 'PASS', 'Good work')

        # 例外が発生しないことを確認（警告ログで処理される）
        mock_comment_client.post_comment.assert_called_once()
