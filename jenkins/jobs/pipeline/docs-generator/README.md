# Documentation Generator Jobs

## 概要

Githubのソースコードからドキュメント生成を行うツールです。

## ジョブの説明

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

1. コメント自動生成
    - mainブランチへのプッシュ → コメント自動生成 → documentブランチへの反映

2. HTMLドキュメント生成
    - documentブランチへのプッシュ → HTMLドキュメント生成 → GitHub Pagesへの反映（オプション）
