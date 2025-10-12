"""AI Workflow - CLIエントリーポイント"""
import click
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any
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
from phases.evaluation import EvaluationPhase


def _get_repo_root() -> Path:
    """Gitリポジトリのルートディレクトリを取得"""
    try:
        repo = Repo(search_parent_directories=True)
        return Path(repo.working_dir)
    except Exception:
        # Gitリポジトリが見つからない場合は、カレントディレクトリを返す
        return Path.cwd()


def _get_preset_phases(preset_name: str) -> List[str]:
    """
    プリセット名からフェーズリストを取得

    Args:
        preset_name: プリセット名（例: 'requirements-only'）

    Returns:
        List[str]: フェーズリスト

    Raises:
        ValueError: 不正なプリセット名の場合

    Example:
        >>> phases = _get_preset_phases('design-phase')
        ['requirements', 'design']
    """
    from core.phase_dependencies import PHASE_PRESETS

    if preset_name not in PHASE_PRESETS:
        available_presets = ', '.join(PHASE_PRESETS.keys())
        raise ValueError(
            f"Invalid preset: '{preset_name}'\n"
            f"Available presets: {available_presets}"
        )

    return PHASE_PRESETS[preset_name]


def _load_external_documents(
    requirements_doc: Optional[str],
    design_doc: Optional[str],
    test_scenario_doc: Optional[str],
    metadata_manager: MetadataManager,
    repo_root: Path
) -> Dict[str, str]:
    """
    外部ドキュメントを読み込みメタデータに記録

    Args:
        requirements_doc: 要件定義書のパス
        design_doc: 設計書のパス
        test_scenario_doc: テストシナリオのパス
        metadata_manager: MetadataManagerインスタンス
        repo_root: リポジトリルートパス

    Returns:
        Dict[str, str]: フェーズ名 → ファイルパスのマッピング

    Raises:
        ValueError: バリデーションエラーの場合

    Example:
        >>> docs = _load_external_documents(
        ...     requirements_doc='path/to/requirements.md',
        ...     design_doc=None,
        ...     test_scenario_doc=None,
        ...     metadata_manager=metadata_manager,
        ...     repo_root=repo_root
        ... )
        {'requirements': 'path/to/requirements.md'}
    """
    from core.phase_dependencies import validate_external_document

    external_docs = {}
    doc_mapping = {
        'requirements': requirements_doc,
        'design': design_doc,
        'test_scenario': test_scenario_doc
    }

    for phase_name, doc_path in doc_mapping.items():
        if doc_path:
            # バリデーション
            result = validate_external_document(doc_path, repo_root)

            if not result['valid']:
                error_msg = f"[ERROR] Invalid external document for {phase_name}: {doc_path}\n"
                error_msg += f"[ERROR] Reason: {result['error']}\n"
                error_msg += f"[ERROR]\n"
                error_msg += f"[ERROR] Please ensure:\n"
                error_msg += f"[ERROR]   - File exists and is readable\n"
                error_msg += f"[ERROR]   - File format is .md or .txt\n"
                error_msg += f"[ERROR]   - File size is less than 10MB\n"
                error_msg += f"[ERROR]   - File is within the repository"
                raise ValueError(error_msg)

            external_docs[phase_name] = result['absolute_path']

            # メタデータに記録
            if 'external_documents' not in metadata_manager.data:
                metadata_manager.data['external_documents'] = {}

            metadata_manager.data['external_documents'][phase_name] = result['absolute_path']

            # フェーズステータスを completed に変更
            metadata_manager.update_phase_status(
                phase_name=phase_name,
                status='completed',
                output_file=doc_path
            )

            click.echo(f"[INFO] External document for {phase_name}: {doc_path}")

    # メタデータ保存
    metadata_manager.save()

    return external_docs


