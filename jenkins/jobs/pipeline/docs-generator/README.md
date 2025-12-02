# Documentation Generator Jobs

## 概要

Githubのソースコードからドキュメント生成を行うツールです。

## ジョブの説明

### PRコメント自動生成関連

**pull-request-comment-builder**
- プルリクエストの変更内容を分析し、自動的にコメントとタイトルを生成
- OpenAI APIを使用してインテリジェントな分析を実施
- モジュール化されたアーキテクチャで保守性とテスタビリティを向上

**主要コンポーネント**:
- `models.py`: PR情報とファイル変更のデータモデル
- `statistics.py`: 統計計算とチャンクサイズ最適化
- `formatter.py`: Markdownコメントのフォーマット処理
- `token_estimator.py`: トークン数推定とテキスト切り詰め
- `prompt_manager.py`: プロンプトテンプレート管理

**テストカバレッジ**: 72ケースのテストコード（ユニット、統合、BDD）

### Doxygenコメント自動生成関連

**auto_insert_doxygen_comment**
- ソースコードにDoxygenフォーマットのコメントを自動生成
- プルリクエストの作成または直接プッシュが可能

**auto_insert_doxygen_comment_github_trigger**
- mainブランチへのプッシュを検知して自動実行
- auto_insert_doxygen_commentジョブを起動

### HTMLドキュメント生成関連

**generate_doxygen_html**
- Doxygenを使用してHTMLドキュメントを生成
- GitHub Pagesへのデプロイにも対応

**generate_doxygen_html_github_trigger**
- documentブランチへのプッシュを検知して自動実行
- generate_doxygen_htmlジョブを起動

## 処理の流れ

1. PRコメント自動生成
    - プルリクエスト作成/更新 → ファイル変更の分析 → OpenAI APIによるコメント生成 → PRへのコメント投稿

2. Doxygenコメント自動生成
    - mainブランチへのプッシュ → コメント自動生成 → documentブランチへの反映

3. HTMLドキュメント生成
    - documentブランチへのプッシュ → HTMLドキュメント生成 → GitHub Pagesへの反映（オプション）
