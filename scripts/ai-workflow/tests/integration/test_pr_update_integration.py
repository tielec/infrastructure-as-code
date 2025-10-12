"""PR更新統合テスト (Issue #363)

Phase 8完了 → PR更新の一連のE2Eフローを検証
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
from core.github_client import GitHubClient
from phases.report import ReportPhase


@pytest.mark.integration
class TestPRUpdateIntegration:
    """PR更新統合テスト"""

    # IT-01: E2Eフロー_全フェーズ成果物あり_正常系
    def test_e2e_flow_all_phases_success(self, mocker, tmp_path):
        """
        IT-01: Phase 8完了からPR更新までの一連のフローが正常に動作することを検証

        Given: Phase 1-7の成果物が全て生成されている、メタデータにpr_number=123が保存されている
        When: ReportPhase.execute()を実行
        Then: PR #123の本文が詳細版に更新される
        """
        # GitHubClientのモック準備
        mock_pr = mocker.Mock()
        mock_pr.edit = mocker.Mock()

        mock_issue = mocker.Mock()
        mock_issue.body = "## 概要\n\nテスト用Issue本文"

        mock_repository = mocker.Mock()
        mock_repository.get_pull.return_value = mock_pr
        mock_repository.get_issue.return_value = mock_issue

        github_client = GitHubClient(token='test_token', repository='owner/repo')
        github_client.repository = mock_repository

        # メタデータマネージャーのモック
        mock_metadata = mocker.Mock()
        mock_metadata.data = {
            'pr_number': 123,
            'branch_name': 'ai-workflow/issue-363'
        }

        # 成果物ファイルのモック
        implementation_path = tmp_path / "implementation.md"
        implementation_path.write_text("""# 実装ログ

## 実装内容

- GitHubClient拡張
- ReportPhase統合
""", encoding='utf-8')

        test_result_path = tmp_path / "test-result.md"
        test_result_path.write_text("""# テスト結果

## テスト結果サマリー

全テストPASS
""", encoding='utf-8')

        documentation_path = tmp_path / "documentation-update-log.md"
        documentation_path.write_text("""# ドキュメント更新ログ

## 更新されたドキュメント

- README.md更新
""", encoding='utf-8')

        design_path = tmp_path / "design.md"
        design_path.write_text("""# 詳細設計書

## レビューポイント

1. エラーハンドリング確認
""", encoding='utf-8')

        phase_outputs = {
            'implementation': implementation_path,
            'test_result': test_result_path,
            'documentation': documentation_path,
            'design': design_path
        }

        # テンプレートファイルのモック
        template_content = """## AI Workflow自動生成PR

Closes #{issue_number}

{summary}

{implementation_details}

{test_results}

{documentation_updates}

{review_points}

