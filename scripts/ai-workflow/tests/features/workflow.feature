# language: ja
機能: AI駆動開発自動化ワークフロー

  シナリオ: ワークフロー初期化とメタデータ作成
    前提 作業ディレクトリが "C:\Users\ytaka\TIELEC\development\infrastructure-as-code" である
    もし 開発者がワークフローを初期化する
      """
      python scripts/ai-workflow/main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/999
      """
    ならば ワークフローディレクトリ ".ai-workflow/issue-999" が作成される
    かつ "metadata.json" ファイルが存在する
    かつ metadata.json に以下の情報が含まれる:
      | フィールド        | 値                |
      | issue_number     | 999               |
      | current_phase    | requirements      |
      | workflow_version | 1.0.0             |
    かつ すべてのフェーズのステータスが "pending" である
