#!/usr/bin/env python3
"""
テスト実行スクリプト

このスクリプトはphase_dependencies関連のテストを実行し、結果を出力します。
"""
import sys
import os

# PYTHONPATHにプロジェクトルートを追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# pytestをインポート
try:
    import pytest
except ImportError:
    print("ERROR: pytest is not installed")
    print("Please install pytest: pip install pytest")
    sys.exit(1)

def main():
    """テストを実行"""
    # テスト実行オプション
    args = [
        'tests/unit/core/test_phase_dependencies.py',
        'tests/integration/test_phase_dependencies_integration.py',
        '-v',  # 詳細出力
        '--tb=short',  # トレースバックを短く
        '-x',  # 最初の失敗で停止
        '--color=yes',  # カラー出力
    ]

    print("=" * 80)
    print("AI Workflow Phase Dependencies - Test Execution")
    print("=" * 80)
    print()

    # pytestを実行
    exit_code = pytest.main(args)

    print()
    print("=" * 80)
    print(f"Test execution finished with exit code: {exit_code}")
    print("=" * 80)

    return exit_code

if __name__ == '__main__':
    sys.exit(main())