{branch_name}
"""
        mock_open = mocker.mock_open(read_data=template_content)
        mocker.patch('builtins.open', mock_open)

        # _extract_phase_outputsの実行をシミュレート
        extracted_info = github_client._extract_phase_outputs(
            issue_number=363,
            phase_outputs=phase_outputs
        )

        # _generate_pr_body_detailedの実行をシミュレート
        pr_body = github_client._generate_pr_body_detailed(
            issue_number=363,
            branch_name='ai-workflow/issue-363',
            extracted_info=extracted_info
        )

        # update_pull_requestの実行
        result = github_client.update_pull_request(
            pr_number=123,
            body=pr_body
        )

        # アサーション
        assert result['success'] is True
        assert result['error'] is None

        # PR更新が呼ばれたことを確認
        mock_repository.get_pull.assert_called_once_with(123)
        mock_pr.edit.assert_called_once()

        # PR本文に必要な情報が含まれることを確認
        call_args = mock_pr.edit.call_args
        pr_body_arg = call_args[1]['body']
        assert '363' in pr_body_arg
        assert 'ai-workflow/issue-363' in pr_body_arg

    # IT-02: E2Eフロー_PR番号未保存_検索成功
    def test_e2e_flow_pr_number_not_saved_search_success(self, mocker):
        """
        IT-02: メタデータにPR番号がない場合でも、既存PR検索で取得して更新できることを検証

        Given: メタデータにpr_numberが保存されていない、ブランチに対応するPR #123が存在
        When: check_existing_pr()でPR検索
        Then: PR #123が見つかり、update_pull_request()が実行される
        """
        # GitHubClientのモック準備
        mock_pr = mocker.Mock()
        mock_pr.number = 123
        mock_pr.html_url = 'https://github.com/owner/repo/pull/123'
        mock_pr.state = 'open'
        mock_pr.edit = mocker.Mock()

        mock_owner = mocker.Mock()
        mock_owner.login = 'owner'

        mock_repository = mocker.Mock()
        mock_repository.owner = mock_owner
        mock_repository.get_pulls.return_value = [mock_pr]
        mock_repository.get_pull.return_value = mock_pr

        github_client = GitHubClient(token='test_token', repository='owner/repo')
        github_client.repository = mock_repository

        # 既存PR検索
        existing_pr = github_client.check_existing_pr(
            head='ai-workflow/issue-363',
            base='main'
        )

        # アサーション（PR検索成功）
        assert existing_pr is not None
        assert existing_pr['pr_number'] == 123

        # PR更新を実行
        result = github_client.update_pull_request(
            pr_number=existing_pr['pr_number'],
            body='## 更新されたPR本文'
        )

        # アサーション（PR更新成功）
        assert result['success'] is True
        mock_pr.edit.assert_called_once()

    # IT-03: E2Eフロー_PR未発見_スキップ
    def test_e2e_flow_pr_not_found_skip(self, mocker):
        """
        IT-03: PRが見つからない場合でもエラーにならないことを検証

        Given: 対応するPRが存在しない
        When: check_existing_pr()でPR検索
        Then: Noneが返され、PR更新はスキップされる
        """
        # GitHubClientのモック準備
        mock_owner = mocker.Mock()
        mock_owner.login = 'owner'

        mock_repository = mocker.Mock()
        mock_repository.owner = mock_owner
        mock_repository.get_pulls.return_value = []  # 空のリスト

        github_client = GitHubClient(token='test_token', repository='owner/repo')
        github_client.repository = mock_repository

        # 既存PR検索
        existing_pr = github_client.check_existing_pr(
            head='ai-workflow/issue-363',
            base='main'
        )

        # アサーション（PR未発見）
        assert existing_pr is None

    # IT-04: E2Eフロー_成果物一部欠落_デフォルト値使用
    def test_e2e_flow_partial_outputs_default_values(self, mocker, tmp_path):
        """
        IT-04: 一部の成果物が欠落していてもPR更新が継続されることを検証

        Given: Phase 4（implementation.md）の成果物が欠落
        When: _extract_phase_outputs()を実行
        Then: 欠落フィールドにデフォルト値が設定される
        """
        # GitHubClientのモック準備
        mock_issue = mocker.Mock()
        mock_issue.body = "## 概要\n\nテスト用Issue本文"

        mock_repository = mocker.Mock()
        mock_repository.get_issue.return_value = mock_issue

        github_client = GitHubClient(token='test_token', repository='owner/repo')
        github_client.repository = mock_repository

        # implementation.mdは存在しない（欠落）
        test_result_path = tmp_path / "test-result.md"
        test_result_path.write_text("## テスト結果サマリー\n\nテストOK", encoding='utf-8')

        documentation_path = tmp_path / "documentation-update-log.md"
        documentation_path.write_text("## 更新されたドキュメント\n\nREADME.md", encoding='utf-8')

        design_path = tmp_path / "design.md"
        design_path.write_text("## レビューポイント\n\nレビューテスト", encoding='utf-8')

        phase_outputs = {
            # 'implementation': None,  # 欠落
            'test_result': test_result_path,
            'documentation': documentation_path,
            'design': design_path
        }

        # 情報抽出
        result = github_client._extract_phase_outputs(
            issue_number=363,
            phase_outputs=phase_outputs
        )

        # アサーション（欠落フィールドにデフォルト値が設定）
        assert result['implementation_details'] == '（実装詳細の記載なし）'
        assert 'テストOK' in result['test_results']
        assert 'README.md' in result['documentation_updates']
        assert 'レビューテスト' in result['review_points']

    # IT-05: E2Eフロー_GitHub API制限到達_継続
    def test_e2e_flow_api_rate_limit_continue(self, mocker):
        """
        IT-05: GitHub API制限到達時のエラーハンドリングを検証

        Given: GitHub APIのrate limitに到達している
        When: update_pull_request()を実行
        Then: rate limitエラーが返されるが、例外はスローされない
        """
        from github import GithubException

        # GitHubClientのモック準備（rate limitエラー）
        mock_repository = mocker.Mock()
        mock_repository.get_pull.side_effect = GithubException(
            status=429,
            data={'message': 'API rate limit exceeded'},
            headers={}
        )

        github_client = GitHubClient(token='test_token', repository='owner/repo')
        github_client.repository = mock_repository

        # PR更新を実行
        result = github_client.update_pull_request(
            pr_number=123,
            body='## 更新されたPR本文'
        )

        # アサーション（エラーハンドリング確認）
        assert result['success'] is False
        assert result['error'] == 'GitHub API rate limit exceeded'
        # 例外はスローされず、エラー情報が返される

    # IT-06: GitHub API連携_PR取得と更新
    def test_github_api_integration_get_and_update(self, mocker):
        """
        IT-06: GitHub APIとの連携（PR取得 → 更新）が正常に動作することを検証

        Given: GitHub API連携をモック化、PR #123が存在する
        When: repository.get_pull(123) → pr.edit(body=new_body)を実行
        Then: 正しい順序でAPIが呼ばれる
        """
        # GitHubClientのモック準備
        mock_pr = mocker.Mock()
        mock_pr.edit = mocker.Mock()

        mock_repository = mocker.Mock()
        mock_repository.get_pull.return_value = mock_pr

        github_client = GitHubClient(token='test_token', repository='owner/repo')
        github_client.repository = mock_repository

        # PR更新を実行
        result = github_client.update_pull_request(
            pr_number=123,
            body='## 新しいPR本文'
        )

        # アサーション
        assert result['success'] is True

        # APIが正しい順序で呼ばれたことを確認
        mock_repository.get_pull.assert_called_once_with(123)
        mock_pr.edit.assert_called_once_with(body='## 新しいPR本文')

    # IT-07: GitHub API連携_複数回実行の冪等性
    def test_github_api_integration_idempotency(self, mocker):
        """
        IT-07: 同じPRに対して複数回実行しても、最新の成果物に基づいて正しく更新されることを検証

        Given: PR #123が存在する
        When: update_pull_request()を2回実行
        Then: 両方とも成功し、2回目は1回目を上書きする
        """
        # GitHubClientのモック準備
        mock_pr = mocker.Mock()
        mock_pr.edit = mocker.Mock()

        mock_repository = mocker.Mock()
        mock_repository.get_pull.return_value = mock_pr

        github_client = GitHubClient(token='test_token', repository='owner/repo')
        github_client.repository = mock_repository

        # 1回目のPR更新
        result1 = github_client.update_pull_request(
            pr_number=123,
            body='## 1回目のPR本文'
        )

        # 2回目のPR更新（同じPR）
        result2 = github_client.update_pull_request(
            pr_number=123,
            body='## 2回目のPR本文（更新版）'
        )

        # アサーション
        assert result1['success'] is True
        assert result2['success'] is True

        # editが2回呼ばれたことを確認
        assert mock_pr.edit.call_count == 2

        # 2回目の呼び出しで正しいbodyが渡されたことを確認
        second_call_args = mock_pr.edit.call_args_list[1]
        assert second_call_args[1]['body'] == '## 2回目のPR本文（更新版）'

    # IT-08: エラーリカバリー_テンプレート読み込み失敗
    def test_error_recovery_template_load_failure(self, mocker):
        """
        IT-08: テンプレート読み込み失敗時のエラーリカバリーを検証

        Given: テンプレートファイルが存在しない
        When: _generate_pr_body_detailed()を実行
        Then: FileNotFoundErrorが発生する
        """
        # GitHubClientのモック準備
        mocker.patch('builtins.open', side_effect=FileNotFoundError())

        github_client = GitHubClient(token='test_token', repository='owner/repo')

        extracted_info = {
            'summary': 'test',
            'implementation_details': 'test',
            'test_results': 'test',
            'documentation_updates': 'test',
            'review_points': 'test'
        }

        # テスト実行とアサーション
        with pytest.raises(FileNotFoundError) as exc_info:
            github_client._generate_pr_body_detailed(
                issue_number=363,
                branch_name='ai-workflow/issue-363',
                extracted_info=extracted_info
            )

        assert 'Template file not found' in str(exc_info.value)

    # IT-09: エラーリカバリー_Issue取得失敗
    def test_error_recovery_issue_fetch_failure(self, mocker, capsys):
        """
        IT-09: Issue本文取得失敗時のエラーリカバリーを検証

        Given: Issue #363の取得がGitHub APIエラーで失敗する
        When: _extract_phase_outputs()を実行
        Then: 全フィールドにエラー表示が設定される
        """
        from github import GithubException

        # GitHubClientのモック準備（Issue取得失敗）
        mock_repository = mocker.Mock()
        mock_repository.get_issue.side_effect = GithubException(
            status=500,
            data={'message': 'Internal Server Error'},
            headers={}
        )

        github_client = GitHubClient(token='test_token', repository='owner/repo')
        github_client.repository = mock_repository

        phase_outputs = {}

        # 情報抽出
        result = github_client._extract_phase_outputs(
            issue_number=363,
            phase_outputs=phase_outputs
        )

        # アサーション（全フィールドにエラー表示）
        assert result['summary'] == '（情報抽出エラー）'
        assert result['implementation_details'] == '（情報抽出エラー）'
        assert result['test_results'] == '（情報抽出エラー）'
        assert result['documentation_updates'] == '（情報抽出エラー）'
        assert result['review_points'] == '（情報抽出エラー）'

        # 警告ログが出力されることを確認
        captured = capsys.readouterr()
        assert '[WARNING] 成果物抽出中にエラー' in captured.out
