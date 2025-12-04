# dot_processor.py テストドキュメント

## 概要

このディレクトリには、`dot_processor.py`の特性テスト（Characterization Test）が含まれています。

## テスト構造

```
tests/
├── __init__.py
├── conftest.py                # 共通フィクスチャ
├── test_dot_processor.py      # メインテストコード
├── fixtures/
│   └── test_data/             # サンプルデータ
└── README.md                  # このファイル
```

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
# クラス単位
pytest tests/test_dot_processor.py::TestDotFileGeneratorEscaping

# テストケース単位
pytest tests/test_dot_processor.py::TestDotFileGeneratorEscaping::test_escape_dot_string_with_double_quotes

# マーカー指定
pytest tests/ -m "characterization"
pytest tests/ -m "edge_case"
```

## テストの種類

### 特性テスト（Characterization Test）

既存の振る舞いを記録するテスト。将来のリファクタリング時に振る舞いが維持されていることを検証します。

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

1. `test_dot_processor.py`に新しいテストクラスまたはメソッドを追加
2. Given-When-Then形式でコメントを記載
3. 適切なマーカーを付与（`@pytest.mark.characterization`等）
4. テストを実行して動作確認

### テストデータの追加

1. `fixtures/test_data/`にJSONファイルを追加
2. `conftest.py`に新しいフィクスチャを定義
3. テストコードでフィクスチャを使用

## 参考資料

- [pytest公式ドキュメント](https://docs.pytest.org/)
- [特性テスト（Characterization Test）について](https://en.wikipedia.org/wiki/Characterization_test)
- [カバレッジ測定について](https://coverage.readthedocs.io/)
