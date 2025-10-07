"""BDDステップ定義"""
import json
import os
import shutil
import subprocess
from pathlib import Path
from behave import given, when, then


@given('作業ディレクトリが "{directory}" である')
def step_set_working_directory(context, directory):
    """作業ディレクトリを設定"""
    context.working_dir = Path(directory)
    os.chdir(context.working_dir)


@when('開発者がワークフローを初期化する')
def step_initialize_workflow(context):
    """ワークフロー初期化コマンドを実行"""
    # クリーンアップ（前回のテスト結果を削除）
    workflow_dir = Path('.ai-workflow/issue-999')
    if workflow_dir.exists():
        shutil.rmtree(workflow_dir)

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
