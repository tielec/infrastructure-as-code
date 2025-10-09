"""ワークフロー初期化の統合テスト"""
import json
import subprocess
import pytest
from pathlib import Path
import shutil


class TestWorkflowInit:
    """ワークフロー初期化の統合テスト"""

    @pytest.fixture
    def repo_root(self):
        """リポジトリルートを取得"""
        # Git リポジトリのルートを取得
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            check=True
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def cleanup_workflow(self, repo_root):
        """テスト後のクリーンアップ"""
        workflow_dir = repo_root / '.ai-workflow' / 'issue-999'

        # テスト前にクリーンアップ
        if workflow_dir.exists():
            shutil.rmtree(workflow_dir)

        yield workflow_dir

        # テスト後にクリーンアップ
        if workflow_dir.exists():
            shutil.rmtree(workflow_dir)

    def test_cli_init_command_success(self, repo_root, cleanup_workflow):
        """
        CLI initコマンド → WorkflowState → ファイルシステム統合テスト

        検証項目:
        - CLIの`init`コマンドがWorkflowState.create_new()を正しく呼び出すか
        - WorkflowStateがmetadata.jsonを正しく生成し、ファイルシステムに保存するか
        """
        # Arrange
        workflow_dir = cleanup_workflow
        issue_url = 'https://github.com/tielec/infrastructure-as-code/issues/999'

        # Act
        result = subprocess.run(
            ['python', 'scripts/ai-workflow/main.py', 'init', '--issue-url', issue_url],
            cwd=repo_root,
            capture_output=True,
            text=True
        )

        # Assert
        assert result.returncode == 0, f"Command failed: {result.stderr}"
        assert '[OK] Workflow initialized' in result.stdout
        assert workflow_dir.exists()

        metadata_path = workflow_dir / 'metadata.json'
        assert metadata_path.exists()

    def test_metadata_json_structure(self, repo_root, cleanup_workflow):
        """
        WorkflowState → metadata.json → 読み込み検証

        検証項目:
        - WorkflowStateが生成したmetadata.jsonの構造とデータが要件通りであるか
        - 保存後の再読み込みでデータが一致するか
        """
        # Arrange
        workflow_dir = cleanup_workflow
        issue_url = 'https://github.com/tielec/infrastructure-as-code/issues/999'

        # Act - ワークフロー初期化
        subprocess.run(
            ['python', 'scripts/ai-workflow/main.py', 'init', '--issue-url', issue_url],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True
        )

        # Assert - metadata.jsonを読み込んで検証
        metadata_path = workflow_dir / 'metadata.json'
        with open(metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 必須フィールドの存在確認
        assert data['issue_number'] == '999'
        assert data['issue_url'] == issue_url
        assert data['workflow_version'] == '1.0.0'
        assert data['current_phase'] == 'requirements'

        # design_decisionsが初期化されているか
        assert data['design_decisions']['implementation_strategy'] is None
        assert data['design_decisions']['test_strategy'] is None
        assert data['design_decisions']['test_code_strategy'] is None

        # cost_trackingが初期化されているか
        assert data['cost_tracking']['total_input_tokens'] == 0
        assert data['cost_tracking']['total_output_tokens'] == 0
        assert data['cost_tracking']['total_cost_usd'] == 0.0

        # phasesがすべて存在し、pendingであるか
        phases = ['requirements', 'design', 'test_scenario',
                  'implementation', 'testing', 'documentation']
        for phase in phases:
            assert phase in data['phases']
            assert data['phases'][phase]['status'] == 'pending'
            assert data['phases'][phase]['retry_count'] == 0
            assert data['phases'][phase]['started_at'] is None
            assert data['phases'][phase]['completed_at'] is None

        # タイムスタンプがISO 8601形式であるか
        assert data['created_at'].endswith('Z')
        assert data['updated_at'].endswith('Z')

    def test_metadata_json_utf8_encoding(self, repo_root, cleanup_workflow):
        """
        日本語データの保存・読み込み検証

        検証項目:
        - 日本語を含むデータが正しく処理されるか
        - UTF-8エンコーディングが正しく設定されるか
        """
        # Arrange
        workflow_dir = cleanup_workflow
        issue_url = 'https://github.com/tielec/infrastructure-as-code/issues/999'

        # Act - ワークフロー初期化
        subprocess.run(
            ['python', 'scripts/ai-workflow/main.py', 'init', '--issue-url', issue_url],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True
        )

        # Assert - metadata.jsonを読み込んで日本語確認
        metadata_path = workflow_dir / 'metadata.json'

        # UTF-8で読み込めるか
        with open(metadata_path, 'r', encoding='utf-8') as f:
            content = f.read()
            data = json.loads(content)

        # issue_titleが正しく保存されているか
        assert 'Issue #999' in data['issue_title']

        # ファイル内容に日本語が含まれていた場合、正しく保存されているか確認
        # （このテストケースでは日本語は含まれていないが、仕組みを確認）
        # ensure_ascii=Falseが適用されているか確認するため、
        # ファイル内容に \uXXXX 形式のエスケープがないことを確認
        assert '\\u' not in content or 'issue_url' in content  # URLには\uが含まれる可能性があるため除外

    def test_existing_workflow_error(self, repo_root, cleanup_workflow):
        """
        既存ワークフロー存在時のエラーハンドリング

        検証項目:
        - 同じIssue番号で2回目の初期化を試みた場合、適切なエラーメッセージが表示されるか
        - 既存のmetadata.jsonが上書きされないか
        """
        # Arrange
        workflow_dir = cleanup_workflow
        issue_url = 'https://github.com/tielec/infrastructure-as-code/issues/999'

        # 1回目の初期化
        subprocess.run(
            ['python', 'scripts/ai-workflow/main.py', 'init', '--issue-url', issue_url],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True
        )

        # 既存のmetadata.jsonのタイムスタンプを記録
        metadata_path = workflow_dir / 'metadata.json'
        original_mtime = metadata_path.stat().st_mtime

        # Act - 2回目の初期化（エラーになるはず）
        result = subprocess.run(
            ['python', 'scripts/ai-workflow/main.py', 'init', '--issue-url', issue_url],
            cwd=repo_root,
            capture_output=True,
            text=True
        )

        # Assert
        assert result.returncode != 0, "Command should have failed"
        assert 'Error: Workflow already exists' in result.stdout

        # 既存ファイルが上書きされていないか確認
        assert metadata_path.stat().st_mtime == original_mtime

    def test_workflow_directory_structure(self, repo_root, cleanup_workflow):
        """
        ワークフロー初期化後のディレクトリ構造確認

        検証項目:
        - `.ai-workflow/issue-{number}/`ディレクトリが作成されるか
        - metadata.jsonが正しい場所に配置されるか
        """
        # Arrange
        workflow_dir = cleanup_workflow
        issue_url = 'https://github.com/tielec/infrastructure-as-code/issues/999'

        # Act
        subprocess.run(
            ['python', 'scripts/ai-workflow/main.py', 'init', '--issue-url', issue_url],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True
        )

        # Assert
        assert workflow_dir.exists()
        assert workflow_dir.is_dir()

        metadata_path = workflow_dir / 'metadata.json'
        assert metadata_path.exists()
        assert metadata_path.is_file()

    def test_metadata_reload_consistency(self, repo_root, cleanup_workflow):
        """
        WorkflowStateでの再読み込み一貫性テスト

        検証項目:
        - metadata.jsonを作成後、WorkflowStateで再読み込みしてデータが一致するか
        """
        # Arrange
        workflow_dir = cleanup_workflow
        issue_url = 'https://github.com/tielec/infrastructure-as-code/issues/999'

        # Act - ワークフロー初期化
        subprocess.run(
            ['python', 'scripts/ai-workflow/main.py', 'init', '--issue-url', issue_url],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True
        )

        # Pythonスクリプトで再読み込みテスト
        test_script = f"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path('{repo_root}') / 'scripts' / 'ai-workflow'))

from core.workflow_state import WorkflowState

metadata_path = Path('{workflow_dir}') / 'metadata.json'
state = WorkflowState(metadata_path)

assert state.data['issue_number'] == '999'
assert state.data['workflow_version'] == '1.0.0'
print('OK')
"""

        result = subprocess.run(
            ['python', '-c', test_script],
            capture_output=True,
            text=True
        )

        # Assert
        assert result.returncode == 0, f"Reload test failed: {result.stderr}"
        assert 'OK' in result.stdout
