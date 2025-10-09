"""Behaveフック - テスト前後の処理"""
import shutil
from pathlib import Path


def before_scenario(context, scenario):
    """
    各シナリオ実行前の処理

    Args:
        context: Behaveコンテキスト
        scenario: 実行するシナリオ
    """
    # テスト用ワークフローディレクトリのクリーンアップ
    workflow_dir = Path('.ai-workflow/issue-999')
    if workflow_dir.exists():
        shutil.rmtree(workflow_dir)


def after_scenario(context, scenario):
    """
    各シナリオ実行後の処理

    Args:
        context: Behaveコンテキスト
        scenario: 実行したシナリオ
    """
    # テスト後のクリーンアップ（オプション）
    # 必要に応じてコメントアウトを外す
    # workflow_dir = Path('.ai-workflow/issue-999')
    # if workflow_dir.exists():
    #     shutil.rmtree(workflow_dir)
    pass
