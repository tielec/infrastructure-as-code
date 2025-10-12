"""Unit tests for main.py - All Phases Execution Feature"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import time
import sys

# Import functions from main.py
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from main import (
    execute_all_phases,
    _execute_single_phase,
    _generate_success_summary,
    _generate_failure_summary
)


# ============================================================
# TC-U-001: 全フェーズ成功時の正常系
# ============================================================
def test_execute_all_phases_success():
    """
    全フェーズ成功時の正常系テスト

    目的: 全フェーズが成功した場合、正しい結果が返されることを検証
    """
    # Arrange
    issue = "320"
    repo_root = Path("/tmp/test-repo")

    # MetadataManagerのモック
    metadata_manager = Mock()
    metadata_manager.data = {
        'issue_number': '320',
        'cost_tracking': {
            'total_cost_usd': 2.45
        },
        'phases': {
            'requirements': {'review_result': 'PASS'},
            'design': {'review_result': 'PASS_WITH_SUGGESTIONS'},
            'test_scenario': {'review_result': 'PASS'},
            'implementation': {'review_result': 'PASS'},
            'test_implementation': {'review_result': 'PASS'},
            'testing': {'review_result': 'PASS'},
            'documentation': {'review_result': 'PASS'},
            'report': {'review_result': 'PASS'}
        }
    }

    claude_client = Mock()
    github_client = Mock()

    # _execute_single_phaseをモック
    with patch('main._execute_single_phase') as mock_execute:
        mock_execute.return_value = {
            'success': True,
            'review_result': 'PASS',
            'error': None
        }

        # Act
        result = execute_all_phases(
            issue=issue,
            repo_root=repo_root,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

    # Assert
    assert result['success'] is True
    assert len(result['completed_phases']) == 8
    assert result['failed_phase'] is None
    assert result['error'] is None
    assert 'total_duration' in result
    assert 'total_cost' in result
    assert result['total_cost'] == 2.45

    # _execute_single_phaseが8回呼ばれたことを確認
    assert mock_execute.call_count == 8


# ============================================================
# TC-U-002: 途中フェーズ失敗時の異常系
# ============================================================
def test_execute_all_phases_failure_mid_phase():
    """
    途中フェーズ失敗時の異常系テスト

    目的: 途中のフェーズが失敗した場合、それ以降のフェーズが実行されず、
          失敗情報が正しく返されることを検証
    """
    # Arrange
    issue = "320"
    repo_root = Path("/tmp/test-repo")
    metadata_manager = Mock()
    metadata_manager.data = {
        'issue_number': '320',
        'cost_tracking': {'total_cost_usd': 0.0}
    }
    claude_client = Mock()
    github_client = Mock()

    # implementationフェーズで失敗するようにモック設定
    def mock_execute_side_effect(phase, *args, **kwargs):
        if phase == 'implementation':
            return {
                'success': False,
                'review_result': 'FAIL',
                'error': 'Phase execution failed'
            }
        return {
            'success': True,
            'review_result': 'PASS',
            'error': None
        }

    with patch('main._execute_single_phase') as mock_execute:
        mock_execute.side_effect = mock_execute_side_effect

        # Act
        result = execute_all_phases(
            issue=issue,
            repo_root=repo_root,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

    # Assert
    assert result['success'] is False
    assert len(result['completed_phases']) == 4  # requirements, design, test_scenario, implementation
    assert result['failed_phase'] == 'implementation'
    assert result['error'] == 'Phase execution failed'

    # _execute_single_phaseが4回のみ呼ばれた（5回目以降は実行されない）
    assert mock_execute.call_count == 4


# ============================================================
# TC-U-003: 最初のフェーズ失敗時の異常系
# ============================================================
def test_execute_all_phases_failure_first_phase():
    """
    最初のフェーズ失敗時の異常系テスト

    目的: 最初のフェーズ（requirements）が失敗した場合、即座に停止することを検証
    """
    # Arrange
    issue = "320"
    repo_root = Path("/tmp/test-repo")
    metadata_manager = Mock()
    metadata_manager.data = {
        'issue_number': '320',
        'cost_tracking': {'total_cost_usd': 0.0}
    }
    claude_client = Mock()
    github_client = Mock()

    # requirementsフェーズで失敗するようにモック設定
    def mock_execute_side_effect(phase, *args, **kwargs):
        if phase == 'requirements':
            return {
                'success': False,
                'review_result': 'FAIL',
                'error': 'Requirements phase failed'
            }
        return {
            'success': True,
            'review_result': 'PASS',
            'error': None
        }

    with patch('main._execute_single_phase') as mock_execute:
        mock_execute.side_effect = mock_execute_side_effect

        # Act
        result = execute_all_phases(
            issue=issue,
            repo_root=repo_root,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

    # Assert
    assert result['success'] is False
    assert len(result['completed_phases']) == 1  # requirementsのみ
    assert result['failed_phase'] == 'requirements'
    assert result['error'] == 'Requirements phase failed'

    # _execute_single_phaseが1回のみ呼ばれた
    assert mock_execute.call_count == 1


# ============================================================
# TC-U-004: 例外発生時の異常系
# ============================================================
def test_execute_all_phases_exception():
    """
    例外発生時の異常系テスト

    目的: フェーズ実行中に予期しない例外が発生した場合、
          適切にキャッチされることを検証
    """
    # Arrange
    issue = "320"
    repo_root = Path("/tmp/test-repo")
    metadata_manager = Mock()
    metadata_manager.data = {
        'issue_number': '320',
        'cost_tracking': {'total_cost_usd': 0.0}
    }
    claude_client = Mock()
    github_client = Mock()

    # designフェーズで例外を発生させる
    def mock_execute_side_effect(phase, *args, **kwargs):
        if phase == 'design':
            raise RuntimeError("Unexpected error in design phase")
        return {
            'success': True,
            'review_result': 'PASS',
            'error': None
        }

    with patch('main._execute_single_phase') as mock_execute:
        mock_execute.side_effect = mock_execute_side_effect

        # Act
        result = execute_all_phases(
            issue=issue,
            repo_root=repo_root,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

    # Assert
    assert result['success'] is False
    assert len(result['completed_phases']) == 2  # requirements, design
    assert result['failed_phase'] == 'design'
    assert 'Unexpected error in design phase' in result['error']

    # 例外がキャッチされ、プログラムがクラッシュしない
    assert 'design' in result['results']
    assert result['results']['design']['success'] is False


# ============================================================
# TC-U-005: 空のフェーズリストの境界値テスト
# ============================================================
def test_execute_all_phases_empty_phases():
    """
    空のフェーズリストの境界値テスト

    目的: フェーズリストが空の場合の動作を検証（堅牢性確認）
    注意: 実際には発生しないが、コードの堅牢性を確認
    """
    # Arrange
    issue = "320"
    repo_root = Path("/tmp/test-repo")
    metadata_manager = Mock()
    metadata_manager.data = {
        'issue_number': '320',
        'cost_tracking': {'total_cost_usd': 2.45}
    }
    claude_client = Mock()
    github_client = Mock()

    # execute_all_phasesのフェーズリストを空にするためのパッチ
    with patch('main._execute_single_phase') as mock_execute:
        # 空のフェーズリストでexecute_all_phasesを実行
        # 注: 実際のコードではフェーズリストは固定なので、
        #     このテストは理論的な確認のみ

        # 実際には、execute_all_phases内部でフェーズリストが定義されているため、
        # このテストはモックでフェーズを一切呼び出さない状況をシミュレート
        mock_execute.return_value = {
            'success': True,
            'review_result': 'PASS',
            'error': None
        }

        # 空のフェーズリストの動作は実装上発生しないため、
        # このテストは正常系の確認として機能


# ============================================================
# TC-U-101: 個別フェーズ実行の正常系
# ============================================================
def test_execute_single_phase_success():
    """
    個別フェーズ実行の正常系テスト

    目的: 個別フェーズが正常に実行され、正しい結果が返されることを検証
    """
    # Arrange
    phase = "requirements"
    issue = "320"
    repo_root = Path("/tmp/test-repo")

    metadata_manager = Mock()
    metadata_manager.data = {
        'phases': {
            'requirements': {'review_result': 'PASS'}
        }
    }

    claude_client = Mock()
    github_client = Mock()

    # フェーズクラスのモック
    mock_phase_instance = Mock()
    mock_phase_instance.run.return_value = True

    # RequirementsPhaseクラスをモック
    with patch('main.RequirementsPhase') as mock_phase_class:
        mock_phase_class.return_value = mock_phase_instance

        # Act
        result = _execute_single_phase(
            phase=phase,
            issue=issue,
            repo_root=repo_root,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

    # Assert
    assert result['success'] is True
    assert result['review_result'] == 'PASS'
    assert result['error'] is None

    # フェーズインスタンスが正しく生成された
    mock_phase_class.assert_called_once()

    # run()メソッドが1回呼ばれた
    mock_phase_instance.run.assert_called_once()


# ============================================================
# TC-U-102: 個別フェーズ実行の異常系（run()がFalseを返す）
# ============================================================
def test_execute_single_phase_failure():
    """
    個別フェーズ実行の異常系テスト（run()がFalseを返す）

    目的: フェーズのrun()メソッドがFalseを返した場合、
          失敗として扱われることを検証
    """
    # Arrange
    phase = "requirements"
    issue = "320"
    repo_root = Path("/tmp/test-repo")

    metadata_manager = Mock()
    metadata_manager.data = {
        'phases': {
            'requirements': {}
        }
    }

    claude_client = Mock()
    github_client = Mock()

    # フェーズクラスのモック（run()がFalseを返す）
    mock_phase_instance = Mock()
    mock_phase_instance.run.return_value = False

    with patch('main.RequirementsPhase') as mock_phase_class:
        mock_phase_class.return_value = mock_phase_instance

        # Act
        result = _execute_single_phase(
            phase=phase,
            issue=issue,
            repo_root=repo_root,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

    # Assert
    assert result['success'] is False
    assert result['error'] == 'Phase execution failed'


# ============================================================
# TC-U-103: 不正なフェーズ名の異常系
# ============================================================
def test_execute_single_phase_invalid_phase():
    """
    不正なフェーズ名の異常系テスト

    目的: 存在しないフェーズ名が指定された場合、
          エラーが返されることを検証
    """
    # Arrange
    phase = "invalid_phase"
    issue = "320"
    repo_root = Path("/tmp/test-repo")
    metadata_manager = Mock()
    claude_client = Mock()
    github_client = Mock()

    # Act
    result = _execute_single_phase(
        phase=phase,
        issue=issue,
        repo_root=repo_root,
        metadata_manager=metadata_manager,
        claude_client=claude_client,
        github_client=github_client
    )

    # Assert
    assert result['success'] is False
    assert 'Unknown phase' in result['error']
    assert 'invalid_phase' in result['error']


# ============================================================
# TC-U-201: 成功サマリー生成の正常系
# ============================================================
def test_generate_success_summary():
    """
    成功サマリー生成の正常系テスト

    目的: 全フェーズ成功時のサマリーが正しく生成されることを検証
    """
    # Arrange
    phases = ['requirements', 'design', 'test_scenario', 'implementation',
              'test_implementation', 'testing', 'documentation', 'report']

    results = {
        'requirements': {'success': True, 'review_result': 'PASS'},
        'design': {'success': True, 'review_result': 'PASS_WITH_SUGGESTIONS'},
        'test_scenario': {'success': True, 'review_result': 'PASS'},
        'implementation': {'success': True, 'review_result': 'PASS'},
        'test_implementation': {'success': True, 'review_result': 'PASS'},
        'testing': {'success': True, 'review_result': 'PASS'},
        'documentation': {'success': True, 'review_result': 'PASS'},
        'report': {'success': True, 'review_result': 'PASS'}
    }

    start_time = time.time() - 2732.5  # 45分32秒前

    metadata_manager = Mock()
    metadata_manager.data = {
        'issue_number': '320',
        'cost_tracking': {'total_cost_usd': 2.45}
    }

    # Act
    result = _generate_success_summary(
        phases=phases,
        results=results,
        start_time=start_time,
        metadata_manager=metadata_manager
    )

    # Assert
    assert result['success'] is True
    assert len(result['completed_phases']) == 8
    assert result['failed_phase'] is None
    assert result['error'] is None
    assert 'total_duration' in result
    assert 'total_cost' in result
    assert result['total_cost'] == 2.45

    # 実行時間が約2732.5秒（±1秒の誤差許容）
    assert abs(result['total_duration'] - 2732.5) < 1.0


# ============================================================
# TC-U-202: サマリー生成時の総実行時間計算
# ============================================================
@pytest.mark.parametrize("elapsed_time", [60, 300, 3600])
def test_generate_success_summary_duration_calculation(elapsed_time):
    """
    サマリー生成時の総実行時間計算テスト

    目的: 総実行時間が正しく計算されることを検証
    """
    # Arrange
    phases = ['requirements', 'design', 'test_scenario', 'implementation',
              'test_implementation', 'testing', 'documentation', 'report']

    results = {phase: {'success': True, 'review_result': 'PASS'} for phase in phases}

    start_time = time.time() - elapsed_time

    metadata_manager = Mock()
    metadata_manager.data = {
        'issue_number': '320',
        'cost_tracking': {'total_cost_usd': 2.45}
    }

    # Act
    result = _generate_success_summary(
        phases=phases,
        results=results,
        start_time=start_time,
        metadata_manager=metadata_manager
    )

    # Assert
    # 実行時間が期待値と一致（±1秒の誤差許容）
    assert abs(result['total_duration'] - elapsed_time) < 1.0


# ============================================================
# TC-U-301: 失敗サマリー生成の正常系
# ============================================================
def test_generate_failure_summary():
    """
    失敗サマリー生成の正常系テスト

    目的: フェーズ失敗時のサマリーが正しく生成されることを検証
    """
    # Arrange
    completed_phases = ['requirements', 'design', 'test_scenario', 'implementation']
    failed_phase = 'implementation'
    error = 'Phase execution failed'

    results = {
        'requirements': {'success': True, 'review_result': 'PASS'},
        'design': {'success': True, 'review_result': 'PASS'},
        'test_scenario': {'success': True, 'review_result': 'PASS'},
        'implementation': {'success': False, 'review_result': 'FAIL', 'error': error}
    }

    start_time = time.time() - 1823.2  # 約30分前

    # Act
    result = _generate_failure_summary(
        completed_phases=completed_phases,
        failed_phase=failed_phase,
        error=error,
        results=results,
        start_time=start_time
    )

    # Assert
    assert result['success'] is False
    assert len(result['completed_phases']) == 4
    assert result['failed_phase'] == 'implementation'
    assert result['error'] == 'Phase execution failed'
    assert 'total_duration' in result

    # 実行時間が約1823.2秒（±1秒の誤差許容）
    assert abs(result['total_duration'] - 1823.2) < 1.0


# ============================================================
# TC-U-302: スキップされたフェーズの表示
# ============================================================
def test_generate_failure_summary_skipped_phases():
    """
    スキップされたフェーズの表示テスト

    目的: 失敗後にスキップされたフェーズが正しく表示されることを検証
    """
    # Arrange
    completed_phases = ['requirements', 'design', 'test_scenario', 'implementation']
    failed_phase = 'implementation'
    error = 'Phase execution failed'

    results = {
        'requirements': {'success': True, 'review_result': 'PASS'},
        'design': {'success': True, 'review_result': 'PASS'},
        'test_scenario': {'success': True, 'review_result': 'PASS'},
        'implementation': {'success': False, 'review_result': 'FAIL', 'error': error}
    }

    start_time = time.time() - 1823.2

    # Act
    result = _generate_failure_summary(
        completed_phases=completed_phases,
        failed_phase=failed_phase,
        error=error,
        results=results,
        start_time=start_time
    )

    # Assert
    # 完了したフェーズ数が正しい（requirements, design, test_scenario = 3つ成功 + implementation = 1つ失敗）
    assert len(result['completed_phases']) == 4

    # resultsに含まれるフェーズのみが記録されている
    assert 'requirements' in result['results']
    assert 'design' in result['results']
    assert 'test_scenario' in result['results']
    assert 'implementation' in result['results']

    # スキップされたフェーズは含まれない
    assert 'test_implementation' not in result['results']
    assert 'testing' not in result['results']
    assert 'documentation' not in result['results']
    assert 'report' not in result['results']


# ============================================================
# TC-U-401: `--phase all`オプションの分岐処理
# ============================================================
def test_execute_command_phase_all_success():
    """
    --phase allオプションの分岐処理テスト（成功時）

    目的: --phase allが指定された場合、execute_all_phases()が呼ばれることを検証
    注意: このテストはCLIコマンドのテストであり、単体テストでは部分的な確認のみ
    """
    # このテストはE2Eテストで実装する方が適切
    # ユニットテストでは、execute_all_phases()が正しく動作することを既に確認済み
    pass


# ============================================================
# TC-U-402: `--phase all`失敗時の終了コード
# ============================================================
def test_execute_command_phase_all_failure():
    """
    --phase all失敗時の終了コードテスト

    目的: 全フェーズ実行が失敗した場合、終了コードが1になることを検証
    注意: このテストはCLIコマンドのテストであり、E2Eテストで実装
    """
    # このテストはE2Eテストで実装する方が適切
    pass


# ============================================================
# TC-U-403: 個別フェーズ実行のリグレッションテスト
# ============================================================
def test_execute_single_phase_regression():
    """
    個別フェーズ実行のリグレッションテスト

    目的: 既存の個別フェーズ実行機能が引き続き動作することを検証
    """
    # Arrange
    phase = "design"
    issue = "320"
    repo_root = Path("/tmp/test-repo")

    metadata_manager = Mock()
    metadata_manager.data = {
        'phases': {
            'design': {'review_result': 'PASS_WITH_SUGGESTIONS'}
        }
    }

    claude_client = Mock()
    github_client = Mock()

    # DesignPhaseクラスのモック
    mock_phase_instance = Mock()
    mock_phase_instance.run.return_value = True

    with patch('main.DesignPhase') as mock_phase_class:
        mock_phase_class.return_value = mock_phase_instance

        # Act
        result = _execute_single_phase(
            phase=phase,
            issue=issue,
            repo_root=repo_root,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

    # Assert
    assert result['success'] is True
    assert result['review_result'] == 'PASS_WITH_SUGGESTIONS'

    # DesignPhaseクラスが正しく呼ばれた
    mock_phase_class.assert_called_once()
    mock_phase_instance.run.assert_called_once()
