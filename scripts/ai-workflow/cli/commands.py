"""CLI Commands - コマンドラインインターフェース

このモジュールは、AI駆動ワークフローのCLIコマンドを定義します。

機能:
    - init: ワークフロー初期化
    - execute: フェーズ実行（単一 or 全フェーズ）
    - status: ワークフロー状態確認
    - resume: ワークフロー再開

使用例:
    $ python main.py init --issue-url https://github.com/owner/repo/issues/380
    $ python main.py execute --issue 380 --phase planning
    $ python main.py execute --issue 380 --phase all
    $ python main.py status --issue 380
    $ python main.py resume --issue 380
"""

import click
import sys
import os
from pathlib import Path
from typing import Optional
from git import Repo
from core.workflow_controller import WorkflowController
from core.config_manager import ConfigManager
from core.metadata_manager import MetadataManager
from core.claude_agent_client import ClaudeAgentClient
from core.git.repository import GitRepository
from core.git.branch import GitBranch
from core.git.commit import GitCommit
from core.github.issue_client import IssueClient
from core.github.pr_client import PRClient
from core.github.comment_client import CommentClient
from common.logger import Logger


def _get_repo_root() -> Path:
    """Gitリポジトリのルートディレクトリを取得"""
    try:
        repo = Repo(search_parent_directories=True)
        return Path(repo.working_dir)
    except Exception:
        # Gitリポジトリが見つからない場合は、カレントディレクトリを返す
        return Path.cwd()


def _initialize_workflow_controller(
    issue_number: int,
    metadata_path: Optional[Path] = None
) -> WorkflowController:
    """WorkflowControllerを初期化

    Args:
        issue_number: Issue番号
        metadata_path: メタデータファイルのパス（オプション）

    Returns:
        WorkflowController: 初期化されたインスタンス
    """
    # リポジトリルート取得
    repo_root = _get_repo_root()

    # ConfigManager初期化
    config_path = repo_root / 'scripts' / 'ai-workflow' / 'config.yaml'
    config_manager = ConfigManager(config_path)
    config = config_manager.load_config()

    # MetadataManager初期化
    if metadata_path is None:
        metadata_path = repo_root / '.ai-workflow' / f'issue-{issue_number}' / 'metadata.json'

    metadata_manager = MetadataManager(metadata_path)

    # Git関連インスタンス初期化
    git_repository = GitRepository(repo_root)
    git_branch = GitBranch(repo_root)
    git_commit = GitCommit(git_repository.repo, metadata_manager)

    # GitHub関連インスタンス初期化
    github_token = config_manager.get('github_token')
    github_repository = config_manager.get('github_repository')

    issue_client = IssueClient(github_token, github_repository)
    pr_client = PRClient(github_token, github_repository)
    comment_client = CommentClient(github_token, github_repository)

    # ClaudeAgentClient初期化
    claude_client = ClaudeAgentClient(working_dir=repo_root / 'scripts' / 'ai-workflow')

    # WorkflowController初期化
    controller = WorkflowController(
        repo_root=repo_root,
        config_manager=config_manager,
        metadata_manager=metadata_manager,
        git_repository=git_repository,
        git_branch=git_branch,
        git_commit=git_commit,
        issue_client=issue_client,
        pr_client=pr_client,
        comment_client=comment_client,
        claude_client=claude_client
    )

    return controller


@click.group()
def cli():
    """AI駆動開発自動化ワークフロー"""
    pass