def _execute_single_phase(
    phase: str,
    issue: str,
    repo_root: Path,
    metadata_manager: MetadataManager,
    claude_client: ClaudeAgentClient,
    github_client: GitHubClient,
    skip_dependency_check: bool = False,
    ignore_dependencies: bool = False
) -> Dict[str, Any]:
    """
    個別フェーズを実行

    Args:
        phase: フェーズ名
        issue: Issue番号
        repo_root: リポジトリルートパス
        metadata_manager: メタデータマネージャー
        claude_client: Claude Agent SDKクライアント
        github_client: GitHub APIクライアント
        skip_dependency_check: 依存関係チェックをスキップするか（デフォルト: False）
        ignore_dependencies: 依存関係違反を警告のみで許可するか（デフォルト: False）

    Returns:
        Dict[str, Any]: 実行結果
            - success: bool - 成功/失敗
            - review_result: Optional[str] - レビュー結果（PASS/PASS_WITH_SUGGESTIONS/FAIL）
            - error: Optional[str] - エラーメッセージ
    """
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
        'report': ReportPhase,
        'evaluation': EvaluationPhase
    }

    phase_class = phase_classes.get(phase)
    if not phase_class:
        return {
            'success': False,
            'error': f'Unknown phase: {phase}'
        }

    # working_dirはscripts/ai-workflowディレクトリ
    working_dir = repo_root / 'scripts' / 'ai-workflow'

    # フェーズインスタンス生成
    phase_instance = phase_class(
        working_dir=working_dir,
        metadata_manager=metadata_manager,
        claude_client=claude_client,
        github_client=github_client,
        skip_dependency_check=skip_dependency_check,
        ignore_dependencies=ignore_dependencies
    )

    # run()メソッド実行
    success = phase_instance.run()

    # レビュー結果取得
    review_result = metadata_manager.data['phases'].get(phase, {}).get('review_result')

    # 結果返却
    return {
        'success': success,
        'review_result': review_result,
        'error': None if success else 'Phase execution failed'
    }


def _generate_success_summary(
    phases: list,
    results: Dict[str, Dict[str, Any]],
    start_time: float,
    metadata_manager: MetadataManager
) -> Dict[str, Any]:
    """
    成功時の実行サマリーを生成

    Args:
        phases: フェーズリスト
        results: 各フェーズの実行結果
        start_time: 開始時刻（time.time()）
        metadata_manager: メタデータマネージャー

    Returns:
        Dict[str, Any]: 実行結果サマリー
    """
    # 総実行時間計算
    total_duration = time.time() - start_time

    # 総コスト取得
    total_cost = metadata_manager.data['cost_tracking']['total_cost_usd']

    # サマリー表示
    click.echo(f"\n{'='*60}")
    click.echo(f"Execution Summary - Issue #{metadata_manager.data['issue_number']}")
    click.echo(f"{'='*60}\n")

    click.echo(f"Total Phases: {len(phases)}")
    click.echo(f"✓ Completed: {len(phases)}")
    click.echo(f"✗ Failed: 0\n")

    click.echo("Phase Results:")
    for i, phase in enumerate(phases, 1):
        review_result = results[phase].get('review_result', 'N/A')
        click.echo(f"  {i}. {phase:20s} ✓ {review_result}")

    click.echo(f"\nTotal Execution Time: {total_duration // 60:.0f}m {total_duration % 60:.0f}s")
    click.echo(f"Total Cost: ${total_cost:.2f} USD\n")

    click.echo("All phases completed successfully!")
    click.echo(f"{'='*60}\n")

    # 結果返却
    return {
        'success': True,
        'completed_phases': phases,
        'failed_phase': None,
        'error': None,
        'results': results,
        'total_duration': total_duration,
        'total_cost': total_cost
    }


