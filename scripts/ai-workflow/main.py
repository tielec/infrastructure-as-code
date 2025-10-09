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
from phases.requirements import RequirementsPhase
from phases.design import DesignPhase
from phases.test_scenario import TestScenarioPhase
from phases.implementation import ImplementationPhase
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
        click.echo(f'[ERROR] Workflow already exists for issue {issue_number}')
        click.echo(f'[INFO] Metadata file: {metadata_path}')
        sys.exit(1)

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
              type=click.Choice(['requirements', 'design', 'test_scenario',
                                'implementation', 'testing', 'documentation', 'report']))
@click.option('--issue', required=True, help='Issue number')
def execute(phase: str, issue: str):
    """フェーズ実行"""
    repo_root = _get_repo_root()
    workflow_dir = repo_root / '.ai-workflow' / f'issue-{issue}'
    metadata_path = workflow_dir / 'metadata.json'

    if not metadata_path.exists():
        click.echo(f'Error: Workflow not found. Run init first.')
        sys.exit(1)

    # 環境変数チェック
    github_token = os.getenv('GITHUB_TOKEN')
    github_repository = os.getenv('GITHUB_REPOSITORY')

    if not github_token or not github_repository:
        click.echo('Error: GITHUB_TOKEN and GITHUB_REPOSITORY environment variables are required.')
        click.echo('Example:')
        click.echo('  export GITHUB_TOKEN="ghp_..."')
        click.echo('  export GITHUB_REPOSITORY="tielec/infrastructure-as-code"')
        sys.exit(1)

    # クライアント初期化
    metadata_manager = MetadataManager(metadata_path)
    claude_client = ClaudeAgentClient(working_dir=repo_root)
    github_client = GitHubClient(token=github_token, repository=github_repository)

    # フェーズインスタンス生成
    phase_classes = {
        'requirements': RequirementsPhase,
        'design': DesignPhase,
        'test_scenario': TestScenarioPhase,
        'implementation': ImplementationPhase,
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
