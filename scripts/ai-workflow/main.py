"""AI Workflow - CLIエントリーポイント"""
import click
import os
import sys
from pathlib import Path
from git import Repo
from core.workflow_state import WorkflowState, PhaseStatus
from core.metadata_manager import MetadataManager
from core.claude_agent_client import ClaudeAgentClient
from core.github_client import GitHubClient
from phases.planning import PlanningPhase
from phases.requirements import RequirementsPhase
from phases.design import DesignPhase
from phases.test_scenario import TestScenarioPhase
from phases.implementation import ImplementationPhase
from phases.test_implementation import TestImplementationPhase
from phases.testing import TestingPhase
from phases.documentation import DocumentationPhase
from phases.report import ReportPhase


def _get_repo_root() -> Path:
    """Gitリポジトリのルートディレクトリを取得"""
    try:
        repo = Repo(search_parent_directories=True)
        return Path(repo.working_dir)
    except Exception:
        # Gitリポジトリが見つからない場合は、カレントディレクトリを返す
        return Path.cwd()


@click.group()
def cli():
    """AI駆動開発自動化ワークフロー"""
    pass


@cli.command()
@click.option('--issue-url', required=True, help='GitHub Issue URL')
def init(issue_url: str):
    """ワークフロー初期化"""
    # Issue URLからIssue番号を抽出
    issue_number = issue_url.rstrip('/').split('/')[-1]

    # ワークフローディレクトリ作成（リポジトリルート配下）
    repo_root = _get_repo_root()
    workflow_dir = repo_root / '.ai-workflow' / f'issue-{issue_number}'
    metadata_path = workflow_dir / 'metadata.json'

    if metadata_path.exists():
        click.echo(f'[INFO] Workflow already exists for issue {issue_number}')
        click.echo(f'[INFO] Metadata file: {metadata_path}')

        # マイグレーション実行
        click.echo(f'[INFO] Checking metadata.json schema...')
        state = WorkflowState(metadata_path)
        migrated = state.migrate()

        if migrated:
            click.echo(f'[OK] Metadata schema updated successfully')
        else:
            click.echo(f'[INFO] Metadata schema is already up to date')

        return

    # ━━━ 新規追加: ブランチ作成処理 ━━━
    # GitManagerインスタンス生成（一時的なmetadata_managerを使用）
    from core.git_manager import GitManager

    # 一時的なMetadataManagerを作成（issue_numberのみ設定）
    class TempMetadata:
        def __init__(self, issue_number):
            self.data = {'issue_number': issue_number}

    temp_metadata = TempMetadata(issue_number)
    git_manager = GitManager(
        repo_path=repo_root,
        metadata_manager=temp_metadata
    )

    # ブランチ名生成
    branch_name = f'ai-workflow/issue-{issue_number}'

    # ブランチ作成
    result = git_manager.create_branch(branch_name)

    if not result['success']:
        click.echo(f"[ERROR] {result['error']}")
        sys.exit(1)

    click.echo(f"[OK] Branch created and checked out: {result['branch_name']}")
    # ━━━ 新規追加ここまで ━━━

    # WorkflowState初期化
    state = WorkflowState.create_new(
        metadata_path=metadata_path,
        issue_number=issue_number,
        issue_url=issue_url,
        issue_title=f"Issue #{issue_number}"
    )

    click.echo(f'[OK] Workflow initialized: {workflow_dir}')
    click.echo(f'[OK] metadata.json created')


@cli.command()
@click.option('--phase', required=True,
              type=click.Choice(['planning', 'requirements', 'design', 'test_scenario',
                                'implementation', 'test_implementation', 'testing',
                                'documentation', 'report']))
