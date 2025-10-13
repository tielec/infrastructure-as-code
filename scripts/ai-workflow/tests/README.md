# AI Workflow テスト

このディレクトリには、AI駆動開発自動化ワークフローのテストスイートが含まれています。

## ディレクトリ構造

```
tests/
├── __init__.py
├── conftest.py              # 共通フィクスチャ定義
├── pytest.ini               # pytest設定（ルートディレクトリ）
├── README.md                # このファイル
├── unit/                    # ユニットテスト（高速、モック使用）
│   ├── core/
│   │   ├── test_claude_agent_client.py
│   │   ├── test_github_client.py（旧版、非推奨）
│   │   ├── git/            # 【v2.4.0】Git Operations テスト
│   │   │   ├── test_repository.py
│   │   │   ├── test_branch.py
│   │   │   └── test_commit.py
│   │   └── github/         # 【v2.4.0】GitHub Operations テスト
│   │       ├── test_issue_client.py
│   │       ├── test_pr_client.py
│   │       └── test_comment_client.py
│   ├── phases/
│   │   └── base/           # 【v2.4.0】Phase基底クラステスト
│   │       ├── test_abstract_phase.py
│   │       ├── test_phase_executor.py
│   │       ├── test_phase_validator.py
│   │       └── test_phase_reporter.py
│   └── common/             # 【v2.4.0】共通処理テスト
│       ├── test_logger.py
│       ├── test_error_handler.py
│       ├── test_retry.py
│       └── test_file_handler.py
├── integration/             # 統合テスト（中速、実ファイルI/O）
│   ├── test_docker_environment.py
│   └── test_phase1_review.py
├── e2e/                     # E2Eテスト（低速、外部API使用）
└── fixtures/                # テストデータ・フィクスチャ
```

**【v2.4.0の変更点】**:
- **新規テストディレクトリ**: unit/core/git/, unit/core/github/, unit/phases/base/, unit/common/
- **テストファイル追加**: Issue #376のリファクタリングに伴い、分割された各クラス用のテストファイルを追加
- **Phase 5で実装**: これらのテストファイルはPhase 5（テストコード実装）で作成される予定

## テスト種別

### ユニットテスト (unit/)
- **目的**: 個別モジュールの動作確認
- **実行速度**: 高速（数秒）
- **依存関係**: モック使用、外部API不要
- **マーカー**: `@pytest.mark.unit`

### 統合テスト (integration/)
- **目的**: モジュール間の連携確認
- **実行速度**: 中速（数十秒〜数分）
- **依存関係**: 実ファイルI/O、Docker環境
- **マーカー**: `@pytest.mark.integration`

### E2Eテスト (e2e/)
- **目的**: エンドツーエンドの動作確認
- **実行速度**: 低速（数分〜数十分）
- **依存関係**: 外部API（GitHub、Claude）、Docker必須
- **マーカー**: `@pytest.mark.e2e`

## テストマーカー

pytest.iniで定義されているカスタムマーカー：

| マーカー | 説明 |
|---------|------|
| `unit` | ユニットテスト（高速、モック使用） |
| `integration` | 統合テスト（中速、実ファイルI/O） |
| `e2e` | E2Eテスト（低速、外部API使用、Docker必須） |
| `slow` | 実行時間が長いテスト（3分以上） |
| `requires_docker` | Docker環境が必要なテスト |
| `requires_github` | GitHub API認証が必要なテスト |
| `requires_claude` | Claude API認証が必要なテスト |

## テスト実行方法

### 前提条件

1. **環境変数の設定**:
   ```bash
   export GITHUB_TOKEN="ghp_..."
   export GITHUB_REPOSITORY="tielec/infrastructure-as-code"
   export CLAUDE_CODE_OAUTH_TOKEN="sk-ant-oat01-..."
   ```

2. **Docker環境**:
   - Docker Desktop起動
   - ai-workflowイメージをビルド済み

### 基本的な実行方法