def _generate_failure_summary(
    completed_phases: list,
    failed_phase: str,
    error: str,
    results: Dict[str, Dict[str, Any]],
    start_time: float
) -> Dict[str, Any]:
    """
    失敗時の実行サマリーを生成

    Args:
        completed_phases: 完了したフェーズリスト
        failed_phase: 失敗したフェーズ
        error: エラーメッセージ
        results: 各フェーズの実行結果
        start_time: 開始時刻（time.time()）

    Returns:
        Dict[str, Any]: 実行結果サマリー
    """
    # 総実行時間計算
    total_duration = time.time() - start_time

    # サマリー表示
    click.echo(f"\n{'='*60}")
    click.echo(f"Execution Summary - FAILED")
    click.echo(f"{'='*60}\n")

    total_phases = len(completed_phases)
    completed_count = sum(1 for p in completed_phases if results.get(p, {}).get('success', False))

    click.echo(f"Total Phases: {total_phases}")
    click.echo(f"✓ Completed: {completed_count}")
    click.echo(f"✗ Failed: 1")
    click.echo(f"⊘ Skipped: {10 - total_phases}\n")

    click.echo("Phase Results:")
    all_phases = ['planning', 'requirements', 'design', 'test_scenario', 'implementation',
                  'test_implementation', 'testing', 'documentation', 'report', 'evaluation']

    for i, phase in enumerate(all_phases, 1):
        if phase in results:
            result = results[phase]
            if result.get('success', False):
                review_result = result.get('review_result', 'PASS')
                click.echo(f"  {i}. {phase:20s} ✓ {review_result}")
            else:
                click.echo(f"  {i}. {phase:20s} ✗ FAIL")
        else:
            click.echo(f"  {i}. {phase:20s} ⊘ SKIPPED")

    click.echo(f"\nFailed Phase: {failed_phase}")
    click.echo(f"Error: {error}\n")

    click.echo(f"Total Execution Time: {total_duration // 60:.0f}m {total_duration % 60:.0f}s")
    click.echo(f"{'='*60}\n")

    # 結果返却
    return {
        'success': False,
        'completed_phases': completed_phases,
        'failed_phase': failed_phase,
        'error': error,
        'results': results,
        'total_duration': total_duration
    }


def execute_phases_from(
    start_phase: str,
    issue: str,
    repo_root: Path,
    metadata_manager: MetadataManager,
    claude_client: ClaudeAgentClient,
    github_client: GitHubClient,
    skip_dependency_check: bool = False,
    ignore_dependencies: bool = False
) -> Dict[str, Any]:
    """
    指定フェーズから全フェーズを順次実行（レジューム用）

    Args:
        start_phase: 開始フェーズ名
        issue: Issue番号（文字列）
        repo_root: リポジトリルートパス
        metadata_manager: メタデータマネージャー
        claude_client: Claude Agent SDKクライアント
        github_client: GitHub APIクライアント

    Returns:
        Dict[str, Any]: 実行結果サマリー（execute_all_phases()と同じ形式）
    """
    # フェーズリスト定義
    all_phases = [
        'planning',
        'requirements',
        'design',
        'test_scenario',
        'implementation',
        'test_implementation',
        'testing',
        'documentation',
        'report',
        'evaluation'
    ]

    # 開始フェーズのインデックス取得
    if start_phase not in all_phases:
        raise ValueError(f"Unknown phase: {start_phase}")

    start_index = all_phases.index(start_phase)
    phases = all_phases[start_index:]  # 開始フェーズから最後まで

    # 初期化
    results = {}
    start_time = time.time()
    total_phases = len(phases)

    # ヘッダー表示
    click.echo(f"\n{'='*60}")
    click.echo(f"AI Workflow Resume Execution - Issue #{issue}")
    click.echo(f"Starting from: {start_phase}")
    click.echo(f"{'='*60}\n")

    # フェーズループ（execute_all_phases()と同じロジック）
    for i, phase in enumerate(phases, 1):
        # 進捗表示
        click.echo(f"\n{'='*60}")
        click.echo(f"Progress: [{i}/{total_phases}] Phase: {phase}")
        click.echo(f"{'='*60}\n")

        try:
            # フェーズ実行
            phase_result = _execute_single_phase(
                phase=phase,
                issue=issue,
                repo_root=repo_root,
                metadata_manager=metadata_manager,
                claude_client=claude_client,
                github_client=github_client,
                skip_dependency_check=skip_dependency_check,
                ignore_dependencies=ignore_dependencies
            )

            # 結果記録
            results[phase] = phase_result

            # 成功チェック
            if not phase_result.get('success', False):
                # フェーズ失敗 → 停止
                click.echo(f"\n[ERROR] Phase '{phase}' failed. Stopping workflow.")
                return _generate_failure_summary(
                    completed_phases=list(results.keys()),
                    failed_phase=phase,
                    error=phase_result.get('error', 'Unknown error'),
                    results=results,
                    start_time=start_time
                )

        except Exception as e:
            # 例外発生 → 停止
            click.echo(f"\n[ERROR] Exception in phase '{phase}': {e}")
            import traceback
            traceback.print_exc()

            results[phase] = {'success': False, 'error': str(e)}
            return _generate_failure_summary(
                completed_phases=list(results.keys()),
                failed_phase=phase,
                error=str(e),
                results=results,
                start_time=start_time
            )

    # 成功サマリー生成
    return _generate_success_summary(
        phases=phases,
        results=results,
        start_time=start_time,
        metadata_manager=metadata_manager
    )