@cli.command()
@click.option('--issue-url', required=True, help='GitHub Issue URL')
def init(issue_url: str):
    """ワークフロー初期化

    処理内容:
        1. Issue URLからIssue番号を抽出
        2. WorkflowController.initialize()を呼び出し
        3. 初期化成功時のメッセージ表示
        4. エラー時の適切なエラーメッセージとexit code

    例:
        python main.py init --issue-url https://github.com/owner/repo/issues/380
    """
    import re

    # Issue URLのバリデーション
    if not re.match(r'^https://github\.com/[\w-]+/[\w-]+/issues/\d+/?$', issue_url.rstrip('/')):
        click.echo('[ERROR] Invalid Issue URL format')
        click.echo('[ERROR] Expected format: https://github.com/owner/repo/issues/NUMBER')
        sys.exit(1)

    # Issue番号抽出
    issue_number = issue_url.rstrip('/').split('/')[-1]

    # Issue番号のバリデーション
    if not issue_number.isdigit():
        click.echo('[ERROR] Invalid Issue number')
        sys.exit(1)

    issue_number = int(issue_number)

    try:
        # WorkflowController初期化
        controller = _initialize_workflow_controller(issue_number)

        # ワークフロー初期化
        result = controller.initialize(issue_number=issue_number, issue_url=issue_url)

        if result['success']:
            click.echo(f'[OK] Workflow initialized for Issue #{issue_number}')
            click.echo(f'[OK] Branch: {result["branch_name"]}')
            click.echo(f'[OK] Metadata: {result["metadata_path"]}')
        else:
            click.echo(f'[ERROR] Workflow initialization failed')
            click.echo(f'[ERROR] {result["error"]}')
            sys.exit(1)

    except Exception as e:
        click.echo(f'[ERROR] Unexpected error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option('--phase', required=True,
              type=click.Choice(['all', 'planning', 'requirements', 'design',
                                'test_scenario', 'implementation', 'test_implementation',
                                'testing', 'documentation', 'report', 'evaluation']))
@click.option('--issue', required=True, help='Issue number')
@click.option('--skip-dependency-check', is_flag=True, default=False,
              help='Skip dependency checks')
@click.option('--ignore-dependencies', is_flag=True, default=False,
              help='Show warnings but continue when dependencies are not met')
