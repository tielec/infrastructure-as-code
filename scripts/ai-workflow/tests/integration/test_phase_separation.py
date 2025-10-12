"""Integration Test: Phase 4/5/6の責務分離と依存関係を検証

Issue #324の受け入れ基準を検証するための統合テスト：
- AC-001: Phase 5（test_implementation）が新設されている
- AC-002: Phase 5でテストコードのみが実装される
- AC-003: Phase 4では実コードのみが実装される
- AC-007: metadata.jsonにtest_implementationフェーズが記録される
"""
import pytest
import json
import hashlib
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from core.workflow_state import WorkflowState
from phases.base_phase import BasePhase


class TestPhaseNumbers:
    """フェーズ番号定義のテスト"""

    def test_phase_numbers_correct(self):
        """AC-007: フェーズ番号が正しいことを確認

        テストの意図:
        - PHASE_NUMBERSにtest_implementationが'05'にマッピングされている
        - 既存フェーズの番号が正しく繰り下げられている
        """
        # Given: BasePhaseのPHASE_NUMBERS定義
        expected = {
            'planning': '00',
            'requirements': '01',
            'design': '02',
            'test_scenario': '03',
            'implementation': '04',
            'test_implementation': '05',
            'testing': '06',
            'documentation': '07',
            'report': '08'
        }

        # When: PHASE_NUMBERSを取得
        actual = BasePhase.PHASE_NUMBERS

        # Then: 期待される辞書と一致すること
        assert actual == expected, f"Phase numbers mismatch: {actual}"
        assert actual['test_implementation'] == '05', "test_implementation should be '05'"
        assert actual['testing'] == '06', "testing should be '06' (繰り下げ後)"
        assert actual['documentation'] == '07', "documentation should be '07' (繰り下げ後)"
        assert actual['report'] == '08', "report should be '08' (繰り下げ後)"


class TestMetadataStructure:
    """metadata.json構造のテスト"""

    def test_metadata_includes_test_implementation(self, tmp_path):
        """AC-007: 新規作成されたmetadata.jsonにtest_implementationが記録されることを確認

        テストの意図:
        - WorkflowState.create_new()で作成されたmetadata.jsonに'test_implementation'フェーズが含まれる
        - フェーズの順序が正しい（planning → ... → test_implementation → testing → ...）
        - test_implementationフェーズのステータスが'pending'である
        """
        # Given: 新規metadata.jsonのパス
        metadata_path = tmp_path / 'metadata.json'

        # When: WorkflowState.create_new()で新規metadata.jsonを作成
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='324',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/324',
            issue_title='[FEATURE] 実装フェーズとテストコード実装フェーズの分離'
        )

        # Then: phases辞書にtest_implementationが存在する
        assert 'test_implementation' in state.data['phases'], \
            "test_implementation phase should exist in metadata.json"

        # Then: test_implementationフェーズのステータスがpending
        assert state.data['phases']['test_implementation']['status'] == 'pending', \
            "test_implementation status should be 'pending'"

        # Then: フェーズの順序が正しい
        expected_order = [
            'planning', 'requirements', 'design', 'test_scenario',
            'implementation', 'test_implementation', 'testing',
            'documentation', 'report'
        ]
        actual_order = list(state.data['phases'].keys())
        assert actual_order == expected_order, \
            f"Phase order mismatch: expected {expected_order}, got {actual_order}"

    def test_metadata_phase_structure(self, tmp_path):
        """test_implementationフェーズの構造が正しいことを確認

        テストの意図:
        - test_implementationフェーズが必要なフィールドを持っている
        - retry_countが0で初期化されている
        """
        # Given: 新規metadata.json
        metadata_path = tmp_path / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='324',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/324',
            issue_title='Test'
        )

        # When: test_implementationフェーズのデータを取得
        test_impl_phase = state.data['phases']['test_implementation']

        # Then: 必要なフィールドが存在する
        assert 'status' in test_impl_phase, "status field should exist"
        assert 'retry_count' in test_impl_phase, "retry_count field should exist"

        # Then: 初期値が正しい
        assert test_impl_phase['status'] == 'pending', "Initial status should be 'pending'"
        assert test_impl_phase['retry_count'] == 0, "Initial retry_count should be 0"