def execute_all_phases(
    issue: str,
    repo_root: Path,
    metadata_manager: MetadataManager,
    claude_client: ClaudeAgentClient,
    github_client: GitHubClient,
    skip_dependency_check: bool = False,
    ignore_dependencies: bool = False
) -> Dict[str, Any]:
    """
    全フェーズを順次実行

    Args:
        issue: Issue番号（文字列）
        repo_root: リポジトリルートパス
        metadata_manager: メタデータマネージャー
        claude_client: Claude Agent SDKクライアント
        github_client: GitHub APIクライアント

    Returns:
        Dict[str, Any]: 実行結果サマリー
            - success: bool - 全フェーズが成功したか
            - completed_phases: List[str] - 完了したフェーズ一覧
            - failed_phase: Optional[str] - 失敗したフェーズ（成功時はNone）
            - error: Optional[str] - エラーメッセージ（成功時はNone）
            - results: Dict[str, Dict[str, Any]] - 各フェーズの実行結果
            - total_duration: float - 総実行時間（秒）
            - total_cost: float - 総コスト（USD）
    """
    # フェーズリスト定義
    phases = [
        'planning',
        'requirements',
        'design',
        'test_scenario',
        'implementation',
        'test_implementation',
        'testing',
        'documentation',
        'report',
        'evaluation'
    ]

    # 初期化
    results = {}
    start_time = time.time()
    total_phases = len(phases)

    # ヘッダー表示
    click.echo(f"\n{'='*60}")
    click.echo(f"AI Workflow Full Execution - Issue #{issue}")
    click.echo(f"{'='*60}\n")

    # フェーズループ
    for i, phase in enumerate(phases, 1):
        # 進捗表示
        click.echo(f"\n{'='*60}")
        click.echo(f"Progress: [{i}/{total_phases}] Phase: {phase}")
        click.echo(f"{'='*60}\n")

        try:
            # フェーズ実行
            phase_result = _execute_single_phase(
                phase=phase,
                issue=issue,
                repo_root=repo_root,
                metadata_manager=metadata_manager,
                claude_client=claude_client,
                github_client=github_client,
                skip_dependency_check=skip_dependency_check,
                ignore_dependencies=ignore_dependencies
            )

            # 結果記録
            results[phase] = phase_result

            # 成功チェック
            if not phase_result.get('success', False):
                # フェーズ失敗 → 停止
                click.echo(f"\n[ERROR] Phase '{phase}' failed. Stopping workflow.")
                return _generate_failure_summary(
                    completed_phases=list(results.keys()),
                    failed_phase=phase,
                    error=phase_result.get('error', 'Unknown error'),
                    results=results,
                    start_time=start_time
                )

        except Exception as e:
            # 例外発生 → 停止
            click.echo(f"\n[ERROR] Exception in phase '{phase}': {e}")
            import traceback
            traceback.print_exc()

            results[phase] = {'success': False, 'error': str(e)}
            return _generate_failure_summary(
                completed_phases=list(results.keys()),
                failed_phase=phase,
                error=str(e),
                results=results,
                start_time=start_time
            )

    # 成功サマリー生成
    return _generate_success_summary(
        phases=phases,
        results=results,
        start_time=start_time,
        metadata_manager=metadata_manager
    )


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

    # ━━━ 新規追加: commit & push & PR作成 ━━━
    try:
        # GitManagerインスタンス生成（metadata_managerを使用）
        from core.metadata_manager import MetadataManager

        metadata_manager = MetadataManager(metadata_path)
        git_manager = GitManager(
            repo_path=repo_root,
            metadata_manager=metadata_manager
        )

        # metadata.jsonをcommit
        click.echo('[INFO] Committing metadata.json...')
        commit_result = git_manager.commit_phase_output(
            phase_name='planning',  # Phase 0 = planning
            status='completed',
            review_result='N/A'
        )

        if not commit_result.get('success'):
            click.echo(f"[WARNING] Commit failed. PR will not be created: {commit_result.get('error')}")
            return

        click.echo(f"[OK] Commit successful: {commit_result.get('commit_hash', 'N/A')[:7]}")

        # リモートにpush
        click.echo('[INFO] Pushing to remote...')
        push_result = git_manager.push_to_remote()

        if not push_result.get('success'):
            click.echo(f"[WARNING] Push failed. PR will not be created: {push_result.get('error')}")
            return

        click.echo(f"[OK] Push successful")

        # GitHubClientインスタンス生成
        github_token = os.getenv('GITHUB_TOKEN')
        github_repository = os.getenv('GITHUB_REPOSITORY')

        if not github_token or not github_repository:
            click.echo('[WARNING] GITHUB_TOKEN or GITHUB_REPOSITORY not set. PR creation skipped.')
            click.echo('[INFO] You can create PR manually: gh pr create --draft')
            return

        github_client = GitHubClient(token=github_token, repository=github_repository)

        # 既存PRチェック
        click.echo('[INFO] Checking for existing PR...')
        existing_pr = github_client.check_existing_pr(
            head=branch_name,
            base='main'
        )

        if existing_pr:
            click.echo(f"[WARNING] PR already exists: {existing_pr['pr_url']}")
            click.echo('[INFO] Workflow initialization completed (PR creation skipped)')
            return

        # ドラフトPR作成
        click.echo('[INFO] Creating draft PR...')
        pr_title = f"[AI-Workflow] Issue #{issue_number}"
        pr_body = github_client._generate_pr_body_template(
            issue_number=int(issue_number),
            branch_name=branch_name
        )

        pr_result = github_client.create_pull_request(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base='main',
            draft=True
        )

        if pr_result.get('success'):
            click.echo(f"[OK] Draft PR created: {pr_result['pr_url']}")
            click.echo(f"[OK] Workflow initialization completed successfully")
        else:
            click.echo(f"[WARNING] PR creation failed: {pr_result.get('error')}")
            click.echo('[INFO] Workflow initialization completed (PR creation failed)')

    except Exception as e:
        click.echo(f"[ERROR] Unexpected error during PR creation: {e}")
        import traceback
        traceback.print_exc()
        click.echo('[INFO] Workflow initialization completed (PR creation failed)')
    # ━━━ 新規追加ここまで ━━━


