"""AI Workflow - CLIエントリーポイント"""
import click
import os
import sys
from pathlib import Path
from core.workflow_state import WorkflowState, PhaseStatus


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

    # ワークフローディレクトリ作成
    workflow_dir = Path('.ai-workflow') / f'issue-{issue_number}'
    metadata_path = workflow_dir / 'metadata.json'

    if metadata_path.exists():
        click.echo(f'Error: Workflow already exists: {workflow_dir}')
        sys.exit(1)

    # WorkflowState初期化
    state = WorkflowState.create_new(
        metadata_path=metadata_path,
        issue_number=issue_number,
        issue_url=issue_url,
        issue_title=f"Issue #{issue_number}"
    )

    click.echo(f'✓ Workflow initialized: {workflow_dir}')
    click.echo(f'✓ metadata.json created')


@cli.command()
@click.option('--phase', required=True,
              type=click.Choice(['requirements', 'design', 'test_scenario',
                                'implementation', 'testing', 'documentation']))
@click.option('--issue', required=True, help='Issue number')
def execute(phase: str, issue: str):
    """フェーズ実行"""
    metadata_path = Path('.ai-workflow') / f'issue-{issue}' / 'metadata.json'

    if not metadata_path.exists():
        click.echo(f'Error: Workflow not found. Run init first.')
        sys.exit(1)

    state = WorkflowState(metadata_path)
    state.update_phase_status(phase, PhaseStatus.IN_PROGRESS)
    state.save()

    click.echo(f'✓ Phase {phase} started')


@cli.command()
@click.option('--phase', required=True)
@click.option('--issue', required=True, help='Issue number')
def review(phase: str, issue: str):
    """フェーズレビュー"""
    metadata_path = Path('.ai-workflow') / f'issue-{issue}' / 'metadata.json'

    if not metadata_path.exists():
        click.echo(f'Error: Workflow not found')
        sys.exit(1)

    state = WorkflowState(metadata_path)
    current_status = state.get_phase_status(phase)

    click.echo(f'✓ Phase {phase} status: {current_status}')


if __name__ == '__main__':
    cli()
