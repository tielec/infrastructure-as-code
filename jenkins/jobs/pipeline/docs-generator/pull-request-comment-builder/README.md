# PR Comment Generator

プルリクエストの変更内容を自動的に分析し、インテリジェントなコメントとタイトルを生成するツールです。

## 概要

OpenAI APIを使用してプルリクエストの変更内容を分析し、以下を自動生成します：

- **PRコメント**: 変更内容のサマリー、チャンク分析結果、ファイルリスト
- **PRタイトル**: 変更内容を簡潔に表現したタイトル

## アーキテクチャ

### モジュール構成

本ツールは保守性とテスタビリティを向上させるため、以下のモジュールに分割されています：

```
src/pr_comment_generator/
├── __init__.py           # Facade（互換性レイヤー）
├── models.py             # データモデル（PRInfo, FileChange）
├── statistics.py         # 統計計算とチャンクサイズ最適化
├── formatter.py          # Markdownフォーマット処理
├── token_estimator.py    # トークン数推定とテキスト切り詰め
├── prompt_manager.py     # プロンプトテンプレート管理
├── openai_client.py      # OpenAI API連携（リトライ、トークン管理）
├── generator.py          # PRコメント生成オーケストレーター
├── chunk_analyzer.py     # チャンク分割・分析調整
└── cli.py                # CLIエントリポイント
```

### 主要コンポーネント

#### models.py
PR情報とファイル変更のデータモデルを定義します。

- `PRInfo`: PRの基本情報（タイトル、番号、本文、ブランチ等）
- `FileChange`: ファイル変更情報（ファイル名、ステータス、追加/削除行数等）

#### statistics.py
統計計算とチャンクサイズの最適化を行います。

- 最適なチャンクサイズの計算
- チャンクのトークン数推定
- ファイル変更の統計情報計算

#### formatter.py
コメントのフォーマット処理を行います。

- Markdownのクリーンアップ
- チャンク分析結果のフォーマット
- ファイルリストのフォーマット
- 最終コメントの組み立て

#### token_estimator.py
トークン数の推定とテキスト切り詰めを行います。

- 日本語・英語混在テキストのトークン数推定
- バイナリサーチによる効率的なテキスト切り詰め

#### prompt_manager.py
プロンプトテンプレートの管理を行います。

- テンプレートファイルの読み込み
- プロンプトのフォーマット
- チャンク分析・サマリー生成用プロンプトの生成

#### openai_client.py
OpenAI APIとの通信を管理します。

- API呼び出し（指数バックオフリトライ付き）
- トークン使用量の追跡
- プロンプトと結果の保存（デバッグ用）
- 入力サイズの最適化

#### generator.py
PRコメント生成のオーケストレーターです。

- 依存コンポーネントの初期化
- PR情報とDiffの読み込み
- GitHubからのファイル内容取得
- コメント生成ワークフローの調整

#### chunk_analyzer.py
PRファイル変更のチャンク分割と分析を調整します。

- 最適なチャンクサイズの計算
- ファイル変更のチャンク分割
- チャンク分析の調整

#### cli.py
コマンドライン処理を担当します。

- 引数パーサー設定
- 環境変数オーバーライド
- エラーハンドリングとJSON出力処理

## 使用方法

### 基本的な使用方法

```bash
python pr_comment_generator.py \
  --pr-info <PR情報JSONファイル> \
  --pr-diff <Diff JSONファイル> \
  --output <出力JSONファイル>
```

### オプション

- `--template-dir`: テンプレートディレクトリパス（デフォルト: `templates`）
- `--save-prompts`: プロンプトと結果を保存
- `--prompt-output-dir`: プロンプト保存ディレクトリ（デフォルト: `/prompts`）
- `--log-level`: ログレベル（デフォルト: `INFO`）

### 環境変数

- `OPENAI_API_KEY`: OpenAI APIキー（必須）
- `OPENAI_MODEL_NAME`: 使用するモデル名（デフォルト: `gpt-4-turbo`）
- `SAVE_PROMPTS`: プロンプト保存フラグ（デフォルト: `true`）

## テスト

### テストの実行

```bash
# すべてのテストを実行
pytest tests/ -v

# ユニットテストのみ
pytest tests/unit/ -v

# 統合テストのみ
pytest tests/integration/ -v

# BDDテストのみ
pytest tests/bdd/ -v

# カバレッジレポート付き
pytest tests/ --cov=pr_comment_generator --cov-report=term --cov-report=html
```

### テストカバレッジ

- **ユニットテスト**: 90ケース（10モジュール）
- **統合テスト**: 12ケース（モジュール間連携、互換性レイヤー）
- **BDDテスト**: 5ケース（エンドユーザーシナリオ）
- **合計**: 107ケース
- **目標カバレッジ**: 80%以上

## 開発

### 後方互換性

旧インポートパスとの互換性を維持するため、Facadeパターンを実装しています：

```python
# 旧インポートパス（非推奨だが動作する）
from pr_comment_generator import PRCommentGenerator

# 新インポートパス（推奨）
from pr_comment_generator.generator import PRCommentGenerator
from pr_comment_generator.openai_client import OpenAIClient
from pr_comment_generator.chunk_analyzer import ChunkAnalyzer
from pr_comment_generator.models import PRInfo, FileChange
from pr_comment_generator.cli import main
```

### コーディング規約

- Python PEP 8に準拠
- 日本語コメントを使用
- 型ヒントを活用
- ドキュメント文字列を記述

## トラブルシューティング

### APIキー未設定エラー

```bash
# エラー: Missing required environment variable: OPENAI_API_KEY
export OPENAI_API_KEY="your-api-key"
```

### テスト実行エラー

```bash
# pytest未インストールの場合
pip install -r requirements.txt
```

### インポートエラー

```bash
# Pythonパスの設定
export PYTHONPATH="/path/to/pull-request-comment-builder/src:$PYTHONPATH"
```

## 関連ドキュメント

### Issue #445（初期実装）
- [要件定義書](.ai-workflow/issue-445/01_requirements/output/requirements.md)
- [設計書](.ai-workflow/issue-445/02_design/output/design.md)
- [テストシナリオ](.ai-workflow/issue-445/03_test_scenario/output/test-scenario.md)
- [実装ログ](.ai-workflow/issue-445/04_implementation/output/implementation.md)
- [テスト実装ログ](.ai-workflow/issue-445/05_test_implementation/output/test-implementation.md)

### Issue #528（モジュール分割リファクタリング）
- [計画書](.ai-workflow/issue-528/00_planning/output/planning.md)
- [要件定義書](.ai-workflow/issue-528/01_requirements/output/requirements.md)
- [設計書](.ai-workflow/issue-528/02_design/output/design.md)
- [テストシナリオ](.ai-workflow/issue-528/03_test_scenario/output/test-scenario.md)
- [実装ログ](.ai-workflow/issue-528/04_implementation/output/implementation.md)
- [テスト実装ログ](.ai-workflow/issue-528/05_test_implementation/output/test-implementation.md)