@cli.command()
@click.option('--phase', required=False,
              type=click.Choice(['all', 'planning', 'requirements', 'design', 'test_scenario',
                                'implementation', 'test_implementation', 'testing',
                                'documentation', 'report', 'evaluation']))
@click.option('--issue', required=True, help='Issue number')
@click.option('--git-user', help='Git commit user name')
@click.option('--git-email', help='Git commit user email')
@click.option('--force-reset', is_flag=True, default=False,
              help='Clear metadata and restart from Phase 1')
@click.option('--skip-dependency-check', is_flag=True, default=False,
              help='Skip all dependency checks')
@click.option('--ignore-dependencies', is_flag=True, default=False,
              help='Show warnings but continue when dependencies are not met')
@click.option('--preset', type=click.Choice(['requirements-only', 'design-phase',
                                             'implementation-phase', 'full-workflow']),
              help='Execute preset workflow')
@click.option('--requirements-doc', type=str, help='External requirements document path')
@click.option('--design-doc', type=str, help='External design document path')
@click.option('--test-scenario-doc', type=str, help='External test scenario document path')
def execute(phase: str, issue: str, git_user: str = None, git_email: str = None,
            force_reset: bool = False, skip_dependency_check: bool = False,
            ignore_dependencies: bool = False, preset: Optional[str] = None,
            requirements_doc: Optional[str] = None, design_doc: Optional[str] = None,
            test_scenario_doc: Optional[str] = None):
    """フェーズ実行"""
    # ━━━ 新規追加: オプションの排他性チェック ━━━
    # --preset と --phase の排他性
    if preset and phase:
        click.echo("[ERROR] Options '--preset' and '--phase' are mutually exclusive")
        click.echo("[ERROR] Please specify only one of them")
        sys.exit(1)

    # --skip-dependency-check と --ignore-dependencies の排他性
    if skip_dependency_check and ignore_dependencies:
        click.echo("[ERROR] Options '--skip-dependency-check' and '--ignore-dependencies' are mutually exclusive")
        click.echo("[ERROR] Please specify only one of them")
        sys.exit(1)

    # --preset または --phase のどちらかが必須
    if not preset and not phase:
        click.echo("[ERROR] Either '--preset' or '--phase' option is required")
        sys.exit(1)
    # ━━━ 新規追加ここまで ━━━

    # CLIオプションが指定されている場合、環境変数に設定（最優先）
    if git_user:
        os.environ['GIT_COMMIT_USER_NAME'] = git_user
        click.echo(f'[INFO] Git user name set from CLI option: {git_user}')

    if git_email:
        os.environ['GIT_COMMIT_USER_EMAIL'] = git_email
        click.echo(f'[INFO] Git user email set from CLI option: {git_email}')

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

    # ━━━ 新規追加: 外部ドキュメント処理 ━━━
    if requirements_doc or design_doc or test_scenario_doc:
        try:
            _load_external_documents(
                requirements_doc=requirements_doc,
                design_doc=design_doc,
                test_scenario_doc=test_scenario_doc,
                metadata_manager=metadata_manager,
                repo_root=repo_root
            )
        except ValueError as e:
            click.echo(str(e))
            sys.exit(1)
    # ━━━ 新規追加ここまで ━━━

    # ━━━ 新規追加: プリセット処理 ━━━
    if preset:
        try:
            phase_list = _get_preset_phases(preset)
            click.echo(f'[INFO] Preset "{preset}" selected: {", ".join(phase_list)}')
            # プリセットの場合、phase を 'all' として扱い、phase_list を使用
            phase = 'all'
        except ValueError as e:
            click.echo(str(e))
            sys.exit(1)
    # ━━━ 新規追加ここまで ━━━

    # ━━━ 新規追加: レジューム機能統合 ━━━
    if phase == 'all':
        click.echo('[INFO] Starting all phases execution')

        # ResumeManagerインスタンス生成
        from utils.resume import ResumeManager
        resume_manager = ResumeManager(metadata_manager)

        # --force-reset フラグチェック
        if force_reset:
            click.echo('[INFO] --force-reset specified. Restarting from Phase 1...')
            resume_manager.reset()

            # 新規ワークフローとして実行
            try:
                result = execute_all_phases(
                    issue=issue,
                    repo_root=repo_root,
                    metadata_manager=metadata_manager,
                    claude_client=claude_client,
                    github_client=github_client,
                    skip_dependency_check=skip_dependency_check,
                    ignore_dependencies=ignore_dependencies
                )

                if result['success']:
                    click.echo('[OK] All phases completed successfully')
                    sys.exit(0)
                else:
                    click.echo(f"[ERROR] Workflow failed at phase: {result['failed_phase']}")
                    click.echo(f"[ERROR] Error: {result['error']}")
                    sys.exit(1)

            except Exception as e:
                click.echo(f'[ERROR] {e}')
                import traceback
                traceback.print_exc()
                sys.exit(1)

        # レジューム可能性チェック
        try:
            can_resume = resume_manager.can_resume()
        except json.JSONDecodeError as e:
            # メタデータJSON破損
            click.echo('[WARNING] metadata.json is corrupted. Starting as new workflow.')
            click.echo(f'[DEBUG] Error: {e}')
            can_resume = False
        except Exception as e:
            # その他のエラー
            click.echo(f'[ERROR] Failed to check resume status: {e}')
            import traceback
            traceback.print_exc()
            sys.exit(1)

        if can_resume:
            resume_phase = resume_manager.get_resume_phase()

            if resume_phase is None:
                # 全フェーズ完了済み
                click.echo('[INFO] All phases are already completed.')
                click.echo('[INFO] To re-run, use --force-reset flag.')
                sys.exit(0)

            # レジューム実行
            status = resume_manager.get_status_summary()
            click.echo('[INFO] Existing workflow detected.')
            if status['completed']:
                click.echo(f"[INFO] Completed phases: {', '.join(status['completed'])}")
            if status['failed']:
                click.echo(f"[INFO] Failed phases: {', '.join(status['failed'])}")
            if status['in_progress']:
                click.echo(f"[INFO] In-progress phases: {', '.join(status['in_progress'])}")
            click.echo(f"[INFO] Resuming from phase: {resume_phase}")

            # レジューム開始フェーズから実行
            try:
                result = execute_phases_from(
                    start_phase=resume_phase,
                    issue=issue,
                    repo_root=repo_root,
                    metadata_manager=metadata_manager,
                    claude_client=claude_client,
                    github_client=github_client,
                    skip_dependency_check=skip_dependency_check,
                    ignore_dependencies=ignore_dependencies
                )

                if result['success']:
                    click.echo('[OK] All phases completed successfully')
                    sys.exit(0)
                else:
                    click.echo(f"[ERROR] Workflow failed at phase: {result['failed_phase']}")
                    click.echo(f"[ERROR] Error: {result['error']}")
                    sys.exit(1)

            except Exception as e:
                click.echo(f'[ERROR] {e}')
                import traceback
                traceback.print_exc()
                sys.exit(1)

        else:
            # 新規ワークフロー（メタデータ不存在 or 全フェーズpending）
            click.echo('[INFO] Starting new workflow.')
            try:
                result = execute_all_phases(
                    issue=issue,
                    repo_root=repo_root,
                    metadata_manager=metadata_manager,
                    claude_client=claude_client,
                    github_client=github_client
                )

                if result['success']:
                    click.echo('[OK] All phases completed successfully')
                    sys.exit(0)
                else:
                    click.echo(f"[ERROR] Workflow failed at phase: {result['failed_phase']}")
                    click.echo(f"[ERROR] Error: {result['error']}")
                    sys.exit(1)

            except Exception as e:
                click.echo(f'[ERROR] {e}')
                import traceback
                traceback.print_exc()
                sys.exit(1)
    # ━━━ 新規追加ここまで ━━━

    # ━━━ 既存の個別フェーズ実行 ━━━
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
        'report': ReportPhase,
        'evaluation': EvaluationPhase
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
            github_client=github_client,
            skip_dependency_check=skip_dependency_check,
            ignore_dependencies=ignore_dependencies
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