class TestPhase4Responsibility:
    """Phase 4の責務分離テスト"""

    @pytest.mark.skip(reason="Requires actual phase execution with Claude Agent SDK")
    def test_phase4_implementation_only(self, tmp_path):
        """AC-003: Phase 4で実コードのみが実装されることを確認

        テストの意図:
        - Phase 4実行後、実コードファイルが作成される
        - Phase 4実行後、テストファイル（test_*.py等）は作成されない
        - metadata.jsonのフェーズステータスが'completed'になる

        Note: このテストは実際のClaude Agent SDK呼び出しが必要なため、
        E2Eテスト環境でのみ実行可能です。
        """
        # Setup
        workflow_dir = tmp_path / '.ai-workflow' / 'issue-324'
        workflow_dir.mkdir(parents=True)

        # metadata.jsonを作成（Phase 0-3完了状態）
        metadata_path = workflow_dir / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='324',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/324',
            issue_title='[FEATURE] 実装フェーズとテストコード実装フェーズの分離'
        )
        state.update_phase_status('planning', 'completed')
        state.update_phase_status('requirements', 'completed')
        state.update_phase_status('design', 'completed')
        state.update_phase_status('test_scenario', 'completed')

        # Phase 4実行（モックではなく実際の実行が必要）
        # 実装例:
        # from phases.implementation import ImplementationPhase
        # phase = ImplementationPhase(
        #     issue_number='324',
        #     metadata_manager=MetadataManager(metadata_path),
        #     github_client=RealGitHubClient()
        # )
        # result = phase.run()

        # Assert: implementation.md確認
        implementation_md = workflow_dir / '04_implementation' / 'output' / 'implementation.md'
        # assert implementation_md.exists(), "implementation.md should be created"

        # Assert: テストファイルが存在しないこと
        test_patterns = ['test_*.py', '*.test.js', '*.test.ts', '*_test.go']
        for pattern in test_patterns:
            test_files = list(tmp_path.rglob(pattern))
            test_files = [f for f in test_files if '.git' not in str(f) and 'node_modules' not in str(f)]
            # assert len(test_files) == 0, f"Phase 4 should not create test files (pattern: {pattern})"


class TestPhase5Responsibility:
    """Phase 5の責務分離テスト"""

    @pytest.mark.skip(reason="Requires actual phase execution with Claude Agent SDK")
    def test_phase5_test_implementation_only(self, tmp_path):
        """AC-002: Phase 5でテストコードのみが実装されることを確認

        テストの意図:
        - Phase 5実行後、テストファイル（test_*.py等）が作成される
        - Phase 5実行後、実コードファイルは変更されない（チェックサム一致）
        - metadata.jsonのフェーズステータスが'completed'になる

        Note: このテストは実際のClaude Agent SDK呼び出しが必要なため、
        E2Eテスト環境でのみ実行可能です。
        """
        # Setup: Phase 4完了状態
        workflow_dir = tmp_path / '.ai-workflow' / 'issue-324'
        metadata_path = workflow_dir / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='324',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/324',
            issue_title='Test'
        )
        state.update_phase_status('implementation', 'completed')

        # 実コードのチェックサムを記録（実際のプロジェクトの場合）
        # src_files = list(Path('src').rglob('*.py'))
        # checksums_before = {f: hashlib.md5(f.read_bytes()).hexdigest() for f in src_files}

        # Phase 5実行（モックではなく実際の実行が必要）
        # from phases.test_implementation import TestImplementationPhase
        # phase = TestImplementationPhase(...)
        # result = phase.run()

        # Assert: test-implementation.md確認
        test_impl_md = workflow_dir / '05_test_implementation' / 'output' / 'test-implementation.md'
        # assert test_impl_md.exists(), "test-implementation.md should be created"

        # Assert: テストファイルが作成されていること
        test_patterns = ['test_*.py', '*.test.js', '*.test.ts', '*_test.go']
        test_files_found = False
        # for pattern in test_patterns:
        #     test_files = list(tmp_path.rglob(pattern))
        #     if len(test_files) > 0:
        #         test_files_found = True
        #         break
        # assert test_files_found, "Phase 5 should create at least one test file"

        # Assert: 実コードが変更されていないこと
        # checksums_after = {f: hashlib.md5(f.read_bytes()).hexdigest() for f in src_files}
        # assert checksums_before == checksums_after, "Phase 5 should not modify source code"