@click.option('--issue', required=True, help='Issue number')
def execute(phase: str, issue: str):
    """フェーズ実行"""
    repo_root = _get_repo_root()
    workflow_dir = repo_root / '.ai-workflow' / f'issue-{issue}'
    metadata_path = workflow_dir / 'metadata.json'

    if not metadata_path.exists():
        click.echo(f'Error: Workflow not found. Run init first.')
        sys.exit(1)

    # ━━━ 新規追加: ブランチ切り替え処理 ━━━
    # クライアント初期化（metadata_managerを先に初期化）
    metadata_manager = MetadataManager(metadata_path)

    from core.git_manager import GitManager
    git_manager = GitManager(
        repo_path=repo_root,
        metadata_manager=metadata_manager
    )

    # ブランチ名生成
    branch_name = f'ai-workflow/issue-{issue}'

    # ブランチ存在チェック
    if not git_manager.branch_exists(branch_name):
        click.echo(f"[ERROR] Branch not found: {branch_name}. Please run 'init' first.")
        sys.exit(1)

    # 現在のブランチ取得
    current_branch = git_manager.get_current_branch()

    # ブランチ切り替え（現在のブランチと異なる場合のみ）
    if current_branch != branch_name:
        result = git_manager.switch_branch(branch_name)

        if not result['success']:
            click.echo(f"[ERROR] {result['error']}")
            sys.exit(1)

        click.echo(f"[INFO] Switched to branch: {result['branch_name']}")
    else:
        click.echo(f"[INFO] Already on branch: {branch_name}")

    # リモートの最新状態を取り込む（non-fast-forward エラーを防ぐため）
    click.echo(f"[INFO] Pulling latest changes from origin/{branch_name}...")
    try:
        git_manager.repo.git.pull('origin', branch_name)
        click.echo(f"[OK] Successfully pulled latest changes")
    except Exception as e:
        click.echo(f"[WARNING] Failed to pull latest changes: {e}")
        click.echo(f"[WARNING] Continuing workflow execution...")
        # pull失敗してもワークフローは続行（conflict等の可能性があるため手動対応が必要）
    # ━━━ 新規追加ここまで ━━━

    # 環境変数チェック
    github_token = os.getenv('GITHUB_TOKEN')
    github_repository = os.getenv('GITHUB_REPOSITORY')

    if not github_token or not github_repository:
        click.echo('Error: GITHUB_TOKEN and GITHUB_REPOSITORY environment variables are required.')
        click.echo('Example:')
        click.echo('  export GITHUB_TOKEN="ghp_..."')
        click.echo('  export GITHUB_REPOSITORY="tielec/infrastructure-as-code"')
        sys.exit(1)

    # クライアント初期化（続き）
    claude_client = ClaudeAgentClient(working_dir=repo_root)
    github_client = GitHubClient(token=github_token, repository=github_repository)

    # フェーズインスタンス生成
    phase_classes = {
        'planning': PlanningPhase,
        'requirements': RequirementsPhase,
        'design': DesignPhase,
        'test_scenario': TestScenarioPhase,
        'implementation': ImplementationPhase,
        'test_implementation': TestImplementationPhase,
        'testing': TestingPhase,
        'documentation': DocumentationPhase,
        'report': ReportPhase
    }

    phase_class = phase_classes.get(phase)
    if not phase_class:
        click.echo(f'Error: Unknown phase: {phase}')
        sys.exit(1)

    # フェーズ実行
    try:
        # working_dirはscripts/ai-workflowディレクトリ（プロンプトファイルの基準パス）
        working_dir = repo_root / 'scripts' / 'ai-workflow'
        phase_instance = phase_class(
            working_dir=working_dir,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

        click.echo(f'[INFO] Starting phase: {phase}')
        success = phase_instance.run()

        if success:
            click.echo(f'[OK] Phase {phase} completed successfully')
        else:
            click.echo(f'[ERROR] Phase {phase} failed. Check GitHub Issue for details.')
            sys.exit(1)

    except Exception as e:
        click.echo(f'[ERROR] {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option('--phase', required=True)
@click.option('--issue', required=True, help='Issue number')
def review(phase: str, issue: str):
    """フェーズレビュー"""
    repo_root = _get_repo_root()
    metadata_path = repo_root / '.ai-workflow' / f'issue-{issue}' / 'metadata.json'

    if not metadata_path.exists():
        click.echo(f'Error: Workflow not found')
        sys.exit(1)

    state = WorkflowState(metadata_path)
    current_status = state.get_phase_status(phase)

    click.echo(f'[OK] Phase {phase} status: {current_status}')


if __name__ == '__main__':
    cli()