```bash
# すべてのテストを実行
pytest

# 詳細出力で実行
pytest -v

# 特定のディレクトリのみ実行
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# 特定のファイルのみ実行
pytest tests/unit/core/test_github_client.py

# 特定のテスト関数のみ実行
pytest tests/unit/core/test_github_client.py::TestGitHubClient::test_client_initialization
```

### マーカーを使った実行

```bash
# ユニットテストのみ実行
pytest -m unit

# 統合テストのみ実行
pytest -m integration

# E2Eテストのみ実行
pytest -m e2e

# GitHub API不要なテストのみ実行
pytest -m "not requires_github"

# 高速なテストのみ実行（slowマーカーを除外）
pytest -m "not slow"
```

### Docker環境での実行

```bash
# Dockerコンテナ内でテスト実行
docker run --rm \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  -e GITHUB_REPOSITORY="${GITHUB_REPOSITORY}" \
  -e CLAUDE_CODE_OAUTH_TOKEN="${CLAUDE_CODE_OAUTH_TOKEN}" \
  -v "$(pwd):/workspace" \
  -w "/workspace/scripts/ai-workflow" \
  ai-workflow:latest \
  pytest -v

# ユニットテストのみDocker実行
docker run --rm \
  -v "$(pwd):/workspace" \
  -w "/workspace/scripts/ai-workflow" \
  ai-workflow:latest \
  pytest -m unit -v
```

## カバレッジ測定

```bash
# カバレッジ付きで実行
pytest --cov=core --cov=phases --cov-report=html --cov-report=term

# HTML レポート生成
pytest --cov=core --cov=phases --cov-report=html
# htmlcov/index.html をブラウザで開く
```

## トラブルシューティング

### テストが収集されない

**症状**: `collected 0 items`

**原因**:
1. `__init__.py`がない
2. テストファイル名が`test_*.py`形式でない
3. テストクラス名が`Test*`形式でない
4. テスト関数名が`test_*`形式でない

**解決方法**:
```bash
# ファイル名確認
ls tests/unit/core/

# __init__.py確認
find tests -name __init__.py

# pytest設定確認
cat pytest.ini
```

### Import Error

**症状**: `ModuleNotFoundError: No module named 'core'`

**原因**: Python pathに親ディレクトリが含まれていない

**解決方法**: conftest.pyの`add_project_root_to_path`フィクスチャが正しく動作しているか確認

### 環境変数エラー

**症状**: `pytest.skip("GITHUB_TOKEN not set")`

**解決方法**: 環境変数を設定してテスト実行
```bash
export GITHUB_TOKEN="ghp_..."
export GITHUB_REPOSITORY="tielec/infrastructure-as-code"
pytest
```

## テスト追加ガイドライン

### 新しいユニットテストの追加

1. 適切なディレクトリにファイル作成: `tests/unit/{module}/test_{name}.py`
2. pytest マーカー付与: `@pytest.mark.unit`
3. 必要に応じて追加マーカー: `@pytest.mark.requires_{dependency}`
4. docstring で目的を明記

例:
```python
"""新機能 ユニットテスト

新機能の基本動作確認
"""
import pytest
from core.new_module import NewClass

@pytest.mark.unit
class TestNewClass:
    """NewClassのユニットテスト"""

    def test_initialization(self):
        """初期化テスト"""
        obj = NewClass()
        assert obj is not None
```

### 新しい統合テストの追加

1. ファイル作成: `tests/integration/test_{feature}.py`
2. pytest マーカー付与:
   ```python
   pytestmark = [
       pytest.mark.integration,
       pytest.mark.requires_docker  # 必要に応じて
   ]
   ```
3. 実ファイル・実環境を使用
4. クリーンアップ処理を含める

### テストフィクスチャの追加

共通フィクスチャは`conftest.py`に追加:

```python
@pytest.fixture
def sample_data():
    """サンプルデータ"""
    return {"key": "value"}
```

## 参考リンク

- [pytest公式ドキュメント](https://docs.pytest.org/)
- [pytest マーカー](https://docs.pytest.org/en/stable/example/markers.html)
- [pytest フィクスチャ](https://docs.pytest.org/en/stable/fixture.html)
