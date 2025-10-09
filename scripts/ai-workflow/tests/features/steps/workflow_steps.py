"""BDDステップ定義"""
import json
import os
import subprocess
from pathlib import Path
from behave import given, when, then


@given('作業ディレクトリが "{directory}" である')
def step_set_working_directory(context, directory):
    """作業ディレクトリを設定"""
    context.working_dir = Path(directory)
    os.chdir(context.working_dir)


@given('作業ディレクトリがリポジトリルートである')
def step_set_working_directory_to_repo_root(context):
    """作業ディレクトリをリポジトリルートに設定"""
    # Gitリポジトリのルートを取得
    result = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],
        capture_output=True,
        text=True,
        check=True
    )
    context.working_dir = Path(result.stdout.strip())
    os.chdir(context.working_dir)


@given('ワークフローが既に初期化されている')
def step_workflow_already_initialized(context):
    """ワークフローを事前に初期化"""
    workflow_dir = Path('.ai-workflow/issue-999')
    cmd = 'python scripts/ai-workflow/main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/999'
    subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
    context.workflow_dir = workflow_dir


@when('開発者がワークフローを初期化する')
def step_initialize_workflow(context):
    """ワークフロー初期化コマンドを実行"""
    workflow_dir = Path('.ai-workflow/issue-999')

    # 初期化コマンド実行
    cmd = context.text.strip()
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    context.command_result = result
    context.workflow_dir = workflow_dir


@then('ワークフローディレクトリ "{directory}" が作成される')
def step_workflow_directory_created(context, directory):
    """ワークフローディレクトリの存在確認"""
    workflow_path = Path(directory)
    assert workflow_path.exists(), f"Workflow directory not found: {workflow_path}"
    assert workflow_path.is_dir(), f"Path is not a directory: {workflow_path}"


@then('"{filename}" ファイルが存在する')
def step_file_exists(context, filename):
    """ファイルの存在確認"""
    file_path = context.workflow_dir / filename
    assert file_path.exists(), f"File not found: {file_path}"


@then('metadata.json に以下の情報が含まれる')
def step_metadata_contains(context):
    """metadata.jsonの内容確認"""
    metadata_path = context.workflow_dir / 'metadata.json'
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    for row in context.table:
        field = row['フィールド']
        expected_value = row['値']

        assert field in metadata, f"Field not found: {field}"

        actual_value = str(metadata[field])
        assert actual_value == expected_value, \
            f"Field {field}: expected {expected_value}, got {actual_value}"


@then('すべてのフェーズのステータスが "{status}" である')
def step_all_phases_have_status(context, status):
    """すべてのフェーズのステータス確認"""
    metadata_path = context.workflow_dir / 'metadata.json'
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    phases = metadata['phases']
    for phase_name, phase_data in phases.items():
        actual_status = phase_data['status']
        assert actual_status == status, \
            f"Phase {phase_name}: expected {status}, got {actual_status}"


@when('開発者が同じIssue番号でワークフローを初期化しようとする')
def step_initialize_workflow_duplicate(context):
    """同じIssue番号でワークフロー初期化を試みる"""
    cmd = context.text.strip()
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    context.command_result = result


@then('コマンドが失敗する')
def step_command_fails(context):
    """コマンドが失敗することを確認"""
    assert context.command_result.returncode != 0, \
        f"Command should have failed but returned {context.command_result.returncode}"


@then('エラーメッセージ "{message}" が表示される')
def step_error_message_displayed(context, message):
    """エラーメッセージが表示されることを確認"""
    output = context.command_result.stdout + context.command_result.stderr
    assert message in output, \
        f"Expected message '{message}' not found in output: {output}"


@when('開発者がヘルプコマンドを実行する')
def step_execute_help_command(context):
    """ヘルプコマンドを実行"""
    cmd = context.text.strip()
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    context.command_result = result


@then('利用可能なコマンドのリストが表示される')
def step_command_list_displayed(context):
    """利用可能なコマンドのリストが表示されることを確認"""
    output = context.command_result.stdout
    assert 'Commands:' in output or 'init' in output, \
        f"Expected command list not found in output: {output}"
    assert context.command_result.returncode == 0, \
        f"Help command failed with return code {context.command_result.returncode}"