def execute(phase: str, issue: str, skip_dependency_check: bool = False,
            ignore_dependencies: bool = False):
    """フェーズ実行

    処理内容:
        1. メタデータ読み込み
        2. WorkflowController.execute_phase() または execute_all_phases()を呼び出し
        3. 実行結果の表示
        4. エラー時の適切なエラーメッセージとexit code

    例:
        python main.py execute --issue 380 --phase planning
        python main.py execute --issue 380 --phase all
    """
    # オプションの排他性チェック
    if skip_dependency_check and ignore_dependencies:
        click.echo('[ERROR] Options "--skip-dependency-check" and "--ignore-dependencies" are mutually exclusive')
        sys.exit(1)

    try:
        issue_number = int(issue)

        # WorkflowController初期化
        controller = _initialize_workflow_controller(issue_number)

        # メタデータ存在チェック
        if not controller.metadata.metadata_path.exists():
            click.echo(f'[ERROR] Workflow not found for Issue #{issue_number}')
            click.echo(f'[ERROR] Please run "init" first')
            sys.exit(1)

        # メタデータ読み込み
        controller.metadata.load()

        # フェーズ実行
        if phase == 'all':
            click.echo(f'[INFO] Starting all phases execution for Issue #{issue_number}')
            result = controller.execute_all_phases(
                skip_dependency_check=skip_dependency_check,
                ignore_dependencies=ignore_dependencies
            )

            if result['success']:
                click.echo(f'[OK] All phases completed successfully')
                click.echo(f'[OK] Completed: {", ".join(result["completed_phases"])}')
                click.echo(f'[OK] Duration: {result["total_duration"]:.2f}s')
            else:
                click.echo(f'[ERROR] Workflow failed at phase: {result["failed_phase"]}')
                click.echo(f'[ERROR] {result["error"]}')
                sys.exit(1)
        else:
            click.echo(f'[INFO] Starting phase: {phase}')
            result = controller.execute_phase(
                phase,
                skip_dependency_check=skip_dependency_check,
                ignore_dependencies=ignore_dependencies
            )

            if result['success']:
                click.echo(f'[OK] Phase {phase} completed successfully')
                click.echo(f'[OK] Review result: {result["review_result"]}')
            else:
                click.echo(f'[ERROR] Phase {phase} failed: {result["error"]}')
                sys.exit(1)

    except ValueError:
        click.echo('[ERROR] Invalid issue number')
        sys.exit(1)
    except Exception as e:
        click.echo(f'[ERROR] Unexpected error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option('--issue', required=True, help='Issue number')
def status(issue: str):
    """ワークフローの状態を確認

    処理内容:
        1. メタデータからワークフロー状態を取得
        2. 各フェーズの実行状態（未実行/実行中/完了/失敗）を表示
        3. 現在のブランチ、Issue番号を表示

    例:
        python main.py status --issue 380
    """
    try:
        issue_number = int(issue)

        # WorkflowController初期化
        controller = _initialize_workflow_controller(issue_number)

        # メタデータ存在チェック
        if not controller.metadata.metadata_path.exists():
            click.echo(f'[ERROR] Workflow not found for Issue #{issue_number}')
            sys.exit(1)

        # メタデータ読み込み
        controller.metadata.load()

        # ワークフロー状態取得
        status_info = controller.get_workflow_status()

        # 状態表示
        click.echo(f'Workflow Status - Issue #{status_info["issue_number"]}')
        click.echo(f'Branch: {status_info["branch_name"]}')
        click.echo(f'\nPhase Status:')

        phases = status_info.get('phases', {})
        for phase_name in controller.PHASE_ORDER:
            phase_info = phases.get(phase_name, {})
            phase_status = phase_info.get('status', 'pending')
            review_result = phase_info.get('review_result', '-')

            status_symbol = {
                'pending': '⊘',
                'in_progress': '▶',
                'completed': '✓',
                'failed': '✗'
            }.get(phase_status, '?')

            click.echo(f'  {status_symbol} {phase_name:20s} {phase_status:12s} {review_result}')

    except ValueError:
        click.echo('[ERROR] Invalid issue number')
        sys.exit(1)
    except Exception as e:
        click.echo(f'[ERROR] Unexpected error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option('--issue', required=True, help='Issue number')
@click.option('--skip-dependency-check', is_flag=True, default=False,
              help='Skip dependency checks')
@click.option('--ignore-dependencies', is_flag=True, default=False,
              help='Show warnings but continue when dependencies are not met')
def resume(issue: str, skip_dependency_check: bool = False, ignore_dependencies: bool = False):
    """ワークフロー再開

    処理内容:
        1. メタデータから最後に実行したフェーズを取得
        2. 次のフェーズからWorkflowController.execute_all_phases()を呼び出し
        3. 実行結果の表示

    例:
        python main.py resume --issue 380
    """
    # オプションの排他性チェック
    if skip_dependency_check and ignore_dependencies:
        click.echo('[ERROR] Options "--skip-dependency-check" and "--ignore-dependencies" are mutually exclusive')
        sys.exit(1)

    try:
        issue_number = int(issue)

        # WorkflowController初期化
        controller = _initialize_workflow_controller(issue_number)

        # メタデータ存在チェック
        if not controller.metadata.metadata_path.exists():
            click.echo(f'[ERROR] Workflow not found for Issue #{issue_number}')
            sys.exit(1)

        # メタデータ読み込み
        controller.metadata.load()

        # 最後に完了したフェーズを検索
        phases = controller.metadata.data.get('phases', {})
        last_completed = None
        for phase_name in controller.PHASE_ORDER:
            phase_info = phases.get(phase_name, {})
            if phase_info.get('status') == 'completed':
                last_completed = phase_name

        # 再開フェーズを決定
        if last_completed is None:
            # 最初から開始
            resume_phase = controller.PHASE_ORDER[0]
            click.echo(f'[INFO] No completed phases found. Starting from: {resume_phase}')
        else:
            # 次のフェーズから開始
            current_index = controller.PHASE_ORDER.index(last_completed)
            if current_index + 1 >= len(controller.PHASE_ORDER):
                click.echo('[INFO] All phases are already completed.')
                sys.exit(0)

            resume_phase = controller.PHASE_ORDER[current_index + 1]
            click.echo(f'[INFO] Last completed: {last_completed}')
            click.echo(f'[INFO] Resuming from: {resume_phase}')

        # 再開実行
        result = controller.execute_all_phases(
            start_from=resume_phase,
            skip_dependency_check=skip_dependency_check,
            ignore_dependencies=ignore_dependencies
        )

        if result['success']:
            click.echo(f'[OK] Workflow resumed and completed successfully')
            click.echo(f'[OK] Completed: {", ".join(result["completed_phases"])}')
        else:
            click.echo(f'[ERROR] Workflow failed at phase: {result["failed_phase"]}')
            click.echo(f'[ERROR] {result["error"]}')
            sys.exit(1)

    except ValueError:
        click.echo('[ERROR] Invalid issue number')
        sys.exit(1)
    except Exception as e:
        click.echo(f'[ERROR] Unexpected error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    cli()
