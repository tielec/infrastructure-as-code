# dot_processor.py テストドキュメント

## 概要

このディレクトリには、`dot_processor.py`の特性テスト（Characterization Test）が含まれています。

## テスト構造

```
tests/
├── __init__.py
├── conftest.py                      # 共通フィクスチャ
├── test_dot_processor.py            # DotFileProcessorのテスト（統合テスト）
├── test_urn_processor.py            # UrnProcessorのテスト（ユニットテスト）
├── test_node_label_generator.py     # NodeLabelGeneratorのテスト（ユニットテスト）
├── fixtures/
│   └── test_data/                   # サンプルデータ
└── README.md                        # このファイル
```

**Phase 2-1リファクタリング（Issue #461）による変更**:
- `test_urn_processor.py` を追加: `UrnProcessor`クラスの単体テスト（24ケース）
- `test_dot_processor.py` を更新: 統合テストとして継続（UrnProcessor経由のテスト）

**Phase 2-2リファクタリング（Issue #462）による変更**:
- `test_node_label_generator.py` を追加: `NodeLabelGenerator`クラスの単体テスト（29ケース）
- `test_dot_processor.py` を更新: 統合テストとして継続（NodeLabelGenerator経由のテスト）

**Phase 2-3リファクタリング（Issue #463）による変更**:
- `test_resource_dependency_builder.py` を追加: `ResourceDependencyBuilder`クラスの単体テスト（37ケース）
- `test_dot_processor.py` を更新: 統合テストとして継続（ResourceDependencyBuilder経由のテスト）

**Phase 3リファクタリング（Issue #464）による変更**:
- `test_dot_processor.py` を更新: 新規テストケース24個を追加
  - `TestDotProcessorHelperMethods`: 新規ヘルパーメソッドの単体テスト（17ケース）
  - `TestDotProcessorIntegration`: Phase 3統合テスト（6ケース）
  - `TestDotProcessorPerformance`: パフォーマンステスト（1ケース）

## テスト実行方法

### 前提条件

```bash
# Python 3.8以上が必要
python3 --version

# 依存ライブラリのインストール
pip3 install pytest==7.4.3 pytest-cov==4.1.0 pytest-mock==3.12.0
```

### 基本的な実行

```bash
# すべてのテストを実行
pytest tests/

# 詳細な出力
pytest tests/ -v

# 並列実行（高速化）
pytest tests/ -n auto
```

### カバレッジ測定

```bash
# カバレッジ測定（ターミナル出力）
pytest --cov=src --cov-report=term tests/

# カバレッジ測定（HTMLレポート生成）
pytest --cov=src --cov-report=html tests/

# HTMLレポートを開く
# macOS
open htmlcov/index.html
# Linux
xdg-open htmlcov/index.html
```

### 特定のテストのみ実行

```bash
# UrnProcessorのユニットテストのみ実行
pytest tests/test_urn_processor.py -v

# NodeLabelGeneratorのユニットテストのみ実行
pytest tests/test_node_label_generator.py -v

# ResourceDependencyBuilderのユニットテストのみ実行
pytest tests/test_resource_dependency_builder.py -v

# DotFileProcessorの統合テストのみ実行
pytest tests/test_dot_processor.py -v

# Phase 3で追加されたテストのみ実行
pytest tests/test_dot_processor.py::TestDotProcessorHelperMethods -v
pytest tests/test_dot_processor.py::TestDotProcessorIntegration -v
pytest tests/test_dot_processor.py::TestDotProcessorPerformance -v

# クラス単位
pytest tests/test_dot_processor.py::TestDotFileGeneratorEscaping
pytest tests/test_urn_processor.py::TestUrnProcessorParsing
pytest tests/test_node_label_generator.py::TestGenerateNodeLabel

# テストケース単位
pytest tests/test_dot_processor.py::TestDotFileGeneratorEscaping::test_escape_dot_string_with_double_quotes
pytest tests/test_urn_processor.py::TestUrnProcessorParsing::test_parse_urn_valid_aws
pytest tests/test_node_label_generator.py::TestGenerateNodeLabel::test_generate_node_label_stack_resource
pytest tests/test_resource_dependency_builder.py::TestURNMapping::test_create_urn_to_node_mapping_正常系_3リソース

# マーカー指定
pytest tests/ -m "characterization"
pytest tests/ -m "unit"
pytest tests/ -m "edge_case"
pytest tests/ -m "performance"
```