class TestPhase6Dependency:
    """Phase 6の依存関係テスト"""

    @pytest.mark.skip(reason="Requires actual phase execution with Claude Agent SDK")
    def test_phase6_uses_phase5_output(self, tmp_path):
        """Phase 6がPhase 5の成果物を使用することを確認

        テストの意図:
        - Phase 6がtest-implementation.mdを参照する
        - Phase 6がPhase 5で作成されたテストファイルを実行する
        - metadata.jsonが正しく更新される

        Note: このテストは実際のClaude Agent SDK呼び出しが必要なため、
        E2Eテスト環境でのみ実行可能です。
        """
        # Setup: Phase 5完了状態
        workflow_dir = tmp_path / '.ai-workflow' / 'issue-324'
        metadata_path = workflow_dir / 'metadata.json'
        state = WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='324',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/324',
            issue_title='Test'
        )
        state.update_phase_status('test_implementation', 'completed')

        # Phase 5の成果物を作成
        test_impl_output = workflow_dir / '05_test_implementation' / 'output'
        test_impl_output.mkdir(parents=True)
        (test_impl_output / 'test-implementation.md').write_text('# Test Implementation')

        # Phase 6実行（ログをキャプチャ）
        # from phases.testing import TestingPhase
        # with patch('builtins.print') as mock_print:
        #     phase = TestingPhase(...)
        #     result = phase.run()

        # Assert: Phase 6がPhase 5の成果物を参照している
        # log_output = '\n'.join([str(call) for call in mock_print.call_args_list])
        # assert 'test-implementation.md' in log_output or '05_test_implementation' in log_output

        # Assert: test-result.md確認
        test_result_md = workflow_dir / '06_testing' / 'output' / 'test-result.md'
        # assert test_result_md.exists(), "test-result.md should be created"


class TestGitIntegration:
    """Git統合のテスト"""

    @pytest.mark.skip(reason="Requires actual Git repository and phase execution")
    def test_git_auto_commit_and_push(self, tmp_path):
        """AC-008: Git auto-commit & pushが正しく動作することを確認

        テストの意図:
        - Phase 5実行後、Gitコミットが作成される
        - コミットメッセージが正しい形式（[ai-workflow] Phase 5 (test_implementation) - completed）
        - 成果物ファイルがコミットに含まれている

        Note: このテストは実際のGit操作が必要なため、
        Git環境が整った状態で実行する必要があります。
        """
        # Setup: Gitリポジトリ初期化
        repo_dir = tmp_path / 'repo'
        repo_dir.mkdir()
        # subprocess.run(['git', 'init'], cwd=repo_dir, check=True)
        # subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo_dir, check=True)
        # subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo_dir, check=True)

        # Phase 5実行（実際のGit操作あり）
        # phase = TestImplementationPhase(...)
        # result = phase.run()

        # Assert: Gitコミット確認
        # git_log = subprocess.run(
        #     ['git', 'log', '--oneline', '-1'],
        #     cwd=repo_dir,
        #     capture_output=True,
        #     text=True
        # ).stdout
        # assert '[ai-workflow] Phase 5 (test_implementation)' in git_log
        # assert 'completed' in git_log or 'failed' in git_log


class TestPromptFiles:
    """プロンプトファイルの存在確認"""

    def test_prompt_files_exist(self, repo_root):
        """AC-001: Phase 5のプロンプトファイルが存在することを確認

        テストの意図:
        - execute.txt、review.txt、revise.txtが存在する
        - 各プロンプトファイルが空でない
        """
        # Given: プロンプトディレクトリ
        prompts_dir = repo_root / 'scripts' / 'ai-workflow' / 'prompts' / 'test_implementation'

        # When: 各プロンプトファイルの存在確認
        execute_txt = prompts_dir / 'execute.txt'
        review_txt = prompts_dir / 'review.txt'
        revise_txt = prompts_dir / 'revise.txt'

        # Then: ファイルが存在する
        assert execute_txt.exists(), "execute.txt should exist"
        assert review_txt.exists(), "review.txt should exist"
        assert revise_txt.exists(), "revise.txt should exist"

        # Then: ファイルが空でない
        assert execute_txt.stat().st_size > 0, "execute.txt should not be empty"
        assert review_txt.stat().st_size > 0, "review.txt should not be empty"
        assert revise_txt.stat().st_size > 0, "revise.txt should not be empty"

    def test_execute_prompt_content(self, repo_root):
        """execute.txtの内容が適切であることを確認

        テストの意図:
        - Planning Document参照セクションがある
        - テスト戦略に基づいた実装指示がある
        - 実コード修正の禁止が明記されている
        """
        # Given: execute.txtファイル
        execute_txt = repo_root / 'scripts' / 'ai-workflow' / 'prompts' / 'test_implementation' / 'execute.txt'
        content = execute_txt.read_text(encoding='utf-8')

        # Then: 重要なセクションが含まれている
        assert 'Planning Document' in content or 'planning_document_path' in content, \
            "execute.txt should reference Planning Document"
        assert 'テスト戦略' in content or 'test_strategy' in content, \
            "execute.txt should mention test strategy"
        assert 'テストコードのみ' in content or '実コードの修正は行わない' in content, \
            "execute.txt should prohibit source code modification"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