## テストの種類

### ユニットテスト（Unit Test）

**Phase 2-1で追加**: `test_urn_processor.py`

`UrnProcessor`クラスの全公開メソッドを独立してテストします。

- **対象**: URNパース、ラベル生成、リソース判定
- **テストケース数**: 24ケース
- **カバレッジ目標**: 80%以上

**Phase 2-2で追加**: `test_node_label_generator.py`

`NodeLabelGenerator`クラスの全公開メソッドを独立してテストします。

- **対象**: ノードラベル生成、スタックラベル、リソースラベル、プロバイダー別色設定
- **テストケース数**: 29ケース
- **カバレッジ目標**: 80%以上

**Phase 2-3で追加**: `test_resource_dependency_builder.py`

`ResourceDependencyBuilder`クラスの全公開メソッドを独立してテストします。

- **対象**: URNマッピング作成、直接依存関係、親依存関係、プロパティ依存関係
- **テストケース数**: 37ケース
- **カバレッジ目標**: 80%以上

**Phase 3で追加**: `test_dot_processor.py`に新規テストクラスを追加

Phase 3リファクタリング後の新規ヘルパーメソッドと統合動作をテストします。

- **対象**: 新規ヘルパーメソッド、統合動作、パフォーマンス
- **テストケース数**: 24ケース
  - `TestDotProcessorHelperMethods`: 17ケース
  - `TestDotProcessorIntegration`: 6ケース
  - `TestDotProcessorPerformance`: 1ケース
- **カバレッジ目標**: 80%以上

### 特性テスト（Characterization Test）

**既存**: `test_dot_processor.py`

既存の振る舞いを記録するテスト。将来のリファクタリング時に振る舞いが維持されていることを検証します。Phase 2-1リファクタリング後は、統合テストとしても機能します。

### エッジケーステスト

異常系や境界値のテスト。空文字列、極端に長い入力、不正な形式など。

## トラブルシューティング

### テストが失敗する場合

1. 既存コードの振る舞いが変更されていないか確認
2. テストデータが正しく読み込まれているか確認
3. Pythonパスが正しく設定されているか確認

### カバレッジが目標値（80%）に達しない場合

1. 未カバーのメソッドを確認: `htmlcov/index.html`を開く
2. 優先順位の高いメソッドから追加テストを作成
3. プライベートメソッドは公開メソッド経由でテスト

### ImportErrorが発生する場合

```bash
# src/ディレクトリへのパスが正しく設定されているか確認
# conftest.pyでsys.pathに追加しているため、通常は問題なし

# それでも解決しない場合は、PYTHONPATHを設定
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
pytest tests/
```

## 開発者向け情報

### 新規テストケースの追加

1. 対応するテストファイルに新しいテストクラスまたはメソッドを追加
   - `test_dot_processor.py`: 統合テスト
   - `test_urn_processor.py`: UrnProcessorの単体テスト
   - `test_node_label_generator.py`: NodeLabelGeneratorの単体テスト
   - `test_resource_dependency_builder.py`: ResourceDependencyBuilderの単体テスト
2. Given-When-Then形式でコメントを記載
3. 適切なマーカーを付与（`@pytest.mark.characterization`、`@pytest.mark.unit`等）
4. テストを実行して動作確認

### テストデータの追加

1. `fixtures/test_data/`にJSONファイルを追加
2. `conftest.py`に新しいフィクスチャを定義
3. テストコードでフィクスチャを使用

**Phase 2-1で追加されたフィクスチャ**:
- `urn_processor`: `UrnProcessor`インスタンスを返すフィクスチャ

**Phase 2-2で追加されたフィクスチャ**:
- `node_label_generator`: `NodeLabelGenerator`インスタンスを返すフィクスチャ

**Phase 2-3で追加されたフィクスチャ**:
- `resource_dependency_builder`: `ResourceDependencyBuilder`クラスを返すフィクスチャ（静的メソッドのためクラスを直接返す）

## 参考資料

- [pytest公式ドキュメント](https://docs.pytest.org/)
- [特性テスト（Characterization Test）について](https://en.wikipedia.org/wiki/Characterization_test)
- [カバレッジ測定について](https://coverage.readthedocs.io/)
